"""Piper 本地 TTS（轻量 CPU，英文最佳，中文音色较少）。"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile

from .base import TTSBackend
from utils.audio import play_wav

logger = logging.getLogger("tts.piper")


class PiperTTS(TTSBackend):
    name = "piper"

    def __init__(self, cfg):
        self.model_dir = cfg.tts_piper_model_dir
        p = cfg.tts.get("piper", {})
        self.voice = str(p.get("voice", "zh_CN-huayan-medium")) if isinstance(p, dict) else "zh_CN-huayan-medium"
        self.length_scale = float(p.get("length_scale", 1.0)) if isinstance(p, dict) else 1.0

    @property
    def model_path(self):
        return os.path.join(self.model_dir, self.voice + ".onnx")

    @property
    def config_path(self):
        return os.path.join(self.model_dir, self.voice + ".onnx.json")

    def available(self) -> bool:
        if not (os.path.isfile(self.model_path) and os.path.isfile(self.config_path)):
            return False
        return self._find_piper() is not None

    @staticmethod
    def _find_piper() -> list[str] | None:
        exe = shutil.which("piper")
        if exe:
            return [exe]
        # 尝试 python -m piper
        try:
            r = subprocess.run([sys.executable, "-m", "piper", "--help"],
                               capture_output=True, text=True, timeout=20)
            if r.returncode == 0 or "usage" in (r.stdout + r.stderr).lower():
                return [sys.executable, "-m", "piper"]
        except Exception:
            pass
        return None

    def set_speed(self, speed: float):
        self.length_scale = max(0.5, min(2.0, 1.0 / max(0.5, float(speed))))

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        piper = self._find_piper()
        if piper is None:
            raise RuntimeError("找不到 piper 可执行程序，请先 pip install piper-tts")
        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="neuro_piper_")
        os.close(fd)
        cmd = piper + [
            "-m", self.model_path,
            "-c", self.config_path,
            "-f", wav_path,
        ]
        if self.length_scale != 1.0:
            cmd += ["--length-scale", str(self.length_scale)]
        try:
            r = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise RuntimeError(f"piper 合成失败：{r.stderr or r.stdout}")
            play_wav(wav_path)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
