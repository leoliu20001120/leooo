# -*- coding: utf-8 -*-
"""
参数调优模拟器 v2
新增：WR 排名保护机制 (WR Top Bonus)

思路：在每个等级的分类阶段增加一步——
  对该英雄的全局 WR Top5 符文，在其所在等级的分数上加一个 bonus，
  帮助它们跨过推荐阈值。

这样做的好处：
  1. 不改变推荐总数（仍然每等级5-6个）
  2. 只影响 WR Top5 的符文（精准打击）
  3. 保持公式框架不变，只是增加一个后处理步骤
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
from recommend.scoring_engine import ScoringEngine, WEIGHT_PROFILES
from recommend.blacktech_matcher import BlacktechMatcher

print("=" * 80)
print("  参数调优模拟器 v2 (含 WR 排名保护)")
print("=" * 80)

# 加载数据
dl = DataLoader()
dl.load_all()
engine = ScoringEngine(dl)

base = os.path.dirname(os.path.abspath(__file__))
aid_path = os.path.join(base, "output", "raw", "augment_id_map.json")
AUGMENT_ID_MAP = {}
AUGMENT_NAME_TO_ID = {}
if os.path.exists(aid_path):
    with open(aid_path, "r", encoding="utf-8") as f:
        AUGMENT_ID_MAP = json.load(f)
    AUGMENT_NAME_TO_ID = {v: k for k, v in AUGMENT_ID_MAP.items()}

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

AUGMENTS_BY_LEVEL = {"白银": [], "黄金": [], "棱彩": []}
for name, info in dl.augment_info.items():
    level = info.get("等级", "")
    if level in AUGMENTS_BY_LEVEL:
        if name in AUGMENT_NAME_TO_ID or name in AUGMENT_ID_MAP.values():
            AUGMENTS_BY_LEVEL[level].append(name)

def _get_augment_cn(aug_id):
    clean_id = str(int(float(aug_id))) if '.' in str(aug_id) else str(aug_id)
    return AUGMENT_ID_MAP.get(clean_id, None)

# 预计算
print("\n预计算英雄符文数据...")
t0 = time.time()
bt_matcher = BlacktechMatcher(dl)

HERO_DATA_CACHE = {}  # hero_name -> {aug_name -> {...}}

for idx, h in enumerate(HERO_LIST):
    hero_name = h["name"]
    hero_id = h["id"]
    if (idx + 1) % 50 == 0:
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

            wr = dl.get_augment_winrate(aug_name, hero_id)
            pr_raw = dl.get_augment_pickrate(aug_name, hero_id)
            ugc = dl.get_ugc_score(aug_name)
            ugc_count = dl.get_ugc_sample_count(aug_name)

            wr_norm = engine.normalize_winrate(wr)
            pr_norm = engine.normalize_pickrate(pr_raw)
            ugc_norm = engine.normalize_ugc(ugc, ugc_count)

            hero_augs[aug_name] = {
                "level": level, "wr": wr, "pr": pr_raw,
                "bt": bt_bonus, "syn": syn_bonus,
                "wr_norm": wr_norm, "pr_norm": pr_norm, "ugc_norm": ugc_norm,
            }

    HERO_DATA_CACHE[hero_name] = hero_augs

print(f"  预计算完成 ({time.time() - t0:.1f}s)")


def simulate_v2(pr_threshold, top_n, target_rec, min_rec, max_rec,
                wr_weight_mult=1.0, wr_top_bonus=0):
    """
    带 WR 排名保护的模拟

    新增参数:
        wr_top_bonus: WR Top N 符文在其所在等级的额外加分
                      只在该等级内分类时生效，不影响全局排名
    """
    W_wr = WEIGHT_PROFILES["standard"]["W_winrate"] * wr_weight_mult
    W_pr = WEIGHT_PROFILES["standard"]["W_pickrate"]
    W_ugc = WEIGHT_PROFILES["standard"]["W_ugc"]

    violations = []
    heroes_with_violation = set()
    r2_violations = 0
    r3_violations = 0

    for h in HERO_LIST:
        hero_name = h["name"]
        hero_augs = HERO_DATA_CACHE.get(hero_name, {})
        if not hero_augs:
            continue

        # 第一步：计算所有符文的基础分数（不含 WR top bonus）
        all_items = []
        for aug_name, data in hero_augs.items():
            base_score = (
                data["wr_norm"] * W_wr
                + data["pr_norm"] * W_pr
                + data["ugc_norm"] * W_ugc
            )
            bt_capped = min(data["bt"], 20)
            syn_capped = min(data["syn"], 10)
            score = max(0, base_score + bt_capped + syn_capped)
            all_items.append({
                "aug": aug_name, "level": data["level"],
                "score": round(score, 1), "wr": data["wr"],
                "pr": data["pr"], "bt": bt_capped, "syn": syn_capped,
                "logo": "",
            })

        # 第二步：PR 过滤 + WR 排名
        filtered_items = [it for it in all_items if it["pr"] > pr_threshold]
        wr_sorted = sorted(filtered_items, key=lambda x: -x["wr"])
        top_wr_augs = set(item["aug"] for item in wr_sorted[:top_n])

        # 第三步：对 WR Top N 的符文加 bonus（在分数上直接加）
        if wr_top_bonus > 0:
            for item in all_items:
                if item["aug"] in top_wr_augs:
                    item["score"] = round(item["score"] + wr_top_bonus, 1)

        # 第四步：按等级分组，重新排序和分类
        by_level = defaultdict(list)
        for item in all_items:
            by_level[item["level"]].append(item)

        all_recommended = set()
        all_refresh = set()
        all_logos = {}

        for level in ["白银", "黄金", "棱彩"]:
            items = by_level[level]
            items.sort(key=lambda x: -x["score"])

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

                refresh_idx = max(0, int(len(items) * 0.8))
                refresh_threshold = items[refresh_idx]["score"] if refresh_idx < len(items) else items[-1]["score"]

                for i, item in enumerate(items):
                    if item["score"] >= recommend_th and i < actual_rec_count:
                        item["logo"] = "推荐选取"
                    elif item["score"] < refresh_threshold:
                        item["logo"] = "建议刷新"
                    else:
                        item["logo"] = "值得考虑"

            for it in items:
                if it["logo"] == "推荐选取":
                    all_recommended.add(it["aug"])
                elif it["logo"] == "建议刷新":
                    all_refresh.add(it["aug"])
                if it["aug"] not in all_logos:
                    all_logos[it["aug"]] = it["logo"]
                elif it["logo"] == "推荐选取":
                    all_logos[it["aug"]] = "推荐选取"

        # Rule 1 检查
        top_wr_list = wr_sorted[:top_n]
        for rank, item in enumerate(top_wr_list, 1):
            if item["aug"] not in all_recommended:
                violations.append({
                    "hero": hero_name, "aug": item["aug"], "level": item["level"],
                    "wr_rank": rank, "wr": round(item["wr"], 4),
                    "pr": round(item["pr"], 6), "score": round(item["score"], 2),
                    "actual_logo": all_logos.get(item["aug"], item["logo"]),
                    "bt": round(item.get("bt", 0), 2), "syn": round(item.get("syn", 0), 2),
                })
                heroes_with_violation.add(hero_name)

        # Rule 2
        if len(wr_sorted) >= 20:
            for item in wr_sorted[-20:]:
                if item["aug"] in all_recommended:
                    r2_violations += 1

        # Rule 3
        if len(wr_sorted) >= 10:
            for item in wr_sorted[-10:]:
                if item["aug"] not in all_refresh:
                    r3_violations += 1

    return {
        "r1_count": len(violations),
        "r1_heroes": len(heroes_with_violation),
        "r2_count": r2_violations,
        "r3_count": r3_violations,
        "violations": violations,
    }


# ==================== 搜索 ====================
print("\n" + "=" * 80)
print("  参数搜索 v2（含 WR Top Bonus）")
print("=" * 80)

# 搜索空间
PR_THRESHOLDS = [0, 0.001, 0.005, 0.01, 0.02]
TOP_N = 5  # 固定 Top5
TARGET_RECS = [5, 6]
WR_MULTS = [1.0, 1.2, 1.5]
WR_BONUSES = [0, 5, 10, 15, 20, 25, 30, 35, 40]  # WR Top5 额外加分

results = []
total = len(PR_THRESHOLDS) * len(TARGET_RECS) * len(WR_MULTS) * len(WR_BONUSES)
idx = 0
t_start = time.time()

print(f"搜索空间: {total} 种组合")

for pr_th in PR_THRESHOLDS:
    for rec in TARGET_RECS:
        min_rec = max(4, rec - 1)
        max_rec = rec + 1
        for wr_m in WR_MULTS:
            for wr_b in WR_BONUSES:
                idx += 1
                if idx % 30 == 0 or idx == 1:
                    elapsed = time.time() - t_start
                    eta = elapsed / idx * (total - idx) if idx > 0 else 0
                    print(f"  [{idx}/{total}] PR={pr_th}, Rec={rec}, WR×{wr_m}, Bonus={wr_b} (ETA: {eta:.0f}s)")

                result = simulate_v2(pr_th, TOP_N, rec, min_rec, max_rec, wr_m, wr_b)
                results.append({
                    "pr_threshold": pr_th, "top_n": TOP_N,
                    "target_rec": rec, "min_rec": min_rec, "max_rec": max_rec,
                    "wr_weight_mult": wr_m, "wr_top_bonus": wr_b,
                    "r1_count": result["r1_count"], "r1_heroes": result["r1_heroes"],
                    "r2_count": result["r2_count"], "r3_count": result["r3_count"],
                })

print(f"\n搜索完成! 耗时 {time.time() - t_start:.1f}s")

# ==================== 结果 ====================
print("\n" + "=" * 80)
print("  搜索结果")
print("=" * 80)

zero_r1 = [r for r in results if r["r1_count"] == 0]
print(f"\n🎯 Rule1=0 的组合: {len(zero_r1)}/{len(results)}")

if zero_r1:
    # 按「最小改动」排序: 优先推荐数不变(5) → Bonus 最小 → PR 阈值最低 → WR 倍率最小
    zero_r1.sort(key=lambda x: (x["target_rec"], x["wr_top_bonus"], x["pr_threshold"], x["wr_weight_mult"]))

    print(f"\n  ✅ Rule1=0 的最优组合（最小改动优先）:")
    print(f"  {'PR阈值':>8} | {'推荐数':>4} | {'WR倍率':>5} | {'WR Bonus':>8} | "
          f"{'R1':>3} | {'R2':>3} | {'R3':>3}")
    print(f"  {'-'*55}")
    shown = set()
    for r in zero_r1[:30]:
        key = (r["target_rec"], r["wr_top_bonus"], r["pr_threshold"])
        if key in shown:
            continue
        shown.add(key)
        print(f"  {r['pr_threshold']:>8.3f} | {r['target_rec']:>4} | "
              f"{r['wr_weight_mult']:>5.1f} | {r['wr_top_bonus']:>8} | "
              f"{r['r1_count']:>3} | {r['r2_count']:>3} | {r['r3_count']:>3}")

    # 找到同时满足 R1=0 且 R2=0 且 R3 最低的
    best_all = [r for r in zero_r1 if r["r2_count"] == 0]
    if best_all:
        best_all.sort(key=lambda x: (x["r3_count"], x["target_rec"], x["wr_top_bonus"]))
        print(f"\n  🏆 同时满足 R1=0 且 R2=0 的最优组合:")
        for r in best_all[:10]:
            print(f"    PR={r['pr_threshold']}, Rec={r['target_rec']}, "
                  f"WR×{r['wr_weight_mult']}, Bonus={r['wr_top_bonus']} → "
                  f"R1={r['r1_count']}, R2={r['r2_count']}, R3={r['r3_count']}")
else:
    print("  ❌ 未找到 R1=0 的组合")

# 显示所有结果排序
print(f"\n  全部组合排序（R1最少）:")
results.sort(key=lambda x: (x["r1_count"], x["r2_count"], x["r3_count"], x["wr_top_bonus"]))
print(f"  {'PR阈值':>8} | {'推荐数':>4} | {'WR倍率':>5} | {'Bonus':>6} | "
      f"{'R1':>3} | {'R1英雄':>5} | {'R2':>3} | {'R3':>3}")
print(f"  {'-'*60}")
for r in results[:30]:
    print(f"  {r['pr_threshold']:>8.3f} | {r['target_rec']:>4} | "
          f"{r['wr_weight_mult']:>5.1f} | {r['wr_top_bonus']:>6} | "
          f"{r['r1_count']:>3} | {r['r1_heroes']:>5} | {r['r2_count']:>3} | {r['r3_count']:>3}")

# ==================== 推荐方案详细验证 ====================
if zero_r1:
    # 选最优方案
    best = best_all[0] if best_all else zero_r1[0]
    print(f"\n\n{'='*80}")
    print(f"  🏆 推荐方案详细验证")
    print(f"{'='*80}")
    print(f"  PR 阈值: {best['pr_threshold']}")
    print(f"  Top N: {best['top_n']}")
    print(f"  每等级推荐数: {best['target_rec']} (min={best['min_rec']}, max={best['max_rec']})")
    print(f"  WR 权重倍率: {best['wr_weight_mult']}")
    print(f"  WR Top Bonus: {best['wr_top_bonus']}")
    print(f"  Rule1: {best['r1_count']}, Rule2: {best['r2_count']}, Rule3: {best['r3_count']}")

    # 重新运行获取详细数据
    detail = simulate_v2(
        best['pr_threshold'], best['top_n'],
        best['target_rec'], best['min_rec'], best['max_rec'],
        best['wr_weight_mult'], best['wr_top_bonus']
    )
    print(f"\n  验证结果: R1={detail['r1_count']}, R2={detail['r2_count']}, R3={detail['r3_count']}")
    if detail['violations']:
        print(f"  残留违规:")
        for v in detail['violations']:
            print(f"    {v['hero']} - {v['aug']} (Top{v['wr_rank']}, WR={v['wr']*100:.1f}%, "
                  f"PR={v['pr']:.4f}, Score={v['score']:.1f}, {v['level']})")

    # 保存结果
    save_data = {
        "best_params": best,
        "all_results": results,
        "best_violations": detail["violations"],
    }
    save_path = os.path.join(base, "output", "tune_params_v2_result.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {save_path}")

print("\n" + "=" * 80)
print("  调优完成!")
print("=" * 80)
