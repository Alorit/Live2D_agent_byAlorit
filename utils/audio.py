"""音频播放工具：优先 Windows 原生 winsound（WAV），否则 sounddevice。"""
from __future__ import annotations

import os
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np


def samples_to_wav(path: str, samples, sample_rate: int) -> str:
    """把 float32[-1,1] 或 int16 样本写成 PCM WAV。"""
    path = str(path)
    arr = np.asarray(samples)
    if arr.dtype != np.int16:
        arr = np.clip(arr, -1.0, 1.0)
        arr = (arr * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(arr.tobytes())
    return path


def play_wav(path: str) -> None:
    """阻塞式播放 WAV。"""
    path = str(path)
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        return

    # 非 Windows：用 sounddevice + wave
    import sounddevice as sd
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        frames = w.getnframes()
        pcm = np.frombuffer(w.readframes(frames), dtype=np.int16)
    sd.play(pcm, samplerate=rate)
    sd.wait()


def play_samples(samples, sample_rate: int) -> None:
    """播放内存中的音频样本。"""
    tmp = os.path.join(tempfile.gettempdir(), "neuro_tts_tmp.wav")
    samples_to_wav(tmp, samples, sample_rate)
    try:
        play_wav(tmp)
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass
