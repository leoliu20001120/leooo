# -*- coding: utf-8 -*-
"""
雷达图解读模块

根据玩家雷达图五维数据（先手能力、输出能力、防守能力、博弈能力、资源管理能力），
对每个维度及其子指标进行解读，生成可读的文字分析。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


# ======================== 常量定义 ========================

# 雷达图维度
class RadarDimension:
    INVALID       = 0
    INITIATIVE    = 1  # 先手能力
    DAMAGE        = 2  # 输出能力
    DEFENSE       = 3  # 防守能力
    STRATEGY      = 4  # 博弈能力
    RESOURCE_MGMT = 5  # 资源管理能力


# 维度名称映射
DIMENSION_NAMES: Dict[int, str] = {
    RadarDimension.INITIATIVE:    "先手能力",
    RadarDimension.DAMAGE:        "输出能力",
    RadarDimension.DEFENSE:       "防守能力",
    RadarDimension.STRATEGY:      "博弈能力",
    RadarDimension.RESOURCE_MGMT: "资源管理能力",
}

# 雷达图子维度（原始值）
class RadarSubDimension:
    INVALID = 0
    # 先手能力
    FIRST_HIT_COUNT = 1   # 有效先手次数
    NORMAL_ACCURACY = 2   # 普通命中率
    SKILL_ACCURACY  = 3   # 技能命中率
    CATCH_ACCURACY  = 4   # 投技命中率
    EX_ACCURACY     = 5   # 绝技命中率
    PRESSURE_CNT    = 6   # 成功压起身次数
    # 输出能力
    AVERAGE_DURATION = 11  # 平均连段时长
    AVERAGE_DAMAGE   = 12  # 平均连段伤害
    MAX_DURATION     = 13  # 最大连段时长
    MAX_DAMAGE       = 14  # 最大连段伤害
    COMBO_ACCURACY   = 15  # 连段成功率
    # 防守能力
    BEFENSE_CNT        = 21  # 防御成功次数
    DEF_ATK_CNT        = 22  # 防反成功次数
    DASH_CNT           = 23  # 闪避成功次数
    ESCAPE_SAFETY_RATE = 24  # 脱身后安全率
    # 博弈能力
    SWITCH_LEAD_CNT = 31  # 变招先手次数
    PRIOR_LEAD_CNT  = 32  # 打断招数先手次数
    CLASH_CNT       = 33  # 势均力敌次数
    # 资源管理能力
    NO_RECOVERY_TIME = 41  # 体力不恢复时间
    NO_ESC_TIME      = 42  # 无法脱出的总受击时间
    ENERGY_OVERFLOW  = 43  # 能量溢出
    ASSIST_CD        = 44  # 身外身冷却空转时间


# 加权值偏移量：原始子维度编号 + 100 = 加权值编号
WEIGHTED_OFFSET = 100

# 子维度名称映射
SUB_DIMENSION_NAMES: Dict[int, str] = {
    RadarSubDimension.FIRST_HIT_COUNT: "有效先手次数",
    RadarSubDimension.NORMAL_ACCURACY: "普通命中率",
    RadarSubDimension.SKILL_ACCURACY:  "技能命中率",
    RadarSubDimension.CATCH_ACCURACY:  "投技命中率",
    RadarSubDimension.EX_ACCURACY:     "绝技命中率",
    RadarSubDimension.PRESSURE_CNT:    "成功压起身次数",

    RadarSubDimension.AVERAGE_DURATION: "平均连段时长",
    RadarSubDimension.AVERAGE_DAMAGE:   "平均连段伤害",
    RadarSubDimension.MAX_DURATION:     "最大连段时长",
    RadarSubDimension.MAX_DAMAGE:       "最大连段伤害",
    RadarSubDimension.COMBO_ACCURACY:   "连段成功率",

    RadarSubDimension.BEFENSE_CNT:        "防御成功次数",
    RadarSubDimension.DEF_ATK_CNT:        "防反成功次数",
    RadarSubDimension.DASH_CNT:           "闪避成功次数",
    RadarSubDimension.ESCAPE_SAFETY_RATE: "脱身后安全率",

    RadarSubDimension.SWITCH_LEAD_CNT: "变招先手次数",
    RadarSubDimension.PRIOR_LEAD_CNT:  "打断招数先手次数",
    RadarSubDimension.CLASH_CNT:       "势均力敌次数",

    RadarSubDimension.NO_RECOVERY_TIME: "体力不恢复时间",
    RadarSubDimension.NO_ESC_TIME:      "无法脱出的总受击时间",
    RadarSubDimension.ENERGY_OVERFLOW:  "能量溢出",
    RadarSubDimension.ASSIST_CD:        "身外身冷却空转时间",
}

# 各维度包含的子维度列表
DIMENSION_SUB_DIMENSIONS: Dict[int, List[int]] = {
    RadarDimension.INITIATIVE: [
        RadarSubDimension.FIRST_HIT_COUNT,
        RadarSubDimension.NORMAL_ACCURACY,
        RadarSubDimension.SKILL_ACCURACY,
        RadarSubDimension.CATCH_ACCURACY,
        RadarSubDimension.EX_ACCURACY,
        RadarSubDimension.PRESSURE_CNT,
    ],
    RadarDimension.DAMAGE: [
        RadarSubDimension.AVERAGE_DURATION,
        RadarSubDimension.AVERAGE_DAMAGE,
        RadarSubDimension.MAX_DURATION,
        RadarSubDimension.MAX_DAMAGE,
        RadarSubDimension.COMBO_ACCURACY,
    ],
    RadarDimension.DEFENSE: [
        RadarSubDimension.BEFENSE_CNT,
        RadarSubDimension.DEF_ATK_CNT,
        RadarSubDimension.DASH_CNT,
        RadarSubDimension.ESCAPE_SAFETY_RATE,
    ],
    RadarDimension.STRATEGY: [
        RadarSubDimension.SWITCH_LEAD_CNT,
        RadarSubDimension.PRIOR_LEAD_CNT,
        RadarSubDimension.CLASH_CNT,
    ],
    RadarDimension.RESOURCE_MGMT: [
        RadarSubDimension.NO_RECOVERY_TIME,
        RadarSubDimension.NO_ESC_TIME,
        RadarSubDimension.ENERGY_OVERFLOW,
        RadarSubDimension.ASSIST_CD,
    ],
}


# ======================== 数据结构 ========================

@dataclass
class SubDimensionData:
    """子维度数据，同时包含原始值和加权值"""
    sub_dim_id: int
    name: str
    raw_value: int = 0       # 原始指标值
    weighted_value: int = 0  # 加权值 (weight * standard_value)


@dataclass
class DimensionData:
    """维度数据"""
    dim_id: int
    name: str
    score: int = 0  # 维度总分
    sub_dimensions: List[SubDimensionData] = field(default_factory=list)


@dataclass
class RadarChartData:
    """雷达图完整数据"""
    player_gid: int = 0
    dimensions: List[DimensionData] = field(default_factory=list)


@dataclass
class DimensionDelta:
    """单个维度的分差数据"""
    dim_id: int
    name: str
    player_score: int    # 玩家得分
    opponent_score: int  # 对手得分
    delta: int           # Δ = 玩家得分 - 对手得分


@dataclass
class DimensionDeltaResult:
    """全部维度分差计算结果"""
    deltas: List[DimensionDelta]          # 所有维度的 Δ 列表
    advantage_dim: Optional[DimensionDelta] = None   # 优势维度: max(Δ)
    improvement_dim: Optional[DimensionDelta] = None  # 待提升维度: min(Δ)


# ======================== 核心逻辑 ========================

def parse_radar_chart(player_gid: int, radar_chart: Dict) -> RadarChartData:
    """
    解析雷达图原始数据（来自 proto 的 RadarChart）

    Args:
        player_gid: 玩家 GID
        radar_chart: proto RadarChart 对应的 dict，格式:
            {
                dimension_id: {
                    "value": int,
                    "details": { sub_dim_id: int_value, ... }
                },
                ...
            }

    Returns:
        RadarChartData: 结构化的雷达图数据
    """
    result = RadarChartData(player_gid=player_gid)

    for dim_id in sorted(DIMENSION_NAMES.keys()):
        dim_data = radar_chart.get(dim_id, {})
        details = dim_data.get("details", {})

        dimension = DimensionData(
            dim_id=dim_id,
            name=DIMENSION_NAMES[dim_id],
            score=dim_data.get("value", 0),
        )

        for sub_dim_id in DIMENSION_SUB_DIMENSIONS.get(dim_id, []):
            sub_dim = SubDimensionData(
                sub_dim_id=sub_dim_id,
                name=SUB_DIMENSION_NAMES.get(sub_dim_id, f"未知指标({sub_dim_id})"),
                raw_value=details.get(sub_dim_id, 0),
                weighted_value=details.get(sub_dim_id + WEIGHTED_OFFSET, 0),
            )
            dimension.sub_dimensions.append(sub_dim)

        result.dimensions.append(dimension)

    return result


def get_dimension_level(score: int) -> str:
    """
    根据维度分数返回等级评价

    Args:
        score: 维度分数 (1-10)

    Returns:
        str: 等级描述
    """
    if score >= 9:
        return "极强"
    elif score >= 7:
        return "优秀"
    elif score >= 5:
        return "良好"
    elif score >= 4:
        return "一般"
    elif score >= 2:
        return "较弱"
    else:
        return "薄弱"


def interpret_dimension(dimension: DimensionData) -> str:
    """
    解读单个雷达图维度

    Args:
        dimension: 维度数据

    Returns:
        str: 维度解读文本
    """
    level = get_dimension_level(dimension.score)
    lines = [f"【{dimension.name}】得分: {dimension.score} ({level})"]

    # 按加权值降序排列子维度，展示各指标贡献
    sorted_subs = sorted(dimension.sub_dimensions, key=lambda s: s.weighted_value, reverse=True)

    for sub in sorted_subs:
        lines.append(f"  - {sub.name}: 原始值={sub.raw_value}, 加权值={sub.weighted_value}")

    return "\n".join(lines)


def interpret_radar_chart(radar_data: RadarChartData) -> str:
    """
    生成完整的雷达图解读报告

    Args:
        radar_data: 雷达图数据

    Returns:
        str: 完整解读文本
    """
    lines = [f"===== 玩家 {radar_data.player_gid} 雷达图解读 =====\n"]

    # 总览：按分数排序
    sorted_dims = sorted(radar_data.dimensions, key=lambda d: d.score, reverse=True)

    lines.append("▶ 总览:")
    for dim in sorted_dims:
        level = get_dimension_level(dim.score)
        lines.append(f"  {dim.name}: {dim.score}分 ({level})")

    # 最强维度 & 最弱维度
    if sorted_dims:
        strongest = sorted_dims[0]
        weakest = sorted_dims[-1]
        lines.append(f"\n▶ 最强维度: {strongest.name} ({strongest.score}分)")
        lines.append(f"▶ 最弱维度: {weakest.name} ({weakest.score}分)")

    # 各维度详细解读
    lines.append("\n▶ 详细解读:")
    for dim in radar_data.dimensions:
        lines.append("")
        lines.append(interpret_dimension(dim))

    return "\n".join(lines)


def compute_dimension_deltas(
    player_data: RadarChartData,
    opponent_data: RadarChartData,
) -> DimensionDeltaResult:
    """
    统一计算所有维度的分差 Δ_dimension = 玩家得分 − 对手得分

    优势维度:   max(Δ_dimension) —— 玩家相较对手能力优势最明显的维度
    待提升维度: min(Δ_dimension) —— 玩家相较对手能力差距最大的维度

    Args:
        player_data:   玩家雷达图数据
        opponent_data: 对手雷达图数据

    Returns:
        DimensionDeltaResult: 包含所有维度 Δ、优势维度、待提升维度
    """
    player_dims = {d.dim_id: d for d in player_data.dimensions}
    opponent_dims = {d.dim_id: d for d in opponent_data.dimensions}

    deltas: List[DimensionDelta] = []

    for dim_id in sorted(DIMENSION_NAMES.keys()):
        dim_name = DIMENSION_NAMES[dim_id]
        p_score = player_dims.get(dim_id, DimensionData(dim_id=dim_id, name=dim_name)).score
        o_score = opponent_dims.get(dim_id, DimensionData(dim_id=dim_id, name=dim_name)).score

        deltas.append(DimensionDelta(
            dim_id=dim_id,
            name=dim_name,
            player_score=p_score,
            opponent_score=o_score,
            delta=p_score - o_score,
        ))

    # 优势维度: max(Δ)
    advantage_dim = max(deltas, key=lambda d: d.delta) if deltas else None
    # 待提升维度: min(Δ)
    improvement_dim = min(deltas, key=lambda d: d.delta) if deltas else None

    return DimensionDeltaResult(
        deltas=deltas,
        advantage_dim=advantage_dim,
        improvement_dim=improvement_dim,
    )


def compare_radar_charts(player_data: RadarChartData, opponent_data: RadarChartData) -> str:
    """
    对比两名玩家的雷达图（基于统一的 Δ_dimension 计算）

    Args:
        player_data:   当前玩家雷达图数据
        opponent_data: 对手雷达图数据

    Returns:
        str: 对比解读文本
    """
    result = compute_dimension_deltas(player_data, opponent_data)

    lines = [f"===== 雷达图对比: 玩家{player_data.player_gid} vs 玩家{opponent_data.player_gid} =====\n"]

    for d in result.deltas:
        if d.delta > 0:
            symbol = "🟢"
        elif d.delta < 0:
            symbol = "🔴"
        else:
            symbol = "🟡"
        lines.append(f"  {symbol} {d.name}: {d.player_score} vs {d.opponent_score} (Δ = {d.delta:+d})")

    if result.advantage_dim:
        ad = result.advantage_dim
        lines.append(f"\n▶ 优势维度 (max Δ): {ad.name} (Δ = {ad.delta:+d}, 玩家{ad.player_score} vs 对手{ad.opponent_score})")
    if result.improvement_dim:
        im = result.improvement_dim
        lines.append(f"▶ 待提升维度 (min Δ): {im.name} (Δ = {im.delta:+d}, 玩家{im.player_score} vs 对手{im.opponent_score})")

    return "\n".join(lines)
