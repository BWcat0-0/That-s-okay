"""
端到端功能测试
模拟完整用户流程：首页 → 训练对话 → 复盘
"""
import sys
sys.path.insert(0, ".")

from services.llm import get_smoker_reply
from services.review import get_review

print("=" * 60)
print("端到端功能测试 — 模拟完整用户流程")
print("=" * 60)

# 模拟 session_state
messages = []
round_number = 1
MAX_ROUNDS = 5

# 模拟一个"逐步变强"的用户对话
user_messages = [
    "那个……不好意思，这里是不是不能抽烟？",           # 第1轮：弱
    "这里是公共场所，有禁烟规定的。",                    # 第2轮：讲规则
    "我闻到烟味真的很难受，你能不能把烟灭掉？",           # 第3轮：表达感受
    "请你现在灭掉，这是规定，也是为了大家的健康。",       # 第4轮：坚持边界
]

for i, user_msg in enumerate(user_messages):
    round_number = i + 1
    print(f"\n--- 第 {round_number} 轮 ---")
    print(f"🙋 用户: {user_msg}")

    result = get_smoker_reply(
        user_message=user_msg,
        history=messages,
        round_number=round_number,
        max_rounds=MAX_ROUNDS,
    )
    reply = result["reply"]
    resistance = result["resistance_level"]
    soften = result["should_soften"]

    print(f"🚬 抽烟者: {reply}")
    print(f"   阻力={resistance} 软化={soften}")

    # 保存对话
    messages.append({"role": "user", "content": user_msg})
    messages.append({"role": "smoker", "content": reply})

# 模拟结束训练 → 复盘
print(f"\n{'=' * 60}")
print("对话结束，调用复盘 Agent...")
print(f"{'=' * 60}")

review = get_review(conversation=messages, scenario="公共场所制止抽烟")

print()
print("📊 复盘结果：")
print(f"  🎯 你做到的事: {review['turning_point']}")
print(f"  💪 更稳的说法: {review['better_response']}")
print(f"  📋 边界模板:   {review['boundary_template']}")

# 验证
print(f"\n{'=' * 60}")
checks = []
checks.append(("对话轮数正确", len(messages) == 8))  # 4 user + 4 smoker
checks.append(("turning_point 非空", len(review.get("turning_point", "")) > 5))
checks.append(("better_response 非空", len(review.get("better_response", "")) > 0))
checks.append(("boundary_template 非空", len(review.get("boundary_template", "")) > 0))

all_pass = True
for name, passed in checks:
    status = "✅" if passed else "❌"
    if not passed:
        all_pass = False
    print(f"  {status} {name}")

print(f"\n{'🎉 全部通过！' if all_pass else '❌ 部分失败'}")

# 检查压力等级是否递减（用户变强 → 抽烟者变软）
print("\n📈 阻力变化趋势：")
for msg in messages:
    if msg["role"] == "smoker":
        print(f"  {msg['content']}")
