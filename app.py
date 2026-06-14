"""
吵架训练营 — Streamlit 前端
纯文字版 P0：首页 → 训练对话 → 复盘卡片
"""

import base64
import html
from pathlib import Path

import streamlit as st
from services.llm import get_smoker_reply, select_personality, should_end_conversation
from services.parent_agent import get_parent_reply, select_parent_type, should_end_parent_conversation
from services.review import get_review
from services.comfort import get_comfort_reply

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
        "page": "landing",
        "messages": [],
        "round_number": 1,
        "review": None,
        "scenario_type": None,          # "smoking" | "parent"
        "smoker_personality": None,
        "parent_type": None,
        "_redirect_ready": False,
        "comfort_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_training():
    """重置训练状态，回到首页"""
    st.session_state.page = "landing"
    st.session_state.messages = []
    st.session_state.round_number = 1
    st.session_state.review = None
    st.session_state.scenario_type = None
    st.session_state.smoker_personality = None
    st.session_state.parent_type = None
    st.session_state._redirect_ready = False
    st.session_state.comfort_messages = []


MAX_ROUNDS_SMOKING = 5
MAX_ROUNDS_PARENT = 6
SCENARIO_SMOKING = "公共场所制止抽烟"
LANDING_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "dise.png"
HOME_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "huo.png"
SMOKING_INTRO_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "smoking-intro.png"
SMOKING_CHARACTER_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "yanren.png"
SMOKING_PROTAGONIST_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "jinyanzhe.png"
PARENT_INTRO_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "parent-intro.png"
PARENT_CHILD_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "child.png"
PARENT_CHARACTER_IMAGE_PATH = Path(__file__).parent / "assets" / "landing" / "muqin.png"
LANDING_BUTTON_PATHS = {
    "training": Path(__file__).parent / "assets" / "landing" / "xunlianying-cropped.png",
    "examples": Path(__file__).parent / "assets" / "landing" / "bieren-cropped.png",
    "review": Path(__file__).parent / "assets" / "landing" / "fupan-cropped.png",
}
HOME_BUTTON_PATHS = {
    "smoking": Path(__file__).parent / "assets" / "landing" / "baba.png",
    "parent": Path(__file__).parent / "assets" / "landing" / "mama.png",
}


def _image_to_data_uri(path: Path) -> str:
    """Return a CSS-ready data URI for a local image."""
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:image/png;base64,{encoded}"


# ============================================================
# 自定义 CSS
# ============================================================
def inject_css(page: str = "", landing_bg_url: str = "", home_bg_url: str = "", examples_bg_url: str = "", review_bg_url: str = "", comfort_bg_url: str = ""):
    page_css = ""
    if page == "landing":
        page_css = """
        .stApp {
            background: #eee4d2;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: transparent;
        }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none;
        }
        .block-container {
            max-width: none;
            padding: 0;
        }
        """
    elif page == "home":
        page_css = """
        .stApp {
            background-color: #19110d;
            background-image: __HOME_BG_IMAGE__;
            background-size: cover;
            background-position: center bottom;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: transparent;
        }
        .home-entry-stage {
            min-height: 100vh;
            position: relative;
        }
        .home-scenario-button {
            position: absolute;
            display: block;
            border: 0;
            padding: 0;
            background: transparent;
            line-height: 0;
            cursor: pointer;
            filter: drop-shadow(0 0.35rem 0.25rem rgba(0, 0, 0, 0.28));
            transition: transform 120ms ease, filter 120ms ease;
        }
        .home-scenario-button:hover {
            transform: translateY(-0.35%);
            filter: drop-shadow(0 0.46rem 0.32rem rgba(0, 0, 0, 0.34));
        }
        .home-scenario-button img {
            display: block;
            width: 100%;
            height: auto;
            user-select: none;
            -webkit-user-drag: none;
        }
        .home-smoking-button {
            left: -17%;
            top: 12%;
            width: 58%;
        }
        .home-parent-button {
            right: -18%;
            top: 12%;
            width: 56%;
        }
        @media (max-width: 760px) {
            .home-entry-stage {
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                gap: 1rem;
                padding: 1.25rem;
            }
            .home-scenario-button {
                position: static;
                width: min(86vw, 22rem);
                margin: 0 auto;
            }
        }
        """
    elif page == "comfort":
        page_css = """
        .stApp {
            background-color: #eee4d2;
            background-image: linear-gradient(90deg, rgba(24, 20, 16, 0.5), rgba(24, 20, 16, 0.12)), __COMFORT_BG_IMAGE__;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: transparent;
        }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none;
        }
        .block-container {
            max-width: min(58rem, 90vw);
            padding: 7vh 0 8rem;
        }
        .comfort-shell {
            color: rgba(255, 250, 236, 0.92);
        }
        .comfort-nav {
            display: inline-block;
            color: rgba(255, 250, 236, 0.82) !important;
            text-decoration: none !important;
            padding: 0.52rem 0.8rem;
            border: 1px solid rgba(255, 250, 236, 0.2);
            background: rgba(30, 26, 20, 0.28);
            backdrop-filter: blur(8px);
            margin-bottom: 2rem;
        }
        .comfort-title {
            max-width: 42rem;
            margin-bottom: 1.35rem;
        }
        .comfort-title h1 {
            margin: 0 0 0.75rem;
            color: rgba(255, 250, 236, 0.96);
            font-size: clamp(2.4rem, 5.6vw, 5.2rem);
            line-height: 1.05;
            letter-spacing: 0;
            text-shadow: 0 0.22rem 0.8rem rgba(0, 0, 0, 0.42);
        }
        .comfort-title p {
            margin: 0;
            color: rgba(255, 250, 236, 0.76);
            font-size: 1.02rem;
            line-height: 1.75;
        }
        .comfort-panel {
            border: 1px solid rgba(255, 250, 236, 0.2);
            background: rgba(31, 26, 21, 0.42);
            backdrop-filter: blur(12px);
            box-shadow: 0 1rem 2.4rem rgba(0, 0, 0, 0.22);
            padding: 1.1rem;
        }
        .comfort-empty {
            color: rgba(255, 250, 236, 0.72);
            line-height: 1.85;
            padding: 0.6rem 0.2rem 0.2rem;
        }
        .comfort-message {
            border: 1px solid rgba(255, 250, 236, 0.16);
            background: rgba(255, 250, 236, 0.1);
            color: rgba(255, 250, 236, 0.88);
            padding: 0.9rem 1rem;
            margin: 0.75rem 0;
            line-height: 1.75;
        }
        .comfort-message.user {
            margin-left: clamp(1rem, 9vw, 8rem);
            background: rgba(255, 250, 236, 0.16);
        }
        .comfort-message.assistant {
            margin-right: clamp(1rem, 9vw, 8rem);
            background: rgba(24, 20, 16, 0.48);
        }
        .comfort-speaker {
            display: block;
            margin-bottom: 0.25rem;
            color: rgba(255, 250, 236, 0.58);
            font-size: 0.86rem;
            font-weight: 650;
        }
        .stChatInput {
            max-width: min(58rem, 90vw);
            margin: 0 auto;
        }
        .stChatInput textarea {
            background: rgba(255, 250, 236, 0.9) !important;
            color: #211c17 !important;
        }
        @media (max-width: 760px) {
            .block-container {
                padding-top: 4vh;
            }
            .comfort-message.user,
            .comfort-message.assistant {
                margin-left: 0;
                margin-right: 0;
            }
        }
        """
    elif page == "review":
        page_css = """
        .stApp {
            background-color: #16100d;
            background-image: linear-gradient(90deg, rgba(12, 10, 8, 0.82), rgba(12, 10, 8, 0.68)), __REVIEW_BG_IMAGE__;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: transparent;
        }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none;
        }
        .block-container {
            max-width: min(56rem, 88vw);
            padding-top: 12vh;
            padding-bottom: 8vh;
        }
        .block-container h2,
        .block-container p,
        .block-container div,
        .block-container summary {
            color: rgba(255, 250, 236, 0.9);
        }
        .block-container h2 {
            font-size: clamp(2rem, 4vw, 3.3rem);
            letter-spacing: 0;
            text-shadow: 0 0.25rem 0.9rem rgba(0, 0, 0, 0.42);
        }
        .stApp .review-card {
            background: rgba(22, 18, 14, 0.5);
            border: 1px solid rgba(255, 250, 236, 0.2);
            backdrop-filter: blur(10px);
            box-shadow: 0 0.85rem 1.8rem rgba(0, 0, 0, 0.24);
            color: rgba(255, 250, 236, 0.92);
        }
        .stApp .review-card .card-title {
            color: rgba(255, 250, 236, 0.68);
        }
        .stApp .review-card .card-body {
            color: rgba(255, 250, 236, 0.9);
        }
        [data-testid="stExpander"] {
            border-color: rgba(255, 250, 236, 0.22);
            background: rgba(22, 18, 14, 0.42);
            backdrop-filter: blur(10px);
        }
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] p {
            color: rgba(255, 250, 236, 0.86) !important;
        }
        .stButton > button {
            border: 1px solid rgba(255, 250, 236, 0.28);
            background: rgba(255, 250, 236, 0.12);
            color: rgba(255, 250, 236, 0.92);
            box-shadow: 0 0.55rem 1.1rem rgba(0, 0, 0, 0.18);
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
            background: rgba(152, 55, 48, 0.72);
            border-color: rgba(255, 250, 236, 0.22);
        }
        """
    elif page == "examples":
        page_css = """
        .stApp {
            background-color: #eee4d2;
            background-image: linear-gradient(90deg, rgba(58, 41, 27, 0.48), rgba(92, 65, 42, 0.18)), __EXAMPLES_BG_IMAGE__;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: transparent;
        }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none;
        }
        .block-container {
            max-width: none;
            padding: 0;
        }
        .forum-page {
            min-height: 100vh;
            padding: 3.2rem clamp(1.25rem, 4vw, 4.5rem) 4rem;
            color: rgba(255, 250, 236, 0.94);
        }
        .forum-topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2.2rem;
        }
        .forum-back {
            color: rgba(255, 250, 236, 0.86) !important;
            text-decoration: none !important;
            padding: 0.55rem 0.85rem;
            border: 1px solid rgba(255, 250, 236, 0.24);
            background: rgba(92, 66, 43, 0.34);
            backdrop-filter: blur(8px);
        }
        .forum-title {
            max-width: 42rem;
            margin-bottom: 2rem;
        }
        .forum-title h1 {
            margin: 0 0 0.7rem;
            font-size: clamp(2.2rem, 5vw, 4.8rem);
            line-height: 1.05;
            letter-spacing: 0;
            color: rgba(255, 250, 236, 0.96);
            text-shadow: 0 0.2rem 0.8rem rgba(0, 0, 0, 0.42);
        }
        .forum-title p,
        .forum-stat {
            color: rgba(255, 250, 236, 0.72);
            line-height: 1.65;
            font-size: 1.02rem;
        }
        .forum-layout {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(17rem, 0.34fr);
            gap: 1.1rem;
            align-items: start;
        }
        .forum-feed {
            display: grid;
            gap: 0.9rem;
        }
        .forum-post,
        .forum-side {
            border: 1px solid rgba(255, 244, 218, 0.22);
            background: rgba(92, 66, 43, 0.46);
            backdrop-filter: blur(10px);
            box-shadow: 0 0.8rem 1.6rem rgba(0, 0, 0, 0.18);
        }
        .forum-post {
            padding: 1.05rem 1.15rem;
        }
        .forum-post-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.65rem;
            color: rgba(255, 250, 236, 0.62);
            font-size: 0.86rem;
        }
        .forum-tag {
            border: 1px solid rgba(255, 250, 236, 0.18);
            background: rgba(255, 250, 236, 0.08);
            padding: 0.18rem 0.45rem;
        }
        .forum-post h2 {
            margin: 0 0 0.55rem;
            color: rgba(255, 250, 236, 0.96);
            font-size: clamp(1.25rem, 2.1vw, 1.8rem);
            line-height: 1.22;
            letter-spacing: 0;
        }
        .forum-post p {
            margin: 0;
            color: rgba(255, 246, 226, 0.82);
            line-height: 1.7;
        }
        .forum-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 0.9rem;
            color: rgba(255, 246, 226, 0.7);
            font-size: 0.92rem;
        }
        .forum-side {
            padding: 1rem;
            position: sticky;
            top: 1.25rem;
        }
        .forum-side h3 {
            margin: 0 0 0.8rem;
            color: rgba(255, 250, 236, 0.92);
            font-size: 1.1rem;
        }
        .forum-side ul {
            margin: 0;
            padding-left: 1.1rem;
            color: rgba(255, 250, 236, 0.7);
            line-height: 1.8;
        }
        @media (max-width: 860px) {
            .forum-layout {
                grid-template-columns: 1fr;
            }
            .forum-side {
                position: static;
            }
        }
        """
    st.markdown("""
    <style>
        __LANDING_PAGE_CSS__

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

        /* 初始界面 */
        .landing-stage {
            position: relative;
            width: min(100vw, calc(100vh * 1.528));
            height: min(100vh, calc(100vw / 1.528));
            margin: 0 auto;
            overflow: hidden;
            background-color: #eee4d2;
            background-image: __LANDING_BG_IMAGE__;
            background-size: 100% 100%;
            background-position: center;
            background-repeat: no-repeat;
        }
        .landing-image-button {
            position: absolute;
            display: block;
            border: 0;
            padding: 0;
            background: transparent;
            line-height: 0;
            cursor: pointer;
            filter: drop-shadow(0 0.25rem 0.15rem rgba(0, 0, 0, 0.16));
            transition: transform 120ms ease, filter 120ms ease;
        }
        .landing-image-button:hover {
            transform: translateY(-0.35%);
            filter: drop-shadow(0 0.34rem 0.22rem rgba(0, 0, 0, 0.22));
        }
        .landing-image-button img {
            display: block;
            width: 100%;
            height: auto;
            user-select: none;
            -webkit-user-drag: none;
        }
        .landing-training {
            left: 72.5%;
            top: 52.4%;
            width: 22.8%;
        }
        .landing-examples {
            left: 57.8%;
            top: 73.6%;
            width: 18.4%;
        }
        .landing-review {
            left: 81.5%;
            top: 84.2%;
            width: 15.4%;
        }
        @media (max-aspect-ratio: 1.05/1) {
            .landing-stage {
                width: 100vw;
                height: calc(100vw / 1.528);
                margin-top: max(0px, calc((100vh - (100vw / 1.528)) / 2));
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
    """.replace("__LANDING_PAGE_CSS__", page_css).replace(
        "__LANDING_BG_IMAGE__",
        f'url("{landing_bg_url}")' if landing_bg_url else "none",
    ).replace(
        "__HOME_BG_IMAGE__",
        f'url("{home_bg_url}")' if home_bg_url else "none",
    ).replace(
        "__EXAMPLES_BG_IMAGE__",
        f'url("{examples_bg_url}")' if examples_bg_url else "none",
    ).replace(
        "__REVIEW_BG_IMAGE__",
        f'url("{review_bg_url}")' if review_bg_url else "none",
    ).replace(
        "__COMFORT_BG_IMAGE__",
        f'url("{comfort_bg_url}")' if comfort_bg_url else "none",
    ), unsafe_allow_html=True)


# ============================================================
# 页面：初始界面
# ============================================================
def render_landing():
    training_uri = _image_to_data_uri(LANDING_BUTTON_PATHS["training"])
    examples_uri = _image_to_data_uri(LANDING_BUTTON_PATHS["examples"])
    review_uri = _image_to_data_uri(LANDING_BUTTON_PATHS["review"])

    st.markdown(f"""
    <div class="landing-stage">
        <a class="landing-image-button landing-training" href="?entry=training" aria-label="吵架训练营">
            <img src="{training_uri}" alt="" draggable="false">
        </a>
        <a class="landing-image-button landing-examples" href="?entry=examples" aria-label="看看别人怎么吵">
            <img src="{examples_uri}" alt="" draggable="false">
        </a>
        <a class="landing-image-button landing-review" href="?entry=comfort" aria-label="吵后复盘区">
            <img src="{review_uri}" alt="" draggable="false">
        </a>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 页面：首页
# ============================================================
def render_home():
    smoking_uri = _image_to_data_uri(HOME_BUTTON_PATHS["smoking"])
    parent_uri = _image_to_data_uri(HOME_BUTTON_PATHS["parent"])

    st.markdown(f"""
    <div class="home-entry-stage">
        <a class="home-scenario-button home-smoking-button" href="?scenario=smoking" aria-label="公共场所制止抽烟">
            <img src="{smoking_uri}" alt="" draggable="false">
        </a>
        <a class="home-scenario-button home-parent-button" href="?scenario=parent" aria-label="向父母表达情绪">
            <img src="{parent_uri}" alt="" draggable="false">
        </a>
    </div>
    """, unsafe_allow_html=True)


def render_examples():
    posts = [
        {
            "tag": "校园食堂",
            "meta": "大学城 · 18分钟前 · 128 条回应",
            "title": "绿色鹅腿到底还能不能吃？我和窗口阿姨吵到后厨都出来了",
            "body": "楼主说鹅腿切开是灰绿色，窗口说是卤料颜色。评论区有人贴实验室同学的判断，也有人说先别上纲上线，重点是食堂该不该当场留样。",
            "actions": "边界表达 42 · 证据整理 19 · 需要冷静版话术",
        },
        {
            "tag": "街边小摊",
            "meta": "夜市入口 · 42分钟前 · 76 条回应",
            "title": "小贩说我找茬，我只是问油反复用了几天",
            "body": "买烤冷面时看到油桶颜色很深，摊主反问「不吃就别挡路」。大家在帮楼主拆解：怎样问食品安全问题，既不被带成态度争吵，也能保留投诉证据。",
            "actions": "小贩冲突 31 · 食品安全 27 · 一句话模板",
        },
        {
            "tag": "火车卧铺",
            "meta": "K字头列车 · 1小时前 · 203 条回应",
            "title": "车上买不到卫生巾，弄脏床单却被要求高价赔偿",
            "body": "乘务员说按污染赔偿，同行乘客说女生自己该准备。帖子里有人整理了铁路服务流程，也有人在写不羞耻、不退让的沟通脚本。",
            "actions": "公共服务 66 · 性别处境 54 · 投诉路径",
        },
        {
            "tag": "合租生活",
            "meta": "城中村合租 · 2小时前 · 51 条回应",
            "title": "室友半夜外放短视频，我说了三次后她说我太敏感",
            "body": "问题从噪音变成了「你是不是不好相处」。评论区正在讨论怎么把对话拉回事实：时间、音量、影响和明确请求。",
            "actions": "边界感 22 · 合租公约 14 · 不内耗说法",
        },
    ]

    post_html = "".join(
        '<article class="forum-post">'
        f'<div class="forum-post-meta"><span class="forum-tag">{html.escape(post["tag"])}</span><span>{html.escape(post["meta"])}</span></div>'
        f'<h2>{html.escape(post["title"])}</h2>'
        f'<p>{html.escape(post["body"])}</p>'
        f'<div class="forum-actions"><span>{html.escape(post["actions"])}</span><span>收藏复盘</span><span>进入围观</span></div>'
        '</article>'
        for post in posts
    )

    forum_html = (
        '<main class="forum-page">'
        '<div class="forum-topbar">'
        '<a class="forum-back" href="?entry=landing">回到入口</a>'
        '<div class="forum-stat">今日新增 47 个冲突样本</div>'
        '</div>'
        '<section class="forum-title">'
        '<h1>看看别人怎么吵</h1>'
        '<p>把日常生活里的不舒服、被推诿和不合理收费放到台面上。这里不是围观谁赢，而是收集每一种可以更稳地说出口的方式。</p>'
        '</section>'
        '<section class="forum-layout">'
        f'<div class="forum-feed">{post_html}</div>'
        '<aside class="forum-side">'
        '<h3>正在被讨论</h3>'
        '<ul>'
        '<li>先问事实，还是先表达感受</li>'
        '<li>对方反咬态度时怎么拉回来</li>'
        '<li>留证据但不升级冲突</li>'
        '<li>适合复制的边界句式</li>'
        '</ul>'
        '</aside>'
        '</section>'
        '</main>'
    )
    st.markdown(forum_html, unsafe_allow_html=True)

# ============================================================
# 页面：训练页
# ============================================================
def render_training():
    scenario_type = st.session_state.scenario_type

    if scenario_type == "parent":
        _render_parent_training()
    else:
        _render_smoking_training()


def _inject_smoking_intro_scene(
    intro_path: Path = SMOKING_INTRO_IMAGE_PATH,
    protagonist_path: Path = SMOKING_PROTAGONIST_IMAGE_PATH,
    character_path: Path = SMOKING_CHARACTER_IMAGE_PATH,
    protagonist_extra_class: str = "",
    character_extra_class: str = "",
):
    intro_uri = _image_to_data_uri(intro_path)
    character_uri = _image_to_data_uri(character_path)
    protagonist_uri = _image_to_data_uri(protagonist_path)
    protagonist_class = f"smoking-protagonist {protagonist_extra_class}".strip()
    character_class = f"smoking-character {character_extra_class}".strip()

    st.markdown(f"""
    <div class="smoking-intro-scene" aria-hidden="true"></div>
    <img class="{protagonist_class}" src="{protagonist_uri}" alt="" draggable="false">
    <img class="{character_class}" src="{character_uri}" alt="" draggable="false">
    <style>
        .stApp {{
            background: #050403;
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: transparent;
        }}
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {{
            display: none;
        }}
        .smoking-intro-scene {{
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)),
                url("{intro_uri}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            animation: smokingDim 3.2s ease 1.8s forwards;
        }}
        .smoking-character,
        .smoking-protagonist {{
            position: fixed;
            bottom: 4vh;
            width: min(25vw, 24rem);
            max-height: 82vh;
            object-fit: contain;
            z-index: 1;
            pointer-events: none;
            opacity: 0;
            animation: smokingCharacterIn 1.6s ease 5s forwards;
            filter: drop-shadow(0 0.7rem 0.35rem rgba(0, 0, 0, 0.45));
        }}
        .smoking-character {{
            right: 6vw;
            transform: translateX(2rem);
        }}
        .smoking-protagonist {{
            left: 34vw;
            transform: translateX(-2rem);
        }}
        .smoking-protagonist.parent-child {{
            left: 30vw;
            width: min(24vw, 23rem);
        }}
        .smoking-character.parent-mother {{
            right: 6vw;
            width: min(25vw, 24rem);
        }}
        .block-container {{
            max-width: none;
            padding: 9vh 0 8rem 5vw;
            position: relative;
            z-index: 2;
        }}
        .block-container [data-testid="stVerticalBlock"] {{
            align-items: flex-start;
        }}
        .block-container [data-testid="stElementContainer"]:not(:has(.smoking-intro-scene)),
        .block-container [data-testid="stChatMessage"] {{
            width: min(48vw, 48rem);
            margin-left: 0;
            margin-right: auto;
            opacity: 0;
            animation: smokingTextIn 1.6s ease 5s forwards;
        }}
        .training-hint,
        .bottom-bar,
        [data-testid="stChatMessage"],
        [data-testid="stChatMessage"] * {{
            color: rgba(255, 250, 238, 0.94) !important;
            text-shadow: 0 0.12rem 0.45rem rgba(0, 0, 0, 0.78);
        }}
        .training-hint .opponent-line {{
            color: rgba(255, 250, 238, 0.96) !important;
        }}
        [data-testid="stChatMessage"] {{
            background: rgba(12, 10, 8, 0.42);
            border: 1px solid rgba(255, 250, 238, 0.2);
            border-radius: 0.65rem;
            backdrop-filter: blur(2px);
        }}
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] div {{
            color: rgba(255, 250, 238, 0.94) !important;
        }}
        .smoking-message-flow {{
            position: fixed;
            left: 5vw;
            top: 14vh;
            width: min(38vw, 42rem);
            height: 60vh;
            z-index: 6;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            overflow-y: auto;
            overscroll-behavior-y: contain;
            scroll-snap-type: y mandatory;
            scroll-padding-block: 0;
            padding-right: 0.35rem;
            opacity: 0;
            animation: smokingTextIn 1.6s ease 5s forwards;
            pointer-events: auto;
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 250, 238, 0.45) rgba(10, 8, 6, 0.2);
        }}
        .smoking-message-flow::-webkit-scrollbar {{
            width: 0.45rem;
        }}
        .smoking-message-flow::-webkit-scrollbar-track {{
            background: rgba(10, 8, 6, 0.2);
            border-radius: 999px;
        }}
        .smoking-message-flow::-webkit-scrollbar-thumb {{
            background: rgba(255, 250, 238, 0.45);
            border-radius: 999px;
        }}
        .smoking-flow-item {{
            min-height: 60vh;
            scroll-snap-align: start;
            scroll-snap-stop: always;
            display: flex;
            align-items: center;
            padding: 1.1rem 1.2rem;
            border-radius: 0.75rem;
            background: rgba(10, 8, 6, 0.5);
            border: 1px solid rgba(255, 250, 238, 0.2);
            color: rgba(255, 250, 238, 0.95);
            box-shadow: 0 0.45rem 1rem rgba(0, 0, 0, 0.24);
            backdrop-filter: blur(2px);
            text-shadow: 0 0.12rem 0.35rem rgba(0, 0, 0, 0.82);
            font-size: clamp(1.05rem, 1.25vw, 1.35rem);
            line-height: 1.55;
        }}
        .smoking-flow-role {{
            display: inline-block;
            margin-right: 0.45rem;
            color: rgba(255, 246, 218, 0.98);
            font-weight: 760;
        }}
        .smoking-flow-content {{
            color: rgba(255, 250, 238, 0.95);
            font-weight: 520;
        }}
        .smoking-review-link {{
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 2147483647;
            min-width: 9.5rem;
            padding: 0.85rem 1.2rem;
            border-radius: 0.45rem;
            background: rgba(255, 250, 238, 0.96);
            border: 1px solid rgba(35, 28, 20, 0.2);
            color: #1d1813 !important;
            font-size: 1.06rem;
            font-weight: 780;
            text-align: center;
            text-decoration: none !important;
            box-shadow: 0 0.55rem 1.3rem rgba(0, 0, 0, 0.32);
            opacity: 1;
            animation: none;
        }}
        .smoking-review-link:hover {{
            background: rgba(255, 250, 238, 1);
            color: #1d1813 !important;
        }}
        .block-container [data-testid="stElementContainer"]:has(.visual-review-button-anchor) {{
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 2147483646;
            width: 9.5rem;
            height: 0;
        }}
        .block-container [data-testid="stElementContainer"]:has(.visual-review-button-anchor) + [data-testid="stElementContainer"] {{
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 2147483647;
            width: 9.5rem;
        }}
        .block-container [data-testid="stElementContainer"]:has(.visual-review-button-anchor) + [data-testid="stElementContainer"] button {{
            min-width: 9.5rem;
            padding: 0.85rem 1.2rem;
            border-radius: 0.45rem;
            background: rgba(255, 250, 238, 0.96);
            border: 1px solid rgba(35, 28, 20, 0.2);
            color: #1d1813 !important;
            font-size: 1.06rem;
            font-weight: 780;
            box-shadow: 0 0.55rem 1.3rem rgba(0, 0, 0, 0.32);
        }}
        [data-testid="stChatInput"] {{
            width: min(48vw, 48rem);
            left: 5vw;
            right: auto;
            opacity: 0;
            animation: smokingTextIn 1.6s ease 5s forwards;
        }}
        @keyframes smokingDim {{
            from {{
                filter: brightness(1);
            }}
            to {{
                filter: brightness(0.34);
            }}
        }}
        @keyframes smokingTextIn {{
            from {{
                opacity: 0;
                transform: translateY(0.75rem);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        @keyframes smokingCharacterIn {{
            from {{
                opacity: 0;
                transform: translateX(2rem);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}
        @media (max-width: 820px) {{
            .block-container {{
                padding: 8vh 1rem 8rem;
            }}
            .block-container [data-testid="stElementContainer"]:not(:has(.smoking-intro-scene)),
            .block-container [data-testid="stChatMessage"],
            [data-testid="stChatInput"] {{
                width: calc(100vw - 2rem);
                left: 1rem;
            }}
            .smoking-character,
            .smoking-protagonist {{
                width: 34vw;
                opacity: 0.78;
            }}
            .smoking-character {{
                right: 2vw;
            }}
            .smoking-protagonist {{
                left: 28vw;
            }}
            .smoking-protagonist.parent-child {{
                left: 22vw;
                width: 36vw;
            }}
            .smoking-character.parent-mother {{
                right: 1vw;
                width: 36vw;
            }}
            .smoking-message-flow {{
                left: 1rem;
                top: 15vh;
                width: calc(100vw - 2rem);
                height: 54vh;
            }}
            .smoking-flow-item {{
                min-height: 54vh;
                font-size: 0.95rem;
                padding: 0.8rem 0.9rem;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)


def _render_smoking_training():
    """抽烟场景训练页"""
    _inject_smoking_intro_scene()
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

    _render_smoking_chat_history()

    max_rounds = MAX_ROUNDS_SMOKING
    if st.session_state.round_number <= max_rounds and st.session_state.review is None:
        user_input = st.chat_input(
            "在这里输入你想说的话...",
            key=f"input_round_{st.session_state.round_number}",
        )

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.spinner("💭 对方正在输入..."):
                result = get_smoker_reply(
                    user_message=user_input,
                    history=st.session_state.messages[:-1],
                    round_number=st.session_state.round_number,
                    max_rounds=max_rounds,
                    personality=st.session_state.smoker_personality,
                )

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
                max_rounds=max_rounds,
                messages=st.session_state.messages,
            )

            if should_finish:
                _finish_training()
                if st.session_state.round_number > max_rounds and not st.session_state._redirect_ready:
                    st.session_state._redirect_ready = True
                elif st.session_state.round_number > max_rounds:
                    st.session_state._redirect_ready = False
                    st.session_state.page = "review"

            st.rerun()

    _render_bottom_bar(max_rounds)


def _render_smoking_chat_history():
    """Render smoking conversation context as a visible left-side message flow."""
    role_labels = {"user": "“你：”", "smoker": "“对方：”"}
    flow_items = []
    for msg in st.session_state.messages:
        role = msg.get("role")
        if role not in role_labels:
            continue
        label = role_labels[role]
        content = html.escape(msg.get("content", ""))
        flow_items.append(
            f'<div class="smoking-flow-item {role}">'
            f'<span class="smoking-flow-role">{label}</span>'
            f'<span class="smoking-flow-content">{content}</span>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="smoking-message-flow" aria-live="polite">
        {''.join(flow_items)}
    </div>
    """, unsafe_allow_html=True)


def _render_parent_training():
    """父母场景训练页"""
    _inject_smoking_intro_scene(
        intro_path=PARENT_INTRO_IMAGE_PATH,
        protagonist_path=PARENT_CHILD_IMAGE_PATH,
        character_path=PARENT_CHARACTER_IMAGE_PATH,
        protagonist_extra_class="parent-child",
        character_extra_class="parent-mother",
    )
    parent_type = st.session_state.parent_type or {}
    parent_name = parent_type.get("name", "父母")
    parent_avatar = parent_type.get("avatar", "👨‍👩‍👧")
    opening_hook = parent_type.get("opening_hook", "")

    st.markdown(f"""
    <div class="training-hint">
        🎯 你正在练习：在被否定时完整表达自己的情绪<br>
        <span class="opponent-line">
            {parent_avatar} <b>{parent_name}</b> — {opening_hook}
        </span>
    </div>
    """, unsafe_allow_html=True)

    _render_parent_chat_history()

    max_rounds = MAX_ROUNDS_PARENT
    if st.session_state.round_number <= max_rounds and st.session_state.review is None:
        user_input = st.chat_input(
            "在这里输入你想对父母说的话...",
            key=f"input_round_{st.session_state.round_number}",
        )

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.spinner("💭 父母正在回应..."):
                result = get_parent_reply(
                    user_message=user_input,
                    history=st.session_state.messages[:-1],
                    round_number=st.session_state.round_number,
                    max_rounds=max_rounds,
                    parent_type=st.session_state.parent_type,
                )

            reply_text = result.get("reply", "").strip()
            if not reply_text:
                reply_text = "……（沉默，没有回应）"
            st.session_state.messages.append({
                "role": "parent",
                "content": reply_text,
                "resistance_level": result.get("resistance_level", 2),
                "should_soften": result.get("should_soften", False),
                "coach_signal": result.get("coach_signal", ""),
            })
            st.session_state.round_number += 1

            should_finish = should_end_parent_conversation(
                round_number=st.session_state.round_number - 1,
                max_rounds=max_rounds,
                messages=st.session_state.messages,
            )

            if should_finish:
                _finish_training()
                if st.session_state.round_number > max_rounds and not st.session_state._redirect_ready:
                    st.session_state._redirect_ready = True
                elif st.session_state.round_number > max_rounds:
                    st.session_state._redirect_ready = False
                    st.session_state.page = "review"

            st.rerun()

    _render_bottom_bar(max_rounds)


def _render_parent_chat_history():
    """Render parent conversation context with the same visual flow as smoking."""
    role_labels = {"user": "“你：”", "parent": "“对方：”"}
    flow_items = []
    for msg in st.session_state.messages:
        role = msg.get("role")
        if role not in role_labels:
            continue
        label = role_labels[role]
        content = html.escape(msg.get("content", ""))
        flow_items.append(
            f'<div class="smoking-flow-item {role}">'
            f'<span class="smoking-flow-role">{label}</span>'
            f'<span class="smoking-flow-content">{content}</span>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="smoking-message-flow" aria-live="polite">
        {''.join(flow_items)}
    </div>
    """, unsafe_allow_html=True)


def _render_chat_history(opponent_role: str, opponent_avatar: str):
    """渲染对话历史"""
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="🙋"):
                st.write(msg["content"])
        elif msg["role"] == opponent_role:
            with st.chat_message("assistant", avatar=opponent_avatar):
                st.write(msg["content"])


def _render_visual_review_button(training_done: bool):
    """Use a real Streamlit button so review generation keeps session context."""
    st.markdown('<span class="visual-review-button-anchor"></span>', unsafe_allow_html=True)
    if st.button("查看复盘", key=f"visual_review_{st.session_state.scenario_type}_{training_done}"):
        if not training_done:
            _finish_training()
        st.session_state._redirect_ready = False
        st.session_state.page = "review"
        st.rerun()


def _render_bottom_bar(max_rounds: int):
    """渲染底部状态栏和结束按钮"""
    training_done = st.session_state.review is not None
    is_smoking_page = st.session_state.scenario_type == "smoking"
    is_visual_scene = st.session_state.scenario_type in ("smoking", "parent")

    if training_done:
        if is_visual_scene:
            _render_visual_review_button(training_done=True)
        else:
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
            <span>第 {min(st.session_state.round_number, max_rounds)}/{max_rounds} 轮</span>
        </div>
        """, unsafe_allow_html=True)

        if is_visual_scene:
            _render_visual_review_button(training_done=False)
        elif len(st.session_state.messages) >= 2:
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
    if not st.session_state.messages:
        st.session_state.review = {
            "turning_point": "这次没有读到对话记录。请先完成至少一轮对话，再点击查看复盘。",
            "better_response": "先完成一轮对话，再生成复盘。",
            "boundary_template": "我先说出刚才发生的事，再说我的感受和请求。",
        }
        return

    scenario_type = st.session_state.scenario_type
    if scenario_type == "parent":
        scenario_name = "向父母表达情绪"
        opponent_label = "父母"
        prompt_file = "parent_review_agent.md"
    else:
        scenario_name = SCENARIO_SMOKING
        opponent_label = "抽烟者"
        prompt_file = "review_agent.md"

    with st.spinner("🧠 正在分析你的表现..."):
        result = get_review(
            conversation=st.session_state.messages,
            scenario=scenario_name,
            opponent_label=opponent_label,
            system_prompt_file=prompt_file,
        )
    st.session_state.review = result


# ============================================================
# 页面：吵后复盘区
# ============================================================
def render_comfort():
    st.markdown("""
    <div class="comfort-shell">
        <a class="comfort-nav" href="?entry=landing">回到入口</a>
        <div class="comfort-title">
            <h1>吵后复盘区</h1>
            <p>把刚刚那场争执放在这里。这个空间会先接住你的情绪，再帮你把关系、边界和需求慢慢理清楚。</p>
        </div>
        <div class="comfort-panel">
    """, unsafe_allow_html=True)

    if not st.session_state.comfort_messages:
        st.markdown("""
        <div class="comfort-empty">
            可以直接写：发生了什么、你最卡住的一句话、你现在最难受的点。<br>
            我会用关系视角帮你拆开：你委屈在哪里、对方越界在哪里、下一句怎样说更稳。
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.comfort_messages:
        role = msg.get("role", "assistant")
        speaker = "你" if role == "user" else "关系安抚"
        css_role = "user" if role == "user" else "assistant"
        content = html.escape(msg.get("content", "")).replace("\n", "<br>")
        st.markdown(f"""
        <div class="comfort-message {css_role}">
            <span class="comfort-speaker">{speaker}</span>
            {content}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    user_input = st.chat_input("把刚刚吵完的事说给我听...")
    if user_input:
        st.session_state.comfort_messages.append({"role": "user", "content": user_input})
        with st.spinner("正在帮你把情绪和关系线索理清..."):
            reply = get_comfort_reply(st.session_state.comfort_messages)
        st.session_state.comfort_messages.append({"role": "assistant", "content": reply})
        st.rerun()


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
        opponent_label = "🚬 抽烟者" if st.session_state.scenario_type == "smoking" else "👨‍👩‍👧 父母"
        for msg in st.session_state.messages:
            role_label = "🙋 你" if msg["role"] == "user" else opponent_label
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


def _get_query_value(name: str):
    if hasattr(st, "query_params"):
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    params = st.experimental_get_query_params()
    values = params.get(name, [])
    return values[0] if values else None


def _clear_query_params():
    if hasattr(st, "query_params"):
        st.query_params.clear()
    else:
        st.experimental_set_query_params()


def _start_smoking_scenario():
    st.session_state.scenario_type = "smoking"
    st.session_state.page = "training"
    st.session_state.messages = []
    st.session_state.round_number = 1
    st.session_state.review = None
    st.session_state.smoker_personality = select_personality()
    st.session_state.parent_type = None


def _start_parent_scenario():
    st.session_state.scenario_type = "parent"
    st.session_state.page = "training"
    st.session_state.messages = []
    st.session_state.round_number = 1
    st.session_state.review = None
    st.session_state.parent_type = select_parent_type()
    st.session_state.smoker_personality = None


def _consume_landing_entry():
    action = _get_query_value("action")
    if action == "finish_review":
        _finish_training()
        st.session_state.page = "review"
        _clear_query_params()
        return
    if action == "show_review":
        st.session_state.page = "review"
        _clear_query_params()
        return

    entry = _get_query_value("entry")
    if entry == "training":
        st.session_state.page = "home"
        _clear_query_params()
        return
    if entry == "examples":
        st.session_state.page = "examples"
        _clear_query_params()
        return
    if entry == "comfort":
        st.session_state.page = "comfort"
        _clear_query_params()
        return
    if entry == "landing":
        reset_training()
        _clear_query_params()
        return

    scenario = _get_query_value("scenario")
    if scenario == "smoking":
        _start_smoking_scenario()
        _clear_query_params()
    elif scenario == "parent":
        _start_parent_scenario()
        _clear_query_params()


# ============================================================
# 主入口
# ============================================================
def main():
    init_session()
    _consume_landing_entry()
    page = st.session_state.page
    landing_bg_url = _image_to_data_uri(LANDING_IMAGE_PATH) if page == "landing" else ""
    home_bg_url = _image_to_data_uri(HOME_IMAGE_PATH) if page == "home" else ""
    examples_bg_url = _image_to_data_uri(LANDING_IMAGE_PATH) if page == "examples" else ""
    review_bg_url = _image_to_data_uri(SMOKING_INTRO_IMAGE_PATH) if page == "review" else ""
    comfort_bg_url = _image_to_data_uri(LANDING_IMAGE_PATH) if page == "comfort" else ""
    inject_css(page, landing_bg_url, home_bg_url, examples_bg_url, review_bg_url, comfort_bg_url)

    if page == "landing":
        render_landing()
    elif page == "home":
        render_home()
    elif page == "examples":
        render_examples()
    elif page == "comfort":
        render_comfort()
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
