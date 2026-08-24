"""LLM 上下文压缩器。

成熟做法：保留最近 window_size 条消息原文，把更早的对话交给 LLM
压缩成一段精炼摘要（保留用户个人信息、偏好、任务与关键决定）。
摘要按“人格 + 旧消息指纹 + 窗口”缓存，避免每轮重复调用 LLM。
"""
from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger("agent.compressor")


class ContextCompressor:
    def __init__(self, brain, memory, cfg):
        self.brain = brain
        self.memory = memory
        self.cfg = cfg

    def settings(self) -> dict:
        return self.cfg.llm.get("context_compression", {}) or {}

    def enabled(self, history_len: int) -> bool:
        s = self.settings()
        mode = str(s.get("mode", "auto"))
        if mode == "off":
            return False
        window = max(5, int(s.get("window_size", 20)))
        if mode == "on":
            return history_len > window
        # auto：超过窗口，且更早部分确实有一定信息量
        return history_len > window

    def history_for_llm(self, history: list[dict[str, str]], persona: str) -> list[dict[str, str]]:
        s = self.settings()
        window = max(5, int(s.get("window_size", 20)))
        max_chars = max(100, int(s.get("max_chars", 300)))
        if not self.enabled(len(history)) or len(history) <= window:
            return history

        old = history[:-window]
        recent = history[-window:]
        digest = hashlib.sha1(
            "".join(f"{m['role']}:{m['content']}" for m in old).encode("utf-8")
        ).hexdigest()[:12]
        cache_key = f"ctx:{persona}:{digest}:{window}"

        summary = self.memory.get_summary(cache_key)
        if not summary:
            summary = self._compress(old, max_chars)
            if summary:
                self.memory.set_summary(summary, cache_key)

        if not summary:
            return history
        prefix = [{
            "role": "system",
            "content": ("【更早对话的压缩记忆】下面是对此前对话的摘要，请继承其中的信息，"
                        f"但不要逐字复述：\n{summary}"),
        }]
        return prefix + recent

    def _compress(self, old: list[dict[str, str]], max_chars: int) -> str:
        try:
            client = self.brain._ensure_client()
            lines = "\n".join(f"{m['role']}: {m['content']}" for m in old[-60:])
            prompt = (
                "你是对话上下文压缩器。请把以下较早的对话压缩成一段精炼摘要，"
                "保留：用户的个人信息与偏好、正在进行的话题、双方做出的决定、"
                "与之后回复相关的背景。不要编造内容，不要使用括号描述动作。"
                f"摘要不超过 {max_chars} 个汉字，直接输出摘要正文。\n\n{lines}")
            resp = client.chat.completions.create(
                model=self.cfg.model,
                temperature=0.2,
                max_tokens=max(100, int(max_chars * 0.75)),
                messages=[{"role": "user", "content": prompt}],
            )
            return (resp.choices[0].message.content or "").strip()[: max_chars * 2]
        except Exception as e:
            logger.warning("上下文压缩失败：%s", e)
            return ""
