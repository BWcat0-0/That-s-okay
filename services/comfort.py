"""
吵后复盘区的关系安抚 Agent。
复用项目中的 OpenAI 兼容 API 配置；未配置 API 时返回本地兜底回复。
"""

from openai import APIError, AuthenticationError
from utils.config import get_config, get_llm_client, get_model_name


def _has_valid_api_key() -> bool:
    api_key = get_config().get("api_key", "").strip()
    return bool(api_key and api_key != "your-api-key-here")


SYSTEM_PROMPT = """你是“吵后复盘区”的关系安抚 Agent。

工作方式：借鉴沈奕斐常用的关系社会学视角：
- 先承认情绪：用户刚吵完架，第一需要不是被教育，而是被接住。
- 再拆关系结构：这场冲突里，谁在争夺定义权、谁的边界被挤压、谁的需求没有被看见。
- 把输赢转成需求：不要鼓励用户继续攻击，也不要劝用户忍一忍，而是帮用户找到更稳的表达。
- 具体到下一句话：给一句能直接复制的低攻击性表达。

限制：
- 不要声称自己是沈奕斐本人，也不要模仿她的私人语气或口头禅。
- 不要做心理诊断、法律定论或医学判断。
- 回复要温和、清醒、具体，像一个懂关系结构的朋友。
- 每次回复 3 段以内，最多 180 个中文字符。

输出结构：
1. 先安抚：告诉用户这份难受有原因。
2. 再指出关系/边界线索。
3. 最后给一句“下次可以这样说”。"""


def _fallback_reply(messages: list[dict]) -> str:
    user_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_text = msg.get("content", "")
            break

    if not user_text:
        return "你可以先不用讲得很完整。只要说出刚刚哪句话最刺痛你，我们就能从那里开始整理。"

    return (
        "你现在不舒服，不一定是你太敏感，可能是刚刚那段对话里有人越过了你的边界。\n\n"
        "先别急着判断输赢，先看清：你真正想被听见的是什么，对方又把问题推到了哪里。\n\n"
        "下次可以先说：我现在不是要吵赢，我是想把这件事讲清楚，因为这让我很难受。"
    )

def get_comfort_reply(messages: list[dict]) -> str:
    if not _has_valid_api_key():
        return _fallback_reply(messages)

    client = get_llm_client()
    model = get_model_name()
    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages[-8:]:
        role = "assistant" if msg.get("role") == "assistant" else "user"
        content = str(msg.get("content", "")).strip()
        if content:
            llm_messages.append({"role": role, "content": content})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=llm_messages,
            temperature=0.72,
            max_tokens=420,
        )
        return response.choices[0].message.content.strip()
    except (AuthenticationError, APIError, Exception):
        return _fallback_reply(messages)
