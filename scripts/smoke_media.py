# -*- coding: utf-8 -*-
"""图片/表情包功能冒烟测试（offscreen）：不发 LLM，只验证 UI 与持久化。"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from agent.config import load_config
from agent.memory import MemoryStore
from gui.chat_window import ChatWindow
from utils.stickers import ensure_default_stickers, list_stickers

# 1. 表情包库
cfg = load_config()
stickers = list_stickers(cfg.root)
assert stickers, "应有内置表情包"
assert Path(stickers[0]["path"]).is_file()

# 2. 消息图片路径持久化
tmp_db = Path(tempfile.mkdtemp()) / "media_test.db"
mem = MemoryStore(str(tmp_db))
conv = mem.ensure_main_conversation("nori")
msg_id = mem.record_message("user", "看看这个", persona="nori", conversation_id=conv,
                            image_paths=[stickers[0]["path"]])
rows = mem.get_recent_messages(10, persona="nori", conversation_id=conv)
found = [r for r in rows if r["role"] == "user"]
assert found and found[-1]["image_paths"] == [stickers[0]["path"]], found
mem.close()

# 3. GUI 图片气泡与历史回放
app = QApplication(sys.argv)
w = ChatWindow(cfg, quit_on_close=True, live2d_mode=False)
w.show()

received = []
w.media_send_requested.connect(
    lambda paths, caption: received.append((paths, caption)))
w.input.setText("这个表情")
w._emit_media([stickers[0]["path"]], "这个表情")
assert received and received[-1][0] == [stickers[0]["path"]], received
assert received[-1][1] == "这个表情", received
assert w.input.text() == ""
assert w.bubble_layout.count() - 1 == 1, "发出图片后应有 1 个图片气泡"

w.append_assistant("哈哈，好可爱！")
assert w.bubble_layout.count() - 1 == 2, "应有图片气泡 + 回复气泡"

w.set_chat_history([
    {"role": "user", "content": "看看这个",
     "image_paths": [stickers[1]["path"]]},
    {"role": "assistant", "content": "收到！"},
])
assert w.bubble_layout.count() - 1 == 2, "历史回放应有图片气泡 + 回复气泡"

# 图片按钮 / 表情按钮存在且可禁用
assert w.image_btn.isEnabled()
assert w.sticker_btn.isEnabled()
w.set_input_enabled(False)
assert not w.image_btn.isEnabled() and not w.sticker_btn.isEnabled()

print("stickers:", len(stickers))
print("media message id:", msg_id)
print("media smoke OK")
QTimer.singleShot(300, app.quit)
sys.exit(app.exec())
