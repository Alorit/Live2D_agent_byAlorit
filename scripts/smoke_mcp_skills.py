# -*- coding: utf-8 -*-
"""MCP / Skill 配置管理测试。"""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.mcp_manager import MCPManager

root = Path(tempfile.mkdtemp())
m = MCPManager(root)
assert m.add_server("test", "streamable_http", url="http://127.0.0.1:9999/mcp")
assert m.list_servers()[0]["enabled"] is True
assert m.set_server_enabled("test", False)
assert m.list_servers()[0]["enabled"] is False
assert m.remove_server("test")

# import server config
cfg = root / "mcp.json"
cfg.write_text('{"servers":[{"name":"a","transport":"sse","url":"http://x"},{"name":"a","transport":"sse","url":"http://y"}]}')
assert m.import_server_config(cfg) == 1

# skill
skill = root / "skilldir"
skill.mkdir()
(skill / "SKILL.md").write_text("# 测试技能\n这是技能指令", encoding="utf-8")
assert m.import_skill(skill)
skills = m.list_skills()
assert skills and skills[0]["name"] == "skilldir"
assert "测试技能" in m.skill_instructions()
assert m.set_skill_enabled("skilldir", False)
assert m.skill_instructions() == ""
print("mcp/skills config OK")
