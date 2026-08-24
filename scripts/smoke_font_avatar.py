# -*- coding: utf-8 -*-
"""分离字体与自定义头像槽测试。"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from agent.config import load_config
from main import AppController, setup_logging

cfg = load_config()
setup_logging(cfg.log_file)
app = QApplication(sys.argv)
ctrl = AppController(cfg, app, enable_pet=False, autostart_services=False)

ctrl.on_font_size(12)
ctrl.on_chat_font_size(18)
assert ctrl.chat._font_size == 12
assert ctrl.chat._chat_font_size == 18
assert ctrl.chat.font_combo.currentData() == 12
assert ctrl.chat.chat_font_combo.currentData() == 18

tmp = Path(tempfile.mkdtemp()) / "avatar.png"
img = QImage(80, 80, QImage.Format_ARGB32)
img.fill(0xFFFF00FF)
img.save(str(tmp))
ctrl.on_agent_avatar(str(tmp))
assert ctrl.chat._agent_avatar
assert Path(ctrl.chat._agent_avatar).exists()
ctrl.on_agent_avatar("")
assert ctrl.chat._agent_avatar == ""
ctrl.on_user_name("测试用户")
assert ctrl.chat._user_name == "测试用户"
ctrl.on_user_name("")
assert ctrl.chat._user_name == "Alorit"
print("font/avatar settings OK")
