"""内置 QPainter 桌面宠物（无 Live2D 模型时的兜底形象）。

支持表情（开心/难过/惊讶/害羞/生气/认真/困惑）、简单动作（点头/摇头/挥手/鞠躬/发呆）、
说话嘴部动画、眨眼，以及鼠标拖拽窗口。
"""
from __future__ import annotations

import math

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QTimer,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from PySide6.QtWidgets import QWidget

_EXPRESSIONS = {
    "开心": "happy",
    "happy": "happy",
    "难过": "sad",
    "sad": "sad",
    "惊讶": "surprised",
    "surprised": "surprised",
    "害羞": "shy",
    "shy": "shy",
    "生气": "angry",
    "angry": "angry",
    "认真": "serious",
    "serious": "serious",
    "困惑": "confused",
    "confused": "confused",
}


class FallbackPet(QWidget):
    clicked = Signal()
    drag_to = Signal(int, int)  # global x, y

    def __init__(self, parent=None, bg_color=(245, 245, 245)):
        super().__init__(parent)
        self._expression = "happy"
        self._speaking = False
        self._mouth_open = False
        self._blink = 0.0  # 0 睁眼, 1 闭眼
        self._bob = 0.0    # 上下点头偏移 -1..1
        self._shake = 0.0  # 左右摇头偏移 -1..1
        self._wave = 0.0   # 挥手 0..1
        self._bow = 0.0    # 鞠躬 0..1
        self._scale = 1.0  # 模型缩放
        self._bg = QColor(*bg_color)

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(160, 200)

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._do_blink)
        self._blink_timer.start(2800)

        self._mouth_timer = QTimer(self)
        self._mouth_timer.timeout.connect(self._toggle_mouth)
        self._mouth_timer.setInterval(110)

        self._anim = None
        self._drag_press_global: QPoint | None = None
        self._drag_press_win = QPoint()
        self._dragged = False

    # -------------------------------------------------- 对外接口 ----
    def set_expression(self, name: str):
        self._expression = _EXPRESSIONS.get(name, name or "happy")
        self.update()

    def set_motion(self, name: str):
        name = (name or "").lower()
        if name in ("点头", "nod"):
            self._animate_prop("_bob", 0, 1, 400)
        elif name in ("摇头", "shake"):
            self._animate_prop("_shake", 0, 1, 400)
        elif name in ("鞠躬", "bow"):
            self._animate_prop("_bow", 0, 1, 500)
        elif name in ("挥手", "wave"):
            self._animate_prop("_wave", 0, 1, 500)
        elif name in ("发呆", "idle"):
            self.set_expression("困惑")
        self.update()

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        if speaking:
            if not self._mouth_timer.isActive():
                self._mouth_timer.start()
        else:
            self._mouth_timer.stop()
            self._mouth_open = False
        self.update()

    def set_scale(self, scale: float):
        self._scale = max(0.5, min(2.0, float(scale or 1.0)))
        self.update()

    # -------------------------------------------------- 动画 ----
    def _animate_prop(self, attr: str, start: float, end: float, dur_ms: int):
        anim = QVariantAnimation(self)
        anim.setDuration(dur_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.valueChanged.connect(lambda v, a=attr: self._set_anim_value(a, float(v)))
        anim.finished.connect(lambda a=attr: self._set_anim_value(a, 0.0))
        self._anim = anim
        anim.start()

    def _set_anim_value(self, attr: str, v: float):
        # 用正弦做出来回动作
        wave = math.sin(v * math.pi)
        if attr == "_bob":
            self._bob = wave
        elif attr == "_shake":
            self._shake = wave
        elif attr == "_wave":
            self._wave = wave
        elif attr == "_bow":
            self._bow = wave
        self.update()

    def _do_blink(self):
        self._blink = 1.0
        QTimer.singleShot(130, lambda: setattr(self, "_blink", 0.0) or self.update())
        self.update()

    def _toggle_mouth(self):
        self._mouth_open = not self._mouth_open
        self.update()

    # -------------------------------------------------- 绘制 ----
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w, h = self.width(), self.height()
        cx = w / 2 + self._shake * 12
        cy = h * 0.58 + self._bob * 10 + self._bow * 14

        # 身体（一个圆乎乎的团子）
        body_w = min(w * 0.78, h * 0.42) * self._scale * (1.0 - self._bow * 0.08)
        body_h = min(w * 0.62, h * 0.36) * self._scale * (1.0 + self._bow * 0.15)
        body = QColor("#ffe4ec")
        p.setPen(QPen(QColor("#e8a0b4"), 3))
        p.setBrush(body)
        p.drawEllipse(QPoint(int(cx), int(cy)), int(body_w / 2), int(body_h / 2))

        # 呆毛
        p.setPen(QPen(QColor("#e8a0b4"), 3))
        p.drawArc(int(cx - 8), int(cy - body_h / 2 - 16), 16, 20, 0, 180 * 16)

        # 眼睛
        eye_y = cy - body_h * 0.22 + self._bob * 3
        eye_dx = body_w * 0.22
        eye_r = max(5.0, body_w * 0.055)
        blink = self._blink
        if self._expression == "happy":
            eye_h = eye_r * 1.6 * (1 - blink)
            p.setPen(QPen(QColor("#4a2c3a"), 2))
            p.setBrush(QColor("#4a2c3a"))
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r), int(eye_h))  # 笑眼
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r), int(eye_h))
        elif self._expression == "sad":
            p.setPen(QPen(QColor("#4a2c3a"), 2))
            p.setBrush(QColor("#4a2c3a"))
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r), int(eye_r * (1 - blink)))
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r), int(eye_r * (1 - blink)))
            p.drawArc(int(cx - eye_dx - 8), int(eye_y - 18), 16, 12, 200 * 16, 140 * 16)  # 耷拉眉
            p.drawArc(int(cx + eye_dx - 8), int(eye_y - 18), 16, 12, 200 * 16, 140 * 16)
        elif self._expression == "surprised":
            p.setPen(QPen(QColor("#4a2c3a"), 2))
            p.setBrush(Qt.white)
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r * 1.5), int(eye_r * 1.5 * (1 - blink)))
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r * 1.5), int(eye_r * 1.5 * (1 - blink)))
            p.setBrush(QColor("#4a2c3a"))
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r * 0.6), int(eye_r * 0.6))
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r * 0.6), int(eye_r * 0.6))
        elif self._expression == "angry":
            p.setPen(QPen(QColor("#4a2c3a"), 2))
            p.setBrush(QColor("#4a2c3a"))
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r), int(eye_r * (1 - blink)))
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r), int(eye_r * (1 - blink)))
            p.drawLine(int(cx - eye_dx - 8), int(eye_y - 14), int(cx - eye_dx + 8), int(eye_y - 8))  # 怒眉
            p.drawLine(int(cx + eye_dx + 8), int(eye_y - 14), int(cx + eye_dx - 8), int(eye_y - 8))
        elif self._expression == "serious":
            p.setPen(QPen(QColor("#4a2c3a"), 2))
            p.setBrush(QColor("#4a2c3a"))
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r * 0.9), int(eye_r * (1 - blink)))
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r * 0.9), int(eye_r * (1 - blink)))
            p.drawLine(int(cx - eye_dx - 8), int(eye_y - 10), int(cx - eye_dx + 8), int(eye_y - 10))
            p.drawLine(int(cx + eye_dx - 8), int(eye_y - 10), int(cx + eye_dx + 8), int(eye_y - 10))
        else:  # shy / confused / 默认
            p.setPen(QPen(QColor("#4a2c3a"), 2))
            p.setBrush(QColor("#4a2c3a"))
            p.drawEllipse(QPoint(int(cx - eye_dx), int(eye_y)), int(eye_r), int(eye_r * (1 - blink)))
            p.drawEllipse(QPoint(int(cx + eye_dx), int(eye_y)), int(eye_r), int(eye_r * (1 - blink)))

        # 害羞腮红
        if self._expression == "shy":
            p.setBrush(QColor(255, 150, 170, 120))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(int(cx - eye_dx * 1.6), int(eye_y + 18)), 10, 6)
            p.drawEllipse(QPoint(int(cx + eye_dx * 1.6), int(eye_y + 18)), 10, 6)

        # 嘴
        mouth_y = cy + body_h * 0.22
        p.setPen(QPen(QColor("#b3546e"), 2))
        p.setBrush(QColor("#b3546e"))
        if self._speaking and self._mouth_open:
            p.drawEllipse(QPoint(int(cx), int(mouth_y)), 7, 9)
        elif self._expression == "happy":
            p.drawArc(int(cx - 12), int(mouth_y - 10), 24, 18, 200 * 16, 140 * 16)
        elif self._expression == "sad":
            p.drawArc(int(cx - 10), int(mouth_y + 4), 20, 14, 20 * 16, 140 * 16)
        elif self._expression == "surprised":
            p.drawEllipse(QPoint(int(cx), int(mouth_y)), 6, 7)
        elif self._expression == "angry":
            p.drawArc(int(cx - 10), int(mouth_y + 2), 20, 12, 20 * 16, 140 * 16)
        elif self._expression == "confused":
            p.drawLine(int(cx - 6), int(mouth_y - 2), int(cx + 6), int(mouth_y - 2))
        else:
            p.drawArc(int(cx - 8), int(mouth_y - 6), 16, 12, 200 * 16, 140 * 16)

        # 挥手：画一只简单小手
        if self._wave > 0.05:
            p.setPen(QPen(QColor("#e8a0b4"), 3))
            p.setBrush(body)
            hand_x = cx + body_w * 0.55
            hand_y = cy - body_h * 0.15 - self._wave * 18
            p.drawEllipse(QPoint(int(hand_x), int(hand_y)), 12, 10)

        p.end()

    # -------------------------------------------------- 鼠标拖拽 ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_press_global = e.globalPosition().toPoint()
            self._drag_press_win = self.window().pos()
            self._dragged = False

    def mouseMoveEvent(self, e):
        if self._drag_press_global is not None:
            delta = e.globalPosition().toPoint() - self._drag_press_global
            if delta.manhattanLength() > 3:
                self._dragged = True
            self.drag_to.emit(self._drag_press_win.x() + delta.x(),
                              self._drag_press_win.y() + delta.y())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_press_global = None
            if not self._dragged:
                self.clicked.emit()
