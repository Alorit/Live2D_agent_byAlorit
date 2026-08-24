"""桌面宠物窗口：透明无边框 + 语音气泡 + Live2D/兜底形象。"""
from __future__ import annotations

import logging

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from .fallback_pet import FallbackPet

logger = logging.getLogger("gui.pet")


class PetWindow(QWidget):
    """无边框透明置顶宠物窗口。"""
    chat_toggle_requested = Signal()
    exit_requested = Signal()
    model_failed = Signal(str)

    def __init__(self, cfg):
        super().__init__(None)
        self.cfg = cfg
        l2d = cfg.live2d
        self.bubble_hide_ms = 0

        flags = Qt.FramelessWindowHint | Qt.Tool
        if l2d.get("pet_always_on_top", True) or cfg.gui.get("pet_always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 基准尺寸 + 整体缩放。缩放现在会直接改变窗口大小，模型跟着窗口走
        self.base_width = int(l2d.get("width", 340))
        self.base_height = int(l2d.get("height", 420))
        self._current_scale = float(l2d.get("scale", 1.0) or 1.0)
        self._apply_window_scale()

        self._setup_ui()

        # 选择渲染器
        self.renderer = self._create_renderer()
        self.layout().addWidget(self.renderer, 1)

        # 上下文菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

    # ------------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(0)

        self.bubble = QLabel("", self)
        self.bubble.setWordWrap(True)
        self.bubble.setMaximumWidth(280)
        self.bubble.setStyleSheet(
            "QLabel {"
            " background-color: rgba(255, 255, 255, 235);"
            " color: #333; border-radius: 12px; padding: 10px 14px;"
            " font-size: 13px; font-family: 'Microsoft YaHei';"
            "}")
        self.bubble.hide()
        self.bubble.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.bubble, 0, Qt.AlignHCenter | Qt.AlignTop)

    def _create_renderer(self):
        l2d = self.cfg.live2d
        model_path = getattr(self.cfg, "live2d_model_path", "")
        use_live2d = l2d.get("enabled", True) and bool(model_path)

        if use_live2d:
            try:
                from .live2d_view import Live2DView
                view = Live2DView(self)
                view.bridge.modelError.connect(self._on_model_error)
                view.bridge.dragStarted.connect(self._on_drag_started)
                view.bridge.dragTo.connect(self._on_drag_to)
                view.bridge.petClicked.connect(self.chat_toggle_requested)
                view.bridge.ready.connect(lambda: view.load_model(model_path))
                self._live2d = view
                return view
            except Exception as e:
                logger.warning("QWebEngine Live2D 不可用，使用内置宠物：%s", e)
                if not l2d.get("fallback_on_error", True):
                    self.model_failed.emit(str(e))
        else:
            logger.info("未配置 Live2D 模型路径，使用内置 QPainter 宠物。")

        pet = FallbackPet(self, bg_color=tuple(l2d.get("bg_color", [245, 245, 245])))
        pet.clicked.connect(self.chat_toggle_requested)
        pet.drag_to.connect(self._move_window_to)
        self._live2d = None
        return pet

    def _on_model_error(self, msg: str):
        logger.warning("Live2D 模型加载失败：%s", msg)
        self.model_failed.emit(msg)
        if self.cfg.live2d.get("fallback_on_error", True):
            self._replace_with_fallback()

    def _replace_with_fallback(self):
        if isinstance(self.renderer, FallbackPet):
            return
        old = self.renderer
        self.layout().removeWidget(old)
        old.hide()
        old.deleteLater()
        pet = FallbackPet(self, bg_color=tuple(self.cfg.live2d.get("bg_color", [245, 245, 245])))
        pet.clicked.connect(self.chat_toggle_requested)
        pet.drag_to.connect(self._move_window_to)
        self.layout().addWidget(pet, 1)
        self.renderer = pet
        self._live2d = None

    # ------------------------------------------------------------------
    def _on_drag_started(self, gx: int, gy: int):
        self._drag_offset = QPoint(gx - self.x(), gy - self.y())

    def _on_drag_to(self, gx: int, gy: int):
        if not hasattr(self, "_drag_offset"):
            self._drag_offset = QPoint(gx - self.x(), gy - self.y())
        self.move(gx - self._drag_offset.x(), gy - self._drag_offset.y())

    def _move_window_to(self, x: int, y: int):
        self.move(x, y)

    # ------------------------------------------------------------------
    def show_bubble(self, text: str):
        text = (text or "").strip()
        if not text:
            self.bubble.hide()
            return
        self.bubble.setText(text)
        self.bubble.show()
        secs = min(max(len(text) * 0.25, 3.0), 12.0)
        self.bubble_hide_ms = int(secs * 1000)
        QTimer.singleShot(self.bubble_hide_ms, self._hide_bubble)

    def _hide_bubble(self):
        self.bubble.hide()

    def apply_commands(self, commands):
        """把 LLM 输出的 [expr:xx] [motion:xx] 映射后发给渲染器。"""
        for kind, name in commands:
            if kind == "expr":
                mapped = self._map_name("emotion_map", name)
                self.renderer.set_expression(mapped)
            elif kind == "motion":
                mapped = self._map_name("motion_map", name)
                self.renderer.set_motion(mapped)

    def _map_name(self, map_key: str, name: str) -> str:
        mapping = self.cfg.persona.get(map_key, {})
        if isinstance(mapping, dict):
            return mapping.get(name, name)
        return name

    def set_speaking(self, speaking: bool):
        self.renderer.set_speaking(speaking)

    def _apply_window_scale(self):
        """按缩放倍率调整窗口大小（显示区域跟着变大/变小）。"""
        self._current_scale = max(0.3, min(4.0, self._current_scale))
        w = max(140, int(self.base_width * self._current_scale))
        h = max(180, int(self.base_height * self._current_scale))
        self.resize(w, h)
        # 气泡宽度也随窗口适度缩放，但设个上限避免过宽
        if hasattr(self, "bubble"):
            self.bubble.setMaximumWidth(min(560, int(280 * self._current_scale)))

    def set_scale(self, scale: float):
        self._current_scale = float(scale or 1.0)
        self._apply_window_scale()
        # Live2D 渲染器：窗口 resize 后页面会触发 resize 事件自动重新布局；
        # 这里再把内部倍率重置为 1.0，避免窗口和模型双重缩放。
        if hasattr(self.renderer, "set_scale"):
            self.renderer.set_scale(1.0)

    def reload_model(self, model_path: str):
        if hasattr(self.renderer, "load_model"):
            self.renderer.load_model(model_path)

    # ------------------------------------------------------------------
    def _show_menu(self, pos):
        menu = QMenu(self)
        act_chat = QAction("显示/隐藏对话框", self)
        act_chat.triggered.connect(self.chat_toggle_requested)
        menu.addAction(act_chat)
        menu.addSeparator()
        act_exit = QAction("退出", self)
        act_exit.triggered.connect(self.exit_requested)
        menu.addAction(act_exit)
        menu.exec(self.mapToGlobal(pos))

    def closeEvent(self, event):
        # 关闭宠物窗口默认只是隐藏，真正退出走右键菜单
        event.ignore()
        self.hide()
