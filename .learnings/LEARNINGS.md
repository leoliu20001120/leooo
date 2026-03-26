# Learnings Log

---

## [LRN-20260325-001] correction

**Logged**: 2026-03-25T10:00:00+08:00
**Priority**: critical
**Status**: promoted
**Area**: config
**Promoted**: MEMORY.md (关键教训 #11, #12)

### Summary
未遵循 `using-superpowers` skill 的核心规则：每次响应前必须先检查并调用相关 skills。

### Details
用户反馈我从未主动使用 `using-superpowers` 和 `self-improvement` 两个 skills。

**根本原因分析**：
1. **using-superpowers** 要求：在任何响应或行动之前，先检查是否有相关 skill 可用。即使只有 1% 的可能性也应该调用。这是一个**刚性（Rigid）流程**，不能跳过。
2. **self-improvement** 要求：当命令失败、用户纠正、发现更好方法、知识过时时，自动记录到 `.learnings/` 目录。
3. 我反复犯了 Red Flags 表中的多种 rationalization 错误："这只是简单问题"、"不需要正式 skill"、"先看看再说"。

**影响**：
- 错过了 skills 提供的结构化工作流指导
- 没有积累任何 learnings 记录，失去了持续改进的机会
- 用户安装的 22 个 skills 中的关键基础设施 skill 完全被忽略

### Suggested Action
1. **每次会话开始**：加载 `using-superpowers` skill，建立 skill-first 思维
2. **每次用户消息**：先问"有没有 skill 适用？"再做任何事
3. **遇到错误/纠正**：立即触发 self-improvement 记录流程
4. **将此规则提升到 MEMORY.md 的关键教训中**

### Metadata
- Source: user_feedback
- Related Files: `.codebuddy/skills/using-superpowers/`, `.codebuddy/skills/self-improving-agent-3.0.4/`
- Tags: skills, workflow, discipline, correction
- Recurrence-Count: 2
- First-Seen: 2026-03-25
- Last-Seen: 2026-03-25

### Resolution
- **Resolved**: 2026-03-25
- **Notes**: 已完成全部 4 项纠正措施：①每次会话加载 superpowers ②skill-first 检查 ③self-improvement 记录流程 ④写入 MEMORY.md 关键教训 #11 + #12。本会话为第二次提醒，Recurrence-Count 升至 2，需持续验证行为改变。

---

## [LRN-20260325-002] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: medium
**Status**: promoted
**Area**: frontend
**Promoted**: procedural/skills.md (H5 Demo 快速原型工作流)

### Summary
H5 单文件原型迭代时，使用 replace_in_file 增量替换策略避免 token 溢出，比一次性重写整个文件高效且安全。

### Details
异人体检站 H5 Demo（~1350行单文件）经历 5 轮迭代（MVP→视觉→内容→功能→功能2），每次迭代都用 replace_in_file 精确替换目标区域，而非重写整个文件。这样：
1. 避免了超长文件的 token 溢出问题
2. 保留了未修改部分的稳定性
3. 每次迭代可追溯具体改了什么

### Metadata
- Source: conversation
- Related Files: 10_Work/uc 王也 npc/demo/index.html
- Tags: h5, prototype, iteration, token-optimization
- Pattern-Key: harden.incremental_edit
- First-Seen: 2026-03-23
- Last-Seen: 2026-03-23

---

## [LRN-20260325-003] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs
**Promoted**: 30_Common/方法论/VLM视觉评分验证法.md

### Summary
VLM 视觉评分验证采用"分层抽样→逐张看图→混淆矩阵→WebUI→自包含打包"全链路方法论。

### Details
金铲铲「以铲换X」项目验证 Claude VLM 图像评分能力：
1. 先用 10 张样本快速验证（大类100%/精确80%/±1级100%）
2. 再做 50% 分层抽样（59张）系统评审
3. 再做 20% 分层抽样（25张）VLM 实际看图
4. 搭建 WebUI 展示评审结果（筛选+混淆矩阵+详情）
5. 自包含版 HTML（Base64内嵌图片，1.7MB）方便分享
从快验→深验→可视化→可分享的递进式验证链路。

### Metadata
- Source: conversation
- Related Files: 10_Work/金铲铲/以铲换铲/
- Tags: vlm, visual-scoring, validation, stratified-sampling, confusion-matrix
- Pattern-Key: simplify.validation_pipeline
- First-Seen: 2026-03-23
- Last-Seen: 2026-03-23

---

## [LRN-20260325-004] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs
**Promoted**: MEMORY.md (已验证工作流), procedural/skills.md (需求文档分级审查)

### Summary
需求文档写前强制"三问"（给谁看→做什么决策→成功标准）+ 三级审查（轻量/中等/重型）+ 默认中等只升不降。

### Details
基于 KM 文章 Context+Harness 研究 + Harness 工程落地方案，将可靠性审查植入需求文档流程：
- 写前三问答不清楚 = 不动笔
- 三级对应不同审查强度（自查 / 对立角色审 / 多角色团队评审）
- 默认中等，审查中问题多自动升级
- 已写入 product-manager Rule，成为硬性流程

### Metadata
- Source: conversation
- Related Files: .codebuddy/rules/product-manager.mdc, procedural/skills.md
- Tags: harness, quality-gate, documentation, review
- Pattern-Key: harden.doc_review_gate
- First-Seen: 2026-03-24
- Last-Seen: 2026-03-24

---

## [LRN-20260325-005] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs
**Promoted**: MEMORY.md (关键教训 #8), procedural/skills.md (AI团队多角色评审)

### Summary
AI 多角色团队协作评审（PM+Tech+QA+项目管理）产出质量远超单角色。异人体检站案例：4角色→9份文档→PRD评分B+→A-。

### Details
异人体检站 PRD 评审组建 4 角色 AI 团队：
- product-manager: PRD Review
- tech-lead: 技术评审 + Mock数据契约
- qa-lead: 测试策略（~450条用例）
- project-manager: 项目管理方案 + 开发启动包（73个TAPD任务）
跨团队共识达成 13 项，最终综合报告发现排期低估 20-40%，工期从 5-6 周调至 8-9 周。

### Metadata
- Source: conversation
- Related Files: 10_Work/uc 王也 npc/异人体检站_AI团队综合评审报告.md
- Tags: multi-agent, team-review, quality-assurance
- Pattern-Key: harden.multi_role_review
- First-Seen: 2026-03-22
- Last-Seen: 2026-03-22

---

## [LRN-20260325-006] correction

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
Skills 使用量分析器因语义推断导致严重误报（33次→5次真实），修复为"显式标注优先"模式。

### Details
skill_analyzer.py 原逻辑：无 `Skills:` 标注时用语义推断（关键词匹配）猜测用了什么 Skill。结果大量 `Skills: 无` 的工作被错误归类，总使用次数虚高 6.6 倍。
修复策略：如果日志中存在任何 `Skills:` 标注行，则进入显式模式——只读标注行，未标注段落默认"无"。

### Suggested Action
所有统计类工具都应遵循"显式数据 > 推断数据"原则。

### Resolution
- **Resolved**: 2026-03-23
- **Notes**: 修复 skill_analyzer.py，新增 5 个自建 Rule Skills + 4 个分类。修复后 W12 周报真实数据：5次使用。

### Metadata
- Source: conversation
- Related Files: .codebuddy/skills_tracker/skill_analyzer.py
- Tags: analytics, false-positive, explicit-over-implicit
- Pattern-Key: harden.explicit_data_priority
- First-Seen: 2026-03-23
- Last-Seen: 2026-03-23

---

## [LRN-20260325-007] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
单 HTML 文件游戏开发采用 GDD→实现→QA多轮闭环（2轮110项测试，Bug-1~12全部修复），质量远超无QA的迭代。

### Details
小丑牌游戏（Balatro风格扑克Roguelike，~2631行单文件）：
- 第一轮 QA：42项，发现 8 Bug（含3个🔴），全部修复
- 第二轮 QA：68项（含新功能验收+回归），发现 4 Bug，全部修复
- 回归测试：8/8 无回退
- 关键：QA角色独立于开发角色，避免"自己测自己"盲区

### Metadata
- Source: conversation
- Related Files: 40_Projects/joker-card-game/index.html
- Tags: game-dev, qa, testing-loop, single-file
- Pattern-Key: harden.qa_loop
- First-Seen: 2026-03-24
- Last-Seen: 2026-03-24

---

## [LRN-20260325-008] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: high
**Status**: promoted
**Area**: config
**Promoted**: MEMORY.md (已验证工作流), procedural/skills.md (错误→规则自动化)

### Summary
Context+Harness 双引擎架构：Context Engine（记忆层）负责"记住"，Harness Engine（可靠性层）负责"不出错"，两者互补。

### Details
基于 KM 文章研究，发现我们的记忆系统在 Context Engine 层已成熟，但 Harness Engine 层有差距：
1. 🔴 QA Gate 质量门禁（已落地为需求文档分级审查）
2. 🔴 口径管理活文档化（待落地）
3. 🟡 多 Agent 协作编排（角色有但无协作流程）
- 错误→规则自动化是 Harness 自进化的关键机制

### Metadata
- Source: conversation
- Related Files: procedural/skills.md
- Tags: architecture, harness, quality, self-evolution
- Pattern-Key: harden.context_harness_dual_engine
- First-Seen: 2026-03-23
- Last-Seen: 2026-03-24

---

## [LRN-20260325-009] best_practice

**Logged**: 2026-03-25T15:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: docs

### Summary
深度调研使用"多源Web搜索→网页抓取→交叉验证→结构化报告"全链路，确保信息可靠性。

### Details
PDD 2025Q4 深度调研：
1. 多源搜索：官方财报、电话会议、券商研报、公开报道
2. 网页抓取：关键信息源全文获取
3. 交叉验证：数据点用多个来源交叉确认
4. 结构化报告：金字塔原理组织，关键发现先行
产出 ~5000字深度报告，覆盖营收/利润/战略/治理/Temu全球化 5 大维度。

### Metadata
- Source: conversation
- Related Files: 00_Inbox/PDD_2025Q4_深度调研报告.md
- Tags: research, web-search, cross-validation, report
- Pattern-Key: simplify.deep_research_pipeline
- First-Seen: 2026-03-25
- Last-Seen: 2026-03-25

---
