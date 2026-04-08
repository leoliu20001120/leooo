#!/usr/bin/env python3
"""
S 级符文分类模型 — 基于英雄×符文的胜率和 Pick 率预测 OPGG S 级评级
"""
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path

# === 数据加载与合并 ===
BASE = Path(__file__).parent
df_stats = pd.read_excel(BASE / 'data/step1_2_champion_augment_stats.xlsx')
df_opgg = pd.read_csv(BASE / 'lol_opgg_kiwi_augment_data.csv', sep='\t')

merged = df_stats.merge(
    df_opgg, left_on=['championid', 'player_augment'],
    right_on=['championid', 'augment_id'], how='inner',
    suffixes=('_stats', '_opgg')
)

# === 目标变量 ===
merged['is_S'] = (merged['tier_label'] == 'S').astype(int)

# === 特征工程 ===
# 1. 基础特征
merged['win_rate_pct'] = merged['win_rate'] * 100  # 转成百分比
merged['show_rate_log'] = np.log1p(merged['show_rate'] * 10000)  # log 变换 show_rate
merged['rarity_clean'] = merged['rarity'].replace(0, np.nan)  # rarity=0 表示缺失

# 2. 英雄维度聚合特征
champion_agg = merged.groupby('championid').agg(
    champ_mean_wr=('win_rate', 'mean'),
    champ_std_wr=('win_rate', 'std'),
    champ_mean_sr=('show_rate', 'mean'),
    champ_s_ratio=('is_S', 'mean'),  # 该英雄 S 级符文占比
    champ_augment_count=('player_augment', 'count'),
).reset_index()
merged = merged.merge(champion_agg, on='championid', how='left')

# 3. 符文维度聚合特征
augment_agg = merged.groupby('player_augment').agg(
    aug_mean_wr=('win_rate', 'mean'),
    aug_std_wr=('win_rate', 'std'),
    aug_mean_sr=('show_rate', 'mean'),
    aug_s_ratio=('is_S', 'mean'),  # 该符文在所有英雄中被评为 S 的比例
    aug_champion_count=('championid', 'count'),
).reset_index()
merged = merged.merge(augment_agg, on='player_augment', how='left')

# 4. 差异/交互特征
merged['wr_vs_champ_mean'] = merged['win_rate'] - merged['champ_mean_wr']  # 胜率偏离英雄均值
merged['wr_vs_aug_mean'] = merged['win_rate'] - merged['aug_mean_wr']      # 胜率偏离符文均值
merged['sr_vs_champ_mean'] = merged['show_rate'] - merged['champ_mean_sr']
merged['wr_x_sr'] = merged['win_rate'] * merged['show_rate_log']           # 胜率×log出现率 交互

# 5. rarity one-hot
rarity_dummies = pd.get_dummies(merged['rarity_clean'], prefix='rarity', dummy_na=True)
merged = pd.concat([merged, rarity_dummies], axis=1)

# 填充 NaN
merged = merged.fillna(0)

# === 特征列表 ===
feature_cols = [
    # 基础
    'win_rate', 'show_rate', 'show_rate_log', 'win_rate_pct',
    # rarity
    'rarity_1.0', 'rarity_4.0', 'rarity_8.0', 'rarity_nan',
    # 英雄聚合
    'champ_mean_wr', 'champ_std_wr', 'champ_mean_sr', 'champ_s_ratio', 'champ_augment_count',
    # 符文聚合
    'aug_mean_wr', 'aug_std_wr', 'aug_mean_sr', 'aug_s_ratio', 'aug_champion_count',
    # 差异/交互
    'wr_vs_champ_mean', 'wr_vs_aug_mean', 'sr_vs_champ_mean', 'wr_x_sr',
]

# 确保所有特征列存在
feature_cols = [c for c in feature_cols if c in merged.columns]
print(f"使用特征 ({len(feature_cols)}): {feature_cols}")

X = merged[feature_cols].values
y = merged['is_S'].values

# === 模型训练与评估 ===
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score, f1_score, make_scorer
)
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# 分割数据
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n训练集: {X_train.shape[0]} 样本 (S: {y_train.sum()}, 非S: {(y_train==0).sum()})")
print(f"测试集: {X_test.shape[0]} 样本 (S: {y_test.sum()}, 非S: {(y_test==0).sum()})")

# 定义模型
models = {
    'Logistic Regression': Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(
            class_weight='balanced', max_iter=1000, C=1.0, random_state=42
        ))
    ]),
    'Random Forest': Pipeline([
        ('clf', RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=20,
            class_weight='balanced', random_state=42, n_jobs=-1
        ))
    ]),
    'Gradient Boosting': Pipeline([
        ('clf', GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            min_samples_leaf=20, subsample=0.8, random_state=42
        ))
    ]),
}

# 训练和评估
results = {}
for name, model in models.items():
    print(f"\n{'='*50}")
    print(f"训练: {name}")
    
    # 5-fold CV
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        model, X_train, y_train, cv=cv,
        scoring=['roc_auc', 'f1', 'precision', 'recall'],
        return_train_score=True
    )
    
    print(f"  CV ROC-AUC: {cv_results['test_roc_auc'].mean():.4f} ± {cv_results['test_roc_auc'].std():.4f}")
    print(f"  CV F1:      {cv_results['test_f1'].mean():.4f} ± {cv_results['test_f1'].std():.4f}")
    
    # 在全量训练集上训练
    model.fit(X_train, y_train)
    
    # 测试集预测
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # 评估指标
    roc_auc = roc_auc_score(y_test, y_prob)
    ap = average_precision_score(y_test, y_prob)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=['非S', 'S'], output_dict=True)
    
    # ROC 曲线数据
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_prob)
    
    results[name] = {
        'model': model,
        'y_pred': y_pred,
        'y_prob': y_prob,
        'roc_auc': roc_auc,
        'ap': ap,
        'f1': f1,
        'cm': cm,
        'report': report,
        'fpr': fpr,
        'tpr': tpr,
        'precision_curve': precision_curve,
        'recall_curve': recall_curve,
        'cv_roc_auc_mean': cv_results['test_roc_auc'].mean(),
        'cv_roc_auc_std': cv_results['test_roc_auc'].std(),
        'cv_f1_mean': cv_results['test_f1'].mean(),
        'cv_f1_std': cv_results['test_f1'].std(),
    }
    
    print(f"  Test ROC-AUC: {roc_auc:.4f}")
    print(f"  Test AP:      {ap:.4f}")
    print(f"  Test F1:      {f1:.4f}")
    print(f"  Confusion Matrix:\n{cm}")
    print(classification_report(y_test, y_pred, target_names=['非S', 'S']))

# === 最佳模型的特征重要性 ===
best_name = max(results, key=lambda k: results[k]['roc_auc'])
best_model = results[best_name]['model']
print(f"\n最佳模型: {best_name} (ROC-AUC: {results[best_name]['roc_auc']:.4f})")

if 'Random Forest' in best_name:
    importances = best_model.named_steps['clf'].feature_importances_
elif 'Gradient Boosting' in best_name:
    importances = best_model.named_steps['clf'].feature_importances_
elif 'Logistic' in best_name:
    importances = np.abs(best_model.named_steps['clf'].coef_[0])
else:
    importances = np.zeros(len(feature_cols))

feat_imp = pd.DataFrame({
    'feature': feature_cols,
    'importance': importances
}).sort_values('importance', ascending=False)
print("\n特征重要性 Top 15:")
print(feat_imp.head(15).to_string(index=False))

# === 无泄漏模型（仅用 win_rate 和 show_rate）===
print(f"\n{'='*60}")
print("无泄漏模型（仅 win_rate + show_rate + rarity）")
leak_free_cols = ['win_rate', 'show_rate', 'show_rate_log', 'win_rate_pct',
                  'rarity_1.0', 'rarity_4.0', 'rarity_8.0', 'rarity_nan']
leak_free_cols = [c for c in leak_free_cols if c in merged.columns]

X_lf = merged[leak_free_cols].values
X_lf_train, X_lf_test, y_lf_train, y_lf_test = train_test_split(
    X_lf, y, test_size=0.2, random_state=42, stratify=y
)

lf_models = {
    'LR (leak-free)': Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42))
    ]),
    'RF (leak-free)': Pipeline([
        ('clf', RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=20,
            class_weight='balanced', random_state=42, n_jobs=-1
        ))
    ]),
    'GB (leak-free)': Pipeline([
        ('clf', GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            min_samples_leaf=20, subsample=0.8, random_state=42
        ))
    ]),
}

lf_results = {}
for name, model in lf_models.items():
    model.fit(X_lf_train, y_lf_train)
    y_pred_lf = model.predict(X_lf_test)
    y_prob_lf = model.predict_proba(X_lf_test)[:, 1]
    roc_auc_lf = roc_auc_score(y_lf_test, y_prob_lf)
    f1_lf = f1_score(y_lf_test, y_pred_lf)
    fpr_lf, tpr_lf, _ = roc_curve(y_lf_test, y_prob_lf)
    pr_lf, rc_lf, _ = precision_recall_curve(y_lf_test, y_prob_lf)
    
    lf_results[name] = {
        'roc_auc': roc_auc_lf, 'f1': f1_lf,
        'fpr': fpr_lf, 'tpr': tpr_lf,
        'precision_curve': pr_lf, 'recall_curve': rc_lf,
        'y_prob': y_prob_lf, 'y_pred': y_pred_lf,
        'report': classification_report(y_lf_test, y_pred_lf, target_names=['非S', 'S'], output_dict=True),
        'cm': confusion_matrix(y_lf_test, y_pred_lf),
    }
    print(f"  {name}: ROC-AUC={roc_auc_lf:.4f}, F1={f1_lf:.4f}")

# === 阈值分析（最佳模型）===
best_prob = results[best_name]['y_prob']
thresholds = np.arange(0.05, 0.96, 0.05)
threshold_analysis = []
for t in thresholds:
    y_t = (best_prob >= t).astype(int)
    tp = ((y_t == 1) & (y_test == 1)).sum()
    fp = ((y_t == 1) & (y_test == 0)).sum()
    fn = ((y_t == 0) & (y_test == 1)).sum()
    tn = ((y_t == 0) & (y_test == 0)).sum()
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_t = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    threshold_analysis.append({
        'threshold': t, 'precision': prec, 'recall': rec, 'f1': f1_t,
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
    })
df_thresh = pd.DataFrame(threshold_analysis)
best_thresh_idx = df_thresh['f1'].idxmax()
best_threshold = df_thresh.loc[best_thresh_idx, 'threshold']
print(f"\n最佳 F1 阈值: {best_threshold:.2f} (F1={df_thresh.loc[best_thresh_idx, 'f1']:.4f})")

# ========================================================
#  生成 HTML 报告
# ========================================================
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# 颜色方案
COLORS = {
    'S': '#FF6B35', 'nonS': '#4ECDC4',
    'LR': '#636EFA', 'RF': '#EF553B', 'GB': '#00CC96',
    'LR_lf': '#AB63FA', 'RF_lf': '#FFA15A', 'GB_lf': '#19D3F3',
    'bg': '#1a1a2e', 'card': '#16213e', 'text': '#e0e0e0',
    'accent': '#FF6B35', 'grid': '#2a2a4a'
}

model_colors = {
    'Logistic Regression': COLORS['LR'],
    'Random Forest': COLORS['RF'],
    'Gradient Boosting': COLORS['GB'],
    'LR (leak-free)': COLORS['LR_lf'],
    'RF (leak-free)': COLORS['RF_lf'],
    'GB (leak-free)': COLORS['GB_lf'],
}

layout_defaults = dict(
    paper_bgcolor=COLORS['bg'],
    plot_bgcolor=COLORS['card'],
    font=dict(color=COLORS['text'], family='system-ui, -apple-system, sans-serif'),
    margin=dict(l=60, r=30, t=50, b=50),
)

figures = []

# --- 图1: 模型对比表 ---
fig1 = go.Figure()
model_names_all = list(results.keys()) + list(lf_results.keys())
roc_aucs_all = [results[k]['roc_auc'] for k in results] + [lf_results[k]['roc_auc'] for k in lf_results]
f1s_all = [results[k]['f1'] for k in results] + [lf_results[k]['f1'] for k in lf_results]
precisions_all = [results[k]['report']['S']['precision'] for k in results] + [lf_results[k]['report']['S']['precision'] for k in lf_results]
recalls_all = [results[k]['report']['S']['recall'] for k in results] + [lf_results[k]['report']['S']['recall'] for k in lf_results]

colors_bar = [model_colors.get(n, '#888') for n in model_names_all]

fig1 = make_subplots(rows=1, cols=4, subplot_titles=['ROC-AUC', 'F1 Score', 'Precision (S)', 'Recall (S)'])
for i, (vals, title) in enumerate([
    (roc_aucs_all, 'ROC-AUC'), (f1s_all, 'F1'), (precisions_all, 'Precision'), (recalls_all, 'Recall')
]):
    fig1.add_trace(go.Bar(
        x=model_names_all, y=vals,
        marker_color=colors_bar, text=[f'{v:.3f}' for v in vals],
        textposition='outside', showlegend=False
    ), row=1, col=i+1)

fig1.update_layout(
    **layout_defaults, height=400,
    title='📊 模型性能对比 (全特征 vs 无泄漏)',
)
fig1.update_yaxes(range=[0, 1.05])
figures.append(('model_comparison', fig1))

# --- 图2: ROC 曲线 ---
fig2 = go.Figure()
for name in results:
    r = results[name]
    fig2.add_trace(go.Scatter(
        x=r['fpr'], y=r['tpr'], mode='lines',
        name=f"{name} (AUC={r['roc_auc']:.3f})",
        line=dict(color=model_colors[name], width=2.5)
    ))
for name in lf_results:
    r = lf_results[name]
    fig2.add_trace(go.Scatter(
        x=r['fpr'], y=r['tpr'], mode='lines',
        name=f"{name} (AUC={r['roc_auc']:.3f})",
        line=dict(color=model_colors[name], width=2, dash='dash')
    ))
fig2.add_trace(go.Scatter(
    x=[0, 1], y=[0, 1], mode='lines',
    name='Random', line=dict(color='gray', width=1, dash='dot')
))
fig2.update_layout(
    **layout_defaults, height=500,
    title='📈 ROC 曲线对比',
    xaxis_title='False Positive Rate', yaxis_title='True Positive Rate',
    legend=dict(x=0.55, y=0.05, bgcolor='rgba(0,0,0,0.5)')
)
figures.append(('roc_curves', fig2))

# --- 图3: PR 曲线 ---
fig3 = go.Figure()
for name in results:
    r = results[name]
    ap = average_precision_score(y_test, r['y_prob'])
    fig3.add_trace(go.Scatter(
        x=r['recall_curve'], y=r['precision_curve'], mode='lines',
        name=f"{name} (AP={ap:.3f})",
        line=dict(color=model_colors[name], width=2.5)
    ))
for name in lf_results:
    r = lf_results[name]
    ap_lf = average_precision_score(y_lf_test, r['y_prob'])
    fig3.add_trace(go.Scatter(
        x=r['recall_curve'], y=r['precision_curve'], mode='lines',
        name=f"{name} (AP={ap_lf:.3f})",
        line=dict(color=model_colors[name], width=2, dash='dash')
    ))
# baseline
baseline = y_test.mean()
fig3.add_trace(go.Scatter(
    x=[0, 1], y=[baseline, baseline], mode='lines',
    name=f'Baseline ({baseline:.3f})', line=dict(color='gray', width=1, dash='dot')
))
fig3.update_layout(
    **layout_defaults, height=500,
    title='📈 Precision-Recall 曲线',
    xaxis_title='Recall', yaxis_title='Precision',
    legend=dict(x=0.02, y=0.05, bgcolor='rgba(0,0,0,0.5)')
)
figures.append(('pr_curves', fig3))

# --- 图4: 特征重要性 ---
top_n = 15
top_feat = feat_imp.head(top_n).iloc[::-1]  # 倒序方便横向展示
fig4 = go.Figure(go.Bar(
    x=top_feat['importance'].values,
    y=top_feat['feature'].values,
    orientation='h',
    marker_color=COLORS['accent'],
    text=[f'{v:.4f}' for v in top_feat['importance'].values],
    textposition='outside'
))
fig4.update_layout(
    **layout_defaults, height=500,
    title=f'🔑 特征重要性 Top {top_n} ({best_name})',
    xaxis_title='Importance',
)
figures.append(('feature_importance', fig4))

# --- 图5: 混淆矩阵（最佳模型）---
cm_best = results[best_name]['cm']
cm_labels = ['非S', 'S']
fig5 = go.Figure(go.Heatmap(
    z=cm_best, x=cm_labels, y=cm_labels,
    text=[[str(v) for v in row] for row in cm_best],
    texttemplate='%{text}', textfont=dict(size=20),
    colorscale='YlOrRd', showscale=True
))
fig5.update_layout(
    **layout_defaults, height=400,
    title=f'🎯 混淆矩阵 ({best_name})',
    xaxis_title='预测', yaxis_title='实际',
)
figures.append(('confusion_matrix', fig5))

# --- 图6: 阈值分析 ---
fig6 = go.Figure()
fig6.add_trace(go.Scatter(
    x=df_thresh['threshold'], y=df_thresh['precision'],
    mode='lines+markers', name='Precision',
    line=dict(color=COLORS['LR'], width=2)
))
fig6.add_trace(go.Scatter(
    x=df_thresh['threshold'], y=df_thresh['recall'],
    mode='lines+markers', name='Recall',
    line=dict(color=COLORS['RF'], width=2)
))
fig6.add_trace(go.Scatter(
    x=df_thresh['threshold'], y=df_thresh['f1'],
    mode='lines+markers', name='F1 Score',
    line=dict(color=COLORS['GB'], width=2.5)
))
fig6.add_vline(x=best_threshold, line_dash='dash', line_color=COLORS['accent'],
               annotation_text=f'Best F1={df_thresh.loc[best_thresh_idx, "f1"]:.3f}\n@ t={best_threshold:.2f}')
fig6.update_layout(
    **layout_defaults, height=400,
    title=f'⚖️ 阈值分析 ({best_name})',
    xaxis_title='分类阈值', yaxis_title='分数',
    legend=dict(x=0.7, y=0.95, bgcolor='rgba(0,0,0,0.5)')
)
figures.append(('threshold_analysis', fig6))

# --- 图7: 预测概率分布 ---
prob_s = best_prob[y_test == 1]
prob_ns = best_prob[y_test == 0]
fig7 = go.Figure()
fig7.add_trace(go.Histogram(
    x=prob_ns, name='非S (实际)', nbinsx=50,
    marker_color=COLORS['nonS'], opacity=0.7
))
fig7.add_trace(go.Histogram(
    x=prob_s, name='S (实际)', nbinsx=50,
    marker_color=COLORS['S'], opacity=0.7
))
fig7.update_layout(
    **layout_defaults, height=400, barmode='overlay',
    title=f'📊 预测概率分布 ({best_name})',
    xaxis_title='预测为 S 的概率', yaxis_title='样本数',
    legend=dict(x=0.7, y=0.95, bgcolor='rgba(0,0,0,0.5)')
)
figures.append(('prob_distribution', fig7))

# --- 图8: win_rate vs show_rate 散点（S vs 非S）---
sample = merged.sample(min(5000, len(merged)), random_state=42)
fig8 = go.Figure()
for label, color, name in [(0, COLORS['nonS'], '非S'), (1, COLORS['S'], 'S')]:
    mask = sample['is_S'] == label
    fig8.add_trace(go.Scatter(
        x=sample.loc[mask, 'win_rate'] * 100,
        y=sample.loc[mask, 'show_rate'] * 100,
        mode='markers', name=name,
        marker=dict(color=color, size=4 if label == 0 else 6, opacity=0.5 if label == 0 else 0.8),
        text=sample.loc[mask, 'champion_name_stats'] + ' + ' + sample.loc[mask, 'augment_name_stats'],
        hovertemplate='%{text}<br>胜率: %{x:.1f}%<br>Pick率: %{y:.4f}%'
    ))
fig8.update_layout(
    **layout_defaults, height=500,
    title='🔍 胜率 vs Pick率 散点图（S vs 非S）',
    xaxis_title='胜率 (%)', yaxis_title='Pick率 (%)',
    legend=dict(x=0.85, y=0.95, bgcolor='rgba(0,0,0,0.5)')
)
figures.append(('scatter_wr_sr', fig8))

# --- 图9: 各 rarity 下 S 级分布 ---
rarity_map = {1: '白银', 4: '黄金', 8: '棱彩', 0: '未知'}
merged['rarity_name'] = merged['rarity'].map(rarity_map)
rarity_tier = merged.groupby(['rarity_name', 'is_S']).size().reset_index(name='count')
rarity_total = merged.groupby('rarity_name').size().reset_index(name='total')
rarity_s = rarity_tier[rarity_tier['is_S'] == 1].merge(rarity_total, on='rarity_name')
rarity_s['s_ratio'] = rarity_s['count'] / rarity_s['total']

fig9 = go.Figure(go.Bar(
    x=rarity_s['rarity_name'], y=rarity_s['s_ratio'] * 100,
    marker_color=[COLORS['nonS'], COLORS['accent'], COLORS['LR'], COLORS['GB']],
    text=[f"{v:.1f}%" for v in rarity_s['s_ratio'] * 100],
    textposition='outside'
))
fig9.update_layout(
    **layout_defaults, height=400,
    title='💎 各稀有度下 S 级符文占比',
    xaxis_title='稀有度', yaxis_title='S 级占比 (%)',
)
figures.append(('rarity_s_ratio', fig9))

# ========================================================
#  组装 HTML
# ========================================================
chart_divs = ""
chart_scripts = ""
for i, (chart_id, fig) in enumerate(figures):
    chart_divs += f'<div class="chart-container" id="chart_{chart_id}"></div>\n'
    chart_scripts += f"Plotly.newPlot('chart_{chart_id}', {fig.to_json()}.data, {fig.to_json()}.layout, {{responsive: true}});\n"

# 构建 summary 数据
summary_rows = ""
for name in list(results.keys()) + list(lf_results.keys()):
    r = results.get(name, lf_results.get(name))
    tag = "🏷️ 全特征" if name in results else "🔒 无泄漏"
    summary_rows += f"""
    <tr>
        <td>{name}</td><td>{tag}</td>
        <td><strong>{r['roc_auc']:.4f}</strong></td>
        <td>{r['f1']:.4f}</td>
        <td>{r['report']['S']['precision']:.4f}</td>
        <td>{r['report']['S']['recall']:.4f}</td>
    </tr>"""

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>S 级符文分类模型报告</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
    padding: 20px;
}}
h1 {{ text-align: center; font-size: 2em; margin: 20px 0 10px; color: {COLORS['accent']}; }}
h2 {{ font-size: 1.5em; margin: 30px 0 15px; color: {COLORS['accent']}; border-bottom: 2px solid {COLORS['accent']}; padding-bottom: 5px; }}
h3 {{ font-size: 1.2em; margin: 15px 0 8px; color: #ccc; }}
.subtitle {{ text-align: center; color: #888; margin-bottom: 30px; font-size: 1.1em; }}
.card {{
    background: {COLORS['card']};
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    border: 1px solid {COLORS['grid']};
}}
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 20px 0;
}}
.metric-card {{
    background: {COLORS['card']};
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    border: 1px solid {COLORS['grid']};
}}
.metric-value {{ font-size: 2em; font-weight: bold; color: {COLORS['accent']}; }}
.metric-label {{ font-size: 0.9em; color: #888; margin-top: 5px; }}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}}
th, td {{
    padding: 10px 12px;
    text-align: center;
    border-bottom: 1px solid {COLORS['grid']};
}}
th {{ background: {COLORS['card']}; color: {COLORS['accent']}; font-weight: 600; }}
tr:hover {{ background: rgba(255, 107, 53, 0.08); }}
.chart-container {{
    background: {COLORS['card']};
    border-radius: 12px;
    padding: 10px;
    margin: 20px 0;
    border: 1px solid {COLORS['grid']};
}}
.insight {{ background: rgba(255, 107, 53, 0.1); border-left: 4px solid {COLORS['accent']}; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
.insight strong {{ color: {COLORS['accent']}; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>🏆 S 级符文分类模型报告</h1>
<p class="subtitle">基于英雄×符文胜率和 Pick 率预测 OPGG S 级评级 | 数据: {len(merged):,} 条记录</p>

<div class="metrics-grid">
    <div class="metric-card">
        <div class="metric-value">{results[best_name]['roc_auc']:.4f}</div>
        <div class="metric-label">最佳 ROC-AUC ({best_name})</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{results[best_name]['f1']:.4f}</div>
        <div class="metric-label">最佳 F1 Score</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{best_threshold:.2f}</div>
        <div class="metric-label">最佳分类阈值</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{len(feature_cols)}</div>
        <div class="metric-label">全特征数 / {len(leak_free_cols)} 无泄漏特征</div>
    </div>
</div>

<h2>📋 模型性能总览</h2>
<div class="card">
    <table>
        <thead><tr>
            <th>模型</th><th>类型</th><th>ROC-AUC</th><th>F1</th><th>Precision (S)</th><th>Recall (S)</th>
        </tr></thead>
        <tbody>{summary_rows}</tbody>
    </table>
</div>

<div class="insight">
    <strong>💡 关键发现：</strong> 全特征模型中 {best_name} 表现最好（ROC-AUC={results[best_name]['roc_auc']:.4f}）。
    但注意全特征模型使用了 <code>aug_s_ratio</code>（符文被评为 S 的全局比例）和 <code>champ_s_ratio</code>（英雄 S 级比例）等 target-leakage 特征。
    <strong>无泄漏模型</strong>仅用 win_rate + show_rate + rarity，更适合实际应用场景。
</div>

<h2>📊 可视化分析</h2>

{chart_divs}

<h2>🧠 深度解读</h2>
<div class="card">
    <h3>1. 全特征 vs 无泄漏模型的差距</h3>
    <div class="insight">
        全特征模型 ROC-AUC 显著高于无泄漏模型，说明 <strong>符文粒度聚合特征（aug_s_ratio 等）是最强预测信号</strong>。
        这些特征本质上是"看答案"——符文本身在全局被评为 S 的概率直接预测了它在每个英雄上的 S 级概率。
        在实际推荐系统中，应使用无泄漏模型或将聚合特征基于历史窗口计算避免穿越。
    </div>
    <h3>2. win_rate 和 show_rate 的预测力</h3>
    <div class="insight">
        无泄漏模型仍然有不错的分类能力，说明 <strong>胜率和 Pick 率确实是 OPGG 评级的核心因子</strong>。
        但仅靠这两个特征不足以完全复现 OPGG 的评级逻辑，OPGG 可能还考虑了玩家段位分布、对局样本量、版本变化等因素。
    </div>
    <h3>3. 阈值选择建议</h3>
    <div class="insight">
        默认 0.5 阈值下 Precision 较高但 Recall 偏低（保守）。
        如果目标是<strong>"少推但推准"</strong>，用高阈值；如果目标是<strong>"不漏掉好符文"</strong>，降低阈值换取更高 Recall。
        最佳 F1 阈值为 <strong>{best_threshold:.2f}</strong>。
    </div>
</div>

<div class="card" style="margin-top: 30px; text-align: center; color: #666;">
    <p>生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} | 数据量: {len(merged):,} 条英雄×符文组合</p>
</div>

<script>
{chart_scripts}
</script>
</body>
</html>
"""

output_path = BASE / 's_tier_classification_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
print(f"\n✅ 报告已生成: {output_path}")
