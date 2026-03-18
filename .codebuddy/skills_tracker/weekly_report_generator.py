#!/usr/bin/env python3
"""
Skills Weekly Report Generator
===============================
生成漂亮的 Markdown 周报，在 Obsidian 中可视化效果良好。
使用纯文本 + Mermaid + Callout 实现丰富的展示效果。
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# 导入分析器
sys.path.insert(0, str(Path(__file__).parent))
from skill_analyzer import (
    analyze_week, get_week_range, get_last_week_range,
    KNOWN_SKILLS, CATEGORIES
)


def bar_chart(value, max_value, width=20, filled="█", empty="░"):
    """生成纯文本条形图"""
    if max_value == 0:
        return empty * width
    fill_count = int((value / max_value) * width)
    return filled * fill_count + empty * (width - fill_count)


def sparkline(values, chars="▁▂▃▄▅▆▇█"):
    """生成迷你趋势图"""
    if not values:
        return ""
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return chars[4] * len(values)
    result = ""
    for v in values:
        idx = int((v - min_v) / (max_v - min_v) * (len(chars) - 1))
        result += chars[idx]
    return result


def generate_mermaid_pie(stats):
    """生成 Mermaid 饼图（按分类）"""
    by_cat = stats["by_category"]
    if not by_cat:
        return ""
    
    lines = ['```mermaid', 'pie showData']
    lines.append('    title Skills 分类使用占比')
    for cat, data in sorted(by_cat.items(), key=lambda x: x[1]["count"], reverse=True):
        emoji = CATEGORIES.get(cat, "")
        lines.append(f'    "{emoji} {cat}" : {data["count"]}')
    lines.append('```')
    return "\n".join(lines)


def generate_mermaid_bar(stats):
    """生成 Mermaid 柱状图（按日期）"""
    by_date = stats["by_date"]
    if not by_date:
        return ""
    
    lines = ['```mermaid', 'xychart-beta']
    lines.append('    title "每日 Skills 使用量"')
    
    dates = sorted(by_date.keys())
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    # 补全一周七天
    if dates:
        first = datetime.strptime(dates[0], "%Y-%m-%d").date()
        week_start = first - timedelta(days=first.weekday())
        all_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    else:
        all_dates = dates
    
    labels = []
    values = []
    for d in all_dates:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        day_label = weekdays[dt.weekday()]
        labels.append(f'"{day_label}"')
        values.append(str(by_date.get(d, {"count": 0})["count"]))
    
    lines.append(f'    x-axis [{", ".join(labels)}]')
    lines.append(f'    y-axis "使用次数" 0 --> {max(int(v) for v in values) + 2}')
    lines.append(f'    bar [{", ".join(values)}]')
    lines.append('```')
    return "\n".join(lines)


def generate_skill_rank_table(stats):
    """生成 Skill 排行榜表格"""
    by_skill = stats["by_skill"]
    if not by_skill:
        return "> 本周暂无 Skill 使用记录 🫥\n"
    
    max_count = max(d["count"] for d in by_skill.values())
    
    lines = []
    lines.append("| 排名 | Skill | 使用次数 | 热度 | 分类 |")
    lines.append("|:----:|-------|:--------:|------|------|")
    
    rank = 1
    medals = ["🥇", "🥈", "🥉"]
    for skill, data in sorted(by_skill.items(), key=lambda x: x[1]["count"], reverse=True):
        info = KNOWN_SKILLS.get(skill, {"emoji": "❓", "category": "未知"})
        medal = medals[rank - 1] if rank <= 3 else f" {rank} "
        bar = bar_chart(data["count"], max_count, width=10)
        lines.append(
            f"| {medal} | {info['emoji']} **{skill}** | {data['count']} | {bar} | {info['category']} |"
        )
        rank += 1
    
    return "\n".join(lines)


def generate_problem_solved_section(stats):
    """生成每个 Skill 解决的问题明细"""
    by_skill = stats["by_skill"]
    if not by_skill:
        return ""
    
    lines = []
    for skill, data in sorted(by_skill.items(), key=lambda x: x[1]["count"], reverse=True):
        info = KNOWN_SKILLS.get(skill, {"emoji": "❓", "category": "未知"})
        lines.append(f"### {info['emoji']} {skill}")
        lines.append("")
        
        # 按日期分组
        problems_by_date = defaultdict(list)
        for p in data["problems"]:
            problems_by_date[p["date"]].append(p)
        
        for date, problems in sorted(problems_by_date.items()):
            for p in problems:
                lines.append(f"- **`{date}`** — {p['title']}")
                if p["desc"] and p["desc"] != p["title"]:
                    lines.append(f"  - {p['desc'][:120]}")
        lines.append("")
    
    return "\n".join(lines)


def generate_daily_timeline(stats):
    """生成每日时间线"""
    daily = stats["daily_breakdown"]
    if not daily:
        return ""
    
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    lines = []
    for date_str in sorted(daily.keys()):
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = weekday_names[dt.weekday()]
        items = daily[date_str]
        
        skill_counts = defaultdict(int)
        skill_titles = defaultdict(list)
        for item in items:
            skill_counts[item["skill"]] += 1
            skill_titles[item["skill"]].append(item["title"])
        
        lines.append(f"#### 📅 {date_str} ({day_name})")
        lines.append("")
        
        for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True):
            info = KNOWN_SKILLS.get(skill, {"emoji": "❓"})
            titles = skill_titles[skill]
            title_str = "、".join(set(t[:30] for t in titles))
            lines.append(f"- {info['emoji']} **{skill}** ×{count} — {title_str}")
        
        lines.append("")
    
    return "\n".join(lines)


def generate_category_breakdown(stats):
    """生成分类饼图区域"""
    by_cat = stats["by_category"]
    if not by_cat:
        return ""
    
    total = sum(d["count"] for d in by_cat.values())
    
    lines = []
    for cat, data in sorted(by_cat.items(), key=lambda x: x[1]["count"], reverse=True):
        emoji = CATEGORIES.get(cat, "❓")
        pct = (data["count"] / total * 100) if total > 0 else 0
        bar = bar_chart(data["count"], total, width=15)
        skills_list = ", ".join(data["skills"])
        lines.append(f"| {emoji} **{cat}** | {data['count']} | {pct:.0f}% | {bar} |")
    
    header = "| 分类 | 次数 | 占比 | 分布 |\n|------|:----:|:----:|------|"
    return header + "\n" + "\n".join(lines)


def generate_insights(stats):
    """生成智能洞察"""
    insights = []
    by_skill = stats["by_skill"]
    by_cat = stats["by_category"]
    total = stats["total_uses"]
    
    if total == 0:
        return "> 💤 本周没有 Skill 使用记录，期待下周的数据！\n"
    
    # 最常用 skill
    if by_skill:
        top_skill = max(by_skill.items(), key=lambda x: x[1]["count"])
        info = KNOWN_SKILLS.get(top_skill[0], {"emoji": "❓"})
        insights.append(
            f"🏆 **本周 MVP**: {info['emoji']} `{top_skill[0]}`，使用了 **{top_skill[1]['count']}** 次"
        )
    
    # 最活跃分类
    if by_cat:
        top_cat = max(by_cat.items(), key=lambda x: x[1]["count"])
        emoji = CATEGORIES.get(top_cat[0], "❓")
        insights.append(
            f"📂 **最活跃分类**: {emoji} {top_cat[0]}，共 {top_cat[1]['count']} 次"
        )
    
    # 未使用的 skills
    used_skills = set(by_skill.keys())
    all_skills = set(KNOWN_SKILLS.keys())
    unused = all_skills - used_skills
    if unused:
        insights.append(
            f"💡 **待探索**: 还有 **{len(unused)}** 个 Skill 本周未使用，"
            f"考虑试试 {', '.join(f'`{s}`' for s in list(unused)[:3])}？"
        )
    
    # 活跃天数
    active_days = len(stats["by_date"])
    insights.append(f"📅 **活跃天数**: {active_days} 天使用了 Skills")
    
    # 多样性指数
    diversity = stats["unique_skills"] / len(KNOWN_SKILLS) * 100 if KNOWN_SKILLS else 0
    insights.append(f"🌈 **多样性指数**: {diversity:.0f}%（使用了 {stats['unique_skills']}/{len(KNOWN_SKILLS)} 个 Skills）")
    
    return "\n".join(f"- {i}" for i in insights)


def generate_weekly_report(start_date=None, end_date=None):
    """生成完整的周报 Markdown"""
    result = analyze_week(start_date, end_date)
    stats = result["stats"]
    period = result["period"]
    
    week_num = period["week_number"]
    
    report = f"""---
type: skills-weekly-report
week: {week_num}
period: "{period['start']} ~ {period['end']}"
generated: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
tags:
  - skills-report
  - weekly
---

# 📊 Skills 周报 — W{week_num}

> **统计周期**: {period['start']} ~ {period['end']}
> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📈 本周概览

> [!summary] 数据速览
> | 指标 | 数值 |
> |------|------|
> | 📦 总使用次数 | **{stats['total_uses']}** |
> | 🧩 涉及 Skills | **{stats['unique_skills']}** 个 |
> | 📁 涉及分类 | **{len(stats['by_category'])}** 个 |
> | 📅 活跃天数 | **{len(stats['by_date'])}** 天 |
> | 📝 日志文件数 | **{result['entries_count']}** 个 |

---

## 🏅 Skills 排行榜

{generate_skill_rank_table(stats)}

---

## 📊 可视化

### 每日使用趋势

{generate_mermaid_bar(stats)}

### 分类使用占比

{generate_mermaid_pie(stats)}

### 分类明细

{generate_category_breakdown(stats)}

---

## 🧠 智能洞察

> [!tip] AI 分析
{chr(10).join('> ' + line for line in generate_insights(stats).split(chr(10)))}

---

## 🔍 Skill × 问题 明细

> 每个 Skill 本周解决了哪些具体问题？

{generate_problem_solved_section(stats)}

---

## 🕐 每日时间线

{generate_daily_timeline(stats)}

---

## 📋 完整 Skills 使用清单

> [!info] 全部 {len(KNOWN_SKILLS)} 个已安装 Skills

{generate_full_skill_list(stats)}

---

<div style="text-align:center; color:#888; font-size:0.85em; margin-top:2em;">

🤖 由 CodeBuddy Skills Tracker 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}

</div>
"""
    return report


def generate_full_skill_list(stats):
    """生成完整 Skill 清单（标记使用状态）"""
    by_skill = stats["by_skill"]
    
    lines = []
    lines.append("| Skill | 分类 | 本周 | 状态 |")
    lines.append("|-------|------|:----:|------|")
    
    for skill, info in sorted(KNOWN_SKILLS.items()):
        count = by_skill.get(skill, {}).get("count", 0)
        status = f"✅ {count}次" if count > 0 else "⬜ 未使用"
        lines.append(f"| {info['emoji']} {skill} | {info['category']} | {count} | {status} |")
    
    return "\n".join(lines)


def save_report(report, start_date):
    """保存周报到知识库"""
    workspace = Path(__file__).resolve().parent.parent.parent
    reports_dir = workspace / "10_Work" / "skills_weekly_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    week_num = start_date.isocalendar()[1]
    year = start_date.year
    filename = f"Skills周报_W{week_num}_{year}_{start_date.strftime('%m%d')}.md"
    filepath = reports_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    
    # 同时保存一份到 _latest
    latest = reports_dir / "_latest_report.md"
    with open(latest, "w", encoding="utf-8") as f:
        f.write(report)
    
    return filepath


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Skills 周报生成器")
    parser.add_argument("--last-week", action="store_true", help="生成上周的报告")
    parser.add_argument("--start", type=str, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--save", action="store_true", help="保存报告到知识库")
    parser.add_argument("--stdout", action="store_true", help="输出到标准输出")
    args = parser.parse_args()
    
    if args.last_week:
        start_date, end_date = get_last_week_range()
    elif args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    else:
        start_date, end_date = get_week_range()
    
    report = generate_weekly_report(start_date, end_date)
    
    if args.stdout or not args.save:
        print(report)
    
    if args.save:
        filepath = save_report(report, start_date)
        print(f"\n✅ 周报已保存到: {filepath}")


if __name__ == "__main__":
    main()
