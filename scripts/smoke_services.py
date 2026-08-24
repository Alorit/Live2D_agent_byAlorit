# -*- coding: utf-8 -*-
"""ServiceManager 完整测试：GPT-SoVITS 真正 HTTP 就绪后停止。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests

from agent.config import load_config
from agent.services import ServiceManager

sm = ServiceManager(load_config())
print("start...")
assert sm.start_gpt_sovits()
print("proc pid", sm.gsv_proc.pid if sm.gsv_proc else None)
ready = False
for i in range(180):
    try:
        if requests.get("http://127.0.0.1:9880/docs", timeout=1).status_code == 200:
            ready = True
            break
    except Exception:
        pass
    if sm.gsv_proc and sm.gsv_proc.poll() is not None:
        print("proc exited early", sm.gsv_proc.poll())
        break
    time.sleep(1)
print("ready", ready, "after", i + 1, "s")
assert ready
stopped = sm.stop_gpt_sovits()
print("stopped", stopped)
for _ in range(30):
    try:
        requests.get("http://127.0.0.1:9880/docs", timeout=1)
        time.sleep(0.3)
    except Exception:
        break
print("still_running", sm.gsv_is_running())
assert not sm.gsv_is_running()
print("gsv service OK")
