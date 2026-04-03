# -*- coding: utf-8 -*-
"""
评分验证可视化报告生成
读取 validation_result.json，生成 plotly 交互式图表
"""
import json
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

base = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(base, "output", "validation_result.json")

with open(result_path, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]
r1 = pd.DataFrame(data["rule1_violations"])
r3 = pd.DataFrame(data["rule3_violations"])

# ==================== 综合报告页面 ====================
html_parts = []
html_parts.append("""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>AI Coach 评分机制验证报告</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1117; color: #e0e0e0; }
.container { max-width: 1400px; margin: 0 auto; padding: 24px; }
h1 { font-size: 28px; color: #fff; margin-bottom: 8px; }
h2 { font-size: 22px; color: #60a5fa; margin: 32px 0 16px; border-left: 4px solid #60a5fa; padding-left: 12px; }
h3 { font-size: 18px; color: #93c5fd; margin: 20px 0 10px; }
.subtitle { color: #888; font-size: 14px; margin-bottom: 24px; }
.summary-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }
.card { background: #1a1d26; border-radius: 12px; padding: 20px; border: 1px solid #2a2d36; }
.card-value { font-size: 36px; font-weight: 700; margin: 8px 0; }
.card-label { font-size: 13px; color: #888; }
.card-sub { font-size: 12px; color: #666; margin-top: 4px; }
.pass { color: #22c55e; }
.fail { color: #ef4444; }
.warn { color: #eab308; }
.chart-container { background: #1a1d26; border-radius: 12px; padding: 20px; margin: 16px 0; border: 1px solid #2a2d36; }
.insight { background: #1e293b; border-left: 3px solid #60a5fa; padding: 12px 16px; margin: 12px 0; border-radius: 0 8px 8px 0; font-size: 14px; line-height: 1.6; }
.insight b { color: #93c5fd; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
th { background: #1e293b; color: #93c5fd; padding: 10px 8px; text-align: left; border-bottom: 2px solid #2a2d36; }
td { padding: 8px; border-bottom: 1px solid #1e293b; }
tr:hover { background: #1e293b; }
.tag-pass { background: #166534; color: #86efac; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.tag-fail { background: #7f1d1d; color: #fca5a5; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.tag-warn { background: #78350f; color: #fde68a; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.section-divider { border: none; border-top: 1px solid #2a2d36; margin: 32px 0; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
</style>
</head>
<body>
<div class="container">
<h1>🔍 AI Coach 评分机制验证报告</h1>
<p class="subtitle">验证范围：172 个英雄 × 3 等级（白银/黄金/棱彩），标准模式 (streak=0)</p>
""")

# ==================== 汇总卡片 ====================
html_parts.append(f"""
<div class="summary-cards">
  <div class="card">
    <div class="card-label">总违规数</div>
    <div class="card-value fail">{summary['total_violations']}</div>
    <div class="card-sub">3 条规则合计</div>
  </div>
  <div class="card">
    <div class="card-label">规则1: 胜率Top10→推荐</div>
    <div class="card-value fail">{summary['rule1_violations']}</div>
    <div class="card-sub">{summary['rule1_heroes']}/172 英雄违规（100%）</div>
  </div>
  <div class="card">
    <div class="card-label">规则2: 胜率Bot20→非推荐</div>
    <div class="card-value pass">{summary['rule2_violations']}</div>
    <div class="card-sub">{summary['rule2_heroes']}/172 英雄违规（0%）✅ 全部通过</div>
  </div>
  <div class="card">
    <div class="card-label">规则3: 胜率Bot10→刷新</div>
    <div class="card-value warn">{summary['rule3_violations']}</div>
    <div class="card-sub">{summary['rule3_heroes']}/172 英雄违规（99%）</div>
  </div>
</div>
""")

# ==================== 规则1 深入分析 ====================
html_parts.append("""
<hr class="section-divider">
<h2>📌 规则1：胜率前10的符文必须在推荐范围内</h2>
""")

# 核心发现
html_parts.append(f"""
<div class="insight">
<b>核心发现：</b>每个英雄、每个等级平均有 <b>{len(r1)/172/3:.1f}</b> 个胜率Top10符文未被推荐。
这是结构性问题——当前公式每等级仅推荐 <b>5 个</b>（最多6个），但验证口径要求前10都被推荐。<br>
<b>根本原因：</b>评分公式综合了胜率、选率、UGC三个维度 + 黑科技加成，胜率高但选率/UGC低的符文，最终排名可能跌出前5。
</div>
""")

# 图1: 按等级的违规分布
r1_by_level = r1.groupby("level").size().reset_index(name="count")
level_order = ["白银", "黄金", "棱彩"]
r1_by_level["level"] = pd.Categorical(r1_by_level["level"], categories=level_order, ordered=True)
r1_by_level = r1_by_level.sort_values("level")

fig1 = go.Figure()
colors = {"白银": "#94a3b8", "黄金": "#fbbf24", "棱彩": "#a78bfa"}
for _, row in r1_by_level.iterrows():
    fig1.add_trace(go.Bar(
        x=[row["level"]], y=[row["count"]],
        name=row["level"],
        marker_color=colors.get(row["level"], "#60a5fa"),
        text=[row["count"]], textposition="outside",
    ))
fig1.update_layout(
    title="规则1违规数 - 按符文等级",
    xaxis_title="符文等级", yaxis_title="违规数",
    template="plotly_dark", showlegend=False,
    height=350, margin=dict(t=50, b=40),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart1"></div><script>Plotly.newPlot("chart1", {fig1.to_json()});</script>')
html_parts.append('</div>')

# 图2: 按胜率排名分布（Top几被遗漏最多）
r1_by_rank = r1.groupby("wr_rank").size().reset_index(name="count")
r1_by_rank = r1_by_rank.sort_values("wr_rank")

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=[f"Top{r}" for r in r1_by_rank["wr_rank"]],
    y=r1_by_rank["count"],
    marker_color=["#22c55e" if r <= 2 else "#eab308" if r <= 5 else "#ef4444"
                  for r in r1_by_rank["wr_rank"]],
    text=r1_by_rank["count"], textposition="outside",
))
fig2.update_layout(
    title="规则1违规数 - 按胜率排名（Top几被遗漏最多？）",
    xaxis_title="胜率排名", yaxis_title="违规次数（跨所有英雄×等级）",
    template="plotly_dark", height=350, margin=dict(t=50, b=40),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart2"></div><script>Plotly.newPlot("chart2", {fig2.to_json()});</script>')
html_parts.append('</div>')

html_parts.append(f"""
<div class="insight">
<b>解读：</b>Top1-Top2 几乎不违规（分别仅 {r1_by_rank[r1_by_rank["wr_rank"]==1]["count"].values[0] if 1 in r1_by_rank["wr_rank"].values else 0} 和 {r1_by_rank[r1_by_rank["wr_rank"]==2]["count"].values[0] if 2 in r1_by_rank["wr_rank"].values else 0} 次），
说明公式对极高胜率符文的推荐是有效的。<br>
但从 Top3 开始违规数快速增长，到 Top6-Top10 时几乎每个英雄都违规——
因为每等级只推荐5个位置，第6-10名基本不可能入选。
</div>
""")

# 图3: 违规符文的黑科技加成分布
fig3 = go.Figure()
fig3.add_trace(go.Histogram(
    x=r1["bt"], name="黑科技加成", marker_color="#60a5fa",
    nbinsx=10, opacity=0.7,
))
fig3.add_trace(go.Histogram(
    x=r1["syn"], name="套装加成", marker_color="#a78bfa",
    nbinsx=10, opacity=0.7,
))
fig3.update_layout(
    title="规则1违规符文的加成分布",
    xaxis_title="加成分数", yaxis_title="违规数",
    template="plotly_dark", barmode="overlay",
    height=350, margin=dict(t=50, b=40),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart3"></div><script>Plotly.newPlot("chart3", {fig3.to_json()});</script>')
html_parts.append('</div>')

# 哪些英雄违规最多
r1_by_hero = r1.groupby("hero").size().reset_index(name="count").sort_values("count", ascending=False)
top20_heroes = r1_by_hero.head(20)

fig4 = go.Figure()
fig4.add_trace(go.Bar(
    y=top20_heroes["hero"][::-1], x=top20_heroes["count"][::-1],
    orientation="h", marker_color="#ef4444",
    text=top20_heroes["count"][::-1], textposition="outside",
))
fig4.update_layout(
    title="规则1违规最多的英雄 Top20",
    xaxis_title="违规数", yaxis_title="",
    template="plotly_dark", height=500, margin=dict(t=50, b=40, l=100),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart4"></div><script>Plotly.newPlot("chart4", {fig4.to_json()});</script>')
html_parts.append('</div>')

# ==================== 规则2 ====================
html_parts.append("""
<hr class="section-divider">
<h2>✅ 规则2：胜率倒数20不应出现在推荐范围内</h2>
<div class="insight">
<b>结果：全部通过！</b>没有任何英雄的胜率倒数20符文被推荐为「推荐选取」。<br>
这说明当前公式在<b>排除弱势符文</b>方面表现良好——胜率低的符文即使选率/UGC较高，也不会被推荐到前列。
</div>
""")

# ==================== 规则3 深入分析 ====================
html_parts.append("""
<hr class="section-divider">
<h2>⚠️ 规则3：胜率倒数10的符文必须在建议刷新范围内</h2>
""")

html_parts.append(f"""
<div class="insight">
<b>核心发现：</b>{summary['rule3_violations']} 个胜率倒数10的符文未被标记为「建议刷新」，而是被分类为「值得考虑」。<br>
<b>根本原因：</b>「建议刷新」仅覆盖底部 20% 的符文（按分数排名），而胜率倒数10的符文在分数排名上不一定落在底部20%。
尤其是那些胜率低但选率高、UGC评分高的"伪弱势"符文，分数被拉到中间区域。
</div>
""")

# 图5: 规则3 违规按等级
r3_by_level = r3.groupby("level").size().reset_index(name="count")
r3_by_level["level"] = pd.Categorical(r3_by_level["level"], categories=level_order, ordered=True)
r3_by_level = r3_by_level.sort_values("level")

fig5 = go.Figure()
for _, row in r3_by_level.iterrows():
    fig5.add_trace(go.Bar(
        x=[row["level"]], y=[row["count"]],
        marker_color=colors.get(row["level"], "#eab308"),
        text=[row["count"]], textposition="outside",
    ))
fig5.update_layout(
    title="规则3违规数 - 按符文等级",
    xaxis_title="符文等级", yaxis_title="违规数",
    template="plotly_dark", showlegend=False,
    height=350, margin=dict(t=50, b=40),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart5"></div><script>Plotly.newPlot("chart5", {fig5.to_json()});</script>')
html_parts.append('</div>')

# 图6: 规则3 违规符文的分数分布
fig6 = go.Figure()
fig6.add_trace(go.Histogram(
    x=r3["score"], nbinsx=30, marker_color="#eab308", opacity=0.8,
))
fig6.update_layout(
    title="规则3违规符文的分数分布（本应在刷新区，实际在考虑区）",
    xaxis_title="最终分数", yaxis_title="违规数",
    template="plotly_dark", height=350, margin=dict(t=50, b=40),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart6"></div><script>Plotly.newPlot("chart6", {fig6.to_json()});</script>')
html_parts.append('</div>')

# 图7: 规则3 违规符文的胜率 vs 分数散点图
fig7 = go.Figure()
fig7.add_trace(go.Scatter(
    x=r3["wr"], y=r3["score"],
    mode="markers", marker=dict(color="#eab308", size=4, opacity=0.5),
    text=r3.apply(lambda x: f"{x['hero']} - {x['aug']}<br>胜率: {x['wr']}%<br>分数: {x['score']}", axis=1),
    hoverinfo="text",
))
fig7.update_layout(
    title="规则3违规符文：胜率 vs 最终分数",
    xaxis_title="英雄×符文 胜率(%)", yaxis_title="最终分数",
    template="plotly_dark", height=400, margin=dict(t=50, b=40),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart7"></div><script>Plotly.newPlot("chart7", {fig7.to_json()});</script>')
html_parts.append('</div>')

# 规则3违规最多的英雄
r3_by_hero = r3.groupby("hero").size().reset_index(name="count").sort_values("count", ascending=False)
top20_r3 = r3_by_hero.head(20)

fig8 = go.Figure()
fig8.add_trace(go.Bar(
    y=top20_r3["hero"][::-1], x=top20_r3["count"][::-1],
    orientation="h", marker_color="#eab308",
    text=top20_r3["count"][::-1], textposition="outside",
))
fig8.update_layout(
    title="规则3违规最多的英雄 Top20",
    xaxis_title="违规数", yaxis_title="",
    template="plotly_dark", height=500, margin=dict(t=50, b=40, l=100),
    plot_bgcolor="#1a1d26", paper_bgcolor="#1a1d26",
)

html_parts.append('<div class="chart-container">')
html_parts.append(f'<div id="chart8"></div><script>Plotly.newPlot("chart8", {fig8.to_json()});</script>')
html_parts.append('</div>')

# ==================== 根因总结 ====================
html_parts.append("""
<hr class="section-divider">
<h2>🔎 根因分析与建议</h2>

<h3>为什么规则1大面积违规？</h3>
<div class="insight">
<b>结构性矛盾：</b>每等级推荐位仅 5 个（max=6），但要求胜率Top10全部入选，数学上不可能同时满足。<br><br>
<b>具体原因：</b><br>
① 公式是多维度综合评分（胜率55% + 选率20% + UGC25%），胜率排名≠分数排名<br>
② 黑科技加成最高+20分，可以让胜率一般但有组合的符文排名超过纯高胜率符文<br>
③ 胜率Top3-5 的符文普遍能进推荐，但 Top6-10 基本只能进"值得考虑"
</div>

<h3>为什么规则2完美通过？</h3>
<div class="insight">
<b>公式设计有效：</b>胜率是权重最高的维度（55%），胜率垫底的符文即使有其他加成，也很难进入前5名。<br>
同时，底部20%的刷新区域足够大，形成有效的安全网。
</div>

<h3>为什么规则3有不少违规？</h3>
<div class="insight">
<b>"伪弱势"现象：</b>胜率倒数10但选率或UGC分高的符文，总分会被拉到中间区域（"值得考虑"），逃过了底部20%的刷新线。<br>
<b>例子：</b>某符文胜率 43%（倒数第5），但选率很高（说明玩家爱选）、UGC评分高（社区好评），总分可能比其他胜率 46% 但冷门的符文还高。
</div>

<h3>📝 调优建议</h3>
<div class="insight">
<b>如果要严格满足规则1：</b><br>
· 方案A：将每等级推荐数从 5 提高到 10（TARGET_RECOMMEND_PER_LEVEL=10），但这会稀释推荐的精准度<br>
· 方案B：增加"胜率保底"机制——胜率Top10的符文无论分数如何，至少进入推荐<br>
· 方案C：提高胜率权重（当前55%→70%），使胜率排名和分数排名更一致<br><br>
<b>如果要严格满足规则3：</b><br>
· 方案A：增大刷新区比例（从20%提到30-35%）<br>
· 方案B：增加"胜率惩罚"机制——胜率倒数10的符文直接标记为刷新<br>
· 方案C：在自适应分类时，同时考虑分数排名和胜率排名的交集
</div>
""")

# ==================== 详细数据表（高频违规符文） ====================
html_parts.append("""
<hr class="section-divider">
<h2>📋 高频违规符文 Top20</h2>
<h3>规则1：最常被漏推的高胜率符文</h3>
""")

r1_by_aug = r1.groupby("aug").agg(
    违规次数=("hero", "size"),
    平均胜率=("wr", "mean"),
    平均分数=("score", "mean"),
    平均黑科技=("bt", "mean"),
).reset_index().sort_values("违规次数", ascending=False).head(20)

html_parts.append("<table><tr><th>符文</th><th>违规次数</th><th>平均胜率%</th><th>平均分数</th><th>平均黑科技</th></tr>")
for _, row in r1_by_aug.iterrows():
    html_parts.append(f"<tr><td>{row['aug']}</td><td>{row['违规次数']}</td>"
                      f"<td>{row['平均胜率']:.1f}</td><td>{row['平均分数']:.1f}</td>"
                      f"<td>{row['平均黑科技']:.1f}</td></tr>")
html_parts.append("</table>")

html_parts.append("<h3>规则3：最常漏刷的低胜率符文</h3>")
r3_by_aug = r3.groupby("aug").agg(
    违规次数=("hero", "size"),
    平均胜率=("wr", "mean"),
    平均分数=("score", "mean"),
    平均黑科技=("bt", "mean"),
    平均套装=("syn", "mean"),
).reset_index().sort_values("违规次数", ascending=False).head(20)

html_parts.append("<table><tr><th>符文</th><th>违规次数</th><th>平均胜率%</th><th>平均分数</th><th>平均黑科技</th><th>平均套装</th></tr>")
for _, row in r3_by_aug.iterrows():
    html_parts.append(f"<tr><td>{row['aug']}</td><td>{row['违规次数']}</td>"
                      f"<td>{row['平均胜率']:.1f}</td><td>{row['平均分数']:.1f}</td>"
                      f"<td>{row['平均黑科技']:.1f}</td><td>{row['平均套装']:.1f}</td></tr>")
html_parts.append("</table>")

# 关闭HTML
html_parts.append("""
<hr class="section-divider">
<p class="subtitle" style="text-align:center; margin-top:32px;">
验证脚本：validate_scoring.py | 报告生成：validate_report.py<br>
验证条件：标准模式 (streak=0)，每等级推荐5个 (target=5, min=4, max=6)，刷新区底部20%
</p>
</div></body></html>
""")

# 输出HTML
report_path = os.path.join(base, "output", "validation_report.html")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))
print(f"报告已生成: {report_path}")
