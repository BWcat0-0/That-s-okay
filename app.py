"""
吵架训练营 — Streamlit 前端
纯文字版 P0：首页 → 训练对话 → 复盘卡片
"""

import streamlit as st
from services.llm import get_smoker_reply, select_personality, should_end_conversation
from services.review import get_review

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="吵架训练营",
    page_icon="💬",
    layout="centered",
)

# ============================================================
# 初始化 Session State
# ============================================================
def init_session():
    """确保所有 session_state 变量有初始值"""
    defaults = {
        "page": "home",
        "messages": [],
        "round_number": 1,
        "review": None,
        "smoker_personality": None,
        "_redirect_ready": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_training():
    """重置训练状态，回到首页"""
    st.session_state.page = "home"
    st.session_state.messages = []
    st.session_state.round_number = 1
    st.session_state.review = None
    st.session_state.smoker_personality = None
    st.session_state._redirect_ready = False


MAX_ROUNDS = 5
SCENARIO = "公共场所制止抽烟"


# ============================================================
# 自定义 CSS
# ============================================================
def inject_css():
    st.markdown("""
    <style>
        :root {
            --camp-card-bg: #f6f6f8;
            --camp-card-border: #d7d8df;
            --camp-text: #31333f;
            --camp-muted: #606575;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --camp-card-bg: #1e1e1e;
                --camp-card-border: #3a3a3a;
                --camp-text: #f5f5f5;
                --camp-muted: #b7b7b7;
            }
        }

        /* 首页大标题 */
        .home-title {
            text-align: center;
            font-size: 2.8rem;
            font-weight: 800;
            margin-top: 2rem;
            margin-bottom: 0.5rem;
        }
        .home-subtitle {
            text-align: center;
            font-size: 1.1rem;
            color: var(--camp-muted);
            margin-bottom: 2rem;
        }

        /* 场景卡片 */
        .scenario-card {
            background: var(--camp-card-bg);
            border: 1px solid var(--camp-card-border);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            margin-bottom: 1.5rem;
            color: var(--camp-text);
        }
        .scenario-card .icon {
            font-size: 3rem;
        }
        .scenario-card .label {
            font-size: 1.2rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }

        /* 复盘卡片 */
        .review-card {
            background: var(--camp-card-bg);
            border: 1px solid var(--camp-card-border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            color: var(--camp-text);
        }
        .review-card .card-title {
            font-size: 0.9rem;
            color: var(--camp-muted);
            margin-bottom: 0.5rem;
            font-weight: 650;
        }
        .review-card .card-body {
            font-size: 1.05rem;
            line-height: 1.6;
            color: var(--camp-text);
        }

        /* 训练页顶部提示 */
        .training-hint {
            text-align: center;
            color: var(--camp-muted);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        .training-hint .opponent-line {
            font-size: 1.0rem;
            color: var(--camp-text);
        }

        /* 底部状态栏 */
        .bottom-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            color: var(--camp-muted);
            margin-top: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# 页面：首页
# ============================================================
def render_home():
    st.markdown('<div class="home-title">吵架训练营</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="home-subtitle">我们不教你赢，我们陪你练习第一次说不</div>',
        unsafe_allow_html=True,
    )

    # 场景卡片
    st.markdown("""
    <div class="scenario-card">
        <div class="icon">🚭</div>
        <div class="label">公共场所制止抽烟</div>
        <div style="color:var(--camp-muted);margin-top:0.5rem;">
            有人在餐厅/高铁抽烟，你要练习开口制止
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 开始按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 开始练习", type="primary", use_container_width=True):
            st.session_state.page = "training"
            st.session_state.messages = []
            st.session_state.round_number = 1
            st.session_state.review = None
            st.session_state.smoker_personality = select_personality()
            st.rerun()


# ============================================================
# 页面：训练页
# ============================================================
def render_training():
    # 顶部提示（含人格信息）
    personality = st.session_state.smoker_personality or {}
    personality_name = personality.get("name", "路人")
    personality_avatar = personality.get("avatar", "🚬")
    personality_hook = personality.get("opening_hook", "")

    st.markdown(f"""
    <div class="training-hint">
        🎯 你正在练习：在餐厅/高铁制止他人抽烟<br>
        <span class="opponent-line">
            今天的对手：{personality_avatar} <b>{personality_name}</b> — {personality_hook}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 对话区域：渲染历史消息
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="🙋"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🚬"):
                    st.write(msg["content"])

    # 输入区域（训练结束后隐藏）
    if st.session_state.round_number <= MAX_ROUNDS and st.session_state.review is None:
        user_input = st.chat_input(
            "在这里输入你想说的话...",
            key=f"input_round_{st.session_state.round_number}",
        )

        if user_input:
            # 1. 记录用户消息
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
            })

            # 2. 调用抽烟者 Agent（带加载提示）
            with st.spinner("💭 对方正在输入..."):
                result = get_smoker_reply(
                    user_message=user_input,
                    history=st.session_state.messages[:-1],  # 不包含本条
                    round_number=st.session_state.round_number,
                    max_rounds=MAX_ROUNDS,
                    personality=st.session_state.smoker_personality,
                )

            # 3. 记录抽烟者回复（空回复兜底）
            reply_text = result.get("reply", "").strip()
            if not reply_text:
                reply_text = "……（对方没说话，瞪了你一眼）"
            st.session_state.messages.append({
                "role": "smoker",
                "content": reply_text,
                "resistance_level": result.get("resistance_level", 2),
                "should_soften": result.get("should_soften", False),
                "coach_signal": result.get("coach_signal", ""),
            })
            st.session_state.round_number += 1

            should_finish = should_end_conversation(
                round_number=st.session_state.round_number - 1,
                max_rounds=MAX_ROUNDS,
                messages=st.session_state.messages,
            )

            # 4. 满足结束条件 → 生成复盘 → 先展示最后一轮，再跳转
            if should_finish:
                _finish_training()
                if st.session_state.round_number > MAX_ROUNDS and not st.session_state._redirect_ready:
                    st.session_state._redirect_ready = True
                elif st.session_state.round_number > MAX_ROUNDS:
                    st.session_state._redirect_ready = False
                    st.session_state.page = "review"

            st.rerun()

    # 底部状态栏
    training_done = st.session_state.review is not None

    if training_done:
        st.success("✅ 复盘已生成，点击下方按钮查看")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📊 查看复盘", use_container_width=True, type="primary"):
                st.session_state._redirect_ready = False
                st.session_state.page = "review"
                st.rerun()
    else:
        st.markdown(f"""
        <div class="bottom-bar">
            <span>第 {min(st.session_state.round_number, MAX_ROUNDS)}/{MAX_ROUNDS} 轮</span>
        </div>
        """, unsafe_allow_html=True)

        # 结束训练按钮（至少对话1轮后才显示）
        if len(st.session_state.messages) >= 2:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🏁 结束训练，查看复盘", use_container_width=True):
                    _finish_training()
                    st.session_state.page = "review"
                    st.rerun()



def _finish_training():
    """结束训练，调用复盘 Agent"""
    if st.session_state.review is not None:
        return  # 已经生成过了

    with st.spinner("🧠 正在分析你的表现..."):
        result = get_review(
            conversation=st.session_state.messages,
            scenario=SCENARIO,
        )
    st.session_state.review = result


# ============================================================
# 页面：复盘页
# ============================================================
def render_review():
    st.markdown("## 🎉 训练完成！")
    st.markdown("以下是你的复盘结果：")

    review = st.session_state.review
    if review is None:
        st.warning("复盘数据丢失，请重新开始训练。")
        if st.button("回到首页"):
            reset_training()
            st.rerun()
        return

    # 卡片1：情绪转折点
    st.markdown(f"""
    <div class="review-card">
        <div class="card-title">🎯 你刚刚做到的事</div>
        <div class="card-body">{review.get("turning_point", "")}</div>
    </div>
    """, unsafe_allow_html=True)

    # 卡片2：更好的回应
    st.markdown(f"""
    <div class="review-card">
        <div class="card-title">💪 可以更稳的一句话</div>
        <div class="card-body">{review.get("better_response", "")}</div>
    </div>
    """, unsafe_allow_html=True)

    # 卡片3：边界模板
    st.markdown(f"""
    <div class="review-card">
        <div class="card-title">📋 下次可复制的边界模板</div>
        <div class="card-body">{review.get("boundary_template", "")}</div>
    </div>
    """, unsafe_allow_html=True)

    # 查看对话记录（可折叠）
    with st.expander("📜 查看对话记录"):
        for msg in st.session_state.messages:
            role_label = "🙋 你" if msg["role"] == "user" else "🚬 抽烟者"
            st.markdown(f"**{role_label}**：{msg['content']}")

    # 按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 再来一次", use_container_width=True, type="primary"):
            reset_training()
            st.rerun()
    with col2:
        if st.button("🏠 回到首页", use_container_width=True):
            reset_training()
            st.rerun()


# ============================================================
# 主入口
# ============================================================
def main():
    init_session()
    inject_css()

    page = st.session_state.page

    if page == "home":
        render_home()
    elif page == "training":
        render_training()
    elif page == "review":
        render_review()
    else:
        st.error(f"未知页面: {page}")
        if st.button("回到首页"):
            reset_training()
            st.rerun()


if __name__ == "__main__":
    main()
