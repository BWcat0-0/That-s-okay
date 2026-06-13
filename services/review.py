"""
非暴力沟通复盘专家 Agent 服务
对话结束后，分析完整对话记录，输出 3 条轻量复盘。
"""

import json
import re
from pathlib import Path
from utils.config import get_llm_client, get_model_name

# Prompt 文件路径
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    """加载 Prompt 文件内容"""
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {filepath}")
    return filepath.read_text(encoding="utf-8")


def get_review(
    conversation: list[dict],
    scenario: str = "公共场所制止抽烟",
) -> dict:
    """
    对完整对话进行复盘分析，输出 3 条复盘内容。

    参数:
        conversation: 完整对话记录
            格式 [{"role": "user", "content": "..."}, {"role": "smoker", "content": "..."}]
        scenario: 场景名称

    返回:
        dict:
            - turning_point: 情绪转折点 / 你刚刚做到的事
            - better_response: 可以更稳的一句话（10-20字）
            - boundary_template: 下次可复制的边界模板（事实 + 感受 + 请求）
    """
    client = get_llm_client()
    model = get_model_name()

    # 加载复盘 Prompt
    system_prompt = _load_prompt("review_agent.md")

    # 将对话记录格式化为可读文本
    conversation_text = ""
    for i, msg in enumerate(conversation, 1):
        if msg["role"] == "user":
            conversation_text += f"第{i}轮 - 用户：{msg['content']}\n"
        elif msg["role"] == "smoker":
            conversation_text += f"第{i}轮 - 抽烟者：{msg['content']}\n"

    # 构建消息
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""请对以下对话进行复盘分析：

场景：{scenario}
用户目标：练习表达边界，对公共场所抽烟者表达"我不舒服，请你灭掉"

完整对话记录：
{conversation_text}

请按照系统提示词中的 JSON 格式输出 3 条复盘内容。""",
        },
    ]

    # 调用 LLM（max_tokens 需要足够大，否则智谱 API 可能返回空）
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
    )

    raw_text = response.choices[0].message.content.strip()

    # 解析 JSON 回复
    # 先去掉可能的 markdown 代码块标记 (```json ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                result = _get_fallback_review()
        else:
            result = _get_fallback_review()

    # 确保必要字段存在
    result.setdefault(
        "turning_point",
        "你今天开口表达了，哪怕声音不大，这就是向前迈出的一大步。",
    )
    result.setdefault(
        "better_response",
        "这里不能抽烟，请你灭掉。",
    )
    result.setdefault(
        "boundary_template",
        "这里禁止吸烟，我闻到烟味不舒服，请你把烟灭掉。",
    )

    return result


def _get_fallback_review() -> dict:
    """当 LLM 解析失败时的兜底复盘"""
    return {
        "turning_point": "你今天开口了，这是你为自己发声的一步。继续练习，你会越来越稳。",
        "better_response": "这里不能抽烟，请你灭掉。",
        "boundary_template": "事实 + 感受 + 请求：这里禁止吸烟，我不舒服，请你灭掉。",
    }
