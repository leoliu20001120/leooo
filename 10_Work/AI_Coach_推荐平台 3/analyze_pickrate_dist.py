# -*- coding: utf-8 -*-
"""
分析 Pick 率分布，用于确定小样本过滤阈值
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine
from recommend.blacktech_matcher import BlacktechMatcher
import logging
logging.basicConfig(level=logging.WARNING)

dl = DataLoader()
dl.load_all()
engine = ScoringEngine(dl)

# 加载符文ID映射
AUGMENT_ID_MAP = {}
AUGMENT_NAME_TO_ID = {}
base = os.path.dirname(os.path.abspath(__file__))
aid_path = os.path.join(base, "output", "raw", "augment_id_map.json")
if os.path.exists(aid_path):
    with open(aid_path, "r", encoding="utf-8") as f:
        AUGMENT_ID_MAP = json.load(f)
    AUGMENT_NAME_TO_ID = {v: k for k, v in AUGMENT_ID_MAP.items()}

# 构建英雄列表
HERO_LIST = []
seen = set()
for (cid_str, aug_name), stats in dl.champion_augment_stats.items():
    cid_clean = str(int(float(cid_str))) if "." in str(cid_str) else str(cid_str)
    if cid_clean in seen:
        continue
    seen.add(cid_clean)
    hero_name = dl.get_champion_name(cid_clean)
    if hero_name and hero_name != cid_clean:
        HERO_LIST.append({"id": cid_clean, "name": hero_name})
HERO_LIST.sort(key=lambda x: x["name"])

# 构建符文等级分组
AUGMENTS_BY_LEVEL = {"白银": [], "黄金": [], "棱彩": []}
AUGMENT_LEVEL_MAP = {}
for name, info in dl.augment_info.items():
    level = info.get("等级", "")
    if level in AUGMENTS_BY_LEVEL:
        if name in AUGMENT_NAME_TO_ID or name in AUGMENT_ID_MAP.values():
            AUGMENTS_BY_LEVEL[level].append(name)
            AUGMENT_LEVEL_MAP[name] = level


def _get_augment_cn(aug_id):
    clean_id = str(int(float(aug_id))) if '.' in str(aug_id) else str(aug_id)
    return AUGMENT_ID_MAP.get(clean_id, None)

# 收集所有英雄的全局胜率 Top10 中的 pick_rate 信息
print("=" * 80)
print("  分析 Pick 率分布（关注全局胜率 Top10 中的小样本问题）")
print("=" * 80)

all_pr_values = []  # 所有英雄×符文的 pick_rate
top10_entries = []  # 全局胜率 Top10 的条目

sample_count = 0
for idx, h in enumerate(HERO_LIST):
    hero_name = h["name"]
    hero_id = h["id"]
    
    bt_matcher = BlacktechMatcher(dl)
    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    all_items = []
    for level, augs in AUGMENTS_BY_LEVEL.items():
        level_augs = [a for a in augs if a in hero_aug_set] if hero_aug_set else augs
        for aug_name in level_augs:
            bt_result = bt_matcher.match(aug_name, hero_name, stage=1, selected_augments=[])
            bt_bonus = bt_result.get("bonus", 0)
            syn_bonus = bt_result.get("synergy_bonus", 0)

            score, detail = engine.calc_final_score(
                aug_name, hero_id, 0, bt_bonus, 1, level,
                synergy_bonus=syn_bonus
            )
            wr = detail.get("win_rate_raw", 0)
            pr = detail.get("pick_rate_raw", 0)

            all_items.append({
                "aug": aug_name,
                "level": level,
                "score": score,
                "wr": wr,
                "pr": pr,
                "hero": hero_name,
            })
            all_pr_values.append(pr)

    if not all_items:
        continue
    
    # 全局胜率排名
    wr_sorted = sorted(all_items, key=lambda x: -x["wr"])
    for rank, item in enumerate(wr_sorted[:10], 1):
        top10_entries.append({
            "hero": item["hero"],
            "aug": item["aug"],
            "level": item["level"],
            "wr": item["wr"],
            "pr": item["pr"],
            "score": item["score"],
            "wr_rank": rank,
        })
    
    sample_count += 1

print(f"\n分析完成: {sample_count} 个英雄")

# 1. 全局 pick_rate 分布
pr_arr = np.array(all_pr_values)
print(f"\n{'=' * 60}")
print(f"  全局 Pick 率分布（英雄×符文，共 {len(pr_arr)} 条）")
print(f"{'=' * 60}")
print(f"  最小值: {pr_arr.min():.4f}%")
print(f"  P1:     {np.percentile(pr_arr, 1):.4f}%")
print(f"  P2:     {np.percentile(pr_arr, 2):.4f}%")
print(f"  P5:     {np.percentile(pr_arr, 5):.4f}%")
print(f"  P10:    {np.percentile(pr_arr, 10):.4f}%")
print(f"  P25:    {np.percentile(pr_arr, 25):.4f}%")
print(f"  中位数: {np.percentile(pr_arr, 50):.4f}%")
print(f"  P75:    {np.percentile(pr_arr, 75):.4f}%")
print(f"  P90:    {np.percentile(pr_arr, 90):.4f}%")
print(f"  P95:    {np.percentile(pr_arr, 95):.4f}%")
print(f"  最大值: {pr_arr.max():.4f}%")
print(f"  均值:   {pr_arr.mean():.4f}%")

# 2. 胜率 Top10 条目中的 pick_rate 分布
top10_pr = [e["pr"] for e in top10_entries]
top10_pr_arr = np.array(top10_pr)
print(f"\n{'=' * 60}")
print(f"  胜率 Top10 条目的 Pick 率分布（共 {len(top10_pr_arr)} 条）")
print(f"{'=' * 60}")
print(f"  最小值: {top10_pr_arr.min():.4f}%")
print(f"  P1:     {np.percentile(top10_pr_arr, 1):.4f}%")
print(f"  P5:     {np.percentile(top10_pr_arr, 5):.4f}%")
print(f"  P10:    {np.percentile(top10_pr_arr, 10):.4f}%")
print(f"  P25:    {np.percentile(top10_pr_arr, 25):.4f}%")
print(f"  中位数: {np.percentile(top10_pr_arr, 50):.4f}%")
print(f"  均值:   {top10_pr_arr.mean():.4f}%")

# 3. 重点：100% 胜率的条目
wr100 = [e for e in top10_entries if e["wr"] >= 99.0]
print(f"\n{'=' * 60}")
print(f"  胜率 ≥ 99% 的 Top10 条目（共 {len(wr100)} 条）")
print(f"{'=' * 60}")
if wr100:
    print(f"  {'英雄':<10} {'符文':<20} {'等级':<4} {'Rank':>4} {'胜率%':>7} {'选取率%':>8} {'分数':>6}")
    print(f"  {'-' * 70}")
    for e in sorted(wr100, key=lambda x: x["pr"]):
        print(f"  {e['hero']:<10} {e['aug']:<20} {e['level']:<4} {e['wr_rank']:>4} {e['wr']:>7.2f} {e['pr']:>8.4f} {e['score']:>6.1f}")
    wr100_pr = [e["pr"] for e in wr100]
    print(f"\n  这些条目的 Pick 率范围: {min(wr100_pr):.4f}% ~ {max(wr100_pr):.4f}%")

# 4. 高胜率低选率：可能的小样本
print(f"\n{'=' * 60}")
print(f"  高胜率(≥65%)且低选率 的 Top10 条目")
print(f"{'=' * 60}")
# 按不同阈值统计
for pr_threshold in [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]:
    low_pr = [e for e in top10_entries if e["wr"] >= 65 and e["pr"] < pr_threshold]
    print(f"\n  选率 < {pr_threshold:.2f}% 且 胜率 ≥ 65%: {len(low_pr)} 条")
    if low_pr and len(low_pr) <= 20:
        for e in sorted(low_pr, key=lambda x: -x["wr"])[:10]:
            print(f"    {e['hero']:<10} {e['aug']:<20} {e['level']:<4} WR={e['wr']:.2f}% PR={e['pr']:.4f}%")

# 5. 不同阈值过滤后对 Top10 的影响
print(f"\n{'=' * 60}")
print(f"  不同 Pick 率阈值对全局胜率 Top10 的过滤影响")
print(f"{'=' * 60}")
for pr_threshold in [0.02, 0.05, 0.10, 0.15, 0.20, 0.30]:
    filtered = [e for e in top10_entries if e["pr"] < pr_threshold]
    affected_heroes = set(e["hero"] for e in filtered)
    print(f"  阈值 {pr_threshold:.2f}%: 过滤掉 {len(filtered)}/{len(top10_entries)} 条 Top10, "
          f"影响 {len(affected_heroes)} 个英雄")
    # 其中 rank=1 的
    rank1_filtered = [e for e in filtered if e["wr_rank"] == 1]
    print(f"    其中 Rank=1 被过滤: {len(rank1_filtered)} 个英雄")
