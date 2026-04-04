# -*- coding: utf-8 -*-
"""
参数调优 v3 - 精细搜索
在 v2 的基础上精细化搜索空间，找到最小 bonus + 最小改动的方案
"""
import sys, os, json, logging, time
from collections import defaultdict

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine, WEIGHT_PROFILES
from recommend.blacktech_matcher import BlacktechMatcher

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
print("预计算...")
bt_matcher = BlacktechMatcher(dl)
HERO_DATA_CACHE = {}

for idx, h in enumerate(HERO_LIST):
    hero_name = h["name"]
    hero_id = h["id"]
    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    hero_augs = {}
    for level, augs in AUGMENTS_BY_LEVEL.items():
        level_augs = [a for a in augs if a in hero_aug_set]
        for aug_name in level_augs:
            bt_result = bt_matcher.match(aug_name, hero_name, stage=1, selected_augments=[])
            wr = dl.get_augment_winrate(aug_name, hero_id)
            pr_raw = dl.get_augment_pickrate(aug_name, hero_id)
            ugc = dl.get_ugc_score(aug_name)
            ugc_count = dl.get_ugc_sample_count(aug_name)
            hero_augs[aug_name] = {
                "level": level, "wr": wr, "pr": pr_raw,
                "bt": bt_result.get("bonus", 0), "syn": bt_result.get("synergy_bonus", 0),
                "wr_norm": engine.normalize_winrate(wr),
                "pr_norm": engine.normalize_pickrate(pr_raw),
                "ugc_norm": engine.normalize_ugc(ugc, ugc_count),
            }
    HERO_DATA_CACHE[hero_name] = hero_augs
print("预计算完成")


def simulate(pr_th, top_n, target_rec, min_rec, max_rec, wr_mult, wr_bonus, pr_filter_wr_rank_only=False):
    """
    pr_filter_wr_rank_only: 如果 True，PR 过滤仅用于 WR 排名（不影响等级内分类）
    """
    W_wr = WEIGHT_PROFILES["standard"]["W_winrate"] * wr_mult
    W_pr = WEIGHT_PROFILES["standard"]["W_pickrate"]
    W_ugc = WEIGHT_PROFILES["standard"]["W_ugc"]

    violations = []
    heroes_with_violation = set()
    r2 = 0
    r3 = 0

    for h in HERO_LIST:
        hero_name = h["name"]
        hero_augs = HERO_DATA_CACHE.get(hero_name, {})
        if not hero_augs:
            continue

        # 计算所有符文分数
        all_items = []
        for aug_name, data in hero_augs.items():
            score = (data["wr_norm"] * W_wr + data["pr_norm"] * W_pr + data["ugc_norm"] * W_ugc
                     + min(data["bt"], 20) + min(data["syn"], 10))
            all_items.append({
                "aug": aug_name, "level": data["level"], "score": round(max(0, score), 1),
                "wr": data["wr"], "pr": data["pr"],
                "bt": min(data["bt"], 20), "syn": min(data["syn"], 10), "logo": "",
            })

        # WR 排名（带 PR 过滤）
        filtered = [it for it in all_items if it["pr"] > pr_th]
        wr_sorted = sorted(filtered, key=lambda x: -x["wr"])
        top_wr_augs = set(item["aug"] for item in wr_sorted[:top_n])

        # WR Top Bonus
        if wr_bonus > 0:
            for item in all_items:
                if item["aug"] in top_wr_augs:
                    item["score"] = round(item["score"] + wr_bonus, 1)

        # 按等级分类
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
                _tr = max(min_rec, min(max_rec, target_rec))
                ri = min(_tr - 1, len(items) - 1)
                rth = items[ri]["score"]
                arc = _tr
                for i in range(_tr, len(items)):
                    if items[i]["score"] >= rth:
                        arc = i + 1
                    else:
                        break
                arc = min(arc, max_rec)
                rth = items[arc - 1]["score"] if arc <= len(items) else items[-1]["score"]
                rfi = max(0, int(len(items) * 0.8))
                rfth = items[rfi]["score"] if rfi < len(items) else items[-1]["score"]
                for i, item in enumerate(items):
                    if item["score"] >= rth and i < arc:
                        item["logo"] = "推荐选取"
                    elif item["score"] < rfth:
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

        for rank, item in enumerate(wr_sorted[:top_n], 1):
            if item["aug"] not in all_recommended:
                violations.append({
                    "hero": hero_name, "aug": item["aug"], "level": item["level"],
                    "wr_rank": rank, "wr": round(item["wr"], 4), "pr": round(item["pr"], 6),
                    "score": round(item["score"], 2), "actual_logo": all_logos.get(item["aug"], item["logo"]),
                    "bt": round(item.get("bt", 0), 2), "syn": round(item.get("syn", 0), 2),
                })
                heroes_with_violation.add(hero_name)

        if len(wr_sorted) >= 20:
            for item in wr_sorted[-20:]:
                if item["aug"] in all_recommended:
                    r2 += 1
        if len(wr_sorted) >= 10:
            for item in wr_sorted[-10:]:
                if item["aug"] not in all_refresh:
                    r3 += 1

    return {
        "r1_count": len(violations), "r1_heroes": len(heroes_with_violation),
        "r2_count": r2, "r3_count": r3, "violations": violations,
    }


# ==================== 精细搜索 ====================
print("\n精细搜索...")

# 从 v2 结果看：PR=0, Rec=6, WR×1.0/1.2/1.5, Bonus=40 都能达到 R1=0
# 现在精细搜索 bonus 范围
results = []
for pr_th in [0]:  # PR=0 最稳
    for rec in [5, 6]:
        min_rec = max(4, rec - 1)
        max_rec = rec + 1
        for wr_m in [1.0, 1.1, 1.2, 1.3, 1.5]:
            for wr_b in range(0, 51, 2):  # bonus 从0到50，步长2
                result = simulate(pr_th, 5, rec, min_rec, max_rec, wr_m, wr_b)
                results.append({
                    "pr_th": pr_th, "rec": rec, "min_rec": min_rec, "max_rec": max_rec,
                    "wr_m": wr_m, "wr_b": wr_b,
                    "r1": result["r1_count"], "r1h": result["r1_heroes"],
                    "r2": result["r2_count"], "r3": result["r3_count"],
                })

print(f"搜索了 {len(results)} 种组合")

# 找 R1=0 的最小 bonus
zero_r1 = [r for r in results if r["r1"] == 0]
print(f"\nR1=0 的组合: {len(zero_r1)}")

if zero_r1:
    # 按 bonus 排序
    zero_r1.sort(key=lambda x: (x["wr_b"], x["rec"], x["wr_m"]))
    print(f"\n最小 bonus 的 R1=0 方案:")
    print(f"  {'Rec':>3} | {'WR倍率':>5} | {'Bonus':>5} | {'R1':>3} | {'R2':>3} | {'R3':>3}")
    print(f"  {'-'*40}")
    for r in zero_r1[:20]:
        print(f"  {r['rec']:>3} | {r['wr_m']:>5.1f} | {r['wr_b']:>5} | {r['r1']:>3} | {r['r2']:>3} | {r['r3']:>3}")

    # 同时 R2=0 的
    zero_r12 = [r for r in zero_r1 if r["r2"] == 0]
    if zero_r12:
        zero_r12.sort(key=lambda x: (x["wr_b"], x["r3"], x["rec"]))
        print(f"\nR1=0 且 R2=0 的最优方案:")
        for r in zero_r12[:10]:
            print(f"  Rec={r['rec']}, WR×{r['wr_m']}, Bonus={r['wr_b']} → R3={r['r3']}")

# 找最低 bonus 到达 R1≤1 和 R1≤2 的方案
for threshold in [0, 1, 2, 3, 5]:
    at_most = [r for r in results if r["r1"] <= threshold and r["r2"] == 0]
    if at_most:
        at_most.sort(key=lambda x: (x["wr_b"], x["rec"]))
        best = at_most[0]
        print(f"\nR1≤{threshold} 且 R2=0 的最小 bonus: Rec={best['rec']}, WR×{best['wr_m']}, "
              f"Bonus={best['wr_b']} → R1={best['r1']}, R3={best['r3']}")

# ==================== 关键问题：R1=1 时残留的是谁？ ====================
print("\n\n" + "=" * 60)
print("R1=1 的方案中，残留的违规是什么？")
print("=" * 60)

# 找 Rec=5, WR×1.0, 最小 bonus 使 R1≤1
for rec_v in [5, 6]:
    for wr_m_v in [1.0, 1.2, 1.5]:
        cands = [r for r in results if r["rec"] == rec_v and r["wr_m"] == wr_m_v and r["r1"] <= 1 and r["r2"] == 0]
        if cands:
            cands.sort(key=lambda x: x["wr_b"])
            best = cands[0]
            if best["r1"] > 0:
                detail = simulate(0, 5, best["rec"], best["min_rec"], best["max_rec"], best["wr_m"], best["wr_b"])
                print(f"\nRec={best['rec']}, WR×{best['wr_m']}, Bonus={best['wr_b']} → R1={best['r1']}")
                for v in detail["violations"]:
                    print(f"  {v['hero']} - {v['aug']} (Top{v['wr_rank']}, WR={v['wr']*100:.1f}%, "
                          f"PR={v['pr']:.4f}, Score={v['score']:.1f}, {v['level']}, "
                          f"bt={v['bt']}, syn={v['syn']})")
