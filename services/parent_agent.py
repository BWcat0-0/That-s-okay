"""
父母冲突 Agent 服务
负责调用 LLM 扮演东亚父母角色，与用户进行情绪否定对话练习。
支持 5 种父母类型 + 话术库注入 + JSON 解析失败重试 + 调试日志。

基于抽烟场景的所有教训：
- max_tokens=800 起步（父母更啰嗦）
- JSON 解析失败重试机制从第一天就内置
- debug 日志从第一天就写入
- 离线 fallback 完整实现 6 种策略路径
"""

import json
import random
import re
from datetime import datetime
from pathlib import Path
from openai import APIError, AuthenticationError
from utils.config import get_config, get_llm_client, get_model_name

# Prompt 文件路径
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DEBUG_LOG = Path(__file__).parent.parent / "debug_parent_output.log"


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


def _load_parent_bank() -> list[dict]:
    """加载父母类型话术库"""
    filepath = PROMPTS_DIR / "parent_personality_bank.json"
    if not filepath.exists():
        raise FileNotFoundError(f"父母类型话术库不存在: {filepath}")
    data = json.loads(filepath.read_text(encoding="utf-8"))
    return data["parent_types"]


def _log_debug(message: str):
    """将调试信息写入日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n[{timestamp}]\n{message}\n")


def select_parent_type(parent_type_id: str | None = None) -> dict:
    """
    随机选择或按 ID 指定父母类型。

    参数:
        parent_type_id: 可选，指定父母类型 ID。为 None 时随机选择。

    返回:
        dict: 完整父母类型数据（name, avatar, phrases, etc.）
    """
    parent_types = _load_parent_bank()

    if parent_type_id is not None:
        for pt in parent_types:
            if pt["id"] == parent_type_id:
                return pt
        print(f"警告：父母类型 ID '{parent_type_id}' 不存在，将随机选择。")

    return random.choice(parent_types)


def _get_fewshot_for_parent(parent_type_id: str) -> str:
    """
    从 fewshot 文件中提取当前父母类型的示例。

    父母类型 → fewshot 段落映射（基于 fewshot_parent.md 的 ## 标题）
    """
    fewshot_full = _load_prompt("fewshot_parent.md")

    id_to_section = {
        "strict_director": "严厉教导型",
        "lecture_preacher": "说教大道理型",
        "sacrifice_binder": "牺牲绑架型",
        "dismissive_cold": "冷淡轻视型",
        "blame_reflector": "反躬自省型",
    }

    section_title = id_to_section.get(parent_type_id, "严厉教导型")

    # 提取目标段落到下一个 ## 标题之前
    pattern = rf"## {re.escape(section_title)}\n(.*?)(?=\n## |\n---\n|\Z)"
    match = re.search(pattern, fewshot_full, re.DOTALL)

    if match:
        return match.group(1).strip()
    else:
        # Fallback: 返回文件中前 800 个字符作为通用参考
        return fewshot_full[:800]


def _build_system_prompt(parent_type: dict) -> str:
    """
    基于父母类型数据构建完整的 system prompt。
    替换 parent_agent.md 中的模板占位符。
    """
    template = _load_prompt("parent_agent.md")

    phrases = parent_type["phrases"]
    phrases_negate = "\n".join(f"- {p}" for p in phrases["negate_emotion"])
    phrases_moral = "\n".join(f"- {p}" for p in phrases["moral_bind"])
    phrases_blame = "\n".join(f"- {p}" for p in phrases["blame_shift"])
    phrases_dismiss = "\n".join(f"- {p}" for p in phrases["dismiss"])
    phrases_soften = "\n".join(f"- {p}" for p in phrases["soften_slightly"])
    phrases_acknowledge = "\n".join(f"- {p}" for p in phrases["acknowledge"])
    catchphrases = "、".join(parent_type.get("catchphrases", []))

    replacements = {
        "{{parent_type_name}}": parent_type["name"],
        "{{parent_type_description}}": parent_type["description"],
        "{{parent_type_speaking_style}}": parent_type["speaking_style"],
        "{{opening_hook}}": parent_type["opening_hook"],
        "{{subtext}}": parent_type.get("subtext", ""),
        "{{phrases_negate_emotion}}": phrases_negate,
        "{{phrases_moral_bind}}": phrases_moral,
        "{{phrases_blame_shift}}": phrases_blame,
        "{{phrases_dismiss}}": phrases_dismiss,
        "{{phrases_soften_slightly}}": phrases_soften,
        "{{phrases_acknowledge}}": phrases_acknowledge,
        "{{catchphrases}}": catchphrases,
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    fewshot_text = _get_fewshot_for_parent(parent_type["id"])

    template += f"""

---

## 以下是你之前以"{parent_type['name']}"身份进行对话的示例，请严格参考这种风格：

{fewshot_text}
"""

    return template


def _parse_json_reply(raw_text: str) -> dict | None:
    """
    尝试从 LLM 原始输出中解析 JSON。
    多级解析：去 markdown → 正则提取 → 补全括号 → 中文引号修复。
    返回 None 表示解析失败。
    """
    cleaned = raw_text
    # 步骤1：去掉 markdown 代码块标记
    cleaned = re.sub(r"^[\s\S]*?```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # 步骤2a：直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 步骤2b：正则提取第一个完整 JSON 对象
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 步骤2c：补全缺失的结尾 }
    if cleaned.startswith("{") and cleaned.count("{") > cleaned.count("}"):
        fixed = cleaned
        missing = cleaned.count("{") - cleaned.count("}")
        for _ in range(missing):
            fixed += "\n}"
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    # 步骤2d：修复中文引号 —— 在 JSON 字符串值内部的双引号
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


def _extract_reply_fallback(raw_text: str) -> str:
    """从非 JSON 文本中尽力提取回复内容（兜底）"""
    if not raw_text or not raw_text.strip():
        return ""

    # 1. 尝试提取完整 JSON 中的 reply 字段
    reply_match = re.search(r'"reply"\s*:\s*"([^"]*)"', raw_text)
    if reply_match:
        text = reply_match.group(1)
        if text.strip():
            return text.strip()

    # 2. 处理截断的 JSON
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
        return text_lines[0][:200]

    # 4. 最后的兜底
    return raw_text.strip()[:200]


def _infer_coach_signal(user_message: str, result: dict) -> str:
    """LLM 未返回 coach_signal 时，用规则判断用户表达的成熟度。"""
    text = user_message.strip()

    attack_words = ("从来都不", "你根本不", "你们从来不", "你知不知道",
                    "你懂什么", "你闭嘴", "你好意思说", "你说什么")
    feeling_words = ("难过", "难受", "委屈", "丢脸", "伤心", "失望",
                     "不开心", "崩溃", "害怕", "累", "疲惫")
    need_words = ("需要你", "想你", "希望", "能不能", "可不可以",
                  "我只是想", "我想要", "我需要", "听我说", "看见")
    weak_words = ("可能", "也许", "不知道", "算了", "没用的", "我知道没用")

    # 用户表达了"需要"——最高成熟度
    if any(word in text for word in need_words) and any(word in text for word in feeling_words):
        return "用户完整表达了感受+需求，可松动至看见"
    # 用户表达了感受
    if any(word in text for word in feeling_words):
        return "用户表达了真实感受，可开始松动"
    # 用户攻击——会触发父母反弹
    if any(word in text for word in attack_words):
        return "用户进入了指责模式，父母可能反弹回道德绑架"
    # 用户偏弱
    if any(word in text for word in weak_words):
        return "用户表达偏弱，可继续施压以促使更坚定"
    # 用户只在讲事
    return "用户主要讲事情未表达感受，继续否定情绪"


def _build_offline_parent_reply(
    user_message: str,
    round_number: int,
    parent_type: dict,
) -> dict:
    """
    API 不可用时的本地规则兜底，保证 demo 闭环可跑。
    用规则引擎判断用户表达成熟度，从 6 种策略中选择。
    """
    coach_signal = _infer_coach_signal(user_message, {"resistance_level": 2})
    phrases = parent_type.get("phrases", {})

    # 根据用户表达成熟度选择策略
    if "指责" in coach_signal:
        bucket = "moral_bind"
        resistance = 3
        should_soften = False
    elif "完整表达了感受+需求" in coach_signal:
        bucket = "acknowledge"
        resistance = 0
        should_soften = True
    elif "真实感受" in coach_signal:
        # 第3轮以上且用户表达了感受 → 开始松动
        if round_number >= 3:
            bucket = "soften_slightly"
            resistance = 1
            should_soften = True
        else:
            bucket = "negate_emotion"
            resistance = 2
            should_soften = False
    elif "偏弱" in coach_signal:
        bucket = "negate_emotion"
        resistance = 3
        should_soften = False
    elif round_number >= 4:
        # 第4轮以上，不管用户说什么，给点松动
        bucket = "dismiss"
        resistance = 2
        should_soften = False
    else:
        bucket = "negate_emotion"
        resistance = 2
        should_soften = False

    options = phrases.get(bucket) or phrases.get("negate_emotion") or ["为你好才说你。"]
    reply = options[(round_number - 1) % len(options)]

    return {
        "reply": reply,
        "resistance_level": resistance,
        "should_soften": should_soften,
        "coach_signal": coach_signal,
        "parent_type_id": parent_type["id"],
        "offline_fallback": True,
    }


def _call_llm(client, model: str, messages: list[dict], max_tokens: int = 800) -> str:
    """调用 LLM 并返回原始文本"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.75,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def get_parent_reply(
    user_message: str,
    history: list[dict],
    round_number: int = 1,
    max_rounds: int = 6,
    parent_type: dict | None = None,
) -> dict:
    """
    调用父母 Agent，返回父母的回应 + 内部状态。
    如果 JSON 解析失败，自动重试一次（发送纠错指令）。
    """
    client = get_llm_client()
    model = get_model_name()

    if parent_type is None:
        parent_type = select_parent_type()

    if not _has_valid_api_key():
        return _build_offline_parent_reply(user_message, round_number, parent_type)

    system_prompt = _build_system_prompt(parent_type)

    # 构建消息列表（不含最终用户输入，方便重试复用）
    base_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        if msg["role"] == "user":
            base_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "parent":
            base_messages.append({"role": "assistant", "content": msg["content"]})

    user_msg_content = (
        f"（当前是第{round_number}轮，共{max_rounds}轮）\n"
        f"孩子说：{user_message}"
    )

    # 第一次调用
    messages = base_messages + [{"role": "user", "content": user_msg_content}]
    try:
        raw_text = _call_llm(client, model, messages, max_tokens=800)
    except (AuthenticationError, APIError, Exception) as exc:
        _log_debug(
            f"PARENT LLM CALL FAILED, USING OFFLINE FALLBACK\n"
            f"PARENT TYPE: {parent_type['name']} ({parent_type['id']})\n"
            f"ROUND: {round_number}/{max_rounds}\n"
            f"USER: {user_message}\n"
            f"ERROR: {type(exc).__name__}: {exc}"
        )
        return _build_offline_parent_reply(user_message, round_number, parent_type)

    result = _parse_json_reply(raw_text)

    # 重试：解析失败时，让 LLM 修正自己的输出
    if result is None:
        _log_debug(
            f"PARENT TYPE: {parent_type['name']} ({parent_type['id']})\n"
            f"ROUND: {round_number}/{max_rounds}\n"
            f"USER: {user_message}\n"
            f"RAW (1st attempt):\n{raw_text}"
        )

        # 根据失败类型选择不同的纠错策略
        if not raw_text or not raw_text.strip():
            correction_prompt = (
                "你没有输出任何内容。请按照 JSON 格式输出你的回复。"
                "记住：你正在和孩子对话。\n\n"
                "正确格式示例：\n"
                '{"reply": "你的回复", "resistance_level": 2, "should_soften": false, '
                '"coach_signal": "孩子表达了感受但没提需求"}'
            )
        else:
            correction_prompt = (
                "你上面的回复不是合法的 JSON 格式。"
                "请重新输出，必须严格遵守以下要求：\n"
                "1. 只输出一行完整的 JSON，不要用 ``` 包裹\n"
                "2. reply 是你对孩子说的话（1-3句话）\n"
                "3. resistance_level 是数字 0-3\n"
                "4. should_soften 是 true 或 false\n"
                "5. 如果引用孩子的话，用「」括起来，不要用英文双引号 \"\n\n"
                "正确格式示例：\n"
                '{"reply": "你的回复", "resistance_level": 2, "should_soften": false, '
                '"coach_signal": "孩子表达了感受但没提需求"}'
            )

        correction_messages = base_messages + [
            {"role": "user", "content": user_msg_content},
            {"role": "assistant", "content": raw_text if raw_text else ""},
            {"role": "user", "content": correction_prompt},
        ]

        try:
            retry_text = _call_llm(client, model, correction_messages, max_tokens=300)
        except (AuthenticationError, APIError, Exception) as exc:
            _log_debug(
                f"PARENT LLM RETRY FAILED, USING OFFLINE FALLBACK\n"
                f"PARENT TYPE: {parent_type['name']} ({parent_type['id']})\n"
                f"ROUND: {round_number}/{max_rounds}\n"
                f"ERROR: {type(exc).__name__}: {exc}"
            )
            return _build_offline_parent_reply(user_message, round_number, parent_type)

        result = _parse_json_reply(retry_text)

        if result is not None:
            _log_debug(f"RETRY SUCCESS:\n{retry_text}")
        else:
            _log_debug(f"RETRY FAILED:\n{retry_text}")
            # 尝试从两次输出中提取 reply
            fallback_reply = _extract_reply_fallback(raw_text)
            if not fallback_reply or len(fallback_reply) < 2:
                fallback_reply = _extract_reply_fallback(retry_text)
            if not fallback_reply or len(fallback_reply) < 2:
                fallback_reply = "……"
            result = {
                "reply": fallback_reply,
                "resistance_level": 2,
                "should_soften": False,
                "coach_signal": _infer_coach_signal(user_message, {"resistance_level": 2}),
            }

    # 确保必要字段存在
    result.setdefault("reply", "……")
    result.setdefault("resistance_level", 2)
    result.setdefault("should_soften", False)
    result.setdefault("coach_signal", _infer_coach_signal(user_message, result))
    result["parent_type_id"] = parent_type["id"]

    return result


def should_end_parent_conversation(
    round_number: int,
    max_rounds: int = 6,
    messages: list[dict] | None = None,
) -> bool:
    """
    判断亲子对话是否应该结束。

    规则：
    1. 达到最大回合数 → 结束
    2. 父母阻力降到 0-1 且用户表达了完整感受+需求 → 结束
    """
    if round_number >= max_rounds:
        return True

    if not messages:
        return False

    parent_messages = [msg for msg in messages if msg.get("role") == "parent"]
    user_messages = [msg for msg in messages if msg.get("role") == "user"]
    if len(parent_messages) < 2 or len(user_messages) < 2:
        return False

    last_parent = parent_messages[-1]
    last_two_parents = parent_messages[-2:]
    last_two_users = user_messages[-2:]

    # 父母连续两轮低阻力
    low_resistance = all(
        msg.get("resistance_level", 2) <= 1
        for msg in last_two_parents
    )

    # 用户表达了感受+需求
    need_words = ("需要你", "想你", "希望你", "我只是想", "我需要", "听我说")
    feeling_words = ("难过", "难受", "委屈", "丢脸", "伤心", "失望")
    expressed_feelings = any(
        any(word in msg.get("content", "") for word in feeling_words)
        for msg in last_two_users
    )
    expressed_needs = any(
        any(word in msg.get("content", "") for word in need_words)
        for msg in last_two_users
    )

    # 父母真正"看见"了（resistance 0）
    parent_acknowledged = last_parent.get("resistance_level", 2) == 0 or any(
        word in last_parent.get("content", "")
        for word in ("对不起", "我不好", "你说吧", "我不骂你", "以后你跟我说",
                     "我没问你好不好受", "是妈不对", "是爸不好")
    )

    return low_resistance and (expressed_feelings or expressed_needs) and parent_acknowledged
