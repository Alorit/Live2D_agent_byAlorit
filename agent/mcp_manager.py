"""MCP 服务器与 Skill 管理。

参考成熟的 Agent 工具方案：
- MCP：Model Context Protocol，把外部工具（stdio / SSE / Streamable HTTP）以
  OpenAI function-calling schema 暴露给 LLM，由 AgentCore 执行 tool_calls 循环；
- Skill：参考 Claude Agent Skills 的“指令包”思路，每个 skill 是一个目录，
  内含 SKILL.md（纯文本指令），启用后其指令注入到对话上下文。
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent.mcp")

DEFAULT_CONFIG = {"servers": [], "skills": []}


class MCPManager:
    def __init__(self, root: Path):
        self.root = root
        self.config_path = root / "data" / "mcp_config.json"
        self.skills_dir = root / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            data.setdefault("servers", [])
            data.setdefault("skills", [])
            return data
        except Exception:
            return dict(DEFAULT_CONFIG)

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------ servers ----
    def list_servers(self) -> list[dict]:
        return self.config.get("servers", [])

    def get_server(self, name: str) -> dict | None:
        return next((s for s in self.list_servers() if s.get("name") == name), None)

    def add_server(self, name: str, transport: str, url: str = "",
                   command: str = "", args: str = "") -> bool:
        name = (name or "").strip()
        if not name or self.get_server(name):
            return False
        server = {
            "name": name,
            "enabled": True,
            "transport": transport,
            "url": (url or "").strip(),
            "command": (command or "").strip(),
            "args": [a for a in (args or "").split() if a],
            "env": {},
        }
        self.config["servers"].append(server)
        self.save()
        return True

    def remove_server(self, name: str) -> bool:
        before = len(self.list_servers())
        self.config["servers"] = [s for s in self.list_servers() if s.get("name") != name]
        self.save()
        return len(self.config["servers"]) < before

    def set_server_enabled(self, name: str, enabled: bool) -> bool:
        for s in self.list_servers():
            if s.get("name") == name:
                s["enabled"] = bool(enabled)
                self.save()
                return True
        return False

    def import_server_config(self, path: str | Path) -> int:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        incoming = data.get("servers") or data.get("mcpServers", [])
        existing = {s.get("name") for s in self.list_servers()}
        added = 0
        for s in incoming:
            if not s.get("name") or s["name"] in existing:
                continue
            self.config["servers"].append(s)
            existing.add(s["name"])
            added += 1
        self.save()
        return added

    async def _tools_for_server(self, server: dict) -> list[dict]:
        try:
            if server.get("transport", "stdio") in ("streamable_http", "http"):
                from mcp.client.streamable_http import streamable_http_client
                from mcp import ClientSession
                async with streamable_http_client(server.get("url", "")) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        return await self._tools_from_session(session, server)
            if server.get("transport", "stdio") == "sse":
                from mcp import ClientSession
                from mcp.client.sse import sse_client
                async with sse_client(server.get("url", "")) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        return await self._tools_from_session(session, server)
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            params = StdioServerParameters(
                command=server.get("command", ""),
                args=server.get("args", []),
                env={**server.get("env", {})} if server.get("env") else None,
            )
            async with stdio_client(params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return await self._tools_from_session(session, server)
        except Exception as e:
            logger.warning("MCP 服务器 %s 连接失败：%s", server.get("name"), e)
            return []

    @staticmethod
    async def _tools_from_session(session, server: dict) -> list[dict]:
        tools = await session.list_tools()
        out = []
        for tool in tools.tools:
            schema = tool.input_schema or {"type": "object", "properties": {}}
            out.append({
                "server": server.get("name", ""),
                "name": tool.name,
                "description": (tool.description or tool.name)[:500],
                "inputSchema": schema,
            })
        return out

    async def build_tool_schemas(self) -> list[dict]:
        tasks = [self._tools_for_server(s) for s in self.list_servers() if s.get("enabled")]
        results = await asyncio.gather(*tasks) if tasks else []
        flat = [t for group in results for t in group]
        return [
            {"type": "function", "function": {
                "name": f"{t['server']}__{t['name']}",
                "description": f"[{t['server']}] {t['description']}",
                "parameters": t["inputSchema"],
            }} for t in flat
        ]

    async def execute_tool(self, qualified_name: str, arguments: dict) -> str:
        server_name, tool_name = qualified_name.split("__", 1)
        server = self.get_server(server_name)
        if not server or not server.get("enabled"):
            return f"MCP 服务器 {server_name} 不存在或未启用"
        try:
            if server.get("transport", "stdio") in ("streamable_http", "http"):
                from mcp.client.streamable_http import streamable_http_client
                from mcp import ClientSession
                async with streamable_http_client(server.get("url", "")) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        return await self._call_tool_on_session(session, tool_name, arguments)
            if server.get("transport", "stdio") == "sse":
                from mcp import ClientSession
                from mcp.client.sse import sse_client
                async with sse_client(server.get("url", "")) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        return await self._call_tool_on_session(session, tool_name, arguments)
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            params = StdioServerParameters(
                command=server.get("command", ""),
                args=server.get("args", []),
                env={**server.get("env", {})} if server.get("env") else None,
            )
            async with stdio_client(params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return await self._call_tool_on_session(session, tool_name, arguments)
        except Exception as e:
            return f"工具执行失败：{e}"

    @staticmethod
    async def _call_tool_on_session(session, tool_name: str, arguments: dict) -> str:
        result = await session.call_tool(tool_name, arguments or {})
        parts = []
        for block in getattr(result, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip() or "（工具执行完成）"

    # ------------------------------------------------------------ skills ----
    def list_skills(self) -> list[dict]:
        known = {s.get("name"): s for s in self.config.get("skills", [])}
        out = []
        for d in sorted(self.skills_dir.iterdir()):
            md = d / "SKILL.md" if d.is_dir() else d
            if md.is_file():
                name = d.name if d.is_dir() else md.stem
                cfg = known.get(name, {"name": name, "enabled": True})
                out.append({"name": name, "enabled": bool(cfg.get("enabled", True)),
                            "path": str(md)})
                known.pop(name, None)
        # config 里存在但目录被删除的条目清理掉
        self.config["skills"] = [s for s in self.config.get("skills", []) if s.get("name") in {x["name"] for x in out}]
        self.save()
        return out

    def import_skill(self, path: str | Path) -> bool:
        src = Path(path)
        if src.is_dir():
            md = src / "SKILL.md"
            if not md.exists():
                md = next(src.glob("*.md"), None)
            if not md:
                return False
            dest = self.skills_dir / (src.name or "skill")
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md, dest / "SKILL.md")
            name = dest.name
        else:
            name = src.stem or "skill"
            dest = self.skills_dir / name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / "SKILL.md")
        self.config.setdefault("skills", [])
        if not any(s.get("name") == name for s in self.config["skills"]):
            self.config["skills"].append({"name": name, "enabled": True})
        self.save()
        return True

    def remove_skill(self, name: str) -> bool:
        self.config["skills"] = [s for s in self.config.get("skills", []) if s.get("name") != name]
        path = self.skills_dir / name
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        self.save()
        return True

    def set_skill_enabled(self, name: str, enabled: bool) -> bool:
        for s in self.config.setdefault("skills", []):
            if s.get("name") == name:
                s["enabled"] = bool(enabled)
                self.save()
                return True
        self.config["skills"].append({"name": name, "enabled": bool(enabled)})
        self.save()
        return True

    def skill_instructions(self) -> str:
        parts = []
        for s in self.list_skills():
            if not s.get("enabled"):
                continue
            try:
                text = Path(s["path"]).read_text(encoding="utf-8").strip()
                parts.append(f"## Skill: {s['name']}\n{text[:4000]}")
            except Exception:
                pass
        return "\n\n".join(parts)
