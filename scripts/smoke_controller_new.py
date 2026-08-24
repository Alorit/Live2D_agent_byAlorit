# -*- coding: utf-8 -*-
"""AppController 冒烟测试（--no-pet --no-services，offscreen）。"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from agent.config import load_config
from main import AppController, setup_logging

cfg = load_config()
setup_logging(cfg.log_file)
app = QApplication(sys.argv)
ctrl = AppController(cfg, app, enable_pet=False, autostart_services=False)
ctrl.show()

print("tts:", ctrl.tts_name)
print("persona editor chars:", len(ctrl.chat.persona_edit.toPlainText()))
print("memory table rows:", ctrl.chat.memory_table.rowCount())
print("service status:", ctrl.services.status())

QTimer.singleShot(1200, app.quit)
code = app.exec()
print("app exited", code)
sys.exit(code)
