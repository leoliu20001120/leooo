"""去重后按独立对局输出比分"""
import json, os, glob
from collections import OrderedDict

def calc_score(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    game_trace_id = data.get('game_trace_id', 'unknown')
    players = data.get('players', {})
    all_rounds = []
    for pid, pdata in players.items():
        if pid == '0':
            continue
        rounds = pdata.get('rounds', [])
        if not all_rounds and rounds:
            all_rounds = rounds
    team_wins = {}
    for r in all_rounds:
        win_id = r.get('win_team_id')
        if win_id is not None:
            team_wins[win_id] = team_wins.get(win_id, 0) + 1
    return game_trace_id, team_wins.get(1, 0), team_wins.get(2, 0), len(all_rounds)

base_dir = os.path.dirname(os.path.abspath(__file__))
json_files = sorted(
    glob.glob(os.path.join(base_dir, "*.json")),
    key=lambda x: int(os.path.basename(x).replace('.json', ''))
)

# 按 game_trace_id 去重
seen = OrderedDict()
for f in json_files:
    gid, t1, t2, total = calc_score(f)
    fname = os.path.basename(f)
    if gid not in seen:
        seen[gid] = (t1, t2, total, [fname])
    else:
        seen[gid][3].append(fname)

print(f"{'#':<4} {'game_trace_id':<25} {'比分':<10} {'结果':<10} {'回合':<6} {'文件'}")
print("-" * 90)
for i, (gid, (t1, t2, total, files)) in enumerate(seen.items(), 1):
    winner = "Team1胜" if t1 > t2 else ("Team2胜" if t2 > t1 else "平局")
    files_str = ", ".join(files)
    print(f"{i:<4} {gid:<25} {t1}:{t2:<8} {winner:<10} {total:<6} {files_str}")

print(f"\n{'='*90}")
print(f"📊 独立对局总数: {len(seen)}")
t1_wins = sum(1 for (t1, t2, _, _) in seen.values() if t1 > t2)
t2_wins = sum(1 for (t1, t2, _, _) in seen.values() if t2 > t1)
draws = sum(1 for (t1, t2, _, _) in seen.values() if t1 == t2)
print(f"   Team1 赢: {t1_wins} 场")
print(f"   Team2 赢: {t2_wins} 场")
if draws:
    print(f"   平局: {draws} 场")
