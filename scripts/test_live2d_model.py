"""开发用：离屏验证 Live2D 模型能否被渲染器加载，以及表情注册。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from agent.config import load_config
from gui.live2d_view import Live2DView

app = QApplication([])
cfg = load_config()
model_path = getattr(cfg, "live2d_model_path", "")
print("model_path:", model_path, flush=True)
print("exists:", Path(model_path).exists(), flush=True)

view = Live2DView()
view.resize(340, 420)
view.show()

state = {"loaded": False, "error": ""}


def on_loaded():
    state["loaded"] = True
    print("MODEL LOADED", flush=True)

    def check_list(js_result):
        print("EXPRESSIONS:", js_result, flush=True)

        def check_expr(expr_result):
            print("EXPR TEST:", expr_result, flush=True)
            QTimer.singleShot(300, app.quit)

        view.page().runJavaScript("window.neuroTestExpression('爱心眼')", check_expr)

    view.page().runJavaScript("window.neuroListExpressions()", check_list)


view.bridge.modelLoaded.connect(on_loaded)
view.bridge.modelError.connect(lambda e: (state.update(error=e), print("MODEL ERROR:", e, flush=True), QTimer.singleShot(300, app.quit)))
view.bridge.ready.connect(lambda: view.load_model(model_path))

QTimer.singleShot(15000, app.quit)
app.exec()
print("final:", state, flush=True)
