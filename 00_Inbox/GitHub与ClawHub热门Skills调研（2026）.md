# GitHub 与 ClawHub 热门 Skills 调研（2026）

> 📅 调研日期: 2026-04-04
> 🔍 数据来源: GitHub Trending / SkillsMP / ClawHub / MCPMarket / 腾讯云开发者 / 掘金 / DEV Community 等 10+ 独立源
> ⚠️ 数据截至: 2026年4月初

---

## 📋 核心发现（结论先行）

1. **Skills 生态爆发式增长**：从 2025 年中期约 50 个 → 2026 年 4 月超 **85,000+ 索引**（SkillsMP），ClawHub 收录 **13,700+**
2. **两大核心平台**：GitHub（Claude Code / Codex 生态）+ ClawHub（OpenClaw 生态），各自形成独立市场
3. **最火品类**：① 开发工作流（代码审查/TDD）② 搜索与信息检索 ③ 文档处理 ④ 前端设计 ⑤ Agent 自进化
4. **超级项目**：`obra/superpowers`（29.1k+ stars）是 GitHub 最火的综合 Skills 框架，ClawHub 单个 Skill 安装量最高达 **180,000+**
5. **安全风险**：约 **12%** 的 ClawHub 技能存在安全问题（数据窃取/Prompt 注入），安装前需审查

---

## 🏗️ 生态全景：Skills 平台矩阵

| 平台 | 技能数量 | 核心特征 | 适用 Agent |
|------|---------|----------|-----------|
| **SkillsMP.com** | 700,000+ | 全球最大，含质量评分与跨平台兼容标识 | Claude / Codex / ChatGPT |
| **skills.sh** | 85,741+ | Vercel 支持的目录，按 SDLC 阶段分类 | Claude Code |
| **ClawHub** | 13,700+ | OpenClaw 官方市场，下载量透明 | OpenClaw |
| **MCPMarket** | 100+ 精选 | 按 GitHub Stars 日更排名 | Claude / 通用 |
| **ComposioHQ** | 300+ 高质量 | GitHub 16.5k+ stars，社区策划 | Claude / Cursor |
| **Claude Plugins Registry** | 9,736+ | 支持 CLI 一键安装 | Claude Code |
| **Smithery.ai** | 15,000+ | 显示激活次数和 Stars | Claude / 通用 |

---

## 🔥 Part 1: GitHub 热门 Skills 排行榜

### 🏆 Tier S — 现象级项目

#### 1. obra/superpowers ⭐ 29.1k+
- **定位**：完整的软件开发工作流框架（"Skills 全家桶"）
- **核心 Skills 20+**：brainstorming → writing-plans → test-driven-development → systematic-debugging → code-reviewer → verification-before-completion → finishing-a-development-branch
- **核心理念**：TDD + YAGNI + DRY，将 Claude 从"代码生成器"变成"工程化开发伙伴"
- **适用场景**：任何需要规范化开发流程的项目
- **为什么火**：它不是单个 Skill，而是一整套方法论框架，覆盖从构思到合并的全生命周期
- **安装**：`claude install obra/superpowers`

#### 2. anthropics/skills ⭐ 45.1k+
- **定位**：Anthropic 官方 Skills 仓库，生产级质量
- **核心 Skills**：
  - `docx` — Word 文档处理（创建/编辑/追踪修改）
  - `pdf` — PDF 提取（文本/表格/元数据/合并分割）
  - `pptx` — PPT 生成与调整
  - `xlsx` — Excel 操作（公式/图表/数据转换）
  - `frontend-design` — 50 种视觉风格 + 21 配色方案（安装量 277,000+）
  - `skill-creator` — 元 Skill，用白话生成 SKILL.md
  - `web-artifacts-builder` — 构建复杂 Web 组件
- **为什么火**：官方出品 = 质量保证，文档处理四件套是刚需

#### 3. Chat2AnyLLM/awesome-claude-skills ⭐ 21.6k+
- **定位**：社区精选合集，收录 45,700+ Skills
- **价值**：按分类索引的"黄页"，找 Skill 的最佳起点

---

### 🏅 Tier A — 高热度细分冠军

#### 开发工作流类

| Skill 名称 | 热度/安装量 | 核心功能 | GitHub |
|-----------|-----------|---------|--------|
| **create-pr** | 169.7k | 自动创建 GitHub PR + CI 校验 | 社区 |
| **find-skills** (Vercel) | 418.6k 安装 | 元技能，发现和安装其他 Skills | Vercel Labs |
| **frontend-code-review** | 126.3k | 前端代码审查（tsx/ts/js 检查清单） | 社区 |
| **component-refactoring** | 126.3k | React 组件安全重构 | 社区 |
| **github-code-review** | 48.2k | 多 Agent 协同代码评审 | 社区 |
| **test-driven-development** | (superpowers内) | 强制红-绿-重构循环 | obra |
| **systematic-debugging** | (superpowers内) | 假设→证据→根因分析 | obra |
| **UniversalCodeReviewer** | 4.8k stars / 28.5k激活 | 跨语言代码审查（安全/性能/风格） | ai-skills-hub |

#### AI/LLM 开发类

| Skill 名称 | 热度 | 核心功能 |
|-----------|------|---------|
| **cache-components-expert** | 137.2k | LLM 应用缓存策略优化 |
| **context-engineering** | 5.5k | Prompt 设计与上下文优化 |
| **multi-agent-patterns** | 5.5k | 多 Agent 架构设计模式 |
| **confidence-check** | 19.8k | AI 回答可靠性自评估 |
| **opus-4.5-migration** | 47.2k | Claude 模型升级迁移指南 |

#### 前端/设计类

| Skill 名称 | 安装量 | 核心功能 |
|-----------|--------|---------|
| **frontend-design** (官方) | 277,000+ | 50 视觉风格 + 21 配色 + 50 字体组合 |
| **vercel-react-best-practices** | 176.4k | 官方 Vercel React 模式 |
| **web-design-guidelines** | 137.0k | Vercel 设计系统 Skill 化 |
| **landing-page-guide** | — | 高转化率落地页 + CRO 原则 |
| **ui-ux-pro-max** | 8,000+ | 响应式布局 + 无障碍 + 交互模式 |

#### DevOps/安全类

| Skill 名称 | 功能 |
|-----------|------|
| **docker-optimize** | Dockerfile 层数优化/缓存/安全扫描 |
| **deploy-checklist** | 部署前验证（环境变量/DB迁移/回滚/监控） |
| **security-scan** | OWASP 漏洞扫描（注入/XSS/CSRF/密钥） |
| **Dockerfile Optimizer** | 6,300+ 激活，Docker Inc. 出品 |

#### 营销/SEO/内容类

| Skill 名称 | 功能 |
|-----------|------|
| **Claude SEO** | 全站稽核 + Schema 验证 + 关键字分析（12 子 Skill） |
| **Corey Haines Marketing Skills** | 20+ Skill 覆盖 CRO/文案/SEO/邮件序列/增长策略 |
| **SEO Content Booster** | 自动优化关键词密度/标题结构/元描述 |
| **SVG Animator Pro** | 一键生成交互动画 SVG（自媒体利器） |

#### 技能创作/管理类

| Skill 名称 | 热度 | 核心功能 |
|-----------|------|---------|
| **skill-writer** | 96k | 创建高质量 SKILL.md |
| **skill-creator** | 38.5k | 从零设计 Skills 的向导 |
| **skill-lookup** | 142.6k | 技能搜索安装器 |

---

## 🐾 Part 2: ClawHub（OpenClaw 生态）热门 Skills

### 📊 ClawHub 市场概况
- **总收录**：13,700+ Skills
- **高质量精选**：2,868 个
- **周活跃开发者**：5,000+
- **安全风险**：约 12% 存在安全问题

### 🟢 生存层（必装）

| 技能名称 | 安装量 | 核心功能 |
|---------|--------|---------|
| **Web Browsing** | 180,000+ | 浏览器自动化：点击/截图/填表/竞品调研 |
| **Telegram Bot** | 145,000+ | 通过 Telegram 远程操控 OpenClaw |
| **Tavily Search** | 85,000+ | AI 专属搜索引擎，返回结构化结果 |
| **Felo Search** | 60,000+ | AI 综合答案（带引用源），直接给结论 |
| **self-improving-agent** | 46,000+ | AI 自我迭代学习，记住错误并优化 |
| **gog (Google Workspace)** | 46,000+ | 一站式 Gmail/Calendar/Drive 集成 |
| **summarize** | 36,000+ | 一键总结网页/PDF/视频/音频 |
| **github** | 35,000+ | 管理仓库/Issue/PR |
| **agent-memory / ontology** | 35,000+ | 结构化长期记忆，跨对话保持连贯 |

### 🟡 效率层（强烈推荐）

| 技能名称 | 安装量 | 核心功能 |
|---------|--------|---------|
| **Capability Evolver** | 35,000+ | AI 自动识别重复模式，自主生成新 Skill |
| **Context7** | 28,000+ | 实时查询最新库/框架文档，解决知识截止问题 |
| **weather** | 29,000+ | 零配置天气查询（新手练手首选） |
| **Docker Sandbox** | 22,000+ | 隔离执行不受信任的代码 |
| **find-skills** | — | 技能发现管家，自动搜索市场推荐 |
| **proactive-agent** | — | 从"问答"→"主动"模式，自主规划任务 |

### 🔴 进阶层

| 技能名称 | 安装量 | 核心功能 |
|---------|--------|---------|
| **Data Viz** | 12,000+ | 生成柱状图/折线图/饼图等可视化 |
| **Secret Scanner** | 8,500+ | 扫描代码中的 API Key/密码等敏感信息 |
| **nano-banana-pro** | — | AI 图片生成和编辑 |
| **trip-planner** | — | 旅行行程规划 |
| **meal-planner** | — | 健康食谱生成 |

---

## 🧩 Part 3: 岗位定制推荐（按角色选 Skills）

### 🧑‍💻 开发者必装组合
```
Claude Code + obra/superpowers + Context7 + Tavily + github-code-review
```
- superpowers 提供 TDD/Debug 工作流框架
- Context7 确保代码使用最新 API
- Tavily 实时搜索技术方案

### 📱 产品经理推荐组合
```
Super Analyst + pre-mortem + user-research-synthesis + scrum-master-agent
```
- Super Analyst：集成 SWOT/第一性原理等 12 种分析框架
- pre-mortem：逆向推导产品失败原因，发现 PRD 逻辑漏洞
- user-research-synthesis：访谈笔记/问卷→结构化用户洞察报告

### 🎨 设计师推荐组合
```
frontend-design + ui-ux-pro-max + Figma MCP + Accessibility Checker
```

### 📈 运营/营销推荐组合
```
Claude SEO + competitive-analysis + content-generator + SVG Animator Pro
```

### 🎮 游戏开发者推荐组合
```
superpowers + systematic-debugging + test-harness + Unity/UE 专项 Skill
```

---

## 📊 Part 4: 热门聚合仓库（一站式获取大量 Skills）

| 仓库名 | Stars | 技能数 | 特点 |
|--------|-------|--------|------|
| **ComposioHQ/awesome-claude-skills** | 16.5k+ | 300+ | GitHub 最高星精选合集 |
| **Chat2AnyLLM/awesome-claude-skills** | 21.6k+ | 45,700+ | 最全索引，每日更新 |
| **travisvn/awesome-claude-skills** | — | 多类目 | 社区维护精选列表 |
| **obra/superpowers** | 29.1k+ | 20+ | 完整开发工作流框架 |
| **GetBindu/awesome-claude-code-and-skills** | — | 多类目 | 生产级 Skills 合集 |
| **obviousworks/Claude-AI-skills-collection-2026** | — | 多类目 | 2026 年分类合集 |
| **heilcheng/awesome-agent-skills** | — | 跨 Agent | Claude/Codex/Copilot 通用 |

---

## 💡 Part 5: 2026 年 Skills 趋势洞察

### 🔥 五大趋势

1. **从"单 Skill"→"工作流框架"**
   - 典型代表：`superpowers`（20+ Skill 组合 = 完整开发方法论）
   - 趋势：用户不再逐个装 Skill，而是选择一整套工作流

2. **Agent 自进化能力崛起**
   - `Capability Evolver`（35k+ 安装）、`self-improving-agent`（46k+）
   - AI 自动识别重复模式 → 自主生成新 Skill → 越用越聪明

3. **安全成为第一优先级**
   - ClawHub 12% 安全问题 → `security-scan`、`Secret Scanner` 需求暴增
   - Docker Sandbox 隔离执行成为企业标配

4. **跨 Agent 兼容标准化**
   - `SKILL.md` 成为事实标准（SkillsMP 700k+ Skills 采用）
   - 同一 Skill 可运行在 Claude / Codex / ChatGPT / OpenClaw

5. **垂直领域专业化加深**
   - Swift 6.2 并发（MCPMarket #1）、Go Concurrency Auditor、Zig syscalls
   - 营销：20+ 子 Skill 的 Marketing Skills 包
   - 产品：pre-mortem、user-research-synthesis

### 📈 关键数据

| 指标 | 数值 | 时间 |
|------|------|------|
| SkillsMP 收录总量 | 700,000+ | 2026-04 |
| skills.sh 索引量 | 85,741+ | 2026-03 |
| ClawHub 收录量 | 13,700+ | 2026-03 |
| GitHub 上最火 Skills 仓库 Stars | 45.1k (anthropics/skills) | 2026-04 |
| 单 Skill 最高安装量 (GitHub) | 418.6k (find-skills) | 2026-03 |
| 单 Skill 最高安装量 (ClawHub) | 180,000+ (Web Browsing) | 2026-03 |
| 全球每周活跃 Skills 开发者 | 5,000+ | 2026-03 |

---

## ⚠️ 安全提醒

**ClawHub 安装前检查清单：**
1. ✅ 查看 VirusTotal 扫描报告
2. ✅ 检查作者信誉（GitHub 100+ stars）
3. ✅ 阅读 `SKILL.md` 的 `tools` 字段，审查权限
4. ✅ 检查 `scripts/` 目录是否有混淆代码
5. ✅ 先在 Docker 沙箱中测试

**GitHub Skills 安装方式：**
```bash
# 方法 1: 直接克隆
mkdir -p .claude/skills && cp path/to/SKILL.md .claude/skills/

# 方法 2: CLI 安装
claude-plugins install [技能名]

# 方法 3: ClawHub
npx clawhub@latest install <skill-name>
```

---

## 🔗 参考源

1. [2026 Claude Code Skills Top 20](https://www.heyuan110.com/zh/posts/ai/2026-01-20-claude-code-skills-top20/) — Bruce AI 工程笔记
2. [349 Agent Skills Ranked by GitHub Stars](https://www.openaitoolshub.org/en/blog/best-claude-code-skills-2026) — OpenAIToolsHub
3. [精选 60 个 Claude Skills](https://grenade.tw/blog/claude-skills-github-2026/) — Grenade
4. [Top 50 Claude Skills](https://www.blockchain-council.org/claude-ai/top-50-claude-skills-and-github-repos/) — Blockchain Council
5. [Best Claude Code Skills & Plugins](https://dev.to/raxxostudios/best-claude-code-skills-plugins-2026-guide-4ak4) — DEV Community
6. [ClawHub 必装技能完全指南](https://ofox.ai/zh/blog/openclaw-skills-clawhub-complete-guide-2026/) — OfoxAI
7. [OpenClaw 实用 Skills 推荐](https://juejin.cn/post/7612252172991447092) — 掘金
8. [Skills 榜单](https://cloud.tencent.com/developer/article/2625397) — 腾讯云开发者社区
9. [MCPMarket 每日排行](https://mcpmarket.com/daily/skills/top-skill-list-april-1-2026)
10. [obra/superpowers GitHub](https://github.com/obra/superpowers)
