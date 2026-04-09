import pandas as pd
import json
from collections import Counter

filepath = '10_Work/海克斯大乱斗/测试.xlsx'

df_pool = pd.read_excel(filepath, sheet_name='完整预选池')
df_best = pd.read_excel(filepath, sheet_name='最佳拍档')
df_strong = pd.read_excel(filepath, sheet_name='强力单卡')
df_fun = pd.read_excel(filepath, sheet_name='娱乐')

# 预选池推荐
rec = df_pool[df_pool['标签'] == '推荐']
rec_augments = sorted(rec['符文名称'].unique())
total = len(rec_augments)

# 三个标签的符文集合
best_set = set(df_best['符文'].unique())
strong_set = set(df_strong['augment_name'].unique())
fun_set = set(df_fun['符文ID'].unique())

# 按优先级分配标签
results = []
for aug in rec_augments:
    in_best = aug in best_set
    in_fun = aug in fun_set
    in_strong = aug in strong_set
    
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
    
    results.append({
        'augment': aug,
        'label': label,
        'in_best': in_best,
        'in_fun': in_fun,
        'in_strong': in_strong,
        'all_labels': '、'.join(all_labels) if all_labels else '无'
    })

df_result = pd.DataFrame(results)

# 统计
label_counts = Counter(df_result['label'])
stats = []
for label in ['最佳拍档', '娱乐', '强力单卡', '无标签']:
    count = label_counts.get(label, 0)
    stats.append({'label': label, 'count': count, 'pct': round(count/total*100, 1)})

no_label_augs = df_result[df_result['label'] == '无标签']['augment'].tolist()
detail_data = df_result.to_dict('records')

no_label_html = ''.join(f'<span class="no-label-item">{a}</span>' for a in no_label_augs)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>预选池推荐符文标签分析</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1923; color: #e8e8e8; padding: 24px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ text-align: center; font-size: 28px; font-weight: 700; margin-bottom: 8px; background: linear-gradient(135deg, #ffd700, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.subtitle {{ text-align: center; color: #8899aa; font-size: 14px; margin-bottom: 32px; }}

.summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
.stat-card {{ background: #1a2736; border-radius: 12px; padding: 24px; text-align: center; border: 1px solid #2a3a4a; position: relative; overflow: hidden; }}
.stat-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }}
.stat-card.best::before {{ background: linear-gradient(90deg, #ffd700, #ffaa00); }}
.stat-card.fun::before {{ background: linear-gradient(90deg, #ff6b9d, #c44dff); }}
.stat-card.strong::before {{ background: linear-gradient(90deg, #00d4ff, #0088ff); }}
.stat-card.none::before {{ background: linear-gradient(90deg, #666, #999); }}
.stat-number {{ font-size: 42px; font-weight: 800; line-height: 1.1; }}
.stat-card.best .stat-number {{ color: #ffd700; }}
.stat-card.fun .stat-number {{ color: #ff6b9d; }}
.stat-card.strong .stat-number {{ color: #00d4ff; }}
.stat-card.none .stat-number {{ color: #999; }}
.stat-pct {{ font-size: 16px; color: #8899aa; margin-top: 4px; }}
.stat-label {{ font-size: 14px; color: #aabbcc; margin-top: 8px; font-weight: 500; }}

.chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }}
.chart-card {{ background: #1a2736; border-radius: 12px; padding: 20px; border: 1px solid #2a3a4a; }}
.chart-title {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #dde; }}

.no-label-section {{ background: #1a2736; border-radius: 12px; padding: 24px; border: 1px solid #2a3a4a; margin-bottom: 32px; }}
.no-label-section h3 {{ font-size: 16px; margin-bottom: 16px; color: #ff6b35; }}
.no-label-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.no-label-item {{ background: #2a3a4a; padding: 6px 14px; border-radius: 20px; font-size: 13px; color: #ccc; border: 1px solid #3a4a5a; }}

.detail-section {{ background: #1a2736; border-radius: 12px; padding: 24px; border: 1px solid #2a3a4a; }}
.detail-section h3 {{ font-size: 16px; margin-bottom: 16px; color: #dde; }}
.filter-bar {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
.filter-btn {{ padding: 6px 16px; border-radius: 20px; border: 1px solid #3a4a5a; background: #2a3a4a; color: #aabbcc; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
.filter-btn:hover {{ background: #3a4a5a; }}
.filter-btn.active {{ background: #ffd700; color: #0f1923; border-color: #ffd700; font-weight: 600; }}

table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #0f1923; padding: 10px 12px; text-align: left; font-size: 13px; color: #8899aa; border-bottom: 2px solid #2a3a4a; position: sticky; top: 0; }}
td {{ padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #1f2f3f; }}
tr:hover td {{ background: #1f2f3f; }}
.table-wrapper {{ max-height: 500px; overflow-y: auto; border-radius: 8px; }}
.tag {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }}
.tag-best {{ background: rgba(255,215,0,0.15); color: #ffd700; }}
.tag-fun {{ background: rgba(255,107,157,0.15); color: #ff6b9d; }}
.tag-strong {{ background: rgba(0,212,255,0.15); color: #00d4ff; }}
.tag-none {{ background: rgba(153,153,153,0.15); color: #999; }}

.priority-note {{ background: #1a2736; border-radius: 12px; padding: 16px 24px; border: 1px solid #2a3a4a; margin-bottom: 32px; }}
.priority-note .title {{ font-size: 14px; color: #ffd700; font-weight: 600; margin-bottom: 8px; }}
.priority-note .desc {{ font-size: 13px; color: #8899aa; line-height: 1.6; }}
.priority-arrow {{ color: #ffd700; font-weight: 700; }}
</style>
</head>
<body>
<div class="container">
<h1>🎮 预选池推荐符文 — 标签覆盖分析</h1>
<p class="subtitle">以预选池 {total} 个推荐符文为分母，匹配最佳拍档 / 娱乐 / 强力单卡三个标签</p>

<div class="priority-note">
  <div class="title">📌 标签优先级规则</div>
  <div class="desc">当一个符文同时出现在多个标签页签中时，按以下优先级分配唯一标签：<br>
  <span class="priority-arrow">最佳拍档 &gt; 娱乐 &gt; 强力单卡</span><br>
  即：如果符文同时在"最佳拍档"和"强力单卡"中，则归为"最佳拍档"；如果只在"娱乐"和"强力单卡"中，则归为"娱乐"。</div>
</div>

<div class="summary-grid">
  <div class="stat-card best">
    <div class="stat-number">{stats[0]['count']}</div>
    <div class="stat-pct">{stats[0]['pct']}%</div>
    <div class="stat-label">最佳拍档</div>
  </div>
  <div class="stat-card fun">
    <div class="stat-number">{stats[1]['count']}</div>
    <div class="stat-pct">{stats[1]['pct']}%</div>
    <div class="stat-label">娱乐</div>
  </div>
  <div class="stat-card strong">
    <div class="stat-number">{stats[2]['count']}</div>
    <div class="stat-pct">{stats[2]['pct']}%</div>
    <div class="stat-label">强力单卡</div>
  </div>
  <div class="stat-card none">
    <div class="stat-number">{stats[3]['count']}</div>
    <div class="stat-pct">{stats[3]['pct']}%</div>
    <div class="stat-label">无标签</div>
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

<div class="no-label-section">
  <h3>⚠️ 无标签符文（{len(no_label_augs)} 个）— 不在任何标签页签中</h3>
  <div class="no-label-list">
    {no_label_html}
  </div>
</div>

<div class="detail-section">
  <h3>📋 全量符文明细（{total} 个）</h3>
  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all">全部 ({total})</button>
    <button class="filter-btn" data-filter="最佳拍档">最佳拍档 ({stats[0]['count']})</button>
    <button class="filter-btn" data-filter="娱乐">娱乐 ({stats[1]['count']})</button>
    <button class="filter-btn" data-filter="强力单卡">强力单卡 ({stats[2]['count']})</button>
    <button class="filter-btn" data-filter="无标签">无标签 ({stats[3]['count']})</button>
  </div>
  <div class="table-wrapper">
    <table id="detail-table">
      <thead><tr><th>#</th><th>符文名称</th><th>分配标签</th><th>所有匹配标签</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>
</div>

<script>
const data = {json.dumps(detail_data, ensure_ascii=False)};
const stats = {json.dumps(stats, ensure_ascii=False)};

// 饼图
Plotly.newPlot('pie-chart', [{{
  type: 'pie',
  labels: stats.map(s => s.label),
  values: stats.map(s => s.count),
  marker: {{ colors: ['#ffd700', '#ff6b9d', '#00d4ff', '#666'] }},
  textinfo: 'label+value+percent',
  textfont: {{ size: 13, color: '#fff' }},
  hole: 0.45,
  pull: [0, 0, 0, 0.05]
}}], {{
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{ t: 10, b: 10, l: 10, r: 10 }},
  height: 320,
  showlegend: false,
  annotations: [{{ text: '{total}<br>符文', showarrow: false, font: {{ size: 20, color: '#fff' }} }}]
}}, {{ responsive: true, displayModeBar: false }});

// 条形图
Plotly.newPlot('bar-chart', [{{
  type: 'bar',
  x: stats.map(s => s.label),
  y: stats.map(s => s.count),
  text: stats.map(s => s.count + ' (' + s.pct + '%)'),
  textposition: 'outside',
  textfont: {{ color: '#ccc', size: 13 }},
  marker: {{ color: ['#ffd700', '#ff6b9d', '#00d4ff', '#666'] }}
}}], {{
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{ t: 30, b: 40, l: 50, r: 20 }},
  height: 320,
  xaxis: {{ color: '#8899aa', gridcolor: '#1f2f3f' }},
  yaxis: {{ color: '#8899aa', gridcolor: '#1f2f3f', title: '符文数量' }}
}}, {{ responsive: true, displayModeBar: false }});

// 表格
const tagClass = {{'最佳拍档': 'tag-best', '娱乐': 'tag-fun', '强力单卡': 'tag-strong', '无标签': 'tag-none'}};
function renderTable(filter) {{
  const tbody = document.querySelector('#detail-table tbody');
  const filtered = filter === 'all' ? data : data.filter(d => d.label === filter);
  tbody.innerHTML = filtered.map((d, i) => 
    `<tr><td>${{i+1}}</td><td>${{d.augment}}</td><td><span class="tag ${{tagClass[d.label]}}">${{d.label}}</span></td><td>${{d.all_labels}}</td></tr>`
  ).join('');
}}
renderTable('all');

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.className = 'filter-btn');
    btn.classList.add('active');
    renderTable(btn.dataset.filter);
  }});
}});
</script>
</body>
</html>"""

output_path = '10_Work/海克斯大乱斗/data/augment_label_analysis.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'✅ 报告已生成: {output_path}')

# 打印摘要
print(f'\n{"="*50}')
print(f'预选池推荐符文: {total} 个')
print(f'{"─"*50}')
for s in stats:
    print(f'  {s["label"]}: {s["count"]} 个 ({s["pct"]}%)')
print(f'{"─"*50}')
print(f'无标签符文: {", ".join(no_label_augs)}')
