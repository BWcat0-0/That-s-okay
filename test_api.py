"""
API 连通性测试
测试智谱 GLM-5.1 的两个 Agent 能否正常调用
"""
import sys
sys.path.insert(0, ".")

from services.llm import get_smoker_reply
from services.review import get_review

print("=" * 60)
print("API 连通性测试 - 智谱 GLM-5.1")
print("=" * 60)

# 测试1: 抽烟者 Agent
print("\n[测试1] 抽烟者冲突 Agent")
print("-" * 40)

# 模拟：用户第一次制止（只讲规则）
result1 = get_smoker_reply(
    user_message="这里不能抽烟，请你灭掉。",
    history=[],
    round_number=1,
)
print(f"用户说: 这里不能抽烟，请你灭掉。")
print(f"抽烟者: {result1.get('reply')}")
print(f"阻力等级: {result1.get('resistance_level')}")
print(f"是否软化: {result1.get('should_soften')}")

# 模拟：用户表达不舒服（带历史）
print("\n--- 第二轮 ---")
history = [
    {"role": "user", "content": "这里不能抽烟，请你灭掉。"},
    {"role": "smoker", "content": result1.get('reply', '')},
]
result2 = get_smoker_reply(
    user_message="我闻到烟味真的很难受，你能不能不抽了？",
    history=history,
    round_number=2,
)
print(f"用户说: 我闻到烟味真的很难受，你能不能不抽了？")
print(f"抽烟者: {result2.get('reply')}")
print(f"阻力等级: {result2.get('resistance_level')}")
print(f"是否软化: {result2.get('should_soften')}")

# 测试2: 复盘 Agent
print("\n\n[测试2] 非暴力沟通复盘 Agent")
print("-" * 40)

# 构建完整对话记录
conversation = [
    {"role": "user", "content": "那个……不好意思……这里好像不能抽烟……"},
    {"role": "smoker", "content": "关你什么事？我就吸一根。"},
    {"role": "user", "content": "这里是公共场所，有规定的。"},
    {"role": "smoker", "content": "又没人管，你操什么心？"},
    {"role": "user", "content": "我闻到烟味真的不舒服，请你灭掉。"},
    {"role": "smoker", "content": "……行，我灭了。"},
]

review = get_review(conversation)

print("复盘结果：")
print(f"  卡片1-情绪转折: {review.get('turning_point')}")
print(f"  卡片2-更好回应:   {review.get('better_response')}")
print(f"  卡片3-边界模板: {review.get('boundary_template')}")

print("\n" + "=" * 60)
print("API 连通性测试完成！")
print("=" * 60)
