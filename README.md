# 吵架训练营 💬

我们不教你赢，我们陪你练习第一次说不。

一个基于 LLM 的边界表达练习工具 — 你和 AI 扮演的"公共场所抽烟者"进行对话，练习在冲突中清晰表达自己的边界。对话结束后，非暴力沟通复盘专家会给出轻量、不说教的反馈。

---

## 工作流程

```
首页 → 训练对话（1-5轮）→ 复盘卡片（3张）
```

1. **首页** — 选择场景，点击开始
2. **训练页** — 打字和抽烟者对话，最多5轮
3. **复盘页** — 查看3张卡片：你做到的事 / 更稳的说法 / 边界模板

---

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Streamlit |
| LLM | 智谱 GLM-5.1（两个 Agent 并行） |
| 抽烟者 Agent | 系统提示词驱动，动态阻力调节 |
| 复盘 Agent | 非暴力沟通框架，结构化 JSON 输出 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入智谱 API Key
```

`.env` 内容：

```
API_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
API_KEY=your-api-key-here
MODEL_NAME=GLM-5.1
```

### 3. 启动

```bash
streamlit run app.py
```

打开浏览器访问 `http://localhost:8501`。

---

## 目录结构

```
argue-training-camp/
├── app.py                  # Streamlit 主入口（3个页面）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── .gitignore
│
├── services/
│   ├── llm.py              # 抽烟者冲突 Agent（GLM-5.1）
│   ├── review.py           # 非暴力沟通复盘 Agent
│   ├── stt.py              # 语音转文字（预留）
│   └── tts.py              # 文字转语音（预留）
│
├── prompts/
│   ├── smoker_agent.md     # 抽烟者系统提示词
│   ├── review_agent.md     # 复盘专家系统提示词
│   └── fewshot_smoking.md  # Few-shot 示例
│
├── utils/
│   └── config.py           # LLM 客户端 & 配置加载
│
├── test_api.py             # API 连通性测试
├── test_e2e.py             # 端到端流程测试
└── test_backend.py         # 后端单元测试
```

---

## 两个 Agent

### 🚬 抽烟者冲突 Agent

- 扮演公共场所抽烟的人
- 根据用户表达的强弱动态调整阻力：狡辩 → 松动 → 让步
- 不人身攻击、不升级冲突、不骂人
- 每次回复不超过2句话

### 🧠 复盘专家 Agent

- 非暴力沟通框架
- 输出3条轻量复盘：
  - 🎯 **turning_point** — 你在哪个时刻表达了边界
  - 💪 **better_response** — 一句更稳更简短的表达
  - 📋 **boundary_template** — 事实 + 感受 + 请求模板
- 不说教、不鸡汤、不分析人格

---

## 运行测试

```bash
# API 连通性测试
python test_api.py

# 端到端流程测试
python test_e2e.py

# 后端单元测试
python test_backend.py
```

---

## 许可

MIT
