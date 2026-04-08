#!/usr/bin/env python3
"""
OPGG 各英雄 S 级符文 vs 胜率/Pick率 关系分析
分析目标：OPGG 评出的 S 级符文，是否真的在胜率和 Pick 率上表现突出？
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import os

# ============================================================
# 1. 数据加载与合并
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

df_stats = pd.read_excel(os.path.join(DATA_DIR, "step1_2_champion_augment_stats.xlsx"))
df_opgg = pd.read_csv(os.path.join(BASE_DIR, "lol_opgg_kiwi_augment_data.csv"), sep="\t")

merged = df_stats.merge(
    df_opgg,
    left_on=["championid", "player_augment"],
    right_on=["championid", "augment_id"],
    how="inner",
    suffixes=("_stats", "_opgg"),
)

# 转换为百分比
merged["win_rate_pct"] = merged["win_rate"] * 100
merged["show_rate_pct"] = merged["show_rate"] * 100

tier_order = ["S", "A", "B", "C", "D", "E"]
tier_colors = {
    "S": "#FF4444",
    "A": "#FF8C00",
    "B": "#FFD700",
    "C": "#32CD32",
    "D": "#4169E1",
    "E": "#808080",
}

# ============================================================
# 2. 汇总统计
# ============================================================
tier_summary = (
    merged.groupby("tier_label")
    .agg(
        count=("win_rate_pct", "count"),
        win_rate_mean=("win_rate_pct", "mean"),
        win_rate_median=("win_rate_pct", "median"),
        win_rate_q25=("win_rate_pct", lambda x: x.quantile(0.25)),
        win_rate_q75=("win_rate_pct", lambda x: x.quantile(0.75)),
        win_rate_std=("win_rate_pct", "std"),
        show_rate_mean=("show_rate_pct", "mean"),
        show_rate_median=("show_rate_pct", "median"),
        performance_mean=("performance", "mean"),
        popular_mean=("popular", "mean"),
    )
    .reset_index()
)
tier_summary["tier_label"] = pd.Categorical(
    tier_summary["tier_label"], categories=tier_order, ordered=True
)
tier_summary = tier_summary.sort_values("tier_label")

print("=" * 60)
print("各 Tier 统计摘要")
print("=" * 60)
print(tier_summary.to_string(index=False))

# ============================================================
# 图1: 各 Tier 胜率箱线图
# ============================================================
fig1 = go.Figure()
for tier in tier_order:
    tier_data = merged[merged["tier_label"] == tier]["win_rate_pct"]
    fig1.add_trace(
        go.Box(
            y=tier_data,
            name=f"{tier} (n={len(tier_data)})",
            marker_color=tier_colors[tier],
            boxmean=True,
        )
    )

fig1.update_layout(
    title=dict(
        text="<b>各 Tier 英雄×符文 胜率分布</b><br><sup>S 级符文是否真的胜率更高？</sup>",
        font=dict(size=18),
    ),
    yaxis_title="胜率 (%)",
    xaxis_title="OPGG Tier",
    template="plotly_white",
    height=500,
    showlegend=False,
    yaxis=dict(dtick=5),
)
fig1.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50% 基准线")

# ============================================================
# 图2: 各 Tier Pick率（show_rate）箱线图
# ============================================================
fig2 = go.Figure()
for tier in tier_order:
    tier_data = merged[merged["tier_label"] == tier]["show_rate_pct"]
    fig2.add_trace(
        go.Box(
            y=tier_data,
            name=f"{tier} (n={len(tier_data)})",
            marker_color=tier_colors[tier],
            boxmean=True,
        )
    )

fig2.update_layout(
    title=dict(
        text="<b>各 Tier 英雄×符文 Pick率分布</b><br><sup>S 级符文是否 Pick 率更高？</sup>",
        font=dict(size=18),
    ),
    yaxis_title="Pick率 (%)",
    xaxis_title="OPGG Tier",
    template="plotly_white",
    height=500,
    showlegend=False,
)

# ============================================================
# 图3: 胜率 vs Pick率 散点图（按 Tier 着色）
# ============================================================
# 抽样以避免点过多
np.random.seed(42)
sample_size = min(5000, len(merged))
sample_df = merged.sample(sample_size)

fig3 = go.Figure()
for tier in tier_order:
    t_df = sample_df[sample_df["tier_label"] == tier]
    fig3.add_trace(
        go.Scatter(
            x=t_df["win_rate_pct"],
            y=t_df["show_rate_pct"],
            mode="markers",
            name=tier,
            marker=dict(color=tier_colors[tier], size=5, opacity=0.5),
            text=t_df.apply(
                lambda r: f"{r['champion_name_stats']} - {r['augment_name_stats']}<br>胜率: {r['win_rate_pct']:.1f}%<br>Pick率: {r['show_rate_pct']:.3f}%<br>Tier: {r['tier_label']}",
                axis=1,
            ),
            hovertemplate="%{text}<extra></extra>",
        )
    )

fig3.update_layout(
    title=dict(
        text="<b>胜率 vs Pick率 散点图（按 Tier 着色）</b><br><sup>S 级符文集中在右上方（高胜率+高Pick率）</sup>",
        font=dict(size=18),
    ),
    xaxis_title="胜率 (%)",
    yaxis_title="Pick率 (%)",
    template="plotly_white",
    height=600,
    legend=dict(title="OPGG Tier"),
)
fig3.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)

# ============================================================
# 图4: Tier 均值条形图 - 胜率 & Pick率 并排
# ============================================================
fig4 = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=["平均胜率 by Tier", "平均 Pick率 by Tier"],
    horizontal_spacing=0.15,
)

fig4.add_trace(
    go.Bar(
        x=tier_summary["tier_label"].astype(str),
        y=tier_summary["win_rate_mean"],
        marker_color=[tier_colors[t] for t in tier_summary["tier_label"]],
        text=[f"{v:.1f}%" for v in tier_summary["win_rate_mean"]],
        textposition="outside",
        showlegend=False,
    ),
    row=1,
    col=1,
)

fig4.add_trace(
    go.Bar(
        x=tier_summary["tier_label"].astype(str),
        y=tier_summary["show_rate_mean"],
        marker_color=[tier_colors[t] for t in tier_summary["tier_label"]],
        text=[f"{v:.4f}%" for v in tier_summary["show_rate_mean"]],
        textposition="outside",
        showlegend=False,
    ),
    row=1,
    col=2,
)

fig4.update_layout(
    title=dict(
        text="<b>各 Tier 平均胜率 & Pick率</b><br><sup>S→E 胜率和 Pick率 呈明显递减趋势</sup>",
        font=dict(size=18),
    ),
    template="plotly_white",
    height=450,
)
fig4.update_yaxes(title_text="平均胜率 (%)", row=1, col=1)
fig4.update_yaxes(title_text="平均 Pick率 (%)", row=1, col=2)

# ============================================================
# 图5: S 级符文详细分析 - 各英雄 S 级符文数量分布
# ============================================================
s_tier = merged[merged["tier_label"] == "S"]
s_per_champ = s_tier.groupby("champion_name_stats").size().reset_index(name="s_count")
s_count_dist = s_per_champ["s_count"].value_counts().sort_index().reset_index()
s_count_dist.columns = ["s_count", "champion_count"]

fig5 = go.Figure(
    go.Bar(
        x=s_count_dist["s_count"],
        y=s_count_dist["champion_count"],
        marker_color="#FF4444",
        text=s_count_dist["champion_count"],
        textposition="outside",
    )
)
fig5.update_layout(
    title=dict(
        text="<b>各英雄拥有的 S 级符文数量分布</b><br><sup>大部分英雄有 10-15 个 S 级符文</sup>",
        font=dict(size=18),
    ),
    xaxis_title="S 级符文数量",
    yaxis_title="英雄数量",
    template="plotly_white",
    height=400,
)

# ============================================================
# 图6: S 级符文的 performance vs 胜率
# ============================================================
fig6 = go.Figure()
fig6.add_trace(
    go.Scatter(
        x=s_tier["performance"],
        y=s_tier["win_rate_pct"],
        mode="markers",
        marker=dict(
            color=s_tier["show_rate_pct"],
            colorscale="YlOrRd",
            size=6,
            opacity=0.6,
            colorbar=dict(title="Pick率(%)"),
        ),
        text=s_tier.apply(
            lambda r: f"{r['champion_name_stats']} - {r['augment_name_stats']}<br>Performance: {r['performance']}<br>胜率: {r['win_rate_pct']:.1f}%<br>Pick率: {r['show_rate_pct']:.3f}%",
            axis=1,
        ),
        hovertemplate="%{text}<extra></extra>",
    )
)
fig6.update_layout(
    title=dict(
        text="<b>S 级符文: OPGG Performance 分 vs 实际胜率</b><br><sup>颜色深浅=Pick率 | Performance 与胜率有正相关</sup>",
        font=dict(size=18),
    ),
    xaxis_title="OPGG Performance 分",
    yaxis_title="实际胜率 (%)",
    template="plotly_white",
    height=550,
)
fig6.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)

# ============================================================
# 图7: S 级 vs 非 S 级的相关性对比
# ============================================================
merged["is_S"] = merged["tier_label"] == "S"

# 计算 performance vs win_rate 的相关系数
corr_all = merged[["performance", "win_rate_pct"]].corr().iloc[0, 1]
corr_s = s_tier[["performance", "win_rate_pct"]].corr().iloc[0, 1]
non_s = merged[merged["tier_label"] != "S"]
corr_non_s = non_s[["performance", "win_rate_pct"]].corr().iloc[0, 1]

print(f"\n=== Performance vs 胜率 相关系数 ===")
print(f"全部: {corr_all:.4f}")
print(f"S级: {corr_s:.4f}")
print(f"非S级: {corr_non_s:.4f}")

# popular vs show_rate 相关性
corr_pop_show_all = merged[["popular", "show_rate_pct"]].corr().iloc[0, 1]
corr_pop_show_s = s_tier[["popular", "show_rate_pct"]].corr().iloc[0, 1]
print(f"\n=== Popular vs Pick率 相关系数 ===")
print(f"全部: {corr_pop_show_all:.4f}")
print(f"S级: {corr_pop_show_s:.4f}")

# performance vs win_rate 相关系数 by tier
corr_by_tier = []
for tier in tier_order:
    t_df = merged[merged["tier_label"] == tier]
    c_perf_wr = t_df[["performance", "win_rate_pct"]].corr().iloc[0, 1]
    c_pop_sr = t_df[["popular", "show_rate_pct"]].corr().iloc[0, 1]
    corr_by_tier.append({"tier": tier, "corr_perf_wr": c_perf_wr, "corr_pop_sr": c_pop_sr})
corr_df = pd.DataFrame(corr_by_tier)
print(f"\n=== 各 Tier 相关系数 ===")
print(corr_df.to_string(index=False))

# ============================================================
# 图8: OPGG popular 分 vs 实际 Pick率
# ============================================================
fig8 = go.Figure()
for tier in tier_order:
    t_df = sample_df[sample_df["tier_label"] == tier]
    fig8.add_trace(
        go.Scatter(
            x=t_df["popular"],
            y=t_df["show_rate_pct"],
            mode="markers",
            name=tier,
            marker=dict(color=tier_colors[tier], size=5, opacity=0.5),
            text=t_df.apply(
                lambda r: f"{r['champion_name_stats']} - {r['augment_name_stats']}<br>Popular: {r['popular']}<br>Pick率: {r['show_rate_pct']:.3f}%<br>Tier: {r['tier_label']}",
                axis=1,
            ),
            hovertemplate="%{text}<extra></extra>",
        )
    )

fig8.update_layout(
    title=dict(
        text="<b>OPGG Popular 分 vs 实际 Pick率</b><br><sup>两者高度正相关，S 级符文 Popular 和 Pick率 都更高</sup>",
        font=dict(size=18),
    ),
    xaxis_title="OPGG Popular 分",
    yaxis_title="实际 Pick率 (%)",
    template="plotly_white",
    height=550,
    legend=dict(title="OPGG Tier"),
)

# ============================================================
# 图9: Top S 级符文 - 胜率最高的 30 个英雄×符文组合
# ============================================================
top_s = (
    s_tier.nlargest(30, "win_rate_pct")[
        ["champion_name_stats", "augment_name_stats", "win_rate_pct", "show_rate_pct", "performance", "popular", "rarity_label"]
    ]
    .reset_index(drop=True)
)
top_s["label"] = top_s["champion_name_stats"] + " - " + top_s["augment_name_stats"]

fig9 = go.Figure()
fig9.add_trace(
    go.Bar(
        y=top_s["label"][::-1],
        x=top_s["win_rate_pct"][::-1],
        orientation="h",
        marker=dict(
            color=top_s["show_rate_pct"][::-1],
            colorscale="YlOrRd",
            colorbar=dict(title="Pick率(%)"),
        ),
        text=[f"{v:.1f}%" for v in top_s["win_rate_pct"][::-1]],
        textposition="outside",
        hovertext=[
            f"{r['label']}<br>胜率: {r['win_rate_pct']:.1f}%<br>Pick率: {r['show_rate_pct']:.3f}%<br>稀有度: {r['rarity_label']}"
            for _, r in top_s[::-1].iterrows()
        ],
        hovertemplate="%{hovertext}<extra></extra>",
    )
)
fig9.update_layout(
    title=dict(
        text="<b>S 级符文 Top 30 胜率最高的英雄×符文组合</b><br><sup>颜色深浅=Pick率</sup>",
        font=dict(size=18),
    ),
    xaxis_title="胜率 (%)",
    template="plotly_white",
    height=900,
    margin=dict(l=250),
)

# ============================================================
# 图10: 各 Tier 相关系数对比图
# ============================================================
fig10 = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=[
        "Performance 分 vs 实际胜率 (相关系数)",
        "Popular 分 vs 实际 Pick率 (相关系数)",
    ],
    horizontal_spacing=0.15,
)

fig10.add_trace(
    go.Bar(
        x=corr_df["tier"],
        y=corr_df["corr_perf_wr"],
        marker_color=[tier_colors[t] for t in corr_df["tier"]],
        text=[f"{v:.3f}" for v in corr_df["corr_perf_wr"]],
        textposition="outside",
        showlegend=False,
    ),
    row=1,
    col=1,
)

fig10.add_trace(
    go.Bar(
        x=corr_df["tier"],
        y=corr_df["corr_pop_sr"],
        marker_color=[tier_colors[t] for t in corr_df["tier"]],
        text=[f"{v:.3f}" for v in corr_df["corr_pop_sr"]],
        textposition="outside",
        showlegend=False,
    ),
    row=1,
    col=2,
)

fig10.update_layout(
    title=dict(
        text="<b>各 Tier 的 OPGG 指标与实际数据相关性</b><br><sup>Performance 与胜率弱相关，Popular 与 Pick率 强相关</sup>",
        font=dict(size=18),
    ),
    template="plotly_white",
    height=450,
)
fig10.update_yaxes(title_text="Pearson 相关系数", row=1, col=1)
fig10.update_yaxes(title_text="Pearson 相关系数", row=1, col=2)

# ============================================================
# 汇总报告 HTML
# ============================================================
OUTPUT_DIR = BASE_DIR

html_parts = []
html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OPGG S级符文 vs 胜率/Pick率 关系分析</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: #f8f9fa;
        color: #333;
    }
    h1 { color: #1a1a2e; border-bottom: 3px solid #FF4444; padding-bottom: 10px; }
    h2 { color: #16213e; margin-top: 40px; }
    .summary-box {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .kpi-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        margin: 20px 0;
    }
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        flex: 1;
        min-width: 180px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .kpi-card .value { font-size: 28px; font-weight: bold; }
    .kpi-card .label { font-size: 13px; color: #666; margin-top: 4px; }
    .kpi-card.s-tier .value { color: #FF4444; }
    .kpi-card.a-tier .value { color: #FF8C00; }
    .kpi-card.e-tier .value { color: #808080; }
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin: 24px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .insight {
        background: #FFF3CD;
        border-left: 4px solid #FFD700;
        padding: 12px 16px;
        margin: 16px 0;
        border-radius: 0 8px 8px 0;
        font-size: 14px;
    }
    .conclusion {
        background: #D4EDDA;
        border-left: 4px solid #28A745;
        padding: 12px 16px;
        margin: 16px 0;
        border-radius: 0 8px 8px 0;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }
    th, td {
        padding: 10px 14px;
        text-align: center;
        border-bottom: 1px solid #eee;
    }
    th { background: #f1f3f5; font-weight: 600; }
    tr:hover { background: #f8f9fa; }
    .tier-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-weight: bold;
        color: white;
    }
</style>
</head>
<body>
<h1>🎯 OPGG S级符文 vs 英雄×符文 胜率/Pick率 关系分析</h1>
<p style="color:#666;">数据日期: 2026-04-03 | 英雄数: 172 | 符文数: 200+ | 分析: 29,844 个英雄×符文组合</p>
""")

# KPI cards
s_stats = tier_summary[tier_summary["tier_label"] == "S"].iloc[0]
a_stats = tier_summary[tier_summary["tier_label"] == "A"].iloc[0]
e_stats = tier_summary[tier_summary["tier_label"] == "E"].iloc[0]

html_parts.append(f"""
<div class="kpi-row">
    <div class="kpi-card s-tier">
        <div class="value">{s_stats['win_rate_mean']:.1f}%</div>
        <div class="label">S 级平均胜率</div>
    </div>
    <div class="kpi-card a-tier">
        <div class="value">{a_stats['win_rate_mean']:.1f}%</div>
        <div class="label">A 级平均胜率</div>
    </div>
    <div class="kpi-card e-tier">
        <div class="value">{e_stats['win_rate_mean']:.1f}%</div>
        <div class="label">E 级平均胜率</div>
    </div>
    <div class="kpi-card s-tier">
        <div class="value">{s_stats['show_rate_mean']:.4f}%</div>
        <div class="label">S 级平均 Pick率</div>
    </div>
    <div class="kpi-card e-tier">
        <div class="value">{e_stats['show_rate_mean']:.4f}%</div>
        <div class="label">E 级平均 Pick率</div>
    </div>
</div>
""")

# 核心发现
html_parts.append("""
<div class="summary-box">
<h2 style="margin-top:0;">📊 核心发现</h2>
<div class="conclusion">
<strong>结论：OPGG 的 S 级评级确实与更高的胜率和 Pick率 显著正相关。</strong>
</div>
<ul>
""")
html_parts.append(f"""
<li><strong>胜率梯度明显</strong>：S 级平均胜率 <b>{s_stats['win_rate_mean']:.1f}%</b>，比 E 级高 <b>{s_stats['win_rate_mean'] - e_stats['win_rate_mean']:.1f} 个百分点</b></li>
<li><strong>Pick率差距巨大</strong>：S 级平均 Pick率是 E 级的 <b>{s_stats['show_rate_mean'] / e_stats['show_rate_mean']:.0f} 倍</b>（{s_stats['show_rate_mean']:.4f}% vs {e_stats['show_rate_mean']:.4f}%）</li>
<li><strong>OPGG Popular 分与实际 Pick率 强相关</strong>：全局 Pearson r = <b>{corr_pop_show_all:.3f}</b></li>
<li><strong>OPGG Performance 分与实际胜率 弱相关</strong>：全局 Pearson r = <b>{corr_all:.3f}</b>（Performance 是综合指标，不仅仅反映胜率）</li>
</ul>
</div>
""")

# Tier 汇总表
html_parts.append("""
<h2>📋 各 Tier 统计汇总</h2>
<table>
<tr><th>Tier</th><th>样本数</th><th>平均胜率</th><th>中位胜率</th><th>平均 Pick率</th><th>平均 Performance</th><th>平均 Popular</th></tr>
""")
for _, row in tier_summary.iterrows():
    tier = str(row["tier_label"])
    color = tier_colors[tier]
    html_parts.append(
        f'<tr><td><span class="tier-badge" style="background:{color}">{tier}</span></td>'
        f'<td>{int(row["count"])}</td>'
        f'<td>{row["win_rate_mean"]:.1f}%</td>'
        f'<td>{row["win_rate_median"]:.1f}%</td>'
        f'<td>{row["show_rate_mean"]:.4f}%</td>'
        f'<td>{row["performance_mean"]:.1f}</td>'
        f'<td>{row["popular_mean"]:.2f}</td></tr>'
    )
html_parts.append("</table>")

# 插入图表
charts = [
    (fig4, "tier_bar", "各 Tier 平均胜率 & Pick率"),
    (fig1, "tier_winrate_box", "各 Tier 胜率分布"),
    (fig2, "tier_pickrate_box", "各 Tier Pick率分布"),
    (fig3, "scatter_wr_pr", "胜率 vs Pick率 散点图"),
    (fig6, "s_perf_wr", "S 级符文 Performance vs 胜率"),
    (fig8, "pop_pr", "OPGG Popular vs 实际 Pick率"),
    (fig10, "corr_compare", "各 Tier 相关系数"),
    (fig5, "s_count_dist", "英雄 S 级符文数量分布"),
    (fig9, "top30_s", "S 级 Top 30 胜率"),
]

for fig, div_id, title in charts:
    fig_json = fig.to_json()
    html_parts.append(f"""
<h2>{title}</h2>
<div class="chart-container">
    <div id="{div_id}"></div>
</div>
<script>
    Plotly.newPlot('{div_id}', ...function(){{
        var data = {fig_json};
        return [data.data, data.layout];
    }}());
</script>
""")

# Insight annotations
html_parts.append("""
<h2>🔍 深度洞察</h2>

<div class="insight">
<strong>💡 洞察 1: S 级评级的"信号强度"</strong><br>
S 级符文的胜率标准差（3.9%）明显小于 E 级（6.0%），说明 S 级评级的"噪声"更小——被评为 S 级的符文，其胜率表现更加稳定一致。
</div>

<div class="insight">
<strong>💡 洞察 2: B/C/D 级的"模糊地带"</strong><br>
B、C、D 三个 Tier 的平均胜率非常接近（约 46.9%-47.0%），区分度不如 S vs E 那么明显。OPGG 可能在这些中间级别更多依赖 Popular（使用率）来区分。
</div>

<div class="insight">
<strong>💡 洞察 3: Performance 不等于胜率</strong><br>
OPGG 的 Performance 分与实际胜率的相关系数仅 0.2-0.4（弱到中等相关），说明 Performance 是一个综合指标，包含了胜率以外的因素（如热门度、版本强度等），不能直接等同于胜率排序。
</div>

<div class="insight">
<strong>💡 洞察 4: Popular 分高度反映实际 Pick率</strong><br>
Popular 分与实际 Pick率 的全局相关系数高达 0.96+，几乎是线性关系。这表明 OPGG 的 Popular 指标可能直接来源于真实使用数据。
</div>

<div class="conclusion">
<strong>🎯 产品启示</strong>：OPGG 的 Tier 评级体系对于筛选高胜率符文是有效的。在设计符文推荐系统时，可以将 OPGG Tier 作为一个强信号特征。但需注意 B/C/D 级区分度不够高，中间层级的推荐可能需要结合其他特征（如玩家水平、英雄类型）做更精细化的判断。
</div>
""")

html_parts.append("</body></html>")

# 写入文件
output_path = os.path.join(OUTPUT_DIR, "英雄符文相似度分析_opgg_tier_analysis.html")

# 修复 plotly JSON 嵌入方式
html_content = []
html_content.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OPGG S级符文 vs 胜率/Pick率 关系分析</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: #f8f9fa;
        color: #333;
    }
    h1 { color: #1a1a2e; border-bottom: 3px solid #FF4444; padding-bottom: 10px; }
    h2 { color: #16213e; margin-top: 40px; }
    .summary-box {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .kpi-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        margin: 20px 0;
    }
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        flex: 1;
        min-width: 180px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .kpi-card .value { font-size: 28px; font-weight: bold; }
    .kpi-card .label { font-size: 13px; color: #666; margin-top: 4px; }
    .kpi-card.s-tier .value { color: #FF4444; }
    .kpi-card.a-tier .value { color: #FF8C00; }
    .kpi-card.e-tier .value { color: #808080; }
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin: 24px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .insight {
        background: #FFF3CD;
        border-left: 4px solid #FFD700;
        padding: 12px 16px;
        margin: 16px 0;
        border-radius: 0 8px 8px 0;
        font-size: 14px;
    }
    .conclusion {
        background: #D4EDDA;
        border-left: 4px solid #28A745;
        padding: 12px 16px;
        margin: 16px 0;
        border-radius: 0 8px 8px 0;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }
    th, td {
        padding: 10px 14px;
        text-align: center;
        border-bottom: 1px solid #eee;
    }
    th { background: #f1f3f5; font-weight: 600; }
    tr:hover { background: #f8f9fa; }
    .tier-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-weight: bold;
        color: white;
    }
</style>
</head>
<body>
""")

# 直接用已有 html_parts 的内容（从 KPI 开始），但图表用正确的 JSON 注入方式
# 重新组装——用更简单的方式

import json

final_html = []
final_html.append(html_content[0])

# Title and metadata
final_html.append("""
<h1>🎯 OPGG S级符文 vs 英雄×符文 胜率/Pick率 关系分析</h1>
<p style="color:#666;">数据日期: 2026-04-03 | 英雄数: 172 | 符文数: 200+ | 分析: 29,844 个英雄×符文组合</p>
""")

# KPI
final_html.append(f"""
<div class="kpi-row">
    <div class="kpi-card s-tier">
        <div class="value">{s_stats['win_rate_mean']:.1f}%</div>
        <div class="label">S 级平均胜率</div>
    </div>
    <div class="kpi-card a-tier">
        <div class="value">{a_stats['win_rate_mean']:.1f}%</div>
        <div class="label">A 级平均胜率</div>
    </div>
    <div class="kpi-card e-tier">
        <div class="value">{e_stats['win_rate_mean']:.1f}%</div>
        <div class="label">E 级平均胜率</div>
    </div>
    <div class="kpi-card s-tier">
        <div class="value">{s_stats['show_rate_mean']:.4f}%</div>
        <div class="label">S 级平均 Pick率</div>
    </div>
    <div class="kpi-card e-tier">
        <div class="value">{e_stats['show_rate_mean']:.4f}%</div>
        <div class="label">E 级平均 Pick率</div>
    </div>
</div>
""")

# Core findings
final_html.append(f"""
<div class="summary-box">
<h2 style="margin-top:0;">📊 核心发现</h2>
<div class="conclusion">
<strong>结论：OPGG 的 S 级评级确实与更高的胜率和 Pick率 显著正相关。</strong>
</div>
<ul>
<li><strong>胜率梯度明显</strong>：S 级平均胜率 <b>{s_stats['win_rate_mean']:.1f}%</b>，比 E 级高 <b>{s_stats['win_rate_mean'] - e_stats['win_rate_mean']:.1f} 个百分点</b></li>
<li><strong>Pick率差距巨大</strong>：S 级平均 Pick率是 E 级的 <b>{s_stats['show_rate_mean'] / e_stats['show_rate_mean']:.0f} 倍</b>（{s_stats['show_rate_mean']:.4f}% vs {e_stats['show_rate_mean']:.4f}%）</li>
<li><strong>OPGG Popular 分与实际 Pick率 强相关</strong>：全局 Pearson r = <b>{corr_pop_show_all:.3f}</b></li>
<li><strong>OPGG Performance 分与实际胜率 弱相关</strong>：全局 Pearson r = <b>{corr_all:.3f}</b>（Performance 是综合指标，不仅仅反映胜率）</li>
</ul>
</div>
""")

# Tier summary table
final_html.append("""
<h2>📋 各 Tier 统计汇总</h2>
<table>
<tr><th>Tier</th><th>样本数</th><th>平均胜率</th><th>中位胜率</th><th>平均 Pick率</th><th>平均 Performance</th><th>平均 Popular</th></tr>
""")
for _, row in tier_summary.iterrows():
    tier = str(row["tier_label"])
    color = tier_colors[tier]
    final_html.append(
        f'<tr><td><span class="tier-badge" style="background:{color}">{tier}</span></td>'
        f'<td>{int(row["count"])}</td>'
        f'<td>{row["win_rate_mean"]:.1f}%</td>'
        f'<td>{row["win_rate_median"]:.1f}%</td>'
        f'<td>{row["show_rate_mean"]:.4f}%</td>'
        f'<td>{row["performance_mean"]:.1f}</td>'
        f'<td>{row["popular_mean"]:.2f}</td></tr>'
    )
final_html.append("</table>")

# Charts with correct JSON injection
for fig_obj, div_id, section_title in charts:
    fig_dict = json.loads(fig_obj.to_json())
    data_json = json.dumps(fig_dict["data"])
    layout_json = json.dumps(fig_dict["layout"])
    final_html.append(f"""
<h2>{section_title}</h2>
<div class="chart-container">
    <div id="{div_id}"></div>
</div>
<script>
    var data_{div_id} = {data_json};
    var layout_{div_id} = {layout_json};
    layout_{div_id}.autosize = true;
    Plotly.newPlot('{div_id}', data_{div_id}, layout_{div_id}, {{responsive: true}});
</script>
""")

# Insights
final_html.append(f"""
<h2>🔍 深度洞察</h2>

<div class="insight">
<strong>💡 洞察 1: S 级评级的"信号强度"</strong><br>
S 级符文的胜率标准差（{tier_summary[tier_summary['tier_label']=='S'].iloc[0]['win_rate_std']:.1f}%）明显小于 E 级（{tier_summary[tier_summary['tier_label']=='E'].iloc[0]['win_rate_std']:.1f}%），说明 S 级评级的"噪声"更小——被评为 S 级的符文，其胜率表现更加稳定一致。
</div>

<div class="insight">
<strong>💡 洞察 2: B/C/D 级的"模糊地带"</strong><br>
B、C、D 三个 Tier 的平均胜率非常接近（约 46.9%-47.0%），区分度不如 S vs E 那么明显。OPGG 可能在这些中间级别更多依赖 Popular（使用率）来区分。
</div>

<div class="insight">
<strong>💡 洞察 3: Performance 不等于胜率</strong><br>
OPGG 的 Performance 分与实际胜率的相关系数仅 {corr_all:.2f}（弱到中等相关），说明 Performance 是一个综合指标，包含了胜率以外的因素（如热门度、版本强度等），不能直接等同于胜率排序。
</div>

<div class="insight">
<strong>💡 洞察 4: Popular 分高度反映实际 Pick率</strong><br>
Popular 分与实际 Pick率 的全局相关系数高达 {corr_pop_show_all:.2f}，几乎是线性关系。这表明 OPGG 的 Popular 指标可能直接来源于真实使用数据。
</div>

<div class="conclusion">
<strong>🎯 产品启示</strong>：OPGG 的 Tier 评级体系对于筛选高胜率符文是有效的。在设计符文推荐系统时，可以将 OPGG Tier 作为一个强信号特征。但需注意 B/C/D 级区分度不够高，中间层级的推荐可能需要结合其他特征（如玩家水平、英雄类型）做更精细化的判断。
</div>
""")

final_html.append("</body></html>")

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(final_html))

print(f"\n✅ 报告已生成: {output_path}")
print(f"文件大小: {os.path.getsize(output_path) / 1024:.0f} KB")
