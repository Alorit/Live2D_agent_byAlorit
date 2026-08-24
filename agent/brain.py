"""DeepSeek 大脑：OpenAI 兼容调用 + 标签解析 + 反思整合。"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

logger = logging.getLogger("agent.brain")

# [expr:开心] / [motion:点头] / [emotion:xxx]（emotion 作为 expr 的别名）
_TAG_RE = re.compile(r"\[(expr|motion|emotion):([^\]\]]+)\]")


@dataclass
class AgentReply:
    text: str
    commands: list[tuple[str, str]] = field(default_factory=list)  # [(kind, name), ...]
    raw: str = ""
    user_msg_id: int | None = None
    assistant_msg_id: int | None = None


def parse_commands(raw: str) -> tuple[str, list[tuple[str, str]]]:
    """从 LLM 输出中提取并移除 [expr:xx] [motion:xx] 标签。"""
    cmds: list[tuple[str, str]] = []

    def _repl(m: re.Match) -> str:
        kind = m.group(1)
        if kind == "emotion":
            kind = "expr"
        name = m.group(2).strip()
        if name:
            cmds.append((kind, name))
        return ""

    clean = _TAG_RE.sub(_repl, raw)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, cmds


class Brain:
    """封装 DeepSeek API 调用。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.client: OpenAI | None = None
        if cfg.api_key:
            self.client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
        else:
            logger.warning("DeepSeek API key 为空，对话功能将返回提示。")

    def _ensure_client(self):
        if not self.cfg.api_key:
            raise RuntimeError("还没有配置 DeepSeek API Key。请编辑 config.yaml 里的 llm.api_key，"
                               "或设置环境变量 DEEPSEEK_API_KEY。")
        if self.client is None:
            self.client = OpenAI(api_key=self.cfg.api_key, base_url=self.cfg.base_url)
        return self.client

    def reload(self):
        """API Key / Base URL 在 GUI 修改后重建客户端。"""
        if self.cfg.api_key:
            self.client = OpenAI(api_key=self.cfg.api_key, base_url=self.cfg.base_url)
        else:
            self.client = None

    def chat(self, system_prompt: str, history: list[dict[str, str]], user_text: str) -> AgentReply:
        """同步调用 DeepSeek。应在工作线程中运行。"""
        client = self._ensure_client()
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages += history[- self.cfg.working_memory_size * 2:]  # user/assistant 成对
        messages.append({"role": "user", "content": user_text})

        resp = client.chat.completions.create(
            model=self.cfg.model,
            messages=messages,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            stream=False,
        )
        raw = resp.choices[0].message.content or ""
        text, cmds = parse_commands(raw)
        return AgentReply(text=text, commands=cmds, raw=raw)

    def chat_message(self, messages: list[dict[str, Any]], tools: list[dict] | None = None):
        """通用调用：返回 OpenAI message 对象（支持 function calling）。"""
        client = self._ensure_client()
        kwargs: dict[str, Any] = dict(
            model=self.cfg.model,
            messages=messages,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            stream=False,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message

    def score_importance(self, user_text: str, reply_text: str) -> float:
        """调用 LLM 为一条交换打分（0~1）。可选，默认启发式打分不用调它。"""
        try:
            client = self._ensure_client()
            resp = client.chat.completions.create(
                model=self.cfg.model,
                temperature=0,
                max_tokens=10,
                messages=[
                    {"role": "system",
                     "content": "评估以下对话对长期记忆的价值。用户偏好、个人信息、关系事件等得高分；"
                                "普通闲聊得低分。只输出 0 到 1 之间的数字，不要输出别的。"},
                    {"role": "user", "content": f"用户：{user_text}\nAI：{reply_text}"},
                ],
            )
            val = float((resp.choices[0].message.content or "0.5").strip())
            return max(0.0, min(1.0, val))
        except Exception:
            return 0.5

    def consolidate(self, recent_messages: list[tuple[str, str, str]]) -> dict[str, Any]:
        """把最近对话提炼成 事实/事件/规则。返回 dict。"""
        client = self._ensure_client()
        if not recent_messages:
            return {"facts": [], "episodes": [], "rules": []}

        lines = "\n".join(f"{role}: {content}" for role, content, _ in recent_messages[-80:])
        prompt = f"""下面是最近的对话记录：
---
{lines}
---

请做三件事，并只输出 JSON：
1. "facts": 提取用户新透露的个人信息或稳定偏好（例如姓名、宠物、工作、喜好、忌讳），用简洁陈述句，如 "用户养了一只叫汤圆的猫"；
2. "episodes": 总结本次值得记住的具体事件（最多 2 条），如 "用户今天心情不好，因为工作压力大"；
3. "rules": 提炼对未来互动有帮助的行为规则（最多 2 条），如 "用户不喜欢被剧透，聊到影视时先问是否看过"。

没有内容的字段给空数组。JSON 格式：{{"facts": [...], "episodes": [...], "rules": [...]}}"""
        kwargs: dict[str, Any] = dict(
            model=self.cfg.model,
            temperature=0.3,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
        except Exception:
            # 部分模型/网关不支持 json_object，退回普通模式
            kwargs.pop("response_format", None)
            resp = client.chat.completions.create(**kwargs)

        raw = resp.choices[0].message.content or "{}"
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            return {"facts": [], "episodes": [], "rules": []}
