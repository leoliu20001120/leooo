---
type: readme
updated: "2026-03-18"
---

# 📊 Skills 周报

> CodeBuddy Skills 使用量每周统计报告，自动生成。

## 说明

每周自动分析 `.codebuddy/memory/` 中的日志，提取 Skill 使用数据，生成包含以下内容的周报：

1. **📈 使用量排行** — 哪些 Skills 用得最多
2. **🧩 分类分布** — 创意设计/开发工具/文档处理等分类占比
3. **🔍 问题明细** — 每个 Skill 本周解决了什么具体问题
4. **🕐 每日时间线** — 按天查看使用情况
5. **🧠 智能洞察** — AI 分析趋势和建议

## 文件命名

```
Skills周报_W{周数}_{年}_{月日}.md
```

例：`Skills周报_W12_2026_0316.md`

## 生成方式

- **自动**: 每周一由 CodeBuddy Automation 自动生成上周报告
- **手动**: 运行 `.codebuddy/skills_tracker/weekly_report_generator.py --save`

## 相关文件

| 文件 | 说明 |
|------|------|
| `.codebuddy/skills_tracker/skill_analyzer.py` | 分析引擎 |
| `.codebuddy/skills_tracker/weekly_report_generator.py` | 周报生成器 |
| `_latest_report.md` | 最新一期周报（快捷入口） |
