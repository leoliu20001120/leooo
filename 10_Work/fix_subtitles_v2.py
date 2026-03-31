#!/usr/bin/env python3
"""
修正Whisper转录文本中的错误识别 - 第二轮全面修正
包含：英雄名、符文名、游戏术语、装备名、以及清理BGM噪音
"""

import os
import re
import pandas as pd

# ========== 路径配置 ==========
BASE = "/Users/liusixing_tx/Documents/Obsidian Vault/10_Work"
TEXT_DIR = f"{BASE}/海克斯大乱斗_字幕/text"
SUMMARY_FILE = f"{BASE}/海克斯大乱斗_字幕汇总.md"

# ========== 替换词典（按长度降序替换） ==========
replacements = {}

# --- 英雄名/称号错误 ---
hero_fixes = {
    # 常见误识别
    "杀弥拉": "莎弥拉", "杀美拉": "莎弥拉",
    "齐亚拉": "奇亚娜", "齐亚了": "奇亚娜", "齐亚那": "奇亚娜",
    "卡莉斯塔": "卡莉丝塔",
    "角月": "皎月", "脚月": "皎月",  # 黛安娜
    "我光": "维克兹", "续空之眼": "虚空之眼", "续空治眼": "虚空之眼",
    "心得了": "辛德拉",
    "天然": "天使", # 凯尔别称/可能也是误识别
    "小题目": "提莫", "題目": "提莫", "题目": "提莫",
    "师子狗": "狮子狗", "獅子狗": "狮子狗",  # 雷恩加尔
    "剑机": "剑姬",  # 菲奥娜
    "布龙": "布隆",
    "为人": "薇恩", "為人": "薇恩",
    "卡沙": "卡莎",
    "下可": "夏洛", "下克": "夏洛",
    "龙里": "希瓦娜",
    "派科": "派克",
    "次刻": "刺客",
    "签绝": "虔诚",
    "笨蛋": "笨蛋",  # 保留，主播用语
    "小火龙": "小火龙",
    "太均": "太均",
    "凯南虎": "凯南",
    "杨道": "杨刀",  # 可能是装备破败/杨刀
    "秋秋为人": "秋秋薇恩",
    "秋秋薇恩": "秋秋薇恩",
}

# --- 符文/海克斯名错误 ---
rune_fixes = {
    # 第一轮遗漏的
    "喊刻引起": "坦克引擎", "喊刻引擎": "坦克引擎", "很刻引擎": "坦克引擎",
    "喊克引擎": "坦克引擎",
    "淘宝计划": "逃跑计划",
    "会新质疗": "会心治疗", "会新治疗": "会心治疗",
    "监顿发明家": "尖端发明家", "建顿发明家": "尖端发明家",
    "牢链居神": "老练狙神",
    "秘书冲拳": "秘术冲拳",
    "火上焦油": "火上浇油", "火上交流": "火上浇油", "火上交油": "火上浇油",
    "面包和乃浪": "面包和奶酪", "面包和乃烙": "面包和奶酪",
    "利任华耳资": "利刃华尔兹", "利认华尔兹": "利刃华尔兹",
    "练狱膏管": "炼狱导管", "面育导管": "炼狱导管", "练育导管": "炼狱导管",
    "面育導管": "炼狱导管",
    "暗影极奔": "暗影疾奔", "暗影击奔": "暗影疾奔", "暗影擊奔": "暗影疾奔",
    "安隱疾奔": "暗影疾奔",
    "全评身法": "全凭身法", "全体身法": "全凭身法", "全評身法": "全凭身法",
    "坚弱盘时": "坚若磐石", "坚顿发明": "尖端发明",
    "黄兔豪器": "狂徒豪气", "狂吐好气": "狂徒豪气", "黃兔豪器": "狂徒豪气",
    "綴額快感": "罪恶快感",
    "终极换性": "终极唤醒", "終極換性": "终极唤醒",
    "循环老副": "循环往复", "循环老复": "循环往复",
    "无尽知任": "无尽之刃", "无尽之任": "无尽之刃", "無盡之認": "无尽之刃",
    "报上加猫": "帽上加帽",
    "坏中求稳": "快中求稳",
    "违快不破": "唯快不破",
    "苗准进": "瞄准镜", "苗翠平": "瞄准镜", "苗准進": "瞄准镜",
    "描准进": "瞄准镜", "描准進": "瞄准镜", "描转进": "瞄准镜",
    "搖轉鏡": "瞄准镜", "苗转镜": "瞄准镜",
    "龙菜海克斯": "棱彩海克斯", "龙菜阶": "棱彩", "龙采阶": "棱彩",
    "龙菜": "棱彩", "颜色海克斯": "棱彩海克斯",
    "颜色海克思": "棱彩海克斯",
    "还克思": "海克斯",
    "冷彩": "棱彩",
    "中辣升级": "中亚升级",
    "黄金之变": "黄金质变", "黄金街只变": "黄金质变",
    "黄金街": "黄金",
    "金色街": "金色",
    "直遍直接换化出": "质变直接转化出",
    "换化出": "转化出",
    "经产产": "金铲铲",
    "加元卫视": "家园卫士",
    "加原卫视": "家园卫士",
    "神盛干预": "神圣干预",
    "神圣干于": "神圣干预",
    "无法接修": "物法皆修",
    "帽子断体": "帽子叠体",
    "断体修先": "叠体修仙",
    "无中恨意": "虚空恨意",
    "一满意诚": "一板一眼",
    "一动精神": "移动金身",
    "移动精神": "移动金身", "移动的精神": "移动的金身",
    "会移动的精神": "会移动的金身",
    "变开精神变移动": "变成金身变移动",
    "超模": "超模",
    "超魔": "超模",
}

# --- 装备名错误 ---
equip_fixes = {
    "蛇牙": "蛇牙",  # 可能正确
    "叶认": "夜刃",
    "三项": "三项之力",
    "攤域九头蛇": "贪欲九头蛇", "攤域": "贪欲",
    "四五": "死舞",
    "四王之五": "死亡之舞",
    "心实": "迅刃",
    "收集者": "收集者",
    "黄王": "黄损", "黃王": "黄损",
    "冰涨": "冰杖", "冰状": "冰杖", "冰双之心": "冰霜之心",
    "大面具": "大面具",
    "新脂肪": "新制钢", "新制钢": "新制钢",
    "雪球": "雪球",
    "火炮": "火炮",
    "火具": "火炬",
    "冷却学": "冷却鞋",
    "铁板穴": "铁板鞋", "铁板学": "铁板鞋",
    "攻速鞋": "攻速鞋",
    "水银鞋": "水银鞋",
    "破败": "破败",
    "轻与火炮": "轻语火炮",
    "类假黄图": "泪假黄图",
    "清晰书宝": "清晰书宝",
    "无妖之后": "无尽之刃",
    "无尽之力": "无尽之刃",
    "风暴狂有": "风暴巨剑",
    "蝎": "鞋",
    "内甲": "内甲",
    "狂妄": "狂妄",
    "狂途": "狂徒",
    "兴计时机": "兴计时机",
    "新制钢狂突开甲": "新世纪狂徒开甲",
    "蓝的": "蓝盾",
    "续航蓝盾": "续航蓝盾",
    "退生": "推生",
    "火剧": "火炬",
    "锋利元湖": "锋利圆弧",
    "九头蛇": "九头蛇",
}

# --- 游戏术语/主播用语错误 ---
term_fixes = {
    # 主播称呼
    "主导": "主播",
    "主爆": "主播", "主抱": "主播",

    # 游戏操作
    "无成胜率": "五成胜率", "又成胜率": "五成胜率", "我成胜率": "五成胜率",
    "无成勝率": "五成胜率", "無成勝率": "五成胜率",
    "三层胜率": "三成胜率",
    "六成圣律": "六成胜率",
    "两成胜利率": "两成胜率",
    "五成胜利率": "五成胜率",
    "九成话": "九成吧",
    "饥杀": "击杀", "参与饥杀": "参与击杀",
    "位积能": "位移技能",
    "评约接普攻": "平A接普攻", "评业接普攻": "平A接普攻",
    "亭类街普攻": "平A接普攻", "蘋雅街普攻": "平A接普攻",
    "评约": "平A",
    "秋季能": "技能",
    "案例": "安利", "安立": "安利",
    "案例一套": "安利一套", "安立一套": "安利一套",
    "绿碗狂蓝": "力挽狂澜", "力弯狂蓝": "力挽狂澜",
    "绿碗狂来": "力挽狂澜", "綠碗狂來": "力挽狂澜",
    "力挽狂蓝": "力挽狂澜",
    "对军": "对局",
    "全体企例": "全体起立", "全體企例": "全体起立",
    "全體起立": "全体起立",
    "開局": "开局", "開居": "开局",
    "开居": "开局",
    "着吧": "这把", "这吧": "这把", "者吧": "这把", "者把": "这把",
    "着把": "这把",
    "主播着吧": "主播这把",
    "主播者把": "主播这把",
    "主播着把": "主播这把",
    "主播这吧": "主播这把",
    "团站": "团战",
    "团站中": "团战中",
    "处装": "出装", "处装选择": "出装选择",
    "初装选择": "出装选择",
    "化身": "化身",
    "起飞": "起飞",
    "实战中": "实战中",
    "下次如果": "下次如果",
    "超护你的想象": "超乎你的想象",
    "如如无人直径": "如入无人之境", "如如无人之敬": "如入无人之境",
    "如如无人之镜": "如入无人之境",
    "剧武吧": "巨无霸",
    "之前剧售": "史前巨兽",
    "千速游龙": "千速游龙",
    "建议如风": "健步如风",
    "究竟移速": "究极移速",
    "究竟素充": "究极速冲",
    "同进无人能敌": "同阵无人能敌", "同进无敌": "同阵无敌",
    "一式同人": "一视同仁",
    "一技决成": "一击决成",
    "五射手机败": "五射手阵败",
    "无限无限划步": "无限无限滑步",
    "无限划步": "无限滑步",
    "保脏发现": "宝藏发现",
    "鼠石惊人": "属实惊人",
    "双刀柳": "双刀流",
    "双刀刀刀": "双刀流",
    "轻时学剪": "轻松学剑",
    "变脑": "电脑", "變腦": "电脑",
    "之前巨售": "史前巨兽",
    "万穴老怪物": "万血老怪物",
    "不知生": "不吱声",
    "不知声": "不吱声",
    "知生": "吱声",
    "以步步登神": "一步步登神",
    "退变成神": "蜕变成神",
    "天神下班": "天神下凡",
    "天虎": "天胡",
    "天狐": "天胡",
    "天焦之路": "天骄之路",
    "高原血统": "高原血统",
    "抄神": "超神",
    "乃浪": "奶酪",
    "任务工业": "任务攻略",
    "宣识": "鞋子",
    "公诉宣识": "攻速鞋子",
    "三诉宣识": "三速鞋子",
    "铁板宣识": "铁板鞋子",
    "鞋字": "鞋子",
    "终极神装备": "终极神装",
    "划身和弹头": "化身核弹头",
    "六重著燒": "六重灼烧", "六重着烧": "六重灼烧",
    "著燒效果": "灼烧效果", "着烧效果": "灼烧效果",
    "著燒": "灼烧", "着烧": "灼烧",
    "着烧降低": "灼烧降低",
    "技能复加着烧": "技能附加灼烧",
    "技能復加著燒": "技能附加灼烧",
    "慨重磨固": "概率触发",
    "互相群乱": "互相群乱",
    "检速": "减速",
    "摩扛": "魔抗",
    "游离卡": "冷却",
    "多金": "多金",
    "采三件好": "才三件套",
    "神庄": "三装",
    "双靠": "双抗",
    "黄图": "黄图",
    "武杀": "五杀",
    "五沙": "五杀", "十五沙": "15杀",
    "二十砂": "20杀",
    "十六杀": "16杀",
    "十次杀": "10次杀",
    "二十二杀": "22杀",
    "三十二杀": "32杀",
    "三十三杀": "33杀",
    "1打5": "1打5",
    "S平分": "S+评分", "S评分": "S+评分",
    "NVP": "MVP",
    "全体起立主导": "全体起立主播",

    # 广告相关术语修正（保留但修正）
    "斗地高手": "段位高手", "豆地高手": "段位高手", "都抵高手": "段位高手",
    "都抵": "段位",
    "权力一副": "全力以赴", "全力与父": "全力以赴", "全力与负": "全力以赴",
    "软盟相铁": "软萌相贴", "软蒙相片": "软萌相贴", "软蒙相铁": "软萌相贴",
    "饱子": "宝子", "薄子": "宝子",
    "治底": "置顶", "治地": "置顶", "執地": "置顶",
    "免担": "免单",
    "药进行": "要进行",
    "陪陪情续价值": "陪陪情绪价值",
    "情续": "情绪",
    "打扣": "打Call",
    "丽负配合": "力负配合",
    "选丽负": "选英雄",

    # 联华战桥已在第一轮修正
    "同夫之橋": "嚎哭深渊", "同夫之桥": "嚎哭深渊",

    # 其他
    "伏文是些许愁像": "",  # 垃圾BGM识别，删除
    "参参的赋温是些许愁像": "",
    "参参的浮温是些许愁像": "",
    "字幕視頻": "",  # 空视频
}

# 合并所有
replacements.update(hero_fixes)
replacements.update(rune_fixes)
replacements.update(equip_fixes)
replacements.update(term_fixes)

# 移除相同映射
replacements = {k: v for k, v in replacements.items() if k != v}

# 按长度降序排列
sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)


def clean_bgm_tail(text):
    """
    清理视频末尾的BGM噪音文字。
    策略：找到最后一个有意义的句子（包含常见结尾语），然后截断后面的内容。
    """
    # 常见结尾标志
    end_markers = [
        "胜率也是有的",
        "胜利率也是有的",
        "胜率也是有",
        "勝率也是有的",
        "勝利率也是有的",
        "如果你也尝试这套玩法",
        "如果你也嘗試這套玩法",
        "感受下",
        "跟随主播第一视角",
        "跟隨主播第一視角",
        "带领队友取胜",
        "帶領隊友取勝",
        "带领队友拿下胜利",
        "快来评论区分享",
        "快來評論區分享",
    ]
    
    lines = text.split('\n')
    last_meaningful_idx = len(lines) - 1
    
    # 从后往前找最后一个包含结尾标志的行
    for marker in end_markers:
        for i in range(len(lines) - 1, -1, -1):
            if marker in lines[i]:
                # 找到标志后，保留这行，但检查后面是否有重复/噪音
                # 给一些缓冲行（可能有一两行有意义的结尾）
                candidate = i
                # 往后看几行，如果有意义就保留
                for j in range(i + 1, min(i + 4, len(lines))):
                    line = lines[j].strip()
                    if not line:
                        continue
                    # 如果是重复的结尾语，跳过
                    if any(m in line for m in end_markers):
                        candidate = j
                        continue
                    # 如果明显是噪音（英文歌词、繁体乱码、重复行）
                    if is_noise_line(line):
                        break
                    candidate = j
                
                last_meaningful_idx = candidate
                # 截断
                result_lines = lines[:last_meaningful_idx + 1]
                # 清理尾部空行
                while result_lines and not result_lines[-1].strip():
                    result_lines.pop()
                return '\n'.join(result_lines) + '\n'
    
    # 没找到结尾标志，尝试从末尾清理明显噪音
    while last_meaningful_idx > 0 and is_noise_line(lines[last_meaningful_idx].strip()):
        last_meaningful_idx -= 1
    
    if last_meaningful_idx < len(lines) - 1:
        result_lines = lines[:last_meaningful_idx + 1]
        while result_lines and not result_lines[-1].strip():
            result_lines.pop()
        return '\n'.join(result_lines) + '\n'
    
    return text


def is_noise_line(line):
    """判断一行是否是BGM噪音"""
    if not line:
        return True
    
    # 纯英文（歌词）
    if re.match(r'^[a-zA-Z\s\',\.\!\?\-\(\)]+$', line):
        return True
    
    # 以 I'm / I was / I can't 等开头的英文歌词
    if re.match(r"^(I'm|I was|I can't|I just|I tried|I had|But in|Watch|Maybe|See me|No one)", line):
        return True
    
    # 繁体+乱码混合
    # 统计繁体字比例高且含乱码特征
    
    # 纯数字行
    if re.match(r'^[\d\s]+$', line):
        return True
    
    # 极短无意义（1-2个字的行，连续多个可能是噪音）
    if len(line) <= 2 and not any(c in line for c in '全体起立海克斯主播'):
        return True
    
    # 重复行模式（如"鱼"、"阿"、"煮"重复）
    if len(set(line.replace(' ', ''))) <= 2 and len(line) <= 6:
        return True
    
    # 包含特定噪音标记
    noise_patterns = [
        r'^à la',
        r'^tu ',
        r'^我 (mirar|tornera|partir)',
        r'^(quarter-th|scraling|detto|Pastor|aule)',
        r'^Não activate',
        r'makeup$',
        r'^\d+$',
    ]
    for pat in noise_patterns:
        if re.search(pat, line):
            return True
    
    return False


def fix_text(text):
    """对文本执行所有替换"""
    for wrong, correct in sorted_replacements:
        text = text.replace(wrong, correct)
    return text


def remove_heavy_repetition(text):
    """移除严重重复的行（连续相同行超过3次）"""
    lines = text.split('\n')
    result = []
    prev_line = None
    repeat_count = 0
    
    for line in lines:
        stripped = line.strip()
        if stripped == prev_line and stripped:
            repeat_count += 1
            if repeat_count <= 2:  # 最多保留3次
                result.append(line)
        else:
            repeat_count = 0
            result.append(line)
        prev_line = stripped
    
    return '\n'.join(result)


def main():
    total_files = 0
    modified_files = 0
    total_replacements = 0
    bgm_cleaned = 0

    txt_files = sorted([f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")])
    total_files = len(txt_files)

    print(f"📋 共 {total_files} 个文件待处理")
    print(f"📖 替换规则: {len(sorted_replacements)} 条\n")

    change_log = []

    for fname in txt_files:
        fpath = os.path.join(TEXT_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            original = f.read()

        # 1. 文本替换
        fixed = fix_text(original)
        
        # 2. 清理BGM尾巴
        cleaned = clean_bgm_tail(fixed)
        
        # 3. 移除严重重复
        cleaned = remove_heavy_repetition(cleaned)

        if cleaned != original:
            modified_files += 1
            file_changes = 0
            for wrong, correct in sorted_replacements:
                count = original.count(wrong)
                if count > 0:
                    file_changes += count
                    total_replacements += count
            
            if cleaned != fixed:
                bgm_cleaned += 1
            
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(cleaned)

            bvid = fname.replace(".txt", "")
            change_log.append(f"  {bvid}: {file_changes} 处修正")
            if modified_files <= 15:
                print(f"  ✅ {fname}: {file_changes} 处修正" + (" + BGM清理" if cleaned != fixed else ""))
            elif modified_files == 16:
                print(f"  ... (后续省略)")

    print(f"\n📊 修正完成:")
    print(f"  总文件: {total_files}")
    print(f"  修改文件: {modified_files}")
    print(f"  总替换次数: {total_replacements}")
    print(f"  BGM噪音清理: {bgm_cleaned} 个文件")

    # 修正汇总文件
    if os.path.exists(SUMMARY_FILE):
        print(f"\n📝 重新生成汇总文件...")
        generate_summary(txt_files)
        print(f"  ✅ 汇总文件已重新生成")

    # 保存修正日志
    log_path = os.path.join(BASE, "海克斯大乱斗_字幕修正日志_v2.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"修正时间: {pd.Timestamp.now()}\n")
        f.write(f"替换规则数: {len(sorted_replacements)}\n")
        f.write(f"修改文件数: {modified_files}/{total_files}\n")
        f.write(f"总替换次数: {total_replacements}\n")
        f.write(f"BGM清理文件数: {bgm_cleaned}\n\n")
        f.write("修改明细:\n")
        for line in change_log:
            f.write(line + "\n")
    print(f"📄 修正日志: {log_path}")


def generate_summary(txt_files):
    """重新生成汇总Markdown"""
    import json
    progress_file = os.path.join(BASE, "海克斯大乱斗_字幕/progress.json")
    progress = {}
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            progress = json.load(f)
    
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("# 海克斯大乱斗 - 视频字幕汇总\n\n")
        f.write(f"- **UP主**: 安逸天晴\n")
        f.write(f"- **视频总数**: {len(txt_files)}\n")
        f.write(f"- **生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Whisper模型**: base\n")
        f.write(f"- **后处理**: 英雄/符文/装备名修正 + BGM噪音清理\n\n")
        f.write("---\n\n")

        for i, fname in enumerate(txt_files, 1):
            bvid = fname.replace(".txt", "")
            fpath = os.path.join(TEXT_DIR, fname)
            
            title = bvid
            url = f"https://www.bilibili.com/video/{bvid}/"
            if bvid in progress:
                title = progress[bvid].get("title", bvid)
                url = progress[bvid].get("url", url)
            
            with open(fpath, "r", encoding="utf-8") as tf:
                text = tf.read().strip()
            
            f.write(f"## {i}. {title}\n\n")
            f.write(f"- **BV号**: {bvid}\n")
            f.write(f"- **链接**: {url}\n\n")
            if text:
                f.write(f"### 转录内容\n\n")
                f.write(text)
                f.write("\n\n")
            else:
                f.write(f"> ⚠️ 无内容\n\n")
            f.write("---\n\n")


if __name__ == "__main__":
    main()
