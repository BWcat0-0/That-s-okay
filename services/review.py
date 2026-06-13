"""
非暴力沟通复盘专家 Agent 服务
对话结束后，分析完整对话记录，输出 3 条轻量复盘。
支持 JSON 解析失败重试 + 调试日志。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from utils.config import get_llm_client, get_model_name

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DEBUG_LOG = Path(__file__).parent.parent / "debug_review_output.log"


def _load_prompt(filename: str) -> str:
    """加载 Prompt 文件内容"""
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {filepath}")
    return filepath.read_text(encoding="utf-8")


def _log_debug(message: str):
    """将调试信息写入日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n[{timestamp}]\n{message}\n")


def _parse_json_reply(raw_text: str) -> dict | None:
    """
    尝试从 LLM 原始输出中解析 JSON。
    返回 None 表示解析失败。
    """
    cleaned = raw_text
    cleaned = re.sub(r"^[\s\S]*?```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 正则提取
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 补全缺失的结尾 }
    if cleaned.startswith("{") and cleaned.count("{") > cleaned.count("}"):
        fixed = cleaned
        missing = cleaned.count("{") - cleaned.count("}")
        for _ in range(missing):
            fixed += "\n}"
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    # 修复中文引号：在 JSON 字符串值内部，将 "xxx" 替换为 「xxx」
    # 匹配 "key": "value 包含 "inner" 引号" 这种模式
    if result is None:
        try:
            fixed = re.sub(
                r'(:\s*"[^"]*?)"([^"]*?)"([^"]*?")',
                r'\1「\2」\3',
                cleaned,
            )
            return json.loads(fixed)
        except (json.JSONDecodeError, Exception):
            pass

    return None


def _call_llm(client, model: str, messages: list[dict], max_tokens: int = 1500) -> str:
    """调用 LLM 并返回原始文本"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def get_review(
    conversation: list[dict],
    scenario: str = "公共场所制止抽烟",
) -> dict:
    """
    对完整对话进行复盘分析，输出 3 条复盘内容。
    JSON 解析失败时自动重试一次。
    """
    client = get_llm_client()
    model = get_model_name()

    system_prompt = _load_prompt("review_agent.md")

    # 将对话记录格式化为可读文本
    conversation_text = ""
    for i, msg in enumerate(conversation, 1):
        if msg["role"] == "user":
            conversation_text += f"第{i}轮 - 用户：{msg['content']}\n"
        elif msg["role"] == "smoker":
            conversation_text += f"第{i}轮 - 抽烟者：{msg['content']}\n"

    user_prompt = f"""请对以下对话进行复盘分析：

场景：{scenario}
用户目标：练习表达边界，对公共场所抽烟者表达"我不舒服，请你灭掉"

完整对话记录：
{conversation_text}

请按照系统提示词中的 JSON 格式输出 3 条复盘内容。"""

    # 第一次调用
    raw_text = _call_llm(client, model, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    result = _parse_json_reply(raw_text)

    # 重试
    if result is None:
        _log_debug(f"RAW (1st attempt):\n{raw_text}")

        retry_text = _call_llm(client, model, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": raw_text},
            {"role": "user", "content": (
                "你上面的回复不是合法的 JSON 格式。"
                "请重新输出，必须严格遵守以下要求：\n"
                "1. 只输出一个完整的 JSON 对象\n"
                "2. 不要用 ``` 代码块包裹\n"
                "3. 三个字段 turning_point、better_response、boundary_template 都必须有内容\n\n"
                "正确格式示例：\n"
                '{"turning_point": "你第三轮说...", '
                '"better_response": "这里不能抽烟，请你灭掉。", '
                '"boundary_template": "这里禁止吸烟，我闻到不舒服，请你灭掉。"}'
            )},
        ], max_tokens=1200)

        result = _parse_json_reply(retry_text)
        if result is not None:
            _log_debug(f"RETRY SUCCESS:\n{retry_text}")
        else:
            _log_debug(f"RETRY FAILED:\n{retry_text}")
            result = _get_fallback_review()

    # 确保必要字段存在
    result.setdefault("turning_point", _get_fallback_review()["turning_point"])
    result.setdefault("better_response", _get_fallback_review()["better_response"])
    result.setdefault("boundary_template", _get_fallback_review()["boundary_template"])

    return result


def _get_fallback_review() -> dict:
    """当 LLM 解析失败时的兜底复盘"""
    return {
        "turning_point": (
            "你今天开口表达了，无论语气如何，这都是为自己发声的一步。"
            "每一次开口都是在练习边界的肌肉。"
        ),
        "better_response": "这里不能抽烟，请你灭掉。",
        "boundary_template": "这里禁止吸烟，我闻到烟味不舒服，请你把烟灭掉。",
    }
