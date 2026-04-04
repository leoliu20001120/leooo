# -*- coding: utf-8 -*-
"""
打印 wr_top_bonus=0 时的所有 Rule 1 badcase
参数：pr_threshold=0, target_rec=6, wr_weight_mult=1.0, wr_top_bonus=0（v3.9 其他参数不变）
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
print("  Rule 1 Badcase 详情（wr_top_bonus=0）")
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

# 参数：v3.9 其他不变，仅 wr_top_bonus=0
PR_THRESHOLD = 0
TOP_N = 5
TARGET_REC = 6
MIN_REC = 5
MAX_REC = 7
WR_WEIGHT_MULT = 1.0
WR_TOP_BONUS = 0  # 关闭 bonus

W_wr = WEIGHT_PROFILES["standard"]["W_winrate"] * WR_WEIGHT_MULT
W_pr = WEIGHT_PROFILES["standard"]["W_pickrate"]
W_ugc = WEIGHT_PROFILES["standard"]["W_ugc"]

print(f"\n参数: PR={PR_THRESHOLD}, TopN={TOP_N}, Rec={TARGET_REC}, WR×{WR_WEIGHT_MULT}, Bonus={WR_TOP_BONUS}")
print(f"权重: W_wr={W_wr:.4f}, W_pr={W_pr:.4f}, W_ugc={W_ugc:.4f}")

# 模拟并收集详细 badcase
all_violations = []

for h in HERO_LIST:
    hero_name = h["name"]
    hero_augs = HERO_DATA_CACHE.get(hero_name, {})
    if not hero_augs:
        continue

    # 计算所有符文的分数
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

    # PR 过滤 + WR 排名
    filtered_items = [it for it in all_items if it["pr"] > PR_THRESHOLD]
    wr_sorted = sorted(filtered_items, key=lambda x: -x["wr"])
    top_wr_augs = set(item["aug"] for item in wr_sorted[:TOP_N])

    # 不加 bonus（WR_TOP_BONUS=0）

    # 按等级分组排序分类
    by_level = defaultdict(list)
    for item in all_items:
        by_level[item["level"]].append(item)

    all_recommended = set()
    all_logos = {}

    for level in ["白银", "黄金", "棱彩"]:
        items = by_level[level]
        items.sort(key=lambda x: -x["score"])

        if items:
            _target_rec = max(MIN_REC, min(MAX_REC, TARGET_REC))
            rec_idx = min(_target_rec - 1, len(items) - 1)
            recommend_th = items[rec_idx]["score"]
            actual_rec_count = _target_rec
            for i in range(_target_rec, len(items)):
                if items[i]["score"] >= recommend_th:
                    actual_rec_count = i + 1
                else:
                    break
            actual_rec_count = min(actual_rec_count, MAX_REC)
            recommend_th = items[actual_rec_count - 1]["score"] if actual_rec_count <= len(items) else items[-1]["score"]

            for i, item in enumerate(items):
                if item["score"] >= recommend_th and i < actual_rec_count:
                    item["logo"] = "推荐选取"
                else:
                    item["logo"] = "其他"

        for it in items:
            if it["logo"] == "推荐选取":
                all_recommended.add(it["aug"])
            if it["aug"] not in all_logos:
                all_logos[it["aug"]] = it["logo"]
            elif it["logo"] == "推荐选取":
                all_logos[it["aug"]] = "推荐选取"

    # Rule 1 检查
    top_wr_list = wr_sorted[:TOP_N]
    for rank, item in enumerate(top_wr_list, 1):
        if item["aug"] not in all_recommended:
            # 找这个符文在其等级内的排名
            level_items = by_level[item["level"]]
            level_rank = None
            level_total = len(level_items)
            for i, it in enumerate(level_items):
                if it["aug"] == item["aug"]:
                    level_rank = i + 1
                    break

            # 找该等级推荐阈值
            rec_items = [it for it in level_items if it["logo"] == "推荐选取"]
            rec_threshold = rec_items[-1]["score"] if rec_items else 0
            score_gap = round(rec_threshold - item["score"], 1)

            all_violations.append({
                "hero": hero_name,
                "aug": item["aug"],
                "level": item["level"],
                "wr_rank": rank,
                "wr": round(item["wr"], 4),
                "pr": round(item["pr"], 6),
                "score": round(item["score"], 1),
                "bt": round(item.get("bt", 0), 1),
                "syn": round(item.get("syn", 0), 1),
                "actual_logo": all_logos.get(item["aug"], "其他"),
                "level_rank": level_rank,
                "level_total": level_total,
                "rec_threshold": round(rec_threshold, 1),
                "score_gap": score_gap,  # 负数=差多少分才能进推荐
            })

# 输出结果
print(f"\n{'=' * 100}")
print(f"  Rule 1 违规总数: {len(all_violations)} 条")
print(f"{'=' * 100}")

# 按英雄分组
r1_by_hero = defaultdict(list)
for v in all_violations:
    r1_by_hero[v["hero"]].append(v)

print(f"\n涉及 {len(r1_by_hero)} 个英雄\n")

# 打印每个 case
print(f"{'序号':>4} | {'英雄':<8} | {'符文':<16} | {'等级':<4} | {'WR排名':>6} | {'WR':>7} | {'分数':>6} | {'推荐线':>6} | {'差距':>6} | {'等级排名':>8} | {'BT':>4} | {'SYN':>4}")
print("-" * 120)

for i, v in enumerate(sorted(all_violations, key=lambda x: (x["hero"], x["wr_rank"])), 1):
    print(f"{i:>4} | {v['hero']:<8} | {v['aug']:<16} | {v['level']:<4} | "
          f"Top{v['wr_rank']:<4} | {v['wr']*100:>6.1f}% | {v['score']:>6.1f} | "
          f"{v['rec_threshold']:>6.1f} | {v['score_gap']:>+6.1f} | "
          f"{v['level_rank']}/{v['level_total']:<5} | {v['bt']:>4.0f} | {v['syn']:>4.0f}")

# 按英雄汇总
print(f"\n\n{'=' * 80}")
print(f"  按英雄汇总（违规数从多到少）")
print(f"{'=' * 80}\n")

print(f"{'英雄':<10} | {'违规数':>4} | {'违规符文详情'}")
print("-" * 100)
for hero, vs in sorted(r1_by_hero.items(), key=lambda x: -len(x[1])):
    augs_detail = []
    for v in sorted(vs, key=lambda x: x["wr_rank"]):
        augs_detail.append(
            f"{v['aug']}(Top{v['wr_rank']}, WR={v['wr']*100:.1f}%, {v['level']}, "
            f"分数={v['score']:.1f}, 推荐线={v['rec_threshold']:.1f}, 差距={v['score_gap']:+.1f})"
        )
    print(f"{hero:<10} | {len(vs):>4} | {'; '.join(augs_detail)}")

# 统计分析
print(f"\n\n{'=' * 80}")
print(f"  统计分析")
print(f"{'=' * 80}")

gaps = [v["score_gap"] for v in all_violations]
levels = defaultdict(int)
for v in all_violations:
    levels[v["level"]] += 1

print(f"\n  分数差距分布:")
print(f"    差距 ≤ -20: {sum(1 for g in gaps if g <= -20)} 条")
print(f"    差距 -20 ~ -10: {sum(1 for g in gaps if -20 < g <= -10)} 条")
print(f"    差距 -10 ~ -5: {sum(1 for g in gaps if -10 < g <= -5)} 条")
print(f"    差距 -5 ~ 0: {sum(1 for g in gaps if -5 < g <= 0)} 条")
print(f"    差距 > 0: {sum(1 for g in gaps if g > 0)} 条")
print(f"    平均差距: {sum(gaps)/len(gaps):.1f}")
print(f"    最大差距: {min(gaps):.1f}")

print(f"\n  按等级分布:")
for level in ["白银", "黄金", "棱彩"]:
    print(f"    {level}: {levels[level]} 条")

# WR Top 排名分布
ranks = defaultdict(int)
for v in all_violations:
    ranks[v["wr_rank"]] += 1
print(f"\n  按 WR 排名分布:")
for rank in sorted(ranks.keys()):
    print(f"    Top{rank}: {ranks[rank]} 条")

# 保存 JSON
output_path = os.path.join(base, "output", "r1_badcase_no_bonus.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
        "params": {
            "pr_threshold": PR_THRESHOLD,
            "top_n": TOP_N,
            "target_rec": TARGET_REC,
            "wr_weight_mult": WR_WEIGHT_MULT,
            "wr_top_bonus": WR_TOP_BONUS,
        },
        "total_violations": len(all_violations),
        "total_heroes": len(r1_by_hero),
        "violations": all_violations,
    }, f, ensure_ascii=False, indent=2)
print(f"\n详细数据已保存: {output_path}")
