# -*- coding: utf-8 -*-
"""字体大小设置槽测试。"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from agent.config import load_config
from main import AppController, setup_logging

cfg = load_config()
setup_logging(cfg.log_file)
app = QApplication(sys.argv)
ctrl = AppController(cfg, app, enable_pet=False, autostart_services=False)
ctrl.on_font_size(16)
assert ctrl.chat._font_size == 16
assert ctrl.chat.font_combo.currentData() == 16
assert ctrl.cfg.gui.get("font_size") == 16
print("font size OK")
