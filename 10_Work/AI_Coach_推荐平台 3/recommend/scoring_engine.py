# -*- coding: utf-8 -*-
"""
评分引擎模块 v3.6
实现：归一化 → 加权打分 → 分英雄自适应阈值 → 新标签体系
     → 连胜/连败权重调整 → 娱乐符文特殊逻辑

v3.6 核心变更:
  1. 三维度统一P2/P98线性映射归一化（胜率/选率/UGC不再用不同方法）
  2. 权重调整: standard选率0.15→0.20, 胜率0.60→0.55（选率满分可贡献20分，与黑科技更平衡）
  3. 选率归一化: 从饱和点除法(pr/P99)改为P2/P98线性映射
  4. UGC归一化: 保留贝叶斯收缩+P5截断，最终映射从/10改为P2/P98线性映射
  5. 黑科技加成上限不变(20分)

v3.5 核心变更:
  1. 禁用英雄胜率纠偏分（每个英雄推荐池已通过TopN设定）
  2. 胜率归一化上下限改为运行时从英雄×符文实际胜率的P2/P98自动计算
  3. 选率归一化饱和点改为运行时从英雄×符文实际选率的P99自动计算
  4. 默认值（WR_FLOOR/WR_CEILING/PR_SATURATION）在data_loader加载时自动覆盖
  5. 使用分位数代替min/max，排除小样本造成的极端值(0%/100%胜率)

v3.3 变更:
  1. 去掉连胜/连败额外乘数(0.96/0.92/1.04/1.08)，仅通过权重调整体现差异
  2. 连胜娱乐降级逻辑改为合并排序：最佳拍档+强力单卡合并后取后50%降级
     （避免小样本下top1也被降级的问题）
  3. 连胜/连败权重可在前端面板实时调整
"""
import logging
import os
import json

logger = logging.getLogger("ScoringEngine")

# ==================== 权重配置 ====================
# v3.8: 目标影响度驱动的权重系统
#   定义"目标影响度"：每个指标变化一定量对分数的影响
#   权重 = 目标影响度 × (CEILING - FLOOR) / (变化量 × 100)
#   数据加载后由 recalc_weights() 根据实际归一化区间自动反推权重
#
# 目标影响度（标准模式）:
#   胜率+1% → +5分
#   选率+0.01% → +2.5分
#   UGC+1分(10分制) → +4分
#
# 连胜/连败模式通过缩放比例调整:
#   连胜(娱乐向): 胜率×0.64, 选率×0.82, UGC×1.80
#   连败(求稳向): 胜率×1.40, 选率×1.10, UGC×0.40

# 标准模式目标影响度
TARGET_IMPACT = {
    "wr_per_1pct": 5.0,       # 胜率+1% → +5分
    "pr_per_0_01pct": 2.5,    # 选率+0.01% → +2.5分
    "ugc_per_1pt": 3.5,       # UGC+1分 → +3.5分
}

# 连胜/连败相对于标准模式的缩放比例
MODE_SCALE = {
    "standard": {"wr": 1.00, "pr": 1.00, "ugc": 1.00},
    "winning":  {"wr": 0.64, "pr": 0.82, "ugc": 1.57},   # ≥3连胜: 胜率↓选率↓UGC↑(娱乐向) UGC→+5.5
    "losing":   {"wr": 1.40, "pr": 1.10, "ugc": 0.43},   # ≥3连败: 胜率↑选率↑UGC↓(求稳)  UGC→+1.5
}

# 权重（会在 recalc_weights() 中根据实际归一化区间自动计算）
# 这里先用默认归一化参数算一个初始值
WEIGHT_PROFILES = {
    "standard": {"W_winrate": 1.0,  "W_pickrate": 0.25, "W_ugc": 0.15},
    "winning":  {"W_winrate": 0.8,  "W_pickrate": 0.20, "W_ugc": 0.25},
    "losing":   {"W_winrate": 1.3,  "W_pickrate": 0.25, "W_ugc": 0.05},
}


def recalc_weights():
    """根据当前归一化区间自动反推权重，确保分数影响度符合目标"""
    wr_range = WR_CEILING - WR_FLOOR
    pr_range = PR_CEILING - PR_FLOOR
    ugc_range = UGC_CEILING - UGC_FLOOR

    if wr_range <= 0 or pr_range <= 0 or ugc_range <= 0:
        logger.warning("recalc_weights: 归一化区间无效，跳过自动计算")
        return

    for mode_name, scale in MODE_SCALE.items():
        # W = target_impact * range / (delta * 100)
        # 胜率: delta=1(%)  → W_wr = target * wr_range / (1 * 100)
        # 选率: delta=0.01(%) → W_pr = target * pr_range / (0.01 * 100)
        # UGC:  delta=1(分)  → W_ugc = target * ugc_range / (1 * 100)
        w_wr = round(TARGET_IMPACT["wr_per_1pct"] * scale["wr"] * wr_range / 100, 4)
        w_pr = round(TARGET_IMPACT["pr_per_0_01pct"] * scale["pr"] * pr_range / 1, 4)
        w_ugc = round(TARGET_IMPACT["ugc_per_1pt"] * scale["ugc"] * ugc_range / 100, 4)

        WEIGHT_PROFILES[mode_name] = {
            "W_winrate": w_wr,
            "W_pickrate": w_pr,
            "W_ugc": w_ugc,
        }

    logger.info(f"  [v3.8] 权重已根据归一化区间自动计算:")
    logger.info(f"    归一化区间: WR=[{WR_FLOOR},{WR_CEILING}]({wr_range:.2f}), "
                f"PR=[{PR_FLOOR},{PR_CEILING}]({pr_range:.4f}), "
                f"UGC=[{UGC_FLOOR},{UGC_CEILING}]({ugc_range:.2f})")
    for mode_name in ["standard", "winning", "losing"]:
        w = WEIGHT_PROFILES[mode_name]
        logger.info(f"    {mode_name}: W_wr={w['W_winrate']}, W_pr={w['W_pickrate']}, W_ugc={w['W_ugc']}")

# ==================== 归一化参数 ====================
# v3.6: 三维度统一使用P2/P98线性映射，默认值会在data_loader加载时被实际分位数覆盖
WR_FLOOR = 45.0       # 运行时被覆盖为英雄×符文胜率的P2
WR_CEILING = 70.0     # 运行时被覆盖为英雄×符文胜率的P98
PR_FLOOR = 0.1        # 运行时被覆盖为英雄×符文选率的P2
PR_CEILING = 5.0      # 运行时被覆盖为英雄×符文选率的P98
PR_SATURATION = 3.0   # 保留兼容（v3.6不再使用，用PR_FLOOR/PR_CEILING代替）
UGC_FLOOR = 3.0       # 运行时被覆盖为UGC评分(贝叶斯收缩后)的P2
UGC_CEILING = 9.0     # 运行时被覆盖为UGC评分(贝叶斯收缩后)的P98
UGC_MAX = 10.0        # 保留兼容

# ==================== UGC评分异常值处理参数 ====================
# 方案: 分位数截断（不依赖正态假设）
# 低于此分位数的UGC评分统一设为该分位数值，防止极端低值
UGC_CLIP_PERCENTILE = 5.0   # 截断在P5（底部5%）
UGC_CLIP_FLOOR = None        # 运行时计算，初始为None

# ==================== UGC低样本贝叶斯收缩参数 ====================
# 思路：评分样本越少，越"收缩"到全局均值，防止小样本偏差
# 收缩后评分 = (样本数 × 原始评分 + 先验权重 × 全局均值) / (样本数 + 先验权重)
# 先验权重越大，低样本符文的UGC越接近全局均值
UGC_BAYESIAN_PRIOR_WEIGHT = 30  # 先验权重（相当于"虚拟样本数"）
UGC_GLOBAL_MEAN = None           # 运行时计算

# 黑科技加成上限
BLACKTECH_BONUS_CAP = 20

# 套装羁绊加成上限（独立于黑科技加成）
SYNERGY_BONUS_CAP = 10

# ==================== 英雄胜率纠偏参数 ====================
# v3.5: 纠偏分已禁用（每个英雄推荐池已通过TopN设定好了）
HERO_CORRECTION_ENABLED = False  # 纠偏开关，False=禁用
# 全英雄平均胜率基准（运行时由data_loader从step1_3真实数据覆盖）
HERO_AVG_WINRATE = 50.0  # 默认值，会被真实数据覆盖
# 纠偏强度系数（越大纠偏越强）
HERO_CORRECTION_STRENGTH = 0.3
# 纠偏上下限
HERO_CORRECTION_MAX = 8.0   # 最多加8分
HERO_CORRECTION_MIN = -5.0  # 最多扣5分

# ==================== 推荐数量目标 ====================
TARGET_RECOMMEND_PER_LEVEL = 6   # 每等级目标推荐数 (v3.9: 从5→6)
MIN_RECOMMEND_PER_LEVEL = 5      # 最少推荐数 (v3.9: 从4→5)
MAX_RECOMMEND_PER_LEVEL = 7      # 最多推荐数 (v3.9: 从6→7)

# ==================== WR Top5 保护机制 (v3.9) ====================
# 全局 WR 排名 Top5 的符文在其所在等级的分类阶段获得额外加分
# 目的：确保高胜率符文不会因为缺少黑科技/羁绊加成而被挤出推荐
# 仅影响等级内分类，不影响全局排名和评分公式
WR_TOP_N = 5                     # 保护前 N 名
WR_TOP_BONUS = 38                # 保护加分（足以覆盖最大 gap）

# ==================== 标签定义 ====================
TAG_POTENTIAL_COMBO = "潜力组合"    # 原"黑科技组合"
TAG_BEST_PARTNER = "最佳拍档"      # 原"英雄专属黑科技"
TAG_STRONG_CARD = "强力单卡"       # 符文本身胜率特别高
TAG_ENTERTAINMENT = "娱乐"          # 连胜用户特有

# 强力单卡判定：英雄×符文胜率在该英雄所有符文中排TOP X%
# TOP 15% 即取排名前15%的英雄×符文胜率作为强力单卡
STRONG_CARD_TOP_PERCENT = 15.0

# ==================== 连胜娱乐逻辑参数 ====================
# 连胜时最佳拍档和强力单卡的降级比例（后X%降级为"值得考虑"）
WINNING_DEMOTE_PERCENT = 50.0  # 默认50%：两类标签的后50%降级
# 连胜时娱乐符文的加分（让娱乐符文提升到"推荐"区域）
ENTERTAINMENT_BOOST = 15.0  # 给娱乐符文加15分

# ==================== 娱乐符文池 ====================
_entertainment_pool = None

def load_entertainment_pool():
    """加载娱乐符文池"""
    global _entertainment_pool
    if _entertainment_pool is not None:
        return _entertainment_pool
    
    _entertainment_pool = set()
    try:
        import pandas as pd
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 优先v5验证版，回退v3
        bt_path_v5 = os.path.join(base_dir, "output", "黑科技组合分析_v5.xlsx")
        bt_path_v3 = os.path.join(base_dir, "output", "黑科技组合分析_v3.xlsx")
        bt_path = bt_path_v5 if os.path.exists(bt_path_v5) else bt_path_v3
        if os.path.exists(bt_path):
            df = pd.read_excel(bt_path, sheet_name="娱乐符文")
            _entertainment_pool = set(df["符文名称"].astype(str).tolist())
            logger.info(f"加载娱乐符文池: {len(_entertainment_pool)} 个 (from {os.path.basename(bt_path)})")
        else:
            logger.warning("黑科技文件不存在，娱乐符文池为空")
    except Exception as e:
        logger.warning(f"加载娱乐符文池失败: {e}")
    return _entertainment_pool


class ScoringEngine:
    """
    评分引擎 v3.5

    公式: 最终得分 = 基础分 + 黑科技加成
    基础分 = 符文胜率分×W_winrate + 符文选择率分×W_pickrate + UGC评分分×W_ugc
    
    v3.5: 禁用英雄胜率纠偏分（每个英雄推荐池已通过TopN设定好了）
          胜率/选率归一化参数改为从英雄×符文实际数据自动计算
    v3.3: 去掉连胜/连败额外乘数，仅通过权重profile体现差异
    """

    def __init__(self, data_loader):
        self.dl = data_loader
        self._hero_thresholds_cache = {}  # 缓存分英雄阈值

    # ==================== 归一化 ====================

    @staticmethod
    def normalize_winrate(wr):
        """胜率归一化: 45%→0分, 70%→100分"""
        score = (wr - WR_FLOOR) / (WR_CEILING - WR_FLOOR) * 100
        return max(0, min(100, score))

    @staticmethod
    def normalize_pickrate(pr):
        """选取率归一化: P2/P98线性映射（v3.6统一归一化方法）"""
        if PR_CEILING <= PR_FLOOR:
            # 安全回退：使用旧的饱和点方法
            score = min(pr / PR_SATURATION, 1.0) * 100
        else:
            score = (pr - PR_FLOOR) / (PR_CEILING - PR_FLOOR) * 100
        return max(0, min(100, score))

    @staticmethod
    def normalize_ugc(ugc_score, sample_count=None):
        """
        UGC评分归一化（含异常值处理 + 低样本收缩 + P2/P98线性映射）
        
        1. 无评分 → 默认50分（中性）
        2. 低样本贝叶斯收缩：样本越少越向全局均值靠拢
        3. 分位数下限截断：低于P5的统一截断
        4. P2/P98线性映射到0-100（v3.6统一归一化方法）
        """
        if ugc_score is None or ugc_score <= 0:
            return 50
        
        adjusted_score = ugc_score
        
        # 低样本贝叶斯收缩
        if (sample_count is not None and sample_count > 0 
                and UGC_GLOBAL_MEAN is not None 
                and UGC_BAYESIAN_PRIOR_WEIGHT > 0):
            # 收缩公式: (n*x + m*μ) / (n+m)
            n = sample_count
            m = UGC_BAYESIAN_PRIOR_WEIGHT
            adjusted_score = (n * ugc_score + m * UGC_GLOBAL_MEAN) / (n + m)
        
        # 分位数下限截断
        if UGC_CLIP_FLOOR is not None and adjusted_score < UGC_CLIP_FLOOR:
            adjusted_score = UGC_CLIP_FLOOR
        
        # v3.6: P2/P98线性映射（与胜率、选率统一）
        if UGC_CEILING > UGC_FLOOR:
            score = (adjusted_score - UGC_FLOOR) / (UGC_CEILING - UGC_FLOOR) * 100
        else:
            # 安全回退：使用旧的/10方法
            score = adjusted_score / UGC_MAX * 100
        return max(0, min(100, score))

    # ==================== 英雄胜率纠偏 ====================

    def calc_hero_correction(self, champion_id):
        """
        计算英雄胜率纠偏分
        
        v3.5: 可通过 HERO_CORRECTION_ENABLED 开关禁用（默认禁用）
        
        低胜率英雄（如40%）→ 正向纠偏 → 更容易获得推荐
        高胜率英雄（如55%）→ 负向纠偏 → 阈值更严格
        
        公式: correction = (HERO_AVG_WR - hero_wr) × STRENGTH × 100 / (CEILING - FLOOR)
        """
        # v3.5: 纠偏分已禁用
        if not HERO_CORRECTION_ENABLED:
            return 0.0
        
        if not champion_id:
            return 0.0
        
        hero_wr = self._get_hero_avg_winrate(champion_id)
        if hero_wr <= 0:
            return 0.0
        
        # 与平均水平的差距
        delta = HERO_AVG_WINRATE - hero_wr
        # 映射到评分维度并乘以强度系数
        correction = delta * HERO_CORRECTION_STRENGTH * 100 / (WR_CEILING - WR_FLOOR)
        # 限幅
        correction = max(HERO_CORRECTION_MIN, min(HERO_CORRECTION_MAX, correction))
        
        return round(correction, 2)

    def _get_hero_avg_winrate(self, champion_id):
        """
        获取英雄真实胜率（从step1_3数据）
        优先使用 champion_win_rate（step1_3直接查出来的英雄胜率）
        回退使用 champion_augment_stats 中所有符文的胜率均值
        """
        if not champion_id:
            return HERO_AVG_WINRATE
        
        cid = str(champion_id)
        cid_dot = f"{cid}.0" if "." not in cid else cid
        
        # 优先使用step1_3的真实英雄胜率
        if hasattr(self.dl, 'champion_win_rate'):
            if cid in self.dl.champion_win_rate:
                return self.dl.champion_win_rate[cid]
            if cid_dot in self.dl.champion_win_rate:
                return self.dl.champion_win_rate[cid_dot]
        
        # 回退：从英雄×符文数据推算（不推荐，仅兜底）
        winrates = []
        for (c, aug), stats in self.dl.champion_augment_stats.items():
            if str(c) == cid or str(c) == cid_dot:
                winrates.append(stats["win_rate"])
        
        if winrates:
            return sum(winrates) / len(winrates)
        
        return HERO_AVG_WINRATE

    # ==================== 权重选择 ====================

    @staticmethod
    def get_weight_profile(streak=0):
        """根据连胜/连败选择权重配置"""
        if streak >= 3:
            return WEIGHT_PROFILES["winning"], "winning"
        elif streak <= -3:
            return WEIGHT_PROFILES["losing"], "losing"
        else:
            return WEIGHT_PROFILES["standard"], "standard"

    # ==================== 连胜连败系数 ====================

    @staticmethod
    def get_streak_multiplier(streak=0):
        """
        连胜连败系数 (v7.5: 不再额外乘系数，只通过权重调整)
        始终返回1.0，连胜/连败的差异完全通过胜率/选率/UGC权重体现
        """
        return 1.0

    # ==================== 基础分计算 ====================

    def calc_base_score(self, augment_name, champion_id=None, streak=0):
        """计算基础分 (0-100)"""
        wr = self.dl.get_augment_winrate(augment_name, champion_id)
        pr = self.dl.get_augment_pickrate(augment_name, champion_id)
        ugc = self.dl.get_ugc_score(augment_name)
        ugc_count = self.dl.get_ugc_sample_count(augment_name)

        wr_norm = self.normalize_winrate(wr)
        pr_norm = self.normalize_pickrate(pr)
        ugc_norm = self.normalize_ugc(ugc, ugc_count)

        weights, profile_name = self.get_weight_profile(streak)

        base_score = (
            wr_norm * weights["W_winrate"]
            + pr_norm * weights["W_pickrate"]
            + ugc_norm * weights["W_ugc"]
        )

        detail = {
            "win_rate_raw": round(wr, 2),
            "pick_rate_raw": round(pr, 2),
            "ugc_score_raw": round(ugc, 2),
            "win_rate_norm": round(wr_norm, 1),
            "pick_rate_norm": round(pr_norm, 1),
            "ugc_norm": round(ugc_norm, 1),
            "weight_profile": profile_name,
            "weights": weights,
            "base_score": round(base_score, 1),
        }

        return round(base_score, 1), detail

    # ==================== 最终得分计算 ====================

    def calc_final_score(self, augment_name, champion_id=None, streak=0,
                         blacktech_bonus=0, stage=1, augment_level=None,
                         synergy_bonus=0):
        """
        计算最终得分 (v3.5)

        公式: 最终得分 = 基础分 + 黑科技加成 + 套装加成
        （英雄纠偏分已禁用，可通过HERO_CORRECTION_ENABLED开关重新启用）
        黑科技加成上限20，套装加成上限10，二者合计上限30
        连胜/连败差异通过基础分中的权重profile体现，不再额外乘系数
        """
        base_score, detail = self.calc_base_score(augment_name, champion_id, streak)
        
        # 英雄胜率纠偏
        hero_correction = self.calc_hero_correction(champion_id)
        corrected_score = base_score + hero_correction
        
        multiplier = self.get_streak_multiplier(streak)  # 始终为1.0
        capped_bt_bonus = min(blacktech_bonus, BLACKTECH_BONUS_CAP)
        capped_syn_bonus = min(synergy_bonus, SYNERGY_BONUS_CAP)
        total_bonus = capped_bt_bonus + capped_syn_bonus

        final_score = corrected_score * multiplier + total_bonus
        final_score = max(0, final_score)  # 只保留下限0，不设上限截断

        detail["hero_correction"] = hero_correction
        detail["corrected_base_score"] = round(corrected_score, 1)
        detail["streak_multiplier"] = multiplier
        detail["blacktech_bonus"] = capped_bt_bonus
        detail["synergy_bonus"] = capped_syn_bonus
        detail["total_bonus"] = total_bonus
        detail["final_score"] = round(final_score, 1)

        return round(final_score, 1), detail

    # ==================== 分英雄自适应阈值 ====================

    def calc_hero_thresholds(self, champion_id, augment_level=None, hero_aug_set=None):
        """
        计算分英雄自适应阈值
        
        思路: 对该英雄×该等级的所有符文评分，按分数排序,
              取第TARGET_RECOMMEND_PER_LEVEL名的分数作为recommend阈值,
              但确保推荐数在 MIN_RECOMMEND_PER_LEVEL ~ MAX_RECOMMEND_PER_LEVEL 之间
              
        Args:
            champion_id: 英雄ID
            augment_level: 符文等级（白银/黄金/棱彩）
            hero_aug_set: 该英雄有数据的符文集合（中文名），
                          如果提供则只考虑这些符文的评分
              
        Returns:
            (recommend_threshold, consider_threshold)
        """
        cache_key = (str(champion_id), str(augment_level))
        if cache_key in self._hero_thresholds_cache:
            return self._hero_thresholds_cache[cache_key]
        
        # 获取该等级的所有符文
        all_augments = []
        for name, info in self.dl.augment_info.items():
            level = info.get("等级", "")
            if augment_level and level != augment_level:
                continue
            # 如果提供了英雄有数据的符文集合，则只考虑其中的符文
            if hero_aug_set and name not in hero_aug_set:
                continue
            all_augments.append(name)
        
        if not all_augments:
            result = (42, 28)  # 兜底
            self._hero_thresholds_cache[cache_key] = result
            return result
        
        # 对所有符文评分（使用标准模式streak=0）
        scores = []
        for aug in all_augments:
            score, _ = self.calc_final_score(aug, champion_id, 0, 0, 1, augment_level)
            scores.append(score)
        
        scores.sort(reverse=True)
        
        # 目标推荐数
        target = int(TARGET_RECOMMEND_PER_LEVEL)
        min_rec = int(MIN_RECOMMEND_PER_LEVEL)
        max_rec = int(MAX_RECOMMEND_PER_LEVEL)
        
        # 确保目标推荐数在 min~max 范围内
        target = max(min_rec, min(max_rec, target))
        
        # 取第N名的分数作为阈值
        rec_idx = min(target - 1, len(scores) - 1)
        con_idx = min(target * 2 - 1, len(scores) - 1)
        
        recommend_th = scores[rec_idx]
        consider_th = scores[con_idx]
        
        # 确保recommend > consider
        if recommend_th <= consider_th:
            consider_th = recommend_th - 5
        
        result = (round(recommend_th, 1), round(consider_th, 1))
        self._hero_thresholds_cache[cache_key] = result
        
        logger.debug(f"英雄{champion_id} {augment_level}阈值: rec={result[0]}, con={result[1]}, "
                      f"总符文={len(scores)}, 有效={len(all_augments)}")
        
        return result

    def get_threshold(self, champion_id=None, stage=1, augment_level=None, hero_aug_set=None):
        """
        获取阈值 (v3.0: 优先分英雄自适应，回退固定阈值)
        """
        if champion_id:
            return self.calc_hero_thresholds(champion_id, augment_level, hero_aug_set=hero_aug_set)
        
        # 无英雄信息时使用固定阈值
        fallback = {
            "白银": (42, 28), "黄金": (45, 30), "棱彩": (35, 22),
        }
        if augment_level in fallback:
            return fallback[augment_level]
        return (42, 28)

    # ==================== Logo判定 (v3.2) ====================

    def get_logo(self, score, stage=1, augment_level=None, champion_id=None,
                 refresh_threshold=None, hero_aug_set=None):
        """
        三分类Logo判定（v3.2: 推荐=自适应阈值以上, 建议刷新=底部X%, 中间=值得考虑）
        
        如果传入 refresh_threshold（建议刷新阈值），则使用该值判定；
        否则使用 consider_th（老逻辑兜底）。
        """
        recommend_th, consider_th = self.get_threshold(champion_id, stage, augment_level,
                                                        hero_aug_set=hero_aug_set)
        if score >= recommend_th:
            return "推荐选取"
        elif refresh_threshold is not None:
            # 新逻辑：低于refresh_threshold的为建议刷新，中间为值得考虑
            if score < refresh_threshold:
                return "建议刷新"
            else:
                return "值得考虑"
        elif score >= consider_th:
            return "值得考虑"
        else:
            return "建议刷新"

    def get_logo_emoji(self, score, stage=1, augment_level=None, champion_id=None):
        """三分类Logo emoji"""
        recommend_th, consider_th = self.get_threshold(champion_id, stage, augment_level)
        if score >= recommend_th:
            return "👍"
        elif score >= consider_th:
            return "🤔"
        else:
            return "🔄"

    def get_logo_color(self, score, stage=1, augment_level=None, champion_id=None):
        """Logo对应颜色"""
        recommend_th, consider_th = self.get_threshold(champion_id, stage, augment_level)
        if score >= recommend_th:
            return "#22c55e"
        elif score >= consider_th:
            return "#eab308"
        else:
            return "#9ca3af"

    # ==================== 新标签判定 (v3.3) ====================

    def determine_tag(self, augment_name, champion_name=None, bt_result=None, streak=0,
                       champion_id=None):
        """
        v3.3 标签判定逻辑（仅判定标签类型，不考虑是否推荐选取）
        
        注意：标签是否显示由 apply_tag_visibility() 统一控制。
        此处只负责判定符文的"潜在标签"。
        
        优先级:
        1. 最佳拍档 - 英雄专属黑科技（黑科技组合分析_v5的985条全量匹配）
        2. 潜力组合 - bt_result中有combo匹配（通用黑科技组合）
        3. 娱乐 - 仅黑科技v5"娱乐符文"sheet中的符文
        4. 强力单卡 - 推迟到 apply_tag_visibility 中再判定（需要知道推荐状态）
        5. None - 普通符文
        
        变更:
        - 娱乐标签始终标记（但显示由连胜状态控制）
        - 强力单卡不在这里判定，推迟到visibility阶段
        - 最佳拍档匹配走黑科技Excel全量985条
        """
        if bt_result is None:
            bt_result = {"tag": "", "details": []}
        
        tag = None
        details = bt_result.get("details", [])
        
        # 检查是否有英雄专属（最佳拍档）— 最高优先级
        has_exclusive = any(d.get("type") == "hero_exclusive" for d in details)
        # 检查是否有组合匹配（潜力组合）
        has_combo = any(d.get("type") in ("combo_complete", "combo_potential_fit", "combo_complete_nofit", "combo_late_stage") for d in details)
        
        if has_exclusive:
            tag = TAG_BEST_PARTNER
        elif has_combo:
            tag = TAG_POTENTIAL_COMBO
        else:
            # 检查是否在娱乐符文池中
            ent_pool = load_entertainment_pool()
            if augment_name in ent_pool:
                tag = TAG_ENTERTAINMENT
        
        return tag

    def _is_strong_card_for_hero(self, augment_name, champion_id):
        """
        判断符文是否是该英雄的强力单卡
        逻辑：该英雄×该符文的胜率在该英雄所有符文胜率中排TOP X%
        
        注意：champion_augment_stats的key是数字ID格式 ('56.0', '1038.0')
        augment_name是中文名，需要通过 _champion_aug_stat_key 转换
        """
        cid = str(champion_id)
        
        # 使用data_loader的转换方法获取正确的key
        ca_key = self.dl._champion_aug_stat_key(cid, augment_name)
        if ca_key is None or ca_key not in self.dl.champion_augment_stats:
            return False
        hero_aug_wr = self.dl.champion_augment_stats[ca_key]["win_rate"]
        
        # 获取该英雄所有符文的胜率
        # champion_augment_stats key是 ('56.0', '1038.0') 格式
        cid_dot = f"{cid}.0" if "." not in cid else cid
        all_wrs = []
        for (c, aug), stats in self.dl.champion_augment_stats.items():
            if str(c) == cid or str(c) == cid_dot:
                all_wrs.append(stats["win_rate"])
        
        if not all_wrs:
            return False
        
        # 计算TOP X%的阈值（P85 = TOP15%）
        import numpy as np
        threshold_percentile = 100 - STRONG_CARD_TOP_PERCENT
        threshold = np.percentile(all_wrs, threshold_percentile)
        
        return hero_aug_wr >= threshold

    # ==================== 连胜娱乐逻辑 ====================

    def apply_winning_entertainment(self, scored_cards, streak=0, champion_id=None,
                                    augment_level=None):
        """
        连胜用户特殊逻辑（分数调整法 v7.5）:
        
        设计思路：
        1. 合并所有"最佳拍档"和"强力单卡"的卡片为一个列表
        2. 统一按分数排序，后 WINNING_DEMOTE_PERCENT% 施加负分数惩罚
           → 让它们自然跌落到"值得考虑"区域
           → 合并排序避免了小样本下top1也被降级的问题
        3. 找出所有"娱乐"标签的卡片，施加正分数奖励
           → 让它们自然提升到"推荐选取"区域
        4. 重新排序（logo由调用方统一重新判定）
        
        Args:
            scored_cards: 已评分的卡片列表 [{aug, score, tag, logo, ...}]
            streak: 连胜数
            champion_id: 英雄ID（用于重新计算阈值）
            augment_level: 符文等级（用于重新计算阈值）
            
        Returns:
            调整后的卡片列表（已重新排序）
        """
        if streak < 3:
            return scored_cards
        
        ent_pool = load_entertainment_pool()
        
        # 1. 合并最佳拍档 + 强力单卡为一个列表，统一排序
        demote_candidates = [c for c in scored_cards 
                             if c.get("tag") in (TAG_BEST_PARTNER, TAG_STRONG_CARD)]
        
        demote_pct = WINNING_DEMOTE_PERCENT / 100.0
        demoted_count = 0
        
        # 2. 统一排序后取后X%降分
        #    保护机制：候选≤2个时不降级（因为这意味着英雄的黑科技/强力卡本来就很少）
        #    保护机制2：保留至少1张纯强力单卡（非娱乐的）不被降级
        if len(demote_candidates) > 2:
            demote_candidates.sort(key=lambda x: x["score"], reverse=True)
            demote_count = max(1, int(len(demote_candidates) * demote_pct))
            # 取后 demote_count 个（分数最低的）
            demoted = demote_candidates[-demote_count:]
            
            # 保护至少1张纯强力单卡：检查降级后是否还剩至少1张强力单卡
            ent_aug_set = set(ent_pool) if ent_pool else set()
            remaining = [c for c in demote_candidates if c not in demoted]
            remaining_pure_strong = [c for c in remaining 
                                     if c.get("tag") == TAG_STRONG_CARD 
                                     and c.get("aug") not in ent_aug_set]
            
            if not remaining_pure_strong:
                # 剩余中没有纯强力单卡了，从demoted中找分数最高的纯强力单卡救回来
                demoted_pure_strong = [c for c in demoted 
                                       if c.get("tag") == TAG_STRONG_CARD 
                                       and c.get("aug") not in ent_aug_set]
                if demoted_pure_strong:
                    # 按分数从高到低排，保留分数最高的那张
                    demoted_pure_strong.sort(key=lambda x: x["score"], reverse=True)
                    rescued = demoted_pure_strong[0]
                    demoted.remove(rescued)
                    logger.info(f"连胜保护: 保留纯强力单卡 '{rescued.get('aug')}' 不被降级")
            
            for card in demoted:
                # 惩罚力度：让分数降到中间偏下区域
                rec_th, con_th = self.get_threshold(champion_id, 1, augment_level)
                penalty = max(5, card["score"] - (rec_th + con_th) / 2)
                card["score"] = round(card["score"] - penalty, 1)
                card["winning_adjusted"] = "demoted"
                card["winning_penalty"] = round(penalty, 1)
            demoted_count = len(demoted)
        
        # 3. 对娱乐符文加分
        entertainment_boosted = 0
        for card in scored_cards:
            if card.get("tag") == TAG_ENTERTAINMENT:
                card["score"] = round(card["score"] + ENTERTAINMENT_BOOST, 1)
                card["winning_adjusted"] = "boosted"
                card["winning_boost"] = ENTERTAINMENT_BOOST
                entertainment_boosted += 1
        
        # 4. 重新排序（logo由调用方统一重新判定）
        scored_cards.sort(key=lambda x: -x["score"])
        
        logger.info(f"连胜娱乐调整: 合并降级{demoted_count}(最佳拍档+强力单卡), "
                     f"提升{entertainment_boosted}娱乐符文")
        
        return scored_cards

    # ==================== 批量评分 ====================

    def score_candidates(self, candidate_augments, champion_id=None,
                         streak=0, blacktech_bonuses=None,
                         stage=1, augment_level=None):
        """对一组候选符文批量评分"""
        bonuses = blacktech_bonuses or {}
        results = []
        for aug in candidate_augments:
            bonus = bonuses.get(aug, 0)
            score, detail = self.calc_final_score(
                aug, champion_id, streak, bonus, stage, augment_level
            )
            results.append((aug, score, detail))

        results.sort(key=lambda x: x[1], reverse=True)
        return results
