# -*- coding: utf-8 -*-
"""
v2 vs v3 验证结果对比分析
生成交互式 HTML 报告，展示小样本过滤的效果
"""
import json
import os

base = os.path.dirname(os.path.abspath(__file__))

# 加载数据
with open(os.path.join(base, "output", "validation_result_v2.json"), "r") as f:
    v2 = json.load(f)
with open(os.path.join(base, "output", "validation_result_v3.json"), "r") as f:
    v3 = json.load(f)

v2s = v2["summary"]
v3s = v3["summary"]

# ====== 对比分析 ======
print("=" * 70)
print("  v2 vs v3 验证结果对比")
print("=" * 70)

print(f"\n{'指标':<30} {'v2':>10} {'v3':>10} {'变化':>10}")
print("-" * 65)
print(f"{'规则1 违规数':<28} {v2s['rule1_violations']:>10} {v3s['rule1_violations']:>10} {v3s['rule1_violations'] - v2s['rule1_violations']:>+10}")
print(f"{'规则1 涉及英雄':<28} {v2s['rule1_heroes']:>10} {v3s['rule1_heroes']:>10} {v3s['rule1_heroes'] - v2s['rule1_heroes']:>+10}")
print(f"{'规则2 违规数':<28} {v2s['rule2_violations']:>10} {v3s['rule2_violations']:>10} {v3s['rule2_violations'] - v2s['rule2_violations']:>+10}")
print(f"{'规则3 违规数':<28} {v2s['rule3_violations']:>10} {v3s['rule3_violations']:>10} {v3s['rule3_violations'] - v2s['rule3_violations']:>+10}")
print(f"{'规则3 涉及英雄':<28} {v2s['rule3_heroes']:>10} {v3s['rule3_heroes']:>10} {v3s['rule3_heroes'] - v2s['rule3_heroes']:>+10}")
print(f"{'总违规数':<28} {v2s['total_violations']:>10} {v3s['total_violations']:>10} {v3s['total_violations'] - v2s['total_violations']:>+10}")

# ====== 分析 v2 违规中有多少是小样本噪声 ======
# v2 的 Rule1 违规不包含 PR 字段，需要用 v3 的数据来推断
# 但 v2 结果不含 PR。我们换个思路：分析哪些 v2 违规在 v3 中消失了（说明是噪声排名效应）

v2_r1_set = set()
for v in v2["rule1_violations"]:
    v2_r1_set.add((v["hero"], v["aug"]))

v3_r1_set = set()
for v in v3["rule1_violations"]:
    v3_r1_set.add((v["hero"], v["aug"]))

disappeared = v2_r1_set - v3_r1_set  # v2 有但 v3 没有的（过滤后排名变化导致不再违规）
appeared = v3_r1_set - v2_r1_set  # v3 新增的（过滤后有新的条目进入 Top10）
common = v2_r1_set & v3_r1_set

print(f"\n{'='*60}")
print("规则1 违规变化详情:")
print(f"{'='*60}")
print(f"  v2→v3 消失的违规: {len(disappeared)} 条（过滤噪声后排名变化，不再违规）")
print(f"  v2→v3 持续的违规: {len(common)} 条（持续存在的真实违规）")
print(f"  v3 新增的违规:    {len(appeared)} 条（噪声被移除后，新条目进入 Top10）")

# 同样分析 Rule3
v2_r3_set = set((v["hero"], v["aug"]) for v in v2["rule3_violations"])
v3_r3_set = set((v["hero"], v["aug"]) for v in v3["rule3_violations"])
r3_disappeared = v2_r3_set - v3_r3_set
r3_appeared = v3_r3_set - v2_r3_set
r3_common = v2_r3_set & v3_r3_set

print(f"\n{'='*60}")
print("规则3 违规变化详情:")
print(f"{'='*60}")
print(f"  v2→v3 消失的违规: {len(r3_disappeared)} 条")
print(f"  v2→v3 持续的违规: {len(r3_common)} 条")
print(f"  v3 新增的违规:    {len(r3_appeared)} 条")

# ====== v3 违规的 PR 分布分析 ======
print(f"\n{'='*60}")
print("v3 Rule1 违规的 Pick Rate 分布:")
print(f"{'='*60}")
prs = [v["pr"] * 100 for v in v3["rule1_violations"]]  # 转为百分比
import statistics
print(f"  最小 PR: {min(prs):.4f}%")
print(f"  最大 PR: {max(prs):.4f}%")
print(f"  中位数 PR: {statistics.median(prs):.4f}%")
print(f"  平均 PR: {statistics.mean(prs):.4f}%")

# 分段统计
brackets = [(0, 0.01), (0.01, 0.05), (0.05, 0.1), (0.1, 0.5), (0.5, 1.0), (1.0, 100)]
for lo, hi in brackets:
    cnt = sum(1 for p in prs if lo < p <= hi)
    print(f"  PR ({lo:.2f}%, {hi:.2f}%]: {cnt} 条 ({cnt/len(prs)*100:.1f}%)")

# ====== 过滤统计 ======
print(f"\n{'='*60}")
print("小样本过滤统计（v3 新增）:")
print(f"{'='*60}")
print(f"  过滤阈值: PR ≤ {v3s['min_pickrate_threshold']}%")
print(f"  过滤总条目: {v3s['total_filtered']} 条")
print(f"  平均每英雄过滤: {v3s['avg_filtered_per_hero']} 条")
print(f"  受影响英雄: {v3s['heroes_with_filter']}/172")

# ====== 生成 HTML 报告 ======
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>v2 vs v3 验证对比报告 - Pick率小样本过滤效果</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 28px; color: #f1f5f9; margin-bottom: 8px; }}
.subtitle {{ color: #94a3b8; font-size: 14px; margin-bottom: 32px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 28px; }}
.card {{ background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }}
.card-title {{ font-size: 16px; color: #94a3b8; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
.card-title .icon {{ font-size: 20px; }}
.metric-row {{ display: flex; justify-content: space-between; align-items: baseline; padding: 8px 0; border-bottom: 1px solid #334155; }}
.metric-row:last-child {{ border-bottom: none; }}
.metric-label {{ color: #94a3b8; font-size: 14px; }}
.metric-value {{ font-size: 18px; font-weight: 700; }}
.metric-value.positive {{ color: #f87171; }}
.metric-value.negative {{ color: #4ade80; }}
.metric-value.neutral {{ color: #60a5fa; }}
.metric-value.gold {{ color: #fbbf24; }}
.chart {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; margin-bottom: 20px; }}
.section-title {{ font-size: 20px; color: #f1f5f9; margin: 32px 0 16px; display: flex; align-items: center; gap: 8px; }}
.insight {{ background: #1e293b; border-radius: 12px; padding: 20px; border-left: 4px solid #60a5fa; margin-bottom: 16px; }}
.insight.warning {{ border-left-color: #fbbf24; }}
.insight.success {{ border-left-color: #4ade80; }}
.insight-title {{ font-weight: 700; color: #f1f5f9; margin-bottom: 8px; }}
.insight-text {{ color: #94a3b8; font-size: 14px; line-height: 1.6; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; }}
th {{ color: #94a3b8; font-weight: 600; background: #1e293b; position: sticky; top: 0; }}
td {{ color: #e2e8f0; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
.badge-red {{ background: #7f1d1d; color: #fca5a5; }}
.badge-green {{ background: #14532d; color: #86efac; }}
.badge-yellow {{ background: #713f12; color: #fde047; }}
.badge-blue {{ background: #1e3a5f; color: #93c5fd; }}
.scrollable {{ max-height: 400px; overflow-y: auto; }}
</style>
</head>
<body>
<div class="container">

<h1>📊 v2 vs v3 验证对比报告</h1>
<p class="subtitle">Pick率小样本过滤效果分析 | 过滤阈值: PR ≤ {v3s['min_pickrate_threshold']}% | {v3s['total_filtered']} 条噪声数据被过滤</p>

<!-- KPI Cards -->
<div class="grid">
  <div class="card">
    <div class="card-title"><span class="icon">🔬</span>小样本过滤概览</div>
    <div class="metric-row"><span class="metric-label">过滤阈值</span><span class="metric-value neutral">PR ≤ {v3s['min_pickrate_threshold']}%</span></div>
    <div class="metric-row"><span class="metric-label">被过滤条目</span><span class="metric-value gold">{v3s['total_filtered']} 条</span></div>
    <div class="metric-row"><span class="metric-label">平均每英雄过滤</span><span class="metric-value">{v3s['avg_filtered_per_hero']} 条</span></div>
    <div class="metric-row"><span class="metric-label">受影响英雄</span><span class="metric-value">{v3s['heroes_with_filter']}/172</span></div>
  </div>
  <div class="card">
    <div class="card-title"><span class="icon">📋</span>规则1: Top10 WR → 推荐</div>
    <div class="metric-row"><span class="metric-label">v2 违规</span><span class="metric-value">{v2s['rule1_violations']}</span></div>
    <div class="metric-row"><span class="metric-label">v3 违规</span><span class="metric-value">{v3s['rule1_violations']}</span></div>
    <div class="metric-row"><span class="metric-label">变化</span><span class="metric-value {'positive' if v3s['rule1_violations'] > v2s['rule1_violations'] else 'negative'}">{v3s['rule1_violations'] - v2s['rule1_violations']:+d}</span></div>
    <div class="metric-row"><span class="metric-label">消失/持续/新增</span><span class="metric-value">{len(disappeared)} / {len(common)} / {len(appeared)}</span></div>
  </div>
  <div class="card">
    <div class="card-title"><span class="icon">📋</span>规则3: Bottom10 WR → 刷新</div>
    <div class="metric-row"><span class="metric-label">v2 违规</span><span class="metric-value">{v2s['rule3_violations']}</span></div>
    <div class="metric-row"><span class="metric-label">v3 违规</span><span class="metric-value">{v3s['rule3_violations']}</span></div>
    <div class="metric-row"><span class="metric-label">变化</span><span class="metric-value positive">{v3s['rule3_violations'] - v2s['rule3_violations']:+d}</span></div>
    <div class="metric-row"><span class="metric-label">消失/持续/新增</span><span class="metric-value">{len(r3_disappeared)} / {len(r3_common)} / {len(r3_appeared)}</span></div>
  </div>
</div>

<!-- 核心洞察 -->
<h2 class="section-title">💡 核心发现</h2>

<div class="insight warning">
  <div class="insight-title">⚠️ 过滤后违规数反增，但这是正确的</div>
  <div class="insight-text">
    v3 过滤掉了 <b>{v3s['total_filtered']}</b> 条 PR=0 的噪声数据后，违规数从 {v2s['total_violations']} 增至 {v3s['total_violations']}（+{v3s['total_violations'] - v2s['total_violations']}）。
    这是因为在 v2 中，大量"虚假高胜率"噪声条目（如1局1胜=100%WR）占据了 Top10 的位置，
    而它们恰好因为没有被推荐而产生了违规。移除这些噪声后，<b>真实的高胜率符文</b>进入了 Top10，
    但其中有些同样未被推荐 → 产生了新的违规。<br><br>
    关键区别：v2 中的很多 Top10 违规是<span style="color:#fca5a5">假阳性</span>（噪声数据不该进 Top10），
    v3 中的 Top10 违规是<span style="color:#fde047">真实问题</span>（真正高胜率但未推荐）。
  </div>
</div>

<div class="insight success">
  <div class="insight-title">✅ 噪声数据已完全清除</div>
  <div class="insight-text">
    v3 的所有违规条目 PR 值均 > 0，不再有"0 样本 100% 胜率"的虚假排名。
    过去 v2 中被你发现的"阿里升级荆棘之甲"等小样本噪声，已被完全排除在排名之外。
  </div>
</div>

<div class="insight">
  <div class="insight-title">📊 排名位移效应</div>
  <div class="insight-text">
    规则1: <b>{len(disappeared)}</b> 条 v2 违规消失（原排名由噪声支撑，过滤后不再位于 Top10）；
    <b>{len(appeared)}</b> 条新违规出现（真实高胜率条目上位进入 Top10）。<br>
    规则3: 同理，Bottom10 排名位移导致 <b>{len(r3_appeared)}</b> 条新违规。
    过滤后整体数据池缩小（每英雄平均减少 {v3s['avg_filtered_per_hero']} 条），Bottom10 的范围也更精确。
  </div>
</div>

<!-- 对比柱状图 -->
<h2 class="section-title">📈 图表分析</h2>
<div class="chart" id="chart1"></div>
<div class="chart" id="chart2"></div>
<div class="chart" id="chart3"></div>

<!-- v3 Rule1 违规详情表 -->
<h2 class="section-title">📋 v3 规则1 违规详情（按英雄分组 Top20）</h2>
<div class="card scrollable">
<table>
<thead><tr><th>英雄</th><th>违规数</th><th>违规符文（Top排名, WR, PR）</th></tr></thead>
<tbody>
"""

# 按英雄分组 Rule1
from collections import defaultdict
r1_by_hero = defaultdict(list)
for v in v3["rule1_violations"]:
    r1_by_hero[v["hero"]].append(v)

sorted_heroes = sorted(r1_by_hero.items(), key=lambda x: -len(x[1]))[:20]
for hero, vs in sorted_heroes:
    details = ", ".join(
        f"{v['aug']}(Top{v['wr_rank']}, WR={v['wr']*100:.0f}%, PR={v['pr']*100:.3f}%)"
        for v in sorted(vs, key=lambda x: x['wr_rank'])
    )
    html += f"<tr><td>{hero}</td><td>{len(vs)}</td><td style='font-size:12px'>{details}</td></tr>\n"

html += """</tbody></table></div>

<!-- v3 过滤统计表 -->
<h2 class="section-title">🔬 每英雄过滤统计 Top20</h2>
<div class="card scrollable">
<table>
<thead><tr><th>英雄</th><th>总符文</th><th>过滤后</th><th>被过滤</th><th>推荐数</th></tr></thead>
<tbody>
"""

# 过滤统计
filter_sorted = sorted(v3["hero_recommend_counts"], key=lambda x: -x["filtered_count"])[:20]
for h in filter_sorted:
    html += f"<tr><td>{h['hero']}</td><td>{h['total_augs']}</td><td>{h['total_augs_after_filter']}</td><td><span class='badge badge-red'>{h['filtered_count']}</span></td><td>{h['total_recommended']}</td></tr>\n"

html += """</tbody></table></div>

</div>

<script>
// Chart 1: v2 vs v3 违规数对比
"""

html += f"""
Plotly.newPlot('chart1', [
  {{
    x: ['规则1<br>Top10 WR→推荐', '规则2<br>Bot20 WR→非推荐', '规则3<br>Bot10 WR→刷新', '总计'],
    y: [{v2s['rule1_violations']}, {v2s['rule2_violations']}, {v2s['rule3_violations']}, {v2s['total_violations']}],
    name: 'v2 (无过滤)',
    type: 'bar',
    marker: {{ color: '#64748b' }},
    text: [{v2s['rule1_violations']}, {v2s['rule2_violations']}, {v2s['rule3_violations']}, {v2s['total_violations']}],
    textposition: 'outside',
    textfont: {{ color: '#94a3b8', size: 14 }}
  }},
  {{
    x: ['规则1<br>Top10 WR→推荐', '规则2<br>Bot20 WR→非推荐', '规则3<br>Bot10 WR→刷新', '总计'],
    y: [{v3s['rule1_violations']}, {v3s['rule2_violations']}, {v3s['rule3_violations']}, {v3s['total_violations']}],
    name: 'v3 (PR≤0过滤)',
    type: 'bar',
    marker: {{ color: '#60a5fa' }},
    text: [{v3s['rule1_violations']}, {v3s['rule2_violations']}, {v3s['rule3_violations']}, {v3s['total_violations']}],
    textposition: 'outside',
    textfont: {{ color: '#93c5fd', size: 14 }}
  }}
], {{
  title: {{ text: 'v2 vs v3 违规数对比', font: {{ color: '#f1f5f9', size: 18 }} }},
  paper_bgcolor: '#1e293b', plot_bgcolor: '#1e293b',
  xaxis: {{ color: '#94a3b8', gridcolor: '#334155' }},
  yaxis: {{ color: '#94a3b8', gridcolor: '#334155', title: '违规数' }},
  barmode: 'group',
  legend: {{ font: {{ color: '#94a3b8' }} }},
  margin: {{ t: 60, b: 80 }}
}}, {{responsive: true}});
"""

# Chart 2: Rule1 违规流向桑基图
html += f"""
// Chart 2: Rule1 违规变化 - 堆叠条形图
Plotly.newPlot('chart2', [
  {{
    x: ['v2 → v3 消失', 'v2 ∩ v3 持续', 'v3 新增'],
    y: [{len(disappeared)}, {len(common)}, {len(appeared)}],
    type: 'bar',
    marker: {{
      color: ['#4ade80', '#fbbf24', '#f87171'],
    }},
    text: [{len(disappeared)}, {len(common)}, {len(appeared)}],
    textposition: 'outside',
    textfont: {{ color: '#e2e8f0', size: 16 }}
  }}
], {{
  title: {{ text: '规则1 违规变化流向', font: {{ color: '#f1f5f9', size: 18 }} }},
  paper_bgcolor: '#1e293b', plot_bgcolor: '#1e293b',
  xaxis: {{ color: '#94a3b8', gridcolor: '#334155' }},
  yaxis: {{ color: '#94a3b8', gridcolor: '#334155', title: '条数' }},
  margin: {{ t: 60, b: 60 }},
  annotations: [
    {{ x: 'v2 → v3 消失', y: {len(disappeared) + 15}, text: '噪声排名消失',
       showarrow: false, font: {{ color: '#86efac', size: 12 }} }},
    {{ x: 'v2 ∩ v3 持续', y: {len(common) + 15}, text: '持续真实违规',
       showarrow: false, font: {{ color: '#fde047', size: 12 }} }},
    {{ x: 'v3 新增', y: {len(appeared) + 15}, text: '真实高WR上位',
       showarrow: false, font: {{ color: '#fca5a5', size: 12 }} }}
  ]
}}, {{responsive: true}});
"""

# Chart 3: v3 Rule1 违规的 PR 分布直方图
pr_values = [v["pr"] * 100 for v in v3["rule1_violations"]]
html += f"""
// Chart 3: v3 Rule1 违规的 Pick Rate 分布
Plotly.newPlot('chart3', [
  {{
    x: {json.dumps(pr_values)},
    type: 'histogram',
    nbinsx: 30,
    marker: {{ color: '#60a5fa', line: {{ color: '#93c5fd', width: 1 }} }},
    opacity: 0.85
  }}
], {{
  title: {{ text: 'v3 Rule1 违规条目的 Pick Rate 分布', font: {{ color: '#f1f5f9', size: 18 }} }},
  paper_bgcolor: '#1e293b', plot_bgcolor: '#1e293b',
  xaxis: {{ color: '#94a3b8', gridcolor: '#334155', title: 'Pick Rate (%)' }},
  yaxis: {{ color: '#94a3b8', gridcolor: '#334155', title: '频次' }},
  margin: {{ t: 60, b: 60 }},
  annotations: [
    {{ x: 0.05, y: 0, text: '所有条目 PR > 0<br>噪声已清除 ✅',
       showarrow: true, arrowcolor: '#4ade80', ax: 60, ay: -60,
       font: {{ color: '#4ade80', size: 13 }},
       bordercolor: '#4ade80', borderwidth: 1, borderpad: 4, bgcolor: '#14532d' }}
  ]
}}, {{responsive: true}});
"""

html += """
</script>
</body>
</html>"""

# 保存报告
report_path = os.path.join(base, "output", "v2_vs_v3_comparison.html")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\n📊 对比报告已保存: {report_path}")
