# -*- coding: utf-8 -*-
"""多人格面板槽函数测试（真实 persona 目录，结束后清理）。"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from agent.config import load_config
from agent.persona import active_persona_name, list_personas, persona_file_for
from main import AppController, setup_logging

cfg = load_config()
setup_logging(cfg.log_file)
app = QApplication(sys.argv)
ctrl = AppController(cfg, app, enable_pet=False, autostart_services=False)

original = active_persona_name(cfg)
try:
    ctrl.on_persona_new("smoketest", "# smoke 人格")
    assert active_persona_name(cfg) == "smoketest"
    assert persona_file_for(cfg, "smoketest").exists()
    assert ctrl.chat.persona_combo.currentData() == "smoketest"
    print("new/switch combo OK")

    ctrl.on_persona_save("smoketest", "# smoke 人格 v2")
    assert persona_file_for(cfg, "smoketest").read_text(encoding="utf-8").strip() == "# smoke 人格 v2"
    print("save OK")

    ctrl.on_persona_switch(original)
    assert active_persona_name(cfg) == original
    assert ctrl.chat.persona_combo.currentData() == original
    print("switch back OK")

    ctrl.on_persona_delete("smoketest")
    assert "smoketest" not in list_personas(cfg)
    print("delete OK")
finally:
    # 确保恢复原状
    try:
        if active_persona_name(cfg) != original:
            from agent.persona import set_active_persona
            set_active_persona(cfg, original)
    except Exception:
        pass
