"""GPT-SoVITS 无窗口服务启动器（由 agent/services.py 用 pythonw 调用）。

用法：
    pythonw gpt_sovits_service.py <runtime_dir> <host> <port> <infer_yaml_rel> <log_path> [pid_path]
"""
import os
import runpy
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 6:
        raise SystemExit("usage: gpt_sovits_service.py runtime_dir host port yaml_rel log_path [pid_path]")

    runtime_dir = Path(sys.argv[1]).resolve()
    host = sys.argv[2]
    port = sys.argv[3]
    infer_yaml = sys.argv[4]
    log_path = Path(sys.argv[5])
    pid_path = Path(sys.argv[6]) if len(sys.argv) > 6 else None

    log_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = f
    sys.stderr = f

    if pid_path is not None:
        try:
            pid_path.write_text(str(os.getpid()), encoding="utf-8")
        except Exception as exc:
            print(f"[gpt_sovits_service] 写入 pid 失败：{exc}", flush=True)

    os.chdir(runtime_dir)
    api_py = Path.cwd() / "api_v2.py"
    if not api_py.exists():
        print(f"[gpt_sovits_service] api_v2.py not found in {runtime_dir}", flush=True)
        raise SystemExit(2)

    sys.argv = ["api_v2.py", "-a", host, "-p", port, "-c", infer_yaml]
    try:
        runpy.run_path(str(api_py), run_name="__main__")
    finally:
        if pid_path is not None:
            try:
                if pid_path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                    pid_path.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    main()
