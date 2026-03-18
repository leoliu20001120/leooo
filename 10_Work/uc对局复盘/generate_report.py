#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《异人之下》NPC王也 AI对话上线效果分析报告
输出格式: HTML
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import jieba
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from wordcloud import WordCloud
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 0. 全局配置
# ============================================================
CSV_PATH = '对话详情.csv'
OUTPUT_HTML = '上线效果分析报告.html'

# 中文字体配置
def get_chinese_font():
    """获取系统中可用的中文字体"""
    font_candidates = [
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
        '/System/Library/Fonts/STHeiti Light.ttc',
    ]
    for fp in font_candidates:
        import os
        if os.path.exists(fp):
            return fp
    return None

FONT_PATH = get_chinese_font()
if FONT_PATH:
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 读取与预处理
# ============================================================
df = pd.read_csv(CSV_PATH)
df['用户对话时间'] = pd.to_datetime(df['用户对话时间'])
df['NPC回答时间'] = pd.to_datetime(df['NPC回答时间'])
df['日期'] = df['用户对话时间'].dt.date
df['小时'] = df['用户对话时间'].dt.hour
df['响应耗时(秒)'] = (df['NPC回答时间'] - df['用户对话时间']).dt.total_seconds()

# ============================================================
# 辅助函数: 图表 → base64
# ============================================================
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=130, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return b64

# ============================================================
# 2. 核心指标
# ============================================================
total_conversations = len(df)
unique_users = df['用户ID'].nunique()
date_range_start = df['用户对话时间'].min().strftime('%Y-%m-%d %H:%M')
date_range_end = df['用户对话时间'].max().strftime('%Y-%m-%d %H:%M')
num_days = df['日期'].nunique()
avg_daily = total_conversations / num_days

user_turns = df.groupby('用户ID').size()
avg_turns = user_turns.mean()
median_turns = user_turns.median()
max_turns = user_turns.max()

normal_reply = len(df[df['回复类型'] == '常规回复'])
refuse_reply = len(df[df['回复类型'] == '拒答回复'])
refuse_rate = refuse_reply / total_conversations * 100

avg_response_time = df['响应耗时(秒)'].mean()
median_response_time = df['响应耗时(秒)'].median()

# ============================================================
# 3. 图表生成
# ============================================================
charts = {}

# 3.1 每日对话量趋势
daily_counts = df.groupby('日期').size()
fig, ax = plt.subplots(figsize=(8, 4))
dates = [str(d) for d in daily_counts.index]
values = daily_counts.values
bars = ax.bar(dates, values, color='#4A90D9', width=0.5, edgecolor='white')
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
            str(val), ha='center', va='bottom', fontsize=12, fontweight='bold')
ax.set_title('每日对话量趋势', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('日期')
ax.set_ylabel('对话数')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(values)*1.2)
fig.tight_layout()
charts['daily_trend'] = fig_to_base64(fig)

# 3.2 每小时对话分布
hourly_counts = df.groupby('小时').size().reindex(range(24), fill_value=0)
fig, ax = plt.subplots(figsize=(10, 4))
ax.fill_between(hourly_counts.index, hourly_counts.values, alpha=0.3, color='#4A90D9')
ax.plot(hourly_counts.index, hourly_counts.values, 'o-', color='#4A90D9', markersize=5, linewidth=2)
ax.set_title('24小时对话分布', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('小时')
ax.set_ylabel('对话数')
ax.set_xticks(range(24))
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
charts['hourly_dist'] = fig_to_base64(fig)

# 3.3 用户对话轮次分布
bins = [0, 1, 3, 5, 10, 20, 50, 100, 300]
labels = ['1轮', '2-3轮', '4-5轮', '6-10轮', '11-20轮', '21-50轮', '51-100轮', '100+轮']
user_turns_binned = pd.cut(user_turns, bins=bins, labels=labels)
turn_dist = user_turns_binned.value_counts().sort_index()

fig, ax = plt.subplots(figsize=(8, 4))
colors_gradient = ['#E8F0FE', '#C5DAF5', '#A1C4ED', '#7DAEE4', '#5998DB', '#4A90D9', '#3B7BC8', '#2C66B7']
bars = ax.bar(range(len(turn_dist)), turn_dist.values, color=colors_gradient, edgecolor='white')
ax.set_xticks(range(len(turn_dist)))
ax.set_xticklabels(turn_dist.index, rotation=30, ha='right')
for bar, val in zip(bars, turn_dist.values):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_title('用户对话轮次分布（用户数）', fontsize=14, fontweight='bold', pad=15)
ax.set_ylabel('用户数')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
charts['turn_dist'] = fig_to_base64(fig)

# 3.4 回复类型分布饼图
fig, ax = plt.subplots(figsize=(5, 5))
sizes = [normal_reply, refuse_reply]
labels_pie = [f'常规回复\n{normal_reply}条', f'拒答回复\n{refuse_reply}条']
colors_pie = ['#4A90D9', '#E74C3C']
wedges, texts, autotexts = ax.pie(sizes, labels=labels_pie, colors=colors_pie,
                                   autopct='%1.1f%%', startangle=90,
                                   textprops={'fontsize': 12})
ax.set_title('回复类型分布', fontsize=14, fontweight='bold', pad=15)
fig.tight_layout()
charts['reply_type'] = fig_to_base64(fig)

# 3.5 响应时间分布
fig, ax = plt.subplots(figsize=(8, 4))
response_times = df['响应耗时(秒)'].dropna()
response_times_clipped = response_times[response_times <= 20]
ax.hist(response_times_clipped, bins=40, color='#4A90D9', edgecolor='white', alpha=0.8)
ax.axvline(x=avg_response_time, color='#E74C3C', linestyle='--', linewidth=2, label=f'均值 {avg_response_time:.1f}s')
ax.axvline(x=median_response_time, color='#F39C12', linestyle='--', linewidth=2, label=f'中位数 {median_response_time:.1f}s')
ax.set_title('NPC响应时间分布', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('响应时间（秒）')
ax.set_ylabel('对话数')
ax.legend(fontsize=10)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
charts['response_time'] = fig_to_base64(fig)

# 3.6 用户跨天留存
user_dates = df.groupby('用户ID')['日期'].apply(lambda x: sorted(x.unique()))
user_day_count = user_dates.apply(len)
retention_dist = user_day_count.value_counts().sort_index()

fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar([f'{d}天' for d in retention_dist.index], retention_dist.values,
              color=['#4A90D9', '#3B7BC8', '#2C66B7', '#1D51A6'], edgecolor='white')
for bar, val in zip(bars, retention_dist.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{val}人\n({val/unique_users*100:.1f}%)', ha='center', va='bottom', fontsize=10)
ax.set_title('用户跨天活跃天数分布', fontsize=14, fontweight='bold', pad=15)
ax.set_ylabel('用户数')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(retention_dist.values)*1.35)
fig.tight_layout()
charts['retention'] = fig_to_base64(fig)

# ============================================================
# 4. 词云
# ============================================================
stopwords = set([
    '的', '了', '是', '我', '你', '吗', '啊', '吧', '呢', '嗯', '哦', '哈',
    '在', '有', '和', '也', '不', '就', '都', '还', '要', '会', '能', '可以',
    '什么', '怎么', '这', '那', '一个', '一下', '好', '没', '没有', '到',
    '说', '去', '来', '上', '下', '里', '中', '大', '小', '多', '少',
    '很', '太', '真', '可', '把', '被', '让', '给', '从', '为', '对',
    '个', '们', '他', '她', '它', '这个', '那个', '哪', '谁', '怎么样',
    '怎样', '如何', '为什么', '因为', '所以', '但是', '可是', '不过',
    '而且', '或者', '如果', '虽然', '已经', '正在', '一直', '一起',
    '一样', '知道', '觉得', '应该', '可能', '一定', '当然', '其实',
    '只是', '就是', '还是', '比较', '特别', '非常', '最', '更', '过',
    '想', '看', '做', '啦', '呀', '嘛', '哈哈', '哈哈哈', '哈哈哈哈',
    '嘿', '喂', '唉', '嗷', '嘻', '呵', '噢', '咋', '咧', '哇',
    'nil', '校验错误', '时候', '什么时候',
])

user_texts = ' '.join(df['用户对话'].dropna().astype(str).tolist())
words = jieba.lcut(user_texts)
words_filtered = [w for w in words if len(w) >= 2 and w not in stopwords]
word_freq = Counter(words_filtered)

wc = WordCloud(
    font_path=FONT_PATH,
    width=900,
    height=450,
    background_color='white',
    max_words=120,
    max_font_size=100,
    min_font_size=12,
    colormap='Blues',
    prefer_horizontal=0.7,
    margin=5,
)
wc.generate_from_frequencies(word_freq)

fig, ax = plt.subplots(figsize=(12, 6))
ax.imshow(wc, interpolation='bilinear')
ax.axis('off')
ax.set_title('用户对话词云', fontsize=16, fontweight='bold', pad=15)
fig.tight_layout()
charts['wordcloud_user'] = fig_to_base64(fig)

npc_texts = ' '.join(df[df['回复类型']=='常规回复']['NPC回答'].dropna().astype(str).tolist())
npc_words = jieba.lcut(npc_texts)
npc_stopwords = stopwords | {'校验', '错误', '这事儿', '不过', '话说', '回来'}
npc_words_filtered = [w for w in npc_words if len(w) >= 2 and w not in npc_stopwords]
npc_word_freq = Counter(npc_words_filtered)

wc_npc = WordCloud(
    font_path=FONT_PATH,
    width=900,
    height=450,
    background_color='white',
    max_words=120,
    max_font_size=100,
    min_font_size=12,
    colormap='Oranges',
    prefer_horizontal=0.7,
    margin=5,
)
wc_npc.generate_from_frequencies(npc_word_freq)

fig, ax = plt.subplots(figsize=(12, 6))
ax.imshow(wc_npc, interpolation='bilinear')
ax.axis('off')
ax.set_title('NPC回答词云', fontsize=16, fontweight='bold', pad=15)
fig.tight_layout()
charts['wordcloud_npc'] = fig_to_base64(fig)

# ============================================================
# 5. 高频词 TOP20
# ============================================================
top20_user = word_freq.most_common(20)
top20_npc = npc_word_freq.most_common(20)

# ============================================================
# 6. 拒答内容分类
# ============================================================
refuse_df = df[df['回复类型'] == '拒答回复'].copy()
refuse_texts = refuse_df['用户对话'].tolist()

def classify_refuse(text):
    text = str(text)
    if any(w in text for w in ['操', '妈', 'cnm', 'wcnm', '草', '艹', '滚', '死', 'sb', 'SB', '傻逼', '妈的']):
        return '辱骂/脏话'
    elif any(w in text for w in ['睡', '三围', '体重', '身材', '胸', '色', '性', '草你', 'doi']):
        return '色情/擦边'
    elif any(w in text for w in ['新中国', '政治', '共产', '国家', '主席', '总书记', '习近平']):
        return '政治敏感'
    else:
        return '其他敏感'

refuse_df['拒答分类'] = refuse_df['用户对话'].apply(classify_refuse)
refuse_category = refuse_df['拒答分类'].value_counts()

fig, ax = plt.subplots(figsize=(5, 5))
colors_refuse = ['#E74C3C', '#F39C12', '#9B59B6', '#95A5A6']
wedges, texts, autotexts = ax.pie(
    refuse_category.values,
    labels=[f'{c}\n{v}条' for c, v in zip(refuse_category.index, refuse_category.values)],
    colors=colors_refuse[:len(refuse_category)],
    autopct='%1.1f%%', startangle=90, textprops={'fontsize': 11}
)
ax.set_title('拒答内容分类', fontsize=14, fontweight='bold', pad=15)
fig.tight_layout()
charts['refuse_category'] = fig_to_base64(fig)

# ============================================================
# 7. 典型对话 case
# ============================================================
top_users = user_turns.nlargest(3).index.tolist()
good_cases = []
for uid in top_users[:2]:
    user_df = df[df['用户ID'] == uid].sort_values('用户对话时间').head(5)
    convs = []
    for _, row in user_df.iterrows():
        convs.append({
            'time': row['用户对话时间'].strftime('%m-%d %H:%M'),
            'user': str(row['用户对话']),
            'npc': str(row['NPC回答'])[:120]
        })
    good_cases.append({'user_id': str(uid)[-8:], 'turns': int(user_turns[uid]), 'conversations': convs})

refuse_cases = []
for _, row in refuse_df.head(8).iterrows():
    refuse_cases.append({
        'user': str(row['用户对话']),
        'category': row['拒答分类']
    })

# ============================================================
# 8. 每日分用户指标
# ============================================================
daily_users = df.groupby('日期')['用户ID'].nunique()
daily_avg_turns = df.groupby('日期').apply(lambda x: len(x) / x['用户ID'].nunique())

# ============================================================
# 9. 生成 HTML
# ============================================================
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>《异人之下》NPC王也 AI对话上线效果分析报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.7;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: white;
            padding: 50px 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
            letter-spacing: 2px;
        }}
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.8;
            margin-top: 8px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 30px 20px;
        }}
        .section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        .section h2 {{
            font-size: 22px;
            color: #1a1a2e;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #4A90D9;
            display: inline-block;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 18px;
            margin-top: 15px;
        }}
        .kpi-card {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8f0fe 100%);
            border-radius: 10px;
            padding: 22px 18px;
            text-align: center;
            border: 1px solid #d5e3f7;
        }}
        .kpi-card .value {{
            font-size: 32px;
            font-weight: 700;
            color: #4A90D9;
            display: block;
        }}
        .kpi-card .label {{
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }}
        .chart-img {{
            text-align: center;
            margin: 20px 0;
        }}
        .chart-img img {{
            max-width: 100%;
            border-radius: 8px;
        }}
        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .two-col {{ grid-template-columns: 1fr; }}
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }}
        table th {{
            background: #4A90D9;
            color: white;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
        }}
        table td {{
            padding: 9px 12px;
            border-bottom: 1px solid #eee;
        }}
        table tr:hover {{
            background: #f8f9ff;
        }}
        table tr:nth-child(even) {{
            background: #fafbfc;
        }}
        .tag {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .tag-red {{ background: #fde8e8; color: #e74c3c; }}
        .tag-orange {{ background: #fef3e2; color: #f39c12; }}
        .tag-purple {{ background: #f0e6f6; color: #9b59b6; }}
        .tag-gray {{ background: #eee; color: #666; }}
        .case-box {{
            background: #f8f9ff;
            border-radius: 8px;
            padding: 18px;
            margin: 12px 0;
            border-left: 4px solid #4A90D9;
        }}
        .case-box .case-title {{
            font-weight: 700;
            color: #4A90D9;
            margin-bottom: 10px;
        }}
        .chat-line {{
            margin: 6px 0;
            font-size: 13.5px;
        }}
        .chat-line .role {{
            font-weight: 600;
            display: inline-block;
            min-width: 48px;
        }}
        .chat-line .role-user {{ color: #2ecc71; }}
        .chat-line .role-npc {{ color: #e67e22; }}
        .insight-box {{
            background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
            border-radius: 8px;
            padding: 18px 22px;
            margin: 15px 0;
            border-left: 4px solid #f39c12;
        }}
        .insight-box strong {{
            color: #e67e22;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 13px;
        }}
        .daily-table {{
            margin-top: 15px;
        }}
    </style>
</head>
<body>

<!-- ==================== HEADER ==================== -->
<div class="header">
    <h1>🎮 《异人之下》NPC王也 AI对话</h1>
    <h1>上线效果分析报告</h1>
    <div class="subtitle">数据周期：{date_range_start} ~ {date_range_end} | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>

<div class="container">

<!-- ==================== 1. 核心指标 ==================== -->
<div class="section">
    <h2>📊 一、核心指标总览</h2>
    <div class="kpi-grid">
        <div class="kpi-card">
            <span class="value">{total_conversations:,}</span>
            <span class="label">总对话数</span>
        </div>
        <div class="kpi-card">
            <span class="value">{unique_users}</span>
            <span class="label">独立用户数</span>
        </div>
        <div class="kpi-card">
            <span class="value">{avg_daily:.0f}</span>
            <span class="label">日均对话数</span>
        </div>
        <div class="kpi-card">
            <span class="value">{avg_turns:.1f}</span>
            <span class="label">人均对话轮次</span>
        </div>
        <div class="kpi-card">
            <span class="value">{median_turns:.0f}</span>
            <span class="label">轮次中位数</span>
        </div>
        <div class="kpi-card">
            <span class="value">{avg_response_time:.1f}s</span>
            <span class="label">平均响应时间</span>
        </div>
        <div class="kpi-card">
            <span class="value">{refuse_rate:.1f}%</span>
            <span class="label">拒答率</span>
        </div>
        <div class="kpi-card">
            <span class="value">{max_turns}</span>
            <span class="label">单用户最高轮次</span>
        </div>
    </div>

    <!-- 每日明细 -->
    <table class="daily-table">
        <tr>
            <th>日期</th>
            <th>对话数</th>
            <th>独立用户数</th>
            <th>人均轮次</th>
        </tr>"""

for d in sorted(daily_counts.index):
    html_content += f"""
        <tr>
            <td>{d}</td>
            <td>{daily_counts[d]}</td>
            <td>{daily_users[d]}</td>
            <td>{daily_avg_turns[d]:.1f}</td>
        </tr>"""

html_content += f"""
    </table>
</div>

<!-- ==================== 2. 趋势分析 ==================== -->
<div class="section">
    <h2>📈 二、对话趋势分析</h2>
    <div class="two-col">
        <div class="chart-img">
            <img src="data:image/png;base64,{charts['daily_trend']}" alt="每日对话量趋势">
        </div>
        <div class="chart-img">
            <img src="data:image/png;base64,{charts['hourly_dist']}" alt="24小时对话分布">
        </div>
    </div>
    <div class="insight-box">
        <strong>📌 洞察：</strong>2月12日对话量出现显著峰值（{daily_counts.max()}条），推测当日可能有运营推广活动或用户自传播驱动。用户活跃高峰集中在白天时段，符合目标用户群体的作息特征。
    </div>
</div>

<!-- ==================== 3. 用户参与度 ==================== -->
<div class="section">
    <h2>👥 三、用户参与度分析</h2>
    <div class="two-col">
        <div class="chart-img">
            <img src="data:image/png;base64,{charts['turn_dist']}" alt="对话轮次分布">
        </div>
        <div class="chart-img">
            <img src="data:image/png;base64,{charts['retention']}" alt="跨天留存">
        </div>
    </div>
    <div class="insight-box">
        <strong>📌 洞察：</strong>
        {turn_dist.iloc[0]}位用户（{turn_dist.iloc[0]/unique_users*100:.1f}%）仅对话1轮即离开，说明首轮体验的吸引力仍有提升空间。
        但也有 {(user_turns >= 10).sum()} 位用户对话超过10轮，说明深度用户的粘性较好。
        中位数为{median_turns:.0f}轮，均值{avg_turns:.1f}轮，均值远高于中位数说明存在少量超高活跃用户拉高均值。
    </div>
</div>

<!-- ==================== 4. 词云分析 ==================== -->
<div class="section">
    <h2>☁️ 四、对话词云分析</h2>
    <h3 style="margin:15px 0 5px;color:#4A90D9;">用户对话词云</h3>
    <div class="chart-img">
        <img src="data:image/png;base64,{charts['wordcloud_user']}" alt="用户对话词云">
    </div>
    <h3 style="margin:15px 0 5px;color:#e67e22;">NPC回答词云</h3>
    <div class="chart-img">
        <img src="data:image/png;base64,{charts['wordcloud_npc']}" alt="NPC回答词云">
    </div>

    <div class="two-col">
        <div>
            <h4 style="margin:10px 0;color:#4A90D9;">🔤 用户高频词 TOP20</h4>
            <table>
                <tr><th>排名</th><th>关键词</th><th>出现次数</th></tr>"""

for i, (word, cnt) in enumerate(top20_user, 1):
    html_content += f"""
                <tr><td>{i}</td><td>{word}</td><td>{cnt}</td></tr>"""

html_content += f"""
            </table>
        </div>
        <div>
            <h4 style="margin:10px 0;color:#e67e22;">🔤 NPC高频词 TOP20</h4>
            <table>
                <tr><th>排名</th><th>关键词</th><th>出现次数</th></tr>"""

for i, (word, cnt) in enumerate(top20_npc, 1):
    html_content += f"""
                <tr><td>{i}</td><td>{word}</td><td>{cnt}</td></tr>"""

html_content += f"""
            </table>
        </div>
    </div>
    <div class="insight-box">
        <strong>📌 洞察：</strong>用户对话中 "上线"、"公测" 等游戏相关词汇高频出现，说明用户对游戏上线时间关注度极高。NPC回答词云则体现了角色"王也"的对话风格特征。
    </div>
</div>

<!-- ==================== 5. 回复质量 ==================== -->
<div class="section">
    <h2>🎯 五、NPC回复质量分析</h2>
    <div class="two-col">
        <div class="chart-img">
            <img src="data:image/png;base64,{charts['reply_type']}" alt="回复类型分布">
        </div>
        <div class="chart-img">
            <img src="data:image/png;base64,{charts['response_time']}" alt="响应时间分布">
        </div>
    </div>
    <div class="insight-box">
        <strong>📌 洞察：</strong>常规回复率 {100-refuse_rate:.1f}%，拒答率 {refuse_rate:.1f}%（{refuse_reply}条），整体安全拦截机制运行正常。
        平均响应时间 {avg_response_time:.1f}秒，中位数 {median_response_time:.1f}秒，响应速度表现良好。
    </div>
</div>

<!-- ==================== 6. 安全合规 ==================== -->
<div class="section">
    <h2>🛡️ 六、安全与合规分析</h2>
    <div class="chart-img" style="max-width:400px;margin:0 auto;">
        <img src="data:image/png;base64,{charts['refuse_category']}" alt="拒答分类">
    </div>
    <h4 style="margin:20px 0 10px;">拒答触发内容示例</h4>
    <table>
        <tr><th>用户输入</th><th>分类</th></tr>"""

tag_class_map = {'辱骂/脏话': 'tag-red', '色情/擦边': 'tag-orange', '政治敏感': 'tag-purple', '其他敏感': 'tag-gray'}
for case in refuse_cases:
    tag_cls = tag_class_map.get(case['category'], 'tag-gray')
    html_content += f"""
        <tr>
            <td>{case['user']}</td>
            <td><span class="tag {tag_cls}">{case['category']}</span></td>
        </tr>"""

html_content += f"""
    </table>
    <div class="insight-box">
        <strong>📌 洞察：</strong>拒答内容主要集中在色情擦边和辱骂类，安全策略有效拦截了敏感内容。建议持续优化拒答话术，避免所有拒答统一返回"[校验错误]"，可改为更自然的角色化回应。
    </div>
</div>

<!-- ==================== 7. 典型对话 ==================== -->
<div class="section">
    <h2>💬 七、典型对话案例</h2>"""

for case in good_cases:
    html_content += f"""
    <div class="case-box">
        <div class="case-title">🔥 高活跃用户 (ID: ...{case['user_id']}) — 共 {case['turns']} 轮对话</div>"""
    for conv in case['conversations']:
        html_content += f"""
        <div class="chat-line"><span class="role role-user">用户：</span>{conv['user']}</div>
        <div class="chat-line"><span class="role role-npc">王也：</span>{conv['npc']}</div>
        <hr style="border:none;border-top:1px dashed #ddd;margin:4px 0;">"""
    html_content += """
    </div>"""

html_content += f"""
</div>

<!-- ==================== 8. 总结建议 ==================== -->
<div class="section">
    <h2>📝 八、总结与优化建议</h2>
    <table>
        <tr><th style="width:80px;">维度</th><th style="width:120px;">现状</th><th>优化建议</th></tr>
        <tr>
            <td><strong>用户规模</strong></td>
            <td>{num_days}天{unique_users}人</td>
            <td>初期用户量合理，建议加大渠道推广力度，利用2月12日的峰值趋势分析传播路径</td>
        </tr>
        <tr>
            <td><strong>用户留存</strong></td>
            <td>首轮流失率 {turn_dist.iloc[0]/unique_users*100:.0f}%</td>
            <td>优化首轮对话体验，增加引导性话术，让NPC主动提问延长对话</td>
        </tr>
        <tr>
            <td><strong>回复质量</strong></td>
            <td>常规回复率 {100-refuse_rate:.1f}%</td>
            <td>拒答话术需优化，避免生硬的"[校验错误]"提示，建议替换为角色化的拒绝话术</td>
        </tr>
        <tr>
            <td><strong>响应速度</strong></td>
            <td>均值 {avg_response_time:.1f}s</td>
            <td>响应速度整体良好，关注长尾延迟case进行优化</td>
        </tr>
        <tr>
            <td><strong>内容安全</strong></td>
            <td>拒答 {refuse_reply} 条</td>
            <td>安全拦截机制有效，建议定期review常规回复中是否有漏网之鱼</td>
        </tr>
        <tr>
            <td><strong>用户诉求</strong></td>
            <td>高频询问上线时间</td>
            <td>优化上线时间相关问答的话术，提供更丰富的引导内容，减少机械式重复回答</td>
        </tr>
    </table>
</div>

</div>

<div class="footer">
    《异人之下》NPC王也 AI对话上线效果分析报告 · 数据周期 {date_range_start} ~ {date_range_end} · 自动生成
</div>

</body>
</html>"""

# ============================================================
# 10. 输出
# ============================================================
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f'✅ 报告已生成: {OUTPUT_HTML}')
print(f'   总对话数: {total_conversations}')
print(f'   独立用户: {unique_users}')
print(f'   图表数量: {len(charts)}')
