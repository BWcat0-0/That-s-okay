"""
抽烟者冲突 Agent 服务
负责调用 LLM 扮演公共场所抽烟者，与用户进行对抗性对话练习。
支持多性格系统 + 话术库注入 + JSON 解析失败重试。
"""

import json
import random
import re
from datetime import datetime
from pathlib import Path
from utils.config import get_llm_client, get_model_name

# Prompt 文件路径
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DEBUG_LOG = Path(__file__).parent.parent / "debug_llm_output.log"


def _load_prompt(filename: str) -> str:
    """加载 Prompt 文件内容"""
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {filepath}")
    return filepath.read_text(encoding="utf-8")


def _load_personality_bank() -> list[dict]:
    """加载人格话术库"""
    filepath = PROMPTS_DIR / "personality_bank.json"
    if not filepath.exists():
        raise FileNotFoundError(f"人格话术库不存在: {filepath}")
    data = json.loads(filepath.read_text(encoding="utf-8"))
    return data["personalities"]


def _log_debug(message: str):
    """将调试信息写入日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n[{timestamp}]\n{message}\n")


def select_personality(personality_id: str | None = None) -> dict:
    """
    随机选择或按 ID 指定抽烟者人格。

    参数:
        personality_id: 可选，指定人格 ID。为 None 时随机选择。

    返回:
        dict: 完整人格数据（name, avatar, phrases, etc.）
    """
    personalities = _load_personality_bank()

    if personality_id is not None:
        for p in personalities:
            if p["id"] == personality_id:
                return p
        print(f"警告：人格 ID '{personality_id}' 不存在，将随机选择。")

    return random.choice(personalities)


def _get_fewshot_for_personality(personality_id: str) -> str:
    """
    从 fewshot 文件中提取当前人格的示例。

    人格 → fewshot 段落映射（基于 fewshot_smoking.md 的 ## 标题）
    """
    fewshot_full = _load_prompt("fewshot_smoking.md")

    id_to_section = {
        "slippery_uncle": "油滑大叔",
        "arrogant_elite": "傲慢精英",
        "victim_player": "委屈无辜型",
        "cold_silent": "冷暴力型",
    }

    section_title = id_to_section.get(personality_id, "油滑大叔")

    pattern = rf"## {re.escape(section_title)}\n(.*?)(?=\n## |\n---\n>|\Z)"
    match = re.search(pattern, fewshot_full, re.DOTALL)

    if match:
        return match.group(1).strip()
    else:
        lines = fewshot_full.split("\n")
        first_example_end = 0
        example_count = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                example_count += 1
                if example_count == 2:
                    first_example_end = i
                    break
        if first_example_end > 0:
            return "\n".join(lines[:first_example_end]).strip()
        return fewshot_full[:500]


def _build_system_prompt(personality: dict) -> str:
    """
    基于人格数据构建完整的 system prompt。
    替换 smoker_agent.md 中的模板占位符。
    """
    template = _load_prompt("smoker_agent.md")

    phrases = personality["phrases"]
    phrases_pressure = "\n".join(f"- {p}" for p in phrases["pressure"])
    phrases_deflect = "\n".join(f"- {p}" for p in phrases["deflect"])
    phrases_soften = "\n".join(f"- {p}" for p in phrases["soften"])
    phrases_concede = "\n".join(f"- {p}" for p in phrases["concede"])
    catchphrases = "、".join(personality.get("catchphrases", []))

    replacements = {
        "{{personality_name}}": personality["name"],
        "{{personality_description}}": personality["description"],
        "{{personality_speaking_style}}": personality["speaking_style"],
        "{{opening_hook}}": personality["opening_hook"],
        "{{phrases_pressure}}": phrases_pressure,
        "{{phrases_deflect}}": phrases_deflect,
        "{{phrases_soften}}": phrases_soften,
        "{{phrases_concede}}": phrases_concede,
        "{{catchphrases}}": catchphrases,
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    fewshot_text = _get_fewshot_for_personality(personality["id"])

    template += f"""

---

## 以下是你之前以"{personality['name']}"身份进行对话的示例，请严格参考这种风格：

{fewshot_text}
"""

    return template


def _parse_json_reply(raw_text: str) -> dict | None:
    """
    尝试从 LLM 原始输出中解析 JSON。
    返回 None 表示解析失败。
    """
    # 步骤1：去掉 markdown 代码块标记
    cleaned = raw_text
    cleaned = re.sub(r"^[\s\S]*?```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # 步骤2：多种方式尝试解析
    # 2a: 直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2b: 正则提取
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 2c: 补全缺失的结尾 }
    if cleaned.startswith("{") and cleaned.count("{") > cleaned.count("}"):
        fixed = cleaned
        missing = cleaned.count("{") - cleaned.count("}")
        for _ in range(missing):
            fixed += "\n}"
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    return None


def _extract_reply_fallback(raw_text: str) -> str:
    """从非 JSON 文本中尽力提取回复内容"""
    if not raw_text or not raw_text.strip():
        return ""

    # 1. 尝试提取完整 JSON 中的 reply 字段
    reply_match = re.search(r'"reply"\s*:\s*"([^"]*)"', raw_text)
    if reply_match:
        text = reply_match.group(1)
        if text.strip():
            return text.strip()

    # 2. 处理截断的 JSON：{"reply": "好吧……我  (缺结尾引号和括号)
    truncated_match = re.search(r'"reply"\s*:\s*"(.+?)$', raw_text)
    if truncated_match:
        text = truncated_match.group(1).strip().rstrip('{').rstrip(',').strip().strip('"')
        if text and len(text) >= 2:
            return text

    # 3. 取第一行非代码块的非空文本
    lines = raw_text.split("\n")
    text_lines = [
        l for l in lines
        if not l.strip().startswith(("```", "{", "}", "//", "/*"))
        and l.strip()
    ]
    if text_lines:
        return text_lines[0][:150]

    # 4. 最后的兜底
    return raw_text.strip()[:150]


def _call_llm(client, model: str, messages: list[dict], max_tokens: int = 500) -> str:
    """调用 LLM 并返回原始文本"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.75,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def get_smoker_reply(
    user_message: str,
    history: list[dict],
    round_number: int = 1,
    max_rounds: int = 5,
    personality: dict | None = None,
) -> dict:
    """
    调用抽烟者 Agent，返回一句反驳回复 + 内部状态。
    如果 JSON 解析失败，自动重试一次（发送纠错指令）。
    """
    client = get_llm_client()
    model = get_model_name()

    if personality is None:
        personality = select_personality()

    system_prompt = _build_system_prompt(personality)

    # 构建消息列表（不含最终用户输入，方便重试复用）
    base_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        if msg["role"] == "user":
            base_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "smoker":
            base_messages.append({"role": "assistant", "content": msg["content"]})

    user_msg_content = f"（当前是第{round_number}轮，共{max_rounds}轮）\n用户说：{user_message}"

    # 第一次调用
    messages = base_messages + [{"role": "user", "content": user_msg_content}]
    raw_text = _call_llm(client, model, messages, max_tokens=500)
    result = _parse_json_reply(raw_text)

    # 重试：解析失败时，让 LLM 修正自己的输出
    if result is None:
        _log_debug(f"PERSONALITY: {personality['name']} ({personality['id']})\n"
                   f"ROUND: {round_number}/{max_rounds}\n"
                   f"USER: {user_message}\n"
                   f"RAW (1st attempt):\n{raw_text}")

        # 根据失败类型选择不同的纠错策略
        if not raw_text or not raw_text.strip():
            # 空白输出 → 重新生成（不是纠错，是重做）
            correction_prompt = (
                "你没有输出任何内容。请按照 JSON 格式输出你的回复。"
                "记住：你正在和用户对话。\n\n"
                "正确格式示例：\n"
                '{"reply": "你的回复", "resistance_level": 2, "should_soften": false}'
            )
        else:
            # 非空白非 JSON → 纠错
            correction_prompt = (
                "你上面的回复不是合法的 JSON 格式。"
                "请重新输出，必须严格遵守以下要求：\n"
                "1. 只输出一行完整的 JSON，不要用 ``` 包裹\n"
                "2. reply 是你对用户说的话（10-25字）\n"
                "3. resistance_level 是数字 0-3\n"
                "4. should_soften 是 true 或 false\n\n"
                "正确格式示例：\n"
                '{"reply": "你的回复", "resistance_level": 2, "should_soften": false}'
            )

        correction_messages = base_messages + [
            {"role": "user", "content": user_msg_content},
            {"role": "assistant", "content": raw_text},
            {"role": "user", "content": correction_prompt},
        ]

        retry_text = _call_llm(client, model, correction_messages, max_tokens=200)
        result = _parse_json_reply(retry_text)

        if result is not None:
            _log_debug(f"RETRY SUCCESS:\n{retry_text}")
        else:
            _log_debug(f"RETRY FAILED:\n{retry_text}")
            fallback_reply = _extract_reply_fallback(raw_text)
            if not fallback_reply or len(fallback_reply) < 2:
                fallback_reply = _extract_reply_fallback(retry_text)
            if not fallback_reply or len(fallback_reply) < 2:
                fallback_reply = "……"
            result = {
                "reply": fallback_reply,
                "resistance_level": 2,
                "should_soften": False,
            }

    # 确保必要字段存在
    result.setdefault("reply", "……")
    result.setdefault("resistance_level", 2)
    result.setdefault("should_soften", False)
    result["personality_id"] = personality["id"]

    return result


def should_end_conversation(round_number: int, max_rounds: int = 5) -> bool:
    """判断对话是否应该结束"""
    return round_number >= max_rounds
