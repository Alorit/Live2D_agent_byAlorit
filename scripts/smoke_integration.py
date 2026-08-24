# -*- coding: utf-8 -*-
"""AppController + 后台服务自动启动集成测试（offscreen）。"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["NORI_HEART_SKIP_LIVE2D"] = "1"
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
ctrl = AppController(cfg, app, enable_pet=False, autostart_services=True)
ctrl.show()
time.sleep(5)
st = ctrl.services.status()
print("service status:", st)
assert st["heart"], "heart should auto-start"
print("gsv proc:", ctrl.services.gsv_proc.pid if ctrl.services.gsv_proc else None)

QTimer.singleShot(500, app.quit)
app.exec()
print("stopping services...")
print("stop heart:", ctrl.services.stop_heart())
print("stop gsv:", ctrl.services.stop_gpt_sovits())
print("final status:", ctrl.services.status())
