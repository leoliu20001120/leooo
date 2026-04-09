import pandas as pd
import numpy as np
import json

# 读取过滤结果
df = pd.read_csv('/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗/data/s_tier_filtered_augments.csv')
df_opgg = pd.read_csv('/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗/lol_opgg_kiwi_augment_data.csv', sep='\t')
df_s = df_opgg[df_opgg['tier_label'] == 'S']

# 计算统计数据
per_champ_before = df_s.groupby('champion_name').size()
per_champ_after = df.groupby('champion_name').size()

champ_retention = pd.DataFrame({
    'before': per_champ_before,
    'after': per_champ_after
}).fillna(0)
champ_retention['rate'] = champ_retention['after'] / champ_retention['before'] * 100

reason_counts = df['filter_reason'].value_counts()
after_dist = per_champ_after.value_counts().sort_index()

# 生成 HTML 报告
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S级符文过滤报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1923; color: #c8aa6e; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
        .header {{ text-align: center; margin-bottom: 32px; padding: 24px; background: linear-gradient(135deg, #1a2332 0%, #0a1628 100%); border: 1px solid #c8aa6e33; border-radius: 12px; }}
        .header h1 {{ font-size: 28px; color: #c8aa6e; margin-bottom: 8px; }}
        .header p {{ color: #8a8a8a; font-size: 14px; }}
        .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
        .kpi {{ background: linear-gradient(135deg, #1a2332 0%, #0d1b2a 100%); border: 1px solid #c8aa6e33; border-radius: 10px; padding: 20px; text-align: center; }}
        .kpi .value {{ font-size: 36px; font-weight: 700; color: #f0e6d2; }}
        .kpi .label {{ font-size: 13px; color: #8a8a8a; margin-top: 4px; }}
        .kpi .sub {{ font-size: 12px; color: #5b5a56; margin-top: 2px; }}
        .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .chart-card {{ background: #1a2332; border: 1px solid #c8aa6e22; border-radius: 10px; padding: 20px; }}
        .chart-card h3 {{ color: #c8aa6e; font-size: 16px; margin-bottom: 16px; }}
        .chart-card canvas {{ max-height: 300px; }}
        .full-width {{ grid-column: 1 / -1; }}
        .table-section {{ background: #1a2332; border: 1px solid #c8aa6e22; border-radius: 10px; padding: 20px; margin-bottom: 24px; }}
        .table-section h3 {{ color: #c8aa6e; font-size: 16px; margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ background: #0d1b2a; color: #c8aa6e; padding: 10px 12px; text-align: left; border-bottom: 2px solid #c8aa6e33; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #1e2d3d; color: #a09b8c; }}
        tr:hover td {{ background: #1e2d3d; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
        .badge-dual {{ background: #c8aa6e22; color: #c8aa6e; }}
        .badge-top7 {{ background: #0397ab22; color: #0397ab; }}
        .badge-both {{ background: #c89b3c22; color: #c89b3c; }}
        .filter-section {{ margin-bottom: 16px; }}
        .filter-section select {{ background: #0d1b2a; color: #c8aa6e; border: 1px solid #c8aa6e44; padding: 8px 12px; border-radius: 6px; font-size: 14px; min-width: 200px; }}
        .filter-section label {{ color: #8a8a8a; margin-right: 8px; font-size: 13px; }}
        .method-box {{ background: #0d1b2a; border: 1px solid #c8aa6e22; border-radius: 8px; padding: 16px; margin-bottom: 20px; font-size: 13px; line-height: 1.8; color: #a09b8c; }}
        .method-box strong {{ color: #c8aa6e; }}
        .method-box .hl {{ color: #0397ab; font-weight: 600; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>⚔️ S级英雄符文过滤报告</h1>
        <p>基于 OPGG 推荐数据 + champion_augment_stats 胜率/Pick率 二次筛选</p>
    </div>
    <div class="method-box">
        <strong>📋 过滤规则说明</strong><br>
        在每个英雄的 S 级符文中，保留满足以下 <span class="hl">任一</span> 条件的符文：<br>
        <strong>条件A (双30%)</strong>：同时处于该英雄 Top 30% 的 Pick率 <em>且</em> Top 30% 的胜率<br>
        <strong>条件B (Top7 绿通)</strong>：该英雄 Pick率排名 Top 7 的符文直接保留<br>
        <em>注：胜率和 Pick率 来自 step1_2_champion_augment_stats 表</em>
    </div>
    <div class="kpi-row">
        <div class="kpi">
            <div class="value">{len(df_s)}</div>
            <div class="label">过滤前 S级符文</div>
            <div class="sub">172 英雄</div>
        </div>
        <div class="kpi">
            <div class="value">{len(df)}</div>
            <div class="label">过滤后保留</div>
            <div class="sub">{len(df)/len(df_s)*100:.1f}% 保留率</div>
        </div>
        <div class="kpi">
            <div class="value">{len(df_s) - len(df)}</div>
            <div class="label">淘汰符文数</div>
            <div class="sub">{(len(df_s)-len(df))/len(df_s)*100:.1f}% 淘汰率</div>
        </div>
        <div class="kpi">
            <div class="value">{per_champ_after.median():.0f}</div>
            <div class="label">每英雄中位数</div>
            <div class="sub">范围 {per_champ_after.min()}-{per_champ_after.max()}</div>
        </div>
    </div>
    <div class="charts-grid">
        <div class="chart-card">
            <h3>📊 保留原因分布</h3>
            <canvas id="reasonChart"></canvas>
        </div>
        <div class="chart-card">
            <h3>📊 每英雄保留符文数分布</h3>
            <canvas id="distChart"></canvas>
        </div>
        <div class="chart-card full-width">
            <h3>📊 各英雄过滤前后对比（按保留率排序）</h3>
            <canvas id="champChart" style="max-height: 400px;"></canvas>
        </div>
    </div>
    <div class="table-section">
        <h3>🔍 英雄符文明细（选择英雄查看）</h3>
        <div class="filter-section">
            <label for="champSelect">选择英雄：</label>
            <select id="champSelect" onchange="updateTable()"></select>
        </div>
        <table id="detailTable">
            <thead>
                <tr><th>#</th><th>符文名</th><th>稀有度</th><th>Performance</th><th>Popular</th><th>胜率</th><th>Pick率</th><th>Pick排名</th><th>保留原因</th></tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
</div>
<script>
const cc = {{ gold: '#c8aa6e', blue: '#0397ab', red: '#c8443c', green: '#1ebd61', dark: '#0d1b2a', text: '#a09b8c' }};

new Chart(document.getElementById('reasonChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(reason_counts.index.tolist())},
        datasets: [{{ data: {json.dumps(reason_counts.values.tolist())}, backgroundColor: ['#0397ab', '#c8aa6e', '#c8443c'], borderColor: '#1a2332', borderWidth: 2 }}]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: cc.text }} }} }} }}
}});

new Chart(document.getElementById('distChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(after_dist.index.tolist())},
        datasets: [{{ label: '英雄数', data: {json.dumps(after_dist.values.tolist())}, backgroundColor: '#c8aa6e88', borderColor: '#c8aa6e', borderWidth: 1 }}]
    }},
    options: {{
        responsive: true,
        scales: {{
            x: {{ title: {{ display: true, text: '保留符文数', color: cc.text }}, ticks: {{ color: cc.text }}, grid: {{ color: '#1e2d3d' }} }},
            y: {{ title: {{ display: true, text: '英雄数量', color: cc.text }}, ticks: {{ color: cc.text }}, grid: {{ color: '#1e2d3d' }} }}
        }},
        plugins: {{ legend: {{ display: false }} }}
    }}
}});

const champData = {json.dumps(champ_retention.sort_values('rate').reset_index().rename(columns={'index': 'champion_name'}).to_dict(orient='records'))};
new Chart(document.getElementById('champChart'), {{
    type: 'bar',
    data: {{
        labels: champData.map(d => d.champion_name),
        datasets: [
            {{ label: '过滤前', data: champData.map(d => d.before), backgroundColor: '#c8aa6e44', borderColor: '#c8aa6e', borderWidth: 1 }},
            {{ label: '过滤后', data: champData.map(d => d.after), backgroundColor: '#0397ab88', borderColor: '#0397ab', borderWidth: 1 }}
        ]
    }},
    options: {{
        responsive: true,
        scales: {{
            x: {{ ticks: {{ display: false }}, grid: {{ color: '#1e2d3d' }} }},
            y: {{ ticks: {{ color: cc.text }}, grid: {{ color: '#1e2d3d' }} }}
        }},
        plugins: {{ legend: {{ labels: {{ color: cc.text }} }} }}
    }}
}});

const allData = {df.to_json(orient='records', force_ascii=False)};
const champSet = [...new Set(allData.map(d => d.champion_name))].sort();
const sel = document.getElementById('champSelect');
champSet.forEach(c => {{ const o = document.createElement('option'); o.value = c; o.textContent = c; sel.appendChild(o); }});

function updateTable() {{
    const champ = sel.value;
    const rows = allData.filter(d => d.champion_name === champ).sort((a,b) => a.pick_rank - b.pick_rank);
    const tbody = document.querySelector('#detailTable tbody');
    tbody.innerHTML = '';
    rows.forEach((r, i) => {{
        const bc = r.filter_reason.includes('+') ? 'badge-both' : r.filter_reason.includes('Top7') ? 'badge-top7' : 'badge-dual';
        tbody.innerHTML += `<tr><td>${{i+1}}</td><td style="color:#f0e6d2">${{r.augment_name}}</td><td>${{r.rarity_label}}</td><td>${{r.performance.toFixed(2)}}</td><td>${{r.popular.toFixed(2)}}</td><td>${{(r.win_rate*100).toFixed(1)}}%</td><td>${{(r.show_rate*100).toFixed(3)}}%</td><td>${{r.pick_rank}}</td><td><span class="badge ${{bc}}">${{r.filter_reason}}</span></td></tr>`;
    }});
}}
updateTable();
</script>
</body>
</html>"""

output_path = '/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗/data/s_tier_filter_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"报告已生成: {output_path}")
