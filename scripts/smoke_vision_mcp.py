# -*- coding: utf-8 -*-
"""视觉 MCP 独立化冒烟测试：验证可被设置界面的 MCP 导入机制正确接入。"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import load_config
from agent.core import AgentCore
from agent.mcp_manager import MCPManager
from agent.memory import MemoryStore
from agent.brain import Brain

# 1. 独立 MCP JSON 必须存在
import_json = ROOT / "vision_mcp" / "nori-vision.mcp.json"
assert import_json.exists(), "缺少 vision_mcp/nori-vision.mcp.json"

# 2. 用临时 MCPManager 模拟“设置界面导入 MCP JSON”
tmp = Path(tempfile.mkdtemp())
mgr = MCPManager(tmp)
added = mgr.import_server_config(import_json)
assert added == 1, "应成功导入 1 个服务器"
srv = mgr.get_server("nori-vision")
assert srv and srv.get("enabled") is True
assert srv.get("transport") == "streamable_http"
assert srv.get("url") == "http://127.0.0.1:47833/mcp"

# 3. AgentCore 应能识别已导入的视觉 MCP 服务器
cfg = load_config()
mem = MemoryStore(cfg.db_path, cfg.memory)
brain = Brain(cfg)
core = AgentCore(cfg, mem, brain, mcp_manager=mgr)
assert core._vision_mcp_server_name() == "nori-vision"

# 4. 主项目 config.yaml 不再包含任何真实 API Key
cfg_text = (ROOT / "config.yaml").read_text(encoding="utf-8")
assert "ark-" not in cfg_text, "config.yaml 不应再出现火山方舟 API Key"
assert "sk-d690" not in cfg_text, "config.yaml 不应再出现 DeepSeek API Key"
assert "bce-v3/ALTAK" not in cfg_text, "config.yaml 不应再出现百度 API Key"
assert "VOLC_ARK_API_KEY" in cfg_text

# 5. 独立视觉 MCP 服务器代码可被导入（不依赖 agent.vision）
import vision_mcp.server as vs
assert vs.settings["port"] == 47833
assert vs.server.name == "nori-vision"

mem.close()
print("vision MCP independent OK")
