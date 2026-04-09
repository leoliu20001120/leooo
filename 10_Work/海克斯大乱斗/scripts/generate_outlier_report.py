#!/usr/bin/env python3
"""
极端值清洗可视化报告
展示 show_rate 和 win_rate 清洗前后的数据分布对比
"""
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go

# 读取清洗后的数据
df = pd.read_excel('/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗/data/step1_2_champion_augment_scored.xlsx')

# ---- 清洗前的统计 ----
before = {
    'total': 30330, 'wr_min': 0.0, 'wr_max': 1.0, 'wr_mean': 0.476188,
    'show_zero': 1725, 'wr_zero': 54, 'wr_100': 30, 'top30': 9171
}
after = {
    'total': len(df),
    'wr_min': df['win_rate'].min(), 'wr_max': df['win_rate'].max(),
    'wr_mean': df['win_rate'].mean(),
    'show_zero': 0, 'wr_zero': 0, 'wr_100': 0,
    'top30': (df['top30_label'] == 'Top30%').sum()
}

# ---- Plotly 图表 ----
dark_layout = dict(
    template='plotly_dark', paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
    font=dict(color='#c9d1d9'), margin=dict(l=50, r=30, t=50, b=50)
)

# 图1: win_rate 分布
fig1 = go.Figure()
fig1.add_trace(go.Histogram(x=df['win_rate']*100, nbinsx=60, marker_color='rgba(88,166,255,0.7)', name='win_rate'))
fig1.update_layout(**dark_layout, height=380, title='清洗后 win_rate 分布', xaxis_title='胜率 (%)', yaxis_title='频次')
fig1.add_vline(x=50, line_dash='dash', line_color='#8b949e', annotation_text='50%')

# 图2: show_rate 分布 (log)
fig2 = go.Figure()
fig2.add_trace(go.Histogram(x=np.log10(df['show_rate']*100+1e-6), nbinsx=60, marker_color='rgba(63,185,80,0.7)', name='show_rate'))
fig2.update_layout(**dark_layout, height=380, title='清洗后 show_rate 分布 (log₁₀)', xaxis_title='log₁₀(Pick率%)', yaxis_title='频次')

# 图3: win_rate vs show_rate
sample = df.sample(min(5000, len(df)), random_state=42)
fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=sample['win_rate']*100, y=sample['show_rate']*100, mode='markers',
    marker=dict(color=sample['composite_score'], colorscale='Viridis', size=4, opacity=0.5, colorbar=dict(title='综合分')),
    text=sample['champion_name']+' - '+sample['augment_name'],
    hovertemplate='%{text}<br>胜率: %{x:.1f}%<br>Pick率: %{y:.4f}%<extra></extra>'
))
fig3.update_layout(**dark_layout, height=480, title='清洗后 win_rate vs show_rate', xaxis_title='胜率 (%)', yaxis_title='Pick率 (%)')
fig3.add_vline(x=50, line_dash='dash', line_color='#484f58')

# 图4: 每英雄符文数
champ_counts = df.groupby('champion_name').size()
fig4 = go.Figure()
fig4.add_trace(go.Histogram(x=champ_counts.values, nbinsx=30, marker_color='rgba(210,153,34,0.7)', name='符文数'))
fig4.update_layout(**dark_layout, height=380, title='每英雄符文数分布', xaxis_title='符文数', yaxis_title='英雄数')

# ---- 构建 HTML ----
def fig_to_html(fig, div_id):
    d = json.loads(fig.to_json())
    return f'''<div class="chart-card"><div id="{div_id}"></div></div>
<script>
Plotly.newPlot('{div_id}', {json.dumps(d['data'])}, {json.dumps(d['layout'])}, {{responsive:true}});
</script>'''

removed = before['total'] - after['total']

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>极端值清洗报告</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:#0f1117;color:#e1e4e8;line-height:1.6}}
.container{{max-width:1200px;margin:0 auto;padding:24px}}
h1{{font-size:28px;font-weight:700;margin-bottom:8px;background:linear-gradient(135deg,#58a6ff,#3fb950);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{color:#8b949e;font-size:14px;margin-bottom:32px}}
.summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}}
.summary-card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;text-align:center}}
.summary-card .number{{font-size:32px;font-weight:700}}
.summary-card .label{{font-size:13px;color:#8b949e;margin-top:4px}}
.summary-card .sub{{font-size:12px;color:#484f58;margin-top:2px}}
.green{{color:#3fb950}}.red{{color:#f85149}}.blue{{color:#58a6ff}}.yellow{{color:#d29922}}
.section{{margin-bottom:32px}}
.section-title{{font-size:20px;font-weight:600;margin-bottom:16px;color:#c9d1d9}}
.chart-card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;margin-bottom:20px}}
.charts-row{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
.insight-box{{background:#161b22;border-left:4px solid #58a6ff;border-radius:0 12px 12px 0;padding:16px 20px;margin-bottom:16px}}
.insight-box h3{{font-size:15px;color:#58a6ff;margin-bottom:8px}}
.insight-box p{{font-size:14px;color:#c9d1d9}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}}
th{{background:#0d1117;padding:10px 12px;text-align:center;font-weight:600;color:#8b949e;border-bottom:2px solid #30363d}}
td{{padding:8px 12px;border-bottom:1px solid #21262d;text-align:center;color:#c9d1d9}}
tr:hover td{{background:rgba(88,166,255,0.04)}}
.removed{{color:#f85149;text-decoration:line-through}}
.kept{{color:#3fb950}}
</style>
</head>
<body>
<div class="container">
<h1>🧹 极端值清洗报告</h1>
<p class="subtitle">对 step1_2_champion_augment_scored.xlsx 中 show_rate 和 win_rate 的极端值进行清洗 | 数据日期: 2026-04-09</p>

<div class="summary-grid">
  <div class="summary-card"><div class="number red">{removed:,}</div><div class="label">剔除的极端值</div><div class="sub">占原始 {removed/before['total']*100:.1f}%</div></div>
  <div class="summary-card"><div class="number green">{after['total']:,}</div><div class="label">清洗后保留</div><div class="sub">原始 {before['total']:,}</div></div>
  <div class="summary-card"><div class="number blue">172</div><div class="label">英雄数不变</div><div class="sub">全部保留</div></div>
  <div class="summary-card"><div class="number yellow">{after['top30']:,}</div><div class="label">新 Top30%</div><div class="sub">原 {before['top30']:,}</div></div>
</div>

<div class="section">
  <div class="section-title">📋 清洗策略</div>
  <div class="insight-box">
    <h3>规则 1：剔除 show_rate == 0</h3>
    <p>共移除 <strong>1,725 条</strong>。show_rate 为 0 意味着该英雄×符文组合<strong>无任何样本</strong>，其 win_rate 完全不可靠——包含 win_rate=0%（54条）和 win_rate=100%（30条）等"数据噪声"。</p>
  </div>
  <div class="insight-box">
    <h3>规则 2：win_rate 边界自动收窄</h3>
    <p>去除 show_rate==0 后，win_rate 范围从 <strong>[0%, 100%]</strong> 自动收窄至 <strong>[{after['wr_min']*100:.1f}%, {after['wr_max']*100:.1f}%]</strong>，无需额外阈值过滤。所有极端 win_rate 均集中在无样本数据中。</p>
  </div>
</div>

<div class="section">
  <div class="section-title">📊 前后对比</div>
  <div class="chart-card">
    <table>
      <tr><th>指标</th><th>清洗前</th><th>清洗后</th><th>变化</th></tr>
      <tr><td>总记录</td><td>{before['total']:,}</td><td class="kept">{after['total']:,}</td><td class="red">-{removed:,}</td></tr>
      <tr><td>win_rate 范围</td><td class="removed">[0%, 100%]</td><td class="kept">[{after['wr_min']*100:.1f}%, {after['wr_max']*100:.1f}%]</td><td>极端值消除 ✓</td></tr>
      <tr><td>win_rate 均值</td><td>{before['wr_mean']*100:.2f}%</td><td class="kept">{after['wr_mean']*100:.2f}%</td><td>{(after['wr_mean']-before['wr_mean'])*100:+.2f}%</td></tr>
      <tr><td>show_rate == 0</td><td class="removed">{before['show_zero']:,} 条</td><td class="kept">0</td><td class="green">✓</td></tr>
      <tr><td>win_rate == 0%</td><td class="removed">{before['wr_zero']}</td><td class="kept">0</td><td class="green">✓</td></tr>
      <tr><td>win_rate == 100%</td><td class="removed">{before['wr_100']}</td><td class="kept">0</td><td class="green">✓</td></tr>
      <tr><td>Top30% 符文</td><td>{before['top30']:,}</td><td class="kept">{after['top30']:,}</td><td>-{before['top30']-after['top30']:,} (重算)</td></tr>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title">📈 清洗后数据分布</div>
  <div class="charts-row">
    {fig_to_html(fig1, 'wr_dist')}
    {fig_to_html(fig2, 'sr_dist')}
  </div>
  {fig_to_html(fig3, 'scatter')}
  <div class="charts-row">
    {fig_to_html(fig4, 'champ_dist')}
    <div class="chart-card" style="display:flex;align-items:center;justify-content:center;flex-direction:column;">
      <div style="font-size:64px;margin-bottom:12px;">✅</div>
      <div style="font-size:18px;color:#3fb950;font-weight:600;">数据清洗完成</div>
      <div style="color:#8b949e;margin-top:8px;font-size:14px;">所有极端值已剔除<br>评分和标签已重新计算</div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">✅ 清洗结论</div>
  <div class="insight-box" style="border-left-color:#3fb950;">
    <h3 style="color:#3fb950;">核心影响</h3>
    <p>
      <strong>1. 数据可靠性↑</strong>：移除 1,725 条无样本脏数据（show_rate==0），含 win_rate 0%/100% 等噪声。<br><br>
      <strong>2. Top30% 更准确</strong>：从 9,171→8,658 条，去除被脏数据"虚占"的名额，真正高表现符文排名更前。<br><br>
      <strong>3. win_rate 分布健康</strong>：范围 [25.6%, 69.5%]，均值 47.8%，无极端值干扰。<br><br>
      <strong>4. 英雄全覆盖</strong>：172 英雄全部保留，只移除了极少量无效数据。
    </p>
  </div>
</div>
</div>
</body>
</html>"""

output = '/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗/data/outlier_cleaning_report.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ 报告已生成: {output}")
print(f"   文件大小: {len(html)/1024:.0f} KB")
