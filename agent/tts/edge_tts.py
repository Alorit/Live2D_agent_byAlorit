"""Edge 在线 TTS（仅作为本地全部不可用时的最后兜底）。"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile

from .base import TTSBackend

logger = logging.getLogger("tts.edge")


class EdgeTTS(TTSBackend):
    name = "edge"

    def __init__(self, cfg):
        e = cfg.tts.get("edge", {})
        self.voice = str(e.get("voice", "zh-CN-XiaoyiNeural")) if isinstance(e, dict) else "zh-CN-XiaoyiNeural"
        self.rate = "+0%"

    def available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except Exception:
            return False

    def set_speed(self, speed: float):
        pct = int(round((float(speed) - 1.0) * 100))
        self.rate = f"{pct:+d}%"

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        import edge_tts

        fd, mp3 = tempfile.mkstemp(suffix=".mp3", prefix="neuro_edge_")
        os.close(fd)
        try:
            asyncio.run(edge_tts.Communicate(text, self.voice, rate=self.rate).save(mp3))
            self._play_mp3(mp3)
        finally:
            try:
                os.unlink(mp3)
            except OSError:
                pass

    @staticmethod
    def _play_mp3(path: str):
        # 优先 pygame
        try:
            import pygame  # type: ignore
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            return
        except Exception:
            pass
        # 其次 ffplay
        ffplay = shutil.which("ffplay")
        if ffplay:
            subprocess.run([ffplay, "-nodisp", "-autoexit", path],
                           capture_output=True, timeout=120)
            return
        raise RuntimeError("Edge TTS 生成了 mp3，但缺少播放器（请安装 pygame 或 ffplay）")
