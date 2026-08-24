@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo  Nori Live2D Agent - Setup
echo ============================================================

if not exist .venv (
    echo [1/4] Creating virtual environment .venv ...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create venv. Please install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )
) else (
    echo [1/4] .venv already exists, skip creation
)

call .venv\Scripts\activate.bat

echo [2/4] Installing Python dependencies ...
python -m pip install -U pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. Check your network or Python version.
    pause
    exit /b 1
)

echo [3/4] Downloading local TTS models（可选） ...
python scripts\download_tts_models.py
if errorlevel 1 (
    echo TTS model download failed. You can retry later:
    echo   .venv\Scripts\python scripts\download_tts_models.py
)

echo.
echo ============================================================
echo  Setup complete!
echo  1) 运行 run.bat 启动，然后在 设置→基础设置 里填写：
echo     DeepSeek API Key / 百度搜索 API Key / 视觉 MCP API Key
echo  2) 也可以手动写入 data\settings_overrides.json 或设置环境变量
echo  3) 如需视觉能力，先配置 vision_mcp\config.json 或 VOLC_ARK_API_KEY
echo  4) 运行 run.bat 启动
echo ============================================================
pause
