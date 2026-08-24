"""百度智能云 AI 搜索（AppBuilder）客户端。

使用官方 MCP SSE 端点：
    http://appbuilder.baidu.com/v2/ai_search/mcp/sse?api_key=Bearer+<bce-v3/ALTAK-...>
工具名：AIsearch
"""
from __future__ import annotations

import asyncio
import logging
import re

logger = logging.getLogger("agent.search")

_SEARCH_PREFIXES = [
    "/搜", "/search", "/搜索",
    "搜索", "帮我搜", "帮我搜索", "百度一下", "查一下",
]


class SearchError(RuntimeError):
    pass


class BaiduSearchClient:
    def __init__(self, cfg):
        self.cfg = cfg
        s = cfg.search if hasattr(cfg, "search") else None
        if s is None:
            self.enabled = False
            return
        self.enabled = bool(s.get("enabled", False)) and bool(s.get("api_key", ""))
        self.api_key = str(s.get("api_key", ""))
        self.top_k = int(s.get("top_k", 4))
        self.timeout = float(s.get("timeout", 120))
        self.mcp_url = (
            "http://appbuilder.baidu.com/v2/ai_search/mcp/sse"
            f"?api_key=Bearer+{self.api_key}"
        )

    # ------------------------------------------------------------------
    def search(self, query: str, instruction: str | None = None,
               top_k: int | None = None) -> str:
        if not self.enabled:
            raise SearchError("联网搜索未启用，请检查 config.yaml 的 search 配置")
        query = (query or "").strip()
        if not query:
            raise SearchError("搜索关键词为空")

        async def _go():
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            async with sse_client(self.mcp_url) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    args = {
                        "query": query,
                        "stream": False,
                        "search_top_k": int(top_k or self.top_k),
                    }
                    if instruction:
                        args["instruction"] = instruction
                    result = await session.call_tool("AIsearch", args)
                    texts = []
                    for block in getattr(result, "content", []) or []:
                        text = getattr(block, "text", None)
                        if text:
                            texts.append(text)
                    text = "\n".join(texts).strip()
                    if getattr(result, "isError", False) or not text:
                        raise SearchError("百度 AI 搜索返回为空或失败")
                    return text

        try:
            return asyncio.run(_go())
        except SearchError:
            raise
        except Exception as e:
            raise SearchError(f"百度 AI 搜索调用失败：{e}") from e

    # ------------------------------------------------------------------
    @staticmethod
    def extract_query(text: str) -> str | None:
        """识别用户消息里的搜索意图，返回关键词；无意图返回 None。"""
        t = (text or "").strip()
        low = t.lower()
        for prefix in _SEARCH_PREFIXES:
            if low.startswith(prefix.lower()):
                rest = t[len(prefix):].strip(" ：:，,。")
                if rest:
                    return rest
        # 消息中间出现“帮我搜/搜索一下”等，取后面的关键词
        m = re.search(r"(?:帮我搜(?:索)?一下?|搜索一下|百度一下)\s*[:：]?\s*(.{2,80})", t)
        if m:
            return m.group(1).strip(" ：:，,。")
        return None
