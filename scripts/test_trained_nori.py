# -*- coding: utf-8 -*-
"""验证 Nori 微调模型：启动 API → 合成测试句 → 对比基频 → 停止 API。"""
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import requests

from agent.config import load_config
from agent.services import ServiceManager

cfg = load_config()
sm = ServiceManager(cfg)
ref = cfg.root / "data" / "voices" / "nori" / "nori_ref.wav"
out = cfg.root / "data" / "voices" / "nori" / "trained_test.wav"

print("start gsv...")
assert sm.start_gpt_sovits()
ready = False
for i in range(240):
    try:
        if requests.get("http://127.0.0.1:9880/docs", timeout=1).status_code == 200:
            ready = True
            break
    except Exception:
        pass
    time.sleep(1)
print("ready", ready, "after", i + 1, "s")
assert ready

r = requests.post("http://127.0.0.1:9880/tts", json={
    "text": "你好呀，主人，今天想让我陪你做点什么吗？",
    "text_lang": "zh",
    "ref_audio_path": str(ref),
    "prompt_text": "Nori 是最擅长玩游戏、最喜欢你陪伴的小人偶 AI！",
    "prompt_lang": "zh",
    "speed_factor": 1.0,
    "streaming_mode": False,
}, timeout=180)
print("tts status", r.status_code, "len", len(r.content))
if r.status_code != 200:
    print(r.text[:500])
    raise SystemExit(1)
out.write_bytes(r.content)


def f0_stats(path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64)
    f0s = []
    n = int(sr * 0.025)
    h = int(sr * 0.010)
    for i in range(0, len(x) - n, h):
        seg = x[i:i + n] - x[i:i + n].mean()
        rms = np.sqrt(np.mean(seg ** 2))
        if rms < 400:
            continue
        ac = np.correlate(seg, seg, mode="full")[len(seg) - 1:]
        ac = ac / (ac[0] + 1e-9)
        lag = int(np.argmax(ac[int(sr / 400):int(sr / 60)]) + int(sr / 400))
        f0s.append(sr / lag if lag else 0)
    return np.median(f0s), len(x) / sr

ref_f0, ref_dur = f0_stats(ref)
syn_f0, syn_dur = f0_stats(out)
print(f"ref  f0={ref_f0:.1f}Hz dur={ref_dur:.2f}s")
print(f"trained f0={syn_f0:.1f}Hz dur={syn_dur:.2f}s")
assert abs(syn_f0 - ref_f0) < 80, "音高偏离过大，微调模型可能异常"
print("trained Nori TTS OK")
print("stop:", sm.stop_gpt_sovits())
