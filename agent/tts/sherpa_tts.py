"""sherpa-onnx 本地 TTS（推荐中文模型 vits-zh-hf-fanchen-C，CPU 可跑）。"""
from __future__ import annotations

import logging
import os

from .base import TTSBackend
from utils.audio import play_samples

logger = logging.getLogger("tts.sherpa")


class SherpaTTS(TTSBackend):
    name = "sherpa"

    def __init__(self, cfg):
        self.model_dir = cfg.tts_sherpa_model_dir
        s = cfg.tts.get("sherpa", {})
        self.speaker_id = int(s.get("speaker_id", 0)) if isinstance(s, dict) else 0
        self.speed = float(s.get("speed", 1.0)) if isinstance(s, dict) else 1.0
        self.provider = str(s.get("provider", "cpu")) if isinstance(s, dict) else "cpu"
        self.num_threads = int(s.get("num_threads", 2)) if isinstance(s, dict) else 2
        self._tts = None

    def _find_model(self) -> str | None:
        if not self.model_dir or not os.path.isdir(self.model_dir):
            return None
        onnx_files = sorted(
            os.path.join(self.model_dir, f)
            for f in os.listdir(self.model_dir)
            if f.endswith(".onnx")
        )
        # 优先取和目录同名的 onnx，否则取第一个
        for f in onnx_files:
            if os.path.basename(f) == os.path.basename(self.model_dir) + ".onnx":
                return f
        return onnx_files[0] if onnx_files else None

    def available(self) -> bool:
        if not self._find_model():
            return False
        if not os.path.isfile(os.path.join(self.model_dir, "tokens.txt")):
            return False
        try:
            import sherpa_onnx  # noqa: F401
            return True
        except Exception:
            return False

    def set_speed(self, speed: float):
        self.speed = float(speed)

    def _load(self):
        if self._tts is not None:
            return self._tts
        import sherpa_onnx

        model_path = self._find_model()
        if not model_path:
            raise RuntimeError(f"sherpa 模型目录里没有 .onnx 文件：{self.model_dir}")
        tokens_path = os.path.join(self.model_dir, "tokens.txt")
        lexicon_path = os.path.join(self.model_dir, "lexicon.txt")
        if not os.path.isfile(lexicon_path):
            lexicon_path = ""

        vits = sherpa_onnx.OfflineTtsVitsModelConfig(
            model=model_path,
            tokens=tokens_path,
            lexicon=lexicon_path,
        )
        model_cfg = sherpa_onnx.OfflineTtsModelConfig(
            vits=vits,
            provider=self.provider,
            num_threads=self.num_threads,
            debug=0,
        )
        tts_cfg = sherpa_onnx.OfflineTtsConfig(
            model=model_cfg,
            rule_fsts="",
            max_num_sentences=2,
        )
        self._tts = sherpa_onnx.OfflineTts(tts_cfg)
        logger.info("sherpa-onnx TTS 已加载：%s", self.model_dir)
        return self._tts

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        tts = self._load()
        audio = tts.generate(text, sid=self.speaker_id, speed=self.speed)
        if audio is None or audio.samples is None or len(audio.samples) == 0:
            raise RuntimeError("sherpa-onnx 合成失败")
        play_samples(audio.samples, audio.sample_rate)
