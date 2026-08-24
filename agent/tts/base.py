"""TTS 后端抽象基类。"""
from __future__ import annotations


class TTSBackend:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def speak(self, text: str) -> None:
        """阻塞式合成并播放。在调用方线程中执行。"""
        raise NotImplementedError
