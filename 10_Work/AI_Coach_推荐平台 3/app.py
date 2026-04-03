# -*- coding: utf-8 -*-
"""
海克斯大乱斗 AI Coach 推荐平台 - Flask 后端
支持动态参数调整 + 实时重新计算评分
"""
import json
import os
import sys
import logging
from flask import Flask, jsonify, request, send_from_directory

# 确保能导入 recommend 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recommend.data_loader import DataLoader
from recommend.scoring_engine import ScoringEngine, load_entertainment_pool
from recommend import scoring_engine as se_module

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("App")

app = Flask(__name__, static_folder="output")

# ==================== 全局数据加载 ====================
dl = DataLoader()
dl.load_all()
engine = ScoringEngine(dl)

# 加载符文ID映射
AUGMENT_ID_MAP = {}  # {数字ID字符串: 中文名}
AUGMENT_NAME_TO_ID = {}  # {中文名: 数字ID字符串}
try:
    base = os.path.dirname(os.path.abspath(__file__))
    aid_path = os.path.join(base, "output", "raw", "augment_id_map.json")
    if os.path.exists(aid_path):
        with open(aid_path, "r", encoding="utf-8") as f:
            AUGMENT_ID_MAP = json.load(f)
        AUGMENT_NAME_TO_ID = {v: k for k, v in AUGMENT_ID_MAP.items()}
        logger.info(f"[启动] 符文ID映射: {len(AUGMENT_ID_MAP)} 条")
except Exception as e:
    logger.warning(f"加载符文ID映射失败: {e}")

# 预构建英雄列表
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

# 预构建符文列表（按等级分组）—— 只包含augment_id_map中存在的符文（本赛季出现的）
AUGMENTS_BY_LEVEL = {"白银": [], "黄金": [], "棱彩": []}
# 同时建立 中文名→等级 映射
AUGMENT_LEVEL_MAP = {}
for name, info in dl.augment_info.items():
    level = info.get("等级", "")
    if level in AUGMENTS_BY_LEVEL:
        # 只保留在augment_id_map中有记录的符文（本赛季出现的）
        if name in AUGMENT_NAME_TO_ID or name in AUGMENT_ID_MAP.values():
            AUGMENTS_BY_LEVEL[level].append(name)
            AUGMENT_LEVEL_MAP[name] = level

# 如果augment_info里的符文不够，从augment_id_map补充
# (有些符文在augment_id_map中但不在augment_info里)
for aid, aname in AUGMENT_ID_MAP.items():
    if aname not in AUGMENT_LEVEL_MAP:
        # 尝试从kiwi等数据推断等级，否则跳过
        pass

logger.info(f"[启动] 本赛季符文: 银{len(AUGMENTS_BY_LEVEL['白银'])}, "
            f"金{len(AUGMENTS_BY_LEVEL['黄金'])}, 棱{len(AUGMENTS_BY_LEVEL['棱彩'])}")

# 加载黑科技数据
BLACKTECH_COMBOS = []
HERO_BLACKTECH = []
try:
    import pandas as pd
    base = os.path.dirname(os.path.abspath(__file__))
    bt_path = os.path.join(base, "output", "黑科技组合分析_v5.xlsx")
    if os.path.exists(bt_path):
        df_combo = pd.read_excel(bt_path, sheet_name="通用黑科技组合")
        for _, row in df_combo.iterrows():
            BLACKTECH_COMBOS.append({
                "label": str(row.get("流派", "") if pd.notna(row.get("流派")) else row.get("组合标签", "")),
                "aug1": str(row.get("符文1", "") if pd.notna(row.get("符文1")) else row.get("符文A", "")),
                "aug2": str(row.get("符文2", "") if pd.notna(row.get("符文2")) else row.get("符文B", "")),
                "pitch": str(row.get("推荐话术", "") if pd.notna(row.get("推荐话术")) else row.get("一句话推荐", "")),
                "hero_type": str(row.get("适配英雄类型", "")),
                "avg_winrate": round(float(row.get("平均胜率", 0) if pd.notna(row.get("平均胜率")) else row.get("组合胜率", 0)), 2),
            })
        df_hbt = pd.read_excel(bt_path, sheet_name="英雄专属黑科技")
        for _, row in df_hbt.iterrows():
            HERO_BLACKTECH.append({
                "hero": str(row.get("英雄", "")),
                "augment": str(row.get("符文", "")),
                "rating": str(row.get("评级", "")),
                "tag": str(row.get("标签", "") if pd.notna(row.get("标签")) else row.get("社区标签", "")),
                "reason": str(row.get("原因", "") if pd.notna(row.get("原因")) else row.get("黑科技原因", "")),
            })
except Exception as e:
    logger.warning(f"加载黑科技数据出错: {e}")

# 娱乐符文池
ENTERTAINMENT_POOL = list(load_entertainment_pool())

logger.info(f"[启动] 英雄={len(HERO_LIST)}, 符文={sum(len(v) for v in AUGMENTS_BY_LEVEL.values())}, "
            f"黑科技组合={len(BLACKTECH_COMBOS)}, 英雄专属={len(HERO_BLACKTECH)}, 娱乐符文={len(ENTERTAINMENT_POOL)}")

# ==================== 当前参数状态 ====================
CURRENT_PARAMS = {
    # 标准模式权重
    "W_winrate": se_module.WEIGHT_PROFILES["standard"]["W_winrate"],
    "W_pickrate": se_module.WEIGHT_PROFILES["standard"]["W_pickrate"],
    "W_ugc": se_module.WEIGHT_PROFILES["standard"]["W_ugc"],
    # 连胜模式权重 (≥3连胜)
    "W_winrate_winning": se_module.WEIGHT_PROFILES["winning"]["W_winrate"],
    "W_pickrate_winning": se_module.WEIGHT_PROFILES["winning"]["W_pickrate"],
    "W_ugc_winning": se_module.WEIGHT_PROFILES["winning"]["W_ugc"],
    # 连败模式权重 (≥3连败)
    "W_winrate_losing": se_module.WEIGHT_PROFILES["losing"]["W_winrate"],
    "W_pickrate_losing": se_module.WEIGHT_PROFILES["losing"]["W_pickrate"],
    "W_ugc_losing": se_module.WEIGHT_PROFILES["losing"]["W_ugc"],
    # 归一化参数
    "WR_FLOOR": se_module.WR_FLOOR,
    "WR_CEILING": se_module.WR_CEILING,
    "PR_FLOOR": se_module.PR_FLOOR,
    "PR_CEILING": se_module.PR_CEILING,
    "PR_SATURATION": se_module.PR_SATURATION,
    "UGC_FLOOR": se_module.UGC_FLOOR,
    "UGC_CEILING": se_module.UGC_CEILING,
    "UGC_MAX": se_module.UGC_MAX,
    "BLACKTECH_BONUS_CAP": se_module.BLACKTECH_BONUS_CAP,
    "SYNERGY_BONUS_CAP": se_module.SYNERGY_BONUS_CAP,
    "HERO_CORRECTION_STRENGTH": se_module.HERO_CORRECTION_STRENGTH,
    "HERO_CORRECTION_MAX": se_module.HERO_CORRECTION_MAX,
    "HERO_CORRECTION_MIN": se_module.HERO_CORRECTION_MIN,
    "TARGET_RECOMMEND_PER_LEVEL": se_module.TARGET_RECOMMEND_PER_LEVEL,
    "MIN_RECOMMEND_PER_LEVEL": se_module.MIN_RECOMMEND_PER_LEVEL,
    "MAX_RECOMMEND_PER_LEVEL": se_module.MAX_RECOMMEND_PER_LEVEL,
    "STRONG_CARD_TOP_PERCENT": se_module.STRONG_CARD_TOP_PERCENT,
    "UGC_CLIP_PERCENTILE": se_module.UGC_CLIP_PERCENTILE,
    "UGC_BAYESIAN_PRIOR_WEIGHT": se_module.UGC_BAYESIAN_PRIOR_WEIGHT,
    "REFRESH_BOTTOM_PERCENT": 20.0,  # 建议刷新：排名最后20%
    "WINNING_DEMOTE_PERCENT": se_module.WINNING_DEMOTE_PERCENT,  # 连胜降级比例
    "ENTERTAINMENT_BOOST": se_module.ENTERTAINMENT_BOOST,  # 娱乐符文加分
}


def _sync_weights_to_params():
    """将 scoring_engine 中 recalc_weights() 计算的权重同步到 CURRENT_PARAMS"""
    CURRENT_PARAMS["W_winrate"] = se_module.WEIGHT_PROFILES["standard"]["W_winrate"]
    CURRENT_PARAMS["W_pickrate"] = se_module.WEIGHT_PROFILES["standard"]["W_pickrate"]
    CURRENT_PARAMS["W_ugc"] = se_module.WEIGHT_PROFILES["standard"]["W_ugc"]
    CURRENT_PARAMS["W_winrate_winning"] = se_module.WEIGHT_PROFILES["winning"]["W_winrate"]
    CURRENT_PARAMS["W_pickrate_winning"] = se_module.WEIGHT_PROFILES["winning"]["W_pickrate"]
    CURRENT_PARAMS["W_ugc_winning"] = se_module.WEIGHT_PROFILES["winning"]["W_ugc"]
    CURRENT_PARAMS["W_winrate_losing"] = se_module.WEIGHT_PROFILES["losing"]["W_winrate"]
    CURRENT_PARAMS["W_pickrate_losing"] = se_module.WEIGHT_PROFILES["losing"]["W_pickrate"]
    CURRENT_PARAMS["W_ugc_losing"] = se_module.WEIGHT_PROFILES["losing"]["W_ugc"]
    # 同步归一化参数
    CURRENT_PARAMS["WR_FLOOR"] = se_module.WR_FLOOR
    CURRENT_PARAMS["WR_CEILING"] = se_module.WR_CEILING
    CURRENT_PARAMS["PR_FLOOR"] = se_module.PR_FLOOR
    CURRENT_PARAMS["PR_CEILING"] = se_module.PR_CEILING
    CURRENT_PARAMS["UGC_FLOOR"] = se_module.UGC_FLOOR
    CURRENT_PARAMS["UGC_CEILING"] = se_module.UGC_CEILING


# 初始化时同步（data_loader已在load_all中调用recalc_weights）
_sync_weights_to_params()


def apply_params(params):
    """将参数写回 scoring_engine 模块全局变量，并清缓存"""
    # 标准模式权重
    se_module.WEIGHT_PROFILES["standard"]["W_winrate"] = params["W_winrate"]
    se_module.WEIGHT_PROFILES["standard"]["W_pickrate"] = params["W_pickrate"]
    se_module.WEIGHT_PROFILES["standard"]["W_ugc"] = params["W_ugc"]
    # 连胜模式权重
    se_module.WEIGHT_PROFILES["winning"]["W_winrate"] = params.get("W_winrate_winning", 0.40)
    se_module.WEIGHT_PROFILES["winning"]["W_pickrate"] = params.get("W_pickrate_winning", 0.15)
    se_module.WEIGHT_PROFILES["winning"]["W_ugc"] = params.get("W_ugc_winning", 0.45)
    # 连败模式权重
    se_module.WEIGHT_PROFILES["losing"]["W_winrate"] = params.get("W_winrate_losing", 0.75)
    se_module.WEIGHT_PROFILES["losing"]["W_pickrate"] = params.get("W_pickrate_losing", 0.15)
    se_module.WEIGHT_PROFILES["losing"]["W_ugc"] = params.get("W_ugc_losing", 0.10)
    # 归一化参数
    se_module.WR_FLOOR = params["WR_FLOOR"]
    se_module.WR_CEILING = params["WR_CEILING"]
    se_module.PR_FLOOR = params.get("PR_FLOOR", 0.1)
    se_module.PR_CEILING = params.get("PR_CEILING", 5.0)
    se_module.PR_SATURATION = params.get("PR_SATURATION", 3.0)
    se_module.UGC_FLOOR = params.get("UGC_FLOOR", 3.0)
    se_module.UGC_CEILING = params.get("UGC_CEILING", 9.0)
    se_module.UGC_MAX = params["UGC_MAX"]
    se_module.BLACKTECH_BONUS_CAP = params["BLACKTECH_BONUS_CAP"]
    se_module.SYNERGY_BONUS_CAP = params.get("SYNERGY_BONUS_CAP", 10)
    se_module.HERO_CORRECTION_STRENGTH = params["HERO_CORRECTION_STRENGTH"]
    se_module.HERO_CORRECTION_MAX = params["HERO_CORRECTION_MAX"]
    se_module.HERO_CORRECTION_MIN = params["HERO_CORRECTION_MIN"]
    se_module.TARGET_RECOMMEND_PER_LEVEL = params["TARGET_RECOMMEND_PER_LEVEL"]
    se_module.MIN_RECOMMEND_PER_LEVEL = params["MIN_RECOMMEND_PER_LEVEL"]
    se_module.MAX_RECOMMEND_PER_LEVEL = params["MAX_RECOMMEND_PER_LEVEL"]
    se_module.STRONG_CARD_TOP_PERCENT = params["STRONG_CARD_TOP_PERCENT"]
    # UGC截断和贝叶斯收缩参数
    se_module.UGC_CLIP_PERCENTILE = params.get("UGC_CLIP_PERCENTILE", 5.0)
    se_module.UGC_BAYESIAN_PRIOR_WEIGHT = params.get("UGC_BAYESIAN_PRIOR_WEIGHT", 30)
    # 连胜娱乐逻辑参数
    se_module.WINNING_DEMOTE_PERCENT = params.get("WINNING_DEMOTE_PERCENT", 50.0)
    se_module.ENTERTAINMENT_BOOST = params.get("ENTERTAINMENT_BOOST", 15.0)
    # 清缓存
    engine._hero_thresholds_cache.clear()


def _get_augment_id(aug_name):
    """中文名 → 数字ID字符串"""
    if aug_name in AUGMENT_NAME_TO_ID:
        return AUGMENT_NAME_TO_ID[aug_name]
    return None


def _get_augment_cn(aug_id):
    """数字ID → 中文名"""
    # 去掉.0后缀
    clean_id = str(int(float(aug_id))) if '.' in str(aug_id) else str(aug_id)
    return AUGMENT_ID_MAP.get(clean_id, None)


def calc_hero_scores(hero_name, streak=0):
    """为一个英雄计算所有等级的符文评分"""
    # 查找英雄ID
    hero_id = None
    for h in HERO_LIST:
        if h["name"] == hero_name:
            hero_id = h["id"]
            break
    if not hero_id:
        return {}

    from recommend.blacktech_matcher import BlacktechMatcher
    bt_matcher = BlacktechMatcher(dl)

    refresh_pct = CURRENT_PARAMS.get("REFRESH_BOTTOM_PERCENT", 20.0)

    # 构建该英雄有数据的符文集合（英雄×符文组合中存在的符文）
    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            # aug_id是数字ID，需要转成中文名
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    result = {}
    target_rec = int(CURRENT_PARAMS.get("TARGET_RECOMMEND_PER_LEVEL", 4))
    min_rec = int(CURRENT_PARAMS.get("MIN_RECOMMEND_PER_LEVEL", 2))
    max_rec = int(CURRENT_PARAMS.get("MAX_RECOMMEND_PER_LEVEL", 6))
    target_rec = max(min_rec, min(max_rec, target_rec))

    for level, augs in AUGMENTS_BY_LEVEL.items():
        items = []
        # 只对该英雄有数据的符文进行评分
        level_augs = [a for a in augs if a in hero_aug_set] if hero_aug_set else augs
        for aug_name in level_augs:
            # 黑科技加成
            bt_result = bt_matcher.match(aug_name, hero_name, stage=1, selected_augments=[])
            bt_bonus = bt_result.get("bonus", 0)
            syn_bonus = bt_result.get("synergy_bonus", 0)

            score, detail = engine.calc_final_score(
                aug_name, hero_id, streak, bt_bonus, 1, level,
                synergy_bonus=syn_bonus
            )
            # determine_tag只判定潜在标签类型（最佳拍档/潜力组合/娱乐），不判定可见性
            tag = engine.determine_tag(aug_name, hero_name, bt_result, streak,
                                       champion_id=hero_id)

            items.append({
                "aug": aug_name,
                "score": score,
                "logo": "",  # 后面统一计算
                "tag": tag,           # 潜在标签（可能不显示）
                "visible_tag": None,  # 实际显示的标签（经过可见性过滤）
                "wr": detail.get("win_rate_raw", 0),
                "pr": detail.get("pick_rate_raw", 0),
                "ugc": detail.get("ugc_score_raw", 0),
                "bt": detail.get("blacktech_bonus", 0),
                "syn": detail.get("synergy_bonus", 0),
                "total_bonus": detail.get("total_bonus", 0),
                "wr_norm": detail.get("win_rate_norm", 0),
                "pr_norm": detail.get("pick_rate_norm", 0),
                "ugc_norm": detail.get("ugc_norm", 0),
                "base": detail.get("base_score", 0),
                "correction": detail.get("hero_correction", 0),
                "multiplier": detail.get("streak_multiplier", 1.0),
                "bt_details": bt_result.get("details", []),
                "bt_tag": bt_result.get("tag", ""),
                "bt_pitch": bt_result.get("pitch", ""),
                "synergy_info": bt_result.get("synergy_info", ""),
                "winning_adjusted": "",
            })
        items.sort(key=lambda x: -x["score"])

        # ====== 后评分自适应分类 (v7.4) ======
        # 在实际评分（含黑科技加成）完成后，直接按排名分类：
        #   - 推荐选取: 前 target_rec 名（确保在 min_rec ~ max_rec 范围内）
        #   - 建议刷新: 底部 refresh_pct% 的符文
        #   - 值得考虑: 中间部分
        # 这样避免了阈值不含黑科技加成导致的推荐数偏多问题
        if items:
            # 计算推荐阈值：取第 target_rec 名的分数
            # 如果第target_rec名与后面的分数相同，则扩展到max_rec
            rec_idx = min(target_rec - 1, len(items) - 1)
            recommend_th = items[rec_idx]["score"]

            # 检查分数相同的情况：如果第target_rec名和后面分数一样，需要一起推荐
            actual_rec_count = target_rec
            for i in range(target_rec, len(items)):
                if items[i]["score"] >= recommend_th:
                    actual_rec_count = i + 1
                else:
                    break
            # 限制推荐数不超过max_rec
            actual_rec_count = min(actual_rec_count, max_rec)
            # 最终推荐阈值
            recommend_th = items[actual_rec_count - 1]["score"] if actual_rec_count <= len(items) else items[-1]["score"]

            # 建议刷新阈值
            refresh_idx = max(0, int(len(items) * (1 - refresh_pct / 100.0)))
            refresh_threshold = items[refresh_idx]["score"] if refresh_idx < len(items) else items[-1]["score"]

            # 分配logo
            for i, item in enumerate(items):
                if item["score"] >= recommend_th and i < actual_rec_count:
                    item["logo"] = "推荐选取"
                elif item["score"] < refresh_threshold:
                    item["logo"] = "建议刷新"
                else:
                    item["logo"] = "值得考虑"

        # ====== 强力单卡标记 (v3.4) ======
        # 在连胜降级之前，先给所有符文判断强力单卡
        # 这样连胜降级时才能把"最佳拍档+强力单卡"后50%一起降级
        # 非连胜时：娱乐标签不生效，强力单卡可以覆盖娱乐
        # 连胜时：娱乐优先级高于强力单卡，不被覆盖
        skip_tags = ("最佳拍档", "潜力组合")
        if streak >= 3:
            skip_tags = ("最佳拍档", "潜力组合", "娱乐")
        for it in items:
            if it["tag"] not in skip_tags:
                if engine._is_strong_card_for_hero(it["aug"], hero_id):
                    it["tag"] = "强力单卡"

        # 连胜时应用娱乐逻辑（分数调整法）
        if streak >= 3:
            items = engine.apply_winning_entertainment(
                items, streak, champion_id=hero_id, augment_level=level
            )
            # 娱乐逻辑会重新排序，需要重新分配logo
            items.sort(key=lambda x: -x["score"])
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

            # 连胜后，新晋推荐位的符文也需要判断强力单卡
            # （娱乐符文提升上来后，如果同时满足TOP15%，保持娱乐标签不变）
            rec_items = [it for it in items if it["logo"] == "推荐选取"]
            for it in rec_items:
                if it["tag"] not in ("最佳拍档", "潜力组合", "娱乐", "强力单卡"):
                    if engine._is_strong_card_for_hero(it["aug"], hero_id):
                        it["tag"] = "强力单卡"

        # ====== 强力单卡补充规则 (v3.6) ======
        # 所有模式统一判定：推荐选取中满足TOP15%且无其他标签的，标记为强力单卡
        # 连胜模式下，强力单卡只可能被降级（后X%降为"值得考虑"），不会凭空升级
        rec_items = [it for it in items if it["logo"] == "推荐选取"]
        for it in rec_items:
            if it["tag"] is None:
                if engine._is_strong_card_for_hero(it["aug"], hero_id):
                    it["tag"] = "强力单卡"

        # ====== 标签可见性控制 (v3.4) ======
        # 标签优先级：最佳拍档 > 潜力组合 > 娱乐(连胜时) > 强力单卡
        # 规则：
        # 1. 所有标签仅在"推荐选取"时可见（"值得考虑"不显示标签）
        # 2. 娱乐标签仅在连胜(streak>=3)时可见
        # 3. 连胜时，娱乐符文即使满足强力单卡条件，也保持"娱乐"标签

        # 应用可见性
        for item in items:
            if item["logo"] != "推荐选取":
                # 非推荐选取的一律不显示标签
                item["visible_tag"] = None
            elif item["tag"] == "娱乐" and streak < 3:
                # 标准模式下不显示娱乐标签
                item["visible_tag"] = None
            else:
                item["visible_tag"] = item["tag"]

        result[level] = items
    return result


def _classify_items(items, refresh_pct):
    """将符文分为推荐/考虑/建议刷新三类"""
    if not items:
        return [], [], []
    rec = [s for s in items if s["logo"] == "推荐选取"]
    con = [s for s in items if s["logo"] == "值得考虑"]
    ref = [s for s in items if s["logo"] == "建议刷新"]
    return rec, con, ref


# ==================== API 路由 ====================

@app.route("/")
def index():
    return send_from_directory("output", "recommend_platform_v7.7.html")


@app.route("/api/meta")
def api_meta():
    """元信息"""
    ugc_stats = getattr(dl, 'ugc_clip_stats', {})
    norm_stats = getattr(dl, 'normalization_stats', {})
    hero_wr_stats = getattr(dl, 'hero_avg_winrate_stats', {})
    return jsonify({
        "total_heroes": len(HERO_LIST),
        "total_augments": sum(len(v) for v in AUGMENTS_BY_LEVEL.values()),
        "augments_by_level": {k: len(v) for k, v in AUGMENTS_BY_LEVEL.items()},
        "total_blacktech_combos": len(BLACKTECH_COMBOS),
        "total_hero_blacktech": len(HERO_BLACKTECH),
        "total_entertainment": len(ENTERTAINMENT_POOL),
        "ugc_clip_stats": ugc_stats,
        "ugc_clip_floor": se_module.UGC_CLIP_FLOOR,
        "hero_avg_winrate": se_module.HERO_AVG_WINRATE,
        "hero_avg_winrate_stats": hero_wr_stats,
        "normalization_stats": norm_stats,
        "version": "v7.7 (权重参数调优+社区推荐理由润色)",
    })


@app.route("/api/heroes")
def api_heroes():
    """英雄列表"""
    return jsonify(HERO_LIST)


@app.route("/api/params")
def api_params():
    """获取当前参数"""
    return jsonify(CURRENT_PARAMS)


@app.route("/api/params", methods=["POST"])
def api_set_params():
    """更新参数"""
    data = request.json
    for k, v in data.items():
        if k in CURRENT_PARAMS:
            CURRENT_PARAMS[k] = float(v)
    apply_params(CURRENT_PARAMS)
    return jsonify({"ok": True, "params": CURRENT_PARAMS})


@app.route("/api/params/reset", methods=["POST"])
def api_reset_params():
    """重置参数"""
    # 重置归一化参数和其他配置（权重由recalc_weights自动计算，不硬编码）
    CURRENT_PARAMS.update({
        "WR_FLOOR": 45.0, "WR_CEILING": 70.0,
        "PR_FLOOR": 0.1, "PR_CEILING": 5.0, "PR_SATURATION": 3.0,
        "UGC_FLOOR": 3.0, "UGC_CEILING": 9.0, "UGC_MAX": 10.0,
        "BLACKTECH_BONUS_CAP": 20, "SYNERGY_BONUS_CAP": 10, "HERO_CORRECTION_STRENGTH": 0.3,
        "HERO_CORRECTION_MAX": 8.0, "HERO_CORRECTION_MIN": -5.0,
        "TARGET_RECOMMEND_PER_LEVEL": 5, "MIN_RECOMMEND_PER_LEVEL": 4,
        "MAX_RECOMMEND_PER_LEVEL": 6, "STRONG_CARD_TOP_PERCENT": 15.0,
        "UGC_CLIP_PERCENTILE": 5.0, "UGC_BAYESIAN_PRIOR_WEIGHT": 30,
        "REFRESH_BOTTOM_PERCENT": 20.0,
        "WINNING_DEMOTE_PERCENT": 50.0, "ENTERTAINMENT_BOOST": 15.0,
    })
    apply_params(CURRENT_PARAMS)
    # 根据归一化区间重新计算权重
    se_module.recalc_weights()
    # 同步权重到 CURRENT_PARAMS
    _sync_weights_to_params()
    return jsonify({"ok": True, "params": CURRENT_PARAMS})


@app.route("/api/hero/<hero_name>")
def api_hero_scores(hero_name):
    """单英雄评分（按需加载，秒级响应）"""
    streak = int(request.args.get("streak", 0))
    scores = calc_hero_scores(hero_name, streak)

    # 查找英雄ID和英雄胜率
    hero_id = None
    for h in HERO_LIST:
        if h["name"] == hero_name:
            hero_id = h["id"]
            break

    hero_wr = 0
    if hero_id and hasattr(dl, 'champion_win_rate'):
        # champion_win_rate的key可能是'33.0'或'33'
        hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
        if hero_id in dl.champion_win_rate:
            hero_wr = round(dl.champion_win_rate[hero_id], 2)
        elif hero_id_dot in dl.champion_win_rate:
            hero_wr = round(dl.champion_win_rate[hero_id_dot], 2)

    # 统计英雄有效数据条数（英雄×符文组合数量）
    hero_data_count = 0
    if hero_id:
        for (c, aug), stats in dl.champion_augment_stats.items():
            if str(int(float(c))) == hero_id:
                hero_data_count += 1

    # 统计各类符文数
    total_rec = 0
    total_con = 0
    total_ref = 0
    for items in scores.values():
        for s in items:
            if s["logo"] == "推荐选取":
                total_rec += 1
            elif s["logo"] == "值得考虑":
                total_con += 1
            else:
                total_ref += 1

    # 找出最高胜率符文
    best_aug = {"name": "", "wr": 0, "pr": 0}
    for items in scores.values():
        for s in items:
            if s["wr"] > best_aug["wr"]:
                best_aug = {"name": s["aug"], "wr": round(s["wr"], 2), "pr": round(s["pr"], 2)}

    # 找出潜力组合符文 - 显示组合胜率和组内符文
    combo_augs = []
    for combo in dl.blacktech_combos:
        aug1, aug2 = combo["aug1"], combo["aug2"]
        # 检查这个英雄是否适配此组合
        from recommend.blacktech_matcher import BlacktechMatcher
        bt_matcher_tmp = BlacktechMatcher(dl)
        hero_fit = bt_matcher_tmp._hero_fits_combo(hero_name, combo)
        if not hero_fit:
            continue
        # 获取组合真实胜率（优先step1_4数据，回退Excel平均胜率）
        pair_wr = dl.get_pair_winrate(aug1, aug2, champion_id=hero_id)
        if pair_wr is None:
            pair_wr = combo.get("avg_winrate", 0)
        combo_augs.append({
            "aug1": aug1,
            "aug2": aug2,
            "combo_wr": round(pair_wr, 2),
            "pitch": combo.get("pitch", combo.get("流派", "")),
            "label": combo.get("流派", ""),
        })
    # 按组合胜率排序去重
    combo_augs.sort(key=lambda x: -x["combo_wr"])
    seen_combos = set()
    unique_combos = []
    for c in combo_augs:
        key = tuple(sorted([c["aug1"], c["aug2"]]))
        if key not in seen_combos:
            seen_combos.add(key)
            unique_combos.append(c)

    level_stats = {}
    for lv, items in scores.items():
        rec_count = sum(1 for s in items if s["logo"] == "推荐选取")
        con_count = sum(1 for s in items if s["logo"] == "值得考虑")
        ref_count = sum(1 for s in items if s["logo"] == "建议刷新")
        rec_th, con_th = engine.get_threshold(
            hero_id, 1, lv
        )
        level_stats[lv] = {
            "rec": rec_count, "con": con_count, "ref": ref_count,
            "rec_th": rec_th, "con_th": con_th,
            "total": len(items),
        }

    # ====== 分数影响度计算 ======
    # 胜率+1%、选率+0.01%、UGC+1分(10分制) 对最终分数的影响
    # 使用se_module运行时实际值（已被data_loader用真实数据P2/P98覆盖），而非CURRENT_PARAMS初始默认值
    wr_floor = se_module.WR_FLOOR
    wr_ceiling = se_module.WR_CEILING
    pr_floor = se_module.PR_FLOOR
    pr_ceiling = se_module.PR_CEILING
    ugc_floor = se_module.UGC_FLOOR
    ugc_ceiling = se_module.UGC_CEILING
    
    # 标准模式
    w_std = se_module.WEIGHT_PROFILES["standard"]
    # 胜率+1%对分数的影响
    wr_delta_std = round(1.0 / (wr_ceiling - wr_floor) * 100 * w_std["W_winrate"], 2)
    # 选率+0.01%对分数的影响
    pr_delta_std = round(0.01 / (pr_ceiling - pr_floor) * 100 * w_std["W_pickrate"], 2) if pr_ceiling > pr_floor else 0
    # UGC+1分对分数的影响
    ugc_delta_std = round(1.0 / (ugc_ceiling - ugc_floor) * 100 * w_std["W_ugc"], 2) if ugc_ceiling > ugc_floor else 0
    
    # 连胜模式
    w_win = se_module.WEIGHT_PROFILES["winning"]
    wr_delta_win = round(1.0 / (wr_ceiling - wr_floor) * 100 * w_win["W_winrate"], 2)
    pr_delta_win = round(0.01 / (pr_ceiling - pr_floor) * 100 * w_win["W_pickrate"], 2) if pr_ceiling > pr_floor else 0
    ugc_delta_win = round(1.0 / (ugc_ceiling - ugc_floor) * 100 * w_win["W_ugc"], 2) if ugc_ceiling > ugc_floor else 0
    
    # 连败模式
    w_lose = se_module.WEIGHT_PROFILES["losing"]
    wr_delta_lose = round(1.0 / (wr_ceiling - wr_floor) * 100 * w_lose["W_winrate"], 2)
    pr_delta_lose = round(0.01 / (pr_ceiling - pr_floor) * 100 * w_lose["W_pickrate"], 2) if pr_ceiling > pr_floor else 0
    ugc_delta_lose = round(1.0 / (ugc_ceiling - ugc_floor) * 100 * w_lose["W_ugc"], 2) if ugc_ceiling > ugc_floor else 0
    
    # 计算该英雄的纠偏分
    hero_correction = engine.calc_hero_correction(hero_id) if hero_id else 0.0
    hero_avg_wr = round(se_module.HERO_AVG_WINRATE, 2)
    
    score_impact = {
        "standard": {"wr_per_1pct": wr_delta_std, "pr_per_0_01pct": pr_delta_std, "ugc_per_1pt": ugc_delta_std},
        "winning":  {"wr_per_1pct": wr_delta_win, "pr_per_0_01pct": pr_delta_win, "ugc_per_1pt": ugc_delta_win},
        "losing":   {"wr_per_1pct": wr_delta_lose, "pr_per_0_01pct": pr_delta_lose, "ugc_per_1pt": ugc_delta_lose},
        "hero_correction": hero_correction,
        "hero_avg_wr": hero_avg_wr,
    }

    return jsonify({
        "hero": hero_name,
        "hero_id": hero_id,
        "hero_wr": hero_wr,
        "hero_data_count": hero_data_count,
        "streak": streak,
        "total_rec": total_rec,
        "total_con": total_con,
        "total_ref": total_ref,
        "best_aug": best_aug,
        "combo_augs": unique_combos[:10],
        "level_stats": level_stats,
        "scores": scores,
        "score_impact": score_impact,
    })


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """模拟推荐（实时计算，支持阶段感知和前置已选卡牌）"""
    data = request.json
    hero_name = data.get("hero", "")
    stage = int(data.get("stage", 1))
    streak = int(data.get("streak", 0))
    num = int(data.get("num", 3))
    selected_augments = data.get("selected_augments", [])  # 前面阶段已选的符文

    # 等级由前端独立传入，不再由阶段自动决定
    level = data.get("level", "白银")
    if level not in ("白银", "黄金", "棱彩"):
        level = "白银"

    # 查找英雄ID
    hero_id = None
    for h in HERO_LIST:
        if h["name"] == hero_name:
            hero_id = h["id"]
            break
    if not hero_id:
        return jsonify({"error": "未找到英雄", "candidates": []})

    from recommend.blacktech_matcher import BlacktechMatcher
    bt_matcher = BlacktechMatcher(dl)

    refresh_pct = CURRENT_PARAMS.get("REFRESH_BOTTOM_PERCENT", 20.0)

    # 构建该英雄有数据的符文集合
    hero_aug_set = set()
    hero_id_dot = f"{hero_id}.0" if "." not in hero_id else hero_id
    for (c, aug_id), stats in dl.champion_augment_stats.items():
        if str(c) == hero_id or str(c) == hero_id_dot:
            aug_cn = _get_augment_cn(aug_id)
            if aug_cn:
                hero_aug_set.add(aug_cn)

    # 对该等级的符文评分（使用阶段感知的黑科技匹配）
    augs = AUGMENTS_BY_LEVEL.get(level, [])
    level_augs = [a for a in augs if a in hero_aug_set] if hero_aug_set else augs
    target_rec = int(CURRENT_PARAMS.get("TARGET_RECOMMEND_PER_LEVEL", 4))
    min_rec = int(CURRENT_PARAMS.get("MIN_RECOMMEND_PER_LEVEL", 2))
    max_rec = int(CURRENT_PARAMS.get("MAX_RECOMMEND_PER_LEVEL", 6))
    target_rec = max(min_rec, min(max_rec, target_rec))
    items = []
    for aug_name in level_augs:
        # 黑科技加成 — 传入stage和已选符文，这样S3/S4只有已选过另一半才给加分
        bt_result = bt_matcher.match(aug_name, hero_name, stage=stage,
                                     selected_augments=selected_augments)
        bt_bonus = bt_result.get("bonus", 0)
        syn_bonus = bt_result.get("synergy_bonus", 0)

        score, detail = engine.calc_final_score(
            aug_name, hero_id, streak, bt_bonus, stage, level,
            synergy_bonus=syn_bonus
        )
        tag = engine.determine_tag(aug_name, hero_name, bt_result, streak,
                                   champion_id=hero_id)

        items.append({
            "aug": aug_name,
            "score": score,
            "logo": "",
            "tag": tag,
            "visible_tag": None,
            "wr": detail.get("win_rate_raw", 0),
            "pr": detail.get("pick_rate_raw", 0),
            "ugc": detail.get("ugc_score_raw", 0),
            "bt": detail.get("blacktech_bonus", 0),
            "syn": detail.get("synergy_bonus", 0),
            "total_bonus": detail.get("total_bonus", 0),
            "wr_norm": detail.get("win_rate_norm", 0),
            "pr_norm": detail.get("pick_rate_norm", 0),
            "ugc_norm": detail.get("ugc_norm", 0),
            "base": detail.get("base_score", 0),
            "correction": detail.get("hero_correction", 0),
            "multiplier": detail.get("streak_multiplier", 1.0),
            "bt_details": bt_result.get("details", []),
            "bt_tag": bt_result.get("tag", ""),
            "bt_pitch": bt_result.get("pitch", ""),
            "synergy_info": bt_result.get("synergy_info", ""),
            "winning_adjusted": "",
        })
    items.sort(key=lambda x: -x["score"])

    # 后评分自适应分类（同calc_hero_scores）
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

    # 连胜娱乐调整
    if streak >= 3:
        items = engine.apply_winning_entertainment(
            items, streak, champion_id=hero_id, augment_level=level
        )
        items.sort(key=lambda x: -x["score"])
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

    # 标签可见性 — 强力单卡补充规则 (v3.6)
    # 所有模式统一判定：推荐选取中满足TOP15%且无其他标签的，标记为强力单卡
    rec_items = [it for it in items if it["logo"] == "推荐选取"]
    for it in rec_items:
        if it["tag"] is None:
            if engine._is_strong_card_for_hero(it["aug"], hero_id):
                it["tag"] = "强力单卡"

    for item in items:
        if item["logo"] != "推荐选取":
            item["visible_tag"] = None
        elif item["tag"] == "娱乐" and streak < 3:
            item["visible_tag"] = None
        else:
            item["visible_tag"] = item["tag"]

    if not items:
        return jsonify({"error": "无数据", "candidates": []})

    import random
    candidates = random.sample(items, min(num, len(items)))
    candidates.sort(key=lambda x: -x["score"])

    return jsonify({
        "hero": hero_name,
        "stage": stage,
        "level": level,
        "streak": streak,
        "selected_augments": selected_augments,
        "candidates": candidates,
        "total_available": len(items),
    })


@app.route("/api/blacktech")
def api_blacktech():
    """黑科技组合"""
    return jsonify({
        "combos": BLACKTECH_COMBOS,
        "hero_blacktech": HERO_BLACKTECH[:200],  # 前端懒加载
        "total_hero_blacktech": len(HERO_BLACKTECH),
    })


@app.route("/api/blacktech/search")
def api_blacktech_search():
    """搜索英雄专属黑科技"""
    q = request.args.get("q", "").lower()
    page = int(request.args.get("page", 0))
    size = int(request.args.get("size", 50))
    filtered = [h for h in HERO_BLACKTECH if q in h["hero"].lower() or q in h["augment"].lower()] if q else HERO_BLACKTECH
    total = len(filtered)
    items = filtered[page * size: (page + 1) * size]
    return jsonify({"items": items, "total": total, "page": page, "size": size})


@app.route("/api/overview")
def api_overview():
    """总览统计（采样20个英雄快速出结果）"""
    import random
    sample = random.sample(HERO_LIST, min(20, len(HERO_LIST)))
    stats = []
    for h in sample:
        scores = calc_hero_scores(h["name"], 0)
        total_rec = sum(sum(1 for s in items if s["logo"] == "推荐选取") for items in scores.values())
        avg_wr_list = [s["wr"] for items in scores.values() for s in items if s["wr"] > 0]
        avg_wr = round(sum(avg_wr_list) / max(1, len(avg_wr_list)), 2)
        stats.append({"hero": h["name"], "total_rec": total_rec, "avg_wr": avg_wr})
    return jsonify({"sample_stats": stats, "sample_size": len(sample), "total_heroes": len(HERO_LIST)})


@app.route("/api/overview/full")
def api_overview_full():
    """
    全量统计：所有英雄各等级推荐数量分布
    返回每个英雄各等级的推荐/考虑/刷新数量，以及汇总统计
    """
    all_hero_stats = []
    level_rec_counts = {"白银": [], "黄金": [], "棱彩": []}
    total_rec_counts = []

    for h in HERO_LIST:
        scores = calc_hero_scores(h["name"], 0)
        hero_stat = {"hero": h["name"], "hero_id": h["id"]}
        hero_total_rec = 0

        for lv in ["白银", "黄金", "棱彩"]:
            items = scores.get(lv, [])
            rec = sum(1 for s in items if s["logo"] == "推荐选取")
            con = sum(1 for s in items if s["logo"] == "值得考虑")
            ref = sum(1 for s in items if s["logo"] == "建议刷新")
            hero_stat[lv] = {"rec": rec, "con": con, "ref": ref, "total": len(items)}
            level_rec_counts[lv].append(rec)
            hero_total_rec += rec

        hero_stat["total_rec"] = hero_total_rec
        total_rec_counts.append(hero_total_rec)
        all_hero_stats.append(hero_stat)

    # 汇总统计
    import numpy as np
    summary = {}
    for lv in ["白银", "黄金", "棱彩"]:
        arr = np.array(level_rec_counts[lv])
        summary[lv] = {
            "mean": round(float(np.mean(arr)), 2) if len(arr) > 0 else 0,
            "median": round(float(np.median(arr)), 1) if len(arr) > 0 else 0,
            "min": int(np.min(arr)) if len(arr) > 0 else 0,
            "max": int(np.max(arr)) if len(arr) > 0 else 0,
            "std": round(float(np.std(arr)), 2) if len(arr) > 0 else 0,
            "total_heroes": len(arr),
        }
    total_arr = np.array(total_rec_counts)
    summary["total"] = {
        "mean": round(float(np.mean(total_arr)), 2) if len(total_arr) > 0 else 0,
        "median": round(float(np.median(total_arr)), 1) if len(total_arr) > 0 else 0,
        "min": int(np.min(total_arr)) if len(total_arr) > 0 else 0,
        "max": int(np.max(total_arr)) if len(total_arr) > 0 else 0,
        "std": round(float(np.std(total_arr)), 2) if len(total_arr) > 0 else 0,
        "total_heroes": len(total_arr),
    }

    # 按总推荐数排序
    all_hero_stats.sort(key=lambda x: -x["total_rec"])

    return jsonify({
        "heroes": all_hero_stats,
        "summary": summary,
        "params": {
            "TARGET_RECOMMEND_PER_LEVEL": CURRENT_PARAMS["TARGET_RECOMMEND_PER_LEVEL"],
            "MIN_RECOMMEND_PER_LEVEL": CURRENT_PARAMS["MIN_RECOMMEND_PER_LEVEL"],
            "MAX_RECOMMEND_PER_LEVEL": CURRENT_PARAMS["MAX_RECOMMEND_PER_LEVEL"],
            "REFRESH_BOTTOM_PERCENT": CURRENT_PARAMS["REFRESH_BOTTOM_PERCENT"],
        },
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  海克斯大乱斗 AI Coach 推荐平台 v7.4")
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
