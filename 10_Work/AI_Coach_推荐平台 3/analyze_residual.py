# -*- coding: utf-8 -*-
"""
深入分析残留违规 - 找出 40 条违规的根本原因
在最优参数组合(Rec=7, WR×1.5, PR=0, Top5)下，这40条违规是什么情况
"""
import sys, os, json, time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
logging.basicConfig(level=logging.WARNING)

from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine, WEIGHT_PROFILES
from recommend.blacktech_matcher import BlacktechMatcher

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

# 用最优参数分析具体案例
# 参数: PR=0, Top5, Rec=7, WR×1.5
PR_THRESHOLD = 0
TOP_N = 5
TARGET_REC = 7
MIN_REC = 6
MAX_REC = 8
WR_MULT = 1.5

W_wr = WEIGHT_PROFILES["standard"]["W_winrate"] * WR_MULT
W_pr = WEIGHT_PROFILES["standard"]["W_pickrate"]
W_ugc = WEIGHT_PROFILES["standard"]["W_ugc"]

print(f"权重: W_wr={W_wr:.4f}, W_pr={W_pr:.4f}, W_ugc={W_ugc:.4f}")
print(f"推荐数: target={TARGET_REC}, min={MIN_REC}, max={MAX_REC}")
print()

bt_matcher = BlacktechMatcher(dl)
violations = []

# 挑几个有违规的英雄做详细分析
detailed_heroes = []

for h in HERO_LIST:
    hero_name = h["name"]
    hero_id = h["id"]

    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    by_level = {}
    all_items = []

    for level in ["白银", "黄金", "棱彩"]:
        items = []
        level_augs = [a for a in AUGMENTS_BY_LEVEL[level] if a in hero_aug_set]
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

            base_score = wr_norm * W_wr + pr_norm * W_pr + ugc_norm * W_ugc
            bt_capped = min(bt_bonus, 20)
            syn_capped = min(syn_bonus, 10)
            score = max(0, base_score + bt_capped + syn_capped)

            items.append({
                "aug": aug_name, "level": level, "score": round(score, 1),
                "wr": wr, "pr": pr_raw, "bt": bt_capped, "syn": syn_capped,
                "wr_norm": round(wr_norm, 1), "pr_norm": round(pr_norm, 1),
                "ugc_norm": round(ugc_norm, 1), "logo": "",
            })
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

            refresh_idx = max(0, int(len(items) * 0.8))
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

    filtered_items = [it for it in all_items if it["pr"] > PR_THRESHOLD]
    wr_sorted = sorted(filtered_items, key=lambda x: -x["wr"])

    all_recommended = set()
    all_logos = {}
    for level, items in by_level.items():
        for it in items:
            if it["logo"] == "推荐选取":
                all_recommended.add(it["aug"])
            if it["aug"] not in all_logos:
                all_logos[it["aug"]] = it["logo"]
            elif it["logo"] == "推荐选取":
                all_logos[it["aug"]] = "推荐选取"

    top_wr = wr_sorted[:TOP_N]
    hero_violations = []
    for rank, item in enumerate(top_wr, 1):
        if item["aug"] not in all_recommended:
            hero_violations.append({
                "hero": hero_name, "aug": item["aug"], "level": item["level"],
                "wr_rank": rank, "wr": round(item["wr"], 4), "pr": round(item["pr"], 6),
                "score": round(item["score"], 2), "logo": all_logos.get(item["aug"], item["logo"]),
                "bt": item["bt"], "syn": item["syn"],
                "wr_norm": item["wr_norm"], "pr_norm": item["pr_norm"], "ugc_norm": item["ugc_norm"],
            })
            violations.append(hero_violations[-1])

    if hero_violations:
        # 记录这个英雄的详细推荐情况
        rec_counts = {lv: sum(1 for it in items if it["logo"] == "推荐选取") for lv, items in by_level.items()}
        detailed_heroes.append({
            "hero": hero_name,
            "violations": hero_violations,
            "rec_counts": rec_counts,
            "total_rec": len(all_recommended),
            "by_level": by_level,
        })

print(f"总违规: {len(violations)}, 涉及英雄: {len(detailed_heroes)}")
print()

# 详细分析违规
print("=" * 80)
print("违规详细分析")
print("=" * 80)

# 按符文名聚合
aug_freq = Counter(v["aug"] for v in violations)
print(f"\n违规符文频率:")
for aug, cnt in aug_freq.most_common(20):
    vs = [v for v in violations if v["aug"] == aug]
    avg_pr = sum(v["pr"] for v in vs) / len(vs)
    avg_wr = sum(v["wr"] for v in vs) / len(vs)
    avg_score = sum(v["score"] for v in vs) / len(vs)
    levels = set(v["level"] for v in vs)
    bt_has = sum(1 for v in vs if v["bt"] > 0)
    syn_has = sum(1 for v in vs if v["syn"] > 0)
    print(f"  {aug:<16} ×{cnt:>2}, PR={avg_pr:.4f}, WR={avg_wr:.1f}%, "
          f"Score={avg_score:.1f}, 等级={','.join(levels)}, bt有{bt_has}/{cnt}, syn有{syn_has}/{cnt}")

# 详细看前5个违规英雄
print(f"\n\n{'='*80}")
print("TOP 5 违规英雄的详细推荐情况")
print("="*80)

for dh in detailed_heroes[:5]:
    hero = dh["hero"]
    print(f"\n📌 {hero} (推荐总数: {dh['total_rec']}, 各等级: {dh['rec_counts']})")
    
    for v in dh["violations"]:
        print(f"  ❌ {v['aug']} (Top{v['wr_rank']}, WR={v['wr']*100:.1f}%, PR={v['pr']:.4f}, "
              f"Score={v['score']:.1f}, {v['level']}, bt={v['bt']}, syn={v['syn']})")
    
    # 显示违规符文所在等级的推荐列表（前10名）
    for v in dh["violations"]:
        level = v["level"]
        level_items = dh["by_level"][level]
        print(f"\n  {level} 等级 Top 10 (共{len(level_items)}个):")
        for i, it in enumerate(level_items[:10]):
            marker = "✅" if it["logo"] == "推荐选取" else ("⚠️" if it["aug"] == v["aug"] else "  ")
            print(f"    {marker} #{i+1} {it['aug']:<14} Score={it['score']:<7.1f} "
                  f"WR={it['wr']:.1f}% PR={it['pr']:.4f} bt={it['bt']} syn={it['syn']} "
                  f"(wr_n={it['wr_norm']}, pr_n={it['pr_norm']}, ugc_n={it['ugc_norm']})")

# ==================== 分析根因 ====================
print(f"\n\n{'='*80}")
print("根因分析")
print("="*80)

# 分析：违规符文的 score 与该等级第7名(推荐阈值) 的 score gap
gaps = []
for dh in detailed_heroes:
    for v in dh["violations"]:
        level = v["level"]
        level_items = dh["by_level"][level]
        rec_items = [it for it in level_items if it["logo"] == "推荐选取"]
        if rec_items:
            min_rec_score = min(it["score"] for it in rec_items)
            gap = min_rec_score - v["score"]
            gaps.append({
                "hero": v["hero"], "aug": v["aug"], "level": level,
                "score": v["score"], "min_rec_score": min_rec_score, "gap": gap,
                "pr": v["pr"], "bt": v["bt"], "syn": v["syn"],
            })

if gaps:
    print(f"\n违规符文离推荐阈值的 gap 分析:")
    print(f"  gap 范围: {min(g['gap'] for g in gaps):.1f} ~ {max(g['gap'] for g in gaps):.1f}")
    print(f"  gap 均值: {sum(g['gap'] for g in gaps)/len(gaps):.1f}")
    print(f"  gap 中位数: {sorted(g['gap'] for g in gaps)[len(gaps)//2]:.1f}")
    
    # gap 分桶
    gap_bins = [(0, 5), (5, 10), (10, 20), (20, 50), (50, 100)]
    for lo, hi in gap_bins:
        cnt = sum(1 for g in gaps if lo <= g["gap"] < hi)
        if cnt > 0:
            print(f"  gap [{lo}, {hi}): {cnt} 条")
    
    # 有 synergy bonus 但仍然违规的
    has_bonus = [g for g in gaps if g["bt"] > 0 or g["syn"] > 0]
    print(f"\n  有 bonus 但仍违规: {len(has_bonus)}")
    
    # 关键：这些符文的 PR 对 score 的贡献
    print(f"\n  违规符文 PR 贡献分析（PR_norm × W_pr）:")
    for g in sorted(gaps, key=lambda x: x["gap"])[:10]:
        # 重算 PR 对 score 的贡献
        v_data = [v for v in violations if v["hero"] == g["hero"] and v["aug"] == g["aug"]][0]
        pr_contrib = v_data.get("pr_norm", 0) * W_pr
        wr_contrib = v_data.get("wr_norm", 0) * W_wr
        print(f"    {g['hero']:<10} {g['aug']:<14} gap={g['gap']:<6.1f} "
              f"WR贡献={wr_contrib:.1f} PR贡献={pr_contrib:.1f} PR={g['pr']:.4f}")

print(f"\n\n💡 关键洞察：")
print(f"  这些违规符文的共同特点是：")
print(f"  1. WR 高（全局前5），但 PR 很低 → PR 归一化后对 score 贡献极小")
print(f"  2. bt=0, syn=0（没有黑科技/羁绊加成）")
print(f"  3. 它们在自己等级内排名不够高（被同等级中有 bt/syn 加成的符文挤掉）")
print(f"\n  解决思路：")
print(f"  A. 更激进地提高 PR 阈值（将这些低 PR 符文从 WR 排名中剔除）")
print(f"  B. 引入 WR 保底机制：如果某符文 WR 排名在 Top5，直接给予额外加分")
print(f"  C. 在分类时增加 WR 排名保护：Top5 WR 符文强制加入推荐")
