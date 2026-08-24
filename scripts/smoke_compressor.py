# -*- coding: utf-8 -*-
"""上下文压缩器离线测试（fake brain）。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.compressor import ContextCompressor
from agent.config import Config
from agent.memory import MemoryStore


class FakeMessage:
    content = "压缩摘要内容"


class FakeChoice:
    message = FakeMessage


class FakeResp:
    choices = [FakeChoice]


class FakeCompletions:
    @staticmethod
    def create(*a, **k):
        return FakeResp


class FakeClient:
    chat = type("Chat", (), {"completions": FakeCompletions})


class FakeBrain:
    def _ensure_client(self):
        return FakeClient


db = Path(tempfile.mkdtemp()) / "mem.db"
m = MemoryStore(str(db), {"backend": "bm25"})
cfg = Config({"llm": {"context_compression": {"mode": "auto", "window_size": 5, "max_chars": 200}}},
             root=Path(tempfile.mkdtemp()))
c = ContextCompressor(FakeBrain(), m, cfg)
history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"}
           for i in range(10)]
out = c.history_for_llm(history, "Nori")
print("out len", len(out), "first role", out[0]["role"])
assert len(out) == 6  # 1 压缩摘要 + 5 原文
assert out[0]["content"].startswith("【更早对话的压缩记忆】")
assert out[1]["content"] == "msg5"
print("compressor OK")
m.close()
