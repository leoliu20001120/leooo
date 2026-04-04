# -*- coding: utf-8 -*-
"""
分析 v3 验证结果中的 Rule1 违规分布
目标：找到最优参数组合使所有英雄 Top5 WR 符文都在推荐范围内
"""
import json
import os
from collections import Counter, defaultdict

base = os.path.dirname(os.path.abspath(__file__))
result_path = os.path.join(base, "output", "validation_result_v3.json")

with open(result_path, "r", encoding="utf-8") as f:
    data = json.load(f)

violations = data["rule1_violations"]
print(f"总 Rule1 违规数: {len(violations)}")
print()

# ==================== 1. Top5 vs Top6-10 分布 ====================
top5 = [v for v in violations if v["wr_rank"] <= 5]
top6_10 = [v for v in violations if v["wr_rank"] > 5]
print("=" * 60)
print("1. 按胜率排名分布 (Top5 vs Top6-10)")
print("=" * 60)
print(f"  Top1-5 违规: {len(top5)} 条")
print(f"  Top6-10 违规: {len(top6_10)} 条")
print()

# Top5 中各排名的分布
rank_dist = Counter(v["wr_rank"] for v in violations)
print("  各排名违规数:")
for rank in sorted(rank_dist.keys()):
    print(f"    Top{rank}: {rank_dist[rank]} 条")
print()

# ==================== 2. PR 分布分析 ====================
print("=" * 60)
print("2. 违规符文的 Pick Rate 分布")
print("=" * 60)

pr_values = [v["pr"] for v in violations]
pr_values_top5 = [v["pr"] for v in top5]

# PR 分桶
pr_bins = [0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0, float('inf')]
pr_labels = ["=0", "(0,0.001]", "(0.001,0.005]", "(0.005,0.01]", "(0.01,0.02]",
             "(0.02,0.05]", "(0.05,0.1]", "(0.1,0.5]", "(0.5,1.0]", ">1.0"]

def pr_bin(pr):
    for i in range(len(pr_bins) - 1):
        if pr_bins[i] <= pr < pr_bins[i + 1]:
            return pr_labels[i]
    return pr_labels[-1]

# 调整: PR 值可能是百分比（如 0.5 表示 0.5%）或小数（如 0.005 表示 0.5%）
# 从数据看 pr 字段的含义
print(f"\n  PR 值范围: min={min(pr_values):.6f}, max={max(pr_values):.6f}")
print(f"  PR 值均值: {sum(pr_values)/len(pr_values):.6f}")
print(f"  PR 值中位数: {sorted(pr_values)[len(pr_values)//2]:.6f}")

# 更细粒度的 PR 分桶
pr_thresholds = [0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 100]

print("\n  全部违规 PR 分桶:")
for i in range(len(pr_thresholds) - 1):
    lo, hi = pr_thresholds[i], pr_thresholds[i + 1]
    count_all = sum(1 for pr in pr_values if lo <= pr < hi)
    count_t5 = sum(1 for pr in pr_values_top5 if lo <= pr < hi)
    if count_all > 0:
        print(f"    PR [{lo:>6.3f}, {hi:>6.3f}): 全部={count_all:>4}, Top5={count_t5:>4}")

# ==================== 3. 累积过滤效果 ====================
print("\n" + "=" * 60)
print("3. 不同 PR 阈值下的过滤效果（累积）")
print("=" * 60)
print(f"  {'PR阈值':>10} | {'剩余全部':>8} | {'剩余Top5':>8} | {'过滤全部':>8} | {'过滤Top5':>8}")
print(f"  {'-'*50}")

for threshold in [0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]:
    remaining_all = [v for v in violations if v["pr"] > threshold]
    remaining_top5 = [v for v in top5 if v["pr"] > threshold]
    filtered_all = len(violations) - len(remaining_all)
    filtered_top5 = len(top5) - len(remaining_top5)
    print(f"  {threshold:>10.3f} | {len(remaining_all):>8} | {len(remaining_top5):>8} | "
          f"{filtered_all:>8} | {filtered_top5:>8}")

# ==================== 4. bt/syn 分布 ====================
print("\n" + "=" * 60)
print("4. 违规符文的黑科技/羁绊加成分布")
print("=" * 60)

bt_zero = sum(1 for v in violations if v["bt"] == 0)
syn_zero = sum(1 for v in violations if v["syn"] == 0)
both_zero = sum(1 for v in violations if v["bt"] == 0 and v["syn"] == 0)
print(f"  bt=0: {bt_zero}/{len(violations)} ({bt_zero/len(violations)*100:.1f}%)")
print(f"  syn=0: {syn_zero}/{len(violations)} ({syn_zero/len(violations)*100:.1f}%)")
print(f"  bt=0 且 syn=0: {both_zero}/{len(violations)} ({both_zero/len(violations)*100:.1f}%)")

# Top5 中的分布
bt_zero_t5 = sum(1 for v in top5 if v["bt"] == 0)
syn_zero_t5 = sum(1 for v in top5 if v["syn"] == 0)
both_zero_t5 = sum(1 for v in top5 if v["bt"] == 0 and v["syn"] == 0)
print(f"\n  Top5 中:")
print(f"  bt=0: {bt_zero_t5}/{len(top5)} ({bt_zero_t5/len(top5)*100:.1f}%)")
print(f"  syn=0: {syn_zero_t5}/{len(top5)} ({syn_zero_t5/len(top5)*100:.1f}%)")
print(f"  bt=0 且 syn=0: {both_zero_t5}/{len(top5)} ({both_zero_t5/len(top5)*100:.1f}%)")

# ==================== 5. 按等级分布 ====================
print("\n" + "=" * 60)
print("5. 违规符文的等级分布")
print("=" * 60)

level_dist_all = Counter(v["level"] for v in violations)
level_dist_top5 = Counter(v["level"] for v in top5)
for level in ["白银", "黄金", "棱彩"]:
    print(f"  {level}: 全部={level_dist_all.get(level, 0)}, Top5={level_dist_top5.get(level, 0)}")

# ==================== 6. 按 actual_logo 分布 ====================
print("\n" + "=" * 60)
print("6. 违规符文当前被标记为什么")
print("=" * 60)

logo_dist_all = Counter(v["actual_logo"] for v in violations)
logo_dist_top5 = Counter(v["actual_logo"] for v in top5)
for logo in ["推荐选取", "值得考虑", "建议刷新"]:
    print(f"  {logo}: 全部={logo_dist_all.get(logo, 0)}, Top5={logo_dist_top5.get(logo, 0)}")

# ==================== 7. 高频违规符文 ====================
print("\n" + "=" * 60)
print("7. 高频违规符文（出现次数最多的符文名称）")
print("=" * 60)

aug_freq_all = Counter(v["aug"] for v in violations)
aug_freq_top5 = Counter(v["aug"] for v in top5)

print("\n  Top 20 高频违规符文（全部）:")
for aug, cnt in aug_freq_all.most_common(20):
    # 获取该符文的典型 PR 和 WR
    typical_v = [v for v in violations if v["aug"] == aug]
    avg_pr = sum(v["pr"] for v in typical_v) / len(typical_v)
    avg_wr = sum(v["wr"] for v in typical_v) / len(typical_v)
    avg_score = sum(v["score"] for v in typical_v) / len(typical_v)
    levels = set(v["level"] for v in typical_v)
    print(f"    {aug:<16} 出现{cnt:>3}次, 平均PR={avg_pr:.4f}, 平均WR={avg_wr*100:.1f}%, "
          f"平均Score={avg_score:.1f}, 等级={','.join(levels)}")

print("\n  Top 20 高频违规符文（Top5）:")
for aug, cnt in aug_freq_top5.most_common(20):
    typical_v = [v for v in top5 if v["aug"] == aug]
    avg_pr = sum(v["pr"] for v in typical_v) / len(typical_v)
    avg_wr = sum(v["wr"] for v in typical_v) / len(typical_v)
    avg_score = sum(v["score"] for v in typical_v) / len(typical_v)
    levels = set(v["level"] for v in typical_v)
    print(f"    {aug:<16} 出现{cnt:>3}次, 平均PR={avg_pr:.4f}, 平均WR={avg_wr*100:.1f}%, "
          f"平均Score={avg_score:.1f}, 等级={','.join(levels)}")

# ==================== 8. 每英雄违规数分布 ====================
print("\n" + "=" * 60)
print("8. 每英雄 Top5 违规数分布")
print("=" * 60)

hero_top5_violations = defaultdict(list)
for v in top5:
    hero_top5_violations[v["hero"]].append(v)

violation_count_dist = Counter(len(vs) for vs in hero_top5_violations.values())
total_heroes = data["summary"]["total_heroes"]
heroes_with_violations = len(hero_top5_violations)
heroes_clean = total_heroes - heroes_with_violations

print(f"  无 Top5 违规的英雄: {heroes_clean}/{total_heroes}")
print(f"  有 Top5 违规的英雄: {heroes_with_violations}/{total_heroes}")
print(f"\n  违规数分布:")
for cnt in sorted(violation_count_dist.keys()):
    print(f"    {cnt} 个违规: {violation_count_dist[cnt]} 个英雄")

# ==================== 9. 分析 Gap：违规符文离推荐阈值差多少 ====================
print("\n" + "=" * 60)
print("9. 违规符文的 score 分析（离第5名差距）")
print("=" * 60)

# 我们需要知道每个英雄每个等级的第5名分数
# 从 hero_recommend_counts 中的 total_recommended 可以推算
# 但更准确的方式是看 score 分布
scores_all = [v["score"] for v in violations]
scores_top5 = [v["score"] for v in top5]
print(f"  全部违规 score: min={min(scores_all):.1f}, max={max(scores_all):.1f}, "
      f"avg={sum(scores_all)/len(scores_all):.1f}")
print(f"  Top5 违规 score: min={min(scores_top5):.1f}, max={max(scores_top5):.1f}, "
      f"avg={sum(scores_top5)/len(scores_top5):.1f}")

# ==================== 10. 模拟：仅改规则为 Top5 ====================
print("\n" + "=" * 60)
print("10. 模拟：如果只检查 Top5（不改 PR 阈值和权重）")
print("=" * 60)

# 当前 violations 中 wr_rank <= 5 的就是 Top5 违规
print(f"  当前 Top10 规则违规: {len(violations)}")
print(f"  改为 Top5 规则违规: {len(top5)}")
print(f"  减少: {len(violations) - len(top5)} ({(len(violations) - len(top5))/len(violations)*100:.1f}%)")

# Top5 违规涉及的英雄数
heroes_t5 = set(v["hero"] for v in top5)
print(f"  Top5 涉及英雄: {len(heroes_t5)}/{total_heroes}")

# ==================== 11. 模拟：Top5 + 不同PR阈值 ====================
print("\n" + "=" * 60)
print("11. 模拟：Top5 + 不同 PR 阈值过滤")
print("=" * 60)
print(f"  注意：PR 阈值过滤的是 WR 排名中的符文，提高阈值会将低PR符文从排名中剔除")
print(f"        从而让其他高PR符文进入Top5，可能减少或增加违规")
print()
print(f"  {'PR阈值':>10} | {'Top5违规':>8} | {'涉及英雄':>8}")
print(f"  {'-'*40}")

for threshold in [0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]:
    remaining = [v for v in top5 if v["pr"] > threshold]
    heroes_remaining = set(v["hero"] for v in remaining)
    print(f"  {threshold:>10.3f} | {len(remaining):>8} | {len(heroes_remaining):>8}")

print("\n" + "=" * 60)
print("分析完成！")
print("=" * 60)
