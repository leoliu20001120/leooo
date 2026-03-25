# 🧠 MEMORY.md — AI 启动上下文

> v2.3 | 更新: 2026-03-24
> 设计原则: **读完此文件即可工作，无需跳转**

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
20_Study/ → 学习（游戏策划理论）
30_Common/→ 知识沉淀
40_Projects/→ 个人项目（CaloriSnap）
99_Templates/→ 模板库
```

## 活跃项目

### 🎮 UC 王也 NPC / 异人体检站 `10_Work/uc 王也 npc/`
- 状态: **已完成评审，Ready for Kick-off**
- 知识库: 1125+ 条（7个Excel文件），28条分场景回复、甲申之乱23条详解、十佬11人完整档案
- 异人体检站 H5:
  - 完整 Demo 已实现（`demo/index.html`），覆盖 STEP 0-4 全流程
  - 功能: 五行拆字批命 + 7轮争议话题对话 + 六维雷达报告 + 分享
  - 特色: Canvas粒子系统、玻璃态UI、Story Bottom Sheet、彩蛋ID
  - AI 团队综合评审完成（A-），评审报告 + 技术评审 + 测试策略 + Mock数据契约 + 开发启动包（73个TAPD任务）
  - 关键结论: 总工期 5-6周→8-9周，人天45→80-95，团队15-17人
- 文档索引: `_README.md`（18个文档 + 10个数据文件，5阶段分类）
- 决策: 新数据独立文件存储，不覆盖原有知识库

### 🎯 UC 对局复盘 `10_Work/uc对局复盘/`
- 状态: **迭代调优中**
- 后端仓库: `10_Work/uc对局复盘/ucgit/go_ai_yr_postmatch_analysis_svr/`（git.woa.com）
- 核心文件: `analysis.go`（复盘分析逻辑）
- 测试工具: `upload_and_report.py`（批量46个JSON→POST接口→result.xlsx）
- 数据分析产出:
  - 交互式分析报告 `analysis_report.html`（Plotly，五维雷达+趋势+角色进步+短板诊断）
  - label分布分析：「有待提升」集中于脱出反打(43.5%)+防御反击(34.8%)
  - 指标数字覆盖率：93.5% 无具体数字（模板化问题）
- 近期修改: jPoints跳转点调整、subdim_behId修复、子维度ID映射(27-30→41-44)

### 📱 CaloriSnap `40_Projects/CaloriSnap/`
- 状态: v0.3原型完成，待Phase 0技术验证
- 定位: 拍照识别奶茶/咖啡标签→计算热量+咖啡因
- 技术: 微信小程序 + FastAPI + Supabase + OCR/LLM
- 数据: 7品牌160+SKU，35+小料，8表+2视图+RLS

### 🏺 景德镇工作坊 `10_Work/景德镇/`
- 状态: 中期开发，设计方案与监修（清华）基本对齐
- AI NPC: 动画数据驱动+LLM+TTS，延迟7-8s待优化至≤3s
- 景德镇游戏: 制瓷历史模拟经营（宋→清四幕），美术80-90%
- 关键节点: 3月底订单系统+精修数据，4/22 CG片段，6月初成片

### 📚 游戏策划学习 `20_Study/游戏策划/`
- 《游戏设计艺术》Jesse Schell → 36文件课程（113个透镜）
- 《快乐之道》Raph Koster → 16文件课程（快乐=学习理论）

## 系统配置

- Git自动同步: launchd 每天11:00+23:00（不用crontab，macOS睡眠不执行）
- Skills: 22个（17官方+5第三方），Skills周报每周一9:00自动生成
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
