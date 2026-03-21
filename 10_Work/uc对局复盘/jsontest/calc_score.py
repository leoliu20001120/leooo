"""
计算 UC 对局复盘 JSON 文件中的比分
通过每个 round 的 win_team_id 统计 team1 vs team2 的胜局数
"""
import json
import os
import glob

def calc_score(filepath):
    """解析单个 JSON 文件，返回比分信息"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    game_trace_id = data.get("game_trace_id", "unknown")
    players = data.get("players", {})
    
    # 收集所有 rounds 中的 win_team_id
    # 取第一个非 "0" 的玩家的 rounds 作为基准（避免重复计算）
    all_rounds = []
    player_info = {}
    
    for pid, pdata in players.items():
        if pid == "0":
            continue
        team_id = None
        rounds = pdata.get("rounds", [])
        if rounds:
            team_id = rounds[0].get("team_id")
        player_info[pid] = {
            "gid": pdata.get("gid", pid),
            "team_id": team_id,
            "round_count": len(rounds)
        }
        
        # 只取第一个玩家的 rounds 来统计 win_team_id
        if not all_rounds and rounds:
            all_rounds = rounds
    
    # 如果第一个玩家没有 rounds，尝试所有玩家
    if not all_rounds:
        for pid, pdata in players.items():
            if pid == "0":
                continue
            rounds = pdata.get("rounds", [])
            if rounds:
                all_rounds = rounds
                break
    
    # 统计各队赢的回合数
    team_wins = {}
    for r in all_rounds:
        win_id = r.get("win_team_id")
        if win_id is not None:
            team_wins[win_id] = team_wins.get(win_id, 0) + 1
    
    # 确定 team1 和 team2
    team1_wins = team_wins.get(1, 0)
    team2_wins = team_wins.get(2, 0)
    
    return {
        "file": os.path.basename(filepath),
        "game_trace_id": game_trace_id,
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "score": f"{team1_wins} : {team2_wins}",
        "total_rounds": len(all_rounds),
        "players": player_info
    }


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_files = sorted(
        glob.glob(os.path.join(base_dir, "*.json")),
        key=lambda x: int(os.path.basename(x).replace('.json', ''))
    )
    
    print(f"{'文件':<10} {'比分 (Team1 : Team2)':<25} {'总回合数':<10} {'game_trace_id'}")
    print("-" * 80)
    
    results = []
    for f in json_files:
        try:
            result = calc_score(f)
            results.append(result)
            print(f"{result['file']:<10} {result['score']:<25} {result['total_rounds']:<10} {result['game_trace_id']}")
        except Exception as e:
            print(f"{os.path.basename(f):<10} ❌ 解析错误: {e}")
    
    # 统计汇总
    print("\n" + "=" * 80)
    print("📊 汇总统计")
    print(f"总对局数: {len(results)}")
    
    team1_total = sum(r['team1_wins'] for r in results)
    team2_total = sum(r['team2_wins'] for r in results)
    
    # 按比分分类
    team1_game_wins = sum(1 for r in results if r['team1_wins'] > r['team2_wins'])
    team2_game_wins = sum(1 for r in results if r['team2_wins'] > r['team1_wins'])
    draws = sum(1 for r in results if r['team1_wins'] == r['team2_wins'])
    
    print(f"Team1 赢的对局: {team1_game_wins}")
    print(f"Team2 赢的对局: {team2_game_wins}")
    if draws:
        print(f"平局: {draws}")
    print(f"Team1 总赢回合: {team1_total}")
    print(f"Team2 总赢回合: {team2_total}")


if __name__ == "__main__":
    main()
