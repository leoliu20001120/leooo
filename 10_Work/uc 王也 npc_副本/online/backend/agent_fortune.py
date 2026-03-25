"""
Sub-Agent 1: 炁脉鉴定师
职责: 分析用户 ID 的炁脉属性 + 调用 LLM 生成王也风格评语
输入: user_id
输出: FortuneResponse（炁脉类型、暗合角色、潜力评级、标签、评语、星级、命数分）
"""
import hashlib
from models import FortuneResponse, QiAnalysisResult, QiAnalysis
from llm_client import chat_completion

# ==================== 6种炁脉定义 ====================
QI_TYPES = {
    'fenghou': {
        'name': '风后奇门',
        'keywords': '洞察、控制、大局观',
        'character': '王也',
        'emoji': '🌀',
        'color': '#4ECDC4',
        'star_abnormal': 5,
        'star_combat': 3,
    },
    'qiti': {
        'name': '炁体源流',
        'keywords': '天赋、潜力、不可预测',
        'character': '冯宝宝',
        'emoji': '✨',
        'color': '#F0D68A',
        'star_abnormal': 5,
        'star_combat': 5,
    },
    'tongming': {
        'name': '通明拳意',
        'keywords': '刚猛、正道、不退让',
        'character': '张灵玉',
        'emoji': '🔥',
        'color': '#FF6B6B',
        'star_abnormal': 3,
        'star_combat': 5,
    },
    'shuangquan': {
        'name': '双全之手',
        'keywords': '治愈、牺牲、两面性',
        'character': '端木瑛',
        'emoji': '💜',
        'color': '#9B59B6',
        'star_abnormal': 4,
        'star_combat': 3,
    },
    'xingming': {
        'name': '性命双修',
        'keywords': '隐忍、爆发、后劲',
        'character': '张楚岚',
        'emoji': '🔸',
        'color': '#F39C12',
        'star_abnormal': 4,
        'star_combat': 4,
    },
    'tianshi': {
        'name': '天师雷法',
        'keywords': '权威、秩序、碾压',
        'character': '张之维',
        'emoji': '⚡',
        'color': '#3498DB',
        'star_abnormal': 3,
        'star_combat': 5,
    },
}

# 炁脉英文key列表（固定顺序，用于 hash 取模）
QI_KEYS = ['fenghou', 'qiti', 'tongming', 'shuangquan', 'xingming', 'tianshi']

# ==================== 中文含义 → 炁脉映射表 ====================
CHAR_QI_MAP: dict[str, str] = {}

# 风后奇门：洞察、控制、大局观、智谋
_fenghou_chars = (
    '智慧谋策算计划局控棋盘道观悟禅玄妙思虑'
    '通达运筹帷幄知晓觉醒睿聪敏锐鉴察洞识'
)
for _c in _fenghou_chars:
    CHAR_QI_MAP[_c] = 'fenghou'

# 炁体源流：天赋、潜力、不可预测、灵气
_qiti_chars = (
    '灵仙神奇异梦幻天星月宙宇虚空玄灿奥妖'
    '魔幽冥飘渺超凡圣瑞祥云霞光芒绝妙逸仙'
)
for _c in _qiti_chars:
    CHAR_QI_MAP[_c] = 'qiti'

# 通明拳意：刚猛、正道、不退让
_tongming_chars = (
    '刚猛烈勇武力拳击斗战攻克胜威震霸豪壮'
    '硬铁钢锋锐剑戈矛盾坚毅决断正义凛冲锤'
)
for _c in _tongming_chars:
    CHAR_QI_MAP[_c] = 'tongming'

# 双全之手：治愈、牺牲、两面性
_shuangquan_chars = (
    '仁善慈医治愈心德恩惠护佑守卫柔温暖爱'
    '容宽恕怜悯救援助安宁静和平祝福纯净雅'
)
for _c in _shuangquan_chars:
    CHAR_QI_MAP[_c] = 'shuangquan'

# 性命双修：隐忍、爆发、后劲
_xingming_chars = (
    '隐忍藏伏潜深沉默韧耐久磨练修炼积蓄厚'
    '稳重镇定从容沐泽润涛海洋江河湖波浩远'
)
for _c in _xingming_chars:
    CHAR_QI_MAP[_c] = 'xingming'

# 天师雷法：权威、秩序、碾压
_tianshi_chars = (
    '雷电龙凤皇帝王君主尊贵冠首领统御令法'
    '规制度章典宪权势力号命旨昭宏伟峰岳崇高'
)
for _c in _tianshi_chars:
    CHAR_QI_MAP[_c] = 'tianshi'

# ==================== 英文字母 → 炁脉（分6组） ====================
ALPHA_QI_MAP: dict[str, str] = {}
# A-D→风后, E-H→炁体, I-L→通明, M-P→双全, Q-T→性命, U-Z→天师
_alpha_groups = [
    ('ABCD', 'fenghou'),
    ('EFGH', 'qiti'),
    ('IJKL', 'tongming'),
    ('MNOP', 'shuangquan'),
    ('QRST', 'xingming'),
    ('UVWXYZ', 'tianshi'),
]
for _letters, _qi in _alpha_groups:
    for _ch in _letters:
        ALPHA_QI_MAP[_ch] = _qi
        ALPHA_QI_MAP[_ch.lower()] = _qi

# ==================== 数字 → 炁脉 ====================
NUM_QI_MAP: dict[str, str] = {
    '0': 'fenghou', '1': 'fenghou',
    '2': 'qiti', '3': 'qiti',
    '4': 'tongming', '5': 'tongming',
    '6': 'shuangquan',
    '7': 'xingming', '8': 'xingming',
    '9': 'tianshi',
}

# ==================== IP化标签池 ====================
QI_TAG_POOL: dict[str, list[str]] = {
    'fenghou': ['看穿一切', '大局为重', '棋高一着', '运筹帷幄', '局外人视角', '懒人智慧'],
    'qiti': ['天选之人', '命运之外', '无限可能', '不按常理', '天生体质', '未知潜能'],
    'tongming': ['后发先至', '不鸣则已', '一拳定乾坤', '正道之光', '刚正不阿', '铁骨铮铮'],
    'shuangquan': ['治愈之手', '光暗共存', '舍身取义', '柔中带刚', '双面人生', '以心换心'],
    'xingming': ['扮猪吃虎', '深藏不露', '大智若愚', '绝地反击', '厚积薄发', '闷声干大事'],
    'tianshi': ['天雷滚滚', '一锤定音', '碾压全场', '秩序守护', '雷厉风行', '不怒自威'],
}


def _stable_hash(text: str) -> int:
    """稳定 hash，同一 ID 每次结果一致"""
    return int(hashlib.md5(text.encode()).hexdigest(), 16)


def _analyze_char(char: str) -> QiAnalysisResult:
    """分析单个字符的炁脉分布（6维打分）"""
    # 初始化6维为0
    scores: dict[str, float] = {k: 0.0 for k in QI_KEYS}

    matched_qi: str | None = None
    method = 'unicode'
    detail = ''

    # 优先：中文含义映射
    if char in CHAR_QI_MAP:
        matched_qi = CHAR_QI_MAP[char]
        method = 'char'
        detail = f'「{char}」字义归属{QI_TYPES[matched_qi]["name"]}'
    # 英文字母映射
    elif char in ALPHA_QI_MAP:
        matched_qi = ALPHA_QI_MAP[char]
        method = 'alpha'
        detail = f'字母 {char.upper()} 归属{QI_TYPES[matched_qi]["name"]}'
    # 数字映射
    elif char in NUM_QI_MAP:
        matched_qi = NUM_QI_MAP[char]
        method = 'num'
        detail = f'数字 {char} 归属{QI_TYPES[matched_qi]["name"]}'
    else:
        # 未匹配汉字或其他符号：用 Unicode hash 分6组
        code = ord(char)
        h = _stable_hash(f'qi_char_{char}_{code}')
        matched_qi = QI_KEYS[h % 6]
        method = 'unicode'
        if 0x4E00 <= code <= 0x9FFF:
            detail = f'「{char}」字形气息近{QI_TYPES[matched_qi]["name"]}'
        else:
            detail = f'符号「{char}」暗合{QI_TYPES[matched_qi]["name"]}'

    # 主炁脉得0.7分，其余随机分配少量分数（确定性）
    scores[matched_qi] = 0.7
    h2 = _stable_hash(f'scatter_{char}')
    remaining_keys = [k for k in QI_KEYS if k != matched_qi]
    # 剩余0.3分按hash确定性分配
    remainder = 0.3
    for i, k in enumerate(remaining_keys):
        if i < len(remaining_keys) - 1:
            portion = round(((h2 >> (i * 4)) % 10) / 50 * remainder, 2)
            portion = min(portion, remainder)
            scores[k] = portion
            remainder -= portion
        else:
            scores[k] = round(remainder, 2)

    return QiAnalysisResult(
        char=char,
        qi_scores=scores,
        method=method,
        detail=detail,
    )


def analyze_name(user_id: str) -> QiAnalysis:
    """综合分析名字的炁脉属性"""
    chars = [c for c in user_id if c.strip()]
    if not chars:
        chars = ['?']  # 兜底

    char_results = [_analyze_char(c) for c in chars]

    # 汇总6维总分
    qi_totals: dict[str, float] = {k: 0.0 for k in QI_KEYS}
    for r in char_results:
        for k in QI_KEYS:
            qi_totals[k] += r.qi_scores.get(k, 0.0)

    # 四舍五入
    qi_totals = {k: round(v, 2) for k, v in qi_totals.items()}

    # 主炁脉 = 总分最高的
    sorted_qi = sorted(qi_totals.items(), key=lambda x: x[1], reverse=True)
    primary_qi = sorted_qi[0][0]
    secondary_qi = sorted_qi[1][0] if sorted_qi[1][1] > 0 else None

    # 计算平衡度：主脉占比越低越平衡
    total_score = sum(qi_totals.values()) or 1.0
    primary_ratio = qi_totals[primary_qi] / total_score
    balance = min(95, max(20, round((1 - (primary_ratio - 0.16)) * 100)))

    # 潜力评级
    potential_grade = _compute_potential_grade(balance, len(chars), primary_ratio)

    return QiAnalysis(
        char_results=char_results,
        qi_totals=qi_totals,
        primary_qi=primary_qi,
        secondary_qi=secondary_qi,
        potential_grade=potential_grade,
        balance=balance,
    )


def _compute_potential_grade(balance: int, total_chars: int, primary_ratio: float) -> str:
    """计算潜力评级"""
    score = (
        balance * 0.4
        + min(100, total_chars * 10) * 0.3
        + (1 - primary_ratio) * 100 * 0.3
    )
    if score >= 75:
        return '甲等·破格'
    if score >= 55:
        return '乙等·上品'
    if score >= 35:
        return '丙等·良才'
    return '丁等·待觉醒'


def _compute_score(user_id: str, balance: int) -> int:
    """命数分（确定性）"""
    base = 50
    balance_bonus = round(balance * 0.3)
    length_bonus = min(15, len(user_id) * 2)
    h = _stable_hash(user_id)
    jitter = (h % 7) - 3  # -3 ~ +3
    return min(95, max(35, base + balance_bonus + length_bonus + jitter))


def _generate_tags(primary_qi: str, secondary_qi: str | None, user_id: str) -> list[str]:
    """生成 2-3 个确定性IP化标签"""
    qi_info = QI_TYPES[primary_qi]
    pool = QI_TAG_POOL[primary_qi]

    h = _stable_hash(user_id)

    # 标签1：主炁脉池随机选
    tags = [pool[h % len(pool)]]

    # 标签2：主炁脉池再选一个（避免重复）
    idx2 = (h // len(pool)) % len(pool)
    if idx2 == h % len(pool):
        idx2 = (idx2 + 1) % len(pool)
    tags.append(pool[idx2])

    # 标签3：如果有暗合属性，从暗合池选一个
    if secondary_qi and secondary_qi in QI_TAG_POOL:
        sec_pool = QI_TAG_POOL[secondary_qi]
        tags.append(sec_pool[(h >> 8) % len(sec_pool)])

    return tags


# ==================== LLM 评语 Prompt ====================
FORTUNE_SYSTEM_PROMPT = """你是王也——精通望气之术。看一个人的名字，就能读出此人暗藏的炁脉属性。
在异人世界里，炁脉决定了一个人的战斗方式和命运走向。

你的说话风格：
- 毒舌但不恶意——像看透一切但懒得计较的高人
- 偶尔用炁/门派术语但说人话，不掉书袋
- 洞察力强，一句话戳中要害
- 带点懒散和随意，像在摸鱼时顺便给人看相
- 绝不说"哈哈""呵呵"这种社交敷衍"""

FORTUNE_USER_PROMPT_TPL = """此人ID「{user_id}」。炁脉鉴定结果：主脉「{qi_name}」，与{character}同源。暗合「{secondary_qi_name}」。
潜力评级{grade}。请用王也口吻评价此人炁脉特征（50字以内），不要解释分析过程。"""


async def run_fortune(user_id: str) -> FortuneResponse:
    """炁脉鉴定师主流程"""
    # 1. 确定性分析
    analysis = analyze_name(user_id)
    qi_key = analysis.primary_qi
    qi_info = QI_TYPES[qi_key]

    score = _compute_score(user_id, analysis.balance)

    # 星级：基础星级 + 平衡度加成
    abnormal = min(5, qi_info['star_abnormal'] + (1 if analysis.balance > 60 else 0))
    # 战斗星级：暗合属性如果是通明/天师则+1
    combat_bonus = 1 if analysis.secondary_qi in ('tongming', 'tianshi') else 0
    combat = min(5, qi_info['star_combat'] + combat_bonus)

    tags = _generate_tags(qi_key, analysis.secondary_qi, user_id)

    # 2. LLM 生成评语
    secondary_qi_name = QI_TYPES[analysis.secondary_qi]['name'] if analysis.secondary_qi else '未显'

    user_prompt = FORTUNE_USER_PROMPT_TPL.format(
        user_id=user_id,
        qi_name=qi_info['name'],
        character=qi_info['character'],
        secondary_qi_name=secondary_qi_name,
        grade=analysis.potential_grade,
    )

    try:
        ai_comment = await chat_completion(
            messages=[
                {"role": "system", "content": FORTUNE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            max_tokens=150,
        )
    except Exception as e:
        # 降级：使用确定性文案
        ai_comment = (
            f'「{user_id}」——主脉{qi_info["name"]}，'
            f'与{qi_info["character"]}同源。{qi_info["keywords"]}，有点意思。'
        )
        print(f"[炁脉鉴定师] LLM 调用失败，降级到确定性文案: {e}")

    return FortuneResponse(
        session_id="",  # 由上层填充
        user_id=user_id,
        qi_type=qi_info['name'],
        qi_type_key=qi_key,
        qi_emoji=qi_info['emoji'],
        aligned_character=qi_info['character'],
        potential_grade=analysis.potential_grade,
        fortune_score=score,
        abnormal_star=abnormal,
        combat_star=combat,
        qi_analysis=analysis,
        ai_comment=ai_comment,
        tags=tags,
    )
