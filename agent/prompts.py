"""构造系统提示词。

重要：当前人格 .md 就是完整 System Prompt 的唯一来源。
- 不再向 .md 之外自动追加 config.yaml 里的人设/规则/主人设定；
- .md 里可以使用以下占位符，程序只替换这些占位符：
    {{time}}     当前日期时间
    {{memory}}   检索到的相关长期记忆
    {{rules}}    学到的行为规则
    {{summary}}  滚动摘要
- 不使用占位符时，发送给 LLM 的 system prompt 就是 .md 原文。
"""
from __future__ import annotations

from datetime import datetime

from .persona import active_persona_name, load_persona_text

_WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def build_system_prompt(cfg, memory, user_text: str = "") -> str:
    """人格 .md 模板 + 可选动态占位符替换。"""
    template = load_persona_text(cfg)
    persona = active_persona_name(cfg)

    now = datetime.now()
    time_line = (f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')} "
                 f"{_WEEKDAYS[now.weekday()]}。涉及日期、时间、节日、天气等时效性问题时，以此为准。")

    mem_text = ""
    if "{{memory}}" in template and user_text:
        mems = memory.retrieve(user_text, k=int(cfg.memory.get("top_k", 8)))
        if mems:
            lines = [f"- [{m['type']}] {m['content']}" for m in mems]
            mem_text = "\n".join(lines)

    rules_text = ""
    if "{{rules}}" in template:
        rules = memory.get_active_rules(limit=15)
        if rules:
            rules_text = "\n".join(f"- {r}" for r in rules)

    summary_text = ""
    if "{{summary}}" in template:
        summary_text = memory.get_summary(f"working:{persona}") or ""

    return (template
            .replace("{{time}}", time_line)
            .replace("{{memory}}", mem_text)
            .replace("{{rules}}", rules_text)
            .replace("{{summary}}", summary_text))
