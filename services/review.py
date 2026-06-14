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


def _clip(text: str, limit: int = 24) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + "……"


def _format_conversation_turns(conversation: list[dict], opponent_label: str) -> str:
    """Format user/opponent pairs as one dialogue turn for review accuracy."""
    lines: list[str] = []
    turn = 1
    has_user_in_turn = False

    for msg in conversation or []:
        role = msg.get("role")
        content = str(msg.get("content", "")).strip()
        if not content:
            continue

        if role == "user":
            if has_user_in_turn:
                turn += 1
            lines.append(f"第{turn}轮 - 用户：{content}")
            has_user_in_turn = True
            continue

        if role in ("smoker", "parent"):
            metadata = []
            if "resistance_level" in msg:
                metadata.append(f"阻力={msg['resistance_level']}")
            if msg.get("coach_signal"):
                metadata.append(f"训练信号={msg['coach_signal']}")
            metadata_text = f"（{'；'.join(metadata)}）" if metadata else ""
            lines.append(f"第{turn}轮 - {opponent_label}{metadata_text}：{content}")
            if has_user_in_turn:
                turn += 1
                has_user_in_turn = False

    return "\n".join(lines)


def _mentions_real_user_input(text: str, conversation: list[dict]) -> bool:
    body = str(text or "")
    for msg in conversation or []:
        if msg.get("role") != "user":
            continue
        content = " ".join(str(msg.get("content", "")).split())
        if not content:
            continue
        probes = {content, _clip(content, 18), _clip(content, 12)}
        for probe in probes:
            probe = probe.replace("……", "")
            if len(probe) >= 4 and probe in body:
                return True
    return False


def _ground_review_result(result: dict, fallback: dict, conversation: list[dict]) -> dict:
    """Ensure the most important review card is grounded in actual user input."""
    grounded = dict(result or {})
    if not _mentions_real_user_input(grounded.get("turning_point", ""), conversation):
        grounded["turning_point"] = fallback["turning_point"]
    for key in ("better_response", "boundary_template"):
        if not str(grounded.get(key, "")).strip():
            grounded[key] = fallback[key]
    return grounded


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

    # 将用户和对手的一来一回格式化为同一轮，避免复盘误读轮数。
    conversation_text = _format_conversation_turns(conversation, opponent_label)

    user_prompt = f"""请对以下对话进行复盘分析：

场景：{scenario}
用户目标：{user_goal}
复盘语气：像朋友递一句具体反馈，不要像老师打分。避免「对话僵住了」「你还没……」「你应该……」这类审判感表达。

完整对话记录：
{conversation_text}

硬性要求：
1. 复盘必须紧贴上面的真实对话记录，至少引用 1 句用户原话，最好也提到 1 句对方回应。
2. 不允许编造用户没有说过的话、没有发生的轮次、没有出现的结局。
3. 如果用户表达很短，也要围绕这几句短输入分析，不要套用通用模板。
4. 轮数以「用户+对方」为一轮，必须和上面的记录一致。

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
    result = _ground_review_result(result, fallback, conversation)

    return result


def _get_fallback_review(conversation: list[dict] | None = None, opponent_label: str = "抽烟者") -> dict:
    """当 LLM 不可用时，也尽量基于真实输入生成复盘。"""
    conversation = conversation or []
    user_messages = [
        str(msg.get("content", "")).strip()
        for msg in conversation
        if msg.get("role") == "user" and str(msg.get("content", "")).strip()
    ]
    opponent_messages = [
        str(msg.get("content", "")).strip()
        for msg in conversation
        if msg.get("role") in ("smoker", "parent") and str(msg.get("content", "")).strip()
    ]

    if not user_messages:
        return {
            "turning_point": "这次没有记录到你的具体输入，所以还不能做真实复盘。下次先把你说出口的第一句话留下来，复盘会更准。",
            "better_response": "我想先把刚才发生的事说清楚。",
            "boundary_template": "我先说事实和感受，再说我希望你怎么做。",
        }

    first = user_messages[0]
    last = user_messages[-1]
    last_opponent = opponent_messages[-1] if opponent_messages else ""
    first_q = _clip(first)
    last_q = _clip(last)
    opponent_q = _clip(last_opponent)

    feeling_words = ("难过", "难受", "委屈", "生气", "不舒服", "害怕", "尴尬", "失望", "烦")
    request_words = ("请", "能不能", "可以", "希望", "别", "不要", "停", "灭", "听我说")
    had_feeling = any(any(word in msg for word in feeling_words) for msg in user_messages)
    had_request = any(any(word in msg for word in request_words) for msg in user_messages)

    if opponent_label == "父母":
        focus = "你已经把情绪放进对话里了" if had_feeling else "你说出了立场，但感受还可以再早一点出现"
        if last_opponent:
            opponent_part = f"对方最后回「{opponent_q}」，说明他们还在自己的逻辑里。"
        else:
            opponent_part = "这段记录里还没有对方回应，所以重点先放在你的表达上。"
        turning_point = (
            f"你开头说「{first_q}」，最后说到「{last_q}」，{focus}。"
            f"{opponent_part}下次可以把事实、感受和请求放在同一句里。"
        )
        if had_request:
            better = f"我听到你的意思了，但我也想把「{last_q}」说完。"
        else:
            better = "我现在很难过，我需要你先听我说完。"
        template = "我知道你有你的想法，但这件事让我很难受，请先听我说完。"
    else:
        focus = "你已经在提出请求" if had_request else "你把不舒服说出来了，但请求还可以更明确"
        if last_opponent:
            opponent_part = f"对方回「{opponent_q}」，是在转移或抵抗。"
        else:
            opponent_part = "这段记录里还没有对方回应，所以先复盘你的开口方式。"
        turning_point = (
            f"你开头说「{first_q}」，后面说到「{last_q}」，{focus}。"
            f"{opponent_part}更稳的方向是少解释、直接说影响和请求。"
        )
        if "烟" in last or "抽" in last or "灭" in last:
            better = "这里烟味让我不舒服，请你现在灭掉。"
        else:
            better = f"我想说的是「{last_q}」，请你现在停一下。"
        template = "这里影响到我了，我不舒服，请你现在停下。"

    return {
        "turning_point": turning_point,
        "better_response": better,
        "boundary_template": template,
    }
