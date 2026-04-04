# -*- coding: utf-8 -*-
"""
参数调优模拟器
完整重算评分和排名，搜索使 Rule1 Top5 违规 = 0 的最优参数组合

搜索空间:
- PR 阈值 (MIN_PICKRATE_FOR_WR_RANK): 过滤 WR 排名中低 PR 符文
- Top N: 检查 WR 前 N 名（用户要求 Top5）
- 推荐数 (TARGET_RECOMMEND_PER_LEVEL): 每个等级的推荐数量
- WR 权重倍率: 在当前权重基础上调整胜率权重
"""
import sys
import os
import json
import logging
import time
from collections import defaultdict

logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine, load_entertainment_pool
from recommend import scoring_engine as se_module
from recommend.blacktech_matcher import BlacktechMatcher

print("=" * 80)
print("  参数调优模拟器 - 搜索最优参数组合")
print("=" * 80)

# ==================== 数据加载 ====================
print("\n加载数据...")
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


# 预计算所有英雄的符文集合和黑科技加成（这是最耗时的部分，缓存起来）
print("预计算英雄符文数据和黑科技加成...")
t0 = time.time()

HERO_DATA_CACHE = {}  # hero_name -> {aug_name -> {level, wr, pr, bt, syn, base_score, wr_norm, pr_norm, ugc_norm}}

bt_matcher = BlacktechMatcher(dl)

for idx, h in enumerate(HERO_LIST):
    hero_name = h["name"]
    hero_id = h["id"]
    if (idx + 1) % 40 == 0:
        print(f"  预计算: {idx + 1}/{len(HERO_LIST)}")

    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    hero_augs = {}
    for level, augs in AUGMENTS_BY_LEVEL.items():
        level_augs = [a for a in augs if a in hero_aug_set] if hero_aug_set else augs
        for aug_name in level_augs:
            bt_result = bt_matcher.match(aug_name, hero_name, stage=1, selected_augments=[])
            bt_bonus = bt_result.get("bonus", 0)
            syn_bonus = bt_result.get("synergy_bonus", 0)

            # 获取原始数据
            wr = dl.get_augment_winrate(aug_name, hero_id)
            pr_raw = dl.get_augment_pickrate(aug_name, hero_id)
            ugc = dl.get_ugc_score(aug_name)
            ugc_count = dl.get_ugc_sample_count(aug_name)

            # 归一化
            wr_norm = engine.normalize_winrate(wr)
            pr_norm = engine.normalize_pickrate(pr_raw)
            ugc_norm = engine.normalize_ugc(ugc, ugc_count)

            hero_augs[aug_name] = {
                "level": level,
                "wr": wr,
                "pr": pr_raw,
                "bt": bt_bonus,
                "syn": syn_bonus,
                "wr_norm": wr_norm,
                "pr_norm": pr_norm,
                "ugc_norm": ugc_norm,
            }

    HERO_DATA_CACHE[hero_name] = hero_augs

print(f"  预计算完成 ({time.time() - t0:.1f}s)")


def simulate(pr_threshold, top_n, target_rec, min_rec, max_rec, wr_weight_mult=1.0):
    """
    用指定参数模拟验证
    
    Args:
        pr_threshold: 选取率过滤阈值
        top_n: 检查 WR 前 N 名
        target_rec: 每等级目标推荐数
        min_rec: 每等级最少推荐数
        max_rec: 每等级最多推荐数
        wr_weight_mult: 胜率权重倍率（1.0 = 不变）
    
    Returns:
        {violations_count, heroes_count, violations_detail, r2_count, r3_count}
    """
    # 获取当前权重
    from recommend.scoring_engine import WEIGHT_PROFILES
    W_wr = WEIGHT_PROFILES["standard"]["W_winrate"] * wr_weight_mult
    W_pr = WEIGHT_PROFILES["standard"]["W_pickrate"]
    W_ugc = WEIGHT_PROFILES["standard"]["W_ugc"]

    violations = []
    heroes_with_violation = set()
    r2_violations = 0
    r3_violations = 0
    total_filtered = 0

    for h in HERO_LIST:
        hero_name = h["name"]
        hero_augs = HERO_DATA_CACHE.get(hero_name, {})
        if not hero_augs:
            continue

        # 按等级分组计算分数和分类
        by_level = {}
        all_items = []

        for level in ["白银", "黄金", "棱彩"]:
            items = []
            for aug_name, data in hero_augs.items():
                if data["level"] != level:
                    continue

                # 重新计算分数（使用调整后的权重）
                base_score = (
                    data["wr_norm"] * W_wr
                    + data["pr_norm"] * W_pr
                    + data["ugc_norm"] * W_ugc
                )
                bt_capped = min(data["bt"], 20)
                syn_capped = min(data["syn"], 10)
                score = max(0, base_score + bt_capped + syn_capped)

                items.append({
                    "aug": aug_name,
                    "level": level,
                    "score": round(score, 1),
                    "wr": data["wr"],
                    "pr": data["pr"],
                    "logo": "",
                    "bt": bt_capped,
                    "syn": syn_capped,
                })

            items.sort(key=lambda x: -x["score"])

            # 后评分自适应分类
            if items:
                _target_rec = max(min_rec, min(max_rec, target_rec))
                rec_idx = min(_target_rec - 1, len(items) - 1)
                recommend_th = items[rec_idx]["score"]
                actual_rec_count = _target_rec
                for i in range(_target_rec, len(items)):
                    if items[i]["score"] >= recommend_th:
                        actual_rec_count = i + 1
                    else:
                        break
                actual_rec_count = min(actual_rec_count, max_rec)
                recommend_th = items[actual_rec_count - 1]["score"] if actual_rec_count <= len(items) else items[-1]["score"]

                refresh_pct = 20.0
                refresh_idx = max(0, int(len(items) * (1 - refresh_pct / 100.0)))
                refresh_threshold = items[refresh_idx]["score"] if refresh_idx < len(items) else items[-1]["score"]

                for i, item in enumerate(items):
                    if item["score"] >= recommend_th and i < actual_rec_count:
                        item["logo"] = "推荐选取"
                    elif item["score"] < refresh_threshold:
                        item["logo"] = "建议刷新"
                    else:
                        item["logo"] = "值得考虑"

            by_level[level] = items
            all_items.extend(items)

        # PR 过滤 + WR 排名
        filtered_items = [it for it in all_items if it["pr"] > pr_threshold]
        filtered_count = len(all_items) - len(filtered_items)
        total_filtered += filtered_count

        wr_sorted = sorted(filtered_items, key=lambda x: -x["wr"])

        # 合并推荐/刷新集合
        all_recommended = set()
        all_refresh = set()
        all_logos = {}

        for level, items in by_level.items():
            for it in items:
                if it["logo"] == "推荐选取":
                    all_recommended.add(it["aug"])
                elif it["logo"] == "建议刷新":
                    all_refresh.add(it["aug"])
                if it["aug"] not in all_logos:
                    all_logos[it["aug"]] = it["logo"]
                elif it["logo"] == "推荐选取":
                    all_logos[it["aug"]] = "推荐选取"

        # Rule 1: Top N WR 必须在推荐范围
        top_wr = wr_sorted[:top_n]
        for rank, item in enumerate(top_wr, 1):
            if item["aug"] not in all_recommended:
                violations.append({
                    "hero": hero_name,
                    "aug": item["aug"],
                    "level": item["level"],
                    "wr_rank": rank,
                    "wr": round(item["wr"], 4),
                    "pr": round(item["pr"], 6),
                    "score": round(item["score"], 2),
                    "actual_logo": all_logos.get(item["aug"], item["logo"]),
                    "bt": round(item.get("bt", 0), 2),
                    "syn": round(item.get("syn", 0), 2),
                })
                heroes_with_violation.add(hero_name)

        # Rule 2: Bottom 20 不应在推荐范围
        if len(wr_sorted) >= 20:
            for item in wr_sorted[-20:]:
                if item["aug"] in all_recommended:
                    r2_violations += 1

        # Rule 3: Bottom 10 应在刷新范围
        if len(wr_sorted) >= 10:
            for item in wr_sorted[-10:]:
                if item["aug"] not in all_refresh:
                    r3_violations += 1

    return {
        "r1_count": len(violations),
        "r1_heroes": len(heroes_with_violation),
        "r2_count": r2_violations,
        "r3_count": r3_violations,
        "total_filtered": total_filtered,
        "violations": violations,
    }


# ==================== 参数搜索 ====================
print("\n" + "=" * 80)
print("  开始参数搜索")
print("=" * 80)

# 搜索空间
PR_THRESHOLDS = [0, 0.001, 0.002, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
TOP_N_VALUES = [5]  # 用户明确要求 Top5
TARGET_REC_VALUES = [5, 6, 7]  # 每等级推荐数
WR_WEIGHT_MULTS = [1.0, 1.1, 1.2, 1.3, 1.5]  # WR 权重倍率

results = []
total_combos = len(PR_THRESHOLDS) * len(TOP_N_VALUES) * len(TARGET_REC_VALUES) * len(WR_WEIGHT_MULTS)
combo_idx = 0

print(f"\n搜索空间: {total_combos} 种组合")
print(f"  PR 阈值: {PR_THRESHOLDS}")
print(f"  Top N: {TOP_N_VALUES}")
print(f"  每等级推荐数: {TARGET_REC_VALUES}")
print(f"  WR 权重倍率: {WR_WEIGHT_MULTS}")

t_start = time.time()

for pr_th in PR_THRESHOLDS:
    for top_n in TOP_N_VALUES:
        for target_rec in TARGET_REC_VALUES:
            min_rec = max(4, target_rec - 1)
            max_rec = target_rec + 1
            for wr_mult in WR_WEIGHT_MULTS:
                combo_idx += 1
                if combo_idx % 20 == 0 or combo_idx == 1:
                    elapsed = time.time() - t_start
                    eta = elapsed / combo_idx * (total_combos - combo_idx) if combo_idx > 0 else 0
                    print(f"  [{combo_idx}/{total_combos}] PR={pr_th}, Top{top_n}, "
                          f"Rec={target_rec}, WR×{wr_mult} (ETA: {eta:.0f}s)")

                result = simulate(pr_th, top_n, target_rec, min_rec, max_rec, wr_mult)
                results.append({
                    "pr_threshold": pr_th,
                    "top_n": top_n,
                    "target_rec": target_rec,
                    "min_rec": min_rec,
                    "max_rec": max_rec,
                    "wr_weight_mult": wr_mult,
                    "r1_count": result["r1_count"],
                    "r1_heroes": result["r1_heroes"],
                    "r2_count": result["r2_count"],
                    "r3_count": result["r3_count"],
                    "total_filtered": result["total_filtered"],
                })

print(f"\n搜索完成! 耗时 {time.time() - t_start:.1f}s")

# ==================== 结果汇总 ====================
print("\n" + "=" * 80)
print("  搜索结果汇总")
print("=" * 80)

# 找到 R1=0 的组合
zero_r1 = [r for r in results if r["r1_count"] == 0]
print(f"\n🎯 Rule1=0 的组合: {len(zero_r1)}/{len(results)}")

if zero_r1:
    # 按「最小改动」排序：优先推荐数不变(5) → PR阈值最低 → WR权重倍率最小
    zero_r1.sort(key=lambda x: (x["target_rec"], x["pr_threshold"], x["wr_weight_mult"]))

    print(f"\n  最优组合（最小改动优先）:")
    print(f"  {'PR阈值':>8} | {'TopN':>4} | {'推荐数':>6} | {'WR倍率':>6} | "
          f"{'R1':>3} | {'R2':>3} | {'R3':>3} | {'过滤数':>6}")
    print(f"  {'-'*65}")
    for r in zero_r1[:20]:
        print(f"  {r['pr_threshold']:>8.3f} | {r['top_n']:>4} | {r['target_rec']:>6} | "
              f"{r['wr_weight_mult']:>6.1f} | {r['r1_count']:>3} | {r['r2_count']:>3} | "
              f"{r['r3_count']:>3} | {r['total_filtered']:>6}")
else:
    print("\n  ❌ 没有找到 R1=0 的组合，需要扩大搜索范围")

# 即使 R1≠0，也显示最优组合
print(f"\n  全部组合排序（R1最少 → PR最低 → 推荐数最少）:")
results.sort(key=lambda x: (x["r1_count"], x["pr_threshold"], x["target_rec"], x["wr_weight_mult"]))
print(f"  {'PR阈值':>8} | {'TopN':>4} | {'推荐数':>6} | {'WR倍率':>6} | "
      f"{'R1':>3} | {'R1英雄':>6} | {'R2':>3} | {'R3':>3} | {'过滤数':>6}")
print(f"  {'-'*75}")
for r in results[:30]:
    print(f"  {r['pr_threshold']:>8.3f} | {r['top_n']:>4} | {r['target_rec']:>6} | "
          f"{r['wr_weight_mult']:>6.1f} | {r['r1_count']:>3} | {r['r1_heroes']:>6} | "
          f"{r['r2_count']:>3} | {r['r3_count']:>3} | {r['total_filtered']:>6}")

# ==================== 保存最佳方案的详细违规 ====================
if zero_r1:
    best = zero_r1[0]
    print(f"\n\n🏆 推荐方案:")
    print(f"  PR 阈值: {best['pr_threshold']}")
    print(f"  Top N: {best['top_n']}")
    print(f"  每等级推荐数: {best['target_rec']} (min={best['min_rec']}, max={best['max_rec']})")
    print(f"  WR 权重倍率: {best['wr_weight_mult']}")
    print(f"  Rule1 违规: {best['r1_count']}")
    print(f"  Rule2 违规: {best['r2_count']}")
    print(f"  Rule3 违规: {best['r3_count']}")
    print(f"  过滤数: {best['total_filtered']}")

    # 重新跑一遍获取详细违规数据
    detail_result = simulate(
        best['pr_threshold'], best['top_n'],
        best['target_rec'], best['min_rec'], best['max_rec'],
        best['wr_weight_mult']
    )

    # 保存结果
    save_data = {
        "best_params": best,
        "all_results": results,
        "best_detail_violations": detail_result["violations"],
    }
    save_path = os.path.join(base, "output", "tune_params_result.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {save_path}")
else:
    # 保存全部搜索结果
    save_data = {"all_results": results}
    save_path = os.path.join(base, "output", "tune_params_result.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {save_path}")

print("\n" + "=" * 80)
print("  调优完成!")
print("=" * 80)
