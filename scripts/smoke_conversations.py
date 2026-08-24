# -*- coding: utf-8 -*-
"""会话（主对话 + 新对话）隔离测试。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.memory import MemoryStore

db = Path(tempfile.mkdtemp()) / "mem.db"
m = MemoryStore(str(db), {"backend": "bm25"})
main_a = m.ensure_main_conversation("A")
main_b = m.ensure_main_conversation("B")
assert main_a != main_b
m.record_message("user", "A 你好", persona="A")
m.record_message("assistant", "A 回复", persona="A")
assert len(m.get_recent_messages(10, persona="A")) == 2
assert len(m.get_recent_messages(10, persona="B")) == 0

conv = m.create_conversation("A", "测试会话")
m.record_message("user", "新会话内容", persona="A", conversation_id=conv)
assert len(m.get_recent_messages(10, conversation_id=conv)) == 1
rows = m.list_conversations("A")
assert len(rows) == 2
assert any(r["is_main"] for r in rows)
assert m.rename_conversation(conv, "改名")
assert m.get_conversation(conv)["title"] == "改名"
assert m.delete_conversation(conv)
assert m.get_conversation(conv) is None
print("conversation OK")
m.close()
