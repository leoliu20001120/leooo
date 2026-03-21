import json, glob

# 维度名称映射
DIM_NAME = {
    '1': '先手能力',
    '2': '输出能力',
    '3': '防守能力',
    '4': '博弈能力',
    '5': '资源管理能力',
}

# 子维度名称映射
SUB_NAME = {
    '1': '有效先手次数',
    '2': '普通命中率',
    '3': '投技命中率',
    '4': '技能命中率',
    '5': '绝技命中率',
    '6': '成功压起身次数',
    '11': '平均连段时长',
    '12': '最大连段时长',
    '13': '平均连段伤害',
    '14': '最大连段伤害',
    '15': '连段成功率',
    '21': '防御成功次数',
    '22': '防反成功次数',
    '23': '脱身后安全率',
    '24': '闪避成功次数',
    '31': '变招先手次数',
    '32': '打断招数先手次数',
    '33': '势均力敌次数',
    '41': '体力不恢复时间',
    '42': '无法脱出的总受击时间',
    '43': '能量溢出',
    '44': '身外身冷却空转时间',
}

for f in sorted(glob.glob('*.json'), key=lambda x: int(x.replace('.json',''))):
    with open(f) as fh:
        data = json.load(fh)
    cur_gid = data.get('current_gid')
    players = data.get('players', {})

    my_data = {}
    opp_data = {}
    for pid, p in players.items():
        if pid == '0':
            continue
        rc = p.get('radar_chart', {}).get('dimension', {})
        gid = p.get('gid', int(pid))
        if gid == cur_gid:
            my_data = rc
        else:
            opp_data = rc

    # 1. 计算5个维度的 value 差值，找最大差(优势)和最小差(劣势)
    diffs = {}
    for d in ['1','2','3','4','5']:
        my_val = my_data.get(d, {}).get('value', 0)
        opp_val = opp_data.get(d, {}).get('value', 0)
        diffs[d] = my_val - opp_val

    max_dim = max(diffs, key=lambda x: diffs[x])  # 优势维度
    min_dim = min(diffs, key=lambda x: diffs[x])  # 劣势维度

    # 2. 在优势维度的 detail 中，找 weighted_value 差值最大的子指标（高光点）
    my_max_detail = my_data.get(max_dim, {}).get('detail', {})
    opp_max_detail = opp_data.get(max_dim, {}).get('detail', {})
    highlight_id = None
    highlight_diff = None
    for sub_id in my_max_detail:
        my_wv = my_max_detail[sub_id].get('weighted_value', 0)
        opp_wv = opp_max_detail.get(sub_id, {}).get('weighted_value', 0)
        d = my_wv - opp_wv
        if highlight_diff is None or d > highlight_diff:
            highlight_diff = d
            highlight_id = sub_id

    # 3. 在劣势维度的 detail 中，找 weighted_value 差值最小的子指标（提升点）
    my_min_detail = my_data.get(min_dim, {}).get('detail', {})
    opp_min_detail = opp_data.get(min_dim, {}).get('detail', {})
    improve_id = None
    improve_diff = None
    for sub_id in my_min_detail:
        my_wv = my_min_detail[sub_id].get('weighted_value', 0)
        opp_wv = opp_min_detail.get(sub_id, {}).get('weighted_value', 0)
        d = my_wv - opp_wv
        if improve_diff is None or d < improve_diff:
            improve_diff = d
            improve_id = sub_id

    # 获取子指标的 original_value（没有该字段就是 0）
    def get_orig(detail_dict, sub_id):
        entry = detail_dict.get(sub_id, {})
        return entry.get('original_value', 0)

    hl_my_orig = get_orig(my_max_detail, highlight_id)
    hl_opp_orig = get_orig(opp_max_detail, highlight_id)
    imp_my_orig = get_orig(my_min_detail, improve_id)
    imp_opp_orig = get_orig(opp_min_detail, improve_id)

    # 输出
    my_adv = round(my_data.get(max_dim, {}).get('value', 0) / 10000, 1)
    opp_adv = round(opp_data.get(max_dim, {}).get('value', 0) / 10000, 1)
    my_dis = round(my_data.get(min_dim, {}).get('value', 0) / 10000, 1)
    opp_dis = round(opp_data.get(min_dim, {}).get('value', 0) / 10000, 1)

    print(f"{f:<10} "
          f"优势:{DIM_NAME.get(max_dim)}(我{my_adv} 对{opp_adv}) 高光点:{SUB_NAME.get(highlight_id, highlight_id)}(我{hl_my_orig} 对{hl_opp_orig})  "
          f"劣势:{DIM_NAME.get(min_dim)}(我{my_dis} 对{opp_dis}) 提升点:{SUB_NAME.get(improve_id, improve_id)}(我{imp_my_orig} 对{imp_opp_orig})")
