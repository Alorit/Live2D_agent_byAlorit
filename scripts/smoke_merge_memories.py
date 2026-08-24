# -*- coding: utf-8 -*-
"""相似记忆合并与多行显示测试。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.memory import MemoryStore

db = Path(tempfile.mkdtemp()) / "mem.db"
m = MemoryStore(str(db), {"backend": "bm25", "max_memories": 100})
m.add_memory("用户喜欢草莓蛋糕", mem_type="semantic", importance=0.6)
m.add_memory("用户很喜欢草莓蛋糕", mem_type="semantic", importance=0.8)
m.add_memory("用户讨厌香菜", mem_type="semantic", importance=0.7)
assert len(m.list_memories()) == 3
merged = m.merge_similar_memories(0.6)
print("merged:", merged)
rows = m.list_memories()
print("rows after:", [(r["id"], r["content"]) for r in rows])
assert len(rows) == 2
assert merged == 1
m.close()
print("merge similar OK")
