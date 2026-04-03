# -*- coding: utf-8 -*-
"""
评分机制验证脚本 v2
修正口径：
- 胜率排名：每个英雄所有等级合并后的全局排名
- 推荐范围：三个等级的推荐合并（约15-18个）
- 刷新范围：三个等级的刷新合并

验证规则：
1. 每个英雄全局胜率前10的符文 → 必须出现在所有等级的推荐范围之内
2. 每个英雄全局胜率倒数20的符文 → 不应出现在任何等级的推荐范围之内  
3. 每个英雄全局胜率倒数10的符文 → 都应出现在建议刷新范围内
"""
import sys
import os
import json
import logging

logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine, load_entertainment_pool
from recommend import scoring_engine as se_module
from recommend.blacktech_matcher import BlacktechMatcher

print("=" * 80)
print("  AI Coach 评分机制验证 v2（全局胜率口径）")
print("=" * 80)

# ==================== 数据加载 ====================
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


def calc_hero_all_levels(hero_name):
    """为一个英雄计算标准模式下所有等级的符文评分和分类
    
    返回：
    - by_level: {等级: [items]}  每个等级内的评分和分类
    - all_items_with_wr: [{aug, level, wr, score, logo, bt, syn}]  所有符文合并的列表
    """
    hero_id = None
    for h in HERO_LIST:
        if h["name"] == hero_name:
            hero_id = h["id"]
            break
    if not hero_id:
        return {}, []

    bt_matcher = BlacktechMatcher(dl)
    streak = 0
    refresh_pct = 20.0

    # 构建该英雄有数据的符文集合
    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    target_rec = 5
    min_rec = 4
    max_rec = 6
    target_rec = max(min_rec, min(max_rec, target_rec))

    by_level = {}
    all_items = []  # 所有等级合并

    for level, augs in AUGMENTS_BY_LEVEL.items():
        items = []
        level_augs = [a for a in augs if a in hero_aug_set] if hero_aug_set else augs
        for aug_name in level_augs:
            bt_result = bt_matcher.match(aug_name, hero_name, stage=1, selected_augments=[])
            bt_bonus = bt_result.get("bonus", 0)
            syn_bonus = bt_result.get("synergy_bonus", 0)

            score, detail = engine.calc_final_score(
                aug_name, hero_id, streak, bt_bonus, 1, level,
                synergy_bonus=syn_bonus
            )
            wr = detail.get("win_rate_raw", 0)

            items.append({
                "aug": aug_name,
                "level": level,
                "score": score,
                "wr": wr,
                "logo": "",
                "bt": detail.get("blacktech_bonus", 0),
                "syn": detail.get("synergy_bonus", 0),
            })

        items.sort(key=lambda x: -x["score"])

        # 后评分自适应分类
        if items:
            rec_idx = min(target_rec - 1, len(items) - 1)
            recommend_th = items[rec_idx]["score"]
            actual_rec_count = target_rec
            for i in range(target_rec, len(items)):
                if items[i]["score"] >= recommend_th:
                    actual_rec_count = i + 1
                else:
                    break
            actual_rec_count = min(actual_rec_count, max_rec)
            recommend_th = items[actual_rec_count - 1]["score"] if actual_rec_count <= len(items) else items[-1]["score"]

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

    return by_level, all_items


# ==================== 验证逻辑 ====================
print(f"\n英雄总数: {len(HERO_LIST)}")
print(f"符文分布: 白银={len(AUGMENTS_BY_LEVEL['白银'])}, "
      f"黄金={len(AUGMENTS_BY_LEVEL['黄金'])}, "
      f"棱彩={len(AUGMENTS_BY_LEVEL['棱彩'])}")
print(f"\n开始验证...\n")

violations_rule1 = []
violations_rule2 = []
violations_rule3 = []

heroes_with_r1_violation = set()
heroes_with_r2_violation = set()
heroes_with_r3_violation = set()

total_heroes = len(HERO_LIST)

# 统计每个英雄的推荐数
hero_recommend_counts = []

for idx, h in enumerate(HERO_LIST):
    hero_name = h["name"]
    if (idx + 1) % 20 == 0 or idx == 0:
        print(f"  进度: {idx + 1}/{total_heroes} ({hero_name})")

    by_level, all_items = calc_hero_all_levels(hero_name)
    
    if not all_items:
        continue

    # === 全局胜率排名（跨等级） ===
    wr_sorted = sorted(all_items, key=lambda x: -x["wr"])
    
    # === 合并所有等级的推荐/刷新集合 ===
    all_recommended = set()  # 所有等级中被标记为"推荐选取"的符文
    all_refresh = set()      # 所有等级中被标记为"建议刷新"的符文
    all_logos = {}           # aug_name → logo（跨等级）
    
    for level, items in by_level.items():
        for it in items:
            if it["logo"] == "推荐选取":
                all_recommended.add(it["aug"])
            elif it["logo"] == "建议刷新":
                all_refresh.add(it["aug"])
            # 记录每个符文的logo（如果在某个等级被推荐了，就算推荐）
            if it["aug"] not in all_logos:
                all_logos[it["aug"]] = it["logo"]
            elif it["logo"] == "推荐选取":
                all_logos[it["aug"]] = "推荐选取"
    
    hero_recommend_counts.append({
        "hero": hero_name,
        "total_recommended": len(all_recommended),
        "total_refresh": len(all_refresh),
        "total_augs": len(wr_sorted),
    })

    # ===== 规则1: 全局胜率前10 → 必须在任一等级的推荐范围内 =====
    top10_wr = wr_sorted[:10]
    for rank, item in enumerate(top10_wr, 1):
        aug_name = item["aug"]
        if aug_name not in all_recommended:
            violations_rule1.append({
                "hero": hero_name,
                "aug": aug_name,
                "level": item["level"],
                "wr_rank": rank,
                "wr": round(item["wr"], 4),
                "score": round(item["score"], 2),
                "actual_logo": all_logos.get(aug_name, item["logo"]),
                "bt": round(item.get("bt", 0), 2),
                "syn": round(item.get("syn", 0), 2),
            })
            heroes_with_r1_violation.add(hero_name)

    # ===== 规则2: 全局胜率倒数20 → 不应在任何等级的推荐范围内 =====
    if len(wr_sorted) >= 20:
        bottom20_wr = wr_sorted[-20:]
        for i, item in enumerate(bottom20_wr):
            aug_name = item["aug"]
            actual_rank = len(wr_sorted) - 20 + i + 1
            if aug_name in all_recommended:
                violations_rule2.append({
                    "hero": hero_name,
                    "aug": aug_name,
                    "level": item["level"],
                    "wr_rank": actual_rank,
                    "total_augs": len(wr_sorted),
                    "wr": round(item["wr"], 4),
                    "score": round(item["score"], 2),
                    "actual_logo": "推荐选取",
                    "bt": round(item.get("bt", 0), 2),
                    "syn": round(item.get("syn", 0), 2),
                })
                heroes_with_r2_violation.add(hero_name)

    # ===== 规则3: 全局胜率倒数10 → 必须在建议刷新范围内 =====
    if len(wr_sorted) >= 10:
        bottom10_wr = wr_sorted[-10:]
        for i, item in enumerate(bottom10_wr):
            aug_name = item["aug"]
            actual_rank = len(wr_sorted) - 10 + i + 1
            if aug_name not in all_refresh:
                violations_rule3.append({
                    "hero": hero_name,
                    "aug": aug_name,
                    "level": item["level"],
                    "wr_rank": actual_rank,
                    "total_augs": len(wr_sorted),
                    "wr": round(item["wr"], 4),
                    "score": round(item["score"], 2),
                    "actual_logo": all_logos.get(aug_name, item["logo"]),
                    "bt": round(item.get("bt", 0), 2),
                    "syn": round(item.get("syn", 0), 2),
                })
                heroes_with_r3_violation.add(hero_name)

# ==================== 输出结果 ====================
print("\n" + "=" * 80)
print("  验证结果汇总（全局胜率口径 v2）")
print("=" * 80)

# 统计每个英雄平均推荐数
avg_rec = sum(h["total_recommended"] for h in hero_recommend_counts) / len(hero_recommend_counts) if hero_recommend_counts else 0
print(f"\n📊 验证范围: {total_heroes} 个英雄")
print(f"  每个英雄平均推荐数: {avg_rec:.1f} 个（三个等级合并）")
print(f"  推荐数范围: {min(h['total_recommended'] for h in hero_recommend_counts)}"
      f" ~ {max(h['total_recommended'] for h in hero_recommend_counts)}")

# 规则1
print(f"\n{'=' * 60}")
print(f"📌 规则1: 全局胜率前10 → 必须在推荐范围内")
print(f"   （三个等级合并推荐约{avg_rec:.0f}个，前10理应被覆盖）")
print(f"{'=' * 60}")
print(f"  违规数: {len(violations_rule1)} 条（涉及 {len(heroes_with_r1_violation)}/{total_heroes} 个英雄）")

if violations_rule1:
    # 按英雄分组显示
    from collections import defaultdict
    r1_by_hero = defaultdict(list)
    for v in violations_rule1:
        r1_by_hero[v["hero"]].append(v)
    
    print(f"\n  共 {len(r1_by_hero)} 个英雄有违规:")
    print(f"  {'英雄':<10} {'违规数':>4} {'详情'}")
    print(f"  {'-' * 70}")
    for hero, vs in sorted(r1_by_hero.items(), key=lambda x: -len(x[1])):
        augs_str = ", ".join(
            f"{v['aug']}(Top{v['wr_rank']},WR={v['wr']*100:.1f}%,{v['level']},{v['actual_logo']})"
            for v in sorted(vs, key=lambda x: x['wr_rank'])
        )
        print(f"  {hero:<10} {len(vs):>4}   {augs_str}")
else:
    print(f"\n  ✅ 全部通过！所有英雄胜率前10的符文均在推荐范围内。")

# 规则2
print(f"\n{'=' * 60}")
print(f"📌 规则2: 全局胜率倒数20 → 不应在推荐范围内")
print(f"{'=' * 60}")
print(f"  违规数: {len(violations_rule2)} 条（涉及 {len(heroes_with_r2_violation)}/{total_heroes} 个英雄）")

if violations_rule2:
    r2_by_hero = defaultdict(list)
    for v in violations_rule2:
        r2_by_hero[v["hero"]].append(v)
    
    print(f"\n  共 {len(r2_by_hero)} 个英雄有违规:")
    print(f"  {'英雄':<10} {'违规数':>4} {'详情'}")
    print(f"  {'-' * 70}")
    for hero, vs in sorted(r2_by_hero.items(), key=lambda x: -len(x[1])):
        augs_str = ", ".join(
            f"{v['aug']}(排名{v['wr_rank']}/{v['total_augs']},WR={v['wr']*100:.1f}%,{v['level']})"
            for v in sorted(vs, key=lambda x: x['wr_rank'])
        )
        print(f"  {hero:<10} {len(vs):>4}   {augs_str}")
else:
    print(f"\n  ✅ 全部通过！")

# 规则3
print(f"\n{'=' * 60}")
print(f"📌 规则3: 全局胜率倒数10 → 必须在建议刷新范围内")
print(f"{'=' * 60}")
print(f"  违规数: {len(violations_rule3)} 条（涉及 {len(heroes_with_r3_violation)}/{total_heroes} 个英雄）")

if violations_rule3:
    r3_by_hero = defaultdict(list)
    for v in violations_rule3:
        r3_by_hero[v["hero"]].append(v)
    
    print(f"\n  共 {len(r3_by_hero)} 个英雄有违规:")
    print(f"  {'英雄':<10} {'违规数':>4} {'详情'}")
    print(f"  {'-' * 70}")
    for hero, vs in sorted(r3_by_hero.items(), key=lambda x: -len(x[1])):
        augs_str = ", ".join(
            f"{v['aug']}(排名{v['wr_rank']}/{v['total_augs']},WR={v['wr']*100:.1f}%,{v['level']},{v['actual_logo']})"
            for v in sorted(vs, key=lambda x: x['wr_rank'])
        )
        print(f"  {hero:<10} {len(vs):>4}   {augs_str}")
else:
    print(f"\n  ✅ 全部通过！")

# 总结
print(f"\n{'=' * 80}")
print(f"  总结")
print(f"{'=' * 80}")
total_violations = len(violations_rule1) + len(violations_rule2) + len(violations_rule3)
print(f"  总违规数: {total_violations}")
print(f"  规则1 (全局胜率Top10→推荐): {len(violations_rule1)} 条, {len(heroes_with_r1_violation)}/{total_heroes} 英雄违规")
print(f"  规则2 (全局胜率Bot20→非推荐): {len(violations_rule2)} 条, {len(heroes_with_r2_violation)}/{total_heroes} 英雄违规")
print(f"  规则3 (全局胜率Bot10→刷新): {len(violations_rule3)} 条, {len(heroes_with_r3_violation)}/{total_heroes} 英雄违规")

# 保存详细结果
output = {
    "summary": {
        "total_heroes": total_heroes,
        "avg_recommended_per_hero": round(avg_rec, 1),
        "total_violations": total_violations,
        "rule1_violations": len(violations_rule1),
        "rule1_heroes": len(heroes_with_r1_violation),
        "rule2_violations": len(violations_rule2),
        "rule2_heroes": len(heroes_with_r2_violation),
        "rule3_violations": len(violations_rule3),
        "rule3_heroes": len(heroes_with_r3_violation),
    },
    "hero_recommend_counts": hero_recommend_counts,
    "rule1_violations": violations_rule1,
    "rule2_violations": violations_rule2,
    "rule3_violations": violations_rule3,
}

output_path = os.path.join(base, "output", "validation_result_v2.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n详细结果已保存到: {output_path}")
