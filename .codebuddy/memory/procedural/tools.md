# 🔨 程序记忆：工具使用技巧与配置

> 工具配置、使用技巧、系统设置
> 标签: #memory/procedural #tools

---

## Git 配置

| 项目 | 值 |
|------|-----|
| 远程仓库 | `git@github.com:leoliu20001120/leooo.git` |
| 分支 | `main` |
| 用户名 | `leoliu20001120` |
| 邮箱 | `leoliu20001120@gmail.com` |
| 认证 | SSH (`~/.ssh/id_ed25519`) |

### UC 对局复盘 Git（工作仓库）

| 项目 | 值 |
|------|-----|
| 本地路径 | `10_Work/uc对局复盘/ucgit/go_ai_yr_postmatch_analysis_svr/` |
| 远程仓库 | `https://git.woa.com/gametalk_backend/ai/go_ai_yr_postmatch_analysis_svr.git` |
| 分支 | `master` |
| 核心文件 | `analysis.go`（~739行，Go语言复盘分析逻辑） |
| 快捷指令 | 用户说"ucgit pull/push/commit" = 在该目录下执行对应 git 操作 |
| 测试接口 | `http://30.189.253.210:8080/fight/report` |
| 测试脚本 | `upload_and_report.py`（批量 POST 46个JSON → result.xlsx） |

## 自动同步 (launchd)

| 项目 | 值 |
|------|-----|
| 脚本 | `~/.local/bin/obsidian_git_sync.sh` |
| plist | `~/Library/LaunchAgents/com.obsidian.gitsync.plist` |
| 频率 | 每天 11:00 + 23:00 |
| 日志 | `~/.local/log/obsidian_git_sync.log` |
| 注意 | ⚠️ 不要用 crontab，macOS 睡眠不执行 |

## CodeBuddy Skills

### 已安装列表（22个）

**Anthropic 官方 (17个):**
algorithmic-art, brand-guidelines, canvas-design, claude-api, doc-coauthoring, docx, frontend-design, internal-comms, mcp-builder, pdf, pptx, skill-creator, slack-gif-creator, theme-factory, web-artifacts-builder, webapp-testing, xlsx

**第三方 (5个):**
memory-management, using-superpowers, planning-with-files, markitdown, self-improving-agent

### 安装方式
- 全局: `~/.agents/skills/`
- 项目级: `.codebuddy/skills/` (软链接)

## CodeBuddy Rules（5个专业角色）

| Rule | 类型 | 用途 |
|------|------|------|
| data-analyst | requested | 数据分析、KPI追踪、A/B测试、漏斗分析、SQL/Python脚本 |
| product-manager | requested | PRD、机会评估、路线图、GTM、Sprint状态 |
| game-designer | requested | 游戏系统设计、GDD、核心循环、经济平衡、玩家引导 |
| marketing-strategist | requested | 营销策略、内容规划、编辑日历、增长实验、竞品分析 |
| project-shepherd | requested | 项目章程、WBS、RACI、风险管理、状态报告、复盘 |

- 全部 requested 类型，需主动引用激活
- 基于 agency-agents 仓库裁剪，本地化（中文+金字塔原理）

## Skills 周报系统

| 项目 | 值 |
|------|-----|
| 分析引擎 | `.codebuddy/skills_tracker/skill_analyzer.py` |
| 周报生成 | `.codebuddy/skills_tracker/weekly_report_generator.py` |
| 报告目录 | `10_Work/skills_weekly_reports/` |
| 自动化 | 每周一 9:00 生成上周周报 |
| 命令 | `python3 .codebuddy/skills_tracker/weekly_report_generator.py --last-week --save` |

### 分析器修复记录（2026-03-23）
- **问题**: 语义推断把大量 `Skills: 无` 的工作误归类
- **修复**: 显式模式优先——有 `Skills:` 标注行时只读标注行，未标注段落默认"无"
- **新增**: 5个自建Rule Skills（data-analyst等）+ 4个分类（数据分析/产品设计/营销策略/项目管理）

## Obsidian MCP Server

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "npx",
      "args": ["mcp-obsidian"]
    }
  }
}
```

## Self-Improvement 系统 (.learnings/)

| 文件 | 用途 |
|------|------|
| `.learnings/LEARNINGS.md` | 教训/最佳实践/纠正记录（LRN-YYYYMMDD-XXX格式） |
| `.learnings/ERRORS.md` | 命令/工具执行错误记录 |
| `.learnings/FEATURE_REQUESTS.md` | 用户请求的缺失能力 |

**当前状态**: 10条Learning（1条 correction + 8条 best_practice + 1条 knowledge_gap），6条已promoted，2条pending，1条resolved

**与记忆系统的关系**:
- `.learnings/` = 系统化分析（为什么错/怎么变好）
- `procedural/skills.md` 错题本 = 简洁教训速查
- 两者互补，`.learnings/` 详细分析 → 提炼为错题本简洁条目 + 关键教训写入 MEMORY.md
