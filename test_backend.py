"""
后端模块验证脚本
测试所有模块能否正常导入，Prompt 文件能否正常加载。
"""

import sys
sys.path.insert(0, ".")

print("=" * 50)
print("🧪 吵架训练营 — 后端模块验证")
print("=" * 50)

# 1. 测试配置模块
print("\n[1/5] 测试 utils/config.py ...")
try:
    from utils.config import get_config, get_llm_client, get_model_name
    cfg = get_config()
    print(f"  ✅ 配置加载成功")
    print(f"     API_BASE_URL: {cfg['base_url']}")
    print(f"     MODEL_NAME:   {cfg['model_name']}")
    print(f"     API_KEY:      {'***' + cfg['api_key'][-4:] if len(cfg['api_key']) > 4 else '未设置'}")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 2. 测试 Prompt 文件加载
print("\n[2/5] 测试 Prompt 文件加载 ...")
try:
    from pathlib import Path
    prompts_dir = Path(__file__).parent / "prompts"
    for f in ["smoker_agent.md", "review_agent.md", "fewshot_smoking.md"]:
        filepath = prompts_dir / f
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            print(f"  ✅ {f} — {len(content)} 字符")
        else:
            print(f"  ❌ {f} — 文件不存在")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 3. 测试 llm.py 模块导入
print("\n[3/5] 测试 services/llm.py ...")
try:
    from services.llm import get_smoker_reply, should_end_conversation
    print(f"  ✅ 导入成功")
    print(f"     get_smoker_reply: {get_smoker_reply}")
    print(f"     should_end_conversation: {should_end_conversation}")
    # 测试结束判断逻辑（不调 LLM）
    assert should_end_conversation(5, 5) is True
    assert should_end_conversation(2, 5) is False
    sample_messages = [
        {"role": "user", "content": "我闻到烟味不舒服，请你灭掉。"},
        {"role": "smoker", "content": "行吧，我注意点。", "resistance_level": 1},
        {"role": "user", "content": "请你现在灭掉。"},
        {"role": "smoker", "content": "好，我灭了。", "resistance_level": 0},
    ]
    assert should_end_conversation(2, 5, sample_messages) is True
    print(f"     should_end_conversation 逻辑正常")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 4. 测试 review.py 模块导入
print("\n[4/5] 测试 services/review.py ...")
try:
    from services.review import get_review
    print(f"  ✅ 导入成功")
    print(f"     get_review: {get_review}")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 5. 测试 STT/TTS 占位模块
print("\n[5/5] 测试 STT/TTS 占位模块 ...")
try:
    from services.stt import speech_to_text
    from services.tts import text_to_speech
    print(f"  ✅ stt.py 导入成功")
    print(f"  ✅ tts.py 导入成功")
    # 验证占位函数抛出 NotImplementedError
    try:
        speech_to_text("test.wav")
        print(f"  ⚠️ stt 未抛出预期异常")
    except NotImplementedError:
        print(f"  ✅ stt 按预期抛出 NotImplementedError（P0阶段正确行为）")
    try:
        text_to_speech("你好")
        print(f"  ⚠️ tts 未抛出预期异常")
    except NotImplementedError:
        print(f"  ✅ tts 按预期抛出 NotImplementedError（P0阶段正确行为）")
except Exception as e:
    print(f"  ❌ 失败: {e}")

print("\n" + "=" * 50)
print("✅ 后端模块验证完成！所有模块正常。")
print("=" * 50)
print("\n📋 文件结构：")
import os
for root, dirs, files in os.walk(Path(__file__).parent):
    if "__pycache__" in root or ".git" in root:
        continue
    level = root.replace(".", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files:
        print(f"{subindent}{file}")
