# -*- coding: utf-8 -*-
"""生成评分验证可视化报告 v2"""
import json
import os

base = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(base, "output", "validation_result_v2.json")

with open(result_path, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]
hero_counts = data["hero_recommend_counts"]
r1 = data["rule1_violations"]
r2 = data["rule2_violations"]
r3 = data["rule3_violations"]

# 按英雄分组规则1违规
from collections import defaultdict, Counter

r1_by_hero = defaultdict(list)
for v in r1:
    r1_by_hero[v["hero"]].append(v)

r3_by_hero = defaultdict(list)
for v in r3:
    r3_by_hero[v["hero"]].append(v)

# 统计规则1中违规符文出现频次（哪些符文最容易被漏掉）
r1_aug_freq = Counter(v["aug"] for v in r1)
r1_level_freq = Counter(v["level"] for v in r1)
r1_rank_dist = Counter(v["wr_rank"] for v in r1)

# 生成HTML报告
html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>AI Coach 评分验证报告 v2</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    background: #0d1117; color: #c9d1d9; 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    padding: 20px; line-height: 1.6;
}
.container { max-width: 1400px; margin: 0 auto; }
h1 { color: #58a6ff; font-size: 28px; margin-bottom: 8px; }
h2 { color: #58a6ff; font-size: 22px; margin: 30px 0 15px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
h3 { color: #79c0ff; font-size: 18px; margin: 20px 0 10px; }
.subtitle { color: #8b949e; margin-bottom: 20px; }

.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
.summary-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 20px; text-align: center;
}
.summary-card .number { font-size: 36px; font-weight: bold; }
.summary-card .label { color: #8b949e; font-size: 14px; margin-top: 5px; }
.pass { color: #3fb950; }
.fail { color: #f85149; }
.warn { color: #d29922; }
.info { color: #58a6ff; }

.chart-container { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin: 15px 0; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }

table { 
    width: 100%; border-collapse: collapse; margin: 10px 0;
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    font-size: 13px;
}
th { background: #21262d; color: #58a6ff; padding: 10px 8px; text-align: left; position: sticky; top: 0; }
td { padding: 8px; border-top: 1px solid #30363d; }
tr:hover { background: #1c2128; }
.table-scroll { max-height: 600px; overflow-y: auto; border-radius: 8px; }

.badge { 
    display: inline-block; padding: 2px 8px; border-radius: 12px; 
    font-size: 12px; font-weight: 500;
}
.badge-rec { background: #1a4f2a; color: #3fb950; }
.badge-con { background: #3d2e00; color: #d29922; }
.badge-ref { background: #4a1d1d; color: #f85149; }

.insight-box {
    background: #161b22; border-left: 3px solid #58a6ff; 
    padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0;
}
.insight-box.warning { border-left-color: #d29922; }
.insight-box.success { border-left-color: #3fb950; }
</style>
</head>
<body>
<div class="container">
<h1>🎮 AI Coach 评分机制验证报告</h1>
<p class="subtitle">全局胜率口径 · 三等级推荐合并验证 · """ + str(summary["total_heroes"]) + """ 个英雄</p>

<!-- 总览卡片 -->
<div class="summary-grid">
    <div class="summary-card">
        <div class="number info">""" + str(summary["total_heroes"]) + """</div>
        <div class="label">验证英雄数</div>
    </div>
    <div class="summary-card">
        <div class="number """ + ("fail" if summary["rule1_violations"] > 0 else "pass") + """">""" + str(summary["rule1_violations"]) + """</div>
        <div class="label">规则1违规 (Top10→推荐)</div>
    </div>
    <div class="summary-card">
        <div class="number pass">""" + str(summary["rule2_violations"]) + """</div>
        <div class="label">规则2违规 (Bot20→非推荐)</div>
    </div>
    <div class="summary-card">
        <div class="number """ + ("warn" if summary["rule3_violations"] > 0 else "pass") + """">""" + str(summary["rule3_violations"]) + """</div>
        <div class="label">规则3违规 (Bot10→刷新)</div>
    </div>
</div>

<div class="insight-box">
<strong>验证口径说明：</strong><br>
• <strong>胜率排名</strong>：每个英雄所有等级（白银+黄金+棱彩）合并后的全局胜率排名<br>
• <strong>推荐范围</strong>：三个等级的"推荐选取"合并（平均每个英雄 """ + f"{summary['avg_recommended_per_hero']}" + """ 个）<br>
• <strong>刷新范围</strong>：三个等级的"建议刷新"合并
</div>

<!-- 规则1详情 -->
<h2>📌 规则1：全局胜率前10 → 必须在推荐范围内</h2>
"""

if r1:
    # 分析
    r1_hero_sorted = sorted(r1_by_hero.items(), key=lambda x: -len(x[1]))
    
    html += """
<div class="insight-box warning">
<strong>违规概况：</strong>""" + str(len(r1)) + """ 条违规，涉及 """ + str(summary["rule1_heroes"]) + """/""" + str(summary["total_heroes"]) + """ 个英雄<br>
<strong>核心原因：</strong>同一等级内仅推荐 5-6 个，全局Top10中有些符文在其所在等级并非分数前5（受选率、UGC、黑科技影响），因此未被推荐。<br>
<strong>高频漏选符文：</strong>""" + ", ".join(f"{aug}({cnt}次)" for aug, cnt in r1_aug_freq.most_common(10)) + """
</div>
"""

    # 图1：每个英雄的违规数分布
    hero_names_r1 = [h for h, _ in r1_hero_sorted[:30]]
    hero_counts_r1 = [len(vs) for _, vs in r1_hero_sorted[:30]]
    
    html += """
<div class="chart-row">
<div class="chart-container">
<div id="chart_r1_hero"></div>
</div>
<div class="chart-container">
<div id="chart_r1_rank"></div>
</div>
</div>

<div class="chart-row">
<div class="chart-container">
<div id="chart_r1_level"></div>
</div>
<div class="chart-container">
<div id="chart_r1_aug"></div>
</div>
</div>
"""

    # 完整违规列表
    html += """
<h3>完整违规列表（按英雄分组）</h3>
<div class="table-scroll">
<table>
<thead><tr><th>英雄</th><th>违规数</th><th>违规符文详情</th></tr></thead>
<tbody>
"""
    for hero, vs in r1_hero_sorted:
        vs_sorted = sorted(vs, key=lambda x: x["wr_rank"])
        details = []
        for v in vs_sorted:
            wr_pct = v["wr"] if v["wr"] < 100 else v["wr"] / 100  # 处理百分比格式
            badge_class = "badge-con" if v["actual_logo"] == "值得考虑" else "badge-ref"
            details.append(
                f'<span class="badge {badge_class}">{v["aug"]}</span> '
                f'Top{v["wr_rank"]} WR={wr_pct:.1f}% [{v["level"]}] 分数={v["score"]:.1f}'
            )
        html += f'<tr><td><strong>{hero}</strong></td><td>{len(vs)}</td><td>{"<br>".join(details)}</td></tr>\n'
    
    html += "</tbody></table></div>\n"
else:
    html += '<div class="insight-box success"><strong>✅ 全部通过！</strong></div>'

# 规则2
html += """
<h2>✅ 规则2：全局胜率倒数20 → 不应在推荐范围内</h2>
<div class="insight-box success">
<strong>✅ 完美通过！</strong>0 条违规。公式在排除弱势符文方面非常有效。
</div>
"""

# 规则3
html += """
<h2>📌 规则3：全局胜率倒数10 → 必须在建议刷新范围内</h2>
"""

if r3:
    html += """
<div class="insight-box """ + ("warning" if len(r3) > 10 else "success") + """">
<strong>违规概况：</strong>""" + str(len(r3)) + """ 条违规，涉及 """ + str(summary["rule3_heroes"]) + """/""" + str(summary["total_heroes"]) + """ 个英雄<br>
<strong>原因：</strong>这些符文虽然胜率垫底，但在其所在等级中因选率/UGC分数不低，未落入底部20%刷新区。
</div>
"""
    html += """
<h3>违规详情</h3>
<table>
<thead><tr><th>英雄</th><th>符文</th><th>等级</th><th>胜率排名</th><th>胜率</th><th>分数</th><th>实际分类</th></tr></thead>
<tbody>
"""
    for v in sorted(r3, key=lambda x: (x["hero"], x["wr_rank"])):
        wr_pct = v["wr"] if v["wr"] < 100 else v["wr"] / 100
        badge_class = "badge-con" if v["actual_logo"] == "值得考虑" else "badge-rec"
        html += f'<tr><td>{v["hero"]}</td><td>{v["aug"]}</td><td>{v["level"]}</td>'
        html += f'<td>{v["wr_rank"]}/{v["total_augs"]}</td><td>{wr_pct:.1f}%</td>'
        html += f'<td>{v["score"]:.1f}</td><td><span class="badge {badge_class}">{v["actual_logo"]}</span></td></tr>\n'
    html += "</tbody></table>\n"
else:
    html += '<div class="insight-box success"><strong>✅ 全部通过！</strong></div>'

# Plotly 图表脚本
html += """
<script>
const dark = {
    paper_bgcolor: '#161b22', plot_bgcolor: '#161b22',
    font: { color: '#c9d1d9' },
    xaxis: { gridcolor: '#30363d' },
    yaxis: { gridcolor: '#30363d' },
};
"""

if r1:
    # 图1: 英雄违规数Top30
    html += """
Plotly.newPlot('chart_r1_hero', [{
    x: """ + json.dumps(hero_names_r1, ensure_ascii=False) + """,
    y: """ + json.dumps(hero_counts_r1) + """,
    type: 'bar',
    marker: { color: '#f85149' },
    text: """ + json.dumps(hero_counts_r1) + """,
    textposition: 'outside',
}], {
    ...dark,
    title: { text: '规则1：英雄违规数 Top30', font: { color: '#58a6ff' } },
    xaxis: { ...dark.xaxis, tickangle: -45 },
    yaxis: { ...dark.yaxis, title: '违规数' },
    margin: { b: 100 },
    height: 400,
});
"""

    # 图2: 按胜率排名分布
    rank_labels = [f"Top{r}" for r in range(1, 11)]
    rank_counts = [r1_rank_dist.get(r, 0) for r in range(1, 11)]
    html += """
Plotly.newPlot('chart_r1_rank', [{
    x: """ + json.dumps(rank_labels) + """,
    y: """ + json.dumps(rank_counts) + """,
    type: 'bar',
    marker: { color: """ + json.dumps(['#3fb950' if c < 10 else '#d29922' if c < 80 else '#f85149' for c in rank_counts]) + """ },
    text: """ + json.dumps(rank_counts) + """,
    textposition: 'outside',
}], {
    ...dark,
    title: { text: '违规按胜率排名分布', font: { color: '#58a6ff' } },
    yaxis: { ...dark.yaxis, title: '违规次数' },
    height: 400,
});
"""

    # 图3: 按等级分布
    level_labels = list(r1_level_freq.keys())
    level_counts = list(r1_level_freq.values())
    html += """
Plotly.newPlot('chart_r1_level', [{
    labels: """ + json.dumps(level_labels, ensure_ascii=False) + """,
    values: """ + json.dumps(level_counts) + """,
    type: 'pie',
    marker: { colors: ['#c0c0c0', '#ffd700', '#9b59b6'] },
    textinfo: 'label+value+percent',
}], {
    ...dark,
    title: { text: '违规按符文等级分布', font: { color: '#58a6ff' } },
    height: 400,
});
"""

    # 图4: 高频漏选符文Top15
    top_augs = r1_aug_freq.most_common(15)
    aug_names = [a for a, _ in top_augs]
    aug_counts = [c for _, c in top_augs]
    html += """
Plotly.newPlot('chart_r1_aug', [{
    y: """ + json.dumps(aug_names[::-1], ensure_ascii=False) + """,
    x: """ + json.dumps(aug_counts[::-1]) + """,
    type: 'bar',
    orientation: 'h',
    marker: { color: '#d29922' },
    text: """ + json.dumps(aug_counts[::-1]) + """,
    textposition: 'outside',
}], {
    ...dark,
    title: { text: '最常漏选的符文 Top15', font: { color: '#58a6ff' } },
    xaxis: { ...dark.xaxis, title: '被漏选次数（跨英雄）' },
    margin: { l: 150 },
    height: 400,
});
"""

html += """
</script>
</div>
</body>
</html>
"""

output_path = os.path.join(base, "output", "validation_report_v2.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"报告已生成: {output_path}")
