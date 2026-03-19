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

## Skills 周报系统

| 项目 | 值 |
|------|-----|
| 分析引擎 | `.codebuddy/skills_tracker/skill_analyzer.py` |
| 周报生成 | `.codebuddy/skills_tracker/weekly_report_generator.py` |
| 报告目录 | `10_Work/skills_weekly_reports/` |
| 自动化 | 每周一 9:00 生成上周周报 |
| 命令 | `python3 .codebuddy/skills_tracker/weekly_report_generator.py --last-week --save` |

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
