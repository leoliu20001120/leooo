#!/usr/bin/env python3
"""
从 OPGG 原始数据中，为每个英雄筛选黄金阶和棱彩阶中：
1. Popular（人气）最高的 S 级符文
2. Performance（表现）最高的 S 级符文

过滤条件：
- 黄金阶：只保留 tier_label == 'S'
- 棱彩阶：优先 S 级，如果某英雄棱彩阶没有 S 级则回退到 A 级
- 只保留 popular > 0（排除无人使用的异常数据）
"""

import pandas as pd
import os

# ============================================================
# 1. 加载数据
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

# 加载原始（未修改的）筛选结果表 - 先恢复到修改前的版本
# 需要重新从 backup 或原始数据加载
# 这里我们先加载现有的，然后去掉之前添加的 OPGG_ 开头的行
df_existing_full = pd.read_csv(os.path.join(BASE_DIR, "s_tier_filtered_augments.csv"))

# 去掉之前可能添加的 OPGG_ 开头的行（恢复到原始状态）
df_existing = df_existing_full[~df_existing_full['filter_reason'].str.startswith('OPGG_', na=False)].copy()
print(f"✅ 已恢复原始筛选表: {len(df_existing)} 行（去除了 {len(df_existing_full) - len(df_existing)} 行之前添加的数据）")
print(f"   英雄数: {df_existing['champion_name'].nunique()}")
print(f"   rarity_label 分布:\n{df_existing['rarity_label'].value_counts().to_string()}")

# 加载 OPGG 原始数据
df_opgg = pd.read_csv(os.path.join(PARENT_DIR, "lol_opgg_kiwi_augment_data.csv"), sep="\t")
print(f"\n✅ 已加载 OPGG 原始数据: {len(df_opgg)} 行")

# ============================================================
# 2. 从 OPGG 数据筛选黄金阶和棱彩阶符文
# ============================================================
# 只保留黄金阶(rarity=4)和棱彩阶(rarity=8)，且 popular > 0
df_gold_prismatic = df_opgg[
    (df_opgg['rarity'].isin([4, 8])) & 
    (df_opgg['popular'] > 0)
].copy()

# 黄金阶：只要 S 级
df_gold_s = df_gold_prismatic[
    (df_gold_prismatic['rarity'] == 4) & 
    (df_gold_prismatic['tier_label'] == 'S')
]

# 棱彩阶：优先 S 级，如果某英雄没有 S 级则回退到 A 级
df_prismatic_all = df_gold_prismatic[df_gold_prismatic['rarity'] == 8]
df_prismatic_s = df_prismatic_all[df_prismatic_all['tier_label'] == 'S']
df_prismatic_a = df_prismatic_all[df_prismatic_all['tier_label'] == 'A']

# 找出棱彩阶有 S 级的英雄
prismatic_s_champions = set(df_prismatic_s['championid'].unique())
# 找出棱彩阶没有 S 级但有 A 级的英雄 → 这些英雄回退到 A 级
prismatic_a_fallback = df_prismatic_a[~df_prismatic_a['championid'].isin(prismatic_s_champions)]
fallback_champions = set(prismatic_a_fallback['championid'].unique())

# 合并棱彩阶：S 级 + 回退的 A 级
df_prismatic_filtered = pd.concat([df_prismatic_s, prismatic_a_fallback], ignore_index=True)

# 合并黄金 + 棱彩
df_filtered = pd.concat([df_gold_s, df_prismatic_filtered], ignore_index=True)

print(f"\n📊 过滤后黄金阶+棱彩阶符文:")
print(f"   黄金+棱彩总数 (popular>0): {len(df_gold_prismatic)}")
print(f"   黄金阶 S 级: {len(df_gold_s)}")
print(f"   棱彩阶 S 级: {len(df_prismatic_s)} ({len(prismatic_s_champions)} 个英雄)")
print(f"   棱彩阶 A 级回退: {len(prismatic_a_fallback)} ({len(fallback_champions)} 个英雄)")
print(f"   合计: {len(df_filtered)}")
print(f"   按稀有度分布:\n{df_filtered['rarity_label'].value_counts().to_string()}")
print(f"   按 tier_label 分布:\n{df_filtered['tier_label'].value_counts().to_string()}")

if fallback_champions:
    fallback_names = df_prismatic_a[df_prismatic_a['championid'].isin(fallback_champions)][['championid','champion_name']].drop_duplicates()
    print(f"\n🔄 棱彩阶回退到 A 级的英雄 ({len(fallback_champions)} 个):")
    for _, r in fallback_names.iterrows():
        print(f"   - {r['champion_name']}")

# ============================================================
# 3. 对每个英雄、每个稀有度，找出 Popular 最高和 Performance 最高的符文
# ============================================================
new_augments = []

# 构建现有表的 (championid, augment_id) 集合，用于去重
existing_pairs = set(zip(df_existing['championid'], df_existing['augment_id']))
print(f"\n现有表中的 (英雄, 符文) 组合数: {len(existing_pairs)}")

added_count = 0
already_exists_count = 0
skipped_count = 0

for rarity_val, rarity_name in [(4, "黄金"), (8, "棱彩")]:
    df_rarity = df_filtered[df_filtered['rarity'] == rarity_val]
    
    for champion_id in df_rarity['championid'].unique():
        champ_data = df_rarity[df_rarity['championid'] == champion_id]
        champion_name = champ_data.iloc[0]['champion_name']
        actual_tier = champ_data.iloc[0]['tier_label']
        
        if len(champ_data) == 0:
            continue
        
        # 判断是否是回退的 A 级
        is_fallback = (rarity_val == 8 and champion_id in fallback_champions)
        tier_suffix = "A级回退" if is_fallback else ""
        
        # 找 Popular 最高的
        top_popular = champ_data.loc[champ_data['popular'].idxmax()]
        
        # 找 Performance 最高的
        top_performance = champ_data.loc[champ_data['performance'].idxmax()]
        
        for row, reason_base in [(top_popular, f"OPGG_{rarity_name}_人气最高"),
                            (top_performance, f"OPGG_{rarity_name}_表现最高")]:
            reason = f"{reason_base}_{tier_suffix}" if tier_suffix else reason_base
            pair = (int(row['championid']), int(row['augment_id']))
            if pair not in existing_pairs:
                new_augments.append({
                    'dtstatdate': int(row['dtstatdate']),
                    'championid': int(row['championid']),
                    'champion_name': row['champion_name'],
                    'augment_id': int(row['augment_id']),
                    'augment_key': row['augment_key'],
                    'augment_name': row['augment_name'],
                    'tier': int(row['tier']),
                    'tier_label': row['tier_label'],
                    'rarity': int(row['rarity']),
                    'rarity_label': row['rarity_label'],
                    'performance': row['performance'],
                    'popular': row['popular'],
                    'win_rate': '',
                    'show_rate': '',
                    'pick_rank': '',
                    'filter_reason': reason,
                })
                existing_pairs.add(pair)
                added_count += 1
            else:
                already_exists_count += 1

print(f"\n📊 筛选结果:")
print(f"   新增符文数: {added_count}")
print(f"   已存在（跳过）: {already_exists_count}")

# ============================================================
# 4. 分析新增符文
# ============================================================
if new_augments:
    df_new = pd.DataFrame(new_augments)
    
    print(f"\n📊 新增符文详情:")
    print(f"   按 filter_reason 分布:")
    print(f"{df_new['filter_reason'].value_counts().to_string()}")
    print(f"\n   按 rarity_label 分布:")
    print(f"{df_new['rarity_label'].value_counts().to_string()}")
    print(f"\n   按 tier_label 分布:")
    print(f"{df_new['tier_label'].value_counts().to_string()}")
    
    # 检查是否有 popular 很低的
    print(f"\n   Popular 分布:")
    print(f"   min: {df_new['popular'].min()}")
    print(f"   median: {df_new['popular'].median()}")
    print(f"   mean: {df_new['popular'].mean():.2f}")
    print(f"   max: {df_new['popular'].max()}")
    
    # ============================================================
    # 5. 合并并保存
    # ============================================================
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    
    # 按英雄排序
    df_combined = df_combined.sort_values(
        ['champion_name', 'rarity', 'pick_rank'], 
        na_position='last'
    ).reset_index(drop=True)
    
    # 保存 CSV
    csv_path = os.path.join(BASE_DIR, "s_tier_filtered_augments.csv")
    df_combined.to_csv(csv_path, index=False)
    print(f"\n✅ 已保存 CSV: {csv_path}")
    print(f"   总行数: {len(df_combined)} (原有 {len(df_existing)} + 新增 {len(df_new)})")
    
    # 保存 xlsx
    xlsx_path = os.path.join(BASE_DIR, "s_tier_filtered_augments.xlsx")
    df_combined.to_excel(xlsx_path, index=False, engine='openpyxl')
    print(f"✅ 已保存 XLSX: {xlsx_path}")
    
    # 输出新增符文的完整列表概览
    print(f"\n📋 新增符文示例（人气最高 - 前10）:")
    pop_rows = df_new[df_new['filter_reason'].str.contains('人气最高')].nlargest(10, 'popular')
    print(pop_rows[['champion_name','augment_name','rarity_label','tier_label','performance','popular','filter_reason']].to_string(index=False))
    
    print(f"\n📋 新增符文示例（表现最高 - 前10）:")
    perf_rows = df_new[df_new['filter_reason'].str.contains('表现最高')].nlargest(10, 'performance')
    print(perf_rows[['champion_name','augment_name','rarity_label','tier_label','performance','popular','filter_reason']].to_string(index=False))
    
    # 统计每个英雄新增了多少个符文
    new_per_champ = df_new.groupby('champion_name').size().reset_index(name='new_count')
    print(f"\n📊 每个英雄新增符文数分布:")
    print(f"{new_per_champ['new_count'].value_counts().sort_index().to_string()}")
    print(f"   共涉及 {len(new_per_champ)} 个英雄")
    
else:
    print("\n⚠️ 没有新增符文，所有候选符文都已存在于现有表中。")

print("\n🎉 完成!")
