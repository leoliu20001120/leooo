# -*- coding: utf-8 -*-
"""
模拟对局数据：自己 3-2 胜利

雷达图维度分值范围: 1-10
包含自己和对手的完整雷达图数据及5局 Round 数据
"""

from radar_interpretation import (
    RadarDimension,
    RadarSubDimension,
    WEIGHTED_OFFSET,
    parse_radar_chart,
    interpret_radar_chart,
    compare_radar_charts,
)
from highlights import generate_highlight_report, format_highlight_report
from improvements import generate_improvement_report, format_improvement_report


# ======================== 玩家信息 ========================
PLAYER_GID = 10001       # 自己
OPPONENT_GID = 20002     # 对手
PLAYER_TEAM_ID = 1
OPPONENT_TEAM_ID = 2

# ======================== 雷达图数据 ========================
# 格式: { RadarDimension: { "value": 维度总分, "details": { SubDimID: raw, SubDimID+100: weighted } } }

# ---------- 自己的雷达图 ----------
player_radar_chart = {
    RadarDimension.INITIATIVE: {
        "value": 8,  # 先手能力 8分
        "details": {
            # 原始值
            RadarSubDimension.FIRST_HIT_COUNT: 12,   # 有效先手12次
            RadarSubDimension.NORMAL_ACCURACY: 65,    # 普通命中率65%
            RadarSubDimension.SKILL_ACCURACY:  58,    # 技能命中率58%
            RadarSubDimension.CATCH_ACCURACY:  40,    # 投技命中率40%
            RadarSubDimension.EX_ACCURACY:     75,    # 绝技命中率75%
            RadarSubDimension.PRESSURE_CNT:    5,     # 成功压起身5次
            # 加权值 (weight * standard_value)
            RadarSubDimension.FIRST_HIT_COUNT + WEIGHTED_OFFSET: 9,
            RadarSubDimension.NORMAL_ACCURACY + WEIGHTED_OFFSET: 7,
            RadarSubDimension.SKILL_ACCURACY  + WEIGHTED_OFFSET: 6,
            RadarSubDimension.CATCH_ACCURACY  + WEIGHTED_OFFSET: 5,
            RadarSubDimension.EX_ACCURACY     + WEIGHTED_OFFSET: 8,
            RadarSubDimension.PRESSURE_CNT    + WEIGHTED_OFFSET: 7,
        },
    },
    RadarDimension.DAMAGE: {
        "value": 7,  # 输出能力 7分
        "details": {
            RadarSubDimension.AVERAGE_DURATION: 2800,  # 平均连段时长2.8秒
            RadarSubDimension.AVERAGE_DAMAGE:   3200,  # 平均连段伤害3200
            RadarSubDimension.MAX_DURATION:     4500,  # 最大连段时长4.5秒
            RadarSubDimension.MAX_DAMAGE:       6800,  # 最大连段伤害6800
            RadarSubDimension.COMBO_ACCURACY:   72,    # 连段成功率72%
            # 加权值
            RadarSubDimension.AVERAGE_DURATION + WEIGHTED_OFFSET: 6,
            RadarSubDimension.AVERAGE_DAMAGE   + WEIGHTED_OFFSET: 7,
            RadarSubDimension.MAX_DURATION     + WEIGHTED_OFFSET: 8,
            RadarSubDimension.MAX_DAMAGE       + WEIGHTED_OFFSET: 9,
            RadarSubDimension.COMBO_ACCURACY   + WEIGHTED_OFFSET: 6,
        },
    },
    RadarDimension.DEFENSE: {
        "value": 5,  # 防守能力 5分
        "details": {
            RadarSubDimension.BEFENSE_CNT:        8,   # 防御成功8次
            RadarSubDimension.DEF_ATK_CNT:        3,   # 防反成功3次
            RadarSubDimension.DASH_CNT:           6,   # 闪避成功6次
            RadarSubDimension.ESCAPE_SAFETY_RATE: 55,  # 脱身后安全率55%
            # 加权值
            RadarSubDimension.BEFENSE_CNT        + WEIGHTED_OFFSET: 5,
            RadarSubDimension.DEF_ATK_CNT        + WEIGHTED_OFFSET: 3,
            RadarSubDimension.DASH_CNT           + WEIGHTED_OFFSET: 6,
            RadarSubDimension.ESCAPE_SAFETY_RATE + WEIGHTED_OFFSET: 4,
        },
    },
    RadarDimension.STRATEGY: {
        "value": 6,  # 博弈能力 6分
        "details": {
            RadarSubDimension.SWITCH_LEAD_CNT: 7,  # 变招先手7次
            RadarSubDimension.PRIOR_LEAD_CNT:  4,  # 打断招数先手4次
            RadarSubDimension.CLASH_CNT:       5,  # 势均力敌5次
            # 加权值
            RadarSubDimension.SWITCH_LEAD_CNT + WEIGHTED_OFFSET: 7,
            RadarSubDimension.PRIOR_LEAD_CNT  + WEIGHTED_OFFSET: 5,
            RadarSubDimension.CLASH_CNT       + WEIGHTED_OFFSET: 6,
        },
    },
    RadarDimension.RESOURCE_MGMT: {
        "value": 4,  # 资源管理能力 4分（短板）
        "details": {
            RadarSubDimension.NO_RECOVERY_TIME: 18000,  # 体力不恢复时间18秒
            RadarSubDimension.NO_ESC_TIME:      12000,  # 无法脱出时间12秒
            RadarSubDimension.ENERGY_OVERFLOW:  3,      # 能量溢出3次
            RadarSubDimension.ASSIST_CD:        8000,   # 身外身冷却空转8秒
            # 加权值
            RadarSubDimension.NO_RECOVERY_TIME + WEIGHTED_OFFSET: 3,
            RadarSubDimension.NO_ESC_TIME      + WEIGHTED_OFFSET: 4,
            RadarSubDimension.ENERGY_OVERFLOW  + WEIGHTED_OFFSET: 2,
            RadarSubDimension.ASSIST_CD        + WEIGHTED_OFFSET: 5,
        },
    },
}

# ---------- 对手的雷达图 ----------
opponent_radar_chart = {
    RadarDimension.INITIATIVE: {
        "value": 6,  # 先手能力 6分
        "details": {
            RadarSubDimension.FIRST_HIT_COUNT: 8,
            RadarSubDimension.NORMAL_ACCURACY: 55,
            RadarSubDimension.SKILL_ACCURACY:  50,
            RadarSubDimension.CATCH_ACCURACY:  35,
            RadarSubDimension.EX_ACCURACY:     60,
            RadarSubDimension.PRESSURE_CNT:    3,
            RadarSubDimension.FIRST_HIT_COUNT + WEIGHTED_OFFSET: 6,
            RadarSubDimension.NORMAL_ACCURACY + WEIGHTED_OFFSET: 5,
            RadarSubDimension.SKILL_ACCURACY  + WEIGHTED_OFFSET: 5,
            RadarSubDimension.CATCH_ACCURACY  + WEIGHTED_OFFSET: 4,
            RadarSubDimension.EX_ACCURACY     + WEIGHTED_OFFSET: 7,
            RadarSubDimension.PRESSURE_CNT    + WEIGHTED_OFFSET: 4,
        },
    },
    RadarDimension.DAMAGE: {
        "value": 6,  # 输出能力 6分
        "details": {
            RadarSubDimension.AVERAGE_DURATION: 2200,
            RadarSubDimension.AVERAGE_DAMAGE:   2800,
            RadarSubDimension.MAX_DURATION:     3500,
            RadarSubDimension.MAX_DAMAGE:       5200,
            RadarSubDimension.COMBO_ACCURACY:   65,
            RadarSubDimension.AVERAGE_DURATION + WEIGHTED_OFFSET: 5,
            RadarSubDimension.AVERAGE_DAMAGE   + WEIGHTED_OFFSET: 6,
            RadarSubDimension.MAX_DURATION     + WEIGHTED_OFFSET: 6,
            RadarSubDimension.MAX_DAMAGE       + WEIGHTED_OFFSET: 7,
            RadarSubDimension.COMBO_ACCURACY   + WEIGHTED_OFFSET: 5,
        },
    },
    RadarDimension.DEFENSE: {
        "value": 7,  # 防守能力 7分（对手强项）
        "details": {
            RadarSubDimension.BEFENSE_CNT:        14,
            RadarSubDimension.DEF_ATK_CNT:        6,
            RadarSubDimension.DASH_CNT:           9,
            RadarSubDimension.ESCAPE_SAFETY_RATE: 70,
            RadarSubDimension.BEFENSE_CNT        + WEIGHTED_OFFSET: 8,
            RadarSubDimension.DEF_ATK_CNT        + WEIGHTED_OFFSET: 7,
            RadarSubDimension.DASH_CNT           + WEIGHTED_OFFSET: 7,
            RadarSubDimension.ESCAPE_SAFETY_RATE + WEIGHTED_OFFSET: 6,
        },
    },
    RadarDimension.STRATEGY: {
        "value": 5,  # 博弈能力 5分
        "details": {
            RadarSubDimension.SWITCH_LEAD_CNT: 4,
            RadarSubDimension.PRIOR_LEAD_CNT:  3,
            RadarSubDimension.CLASH_CNT:       5,
            RadarSubDimension.SWITCH_LEAD_CNT + WEIGHTED_OFFSET: 5,
            RadarSubDimension.PRIOR_LEAD_CNT  + WEIGHTED_OFFSET: 4,
            RadarSubDimension.CLASH_CNT       + WEIGHTED_OFFSET: 6,
        },
    },
    RadarDimension.RESOURCE_MGMT: {
        "value": 7,  # 资源管理能力 7分（对手强项）
        "details": {
            RadarSubDimension.NO_RECOVERY_TIME: 8000,
            RadarSubDimension.NO_ESC_TIME:      5000,
            RadarSubDimension.ENERGY_OVERFLOW:  1,
            RadarSubDimension.ASSIST_CD:        3000,
            RadarSubDimension.NO_RECOVERY_TIME + WEIGHTED_OFFSET: 7,
            RadarSubDimension.NO_ESC_TIME      + WEIGHTED_OFFSET: 7,
            RadarSubDimension.ENERGY_OVERFLOW  + WEIGHTED_OFFSET: 8,
            RadarSubDimension.ASSIST_CD        + WEIGHTED_OFFSET: 6,
        },
    },
}


# ======================== 5局 Round 数据 ========================
# 结果: 自己 3-2 胜利 (赢第1、3、5局，输第2、4局)

player_rounds = [
    # --- 第1局: 自己赢 ---
    {
        "team_id":       PLAYER_TEAM_ID,
        "yiren_id":      1001,               # 使用异人1001
        "win_team_id":   PLAYER_TEAM_ID,     # 自己赢
        "combo_duration":     8500,           # 连击总时长 8.5秒
        "combo_damage":       12000,          # 连击总伤害 12000
        "combo_count":        4,              # 连击4次
        "combo_max_duration": 3200,           # 最大连段时长 3.2秒
        "combo_max_damage":   5500,           # 最大连段伤害 5500
        "bar_chart": {
            1: 8500,   # 伤害量
            2: 2100,   # 控制时间(ms)
            3: 65,     # 普攻命中率(%)
            4: 58,     # 技能命中率(%)
        },
    },
    # --- 第2局: 自己输 ---
    {
        "team_id":       PLAYER_TEAM_ID,
        "yiren_id":      1001,
        "win_team_id":   OPPONENT_TEAM_ID,   # 对手赢
        "combo_duration":     4200,
        "combo_damage":       5800,
        "combo_count":        2,              # 仅2次连段
        "combo_max_duration": 2500,
        "combo_max_damage":   3200,
        "bar_chart": {
            1: 5800,
            2: 800,
            3: 50,
            4: 45,
        },
    },
    # --- 第3局: 自己赢 ---
    {
        "team_id":       PLAYER_TEAM_ID,
        "yiren_id":      1002,               # 换了异人1002
        "win_team_id":   PLAYER_TEAM_ID,     # 自己赢
        "combo_duration":     10200,
        "combo_damage":       15000,
        "combo_count":        5,
        "combo_max_duration": 4500,           # 高光: 4.5秒长连段
        "combo_max_damage":   6800,           # 高光: 6800高伤害连段
        "bar_chart": {
            1: 11000,
            2: 3200,
            3: 70,
            4: 62,
        },
    },
    # --- 第4局: 自己输 ---
    {
        "team_id":       PLAYER_TEAM_ID,
        "yiren_id":      1002,
        "win_team_id":   OPPONENT_TEAM_ID,   # 对手赢
        "combo_duration":     3500,
        "combo_damage":       4500,
        "combo_count":        2,
        "combo_max_duration": 2000,
        "combo_max_damage":   2800,
        "bar_chart": {
            1: 4500,
            2: 600,
            3: 48,
            4: 40,
        },
    },
    # --- 第5局 (决胜局): 自己赢 ---
    {
        "team_id":       PLAYER_TEAM_ID,
        "yiren_id":      1001,               # 换回异人1001
        "win_team_id":   PLAYER_TEAM_ID,     # 自己赢!
        "combo_duration":     9800,
        "combo_damage":       14200,
        "combo_count":        4,
        "combo_max_duration": 3800,           # 决胜局也有精彩连段
        "combo_max_damage":   6200,
        "bar_chart": {
            1: 10500,
            2: 2800,
            3: 68,
            4: 60,
        },
    },
]

# 对手的 Round 数据
opponent_rounds = [
    # --- 第1局: 对手输 ---
    {
        "team_id":       OPPONENT_TEAM_ID,
        "yiren_id":      2001,
        "win_team_id":   PLAYER_TEAM_ID,
        "combo_duration":     5200,
        "combo_damage":       7000,
        "combo_count":        3,
        "combo_max_duration": 2200,
        "combo_max_damage":   3000,
        "bar_chart": {1: 7000, 2: 1200, 3: 55, 4: 50},
    },
    # --- 第2局: 对手赢 ---
    {
        "team_id":       OPPONENT_TEAM_ID,
        "yiren_id":      2001,
        "win_team_id":   OPPONENT_TEAM_ID,
        "combo_duration":     9000,
        "combo_damage":       11500,
        "combo_count":        4,
        "combo_max_duration": 3500,
        "combo_max_damage":   5000,
        "bar_chart": {1: 9500, 2: 2500, 3: 60, 4: 55},
    },
    # --- 第3局: 对手输 ---
    {
        "team_id":       OPPONENT_TEAM_ID,
        "yiren_id":      2002,
        "win_team_id":   PLAYER_TEAM_ID,
        "combo_duration":     4800,
        "combo_damage":       6200,
        "combo_count":        3,
        "combo_max_duration": 2000,
        "combo_max_damage":   2800,
        "bar_chart": {1: 6200, 2: 1000, 3: 52, 4: 48},
    },
    # --- 第4局: 对手赢 ---
    {
        "team_id":       OPPONENT_TEAM_ID,
        "yiren_id":      2002,
        "win_team_id":   OPPONENT_TEAM_ID,
        "combo_duration":     8500,
        "combo_damage":       11000,
        "combo_count":        4,
        "combo_max_duration": 3200,
        "combo_max_damage":   4800,
        "bar_chart": {1: 9000, 2: 2300, 3: 58, 4: 52},
    },
    # --- 第5局: 对手输 ---
    {
        "team_id":       OPPONENT_TEAM_ID,
        "yiren_id":      2001,
        "win_team_id":   PLAYER_TEAM_ID,
        "combo_duration":     5500,
        "combo_damage":       7500,
        "combo_count":        3,
        "combo_max_duration": 2500,
        "combo_max_damage":   3500,
        "bar_chart": {1: 7500, 2: 1500, 3: 54, 4: 50},
    },
]


# ======================== 运行分析 ========================

def main():
    # 解析雷达图
    player_data = parse_radar_chart(PLAYER_GID, player_radar_chart)
    opponent_data = parse_radar_chart(OPPONENT_GID, opponent_radar_chart)

    print("=" * 60)
    print("          对局复盘报告  (最终比分: 3-2 胜利)")
    print("=" * 60)

    # ---- 模块1: 雷达图解读 ----
    print("\n" + "─" * 60)
    print("  📊 模块一: 雷达图解读")
    print("─" * 60)
    print()
    print(interpret_radar_chart(player_data))
    print()
    print(interpret_radar_chart(opponent_data))
    print()
    print(compare_radar_charts(player_data, opponent_data))

    # ---- 模块2: 高光点 ----
    print("\n" + "─" * 60)
    print("  ⭐ 模块二: 高光点")
    print("─" * 60)
    print()
    highlight_report = generate_highlight_report(
        player_gid=PLAYER_GID,
        radar_data=player_data,
        opponent_radar=opponent_data,
        is_win=True,                # 3-2 胜利
        player_rank="万渊三",
        match_id="MATCH_20260223_10001_20002",
    )
    print(format_highlight_report(highlight_report))

    # ---- 模块3: 提升点 ----
    print("\n" + "─" * 60)
    print("  📌 模块三: 提升点")
    print("─" * 60)
    print()
    improvement_report = generate_improvement_report(
        player_gid=PLAYER_GID,
        radar_data=player_data,
        opponent_radar=opponent_data,
        rounds=player_rounds,
    )
    print(format_improvement_report(improvement_report))


if __name__ == "__main__":
    main()
