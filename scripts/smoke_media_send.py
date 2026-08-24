# -*- coding: utf-8 -*-
"""图片/表情包发送链路冒烟测试（offscreen，用 FakeCore 避免真实 LLM）。"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["NORI_HEART_SKIP_LIVE2D"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from agent.brain import AgentReply
from agent.config import load_config
from main import AppController
from utils.stickers import list_stickers


class FakeCore:
    def __init__(self, memory, conv_id):
        self.memory = memory
        self.conv_id = conv_id

    def handle_user_text(self, text, image_paths=None):
        assert image_paths, "应收到图片路径"
        self.memory.record_message(
            "user", text or "", persona="Nori System Prompt V3.5",
            conversation_id=self.conv_id, image_paths=image_paths)
        self.memory.record_message(
            "assistant", "我看到啦！", persona="Nori System Prompt V3.5",
            conversation_id=self.conv_id)
        return AgentReply(text="我看到啦！", commands=[])


cfg = load_config()
cfg.db_path = str(Path(tempfile.mkdtemp()) / "media_e2e.db")
app = QApplication(sys.argv)
ctrl = AppController(cfg, app, enable_pet=False, autostart_services=False)
conv_id = ctrl.memory.ensure_main_conversation("Nori System Prompt V3.5")
ctrl.core = FakeCore(ctrl.memory, conv_id)
ctrl.current_conversation_id = conv_id
ctrl.chat.clear_chat()

sticker = list_stickers(cfg.root)[0]["path"]
ctrl.chat.input.setText("看看这个")
ctrl.chat._emit_media([sticker], "看看这个")
assert not ctrl.chat.input.isEnabled(), "思考期间应锁定输入"
assert ctrl.chat.bubble_layout.count() - 1 == 1, "应立即显示图片气泡"

result = {}


def check():
    result["bubbles"] = ctrl.chat.bubble_layout.count() - 1
    result["enabled"] = ctrl.chat.input.isEnabled()
    rows = ctrl.memory.get_recent_messages(
        5, persona="Nori System Prompt V3.5", conversation_id=conv_id)
    result["image_paths"] = [r["image_paths"] for r in rows if r["role"] == "user"][-1]
    ctrl.memory.close()
    app.quit()


QTimer.singleShot(2000, check)
app.exec()

assert result["bubbles"] >= 2, result
assert result["enabled"] is True, result
assert result["image_paths"] == [sticker], result
print("media send pipeline OK", result)
sys.exit(0)
