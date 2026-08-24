"""Windows SAPI5 本地 TTS（无需安装，中文音色取决于系统语音包）。"""
from __future__ import annotations

import logging
import subprocess
import sys

from .base import TTSBackend

logger = logging.getLogger("tts.system")

_PS_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$zh = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'zh*' } | Select-Object -First 1
if ($zh) { try { $s.SelectVoice($zh.VoiceInfo.Name) } catch {} }
$s.Rate = 0
$s.Speak([Console]::In.ReadToEnd())
"""


class SystemTTS(TTSBackend):
    name = "system"

    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg

    def available(self) -> bool:
        return sys.platform == "win32"

    def set_speed(self, speed: float):
        pass

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _PS_SCRIPT],
                input=text, capture_output=True, text=True, timeout=120,
            )
            if r.returncode != 0:
                raise RuntimeError(f"SAPI5 语音失败：{r.stderr or r.stdout}")
        except FileNotFoundError:
            raise RuntimeError("找不到 powershell")
