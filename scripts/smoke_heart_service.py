# -*- coding: utf-8 -*-
"""Heart 服务启停冒烟测试（跳过 Live2D，不触发 LLM）。"""
import os
import sys
import time
from pathlib import Path

os.environ["NORI_HEART_SKIP_LIVE2D"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import load_config
from agent.services import ServiceManager

cfg = load_config()
sm = ServiceManager(cfg)
print("running before:", sm.heart_is_running())
assert sm.start_heart()
time.sleep(8)
print("running after start:", sm.heart_is_running(), "pid:", sm.heart_proc.pid)
assert sm.heart_is_running()
ok = sm.stop_heart()
print("stop ok:", ok)
for _ in range(10):
    if not sm.heart_is_running():
        break
    time.sleep(0.5)
print("running after stop:", sm.heart_is_running())
assert not sm.heart_is_running()
print("heart service OK")
