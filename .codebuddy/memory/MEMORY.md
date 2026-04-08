# 🧠 MEMORY.md — AI 启动上下文

> v3.0 | 更新: 2026-03-31
> 设计原则: **读完此文件即可工作，无需跳转**
> v3.0 变更: 新增 `projects/` 项目分区，每个项目独立存储知识/决策/教训

---

## 用户

- **角色**: 腾讯 AI 产品经理（游戏方向），GitHub `leoliu20001120`
- **主要职责**:
  - AI NPC方向: 《一人之下》王也 NPC
  - AI Coach方向: LOL 单局/多局复盘、LOL AI Coach（5v5单向→双向）、海克斯大乱斗 AI Coach、LOL Bot 推进、瓦罗兰特 AI Coach（参与较少）
  - 经典项目PM: 景德镇申遗（推进游戏团队制作 + AI NPC PM）
- **兴趣**: 游戏系统策划（通用型，非单一子方向）、AI 应用、AI 产品设计、Agent、产品方法论
- **工作节奏**: 大量时间在开会，其余是写产品文档 + 跟进开发 + 测试
- **痛点**: ①数据分析（新业务数据口径不熟）②需求文档（AI生成质量不稳定，上线效率需反复调试）
- **希望加速**: 文档撰写、Prompt 调试、数据处理、测试验证（程序化）
- **学习偏好**: 播客 > YouTube视频 > 短视频/文章 > 书籍（时间有限，不读完整书籍）；**更倾向中文内容**；播客平台：小宇宙 + Apple Podcasts
- 偏好: Python > JS，中文输出，Markdown 表格，代码直接写入文件
- 思维要求: **第一性原理**（回到本质追问为什么）+ **批判性思维**（质疑假设、检验逻辑）
- 输出要求: **金字塔原理**（结论先行 → 分组归类 → 逻辑递进），文档必须结构化
- 工具: Obsidian 知识管理 + CodeBuddy IDE + Git(SSH) + Supabase + 腾讯云
- 约定: 目录放 `_README.md`，全局导航 `_INDEX.md`，用 `[[双向链接]]`

## 知识库

```
00_Inbox/ → 缓冲区
10_Work/  → 工作项目（王也NPC、景德镇工作坊、Skills周报等）
20_Study/ → 学习（游戏策划理论、深度调研报告等）
30_Common/→ 知识沉淀
40_Projects/→ 个人项目（CaloriSnap）
99_Templates/→ 模板库
```

## 活跃项目（详情见 `projects/<id>/context.md`）

| 项目 | ID | 路径 | 状态 |
|------|-----|------|------|
| 🎮 UC 王也 NPC / 异人体检站 | `uc-wangye-npc` | `10_Work/uc 王也 npc/` | 已完成评审，Ready for Kick-off |
| 🎯 UC 对局复盘 | `uc-postmatch` | `10_Work/uc对局复盘/` | 迭代调优中 |
| 📱 CaloriSnap | `calorisnap` | `40_Projects/CaloriSnap/` | v0.3完成，待Phase 0 |
| 🏺 景德镇工作坊 | `jingdezhen` | `10_Work/景德镇/` | 中期开发 |
| 🎲 海克斯大乱斗 AI Coach | `hex-arena` | `10_Work/海克斯大乱斗/` | 数据体系完成，符文推荐设计中 |
| 🐱 LOLM 峡谷猫格 | `lolm-cat-personality` | `10_Work/lolm峡谷猫格/` | PRD+Demo完成，待评审 |
| 🃏 金铲铲「以铲换X」 | `jinchancha` | `10_Work/金铲铲/以铲换铲/` | VLM验证通过，待动态Demo |
| 🎴 小丑牌游戏 | `joker-card-game` | `40_Projects/joker-card-game/` | 开发完成，待内部测试 |
| 📚 游戏策划学习 | `game-study` | `20_Study/游戏策划/` | 持续学习中 |
| 📊 泡泡玛特财务分析 | `popmart-analysis` | 研究项目（无独立工作目录） | 研究进行中 |

> **项目分区路径**: `.codebuddy/memory/projects/<id>/`
> 每个项目包含: `context.md`（项目知识）+ `decisions.md`（决策记录）+ `learnings.md`（教训沉淀）
> **读取规则**: 涉及具体项目时，按需读取对应 `projects/<id>/` 下的文件

## 系统配置

- Git自动同步: launchd 每天11:00+23:00（不用crontab，macOS睡眠不执行）
- `.gitignore`: 排除 .DS_Store / Office临时文件(~$*) / 大文件(一图流xlsx/step1_5 csv)
- ⚠️ Git状态: 历史已用 filter-repo 重写清除大文件，需 `git push --force origin main` 完成同步
- Skills: 34个（17官方+13 Superpowers+4第三方），Skills周报每周一9:00自动生成
- CodeBuddy Rules: 5个专业角色（data-analyst / product-manager / game-designer / marketing-strategist / project-shepherd），全部 requested 类型。product-manager 已植入分级审查 Harness
- 同步脚本: `~/.local/bin/obsidian_git_sync.sh`（通过 osascript 绕过 TCC）
- UC 对局复盘 git: `10_Work/uc对局复盘/ucgit/go_ai_yr_postmatch_analysis_svr/`（master分支，git.woa.com）

## 关键教训（快速回忆）

1. macOS定时任务 → **永远用launchd**，crontab睡眠不执行
2. launchd访问~/Documents → 通过 **osascript** 绕过 TCC，比加 FDA 权限更可靠
3. UI设计 → **功能性 > 装饰性**，问自己"服务用户还是设计师审美？"
4. 状态覆盖 → 每个功能设计 **正常/空/错误** 三种状态
5. 新数据入库 → **先交叉校验**，标注一致/冲突/新增
6. CTA → 首页最显眼位置，核心任务为中心
7. Skills周报分析器 → **显式标注优先**，有 `Skills:` 行时只读标注行，避免语义误报
8. AI团队评审 → 多角色协作（PM+Tech+QA+项目管理）产出远超单角色
9. 需求文档 → **分级审查**（轻量自查/中等切对立角色/重型多角色评审），默认中等，只升不降
10. 错题本 → 同类错误 ≥3 次 → **自动提炼为硬性规则**写入对应 Rule/SOP，不是软提醒
11. Skills纪律 → **using-superpowers 是刚性流程**：每次用户消息→先检查有无 skill 适用（1% 可能性就调用）→再做任何事。绝不合理化跳过
12. 自我改进 → **self-improvement 是会话结束强制流程**（非自觉流程）：命令失败/用户纠正/发现更好方法/知识过时 → 立即记录到**项目根** `.learnings/`（非 Skill 内部目录）。**每次会话结束前必须执行 memory-system-v2.mdc 的"会话结束 Checklist → Step 1"**，回顾 6 种触发场景。遇到错误不记录 = 浪费学习机会
13. 工具输出 → **输出必须验证**：不假设工具自动正确（数据准确性/格式兼容性/流程执行度）。3次工具类错误共性：显式>推断、格式先验、写规则≠执行
14. VLM评分 → **递进式验证**：快验（10张）→分层50%抽样→分层20%看图→混淆矩阵→Prompt迭代。不跳过中间环节
15. 深度调研 → **多源交叉验证**：关键数据点至少2个独立来源确认，不依赖单一来源
16. 文件读取 → **先搜索再读取**：禁止凭猜测拼接路径，必须 `search_file` 确认完整路径。Obsidian Vault 目录嵌套深且文件可能在非预期位置
17. 大文件管理 → **新增大文件先查大小**：GitHub 硬限制100MB，推荐上限50MB。Excel数据文件容易超标（如一图流174MB），**新增前检查文件大小，超标的加入.gitignore**
18. 工作日志 → **每次会话结束必须写 episodic**：这是最低要求，不写=工作记录丢失。会话独立无法跨会话恢复，不写就永久丢失

## 已验证工作流

- **课程化**: 读笔记→搜原书目录→搜中文解读→拆章节→批量创建（含导航链接+跨书关联）
- **知识库扩充**: 读现有→Web搜索爬取→交叉校验→Excel多Sheet→独立文件→校验报告
- **原型迭代**: 第一性原理Review→问题分类(🔴🟡🟠)→从用户任务出发→实现+更新文档
- **H5 Demo快速原型**: PRD+Mock契约→单文件HTML(CSS+JS)→视觉升级→内容升级→功能迭代（逐步replace_in_file避免token溢出）
- **AI团队评审**: 组建多角色团队(PM/Tech/QA/PM)→各自产出→跨团队共识→综合报告→开发启动包
- **UC对局复盘测试**: 修改analysis.go→commit+push→upload_and_report.py批量测试→result.xlsx对比→数据分析
- **📅 每周方法论沉淀（周五自动）**: 读近7天episodic日志→识别可复用模式→对比30_Common/方法论/去重→新建或更新方法论.md→更新_README索引→记录episodic
- **📝 需求文档分级审查**: 写前三问→定级(🟢轻量/🟡中等/🔴重型)→按级别走审查策略→默认中等、只升不降
- **🔁 错误→规则自动化**: 错误记录→打标签归类→同类≥3次→分析共性→提炼硬性规则→写入Rule/SOP→标注已提炼
- **📋 周报生成**: 除了写详细 md 周报，还需在 md 最上方（frontmatter 和标题之后、`## ✅ 本周完成` 之前）生成一份**简报版**（按项目分组的纯文本摘要，格式与用户输入一致），用 `## 📋 周报简报` + `---` 分隔线与详细内容隔开
- **🔍 深度调研**: 多源Web搜索→网页抓取→交叉验证（关键数据≥2独立来源）→金字塔原理结构化报告
- **🎮 多Agent团队游戏开发**: GDD先行→多角色团队(dev/qa/art/design)→QA独立验证→多轮Bug修复闭环→达标关闭
- **🖼️ VLM视觉评分验证**: 快验(10张)→50%分层抽样→20%看图→混淆矩阵→WebUI→自包含HTML→Prompt迭代
- **🧹 子代理委派（上下文减负）**: 探索性操作（搜索≥3文件/Web搜索≥3次/批量读取≥5文件）→必须委派子代理→只取摘要→主上下文做决策执行
