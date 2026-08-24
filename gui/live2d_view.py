"""Live2D 渲染视图：QWebEngineView 加载本地 HTML + pixi-live2d-display。

这是本地桌面窗口内的嵌入渲染，不打开浏览器；模型文件和 JS 库都在本地。
如果 QWebEngine 或模型不可用，请在 pet_window 里退回 FallbackPet。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Qt, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger("gui.live2d")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = PROJECT_ROOT / "live2d" / "index.html"
JS_DIR = PROJECT_ROOT / "live2d" / "js"


def ensure_qwebchannel_js() -> str | None:
    """找到 Qt 自带的 qwebchannel.js 并复制到 live2d/js/，返回最终路径。"""
    target = JS_DIR / "qwebchannel.js"
    if target.exists():
        return str(target)

    candidates = []
    try:
        import PySide6
        pkg_root = Path(PySide6.__file__).resolve().parent
        candidates += [
            pkg_root / "Qt" / "resources" / "qwebchannel.js",
            pkg_root / "resources" / "qwebchannel.js",
            pkg_root / "qwebchannel.js",
        ]
    except Exception:
        pass

    # 在 site-packages 里全局找一下（带大小限制）
    try:
        import site
        for sp in site.getsitepackages():
            p = Path(sp)
            for cand in p.glob("**/qwebchannel.js"):
                candidates.append(cand)
                if len(candidates) > 40:
                    break
    except Exception:
        pass

    for c in candidates:
        if c.exists():
            try:
                JS_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(c, target)
                return str(target)
            except Exception as e:
                logger.debug("复制 qwebchannel.js 失败：%s", e)
    return None


class Live2DBridge(QObject):
    """暴露给 JS 的桥接对象。"""
    ready = Signal()
    modelLoaded = Signal()
    modelError = Signal(str)
    dragStarted = Signal(int, int)
    dragTo = Signal(int, int)
    petClicked = Signal()

    @Slot()
    def onReady(self):
        self.ready.emit()

    @Slot()
    def onModelLoaded(self):
        self.modelLoaded.emit()

    @Slot(str)
    def onModelError(self, msg: str):
        self.modelError.emit(msg)

    @Slot(int, int)
    def onDragStart(self, x: int, y: int):
        self.dragStarted.emit(x, y)

    @Slot(int, int)
    def onDragMove(self, x: int, y: int):
        self.dragTo.emit(x, y)

    @Slot()
    def onPetClick(self):
        self.petClicked.emit()


class Live2DView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bridge = Live2DBridge()
        self.channel = QWebChannel(self.page())
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)

        # 透明背景
        self.page().setBackgroundColor(Qt.transparent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        ensure_qwebchannel_js()

        if HTML_PATH.exists():
            self.load(QUrl.fromLocalFile(str(HTML_PATH)))
        else:
            logger.error("找不到 live2d/index.html")

    # -------------------------------------------------- 对外 ----
    def load_model(self, model_path: str):
        url = QUrl.fromLocalFile(str(model_path)).toString()
        self._call_js("window.neuroLoadModel", url)

    def set_expression(self, name: str):
        self._call_js("window.neuroSetExpression", name or "")

    def set_motion(self, name: str):
        self._call_js("window.neuroSetMotion", name or "")

    def set_speaking(self, speaking: bool):
        self._call_js("window.neuroSetSpeaking", bool(speaking))

    def set_scale(self, scale: float):
        try:
            self._call_js("window.neuroSetScale", float(scale))
        except Exception:
            pass

    def _call_js(self, fn: str, *args):
        if not hasattr(self, "page"):
            return
        encoded = ",".join(json.dumps(a, ensure_ascii=False) for a in args)
        self.page().runJavaScript(f"{fn}({encoded})")
