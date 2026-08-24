# -*- coding: utf-8 -*-
"""记忆面板槽函数测试：添加后出现在表格，删除后消失。"""
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

marker = "__smoke_memory_ui__"
ctrl.on_memory_add(marker, "episodic", 0.5)
rows = ctrl.memory.list_memories(query=marker)
assert rows, "memory should be added"
mem_id = rows[0]["id"]
table_texts = []
for r in range(ctrl.chat.memory_table.rowCount()):
    item = ctrl.chat.memory_table.item(r, 2)
    if item:
        table_texts.append(item.text())
assert any(marker in t for t in table_texts), table_texts
print("added to table OK, id", mem_id)

ctrl.on_memory_update(mem_id, marker + "_updated", "semantic", 0.9)
row = ctrl.memory.get_memory(mem_id)
assert row["content"] == marker + "_updated" and row["type"] == "semantic"
print("update via slot OK")

ctrl.on_memory_delete(mem_id)
assert ctrl.memory.get_memory(mem_id) is None
print("delete via slot OK")
