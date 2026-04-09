import pandas as pd
import json

filepath = '10_Work/海克斯大乱斗/测试.xlsx'

df_pool = pd.read_excel(filepath, sheet_name='完整预选池')
df_best = pd.read_excel(filepath, sheet_name='最佳拍档')
df_strong = pd.read_excel(filepath, sheet_name='强力单卡')
df_fun = pd.read_excel(filepath, sheet_name='娱乐')
df_hero_map = pd.read_excel('10_Work/海克斯大乱斗/data/英雄id定位表.xlsx')

# 映射
title_to_name = dict(zip(df_hero_map['称号'], df_hero_map['中文名']))
name_to_title = dict(zip(df_hero_map['中文名'], df_hero_map['称号']))

# 预选池推荐（英雄×符文）
rec = df_pool[df_pool['标签'] == '推荐'].copy()
rec_pairs = set(zip(rec['英雄名称'], rec['符文名称']))
total = len(rec_pairs)

# 最佳拍档
best_pairs = set(zip(df_best['英雄'], df_best['符文']))

# 强力单卡
strong_pairs = set(zip(df_strong['champion_name'], df_strong['augment_name']))

# 娱乐（中文名→称号）
df_fun['称号'] = df_fun['英雄ID'].map(name_to_title)
fun_valid = df_fun.dropna(subset=['称号'])
fun_pairs = set(zip(fun_valid['称号'], fun_valid['符文ID']))

# 按优先级分配
results = []
for hero, aug in sorted(rec_pairs):
    in_best = (hero, aug) in best_pairs
    in_fun = (hero, aug) in fun_pairs
    in_strong = (hero, aug) in strong_pairs
    
    if in_best:
        label = '最佳拍档'
    elif in_fun:
        label = '娱乐'
    elif in_strong:
        label = '强力单卡'
    else:
        label = '无标签'
    
    all_labels = []
    if in_best: all_labels.append('最佳拍档')
    if in_fun: all_labels.append('娱乐')
    if in_strong: all_labels.append('强力单卡')
    
    hero_cn = title_to_name.get(hero, hero)
    results.append({
        'hero': hero,
        'hero_cn': hero_cn,
        'augment': aug,
        'label': label,
        'in_best': in_best,
        'in_fun': in_fun,
        'in_strong': in_strong,
        'all_labels': '、'.join(all_labels) if all_labels else '无'
    })

df_result = pd.DataFrame(results)

from collections import Counter
label_counts = Counter(df_result['label'])

stats = []
for label in ['最佳拍档', '娱乐', '强力单卡', '无标签']:
    count = label_counts.get(label, 0)
    stats.append({'label': label, 'count': count, 'pct': round(count/total*100, 1)})

# 无标签分析
no_label_df = df_result[df_result['label'] == '无标签']
no_label_by_hero = no_label_df.groupby(['hero', 'hero_cn']).size().reset_index(name='count').sort_values('count', ascending=False)
no_label_by_aug = no_label_df.groupby('augment').size().reset_index(name='count').sort_values('count', ascending=False)

# 覆盖率（有标签的比例）
covered = total - label_counts.get('无标签', 0)
cover_pct = round(covered / total * 100, 1)

detail_json = json.dumps(results, ensure_ascii=False)
stats_json = json.dumps(stats, ensure_ascii=False)
no_label_hero_json = json.dumps(no_label_by_hero.head(30).to_dict('records'), ensure_ascii=False)
no_label_aug_json = json.dumps(no_label_by_aug.head(30).to_dict('records'), ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>预选池推荐符文标签分析（英雄×符文维度）</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1923; color: #e8e8e8; padding: 24px; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
h1 {{ text-align: center; font-size: 28px; font-weight: 700; margin-bottom: 8px; background: linear-gradient(135deg, #ffd700, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.subtitle {{ text-align: center; color: #8899aa; font-size: 14px; margin-bottom: 32px; }}
.subtitle strong {{ color: #ffd700; font-size: 18px; }}

.summary-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px; }}
.stat-card {{ background: #1a2736; border-radius: 12px; padding: 24px; text-align: center; border: 1px solid #2a3a4a; position: relative; overflow: hidden; }}
.stat-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }}
.stat-card.total::before {{ background: linear-gradient(90deg, #fff, #aabbcc); }}
.stat-card.best::before {{ background: linear-gradient(90deg, #ffd700, #ffaa00); }}
.stat-card.fun::before {{ background: linear-gradient(90deg, #ff6b9d, #c44dff); }}
.stat-card.strong::before {{ background: linear-gradient(90deg, #00d4ff, #0088ff); }}
.stat-card.none::before {{ background: linear-gradient(90deg, #ff4444, #ff8800); }}
.stat-number {{ font-size: 38px; font-weight: 800; line-height: 1.1; }}
.stat-card.total .stat-number {{ color: #fff; }}
.stat-card.best .stat-number {{ color: #ffd700; }}
.stat-card.fun .stat-number {{ color: #ff6b9d; }}
.stat-card.strong .stat-number {{ color: #00d4ff; }}
.stat-card.none .stat-number {{ color: #ff6b35; }}
.stat-pct {{ font-size: 16px; color: #8899aa; margin-top: 4px; }}
.stat-label {{ font-size: 14px; color: #aabbcc; margin-top: 8px; font-weight: 500; }}

.chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }}
.chart-card {{ background: #1a2736; border-radius: 12px; padding: 20px; border: 1px solid #2a3a4a; }}
.chart-title {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #dde; }}

.priority-note {{ background: #1a2736; border-radius: 12px; padding: 16px 24px; border: 1px solid #2a3a4a; margin-bottom: 32px; }}
.priority-note .title {{ font-size: 14px; color: #ffd700; font-weight: 600; margin-bottom: 8px; }}
.priority-note .desc {{ font-size: 13px; color: #8899aa; line-height: 1.6; }}
.priority-arrow {{ color: #ffd700; font-weight: 700; }}

.analysis-section {{ background: #1a2736; border-radius: 12px; padding: 24px; border: 1px solid #2a3a4a; margin-bottom: 32px; }}
.analysis-section h3 {{ font-size: 16px; margin-bottom: 16px; color: #ff6b35; }}
.analysis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}

.detail-section {{ background: #1a2736; border-radius: 12px; padding: 24px; border: 1px solid #2a3a4a; }}
.detail-section h3 {{ font-size: 16px; margin-bottom: 16px; color: #dde; }}
.filter-bar {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
.filter-btn {{ padding: 6px 16px; border-radius: 20px; border: 1px solid #3a4a5a; background: #2a3a4a; color: #aabbcc; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
.filter-btn:hover {{ background: #3a4a5a; }}
.filter-btn.active {{ background: #ffd700; color: #0f1923; border-color: #ffd700; font-weight: 600; }}
.search-box {{ padding: 6px 16px; border-radius: 20px; border: 1px solid #3a4a5a; background: #2a3a4a; color: #e8e8e8; font-size: 13px; width: 200px; outline: none; }}
.search-box:focus {{ border-color: #ffd700; }}

table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #0f1923; padding: 10px 12px; text-align: left; font-size: 13px; color: #8899aa; border-bottom: 2px solid #2a3a4a; position: sticky; top: 0; z-index: 1; }}
td {{ padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #1f2f3f; }}
tr:hover td {{ background: #1f2f3f; }}
.table-wrapper {{ max-height: 600px; overflow-y: auto; border-radius: 8px; }}
.tag {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }}
.tag-best {{ background: rgba(255,215,0,0.15); color: #ffd700; }}
.tag-fun {{ background: rgba(255,107,157,0.15); color: #ff6b9d; }}
.tag-strong {{ background: rgba(0,212,255,0.15); color: #00d4ff; }}
.tag-none {{ background: rgba(255,107,53,0.15); color: #ff6b35; }}

.mini-table {{ width: 100%; }}
.mini-table th {{ background: #0f1923; padding: 8px 10px; font-size: 12px; }}
.mini-table td {{ padding: 6px 10px; font-size: 12px; }}
.mini-table-wrapper {{ max-height: 350px; overflow-y: auto; border-radius: 8px; }}

.count-info {{ text-align: right; color: #8899aa; font-size: 12px; margin-bottom: 8px; }}
</style>
</head>
<body>
<div class="container">
<h1>🎮 预选池推荐符文 — 标签覆盖分析</h1>
<p class="subtitle">以「英雄 × 符文」所有 <strong>{total:,}</strong> 个条目为分母，匹配最佳拍档 / 娱乐 / 强力单卡三个标签</p>

<div class="priority-note">
  <div class="title">📌 分析说明</div>
  <div class="desc">
    <b>分母</b>：预选池中标签为"推荐"的所有「英雄 × 符文」组合，共 <b>{total:,}</b> 条<br>
    <b>标签优先级</b>：当一个条目同时出现在多个标签页签中，按优先级分配唯一标签：
    <span class="priority-arrow">最佳拍档 &gt; 娱乐 &gt; 强力单卡</span><br>
    <b>覆盖率</b>：{cover_pct}% 的条目至少匹配到一个标签
  </div>
</div>

<div class="summary-grid">
  <div class="stat-card total">
    <div class="stat-number">{total:,}</div>
    <div class="stat-pct">100%</div>
    <div class="stat-label">总条目数</div>
  </div>
  <div class="stat-card best">
    <div class="stat-number">{stats[0]['count']:,}</div>
    <div class="stat-pct">{stats[0]['pct']}%</div>
    <div class="stat-label">最佳拍档</div>
  </div>
  <div class="stat-card fun">
    <div class="stat-number">{stats[1]['count']:,}</div>
    <div class="stat-pct">{stats[1]['pct']}%</div>
    <div class="stat-label">娱乐</div>
  </div>
  <div class="stat-card strong">
    <div class="stat-number">{stats[2]['count']:,}</div>
    <div class="stat-pct">{stats[2]['pct']}%</div>
    <div class="stat-label">强力单卡</div>
  </div>
  <div class="stat-card none">
    <div class="stat-number">{stats[3]['count']:,}</div>
    <div class="stat-pct">{stats[3]['pct']}%</div>
    <div class="stat-label">⚠️ 无标签</div>
  </div>
</div>

<div class="chart-row">
  <div class="chart-card">
    <div class="chart-title">标签分布（饼图）</div>
    <div id="pie-chart"></div>
  </div>
  <div class="chart-card">
    <div class="chart-title">标签分布（条形图）</div>
    <div id="bar-chart"></div>
  </div>
</div>

<div class="analysis-section">
  <h3>⚠️ 无标签条目深度分析（{stats[3]['count']:,} 条，占 {stats[3]['pct']}%）</h3>
  <div class="analysis-grid">
    <div>
      <div class="chart-title">无标签 — 按英雄分布 Top 30</div>
      <div id="no-label-hero-chart"></div>
    </div>
    <div>
      <div class="chart-title">无标签 — 按符文分布 Top 30</div>
      <div id="no-label-aug-chart"></div>
    </div>
  </div>
</div>

<div class="detail-section">
  <h3>📋 全量明细（{total:,} 条）</h3>
  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all">全部 ({total:,})</button>
    <button class="filter-btn" data-filter="最佳拍档">最佳拍档 ({stats[0]['count']:,})</button>
    <button class="filter-btn" data-filter="娱乐">娱乐 ({stats[1]['count']:,})</button>
    <button class="filter-btn" data-filter="强力单卡">强力单卡 ({stats[2]['count']:,})</button>
    <button class="filter-btn" data-filter="无标签">无标签 ({stats[3]['count']:,})</button>
    <input type="text" class="search-box" id="searchBox" placeholder="搜索英雄或符文...">
  </div>
  <div class="count-info" id="countInfo"></div>
  <div class="table-wrapper">
    <table id="detail-table">
      <thead><tr><th>#</th><th>英雄（称号）</th><th>英雄（中文名）</th><th>符文名称</th><th>分配标签</th><th>所有匹配</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>
</div>

<script>
const data = {detail_json};
const stats = {stats_json};
const noLabelHero = {no_label_hero_json};
const noLabelAug = {no_label_aug_json};

// 饼图
Plotly.newPlot('pie-chart', [{{
  type: 'pie',
  labels: stats.map(s => s.label),
  values: stats.map(s => s.count),
  marker: {{ colors: ['#ffd700', '#ff6b9d', '#00d4ff', '#ff6b35'] }},
  textinfo: 'label+value+percent',
  textfont: {{ size: 13, color: '#fff' }},
  hole: 0.45,
  pull: [0, 0, 0, 0.05]
}}], {{
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{ t: 10, b: 10, l: 10, r: 10 }},
  height: 340,
  showlegend: false,
  annotations: [{{ text: '{total:,}<br>条目', showarrow: false, font: {{ size: 18, color: '#fff' }} }}]
}}, {{ responsive: true, displayModeBar: false }});

// 条形图
Plotly.newPlot('bar-chart', [{{
  type: 'bar',
  x: stats.map(s => s.label),
  y: stats.map(s => s.count),
  text: stats.map(s => s.count.toLocaleString() + ' (' + s.pct + '%)'),
  textposition: 'outside',
  textfont: {{ color: '#ccc', size: 13 }},
  marker: {{ color: ['#ffd700', '#ff6b9d', '#00d4ff', '#ff6b35'] }}
}}], {{
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{ t: 30, b: 40, l: 60, r: 20 }},
  height: 340,
  xaxis: {{ color: '#8899aa', gridcolor: '#1f2f3f' }},
  yaxis: {{ color: '#8899aa', gridcolor: '#1f2f3f', title: '条目数' }}
}}, {{ responsive: true, displayModeBar: false }});

// 无标签 — 按英雄
Plotly.newPlot('no-label-hero-chart', [{{
  type: 'bar',
  y: noLabelHero.map(d => d.hero_cn || d.hero),
  x: noLabelHero.map(d => d.count),
  text: noLabelHero.map(d => d.count),
  textposition: 'outside',
  textfont: {{ color: '#ccc', size: 11 }},
  orientation: 'h',
  marker: {{ color: '#ff6b35' }}
}}], {{
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{ t: 10, b: 30, l: 100, r: 40 }},
  height: Math.max(400, noLabelHero.length * 22),
  xaxis: {{ color: '#8899aa', gridcolor: '#1f2f3f' }},
  yaxis: {{ color: '#8899aa', autorange: 'reversed' }}
}}, {{ responsive: true, displayModeBar: false }});

// 无标签 — 按符文
Plotly.newPlot('no-label-aug-chart', [{{
  type: 'bar',
  y: noLabelAug.map(d => d.augment),
  x: noLabelAug.map(d => d.count),
  text: noLabelAug.map(d => d.count),
  textposition: 'outside',
  textfont: {{ color: '#ccc', size: 11 }},
  orientation: 'h',
  marker: {{ color: '#ff8844' }}
}}], {{
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{ t: 10, b: 30, l: 100, r: 40 }},
  height: Math.max(400, noLabelAug.length * 22),
  xaxis: {{ color: '#8899aa', gridcolor: '#1f2f3f' }},
  yaxis: {{ color: '#8899aa', autorange: 'reversed' }}
}}, {{ responsive: true, displayModeBar: false }});

// 表格
const tagClass = {{'最佳拍档': 'tag-best', '娱乐': 'tag-fun', '强力单卡': 'tag-strong', '无标签': 'tag-none'}};
let currentFilter = 'all';
let currentSearch = '';

function renderTable() {{
  const tbody = document.querySelector('#detail-table tbody');
  let filtered = currentFilter === 'all' ? data : data.filter(d => d.label === currentFilter);
  if (currentSearch) {{
    const kw = currentSearch.toLowerCase();
    filtered = filtered.filter(d => 
      d.hero.toLowerCase().includes(kw) || 
      d.hero_cn.toLowerCase().includes(kw) || 
      d.augment.toLowerCase().includes(kw)
    );
  }}
  document.getElementById('countInfo').textContent = `显示 ${{filtered.length.toLocaleString()}} / ${{data.length.toLocaleString()}} 条`;
  tbody.innerHTML = filtered.map((d, i) => 
    `<tr><td>${{i+1}}</td><td>${{d.hero}}</td><td>${{d.hero_cn}}</td><td>${{d.augment}}</td><td><span class="tag ${{tagClass[d.label]}}">${{d.label}}</span></td><td>${{d.all_labels}}</td></tr>`
  ).join('');
}}
renderTable();

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.className = 'filter-btn');
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderTable();
  }});
}});

document.getElementById('searchBox').addEventListener('input', (e) => {{
  currentSearch = e.target.value.trim();
  renderTable();
}});
</script>
</body>
</html>"""

output_path = '10_Work/海克斯大乱斗/data/augment_label_analysis.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'✅ 报告已生成: {output_path}')
