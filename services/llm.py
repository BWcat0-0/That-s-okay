"""
抽烟者冲突 Agent 服务
负责调用 LLM 扮演公共场所抽烟者，与用户进行对抗性对话练习。
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


def get_smoker_reply(
    user_message: str,
    history: list[dict],
    round_number: int = 1,
    max_rounds: int = 5,
) -> dict:
    """
    调用抽烟者 Agent，返回一句反驳回复 + 内部状态。

    参数:
        user_message: 用户本轮发言（文字）
        history: 对话历史，格式 [{"role": "user", "content": "..."}, {"role": "smoker", "content": "..."}]
        round_number: 当前轮数（1-5）
        max_rounds: 总轮数上限

    返回:
        dict:
            - reply: Agent 的回复文字（展示给用户）
            - resistance_level: 阻力等级（0-3）
            - should_soften: 是否应该在下轮降低阻力
    """
    client = get_llm_client()
    model = get_model_name()

    # 加载 Prompt
    system_prompt = _load_prompt("smoker_agent.md")
    fewshot_text = _load_prompt("fewshot_smoking.md")

    # 构建消息列表
    messages = [
        {
            "role": "system",
            "content": system_prompt
            + "\n\n---\n\n以下是你之前的对话示例，请严格参考这种风格：\n\n"
            + fewshot_text,
        },
    ]

    # 添加对话历史
    for msg in history:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "smoker":
            messages.append({"role": "assistant", "content": msg["content"]})

    # 添加用户本轮发言，附带轮数信息
    messages.append({
        "role": "user",
        "content": f"（当前是第{round_number}轮，共{max_rounds}轮）\n用户说：{user_message}",
    })

    # 调用 LLM
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.85,  # 稍微高一点，增加回复多样性
        max_tokens=300,
    )

    raw_text = response.choices[0].message.content.strip()

    # 解析 JSON 回复
    try:
        # 尝试直接解析
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # 如果 LLM 返回了额外文字，尝试提取 JSON 部分
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                # 实在解析不了，做兜底处理
                result = {
                    "reply": raw_text[:100],
                    "resistance_level": 2,
                    "should_soften": False,
                }
        else:
            result = {
                "reply": raw_text[:100],
                "resistance_level": 2,
                "should_soften": False,
            }

    # 确保必要字段存在
    result.setdefault("reply", "……")
    result.setdefault("resistance_level", 2)
    result.setdefault("should_soften", False)

    return result


def should_end_conversation(round_number: int, max_rounds: int = 5) -> bool:
    """判断对话是否应该结束"""
    return round_number >= max_rounds
