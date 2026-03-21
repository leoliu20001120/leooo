import json, glob

results = []
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

    # 计算差值 (我方 - 对方)
    diffs = {}
    for d in range(1, 6):
        diffs[d] = my_dims.get(d, 0) - opp_dims.get(d, 0)

    max_dim = max(diffs, key=lambda x: diffs[x])
    min_dim = min(diffs, key=lambda x: diffs[x])

    results.append((f, my_dims, opp_dims, diffs, max_dim, min_dim))

# 输出每个文件
for f, my, opp, diffs, max_d, min_d in results:
    print(f'\n=== {f} ===')
    print(f'  {"维度":<6} {"我方":>8} {"对方":>8} {"差值(我-对)":>12}')
    for d in range(1, 6):
        mark = ''
        if d == max_d:
            mark = ' ◀ 最大'
        if d == min_d:
            mark = ' ◀ 最小'
        print(f'  D{d:<5} {my[d]:>8} {opp[d]:>8} {diffs[d]:>+12}{mark}')
    print(f'  → 最大差值: D{max_d} ({diffs[max_d]:+d})')
    print(f'  → 最小差值: D{min_d} ({diffs[min_d]:+d})')
