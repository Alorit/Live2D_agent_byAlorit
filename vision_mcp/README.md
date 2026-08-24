# Nori 视觉 MCP（独立版）

这个目录是一个**独立、可分发**的视觉 MCP 服务器，不读取主项目 `config.yaml`，
因此主项目分发时不会包含火山方舟 API Key。

## 快速开始

### 1. 配置 API Key

二选一：

- 环境变量：

  ```bat
  set VOLC_ARK_API_KEY=你的火山方舟APIKey
  set VISION_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
  set VISION_MODEL=doubao-seed-2-1-pro-260628
  set VISION_MCP_PORT=47833
  ```

- 本目录 `config.json`（从 `config.example.json` 复制并填写）：

  ```json
  {
    "api_key": "你的火山方舟APIKey",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-seed-2-1-pro-260628",
    "port": 47833,
    "timeout": 120
  }
  ```

### 2. 启动服务器

```bat
python vision_mcp\server.py
```

或指定端口：

```bat
python vision_mcp\server.py --port 47833
```

默认 MCP 地址：`http://127.0.0.1:47833/mcp`

### 3. 在主程序设置界面导入

1. 先启动 `vision_mcp/server.py`。
2. 打开 Nori 控制台 → `⚙ 设置` → `🔌 MCP / Skills` → `📂 导入 MCP JSON`。
3. 选择本目录的 `nori-vision.mcp.json`。
4. 确认服务器 `nori-vision` 已启用。
5. 之后发送普通图片时，Nori 会通过这个 MCP 服务器调用视觉工具。

## 工具

| 工具 | 说明 |
|---|---|
| `analyze_image` | 分析图片：本地路径 / http(s) URL / data URL |
| `describe_image` | 图片内容概括 |

## 独立分发

复制整个 `vision_mcp/` 目录即可（不要包含你的 `config.json`）。
目标机器需要安装：

```txt
openai
mcp
requests
```
