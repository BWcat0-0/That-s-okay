"""
非暴力沟通复盘专家 Agent 服务
对话结束后，分析完整对话记录，输出 3 条轻量复盘。
支持 JSON 解析失败重试 + 调试日志。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from openai import APIError, AuthenticationError
from utils.config import get_config, get_llm_client, get_model_name

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DEBUG_LOG = Path(__file__).parent.parent / "debug_review_output.log"


def _has_valid_api_key() -> bool:
    """判断是否配置了看起来可用的 API key。"""
    api_key = get_config().get("api_key", "").strip()
    return bool(api_key and api_key != "your-api-key-here")


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
    opponent_label: str = "抽烟者",
    user_goal: str = "",
    system_prompt_file: str = "review_agent.md",
) -> dict:
    """
    对完整对话进行复盘分析，输出 3 条复盘内容。
    JSON 解析失败时自动重试一次。

    参数:
        conversation: 对话记录列表
        scenario: 场景名称
        opponent_label: 对手角色标签（"抽烟者" / "父母"）
        user_goal: 用户目标描述，为空时自动根据 opponent_label 生成
        system_prompt_file: 系统提示词文件名（默认 review_agent.md）
    """
    if not _has_valid_api_key():
        return _get_fallback_review(conversation, opponent_label)

    client = get_llm_client()
    model = get_model_name()

    system_prompt = _load_prompt(system_prompt_file)

    # 默认用户目标
    if not user_goal:
        if opponent_label == "父母":
            user_goal = ("练习在被至亲否定情绪时，完整表达自己的感受和需求，"
                         "不因「为你好」而自我怀疑或压抑")
        else:
            user_goal = "练习表达边界，对公共场所抽烟者表达「我不舒服，请你灭掉」"

    # 将对话记录格式化为可读文本
    conversation_text = ""
    for i, msg in enumerate(conversation, 1):
        if msg["role"] == "user":
            conversation_text += f"第{i}轮 - 用户：{msg['content']}\n"
        elif msg["role"] in ("smoker", "parent"):
            metadata = []
            if "resistance_level" in msg:
                metadata.append(f"阻力={msg['resistance_level']}")
            if msg.get("coach_signal"):
                metadata.append(f"训练信号={msg['coach_signal']}")
            metadata_text = f"（{'；'.join(metadata)}）" if metadata else ""
            conversation_text += f"第{i}轮 - {opponent_label}{metadata_text}：{msg['content']}\n"

    user_prompt = f"""请对以下对话进行复盘分析：

场景：{scenario}
用户目标：{user_goal}
复盘语气：像朋友递一句具体反馈，不要像老师打分。避免「对话僵住了」「你还没……」「你应该……」这类审判感表达。

完整对话记录：
{conversation_text}

请按照系统提示词中的 JSON 格式输出 3 条复盘内容。"""

    # 第一次调用
    try:
        raw_text = _call_llm(client, model, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
    except (AuthenticationError, APIError, Exception) as exc:
        _log_debug(f"REVIEW LLM CALL FAILED, USING FALLBACK\nERROR: {type(exc).__name__}: {exc}")
        return _get_fallback_review(conversation, opponent_label)
    result = _parse_json_reply(raw_text)

    # 重试
    if result is None:
        _log_debug(f"RAW (1st attempt):\n{raw_text}")

        try:
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
        except (AuthenticationError, APIError, Exception) as exc:
            _log_debug(f"REVIEW LLM RETRY FAILED, USING FALLBACK\nERROR: {type(exc).__name__}: {exc}")
            return _get_fallback_review(conversation, opponent_label)

        result = _parse_json_reply(retry_text)
        if result is not None:
            _log_debug(f"RETRY SUCCESS:\n{retry_text}")
        else:
            _log_debug(f"RETRY FAILED:\n{retry_text}")
            result = _get_fallback_review(conversation, opponent_label)

    # 确保必要字段存在
    fallback = _get_fallback_review(conversation, opponent_label)
    result.setdefault("turning_point", fallback["turning_point"])
    result.setdefault("better_response", fallback["better_response"])
    result.setdefault("boundary_template", fallback["boundary_template"])

    return result


def _get_fallback_review(conversation: list[dict] | None = None, opponent_label: str = "抽烟者") -> dict:
    """当 LLM 解析失败时的兜底复盘"""
    user_messages = [
        msg.get("content", "")
        for msg in (conversation or [])
        if msg.get("role") == "user"
    ]
    first = user_messages[0] if user_messages else "这里不能抽烟"
    last = user_messages[-1] if user_messages else "请你把烟灭掉"

    if opponent_label == "父母":
        # 父母场景的兜底复盘
        feeling_words = ("难过", "难受", "委屈", "丢脸", "伤心", "失望")
        had_feeling = any(any(word in msg for word in feeling_words) for msg in user_messages)
        if had_feeling:
            turning_point = (
                f"你开口说「{first[:18]}」时已经在表达感受了。"
                "后面你越说越清楚自己需要什么——这就是进步。"
            )
        else:
            turning_point = (
                f"你开头说了「{first[:18]}」。"
                "如果能加入「我很难过」「我很委屈」这样的词，父母更可能停下来听。"
            )
        return {
            "turning_point": turning_point,
            "better_response": "我知道你为我好，但我现在真的很难过，我需要你听我说。",
            "boundary_template": "当你「为你好」来否定我的时候，我感到很难过，我需要你理解我不是在抱怨，我只是需要你听我说。",
        }

    # 抽烟场景的兜底复盘（保持原有逻辑）
    direct_words = ("有病", "滚", "傻", "贱", "垃圾", "毛病")
    had_attack = any(any(word in msg for word in direct_words) for msg in user_messages)
    if had_attack:
        turning_point = (
            f"你开头已经敢说「{first[:18]}」。后面有点跑到指责上了，"
            "如果把重点收回到烟味和请求，对方更难转移话题。"
        )
    else:
        turning_point = (
            f"你开头说到「{first[:18]}」时已经把话题摆出来了。"
            f"后面这句「{last[:18]}」更接近可执行请求，可以再短一点。"
        )

    return {
        "turning_point": turning_point,
        "better_response": "这里烟味让我不舒服，请灭掉。",
        "boundary_template": "这里禁止吸烟，我闻到烟味不舒服，请你把烟灭掉。",
    }
