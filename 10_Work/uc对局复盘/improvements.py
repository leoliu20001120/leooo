# -*- coding: utf-8 -*-
"""
提升点模块

基于统一的 Δ_dimension（玩家得分 − 对手得分）选取待提升维度：
- 待提升维度: min(Δ_dimension) —— 玩家相较对手能力差距最大、最需优先改进的雷达图维度
- 待提升维度下的薄弱子指标解读
- 单局 Round 中暴露的问题
"""

from typing import Dict, List
from dataclasses import dataclass, field

from radar_interpretation import (
    RadarDimension,
    RadarSubDimension,
    DIMENSION_NAMES,
    SUB_DIMENSION_NAMES,
    DIMENSION_SUB_DIMENSIONS,
    WEIGHTED_OFFSET,
    RadarChartData,
    DimensionData,
    DimensionDelta,
    DimensionDeltaResult,
    SubDimensionData,
    parse_radar_chart,
    get_dimension_level,
    compute_dimension_deltas,
)


# ======================== 常量 & 阈值 ========================

WEAK_COMBO_DAMAGE_THRESHOLD = 1500           # 平均连段伤害 <= 此值视为输出不足
WEAK_COMBO_COUNT_THRESHOLD = 2               # 连段次数 <= 此值视为连段能力不足


# ======================== 提升建议模板 ========================

DIMENSION_IMPROVEMENT_TIPS: Dict[int, str] = {
    RadarDimension.INITIATIVE: (
        "建议多练习起手抢招时机，注意观察对手的动作前摇，"
        "提升命中率的同时寻找安全的先手机会。"
    ),
    RadarDimension.DAMAGE: (
        "建议在训练模式中练习连段路线，提高连段伤害和时长，"
        "熟练掌握角色的核心连段套路。"
    ),
    RadarDimension.DEFENSE: (
        "建议加强防御意识，多练习防反和闪避的时机把握，"
        "被压制时注意寻找安全脱身的窗口。"
    ),
    RadarDimension.STRATEGY: (
        "建议丰富进攻套路，通过变招和打断来获取先手，"
        "减少单一进攻模式，增强博弈层次。"
    ),
    RadarDimension.RESOURCE_MGMT: (
        "建议关注体力和能量的管理节奏，避免资源空转和溢出，"
        "合理规划身外身等技能的使用时机。"
    ),
}

SUB_DIMENSION_IMPROVEMENT_TIPS: Dict[int, str] = {
    # 先手能力
    RadarSubDimension.FIRST_HIT_COUNT: "尝试更多元的起手方式，观察对手习惯来抢先手。",
    RadarSubDimension.NORMAL_ACCURACY: "注意普攻的距离和时机，减少空挥。",
    RadarSubDimension.SKILL_ACCURACY:  "练习技能释放的预判和距离感。",
    RadarSubDimension.CATCH_ACCURACY:  "投技需抓住对手防御僵直或落地的时机。",
    RadarSubDimension.EX_ACCURACY:     "绝技释放需更谨慎，确保命中再使用。",
    RadarSubDimension.PRESSURE_CNT:    "多练习压起身的套路和时机选择。",
    # 输出能力
    RadarSubDimension.AVERAGE_DURATION: "练习更长的连段路线，延长连段控制时间。",
    RadarSubDimension.AVERAGE_DAMAGE:   "优化连段路线，选择高伤害的组合方式。",
    RadarSubDimension.MAX_DURATION:     "尝试角色的极限连段，挖掘最大连段潜力。",
    RadarSubDimension.MAX_DAMAGE:       "研究高伤害连段路线，提升单次爆发。",
    RadarSubDimension.COMBO_ACCURACY:   "减少连段失误，注意搓招的准确性和节奏。",
    # 防守能力
    RadarSubDimension.BEFENSE_CNT:        "多观察对手进攻节奏，提高防御反应。",
    RadarSubDimension.DEF_ATK_CNT:        "防御成功后及时反击，把握防反窗口。",
    RadarSubDimension.DASH_CNT:           "练习闪避时机，利用无敌帧规避攻击。",
    RadarSubDimension.ESCAPE_SAFETY_RATE: "脱身后不要急于反击，先确保安全再行动。",
    # 博弈能力
    RadarSubDimension.SWITCH_LEAD_CNT: "进攻时多尝试变招，打乱对手防御节奏。",
    RadarSubDimension.PRIOR_LEAD_CNT:  "观察对手招式前摇，寻找打断机会。",
    RadarSubDimension.CLASH_CNT:       "把握交招时机，争取更多势均力敌的有利对拼。",
    # 资源管理能力
    RadarSubDimension.NO_RECOVERY_TIME: "注意体力恢复节奏，避免长时间处于低体力状态。",
    RadarSubDimension.NO_ESC_TIME:      "合理保留脱出资源，避免在高压时无法脱身。",
    RadarSubDimension.ENERGY_OVERFLOW:  "及时使用能量技能，避免能量溢出浪费。",
    RadarSubDimension.ASSIST_CD:        "规划身外身使用时机，减少冷却空转时间。",
}


# ======================== 数据结构 ========================

@dataclass
class ImprovementItem:
    """单个提升点"""
    category: str        # 分类：improvement_dim / sub_dimension / round
    title: str           # 提升点标题
    description: str     # 问题描述
    suggestion: str      # 提升建议
    priority: int = 0    # 优先级（数值越大越优先）
    round_idx: int = -1  # 关联的 Round 索引（-1 表示全局）


@dataclass
class ImprovementReport:
    """提升点报告"""
    player_gid: int
    improvement_dim: DimensionDelta = None   # 待提升维度 (min Δ)
    items: List[ImprovementItem] = field(default_factory=list)


# ======================== 核心逻辑 ========================

def extract_improvement_dimension(
    delta_result: DimensionDeltaResult,
    player_data: RadarChartData,
) -> List[ImprovementItem]:
    """
    基于 min(Δ_dimension) 提取待提升维度及其子指标

    Args:
        delta_result: 统一的维度分差计算结果
        player_data:  玩家雷达图数据

    Returns:
        List[ImprovementItem]: 待提升维度相关的提升点
    """
    items = []
    imp = delta_result.improvement_dim
    if not imp:
        return items

    level = get_dimension_level(imp.player_score)
    dim_tip = DIMENSION_IMPROVEMENT_TIPS.get(imp.dim_id, "建议针对性练习提升该维度。")

    items.append(ImprovementItem(
        category="improvement_dim",
        title=f"待提升维度: {imp.name}",
        description=(
            f"本局对比对手，{imp.name}差距最大 (Δ = {imp.delta:+d})，"
            f"玩家 {imp.player_score} 分 vs 对手 {imp.opponent_score} 分（{level}），"
            f"是最需要优先改进的方向。"
        ),
        suggestion=dim_tip,
        priority=100,  # 最高优先级
    ))

    # 找到该维度下的子指标，按加权值升序排列（最弱的排前面）
    player_dims = {d.dim_id: d for d in player_data.dimensions}
    dim_data = player_dims.get(imp.dim_id)
    if dim_data:
        sorted_subs = sorted(dim_data.sub_dimensions, key=lambda s: s.weighted_value)
        for sub in sorted_subs:
            sub_tip = SUB_DIMENSION_IMPROVEMENT_TIPS.get(
                sub.sub_dim_id, "建议针对该指标进行专项练习。"
            )
            items.append(ImprovementItem(
                category="sub_dimension",
                title=f"{sub.name}待提升",
                description=(
                    f"在待提升维度「{imp.name}」下，{sub.name}加权值为 {sub.weighted_value}，"
                    f"原始值为 {sub.raw_value}。"
                ),
                suggestion=sub_tip,
                priority=90 - sub.weighted_value,  # 加权值越低优先级越高
            ))

    return items


def extract_round_weaknesses(rounds: List[Dict]) -> List[ImprovementItem]:
    """
    从单局 Round 数据中提取暴露的问题

    Args:
        rounds: Round 数据列表

    Returns:
        List[ImprovementItem]: Round 级提升点列表
    """
    items = []

    for idx, rnd in enumerate(rounds):
        combo_count = rnd.get("combo_count", 0)
        combo_damage = rnd.get("combo_damage", 0)

        # 连段次数过少
        if combo_count <= WEAK_COMBO_COUNT_THRESHOLD and combo_count > 0:
            items.append(ImprovementItem(
                category="round",
                title=f"第{idx + 1}局 连段次数少",
                description=f"第{idx + 1}局仅完成 {combo_count} 次连段，进攻机会不足。",
                suggestion="尝试更主动地寻找进攻机会，通过先手或防反创造连段起手。",
                priority=20,
                round_idx=idx,
            ))

        # 平均连段伤害低
        if combo_count > 0:
            avg_damage = combo_damage // combo_count
            if avg_damage <= WEAK_COMBO_DAMAGE_THRESHOLD:
                items.append(ImprovementItem(
                    category="round",
                    title=f"第{idx + 1}局 连段伤害偏低",
                    description=f"第{idx + 1}局平均连段伤害仅 {avg_damage}，输出效率有待提升。",
                    suggestion="练习更高效的连段路线，确保每次连段都能打出足够伤害。",
                    priority=25,
                    round_idx=idx,
                ))

        # 输掉的局
        win_team_id = rnd.get("win_team_id", 0)
        team_id = rnd.get("team_id", 0)
        if win_team_id != 0 and win_team_id != team_id:
            items.append(ImprovementItem(
                category="round",
                title=f"第{idx + 1}局 落败",
                description=f"第{idx + 1}局未能取胜，需复盘本局的关键失误点。",
                suggestion="回顾本局的关键时刻，分析在哪些节点可以做出更好的选择。",
                priority=15,
                round_idx=idx,
            ))

    return items


def generate_improvement_report(
    player_gid: int,
    radar_data: RadarChartData,
    opponent_radar: RadarChartData,
    rounds: List[Dict],
) -> ImprovementReport:
    """
    生成完整的提升点报告

    核心: 待提升维度 = min(Δ_dimension)，基于玩家与对手的分差选取

    Args:
        player_gid:     玩家 GID
        radar_data:     玩家雷达图数据
        opponent_radar: 对手雷达图数据（必须）
        rounds:         玩家各局 Round 数据

    Returns:
        ImprovementReport: 提升点报告
    """
    # 统一计算维度分差
    delta_result = compute_dimension_deltas(radar_data, opponent_radar)

    report = ImprovementReport(
        player_gid=player_gid,
        improvement_dim=delta_result.improvement_dim,
    )

    # 1. 待提升维度（min Δ）及其子指标
    report.items.extend(extract_improvement_dimension(delta_result, radar_data))

    # 2. Round 级问题
    report.items.extend(extract_round_weaknesses(rounds))

    # 按优先级降序排列
    report.items.sort(key=lambda item: item.priority, reverse=True)

    return report


def format_improvement_report(report: ImprovementReport) -> str:
    """
    格式化提升点报告为可读文本

    Args:
        report: 提升点报告

    Returns:
        str: 格式化文本
    """
    lines = [f"===== 玩家 {report.player_gid} 提升点 =====\n"]

    if not report.items:
        lines.append("本场对局表现全面，暂无明显短板！")
        return "\n".join(lines)

    # 待提升维度总结
    if report.improvement_dim:
        imp = report.improvement_dim
        lines.append(f"🎯 待提升维度: {imp.name} (Δ = {imp.delta:+d}, "
                      f"玩家{imp.player_score} vs 对手{imp.opponent_score})")
        lines.append("")

    for i, item in enumerate(report.items, 1):
        lines.append(f"📌 提升点{i}: {item.title}")
        lines.append(f"   问题: {item.description}")
        lines.append(f"   建议: {item.suggestion}")
        lines.append("")

    lines.append(f"共发现 {len(report.items)} 个提升点，建议优先关注排名靠前的问题。")

    return "\n".join(lines)
