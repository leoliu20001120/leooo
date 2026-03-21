"""根据 current_gid 匹配我方 team_id，计算比分（我方:对方）"""
import json, glob, os

base_dir = os.path.dirname(os.path.abspath(__file__))
files = sorted(
    glob.glob(os.path.join(base_dir, "*.json")),
    key=lambda x: int(os.path.basename(x).replace('.json', ''))
)

for f in files:
    with open(f) as fh:
        data = json.load(fh)
    fname = os.path.basename(f)
    cur_gid = data.get('current_gid')
    players = data.get('players', {})

    # 建立 gid -> team_id 映射
    gid_team = {}
    all_rounds = None
    for pid, p in players.items():
        if pid == '0':
            continue
        gid = p.get('gid', int(pid))
        rounds = p.get('rounds', [])
        tid = rounds[0].get('team_id') if rounds else None
        gid_team[gid] = tid
        if all_rounds is None and rounds:
            all_rounds = rounds

    my_team = gid_team.get(cur_gid, '?')

    if all_rounds:
        my_w = sum(1 for r in all_rounds if r.get('win_team_id') == my_team)
        opp_w = len(all_rounds) - my_w
    else:
        my_w, opp_w = 0, 0

    res = '我方胜' if my_w > opp_w else '对方胜'
    print(f"{fname:<10} current_gid={str(cur_gid):<12} 我方=Team{my_team}  比分 {my_w}:{opp_w}  {res}")
