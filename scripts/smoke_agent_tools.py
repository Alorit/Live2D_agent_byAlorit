# -*- coding: utf-8 -*-
"""AgentCore function-calling / MCP 工具循环离线测试。"""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.config import Config
from agent.core import AgentCore
from agent.memory import MemoryStore


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class TC:
    def __init__(self, name, args, id="call_1"):
        self.id = id
        self.function = type("F", (), {"name": name, "arguments": args})()


class FakeBrain:
    def __init__(self):
        self.calls = 0

    def chat_message(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return FakeMessage(tool_calls=[TC("fake__echo", '{"x": 1}')])
        return FakeMessage(content="工具说 result-ok")


class FakeMCP:
    async def build_tool_schemas(self):
        return [{"type": "function", "function": {
            "name": "fake__echo", "description": "echo",
            "parameters": {"type": "object", "properties": {"x": {"type": "number"}}}}}]

    def execute_tool(self, name, args):
        async def _go():
            return f"result-ok {args.get('x')}"
        return asyncio.run(_go())

    def skill_instructions(self):
        return "技能：保持简短"


root = Path(tempfile.mkdtemp())
cfg = Config({"llm": {"working_memory_size": 10, "context_compression": {"mode": "off"}},
              "memory": {"top_k": 8, "consolidate_interval": 0},
              "persona": {"persona_dir": str(root / "persona"), "active_persona": "test"}},
             root=root)
m = MemoryStore(str(root / "mem.db"), cfg.memory)
brain = FakeBrain()
core = AgentCore(cfg, m, brain, mcp_manager=FakeMCP())
core.current_conversation_id = m.ensure_main_conversation("test")
reply = core.handle_user_text("测试工具")
print("reply:", reply.text, "commands:", reply.commands)
assert reply.text == "工具说 result-ok"
assert brain.calls == 2
print("agent tool loop OK")
m.close()
