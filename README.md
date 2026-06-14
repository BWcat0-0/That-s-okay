# 吵架训练营 💬

我们不教你赢，我们陪你练习第一次说不。

一个基于 LLM 的边界表达与情绪表达练习工具。你与 AI 扮演的对手进行对话，练习在冲突中清晰表达自己。对话结束后，心理框架复盘专家给出轻量、不说教的反馈。

---

## 两个训练场景

### 🚬 公共场所制止抽烟

练习对**陌生人**表达边界。AI 扮演公共场所抽烟者，用狡辩、施压、转移话题等策略对抗你。

- **4 种抽烟者人格**：油滑大叔、傲慢精英、委屈无辜型、冷暴力型，每局随机
- **6 种策略槽位**：施压 / 狡辩 / 松动 / 让步 / 假意顺从再复发 / 反咬态度
- **升级阶梯机制**：对手不会机械降阻力，会有波折和拉锯

### 🏠 向父母表达情绪

练习对**至亲**表达脆弱和需求。AI 扮演东亚父母，用"为你好"否定你的情绪。你以成年自己的身份，练习在被否定时完整表达，不自我压抑。

- **5 种父母类型**（对应 5 个生活剧本）：严厉教导型、说教大道理型、牺牲绑架型、冷淡轻视型、反躬自省型
- **6 种策略槽位**：否定情绪 / 道德绑架 / 归咎孩子 / 轻视转移 / 松动 / 真正看见
- **Gottman 情感邀请分析**：复盘会指出你的"情感邀请"质量如何，父母回应是"转向靠近"还是"转向反对"

---

## 工作流程

```
首页 → 选择场景 → 训练对话（3-6轮）→ 复盘卡片（3张）
```

1. **首页** — 两个场景卡片，选择你想练的
2. **训练页** — 打字和对手对话，AI 根据你的表达动态调整策略
3. **复盘页** — 查看 3 张卡片，含 NVC 分析和可复用的表达模板

---

## 复盘框架

### 抽烟场景

非暴力沟通（NVC）轻量复盘：
- 🎯 **你刚刚做到的事** — 你在哪个时刻表达了边界
- 💪 **可以更稳的一句话** — 更精炼的表达方式
- 📋 **下次可复制的边界模板** — 事实 + 感受 + 请求

### 父母场景

**非暴力沟通（NVC，马尔歇尔·卢森堡）+ 亲密关系（John Gottman）** 复盘：
- 🎯 **你刚刚做到的事** — 你的情感邀请（emotional bid）在哪一轮发出？NVC 四元件（观察/感受/需要/请求）齐不齐？从哪一轮"表达自己"转向了"攻击对方"？
- 💪 **可以更稳的一句话** — 用 NVC 四元件格式重写：「当我看到……我感到……因为我需要……你愿意……吗？」
- 📋 **下次可复制的模板** — 附括号说明为什么有效

---

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Streamlit |
| LLM | 智谱 GLM-5.1（OpenAI 兼容 API） |
| 抽烟者 Agent | 人格话术库 + 升级阶梯 + JSON 解析重试 |
| 父母 Agent | 人设话术库 + 策略弧线 + JSON 解析重试 |
| 复盘 Agent | NVC 框架 / NVC+Gottman 框架，结构化 JSON 输出 |

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

> 无需 API Key 也能跑：未配置 API Key 时，Agent 会使用本地规则引擎兜底，对话和复盘都能走通（demo 模式）。

---

## 目录结构

```
argue-training-camp/
├── app.py                          # Streamlit 主入口（双场景 + 3 页面）
├── requirements.txt
├── .env.example
├── .gitignore
│
├── services/
│   ├── llm.py                      # 抽烟者冲突 Agent（人格 + 话术库 + 升级阶梯）
│   ├── parent_agent.py             # 父母冲突 Agent（NVC 训练 + 策略弧线）
│   ├── review.py                   # 复盘专家（双场景适配）
│   ├── stt.py                      # 语音转文字（预留）
│   └── tts.py                      # 文字转语音（预留）
│
├── prompts/
│   ├── smoker_agent.md             # 抽烟者系统提示词
│   ├── personality_bank.json       # 4 种抽烟者人格 + 79 句话术
│   ├── fewshot_smoking.md          # 抽烟者 Few-shot 示例（8 条）
│   ├── parent_agent.md             # 父母系统提示词
│   ├── parent_personality_bank.json # 5 种父母类型 + 113 句话术
│   ├── fewshot_parent.md           # 父母 Few-shot 示例（10 条）
│   ├── review_agent.md             # 抽烟场景复盘系统提示词
│   └── parent_review_agent.md      # 父母场景复盘（NVC + Gottman）
│
├── utils/
│   └── config.py                   # LLM 客户端 & 配置加载
│
├── test_api.py                     # API 连通性测试
├── test_e2e.py                     # 端到端流程测试
└── test_backend.py                 # 后端单元测试
```

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
