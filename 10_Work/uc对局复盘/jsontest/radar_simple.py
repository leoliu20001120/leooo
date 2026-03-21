import json, glob

for f in sorted(glob.glob('*.json'), key=lambda x: int(x.replace('.json',''))):
    with open(f) as fh:
        data = json.load(fh)
    cur_gid = data.get('current_gid')
    players = data.get('players', {})

    my_dims = {}
    opp_dims = {}
    for pid, p in players.items():
        if pid == '0':
            continue
        rc = p.get('radar_chart', {}).get('dimension', {})
        dims = {}
        for d in ['1','2','3','4','5']:
            dims[int(d)] = rc.get(d, {}).get('value', 0)
        gid = p.get('gid', int(pid))
        if gid == cur_gid:
            my_dims = dims
        else:
            opp_dims = dims

    diffs = {d: my_dims.get(d,0) - opp_dims.get(d,0) for d in range(1,6)}
    max_d = max(diffs, key=lambda x: diffs[x])
    min_d = min(diffs, key=lambda x: diffs[x])

    my_max = round(my_dims[max_d] / 10000, 1)
    opp_max = round(opp_dims[max_d] / 10000, 1)
    my_min = round(my_dims[min_d] / 10000, 1)
    opp_min = round(opp_dims[min_d] / 10000, 1)
    print(f"{f:<10} 最大差:D{max_d}(我{my_max} 对{opp_max} 差{diffs[max_d]:+d})  最小差:D{min_d}(我{my_min} 对{opp_min} 差{diffs[min_d]:+d})")
