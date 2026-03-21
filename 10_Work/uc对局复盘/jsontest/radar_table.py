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

    diffs = {}
    for d in range(1, 6):
        diffs[d] = my_dims.get(d, 0) - opp_dims.get(d, 0)

    max_dim = max(diffs, key=lambda x: diffs[x])
    min_dim = min(diffs, key=lambda x: diffs[x])

    results.append((f, my_dims, opp_dims, diffs, max_dim, min_dim))

# 紧凑表格输出
print(f"{'文件':<10} | {'D1我':>6} {'D1对':>6} {'D1差':>7} | {'D2我':>6} {'D2对':>6} {'D2差':>7} | {'D3我':>6} {'D3对':>6} {'D3差':>7} | {'D4我':>6} {'D4对':>6} {'D4差':>7} | {'D5我':>6} {'D5对':>6} {'D5差':>7} | {'最大差':>6} {'最小差':>6}")
print("-" * 170)
for f, my, opp, diffs, max_d, min_d in results:
    parts = []
    for d in range(1, 6):
        parts.append(f"{my[d]:>6} {opp[d]:>6} {diffs[d]:>+7}")
    line = f"{f:<10} | " + " | ".join(parts) + f" | D{max_d}({diffs[max_d]:+d})  D{min_d}({diffs[min_d]:+d})"
    print(line)
