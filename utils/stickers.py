"""Nori 表情包工具。

- 内置默认表情包：首次打开表情面板时用 Qt 渲染成 PNG，存放在
  data/stickers/default/ 下。
- 用户导入的表情包：复制到 data/stickers/imported/ 下，长期可用。
- 聊天图片会统一复制到 data/chat_media/ 下，保证历史记录始终能找到。
"""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

# key -> (中文名, emoji)
DEFAULT_STICKERS = {
    "big_smile": ("大笑", "😄"),
    "grin": ("开心", "😊"),
    "laugh_cry": ("笑哭", "😂"),
    "heart_eyes": ("喜欢", "😍"),
    "love": ("爱心", "❤️"),
    "shy": ("害羞", "😳"),
    "cry": ("哭哭", "😭"),
    "angry": ("生气", "😠"),
    "surprised": ("惊讶", "😮"),
    "think": ("思考", "🤔"),
    "ok": ("好的", "👌"),
    "wave": ("挥手", "👋"),
    "bunny": ("小兔子", "🐰"),
    "sparkles": ("闪亮", "✨"),
    "cool": ("酷", "😎"),
    "sad": ("难过", "😔"),
}


def stickers_dir(root: Path) -> Path:
    return root / "data" / "stickers"


def media_dir(root: Path) -> Path:
    return root / "data" / "chat_media"


def default_stickers_dir(root: Path) -> Path:
    return stickers_dir(root) / "default"


def is_image_file(path: str | Path) -> bool:
    p = Path(path)
    return p.is_file() and p.suffix.lower() in IMAGE_EXTS


def _render_sticker(dest: Path, emoji: str):
    """把 emoji 渲染成透明底 PNG 表情（需要已存在 QGuiApplication）。"""
    import os

    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import (
        QColor,
        QFont,
        QFontDatabase,
        QGuiApplication,
        QImage,
        QPainter,
    )
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None and QGuiApplication.instance() is None:
        raise RuntimeError("渲染表情包需要 QGuiApplication")

    # Qt 在无自带字体目录的环境里可能找不到 emoji 字体，优先用已加载的系统字体，
    # 找不到时手动加载 Windows 字体。
    font_family = ""
    try:
        for family in QFontDatabase.families():
            if "emoji" in family.lower() or "symbol" in family.lower():
                font_family = family
                break
    except Exception:
        pass
    if not font_family:
        windir = os.environ.get("WINDIR", r"C:\Windows")
        for font_file in ("seguiemj.ttf", "msyh.ttc", "arial.ttf"):
            p = Path(windir) / "Fonts" / font_file
            if p.exists():
                try:
                    fid = QFontDatabase.addApplicationFont(str(p))
                    families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
                    if families:
                        font_family = families[0]
                        break
                except Exception:
                    continue

    size = 320
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(0x00000000)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # 柔和圆底，避免纯透明在深色聊天框里看不清
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(30, 58, 110, 150))
    painter.drawEllipse(QRectF(24, 24, size - 48, size - 48))

    font = QFont(font_family) if font_family else QFont()
    font.setPixelSize(190)
    painter.setFont(font)
    painter.setPen(QColor("#eef2ff"))
    painter.drawText(img.rect(), Qt.AlignCenter, emoji)
    painter.end()

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest), "PNG")


def ensure_default_stickers(root: Path) -> Path:
    """确保内置默认表情包存在，返回 default 目录。"""
    d = default_stickers_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    for key, (_label, emoji) in DEFAULT_STICKERS.items():
        p = d / f"{key}.png"
        if not p.exists():
            try:
                _render_sticker(p, emoji)
            except Exception:
                # 无 GUI 环境下不生成，面板仍可导入已有表情
                break
    return d


def list_stickers(root: Path, limit: int = 160) -> list[dict]:
    """返回 data/stickers 下的表情列表（内置在前，导入的在后）。"""
    d = stickers_dir(root)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.rglob("*")):
        if p.is_file() and is_image_file(p):
            rel = p.relative_to(d)
            label = sticker_label(p, rel)
            out.append({
                "path": str(p),
                "name": label,
                "rel": rel.as_posix(),
            })
            if len(out) >= limit:
                break
    return out


def sticker_label(path: str | Path, rel: Path | None = None) -> str:
    """根据文件名给表情一个可读标签，供 Nori 理解表情含义。"""
    p = Path(path)
    if rel is None:
        parts = p.parts
        if "stickers" in parts:
            idx = parts.index("stickers")
            rel = Path(*parts[idx + 1:])
        else:
            rel = p
    key = rel.stem
    default = DEFAULT_STICKERS.get(key)
    if default:
        return default[0]
    name = key.replace("_", " ").replace("-", " ").strip()
    return name or "表情"


def import_sticker(root: Path, src: str | Path) -> Path | None:
    """把一张本地图片复制进表情包库，返回新路径。"""
    src = Path(src)
    if not is_image_file(src):
        return None
    d = stickers_dir(root) / "imported"
    d.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[\\/:*?\"<>|\s]+", "_", src.stem).strip("_") or "sticker"
    dest = d / f"{stem}{src.suffix.lower()}"
    if dest.exists():
        dest = d / f"{stem}_{int(time.time())}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return dest


def copy_to_chat_media(root: Path, src: str | Path) -> Path | None:
    """把用户发送的图片复制进 data/chat_media，历史记录里长期可用。"""
    src = Path(src)
    if not is_image_file(src):
        return None
    d = media_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stem = re.sub(r"[\\/:*?\"<>|\s]+", "_", src.stem).strip("_") or "image"
    dest = d / f"{stamp}_{stem}{src.suffix.lower()}"
    i = 1
    while dest.exists():
        dest = d / f"{stamp}_{stem}_{i}{src.suffix.lower()}"
        i += 1
    shutil.copy2(src, dest)
    return dest
