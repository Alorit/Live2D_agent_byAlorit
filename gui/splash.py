"""Nori 启动加载界面（无边框、半透明、霓虹风格）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class SplashWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                         Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(520, 280)

        # 居中
        screen = self.screen() or QApplication_primary_screen()
        geo = screen.availableGeometry()
        self.move(geo.center().x() - self.width() // 2,
                  geo.center().y() - self.height() // 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 36)
        layout.setSpacing(10)

        self.cat_label = QLabel("🐰", self)
        self.cat_label.setAlignment(Qt.AlignCenter)
        self.cat_label.setStyleSheet("font-size: 40px; background: transparent;")

        self.title_label = QLabel("加载中...", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "font-size: 30px; font-weight: 900; letter-spacing: 8px;"
            "color: #a7f3d0; background: transparent;")

        self.subtitle_label = QLabel("NEURAL COMPANION // 正在初始化", self)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet(
            "font-size: 12px; color: #7dd3fc; background: transparent;"
            "font-family: Consolas, 'Courier New', monospace;")

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(167,243,208,0.35);
                border-radius: 8px;
                height: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34d399, stop:0.5 #67e8f9, stop:1 #a78bfa);
                border-radius: 7px;
            }
        """)

        self.status_label = QLabel("正在读取配置", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 12px; color: #9fb4d8; background: transparent;")

        layout.addStretch(1)
        layout.addWidget(self.cat_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(8)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    def set_progress(self, value: int, text: str):
        value = max(0, min(100, int(value)))
        try:
            self.progress.setValue(value)
            self.status_label.setText(text)
        except RuntimeError:
            pass

    def finish(self):
        try:
            self.close()
            self.deleteLater()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 半透明深色玻璃底
        painter.setBrush(QColor(10, 15, 30, 235))
        painter.setPen(QPen(QColor(103, 232, 249, 90), 1))
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 22, 22)
        # 顶部霓虹线
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(52, 211, 153, 70))
        painter.drawRoundedRect(2, 2, self.width() - 4, 3, 1, 1)
        super().paintEvent(event)


def QApplication_primary_screen():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        return app.primaryScreen()
    from PySide6.QtGui import QGuiApplication
    return QGuiApplication.primaryScreen()
