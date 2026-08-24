"""Nori 视觉 MCP 服务（独立版，不依赖主项目配置）。

这是一个可独立分发/启动的 MCP 服务器，通过设置界面的“导入 MCP JSON”接入主程序。
API Key 不放在主项目 config.yaml 中，避免分发泄露。

配置优先级：
1. 环境变量：VOLC_ARK_API_KEY / VISION_BASE_URL / VISION_MODEL / VISION_MCP_PORT
2. 本目录 config.json（不会随主项目分发；请复制 config.example.json 后填写）

默认监听 http://127.0.0.1:47833，MCP 路径 /mcp。
工具：
  - analyze_image(source, question, max_tokens)
  - describe_image(source)

启动方式：
  python vision_mcp/server.py
  python vision_mcp/server.py --port 47833
  python vision_mcp/server.py --stdio
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

HERE = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed-2-1-pro-260628"
DEFAULT_PORT = 47833
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB

logger = logging.getLogger("vision_mcp")


class VisionError(RuntimeError):
    pass


def load_settings() -> dict[str, Any]:
    """读取视觉服务配置，优先环境变量，其次本目录 config.json。"""
    data: dict[str, Any] = {}
    cfg_path = HERE / "config.json"
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning("读取 vision_mcp/config.json 失败：%s", e)

    def _pick(env_name: str, key: str, default: Any = "") -> Any:
        env_val = os.environ.get(env_name, "").strip()
        if env_val:
            return env_val
        val = data.get(key)
        return default if val is None else val

    return {
        "api_key": _pick("VOLC_ARK_API_KEY", "api_key", ""),
        "base_url": _pick("VISION_BASE_URL", "base_url", DEFAULT_BASE_URL),
        "model": _pick("VISION_MODEL", "model", DEFAULT_MODEL),
        "port": int(_pick("VISION_MCP_PORT", "port", DEFAULT_PORT) or DEFAULT_PORT),
        "timeout": float(data.get("timeout", 120)),
    }


class VisionAnalyzer:
    def __init__(self, settings: dict[str, Any]):
        self.api_key = str(settings.get("api_key", "") or "").strip()
        self.base_url = str(settings.get("base_url", DEFAULT_BASE_URL))
        self.model = str(settings.get("model", DEFAULT_MODEL))
        self.timeout = float(settings.get("timeout", 120))
        self.enabled = bool(self.api_key)
        if self.enabled:
            self.client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        else:
            self.client = None

    # ------------------------------------------------------------------
    def _load_source(self, source: str) -> tuple[str, bytes]:
        """返回 (mime, bytes)。支持本地路径、http(s) URL、data URL。"""
        source = (source or "").strip()
        if source.startswith("data:"):
            if ";base64," not in source:
                raise VisionError("data URL 只支持 base64 编码")
            header, b64 = source.split(";base64,", 1)
            mime = header.split(":", 1)[1] if ":" in header else "image/png"
            return mime, base64.b64decode(b64)
        if source.startswith(("http://", "https://")):
            import requests
            r = requests.get(source, timeout=30)
            r.raise_for_status()
            mime = r.headers.get("Content-Type", "image/png").split(";")[0]
            return mime, r.content
        p = Path(source)
        if not p.exists():
            raise VisionError(f"图片不存在：{source}")
        ext = p.suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}
        return mime_map.get(ext, "image/png"), p.read_bytes()

    def analyze(self, source: str, question: str = "详细描述这张图片的内容",
                max_tokens: int = 800) -> str:
        if not self.enabled or self.client is None:
            raise VisionError(
                "视觉 MCP 未配置 API Key：请设置环境变量 VOLC_ARK_API_KEY，"
                "或填写 vision_mcp/config.json（可复制 config.example.json）")
        mime, data = self._load_source(source)
        if len(data) > MAX_IMAGE_BYTES:
            raise VisionError(f"图片过大（{len(data) / 1024 / 1024:.1f}MB），请压缩到 10MB 以内")
        b64 = base64.b64encode(data).decode()
        messages: list[dict[str, Any]] = [{
            "role": "user",
            "content": [
                {"type": "text", "text": question or "详细描述这张图片的内容"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=int(max_tokens),
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise VisionError("视觉模型返回了空内容")
        return text

    # ------------------------------------------------------------------
    @staticmethod
    def extract_sources(text: str) -> list[str]:
        """从文本提取图片路径或 URL（供主程序兼容使用）。"""
        out: list[str] = []
        url_re = re.compile(r"https?://[^\s\"'<>（）()【】\[\]]+", re.I)
        img_re = re.compile(r"\.(png|jpe?g|webp|gif|bmp)$", re.I)
        for m in url_re.finditer(text):
            url = m.group(0).rstrip(".,;:!?")
            if img_re.search(url.split("?")[0]):
                out.append(url)
        for m in re.finditer(r"[\"']([^\"']+\.(?:png|jpe?g|webp|gif|bmp))[\"']",
                              text, re.I):
            cand = m.group(1).strip()
            if not cand.startswith(("http://", "https://", "data:")) and Path(cand).exists():
                out.append(cand)
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq


settings = load_settings()
vision = VisionAnalyzer(settings)

from mcp.server.mcpserver import MCPServer  # noqa: E402

server = MCPServer(
    name="nori-vision",
    title="Nori Vision (Seed 2.1 Pro)",
    description="使用火山方舟 doubao-seed-2-1-pro-260628 视觉模型分析图片。",
    version="1.0.0",
)


@server.tool(
    name="analyze_image",
    description="分析一张图片。source 可以是本地文件路径、http(s) 图片 URL 或 data URL；"
                "question 是需要回答的问题，默认详细描述图片内容。",
)
def analyze_image(source: str, question: str = "详细描述这张图片的内容",
                  max_tokens: int = 800) -> str:
    return vision.analyze(source, question=question, max_tokens=max_tokens)


@server.tool(
    name="describe_image",
    description="用一段话概括图片内容（analyze_image 的简化版）。",
)
def describe_image(source: str) -> str:
    return vision.analyze(source, question="详细描述这张图片的内容")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nori Vision MCP")
    parser.add_argument("--stdio", action="store_true",
                        help="stdio 模式（Claude Code / Cursor 等 MCP 客户端）")
    parser.add_argument("--port", type=int, default=None,
                        help="Streamable HTTP 端口（默认 47833）")
    args = parser.parse_args()

    if not vision.enabled:
        logger.warning("视觉 MCP 未配置 API Key；工具调用会返回错误。"
                       "请设置 VOLC_ARK_API_KEY 或填写 vision_mcp/config.json。")

    if args.stdio:
        asyncio.run(server.run_stdio_async())
    else:
        port = args.port or settings["port"]
        asyncio.run(server.run_streamable_http_async(
            host="127.0.0.1", port=port, streamable_http_path="/mcp"))
