# -*- coding: utf-8 -*-
"""
英雄×符文 Top5 胜率分析
- 数据源: step1_2_champion_augment_stats.csv (英雄×符文 胜率 & 选取率)
- 逻辑:
  1. 计算全局 pick 率的 P5 分位数作为阈值
  2. 排除 pick 率 < P5 的英雄×符文组合
  3. 对每个英雄，按胜率降序取 Top5 符文
  4. 输出交互式 HTML 报告（plotly）
"""
import json
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "recommend", "data")
RAW_DIR = os.path.join(BASE_DIR, "output", "raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# ==================== 1. 加载数据 ====================
print("=" * 60)
print("  英雄×符文 Top5 胜率分析")
print("=" * 60)

# 加载英雄×符文统计
df = pd.read_csv(os.path.join(DATA_DIR, "step1_2_champion_augment_stats.csv"))
df["win_rate_pct"] = df["win_rate"] * 100  # 转百分比
df["show_rate_pct"] = df["show_rate"] * 100  # 转百分比

# 加载映射表
with open(os.path.join(RAW_DIR, "champion_id_map.json"), "r", encoding="utf-8") as f:
    champion_id_map = json.load(f)

with open(os.path.join(RAW_DIR, "augment_id_map.json"), "r", encoding="utf-8") as f:
    augment_id_map = json.load(f)

# 映射中文名
df["hero_name"] = df["championid"].astype(str).map(champion_id_map)
df["augment_name"] = df["player_augment"].astype(str).map(augment_id_map)

# 过滤掉无法映射的行
df_valid = df.dropna(subset=["hero_name", "augment_name"]).copy()

print(f"\n📊 数据概览:")
print(f"  总记录数: {len(df):,}")
print(f"  有效记录（可映射中文名）: {len(df_valid):,}")
print(f"  英雄数: {df_valid['hero_name'].nunique()}")
print(f"  符文数: {df_valid['augment_name'].nunique()}")

# ==================== 2. 加载符文等级信息 ====================
# 从Excel知识库获取符文等级（白银/黄金/棱彩）
augment_level_map = {}
excel_path = os.path.join(OUTPUT_DIR, "海克斯大乱斗符文知识库.xlsx")
if os.path.exists(excel_path):
    df_info = pd.read_excel(excel_path, sheet_name="符文基础信息")
    for _, row in df_info.iterrows():
        name = str(row["符文名称"])
        level = str(row.get("等级", ""))
        if name and level:
            augment_level_map[name] = level
    print(f"  符文等级映射: {len(augment_level_map)} 条")

df_valid["augment_level"] = df_valid["augment_name"].map(augment_level_map)

# ==================== 3. 计算 P5 阈值并过滤 ====================
# 注意: 数据中有大量 pick 率 = 0 的记录 (小样本噪声，如胜率100%但0 pick)
# 策略: 先排除 pick 率 = 0，再在非零 pick 率中取 P5 作为阈值
zero_pick_count = (df_valid["show_rate_pct"] == 0).sum()
df_nonzero = df_valid[df_valid["show_rate_pct"] > 0].copy()
p5_threshold = np.percentile(df_nonzero["show_rate_pct"], 5)

print(f"\n🔍 Pick率分布:")
print(f"  pick率=0 的记录: {zero_pick_count} ({zero_pick_count/len(df_valid)*100:.1f}%) ← 直接排除")
print(f"  排除0后剩余: {len(df_nonzero):,} 条")
print(f"\n  非零 pick 率分位数:")
print(f"  min:  {df_nonzero['show_rate_pct'].min():.6f}%")
print(f"  P5:   {p5_threshold:.6f}%  ← 过滤阈值")
print(f"  P25:  {np.percentile(df_nonzero['show_rate_pct'], 25):.6f}%")
print(f"  P50:  {np.percentile(df_nonzero['show_rate_pct'], 50):.6f}%")
print(f"  P75:  {np.percentile(df_nonzero['show_rate_pct'], 75):.6f}%")
print(f"  P95:  {np.percentile(df_nonzero['show_rate_pct'], 95):.6f}%")
print(f"  max:  {df_nonzero['show_rate_pct'].max():.6f}%")

# 过滤: pick 率 > 0 且 >= P5
df_filtered = df_nonzero[df_nonzero["show_rate_pct"] >= p5_threshold].copy()
removed_count = len(df_valid) - len(df_filtered)
print(f"\n✂️  过滤结果:")
print(f"  过滤前: {len(df_valid):,} 条")
print(f"  过滤后: {len(df_filtered):,} 条")
print(f"  被移除: {removed_count:,} 条 ({removed_count/len(df_valid)*100:.1f}%)")
print(f"    其中 pick=0: {zero_pick_count} 条")
print(f"    其中 0<pick<P5: {removed_count - zero_pick_count} 条")

# ==================== 4. 每个英雄 Top5 胜率符文 ====================
# 策略: 先排除每个英雄内部选取率排名在后5%（P5以下）的符文，再取 Top5
top5_list = []
hero_p5_removed = 0  # 统计因英雄内部 P5 过滤被移除的符文数
for hero, group in df_filtered.groupby("hero_name"):
    # 计算该英雄所有符文的选取率排名（降序，选取率越高排名越小）
    group_ranked = group.copy()
    group_ranked["pick_rank"] = group_ranked["show_rate_pct"].rank(ascending=False, method="min").astype(int)
    total_augments = len(group_ranked)

    # 计算该英雄内部的 P5 阈值（选取率后5%）
    hero_p5 = np.percentile(group_ranked["show_rate_pct"], 5)
    # 排除选取率低于英雄内部 P5 的符文
    group_above_p5 = group_ranked[group_ranked["show_rate_pct"] >= hero_p5]
    hero_p5_removed += (len(group_ranked) - len(group_above_p5))

    top5 = group_above_p5.nlargest(5, "win_rate_pct")
    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        top5_list.append({
            "英雄": hero,
            "排名": rank,
            "符文": row["augment_name"],
            "符文等级": row.get("augment_level", ""),
            "胜率(%)": round(row["win_rate_pct"], 2),
            "选取率(%)": round(row["show_rate_pct"], 6),
            "选取率排名": f"{row['pick_rank']}/{total_augments}",
        })

print(f"\n🛡️  英雄内部 P5 过滤: 额外移除 {hero_p5_removed} 条低选取率符文")

df_top5 = pd.DataFrame(top5_list)

print(f"\n🏆 每个英雄 Top5 胜率符文:")
print(f"  涉及英雄: {df_top5['英雄'].nunique()} 个")
print(f"  涉及符文: {df_top5['符文'].nunique()} 个")
print(f"  总记录: {len(df_top5)} 条")

# ==================== 5. 统计分析 ====================
# Top5 胜率分布
print(f"\n📈 Top5 符文胜率分布:")
print(f"  平均: {df_top5['胜率(%)'].mean():.2f}%")
print(f"  中位数: {df_top5['胜率(%)'].median():.2f}%")
print(f"  最高: {df_top5['胜率(%)'].max():.2f}%")
print(f"  最低: {df_top5['胜率(%)'].min():.2f}%")

# 最热门的 Top5 符文（出现在最多英雄的 Top5 中）
aug_freq = df_top5.groupby("符文").agg(
    出现次数=("英雄", "count"),
    平均胜率=("胜率(%)", "mean"),
    平均选取率=("选取率(%)", "mean"),
    符文等级=("符文等级", "first"),
).reset_index().sort_values("出现次数", ascending=False)

print(f"\n🔥 最常出现在 Top5 中的符文 (Top 20):")
for _, row in aug_freq.head(20).iterrows():
    print(f"  {row['符文']:15s} | 等级: {row['符文等级']:3s} | "
          f"出现 {row['出现次数']:3d} 次 | 平均胜率 {row['平均胜率']:.2f}% | "
          f"平均选取率 {row['平均选取率']:.6f}%")

# ==================== 6. 生成交互式 HTML 报告 ====================
print("\n📊 正在生成交互式报告...")

# --- 图表1: Pick率分布直方图 + P5阈值线 ---
fig1 = go.Figure()
fig1.add_trace(go.Histogram(
    x=df_valid["show_rate_pct"],
    nbinsx=100,
    name="Pick率分布",
    marker_color="steelblue",
    opacity=0.8,
))
fig1.add_vline(x=p5_threshold, line_dash="dash", line_color="red", line_width=2,
               annotation_text=f"P5 = {p5_threshold:.6f}%",
               annotation_position="top right",
               annotation_font_size=14,
               annotation_font_color="red")
fig1.update_layout(
    title="英雄×符文 Pick率分布 (P5 过滤阈值)",
    xaxis_title="Pick率 (%)",
    yaxis_title="频次",
    template="plotly_white",
    height=400,
)
fig1_html = fig1.to_html(full_html=False, include_plotlyjs=False)

# --- 图表2: 最常出现在 Top5 中的符文 (Top 30) ---
top30_aug = aug_freq.head(30).sort_values("出现次数", ascending=True)
colors = top30_aug["符文等级"].map({
    "白银": "#C0C0C0", "黄金": "#FFD700", "棱彩": "#FF69B4"
}).fillna("#888888")

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    y=top30_aug["符文"],
    x=top30_aug["出现次数"],
    orientation="h",
    marker_color=colors.tolist(),
    text=[f'{int(x)}次 | 胜率{wr:.1f}%' for x, wr in zip(top30_aug["出现次数"], top30_aug["平均胜率"])],
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>出现次数: %{x}<br>平均胜率: %{customdata[0]:.2f}%<br>等级: %{customdata[1]}<extra></extra>",
    customdata=list(zip(top30_aug["平均胜率"], top30_aug["符文等级"])),
))
fig2.update_layout(
    title="最常出现在英雄 Top5 中的符文 (Top 30)",
    xaxis_title="出现在多少英雄的 Top5 中",
    yaxis_title="",
    template="plotly_white",
    height=max(600, len(top30_aug) * 22),
    margin=dict(l=180),
)
fig2_html = fig2.to_html(full_html=False, include_plotlyjs=False)

# --- 图表3: Top5 胜率散点图（按符文等级着色）---
fig3 = go.Figure()
level_colors = {"白银": "#C0C0C0", "黄金": "#FFD700", "棱彩": "#FF69B4"}
for level, color in level_colors.items():
    mask = df_top5["符文等级"] == level
    if mask.any():
        sub = df_top5[mask]
        fig3.add_trace(go.Scatter(
            x=sub["选取率(%)"],
            y=sub["胜率(%)"],
            mode="markers",
            name=level,
            marker=dict(color=color, size=6, opacity=0.6, line=dict(width=0.5, color="gray")),
            hovertemplate="<b>%{customdata[0]}</b><br>符文: %{customdata[1]}<br>"
                          "胜率: %{y:.2f}%<br>选取率: %{x:.6f}%<extra></extra>",
            customdata=list(zip(sub["英雄"], sub["符文"])),
        ))

fig3.update_layout(
    title="英雄 Top5 符文: 胜率 vs 选取率 (按符文等级)",
    xaxis_title="选取率 (%)",
    yaxis_title="胜率 (%)",
    template="plotly_white",
    height=500,
    legend=dict(title="符文等级"),
)
fig3_html = fig3.to_html(full_html=False, include_plotlyjs=False)

# --- 图表4: 每个英雄 Top1 胜率分布 ---
top1 = df_top5[df_top5["排名"] == 1].copy()
top1_sorted = top1.sort_values("胜率(%)", ascending=True)

fig4 = go.Figure()
fig4.add_trace(go.Bar(
    y=top1_sorted["英雄"],
    x=top1_sorted["胜率(%)"],
    orientation="h",
    marker_color="steelblue",
    text=[f'{wr:.1f}% ({aug})' for wr, aug in zip(top1_sorted["胜率(%)"], top1_sorted["符文"])],
    textposition="outside",
    textfont_size=8,
    hovertemplate="<b>%{y}</b><br>最佳符文: %{customdata[0]}<br>"
                  "胜率: %{x:.2f}%<br>选取率: %{customdata[1]:.6f}%<extra></extra>",
    customdata=list(zip(top1_sorted["符文"], top1_sorted["选取率(%)"])),
))
fig4.update_layout(
    title="每个英雄的 Top1 最高胜率符文",
    xaxis_title="胜率 (%)",
    yaxis_title="",
    template="plotly_white",
    height=max(800, len(top1_sorted) * 16),
    margin=dict(l=100),
)
fig4_html = fig4.to_html(full_html=False, include_plotlyjs=False)

# --- 图表5: Top5符文等级分布 ---
level_dist = df_top5["符文等级"].value_counts()
fig5 = go.Figure()
fig5.add_trace(go.Pie(
    labels=level_dist.index.tolist(),
    values=level_dist.values.tolist(),
    marker_colors=[level_colors.get(l, "#888") for l in level_dist.index],
    textinfo="label+percent+value",
    hovertemplate="<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>",
))
fig5.update_layout(
    title="Top5 符文等级分布",
    template="plotly_white",
    height=400,
)
fig5_html = fig5.to_html(full_html=False, include_plotlyjs=False)

# ==================== 7. 生成完整的 HTML 表格（可搜索） ====================
# 将 df_top5 按英雄分组，生成可搜索的表格
heroes_json = json.dumps(
    df_top5.to_dict(orient="records"),
    ensure_ascii=False
)
aug_freq_json = json.dumps(
    aug_freq.to_dict(orient="records"),
    ensure_ascii=False
)

# ==================== 8. 组装完整 HTML ====================
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英雄×符文 Top5 胜率分析</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        h1 {{ text-align: center; font-size: 28px; margin: 20px 0; color: #2c3e50; }}
        .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 30px; font-size: 14px; }}
        
        /* KPI cards */
        .kpi-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
        .kpi-card {{ flex: 1; min-width: 180px; background: white; border-radius: 12px; padding: 20px;
                     box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }}
        .kpi-card .value {{ font-size: 32px; font-weight: 700; color: #2c3e50; }}
        .kpi-card .label {{ font-size: 13px; color: #7f8c8d; margin-top: 4px; }}
        .kpi-card.highlight .value {{ color: #e74c3c; }}
        
        /* Section */
        .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .section h2 {{ font-size: 18px; color: #2c3e50; margin-bottom: 16px; border-left: 4px solid #3498db; padding-left: 12px; }}
        
        /* Search / Filter */
        .filter-bar {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
        .filter-bar input, .filter-bar select {{
            padding: 8px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none;
        }}
        .filter-bar input:focus, .filter-bar select:focus {{ border-color: #3498db; }}
        
        /* Table */
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ background: #2c3e50; color: white; padding: 10px 12px; text-align: left; position: sticky; top: 0; cursor: pointer; }}
        th:hover {{ background: #34495e; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f0f7ff; }}
        .level-白银 {{ color: #7f8c8d; font-weight: 600; }}
        .level-黄金 {{ color: #d4a017; font-weight: 600; }}
        .level-棱彩 {{ color: #e91e8c; font-weight: 600; }}
        .rank-1 {{ font-weight: 700; color: #e74c3c; }}
        
        /* Tabs */
        .tabs {{ display: flex; gap: 4px; margin-bottom: 16px; }}
        .tab {{ padding: 8px 18px; border: 1px solid #ddd; border-radius: 8px 8px 0 0; cursor: pointer;
                background: #f5f6fa; font-size: 14px; }}
        .tab.active {{ background: white; border-bottom-color: white; font-weight: 600; color: #3498db; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        .table-container {{ max-height: 600px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
        .badge-silver {{ background: #ecf0f1; color: #7f8c8d; }}
        .badge-gold {{ background: #fef9e7; color: #d4a017; }}
        .badge-prismatic {{ background: #fce4ec; color: #e91e8c; }}
    </style>
</head>
<body>
<div class="container">
    <h1>🏆 英雄×符文 Top5 胜率分析</h1>
    <p class="subtitle">数据源: step1_2_champion_augment_stats.csv | 过滤: Pick率 ≥ P5 ({p5_threshold:.6f}%) | 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <!-- KPI Cards -->
    <div class="kpi-row">
        <div class="kpi-card"><div class="value">{df_valid['hero_name'].nunique()}</div><div class="label">英雄数</div></div>
        <div class="kpi-card"><div class="value">{df_valid['augment_name'].nunique()}</div><div class="label">符文数</div></div>
        <div class="kpi-card"><div class="value">{len(df_valid):,}</div><div class="label">英雄×符文组合</div></div>
        <div class="kpi-card highlight"><div class="value">{p5_threshold:.6f}%</div><div class="label">P5 过滤阈值</div></div>
        <div class="kpi-card"><div class="value">{len(df_filtered):,}</div><div class="label">过滤后组合数</div></div>
        <div class="kpi-card"><div class="value">{df_top5['胜率(%)'].mean():.1f}%</div><div class="label">Top5 平均胜率</div></div>
    </div>
    
    <!-- Tab Navigation -->
    <div class="tabs">
        <div class="tab active" onclick="switchTab('tab-table')">📋 数据表格</div>
        <div class="tab" onclick="switchTab('tab-charts')">📊 图表分析</div>
        <div class="tab" onclick="switchTab('tab-freq')">🔥 符文热度</div>
    </div>
    
    <!-- Tab 1: 数据表格 -->
    <div id="tab-table" class="tab-content active">
        <div class="section">
            <h2>每个英雄 Top5 胜率符文</h2>
            <div class="filter-bar">
                <input type="text" id="heroSearch" placeholder="🔍 搜索英雄..." oninput="filterTable()">
                <select id="levelFilter" onchange="filterTable()">
                    <option value="">全部等级</option>
                    <option value="白银">白银</option>
                    <option value="黄金">黄金</option>
                    <option value="棱彩">棱彩</option>
                </select>
                <select id="rankFilter" onchange="filterTable()">
                    <option value="">全部排名</option>
                    <option value="1">仅 Top1</option>
                    <option value="2">Top1-2</option>
                    <option value="3">Top1-3</option>
                </select>
                <span id="resultCount" style="color:#7f8c8d; font-size:13px;"></span>
            </div>
            <div class="table-container">
                <table id="mainTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)">英雄 ↕</th>
                            <th onclick="sortTable(1)">排名 ↕</th>
                            <th onclick="sortTable(2)">符文 ↕</th>
                            <th onclick="sortTable(3)">等级 ↕</th>
                            <th onclick="sortTable(4)">胜率(%) ↕</th>
                            <th onclick="sortTable(5)">选取率(%) ↕</th>
                            <th onclick="sortTable(6)">选取率排名 ↕</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <!-- Tab 2: 图表 -->
    <div id="tab-charts" class="tab-content">
        <div class="section">
            <h2>Pick率分布 & P5 过滤阈值</h2>
            <div>{fig1_html}</div>
        </div>
        <div class="section">
            <h2>Top5 胜率 vs 选取率散点图</h2>
            <div>{fig3_html}</div>
        </div>
        <div class="section">
            <h2>每个英雄的 Top1 最高胜率符文</h2>
            <div>{fig4_html}</div>
        </div>
        <div class="section">
            <h2>Top5 符文等级分布</h2>
            <div>{fig5_html}</div>
        </div>
    </div>
    
    <!-- Tab 3: 符文热度 -->
    <div id="tab-freq" class="tab-content">
        <div class="section">
            <h2>最常出现在英雄 Top5 中的符文</h2>
            <div>{fig2_html}</div>
        </div>
        <div class="section">
            <h2>符文热度详情表</h2>
            <div class="table-container">
                <table id="freqTable">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>符文</th>
                            <th>等级</th>
                            <th>出现英雄数</th>
                            <th>平均胜率(%)</th>
                            <th>平均选取率(%)</th>
                        </tr>
                    </thead>
                    <tbody id="freqBody"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
const allData = {heroes_json};
const freqData = {aug_freq_json};

// 渲染主表格
function renderTable(data) {{
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    data.forEach(row => {{
        const levelClass = row['符文等级'] === '白银' ? 'badge-silver' :
                          row['符文等级'] === '黄金' ? 'badge-gold' :
                          row['符文等级'] === '棱彩' ? 'badge-prismatic' : '';
        const rankClass = row['排名'] === 1 ? 'rank-1' : '';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${{row['英雄']}}</td>
            <td class="${{rankClass}}">#${{row['排名']}}</td>
            <td>${{row['符文']}}</td>
            <td><span class="badge ${{levelClass}}">${{row['符文等级'] || '-'}}</span></td>
            <td style="font-weight:600">${{row['胜率(%)'].toFixed(2)}}%</td>
            <td>${{row['选取率(%)'].toFixed(6)}}%</td>
            <td style="color:#3498db; font-weight:600">${{row['选取率排名'] || '-'}}</td>
        `;
        tbody.appendChild(tr);
    }});
    document.getElementById('resultCount').textContent = `显示 ${{data.length}} 条`;
}}

// 渲染频率表格
function renderFreqTable() {{
    const tbody = document.getElementById('freqBody');
    tbody.innerHTML = '';
    freqData.forEach((row, i) => {{
        const levelClass = row['符文等级'] === '白银' ? 'badge-silver' :
                          row['符文等级'] === '黄金' ? 'badge-gold' :
                          row['符文等级'] === '棱彩' ? 'badge-prismatic' : '';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${{i + 1}}</td>
            <td>${{row['符文']}}</td>
            <td><span class="badge ${{levelClass}}">${{row['符文等级'] || '-'}}</span></td>
            <td style="font-weight:600">${{row['出现次数']}}</td>
            <td>${{row['平均胜率'].toFixed(2)}}%</td>
            <td>${{row['平均选取率'].toFixed(6)}}%</td>
        `;
        tbody.appendChild(tr);
    }});
}}

// 过滤
function filterTable() {{
    const heroQ = document.getElementById('heroSearch').value.toLowerCase();
    const levelQ = document.getElementById('levelFilter').value;
    const rankQ = document.getElementById('rankFilter').value;
    
    let filtered = allData;
    if (heroQ) filtered = filtered.filter(r => r['英雄'].toLowerCase().includes(heroQ));
    if (levelQ) filtered = filtered.filter(r => r['符文等级'] === levelQ);
    if (rankQ) filtered = filtered.filter(r => r['排名'] <= parseInt(rankQ));
    
    renderTable(filtered);
}}

// 排序
let sortDir = {{}};
function sortTable(colIdx) {{
    const keys = ['英雄', '排名', '符文', '符文等级', '胜率(%)', '选取率(%)', '选取率排名'];
    const key = keys[colIdx];
    sortDir[key] = !sortDir[key];
    const dir = sortDir[key] ? 1 : -1;
    
    const heroQ = document.getElementById('heroSearch').value.toLowerCase();
    const levelQ = document.getElementById('levelFilter').value;
    const rankQ = document.getElementById('rankFilter').value;
    
    let filtered = allData;
    if (heroQ) filtered = filtered.filter(r => r['英雄'].toLowerCase().includes(heroQ));
    if (levelQ) filtered = filtered.filter(r => r['符文等级'] === levelQ);
    if (rankQ) filtered = filtered.filter(r => r['排名'] <= parseInt(rankQ));
    
    filtered.sort((a, b) => {{
        if (typeof a[key] === 'number') return (a[key] - b[key]) * dir;
        return a[key].localeCompare(b[key]) * dir;
    }});
    renderTable(filtered);
}}

// Tab切换
function switchTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');
}}

// 初始化
renderTable(allData);
renderFreqTable();
</script>
</body>
</html>"""

output_path = os.path.join(OUTPUT_DIR, "hero_top5_runes_analysis.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n✅ 报告已生成: {output_path}")

# 也导出CSV方便查看
csv_path = os.path.join(OUTPUT_DIR, "hero_top5_runes.csv")
df_top5.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"✅ CSV已导出: {csv_path}")

# 导出符文热度CSV
freq_csv_path = os.path.join(OUTPUT_DIR, "augment_top5_frequency.csv")
aug_freq.to_csv(freq_csv_path, index=False, encoding="utf-8-sig")
print(f"✅ 符文热度CSV已导出: {freq_csv_path}")
