#!/usr/bin/env python3
"""
UC 对局复盘 — 玩家数据分析报告
读取 46 个 JSON 对局数据，生成交互式 HTML 报告
模块一：玩家整体表现（五维雷达图 + 子指标）
模块二：分角色进步分析 + 短板诊断 + 建议
"""

import json
import os
import math
from collections import defaultdict

# ============================================================
# 1. 指标元信息
# ============================================================

RADAR_DIM_NAMES = {
    "1": "先手",
    "2": "输出",
    "3": "防守",
    "4": "博弈",
    "5": "资源管理",
}

BAR_METRICS = {
    "1": {"name": "先手次数", "unit": "次", "type": "count"},
    "2": {"name": "普攻命中率", "unit": "%", "type": "rate_10000"},
    "3": {"name": "投技命中率", "unit": "%", "type": "rate_10000"},
    "4": {"name": "技能命中率", "unit": "%", "type": "rate_10000"},
    "5": {"name": "绝技命中率", "unit": "%", "type": "rate_10000"},
    "6": {"name": "起身压制成功次数", "unit": "次", "type": "count"},
    "7": {"name": "连段成功率", "unit": "%", "type": "rate_10000"},
    "8": {"name": "平均连段时长", "unit": "秒", "type": "ms"},
    "9": {"name": "最大连段时长", "unit": "秒", "type": "ms"},
    "10": {"name": "平均连段伤害", "unit": "", "type": "damage_10000"},
    "11": {"name": "最大连段伤害", "unit": "", "type": "count"},
    "12": {"name": "防御次数", "unit": "次", "type": "count"},
    "13": {"name": "防御成功次数", "unit": "次", "type": "count"},
    "14": {"name": "防御反击触发次数", "unit": "次", "type": "count"},
    "15": {"name": "防御反击造成伤害次数", "unit": "次", "type": "count"},
    "16": {"name": "防御反击命中次数", "unit": "次", "type": "count"},
    "17": {"name": "解招次数", "unit": "次", "type": "count"},
    "18": {"name": "脱出后反打成功率", "unit": "%", "type": "rate_100"},
    "19": {"name": "脱出后安全率", "unit": "%", "type": "rate_100"},
    "20": {"name": "极限闪避次数", "unit": "次", "type": "count"},
    "21": {"name": "倒地受击次数", "unit": "次", "type": "count"},
    "22": {"name": "取消变招获取先手次数", "unit": "次", "type": "count"},
    "23": {"name": "打断对手获取先手次数", "unit": "次", "type": "count"},
    "24": {"name": "触发势均力敌次数", "unit": "次", "type": "count"},
    "25": {"name": "体力消耗", "unit": "格", "type": "stamina"},
    "26": {"name": "体力恢复", "unit": "格", "type": "stamina"},
    "27": {"name": "防御暂停体力恢复时间", "unit": "秒", "type": "ms"},
    "28": {"name": "无法脱出总受击时间", "unit": "秒", "type": "ms"},
    "29": {"name": "炁满时累积伤害量", "unit": "", "type": "count"},
    "30": {"name": "身外身冷却空转时间", "unit": "秒", "type": "ms"},
    "31": {"name": "垫步次数", "unit": "次", "type": "count"},
    "32": {"name": "取消使用次数", "unit": "次", "type": "count"},
    "33": {"name": "取消普攻次数", "unit": "次", "type": "count"},
    "34": {"name": "取消技能次数", "unit": "次", "type": "count"},
    "35": {"name": "取消防反次数", "unit": "次", "type": "count"},
    "36": {"name": "取消其他状态次数", "unit": "次", "type": "count"},
    "37": {"name": "对局时长", "unit": "秒", "type": "ms"},
}

# 指标分组（用于可视化）
METRIC_GROUPS = {
    "进攻": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    "防守": ["12", "13", "14", "15", "16", "17", "18", "19", "20", "21"],
    "博弈": ["22", "23", "24"],
    "资源管理": ["25", "26", "27", "28", "29", "30"],
    "操作技巧": ["31", "32", "33", "34", "35", "36"],
}

# 角色 ID → 名字映射（常见）
YIREN_NAMES = {
    9001: "张楚岚", 9002: "冯宝宝", 9003: "王也", 9004: "诸葛青",
    9005: "风星潼", 9006: "张灵玉", 9007: "陆瑾", 9008: "夏禾",
    9009: "无根生", 9010: "风正豪", 9011: "柳妍妍", 9012: "吕仙",
    9013: "陈朵", 9014: "王并", 9015: "高宁", 9016: "唐茗翠",
    9017: "荔枝仙", 9072: "碧莲",
}


def get_yiren_name(yid):
    return YIREN_NAMES.get(yid, f"异人{yid}")


def format_value(raw, metric_type):
    """将原始数据值转换为可读值"""
    if raw is None:
        return None
    if metric_type == "rate_10000":
        return round(raw / 100, 2)  # 万分比 → 百分比
    elif metric_type == "rate_100":
        return raw  # 已经是百分比（0~100）
    elif metric_type == "ms":
        return round(raw / 1000, 2)  # 毫秒 → 秒
    elif metric_type == "damage_10000":
        return round(raw / 10000, 1)  # 伤害万分比
    elif metric_type == "stamina":
        return round(raw / 1000, 1)  # 千分比 → 格
    return raw


def format_avg(raw, metric_type):
    """将 average/limit 值转换为可读值"""
    if raw is None:
        return None
    if metric_type in ("rate_10000", "rate_100"):
        return raw  # average 本身就是百分比尺度
    elif metric_type == "ms":
        return round(raw / 1000, 2)
    elif metric_type == "damage_10000":
        return round(raw / 10000, 1)
    elif metric_type == "stamina":
        return round(raw / 1000, 1)
    return raw


# ============================================================
# 2. 数据读取
# ============================================================

def load_all_games(folder):
    """读取所有 JSON 文件，返回 list[dict]"""
    games = []
    for i in range(1, 47):
        fp = os.path.join(folder, f"{i}.json")
        if not os.path.exists(fp):
            continue
        with open(fp, "r") as f:
            data = json.load(f)
        data["_file_index"] = i
        games.append(data)
    return games


def extract_player_data(games):
    """
    从全部对局中提取 current_gid 玩家的数据。
    返回:
      - match_records: 每局一条记录 {file_index, gid, arena_phase, sub_phase, radar, rounds_detail, win}
      - round_records: 每个 round 一条 {file_index, round_idx, yiren_id, win, bar_metrics, ...}
    """
    match_records = []
    round_records = []

    for game in games:
        gid = str(game["current_gid"])
        fi = game["_file_index"]
        player = game["players"].get(gid)
        if not player:
            continue

        # 整局信息
        arena_phase = player.get("arena_phase")
        sub_phase = player.get("sub_phase")
        radar = {}
        radar_detail = {}
        if "radar_chart" in player and "dimension" in player["radar_chart"]:
            for dim_id, dim_data in player["radar_chart"]["dimension"].items():
                radar[dim_id] = dim_data.get("value")
                radar_detail[dim_id] = {
                    "value": dim_data.get("value"),
                    "average": dim_data.get("average"),
                    "detail": dim_data.get("detail", {}),
                }

        # 段位均值（从 player "0" 获取）
        avg_radar = {}
        p0 = game["players"].get("0")
        if p0 and "radar_chart" in p0 and "dimension" in p0["radar_chart"]:
            for dim_id, dim_data in p0["radar_chart"]["dimension"].items():
                avg_radar[dim_id] = dim_data.get("value")

        # 回合信息
        rounds = player.get("rounds", [])
        team_id = rounds[0]["team_id"] if rounds else None

        # 判断胜负：统计 win_team_id == team_id 的 round 数
        wins_in_match = sum(1 for r in rounds if r.get("win_team_id") == team_id)
        losses_in_match = len(rounds) - wins_in_match
        match_win = wins_in_match >= 3  # 先赢3局即获胜

        match_records.append({
            "file_index": fi,
            "gid": int(gid),
            "arena_phase": arena_phase,
            "sub_phase": sub_phase,
            "radar": radar,
            "radar_detail": radar_detail,
            "avg_radar": avg_radar,
            "team_id": team_id,
            "round_count": len(rounds),
            "wins_in_match": wins_in_match,
            "losses_in_match": losses_in_match,
            "match_win": match_win,
        })

        for ri, rnd in enumerate(rounds):
            yiren_id = rnd.get("yiren_id")
            round_win = rnd.get("win_team_id") == team_id

            # 提取 bar_chart_extension
            bar_ext = rnd.get("bar_chart_extension", {})
            bar_values = {}
            bar_avgs = {}
            bar_limits = {}
            for mk in BAR_METRICS:
                entry = bar_ext.get(mk, {})
                raw_val = entry.get("value")
                raw_avg = entry.get("average")
                raw_lim = entry.get("limit")
                mt = BAR_METRICS[mk]["type"]
                bar_values[mk] = format_value(raw_val, mt)
                bar_avgs[mk] = format_avg(raw_avg, mt)
                bar_limits[mk] = format_avg(raw_lim, mt)

            round_records.append({
                "file_index": fi,
                "round_idx": ri,
                "yiren_id": yiren_id,
                "yiren_name": get_yiren_name(yiren_id),
                "round_win": round_win,
                "bar_values": bar_values,
                "bar_avgs": bar_avgs,
                "bar_limits": bar_limits,
            })

    return match_records, round_records


# ============================================================
# 3. HTML 报告生成
# ============================================================

def generate_html_report(match_records, round_records):
    """生成完整的交互式 HTML 报告"""

    # --- 统计数据 ---
    total_matches = len(match_records)
    total_wins = sum(1 for m in match_records if m["match_win"])
    total_losses = total_matches - total_wins
    win_rate = round(total_wins / total_matches * 100, 1) if total_matches > 0 else 0

    # 总 round 数
    total_rounds = len(round_records)
    round_wins = sum(1 for r in round_records if r["round_win"])
    round_wr = round(round_wins / total_rounds * 100, 1) if total_rounds > 0 else 0

    # 五维雷达数据（按局平均）
    radar_sums = defaultdict(list)
    avg_radar_sums = defaultdict(list)
    for m in match_records:
        for d in ["1", "2", "3", "4", "5"]:
            if m["radar"].get(d) is not None:
                radar_sums[d].append(m["radar"][d] / 1000)  # 万分 → 百分
            if m["avg_radar"].get(d) is not None:
                avg_radar_sums[d].append(m["avg_radar"][d] / 1000)

    radar_player = [round(sum(radar_sums[d]) / len(radar_sums[d]), 1) if radar_sums[d] else 0 for d in ["1", "2", "3", "4", "5"]]
    radar_avg = [round(sum(avg_radar_sums[d]) / len(avg_radar_sums[d]), 1) if avg_radar_sums[d] else 0 for d in ["1", "2", "3", "4", "5"]]

    # 五维趋势数据
    radar_trend_data = {d: [] for d in ["1", "2", "3", "4", "5"]}
    radar_trend_x = []
    for m in match_records:
        radar_trend_x.append(m["file_index"])
        for d in ["1", "2", "3", "4", "5"]:
            v = m["radar"].get(d)
            radar_trend_data[d].append(round(v / 1000, 1) if v else None)

    # 角色使用统计
    yiren_stats = defaultdict(lambda: {"rounds": 0, "wins": 0, "bar_sums": defaultdict(list)})
    for r in round_records:
        yid = r["yiren_id"]
        yiren_stats[yid]["rounds"] += 1
        if r["round_win"]:
            yiren_stats[yid]["wins"] += 1
        for mk in BAR_METRICS:
            v = r["bar_values"].get(mk)
            if v is not None:
                yiren_stats[yid]["bar_sums"][mk].append(v)

    # 角色列表排序（按使用次数）
    yiren_list = sorted(yiren_stats.keys(), key=lambda y: -yiren_stats[y]["rounds"])

    # 各角色平均指标
    yiren_metric_avgs = {}
    for yid in yiren_list:
        yma = {}
        for mk in BAR_METRICS:
            vals = yiren_stats[yid]["bar_sums"][mk]
            yma[mk] = round(sum(vals) / len(vals), 2) if vals else None
        yiren_metric_avgs[yid] = yma

    # 全局平均（所有 round）
    global_bar_sums = defaultdict(list)
    for r in round_records:
        for mk in BAR_METRICS:
            v = r["bar_values"].get(mk)
            if v is not None:
                global_bar_sums[mk].append(v)
    global_bar_avg = {}
    for mk in BAR_METRICS:
        vals = global_bar_sums[mk]
        global_bar_avg[mk] = round(sum(vals) / len(vals), 2) if vals else None

    # 段位均值（从 bar_avgs 提取，取第一个非空）
    tier_avg = {}
    for r in round_records:
        for mk in BAR_METRICS:
            if mk not in tier_avg and r["bar_avgs"].get(mk) is not None:
                tier_avg[mk] = r["bar_avgs"][mk]

    # 段位变化趋势
    phase_trend = []
    for m in match_records:
        phase_trend.append({
            "x": m["file_index"],
            "arena_phase": m.get("arena_phase"),
            "sub_phase": m.get("sub_phase"),
        })

    # 各角色在不同对局中的使用情况（用于趋势图）
    yiren_by_match = defaultdict(list)
    for r in round_records:
        yiren_by_match[r["file_index"]].append(r["yiren_id"])

    # --- 短板诊断 ---
    # 对每个角色，找出 "玩家均值 vs 段位均值" 差距最大的指标（负方向）
    weakness_analysis = {}
    for yid in yiren_list:
        weaknesses = []
        for mk in BAR_METRICS:
            player_val = yiren_metric_avgs[yid].get(mk)
            tier_val = tier_avg.get(mk)
            if player_val is None or tier_val is None or tier_val == 0:
                continue
            # 倒地受击、体力消耗、受击时间、冷却空转 越小越好
            if mk in ("21", "25", "27", "28", "30"):
                gap = (player_val - tier_val) / abs(tier_val)
            else:
                gap = (tier_val - player_val) / abs(tier_val)
            if gap > 0.1:  # 差距超过 10% 才算短板
                weaknesses.append({
                    "metric_id": mk,
                    "metric_name": BAR_METRICS[mk]["name"],
                    "player_val": player_val,
                    "tier_val": tier_val,
                    "gap_pct": round(gap * 100, 1),
                })
        weaknesses.sort(key=lambda w: -w["gap_pct"])
        weakness_analysis[yid] = weaknesses[:5]  # 取 Top5 短板

    # --- 建议生成 ---
    ADVICE_MAP = {
        "1": "增加主动进攻意识，多利用垫步接近后抢先手。",
        "2": "普攻连段练习，注意攻击距离和时机把控。",
        "3": "投技需要贴身使用，利用垫步或防御后接投技。",
        "4": "技能释放时机要准确，避免空放浪费资源。",
        "5": "绝技要在确保命中的情况下释放，如连段尾段或对手硬直时。",
        "6": "注意对手倒地后的起身时机，提前准备压制招式。",
        "7": "练习稳定连段路线，减少掉链子。",
        "8": "尝试延长连段，加入更多连击组合。",
        "9": "学习角色的最长连段路线，在训练模式中反复练习。",
        "10": "优化连段路线选择高伤害招式。",
        "11": "研究角色最大伤害连段，在确认命中后执行。",
        "12": "提高防御意识，被压制时多用防御减少伤害。",
        "13": "防御时机要准确，不要过早松开防御键。",
        "14": "防御后主动寻找反击机会，而非一味龟缩。",
        "15": "防反后接连段，将防反优势转化为伤害。",
        "16": "防反命中后快速确认，衔接后续攻击。",
        "17": "关注脱出时机，在被连段时合理使用解招。",
        "18": "脱出后不要慌张，先判断对手动作再决定反打还是后退。",
        "19": "脱出后优先确保安全距离，不要急于反打。",
        "20": "练习闪避时机，在对手攻击判定帧前闪避。",
        "21": "减少倒地次数，被击飞后注意快速受身。",
        "22": "灵活运用取消变招打乱对手节奏，创造先手机会。",
        "23": "观察对手出招前摇，用快速招式打断。",
        "24": "势均力敌时注意节奏变化，准备后续应对。",
        "25": "体力消耗过大，减少不必要的垫步和取消操作。",
        "26": "利用拉开距离的时间让体力自然恢复。",
        "27": "不要长时间被动防御，适时释放防御让体力恢复。",
        "28": "被连段时尽快使用脱出，减少无谓受击时间。",
        "29": "炁满时要果断使用绝技，不要让资源空转。",
        "30": "身外身冷却后立即使用，减少空转浪费。",
        "31": "多使用垫步调整距离和创造攻击机会。",
        "32": "增加取消操作的使用，让攻击更具欺骗性。",
        "33": "普攻取消可以打出更灵活的进攻节奏。",
        "34": "技能取消可以在技能前摇被识破时快速转换。",
        "35": "防反取消让防御后的行动更多样化。",
        "36": "灵活使用各种取消，增加操作的不可预测性。",
    }

    # ============================================================
    # 构建 HTML
    # ============================================================

    # JSON 数据序列化
    radar_categories_js = json.dumps([RADAR_DIM_NAMES[d] for d in ["1", "2", "3", "4", "5"]])
    radar_player_js = json.dumps(radar_player)
    radar_avg_js = json.dumps(radar_avg)
    radar_trend_x_js = json.dumps(radar_trend_x)
    radar_trend_data_js = json.dumps({RADAR_DIM_NAMES[d]: radar_trend_data[d] for d in ["1", "2", "3", "4", "5"]})

    # 角色数据
    yiren_info_js = json.dumps([{
        "id": yid,
        "name": get_yiren_name(yid),
        "rounds": yiren_stats[yid]["rounds"],
        "wins": yiren_stats[yid]["wins"],
        "wr": round(yiren_stats[yid]["wins"] / yiren_stats[yid]["rounds"] * 100, 1) if yiren_stats[yid]["rounds"] > 0 else 0,
    } for yid in yiren_list], ensure_ascii=False)

    # 角色指标数据
    yiren_metrics_js = json.dumps({
        str(yid): yiren_metric_avgs[yid] for yid in yiren_list
    })

    global_bar_avg_js = json.dumps(global_bar_avg)
    tier_avg_js = json.dumps(tier_avg)
    bar_metrics_js = json.dumps({k: v["name"] for k, v in BAR_METRICS.items()}, ensure_ascii=False)
    bar_units_js = json.dumps({k: v["unit"] for k, v in BAR_METRICS.items()}, ensure_ascii=False)
    metric_groups_js = json.dumps(METRIC_GROUPS, ensure_ascii=False)

    # 段位趋势
    phase_trend_js = json.dumps(phase_trend)

    # 短板诊断
    weakness_js = json.dumps({
        str(yid): weakness_analysis[yid] for yid in yiren_list
    }, ensure_ascii=False)

    advice_map_js = json.dumps(ADVICE_MAP, ensure_ascii=False)

    # 每局角色使用
    match_yiren_js = json.dumps([{
        "file_index": m["file_index"],
        "win": m["match_win"],
        "yiren_ids": [r["yiren_id"] for r in round_records if r["file_index"] == m["file_index"]],
    } for m in match_records])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UC 对局复盘分析报告</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  :root {{
    --bg-primary: #0f1923;
    --bg-card: #1a2634;
    --bg-card-hover: #243447;
    --text-primary: #e8eaed;
    --text-secondary: #8b95a5;
    --accent-gold: #f0b429;
    --accent-blue: #4fc3f7;
    --accent-red: #ef5350;
    --accent-green: #66bb6a;
    --accent-purple: #ab47bc;
    --border-color: #2d3d50;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
  
  /* 头部 */
  .header {{
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, #1a2634 0%, #0f1923 100%);
    border-bottom: 2px solid var(--accent-gold);
    margin-bottom: 30px;
  }}
  .header h1 {{
    font-size: 2.2em;
    color: var(--accent-gold);
    margin-bottom: 10px;
  }}
  .header .subtitle {{ color: var(--text-secondary); font-size: 1.1em; }}
  
  /* 概览卡片 */
  .overview-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
  }}
  .stat-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }}
  .stat-card .stat-value {{
    font-size: 2.4em;
    font-weight: 700;
    margin: 8px 0;
  }}
  .stat-card .stat-label {{
    color: var(--text-secondary);
    font-size: 0.9em;
  }}
  .stat-card.win .stat-value {{ color: var(--accent-green); }}
  .stat-card.lose .stat-value {{ color: var(--accent-red); }}
  .stat-card.rate .stat-value {{ color: var(--accent-gold); }}
  .stat-card.info .stat-value {{ color: var(--accent-blue); }}
  
  /* 模块 */
  .module {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }}
  .module-title {{
    font-size: 1.5em;
    color: var(--accent-gold);
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }}
  .module-subtitle {{
    font-size: 1.1em;
    color: var(--accent-blue);
    margin: 16px 0 8px 0;
  }}
  
  /* 图表容器 */
  .chart-container {{
    width: 100%;
    margin: 16px 0;
  }}
  .chart-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }}
  @media (max-width: 768px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
  }}
  
  /* 角色选择器 */
  .yiren-selector {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 16px 0;
  }}
  .yiren-btn {{
    padding: 8px 16px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.9em;
  }}
  .yiren-btn:hover {{ background: var(--bg-card-hover); }}
  .yiren-btn.active {{
    background: var(--accent-gold);
    color: var(--bg-primary);
    border-color: var(--accent-gold);
    font-weight: 600;
  }}
  .yiren-btn .badge {{
    display: inline-block;
    background: rgba(255,255,255,0.2);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.8em;
    margin-left: 4px;
  }}
  .yiren-btn.active .badge {{
    background: rgba(0,0,0,0.2);
  }}
  
  /* 短板诊断 */
  .weakness-list {{ list-style: none; padding: 0; }}
  .weakness-item {{
    background: rgba(239, 83, 80, 0.1);
    border-left: 3px solid var(--accent-red);
    padding: 12px 16px;
    margin-bottom: 8px;
    border-radius: 0 8px 8px 0;
  }}
  .weakness-item .metric-name {{
    font-weight: 600;
    color: var(--accent-red);
  }}
  .weakness-item .gap-info {{
    color: var(--text-secondary);
    font-size: 0.9em;
    margin: 4px 0;
  }}
  .weakness-item .advice {{
    color: var(--accent-blue);
    font-size: 0.9em;
    margin-top: 4px;
    padding-left: 16px;
    border-left: 2px solid var(--accent-blue);
  }}
  
  /* 优势项 */
  .strength-item {{
    background: rgba(102, 187, 106, 0.1);
    border-left: 3px solid var(--accent-green);
    padding: 12px 16px;
    margin-bottom: 8px;
    border-radius: 0 8px 8px 0;
  }}
  .strength-item .metric-name {{
    font-weight: 600;
    color: var(--accent-green);
  }}
  
  /* 表格 */
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
  }}
  .data-table th, .data-table td {{
    padding: 10px 12px;
    text-align: center;
    border-bottom: 1px solid var(--border-color);
  }}
  .data-table th {{
    background: var(--bg-primary);
    color: var(--accent-gold);
    font-weight: 600;
  }}
  .data-table tr:hover {{ background: var(--bg-card-hover); }}

  .tab-container {{ margin: 16px 0; }}
  .tab-buttons {{ display: flex; gap: 4px; margin-bottom: 12px; }}
  .tab-btn {{
    padding: 8px 20px;
    border: 1px solid var(--border-color);
    border-radius: 8px 8px 0 0;
    background: var(--bg-primary);
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.9em;
  }}
  .tab-btn.active {{
    background: var(--bg-card);
    color: var(--accent-gold);
    border-bottom-color: var(--bg-card);
  }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
</style>
</head>
<body>

<div class="header">
  <h1>⚔️ UC 对局复盘分析报告</h1>
  <div class="subtitle">基于 {total_matches} 局对局数据 · {total_rounds} 个回合</div>
</div>

<div class="container">

  <!-- 概览 -->
  <div class="overview-grid">
    <div class="stat-card info">
      <div class="stat-label">总对局数</div>
      <div class="stat-value">{total_matches}</div>
      <div class="stat-label">{total_rounds} 个回合</div>
    </div>
    <div class="stat-card win">
      <div class="stat-label">胜利</div>
      <div class="stat-value">{total_wins}</div>
      <div class="stat-label">局</div>
    </div>
    <div class="stat-card lose">
      <div class="stat-label">失败</div>
      <div class="stat-value">{total_losses}</div>
      <div class="stat-label">局</div>
    </div>
    <div class="stat-card rate">
      <div class="stat-label">对局胜率</div>
      <div class="stat-value">{win_rate}%</div>
      <div class="stat-label">回合胜率 {round_wr}%</div>
    </div>
    <div class="stat-card info">
      <div class="stat-label">使用角色数</div>
      <div class="stat-value">{len(yiren_list)}</div>
      <div class="stat-label">个</div>
    </div>
  </div>

  <!-- ============================================================ -->
  <!-- 模块一：玩家整体表现 -->
  <!-- ============================================================ -->
  <div class="module">
    <h2 class="module-title">📊 模块一：玩家整体表现</h2>
    
    <div class="chart-row">
      <div class="chart-container" id="radar-chart"></div>
      <div class="chart-container" id="radar-trend-chart"></div>
    </div>
    
    <h3 class="module-subtitle">📈 各指标组详情（全局平均 vs 段位均值）</h3>
    <div class="tab-container">
      <div class="tab-buttons" id="group-tabs"></div>
      <div id="group-charts"></div>
    </div>
  </div>

  <!-- ============================================================ -->
  <!-- 模块二：分角色进步分析 -->
  <!-- ============================================================ -->
  <div class="module">
    <h2 class="module-title">🎭 模块二：分角色进步分析</h2>
    
    <h3 class="module-subtitle">📊 角色使用概览</h3>
    <div class="chart-row">
      <div class="chart-container" id="yiren-usage-chart"></div>
      <div class="chart-container" id="yiren-wr-chart"></div>
    </div>
    
    <h3 class="module-subtitle">📈 段位变化趋势</h3>
    <div class="chart-container" id="phase-trend-chart"></div>
    
    <h3 class="module-subtitle">🎮 选择角色查看详细分析</h3>
    <div class="yiren-selector" id="yiren-selector"></div>
    
    <div id="yiren-detail-section">
      <div class="chart-container" id="yiren-radar-compare-chart"></div>
      <div class="chart-container" id="yiren-metrics-chart"></div>
      
      <h3 class="module-subtitle">🔍 短板诊断与建议</h3>
      <div id="weakness-section"></div>
    </div>
  </div>

</div>

<script>
// ============================================================
// 数据注入
// ============================================================
const RADAR_CATS = {radar_categories_js};
const RADAR_PLAYER = {radar_player_js};
const RADAR_AVG = {radar_avg_js};
const RADAR_TREND_X = {radar_trend_x_js};
const RADAR_TREND_DATA = {radar_trend_data_js};
const YIREN_INFO = {yiren_info_js};
const YIREN_METRICS = {yiren_metrics_js};
const GLOBAL_BAR_AVG = {global_bar_avg_js};
const TIER_AVG = {tier_avg_js};
const BAR_METRICS = {bar_metrics_js};
const BAR_UNITS = {bar_units_js};
const METRIC_GROUPS = {metric_groups_js};
const PHASE_TREND = {phase_trend_js};
const WEAKNESS = {weakness_js};
const ADVICE_MAP = {advice_map_js};

const PLOTLY_LAYOUT_BASE = {{
  paper_bgcolor: '#1a2634',
  plot_bgcolor: '#1a2634',
  font: {{ color: '#e8eaed', family: '-apple-system, PingFang SC, sans-serif' }},
  margin: {{ t: 40, b: 40, l: 50, r: 20 }},
}};

const PLOTLY_CONFIG = {{ responsive: true, displayModeBar: false }};

// ============================================================
// 模块一：五维雷达图
// ============================================================
function drawRadarChart() {{
  const data = [
    {{
      type: 'scatterpolar',
      r: [...RADAR_PLAYER, RADAR_PLAYER[0]],
      theta: [...RADAR_CATS, RADAR_CATS[0]],
      fill: 'toself',
      fillcolor: 'rgba(240,180,41,0.2)',
      line: {{ color: '#f0b429', width: 2 }},
      name: '我的表现',
    }},
    {{
      type: 'scatterpolar',
      r: [...RADAR_AVG, RADAR_AVG[0]],
      theta: [...RADAR_CATS, RADAR_CATS[0]],
      fill: 'toself',
      fillcolor: 'rgba(79,195,247,0.1)',
      line: {{ color: '#4fc3f7', width: 2, dash: 'dash' }},
      name: '段位均值',
    }},
  ];
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: '五维能力雷达图', font: {{ size: 16 }} }},
    polar: {{
      bgcolor: '#1a2634',
      radialaxis: {{
        visible: true,
        range: [0, 100],
        gridcolor: '#2d3d50',
        linecolor: '#2d3d50',
        tickfont: {{ color: '#8b95a5', size: 10 }},
      }},
      angularaxis: {{
        gridcolor: '#2d3d50',
        linecolor: '#2d3d50',
        tickfont: {{ color: '#e8eaed', size: 12 }},
      }},
    }},
    legend: {{ x: 0.02, y: -0.1, orientation: 'h' }},
    showlegend: true,
  }};
  Plotly.newPlot('radar-chart', data, layout, PLOTLY_CONFIG);
}}

// 五维趋势图
function drawRadarTrend() {{
  const colors = ['#f0b429', '#4fc3f7', '#66bb6a', '#ab47bc', '#ef5350'];
  const dims = Object.keys(RADAR_TREND_DATA);
  const data = dims.map((d, i) => ({{
    type: 'scatter',
    mode: 'lines+markers',
    x: RADAR_TREND_X,
    y: RADAR_TREND_DATA[d],
    name: d,
    line: {{ color: colors[i], width: 2 }},
    marker: {{ size: 4 }},
  }}));
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: '五维能力趋势变化', font: {{ size: 16 }} }},
    xaxis: {{ title: '对局序号', gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    yaxis: {{ title: '分值', gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    legend: {{ x: 0.02, y: -0.2, orientation: 'h' }},
  }};
  Plotly.newPlot('radar-trend-chart', data, layout, PLOTLY_CONFIG);
}}

// 指标组详情
function drawGroupCharts() {{
  const tabButtons = document.getElementById('group-tabs');
  const chartContainer = document.getElementById('group-charts');
  const groups = Object.keys(METRIC_GROUPS);
  
  groups.forEach((g, i) => {{
    const btn = document.createElement('div');
    btn.className = 'tab-btn' + (i === 0 ? ' active' : '');
    btn.textContent = g;
    btn.onclick = () => {{
      document.querySelectorAll('#group-tabs .tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderGroupChart(g);
    }};
    tabButtons.appendChild(btn);
  }});
  
  renderGroupChart(groups[0]);
}}

function renderGroupChart(group) {{
  const metrics = METRIC_GROUPS[group];
  const names = metrics.map(m => BAR_METRICS[m]);
  const playerVals = metrics.map(m => GLOBAL_BAR_AVG[m] || 0);
  const tierVals = metrics.map(m => TIER_AVG[m] || 0);
  
  const data = [
    {{
      type: 'bar',
      x: names,
      y: playerVals,
      name: '我的均值',
      marker: {{ color: '#f0b429' }},
    }},
    {{
      type: 'bar',
      x: names,
      y: tierVals,
      name: '段位均值',
      marker: {{ color: 'rgba(79,195,247,0.6)' }},
    }},
  ];
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: group + ' 指标详情', font: {{ size: 14 }} }},
    barmode: 'group',
    xaxis: {{ gridcolor: '#2d3d50', linecolor: '#2d3d50', tickangle: -30 }},
    yaxis: {{ gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    legend: {{ x: 0.02, y: -0.3, orientation: 'h' }},
    height: 400,
  }};
  
  Plotly.newPlot('group-charts', data, layout, PLOTLY_CONFIG);
}}

// ============================================================
// 模块二：分角色分析
// ============================================================
function drawYirenUsage() {{
  const data = [{{
    type: 'bar',
    x: YIREN_INFO.map(y => y.name),
    y: YIREN_INFO.map(y => y.rounds),
    marker: {{
      color: YIREN_INFO.map((_, i) => {{
        const colors = ['#f0b429', '#4fc3f7', '#66bb6a', '#ab47bc', '#ef5350', '#ff9800', '#e91e63', '#00bcd4'];
        return colors[i % colors.length];
      }}),
    }},
    text: YIREN_INFO.map(y => y.rounds + '回合'),
    textposition: 'auto',
  }}];
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: '角色使用频率（回合数）', font: {{ size: 14 }} }},
    xaxis: {{ gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    yaxis: {{ title: '回合数', gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    showlegend: false,
    height: 350,
  }};
  Plotly.newPlot('yiren-usage-chart', data, layout, PLOTLY_CONFIG);
}}

function drawYirenWR() {{
  const data = [{{
    type: 'bar',
    x: YIREN_INFO.map(y => y.name),
    y: YIREN_INFO.map(y => y.wr),
    marker: {{
      color: YIREN_INFO.map(y => y.wr >= 50 ? '#66bb6a' : '#ef5350'),
    }},
    text: YIREN_INFO.map(y => y.wr + '%'),
    textposition: 'auto',
  }}];
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: '角色胜率', font: {{ size: 14 }} }},
    xaxis: {{ gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    yaxis: {{ title: '胜率 %', gridcolor: '#2d3d50', linecolor: '#2d3d50', range: [0, 100] }},
    showlegend: false,
    height: 350,
    shapes: [{{
      type: 'line', x0: -0.5, x1: YIREN_INFO.length - 0.5,
      y0: 50, y1: 50, line: {{ color: '#8b95a5', dash: 'dash', width: 1 }},
    }}],
  }};
  Plotly.newPlot('yiren-wr-chart', data, layout, PLOTLY_CONFIG);
}}

function drawPhaseTrend() {{
  const x = PHASE_TREND.map(p => p.x);
  const y = PHASE_TREND.map(p => {{
    const ap = p.arena_phase || 0;
    const sp = p.sub_phase || 0;
    return ap + sp / 10;
  }});
  const data = [{{
    type: 'scatter',
    mode: 'lines+markers',
    x: x, y: y,
    line: {{ color: '#f0b429', width: 2 }},
    marker: {{ size: 6, color: '#f0b429' }},
    name: '段位',
  }}];
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: '段位变化趋势（arena_phase.sub_phase）', font: {{ size: 14 }} }},
    xaxis: {{ title: '对局序号', gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    yaxis: {{ title: '段位值', gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    height: 350,
  }};
  Plotly.newPlot('phase-trend-chart', data, layout, PLOTLY_CONFIG);
}}

// 角色选择器
let currentYiren = null;
function initYirenSelector() {{
  const container = document.getElementById('yiren-selector');
  YIREN_INFO.forEach((y, i) => {{
    const btn = document.createElement('div');
    btn.className = 'yiren-btn' + (i === 0 ? ' active' : '');
    btn.innerHTML = y.name + '<span class="badge">' + y.rounds + '回合 | ' + y.wr + '%胜率</span>';
    btn.onclick = () => {{
      document.querySelectorAll('.yiren-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectYiren(y.id);
    }};
    container.appendChild(btn);
  }});
  if (YIREN_INFO.length > 0) selectYiren(YIREN_INFO[0].id);
}}

function selectYiren(yid) {{
  currentYiren = yid;
  drawYirenMetrics(yid);
  drawWeakness(yid);
}}

function drawYirenMetrics(yid) {{
  const yMetrics = YIREN_METRICS[String(yid)];
  if (!yMetrics) return;
  
  const yName = YIREN_INFO.find(y => y.id === yid)?.name || '未知';
  
  // 选择关键指标子集
  const keyMetrics = ['1','2','4','7','12','13','17','18','19','22','23','25','26','31','32'];
  const names = keyMetrics.map(m => BAR_METRICS[m]);
  const playerVals = keyMetrics.map(m => yMetrics[m] || 0);
  const tierVals = keyMetrics.map(m => TIER_AVG[m] || 0);
  const globalVals = keyMetrics.map(m => GLOBAL_BAR_AVG[m] || 0);
  
  const data = [
    {{
      type: 'bar',
      x: names,
      y: playerVals,
      name: yName + ' 均值',
      marker: {{ color: '#f0b429' }},
    }},
    {{
      type: 'bar',
      x: names,
      y: globalVals,
      name: '全局均值',
      marker: {{ color: 'rgba(171,71,188,0.6)' }},
    }},
    {{
      type: 'bar',
      x: names,
      y: tierVals,
      name: '段位均值',
      marker: {{ color: 'rgba(79,195,247,0.5)' }},
    }},
  ];
  
  const layout = {{
    ...PLOTLY_LAYOUT_BASE,
    title: {{ text: yName + ' 关键指标对比', font: {{ size: 14 }} }},
    barmode: 'group',
    xaxis: {{ gridcolor: '#2d3d50', linecolor: '#2d3d50', tickangle: -30 }},
    yaxis: {{ gridcolor: '#2d3d50', linecolor: '#2d3d50' }},
    legend: {{ x: 0, y: -0.3, orientation: 'h' }},
    height: 450,
  }};
  Plotly.newPlot('yiren-metrics-chart', data, layout, PLOTLY_CONFIG);
}}

function drawWeakness(yid) {{
  const section = document.getElementById('weakness-section');
  const weaknesses = WEAKNESS[String(yid)] || [];
  const yName = YIREN_INFO.find(y => y.id === yid)?.name || '未知';
  
  if (weaknesses.length === 0) {{
    section.innerHTML = '<div class="strength-item"><span class="metric-name">✨ ' + yName + ' 没有明显短板！</span> 各项指标均达到或超过段位平均水平。</div>';
    return;
  }}
  
  let html = '<h4 style="color:#ef5350; margin-bottom:12px;">⚠️ ' + yName + ' 的 Top ' + weaknesses.length + ' 短板</h4>';
  html += '<ul class="weakness-list">';
  weaknesses.forEach(w => {{
    const advice = ADVICE_MAP[w.metric_id] || '继续练习提升。';
    html += `
      <li class="weakness-item">
        <div class="metric-name">${{w.metric_name}}</div>
        <div class="gap-info">你的均值: <b>${{w.player_val}}</b> ${{BAR_UNITS[w.metric_id] || ''}} ｜ 段位均值: <b>${{w.tier_val}}</b> ${{BAR_UNITS[w.metric_id] || ''}} ｜ 差距: <span style="color:#ef5350">-${{w.gap_pct}}%</span></div>
        <div class="advice">💡 ${{advice}}</div>
      </li>`;
  }});
  html += '</ul>';
  
  // 找优势项
  const yMetrics = YIREN_METRICS[String(yid)];
  if (yMetrics) {{
    const strengths = [];
    Object.keys(BAR_METRICS).forEach(mk => {{
      const pv = yMetrics[mk];
      const tv = TIER_AVG[mk];
      if (pv == null || tv == null || tv === 0) return;
      let gap;
      if (['21','25','27','28','30'].includes(mk)) {{
        gap = (tv - pv) / Math.abs(tv);
      }} else {{
        gap = (pv - tv) / Math.abs(tv);
      }}
      if (gap > 0.3) strengths.push({{ name: BAR_METRICS[mk], val: pv, tier: tv, gap: Math.round(gap * 100) }});
    }});
    strengths.sort((a, b) => b.gap - a.gap);
    
    if (strengths.length > 0) {{
      html += '<h4 style="color:#66bb6a; margin:20px 0 12px 0;">✅ ' + yName + ' 的优势项</h4>';
      strengths.slice(0, 5).forEach(s => {{
        html += `<div class="strength-item"><span class="metric-name">${{s.name}}</span> — 你: <b>${{s.val}}</b> vs 段位: <b>${{s.tier}}</b> (+${{s.gap}}%)</div>`;
      }});
    }}
  }}
  
  section.innerHTML = html;
}}

// ============================================================
// 初始化
// ============================================================
drawRadarChart();
drawRadarTrend();
drawGroupCharts();
drawYirenUsage();
drawYirenWR();
drawPhaseTrend();
initYirenSelector();
</script>

</body>
</html>"""
    return html


# ============================================================
# 主流程
# ============================================================
if __name__ == "__main__":
    FOLDER = os.path.join(os.path.dirname(__file__), "jsontest")
    print("📂 读取数据中...")
    games = load_all_games(FOLDER)
    print(f"   读取了 {len(games)} 局对局数据")

    print("📊 解析玩家数据...")
    match_records, round_records = extract_player_data(games)
    print(f"   {len(match_records)} 局对局, {len(round_records)} 个回合")

    print("🎨 生成 HTML 报告...")
    html = generate_html_report(match_records, round_records)

    output_path = os.path.join(os.path.dirname(__file__), "analysis_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 报告已生成: {output_path}")
