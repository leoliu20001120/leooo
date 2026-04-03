# -*- coding: utf-8 -*-
"""
评分机制验证脚本
验证三个口径：
1. 每个英雄胜率前10的符文，必须出现在推荐范围之内
2. 每个英雄胜率倒数的20个符文，不应该出现在推荐符文之内
3. 每个英雄胜率倒数的10个符文，都应该出现在重随（建议刷新）范围内
"""
import sys
import os
import json
import logging

# 抑制加载日志
logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine, load_entertainment_pool
from recommend import scoring_engine as se_module
from recommend.blacktech_matcher import BlacktechMatcher

print("=" * 80)
print("  AI Coach 评分机制验证")
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


def calc_hero_scores_standard(hero_name):
    """为一个英雄计算标准模式(streak=0)下所有等级的符文评分和分类"""
    hero_id = None
    for h in HERO_LIST:
        if h["name"] == hero_name:
            hero_id = h["id"]
            break
    if not hero_id:
        return {}

    bt_matcher = BlacktechMatcher(dl)
    streak = 0
    refresh_pct = 20.0  # 默认

    # 构建该英雄有数据的符文集合
    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    result = {}
    target_rec = 5
    min_rec = 4
    max_rec = 6
    target_rec = max(min_rec, min(max_rec, target_rec))

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

            # 获取该英雄+该符文的原始胜率（用于胜率排名）
            wr = detail.get("win_rate_raw", 0)

            items.append({
                "aug": aug_name,
                "score": score,
                "wr": wr,
                "logo": "",  # 下面分配
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

        result[level] = items
    return result


# ==================== 验证逻辑 ====================
print(f"\n英雄总数: {len(HERO_LIST)}")
print(f"符文分布: 白银={len(AUGMENTS_BY_LEVEL['白银'])}, "
      f"黄金={len(AUGMENTS_BY_LEVEL['黄金'])}, "
      f"棱彩={len(AUGMENTS_BY_LEVEL['棱彩'])}")
print(f"\n开始验证...\n")

# 收集违规信息
violations_rule1 = []  # 胜率前10不在推荐
violations_rule2 = []  # 胜率倒数20在推荐中
violations_rule3 = []  # 胜率倒数10不在刷新中

total_heroes = len(HERO_LIST)
heroes_with_r1_violation = set()
heroes_with_r2_violation = set()
heroes_with_r3_violation = set()

for idx, h in enumerate(HERO_LIST):
    hero_name = h["name"]
    if (idx + 1) % 20 == 0 or idx == 0:
        print(f"  进度: {idx + 1}/{total_heroes} ({hero_name})")

    scores = calc_hero_scores_standard(hero_name)

    for level, items in scores.items():
        if len(items) < 10:
            continue  # 符文太少跳过

        # 按胜率排序（独立于分数排序）
        wr_sorted = sorted(items, key=lambda x: -x["wr"])

        # 按分数排序的logo已经在items中
        # 建立 aug_name → logo 的映射
        aug_logo_map = {it["aug"]: it["logo"] for it in items}
        aug_score_map = {it["aug"]: it["score"] for it in items}

        # ===== 规则1: 胜率前10必须在推荐范围 =====
        top10_wr = wr_sorted[:10]
        for rank, aug_item in enumerate(top10_wr, 1):
            aug_name = aug_item["aug"]
            logo = aug_logo_map.get(aug_name, "")
            if logo != "推荐选取":
                violations_rule1.append({
                    "hero": hero_name,
                    "level": level,
                    "aug": aug_name,
                    "wr_rank": rank,
                    "wr": round(aug_item["wr"], 2),
                    "score": aug_score_map.get(aug_name, 0),
                    "actual_logo": logo,
                    "bt": aug_item.get("bt", 0),
                    "syn": aug_item.get("syn", 0),
                })
                heroes_with_r1_violation.add(hero_name)

        # ===== 规则2: 胜率倒数20不应在推荐 =====
        bottom20_wr = wr_sorted[-20:] if len(wr_sorted) >= 20 else []
        for rank_from_bottom, aug_item in enumerate(bottom20_wr):
            aug_name = aug_item["aug"]
            logo = aug_logo_map.get(aug_name, "")
            actual_rank = len(wr_sorted) - len(bottom20_wr) + rank_from_bottom + 1
            if logo == "推荐选取":
                violations_rule2.append({
                    "hero": hero_name,
                    "level": level,
                    "aug": aug_name,
                    "wr_rank": actual_rank,
                    "total_augs": len(wr_sorted),
                    "wr": round(aug_item["wr"], 2),
                    "score": aug_score_map.get(aug_name, 0),
                    "actual_logo": logo,
                    "bt": aug_item.get("bt", 0),
                    "syn": aug_item.get("syn", 0),
                })
                heroes_with_r2_violation.add(hero_name)

        # ===== 规则3: 胜率倒数10应在建议刷新 =====
        bottom10_wr = wr_sorted[-10:] if len(wr_sorted) >= 10 else []
        for rank_from_bottom, aug_item in enumerate(bottom10_wr):
            aug_name = aug_item["aug"]
            logo = aug_logo_map.get(aug_name, "")
            actual_rank = len(wr_sorted) - len(bottom10_wr) + rank_from_bottom + 1
            if logo != "建议刷新":
                violations_rule3.append({
                    "hero": hero_name,
                    "level": level,
                    "aug": aug_name,
                    "wr_rank": actual_rank,
                    "total_augs": len(wr_sorted),
                    "wr": round(aug_item["wr"], 2),
                    "score": aug_score_map.get(aug_name, 0),
                    "actual_logo": logo,
                    "bt": aug_item.get("bt", 0),
                    "syn": aug_item.get("syn", 0),
                })
                heroes_with_r3_violation.add(hero_name)

# ==================== 输出结果 ====================
print("\n" + "=" * 80)
print("  验证结果汇总")
print("=" * 80)

print(f"\n📊 验证范围: {total_heroes} 个英雄 × 3 等级")

# 规则1
print(f"\n{'=' * 60}")
print(f"📌 规则1: 胜率前10的符文必须在「推荐选取」范围内")
print(f"{'=' * 60}")
print(f"  违规数: {len(violations_rule1)} 条（涉及 {len(heroes_with_r1_violation)} 个英雄）")
if violations_rule1:
    print(f"\n  {'英雄':<8} {'等级':<4} {'符文':<14} {'胜率排名':<6} {'胜率%':<7} {'分数':<6} {'实际分类':<8} {'黑科技':>4} {'套装':>4}")
    print(f"  {'-' * 75}")
    # 显示所有
    for v in violations_rule1[:100]:
        print(f"  {v['hero']:<8} {v['level']:<4} {v['aug']:<14} "
              f"Top{v['wr_rank']:<4} {v['wr']:<7} {v['score']:<6} {v['actual_logo']:<8} "
              f"{v['bt']:>4} {v['syn']:>4}")
    if len(violations_rule1) > 100:
        print(f"  ... 还有 {len(violations_rule1) - 100} 条")

# 规则2
print(f"\n{'=' * 60}")
print(f"📌 规则2: 胜率倒数20的符文不应在「推荐选取」范围内")
print(f"{'=' * 60}")
print(f"  违规数: {len(violations_rule2)} 条（涉及 {len(heroes_with_r2_violation)} 个英雄）")
if violations_rule2:
    print(f"\n  {'英雄':<8} {'等级':<4} {'符文':<14} {'胜率排名':<10} {'胜率%':<7} {'分数':<6} {'黑科技':>4} {'套装':>4}")
    print(f"  {'-' * 65}")
    for v in violations_rule2[:100]:
        print(f"  {v['hero']:<8} {v['level']:<4} {v['aug']:<14} "
              f"{v['wr_rank']}/{v['total_augs']:<6} {v['wr']:<7} {v['score']:<6} "
              f"{v['bt']:>4} {v['syn']:>4}")
    if len(violations_rule2) > 100:
        print(f"  ... 还有 {len(violations_rule2) - 100} 条")

# 规则3
print(f"\n{'=' * 60}")
print(f"📌 规则3: 胜率倒数10的符文必须在「建议刷新」范围内")
print(f"{'=' * 60}")
print(f"  违规数: {len(violations_rule3)} 条（涉及 {len(heroes_with_r3_violation)} 个英雄）")
if violations_rule3:
    print(f"\n  {'英雄':<8} {'等级':<4} {'符文':<14} {'胜率排名':<10} {'胜率%':<7} {'分数':<6} {'实际分类':<8} {'黑科技':>4} {'套装':>4}")
    print(f"  {'-' * 75}")
    for v in violations_rule3[:100]:
        print(f"  {v['hero']:<8} {v['level']:<4} {v['aug']:<14} "
              f"{v['wr_rank']}/{v['total_augs']:<6} {v['wr']:<7} {v['score']:<6} {v['actual_logo']:<8} "
              f"{v['bt']:>4} {v['syn']:>4}")
    if len(violations_rule3) > 100:
        print(f"  ... 还有 {len(violations_rule3) - 100} 条")

# 总结
print(f"\n{'=' * 80}")
print(f"  总结")
print(f"{'=' * 80}")
total_violations = len(violations_rule1) + len(violations_rule2) + len(violations_rule3)
print(f"  总违规数: {total_violations}")
print(f"  规则1 (胜率Top10→推荐): {len(violations_rule1)} 条, {len(heroes_with_r1_violation)}/{total_heroes} 英雄违规")
print(f"  规则2 (胜率Bot20→非推荐): {len(violations_rule2)} 条, {len(heroes_with_r2_violation)}/{total_heroes} 英雄违规")
print(f"  规则3 (胜率Bot10→刷新): {len(violations_rule3)} 条, {len(heroes_with_r3_violation)}/{total_heroes} 英雄违规")

# 违规原因分析
if violations_rule1:
    print(f"\n📋 规则1违规原因分析:")
    bt_caused = sum(1 for v in violations_rule1 if v['bt'] == 0 and v['syn'] == 0)
    bt_has = sum(1 for v in violations_rule1 if v['bt'] > 0 or v['syn'] > 0)
    print(f"  · 无黑科技/套装加成导致分数不够: {bt_caused} 条")
    print(f"  · 有黑科技/套装加成但仍不够: {bt_has} 条")
    # 按等级统计
    by_level = {}
    for v in violations_rule1:
        by_level.setdefault(v['level'], []).append(v)
    for lv, vs in by_level.items():
        print(f"  · {lv}: {len(vs)} 条违规")

if violations_rule2:
    print(f"\n📋 规则2违规原因分析:")
    bt_caused = sum(1 for v in violations_rule2 if v['bt'] > 0 or v['syn'] > 0)
    no_bt = sum(1 for v in violations_rule2 if v['bt'] == 0 and v['syn'] == 0)
    print(f"  · 黑科技/套装加成拉高分数: {bt_caused} 条")
    print(f"  · 无黑科技但选率/UGC高: {no_bt} 条")

if violations_rule3:
    print(f"\n📋 规则3违规原因分析:")
    as_consider = sum(1 for v in violations_rule3 if v['actual_logo'] == '值得考虑')
    as_recommend = sum(1 for v in violations_rule3 if v['actual_logo'] == '推荐选取')
    print(f"  · 被分类为「值得考虑」: {as_consider} 条")
    print(f"  · 被分类为「推荐选取」: {as_recommend} 条")

# 保存详细结果到JSON
output = {
    "summary": {
        "total_heroes": total_heroes,
        "total_violations": total_violations,
        "rule1_violations": len(violations_rule1),
        "rule1_heroes": len(heroes_with_r1_violation),
        "rule2_violations": len(violations_rule2),
        "rule2_heroes": len(heroes_with_r2_violation),
        "rule3_violations": len(violations_rule3),
        "rule3_heroes": len(heroes_with_r3_violation),
    },
    "rule1_violations": violations_rule1,
    "rule2_violations": violations_rule2,
    "rule3_violations": violations_rule3,
}

output_path = os.path.join(base, "output", "validation_result.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n详细结果已保存到: {output_path}")
