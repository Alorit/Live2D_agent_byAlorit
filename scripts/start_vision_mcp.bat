@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ============================================================
echo  Nori Vision MCP (独立版)
echo  MCP: http://127.0.0.1:47833/mcp
echo  配置：vision_mcp\config.json 或环境变量 VOLC_ARK_API_KEY
echo ============================================================

if not exist .venv (
    echo Please run setup_venv.bat first.
    pause
    exit /b 1
)

if not exist vision_mcp\config.json (
    echo [提示] 未找到 vision_mcp\config.json
    echo 请复制 vision_mcp\config.example.json 为 vision_mcp\config.json 并填写 API Key，
    echo 或先设置环境变量 VOLC_ARK_API_KEY。
)

.venv\Scripts\python.exe vision_mcp\server.py %*
pause
