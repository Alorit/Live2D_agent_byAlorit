"""下载本地 TTS 模型。

用法：
    python scripts/download_tts_models.py              # 下载 sherpa 中文模型 + piper 中文音色
    python scripts/download_tts_models.py --sherpa     # 只下载 sherpa
    python scripts/download_tts_models.py --piper      # 只下载 piper
    python scripts/download_tts_models.py --sherpa --sherpa-model vits-melo-tts-zh_en   # 换一个音色

需要能访问 GitHub / HuggingFace。下载后模型放在 data/tts/ 下。
"""
from __future__ import annotations

import argparse
import sys
import tarfile
import tempfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_TTS = ROOT / "data" / "tts"

SHERPA_MODEL = "vits-zh-hf-fanchen-C"
SHERPA_URLS = [
    f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{SHERPA_MODEL}.tar.bz2",
    f"https://huggingface.co/csukuangfj/{SHERPA_MODEL}/resolve/main/{SHERPA_MODEL}.tar.bz2",
    f"https://hf-mirror.com/csukuangfj/{SHERPA_MODEL}/resolve/main/{SHERPA_MODEL}.tar.bz2",
]

PIPER_VOICE = "zh_CN-huayan-medium"
PIPER_URLS = [
    (f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/{PIPER_VOICE}.onnx",
     f"{PIPER_VOICE}.onnx"),
    (f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/{PIPER_VOICE}.onnx.json",
     f"{PIPER_VOICE}.onnx.json"),
]
PIPER_MIRRORS = [
    f"https://hf-mirror.com/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/{PIPER_VOICE}.onnx",
    f"https://hf-mirror.com/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/{PIPER_VOICE}.onnx.json",
]


def _download(url: str, dest: Path, timeout=120) -> bool:
    print(f"  下载：{url}")
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
    except requests.exceptions.SSLError:
        # 某些 Windows 环境缺少根证书，退回不校验证书（仅用于下载公开模型）
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            resp = requests.get(url, stream=True, timeout=timeout, verify=False)
        except Exception as e:
            print(f"  连接失败：{e}")
            return False
    except Exception as e:
        print(f"  连接失败：{e}")
        return False
    if resp.status_code != 200:
        print(f"  失败（HTTP {resp.status_code}）")
        return False
    total = int(resp.headers.get("Content-Length", 0))
    done = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {pct:3d}%", end="", flush=True)
    except Exception as e:
        print(f"\n  写入失败：{e}")
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        return False
    print("\r  完成        ")
    return True


def download_sherpa(model_name: str = "vits-zh-hf-fanchen-C"):
    print(f"==> 下载 sherpa-onnx TTS 模型：{model_name}")
    target_dir = DATA_TTS / "sherpa"
    target_dir.mkdir(parents=True, exist_ok=True)
    model_dir = target_dir / model_name
    if _sherpa_model_exists(model_dir):
        print("  已存在，跳过。")
        return True

    # 优先从 hf-mirror 直接下载模型文件（通常比 GitHub release 快）
    direct_base = f"https://hf-mirror.com/csukuangfj/{model_name}/resolve/main"
    direct_files = ["model.onnx", "tokens.txt", "lexicon.txt"]
    direct_ok = True
    for fname in direct_files:
        dest = model_dir / fname
        if dest.exists() and dest.stat().st_size > 0:
            continue
        if not _download(f"{direct_base}/{fname}", dest):
            direct_ok = False
            break
    if direct_ok and _sherpa_model_exists(model_dir):
        print(f"  已就绪：{model_dir}")
        return True

    # 退回 tar.bz2 整包下载
    urls = [
        f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{model_name}.tar.bz2",
        f"https://huggingface.co/csukuangfj/{model_name}/resolve/main/{model_name}.tar.bz2",
        f"https://hf-mirror.com/csukuangfj/{model_name}/resolve/main/{model_name}.tar.bz2",
    ]

    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / f"{model_name}.tar.bz2"
        ok = False
        for url in urls:
            if _download(url, archive):
                ok = True
                break
        if not ok:
            print("  所有下载源都失败。")
            return False
        print("  解压中…")
        with tarfile.open(archive, "r:bz2") as tar:
            tar.extractall(target_dir)
        print(f"  已解压到：{model_dir}")
    return True


def _sherpa_model_exists(model_dir: Path) -> bool:
    if not model_dir.is_dir():
        return False
    has_onnx = any(f.endswith(".onnx") for f in model_dir.iterdir() if f.is_file())
    has_tokens = (model_dir / "tokens.txt").exists()
    return has_onnx and has_tokens


def download_piper():
    print(f"==> 下载 piper 中文音色：{PIPER_VOICE}")
    target_dir = DATA_TTS / "piper"
    target_dir.mkdir(parents=True, exist_ok=True)
    if (target_dir / f"{PIPER_VOICE}.onnx").exists() and \
       (target_dir / f"{PIPER_VOICE}.onnx.json").exists():
        print("  已存在，跳过。")
        return True

    ok = True
    for (url, fname), mirror in zip(PIPER_URLS, PIPER_MIRRORS):
        dest = target_dir / fname
        if dest.exists():
            continue
        if not _download(url, dest) and not _download(mirror, dest):
            ok = False
    if ok:
        print(f"  已保存到：{target_dir}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sherpa", action="store_true", help="只下载 sherpa 模型")
    ap.add_argument("--piper", action="store_true", help="只下载 piper 音色")
    ap.add_argument("--sherpa-model", default="vits-zh-hf-fanchen-C",
                    help="sherpa 模型名，可选：vits-zh-hf-fanchen-C（默认女声）、vits-melo-tts-zh_en（中英女声）")
    args = ap.parse_args()

    both = not (args.sherpa or args.piper)
    results = []
    if both or args.sherpa:
        results.append(("sherpa", download_sherpa(args.sherpa_model)))
    if both or args.piper:
        results.append(("piper", download_piper()))

    print("\n==> 结果")
    all_ok = True
    for name, ok in results:
        print(f"  {name}: {'成功' if ok else '失败'}")
        all_ok = all_ok and ok
    if all_ok:
        print("TTS 模型就绪。运行 main.py 即可使用。")
    else:
        print("部分模型下载失败，请检查网络后重试。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
