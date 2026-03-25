---
created: 2026-03-25
tags: [AI, OpenAI, Boris-Power, GPT, Fine-tuning, 应用研究, 人物调研]
related: "[[Lex Fridman 452 播客笔记 - Anthropic三巨头访谈]]"
---

# 🔍 Boris Power 深度调研：OpenAI 应用研究负责人

> **⚠️ 重要说明**：Boris Power 是 **OpenAI**（不是 Anthropic）的应用研究负责人（Head of Applied Research）。如果你关注的是 Anthropic 的工程负责人，请参见文末 [[#Anthropic 工程侧关键人物补充]]。

---

## 📋 人物速览

| 维度 | 信息 |
|------|------|
| **姓名** | Boris Power |
| **公司** | OpenAI |
| **职位** | Head of Applied Research（应用研究负责人） |
| **专业领域** | 深度学习、AI 应用、微调（Fine-tuning）、嵌入（Embeddings）、模型评估 |
| **职业背景** | 数据科学、软件工程、机器学习咨询 |
| **GitHub** | [@BorisPower](https://github.com/BorisPower)（126 followers，无公开仓库，但有大量 OpenAI 官方仓库贡献） |
| **X/Twitter** | @BorisMPower |
| **主要贡献** | GPT-3/GPT-4 相关工作、OpenAI Fine-tuning API 设计、模型评估标准 |

---

## 🧑‍💻 职业轨迹

### 加入 OpenAI 前
- 拥有数据科学、软件工程和机器学习咨询背景
- 在多个 AI 项目中积累了丰富的实践经验

### 在 OpenAI（~2021 至今）
- **早期贡献（2021）**：作为 Collaborator 身份为 `openai-python` SDK 做出重要贡献
  - PR #29：改进 `prepare_data` 函数——编码修复、静默模式、时间估算、分类微调示例
  - PR #32：添加示例和 CLI 改进
- **核心角色**：参与 GPT-3、GPT-4 系列模型的应用研究
- **晋升至 Head of Applied Research**：领导应用研究团队，负责将基础模型能力转化为开发者可用的产品

---

## 🎯 核心技术观点

### 1. 「强大基础模型 + 简单微调」范式

> Boris Power 的核心理念：**凭借强大的基础模型，仅需简单的微调便能够满足不同领域需求**。

这一观点在多个领域得到验证：
- **自动驾驶**：认为只需要训练最强大的基础模型，然后针对特定驾驶场景进行微调
- **图像生成**：GPT-4o 的图像生成能力展示了多模态基础模型的通用性
- **3D 渲染**：GPT-4o 可以生成 PBR 材质（基于物理渲染的材质），包括纹理、法线贴图等

**核心逻辑链**：
```
投入 → 训练最强基础模型 → 简单微调 → 覆盖各个垂直领域
```

### 2. 模型评估的严谨性

2025年2月，Boris Power 在 X 上公开质疑 xAI 的 Grok 模型评估方法，引发业界广泛讨论：

> "令人遗憾的是，Grok 团队在评估中存在作弊和欺骗的动机。简而言之，o3-mini 在所有评估中都表现得比 Grok 3 更优秀。Grok 3 确实是一个不错的模型，但不必过分夸大其性能。"

**争议焦点**：
- **xAI 使用的方法**：多次测试取最优结果（best-of-N），可通过多次尝试选择最优结果来提升整体评分
- **OpenAI 使用的方法**：单次测试（pass@1），更能反映模型真实能力
- **核心问题**：评测方法差异导致分数不可比，行业需要统一标准

### 3. 微调 API 的产品化思维

Boris Power 在 OpenAI 的核心工作之一是将微调能力产品化：

| 时间 | 里程碑 |
|------|--------|
| 2021年 | 贡献 openai-python SDK 的 prepare_data 工具 |
| 2023年8月 | GPT-3.5 Turbo 微调 API 开放 |
| 2024年8月 | GPT-4o 微调 API 开放（每天免费100万 Token） |
| 2024年10月 | GPT-4o 视觉微调功能上线 |

**关键设计理念**：
- 降低微调门槛，让非专业开发者也能自定义模型
- 提供数据准备工具（`prepare_data`），自动检测和修复训练数据问题
- 通过免费 Token 策略降低试用成本
- 支持文本 → 多模态（图像）的渐进式能力扩展

---

## 🔑 Boris Power 在 OpenAI 生态中的位置

```
Sam Altman (CEO)
├── 研究侧
│   ├── 基础研究（Ilya Sutskever → Jan Leike → ...）
│   └── ⭐ 应用研究（Boris Power）← 你在这里
│       ├── Fine-tuning API & 工具
│       ├── Embeddings API
│       ├── 模型评估与基准
│       └── 垂直领域应用（自动驾驶、3D等）
├── 产品侧（Kevin Weil）
└── 安全侧（Preparedness Team）
```

Boris 的团队连接了**基础研究**和**开发者产品**之间的桥梁：
- 将前沿模型能力转化为可用的 API
- 定义微调、嵌入等功能的最佳实践
- 建立模型评估标准和方法论

---

## 📊 与 Anthropic 对比：应用研究哲学

| 维度 | Boris Power / OpenAI | Anthropic 方式 |
|------|---------------------|---------------|
| **核心策略** | 强基础模型 + 微调 API | 强基础模型 + System Prompt + Constitutional AI |
| **定制化方式** | Fine-tuning API（改变模型权重） | Prompt Engineering + Character Training |
| **开发者工具** | SDK、Cookbook、Playground | API Console、Prompt Library |
| **评估标准** | pass@1 严格单次评估 | 多维安全+能力评估（RSP/ASL） |
| **垂直领域** | 积极推动自动驾驶、3D 渲染等 | 聚焦企业级应用和安全关键领域 |
| **开放程度** | API 优先，广泛开放 | API 优先，安全过滤更严格 |

---

## 📰 关键公开发言与事件

### 2025年2月 — Grok 评估争议
- 公开质疑 xAI 的 Grok 3 评测方法
- xAI 联合创始人 Yuhuai (Tony) Wu 回应：Grok mini 在 AIME 2024、GPQA、LCB 的 pass@1 指标上都超过了 o3-mini high
- **行业影响**：推动了关于 AI 模型评估标准化的讨论

### 2025年3月 — GPT-4o 自动驾驶愿景
- 提出基础模型可以直接应用于自动驾驶领域
- 认为只需最强基础模型 + 微调即可
- 引发争议：部分人认为 Stable Diffusion + ControlNet 已经可以实现类似能力

### 2024年 — 微调 API 产品化
- 主导 GPT-4o 微调功能的开放
- 推出视觉微调功能，将微调从文本扩展到多模态

---

## 💡 对我的启示

### 产品/技术策略
1. **「基础模型 + 微调」是当前最主流的 AI 产品化路径**——OpenAI 和 Anthropic 在这点上有分歧（微调 vs Prompt Engineering），但都认可强基础模型的重要性
2. **评估标准很重要**——模型能力的衡量方式直接影响用户对产品的判断
3. **降低使用门槛是关键**——Boris 的工作重心是让开发者更容易地使用 AI 能力

### 行业观察
1. Boris Power 是 OpenAI 中**偏产品化和落地**的角色，与 Anthropic 的 Amanda Askell（偏哲学和对齐）形成有趣对比
2. **应用研究 ≠ 基础研究**——Boris 关注的不是 Scaling Laws 本身，而是如何将 Scaling Laws 的成果变成开发者手中的工具
3. **Fine-tuning vs Prompting** 之争仍在继续——OpenAI 更倾向于通过微调实现深度定制，Anthropic 更倾向于通过精细的 Prompt Engineering

---

## ⚠️ 调研局限性说明

> Boris Power 相较于 Sam Altman、Dario Amodei 等 CEO 级人物，**公开曝光度较低**。他没有参加过知名播客长访谈（如 Lex Fridman），也没有大量的公开演讲或文章。本调研主要基于：
> 1. X/Twitter 上的公开发言
> 2. GitHub 贡献记录（openai-python SDK）
> 3. 中国 AI 社区的新闻报道
> 4. OpenAI 官方产品发布信息
>
> **未能找到**：深度播客访谈、个人博客/技术文章、学术论文

---

## 🔗 Anthropic 工程侧关键人物补充

如果你实际想了解的是 Anthropic 的工程/技术负责人，以下是关键人物：

| 姓名 | 角色 | 备注 |
|------|------|------|
| **Dario Amodei** | CEO / 技术方向把控 | 参见 [[Lex Fridman 452 播客笔记 - Anthropic三巨头访谈]] |
| **Tom Brown** | Co-founder / 技术 | GPT-3 论文第一作者，后转入 Anthropic |
| **Chris Olah** | Co-founder / 可解释性 | 机械可解释性先驱 |
| **Jan Leike** | 安全研究负责人 | 前 OpenAI 安全团队负责人，2024年跳槽 Anthropic |
| **Mike Krieger** | Chief Product Officer | Instagram 联合创始人，负责 Claude 产品 |
| **Amanda Askell** | 角色研究 | Claude 的"灵魂工程师" |

---

## 📚 参考来源

1. [BorisPower GitHub](https://github.com/BorisPower) — 个人 GitHub 页面
2. [openai-python PR #29](https://github.com/openai/openai-python/pull/29) — prepare_data 函数改进
3. [openai-python PR #32](https://github.com/openai/openai-python/pull/32) — 示例和 CLI 改进
4. [今日头条 - OpenAI 的应用研究负责人质疑 Grok 评测](https://www.toutiao.com/article/7473395408669803049/) — Grok 评估争议报道
5. [搜狐 - GPT-4o 多模态图像生成技术](https://www.sohu.com/a/877272723_121924584) — Boris Power 关于基础模型 + 微调的观点
6. [CSDN - 计算机视觉被 GPT-4o 终结了](https://blog.csdn.net/QbitAI/article/details/146718569) — Boris Power 自动驾驶/3D 渲染观点
7. [搜狐 - OpenAI 与 xAI 的 AI 模型博弈](https://www.sohu.com/a/862015263_121902920) — Grok 评测风波深度分析
