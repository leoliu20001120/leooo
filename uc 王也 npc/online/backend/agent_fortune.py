"""
Sub-Agent 1: 批命师
职责: 分析用户 ID 的五行属性 + 调用 LLM 生成王也风格评语
输入: user_id
输出: FortuneResponse（属性、标签、评语、星级、命数分）
"""
import hashlib
from models import FortuneResponse, WuxingResult, WuxingAnalysis
from llm_client import chat_completion

# ==================== 五行映射表 ====================
# 常见汉字 → 五行
CHAR_WUXING = {
    '金': '金', '鑫': '金', '铁': '金', '钢': '金', '锋': '金', '锐': '金', '银': '金',
    '铭': '金', '剑': '金', '刚': '金', '利': '金', '成': '金', '诚': '金', '超': '金',
    '鹏': '金', '新': '金', '秋': '金', '白': '金', '思': '金', '信': '金', '小': '金',
    '石': '金', '星': '金', '胜': '金', '珍': '金', '正': '金',
    '木': '木', '林': '木', '森': '木', '杰': '木', '松': '木', '梅': '木', '桐': '木',
    '楠': '木', '楚': '木', '荣': '木', '花': '木', '英': '木', '华': '木', '芳': '木',
    '兰': '木', '竹': '木', '青': '木', '春': '木', '东': '木', '叶': '木', '颖': '木',
    '萌': '木', '艺': '木', '彬': '木',
    '水': '水', '冰': '水', '泉': '水', '涛': '水', '海': '水', '洋': '水', '江': '水',
    '河': '水', '湖': '水', '波': '水', '浩': '水', '清': '水', '润': '水', '深': '水',
    '鸿': '水', '雨': '水', '雪': '水', '霜': '水', '露': '水', '雯': '水', '泽': '水',
    '沐': '水', '潇': '水',
    '火': '火', '炎': '火', '烈': '火', '辉': '火', '耀': '火', '明': '火', '光': '火',
    '亮': '火', '晴': '火', '晨': '火', '旭': '火', '阳': '火', '日': '火', '昊': '火',
    '灿': '火', '丹': '火', '红': '火', '南': '火', '暖': '火', '晓': '火', '熙': '火',
    '土': '土', '地': '土', '坤': '土', '城': '土', '坚': '土', '培': '土', '均': '土',
    '圣': '土', '基': '土', '墨': '土', '安': '土', '宇': '土', '宝': '土', '岩': '土',
    '峰': '土', '崇': '土', '岳': '土', '远': '土', '伟': '土', '勇': '土', '中': '土',
    '佳': '土', '磊': '土',
}

# 英文字母 → 五行
ALPHA_WUXING = {}
for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    elements = ['木', '木', '木', '木', '木',  # A-E
                '火', '火', '火', '火', '火',  # F-J
                '土', '土', '土', '土', '土',  # K-O
                '金', '金', '金', '金', '金',  # P-T
                '水', '水', '水', '水', '水', '水']  # U-Z
    ALPHA_WUXING[c] = elements[i]
    ALPHA_WUXING[c.lower()] = elements[i]

# 数字 → 五行
NUM_WUXING = {'0': '土', '1': '木', '2': '木', '3': '火', '4': '火',
              '5': '土', '6': '金', '7': '金', '8': '水', '9': '水'}

# 五行属性描述
WUXING_TRAITS = {
    '金': {'nature': '刚毅果决', 'personality': '决断型', 'star_abnormal': 3, 'star_combat': 5},
    '木': {'nature': '生生不息', 'personality': '成长型', 'star_abnormal': 4, 'star_combat': 3},
    '水': {'nature': '上善若水', 'personality': '智谋型', 'star_abnormal': 5, 'star_combat': 3},
    '火': {'nature': '炎上光明', 'personality': '爆发型', 'star_abnormal': 3, 'star_combat': 5},
    '土': {'nature': '厚德载物', 'personality': '磐石型', 'star_abnormal': 4, 'star_combat': 4},
}

WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}

ELEMENT_EMOJI = {'金': '⚔️', '木': '🌿', '水': '🌊', '火': '🔥', '土': '🏔️'}


def _analyze_char(char: str) -> WuxingResult:
    """分析单个字符的五行"""
    if char in CHAR_WUXING:
        return WuxingResult(char=char, element=CHAR_WUXING[char], method='char',
                            detail=f'「{char}」字直属{CHAR_WUXING[char]}行')
    if char in ALPHA_WUXING:
        return WuxingResult(char=char, element=ALPHA_WUXING[char], method='alpha',
                            detail=f'字母 {char.upper()} 归属{ALPHA_WUXING[char]}行')
    if char in NUM_WUXING:
        return WuxingResult(char=char, element=NUM_WUXING[char], method='num',
                            detail=f'数字 {char} 天干属{NUM_WUXING[char]}')
    # 中文但不在表中 → Unicode 近似
    code = ord(char)
    if 0x4E00 <= code <= 0x9FFF:
        approx = (code - 0x4E00) % 25 + 1
        elements = ['木', '火', '土', '金', '水']
        el = elements[(approx - 1) % 5]
        return WuxingResult(char=char, element=el, method='stroke',
                            detail=f'「{char}」约{approx}画，尾数属{el}')
    # 其他符号
    elements = ['金', '木', '水', '火', '土']
    return WuxingResult(char=char, element=elements[code % 5], method='code',
                        detail=f'符号「{char}」编码属{elements[code % 5]}')


def analyze_name(user_id: str) -> WuxingAnalysis:
    """综合分析名字的五行"""
    chars = [c for c in user_id if c.strip()]
    char_results = [_analyze_char(c) for c in chars]
    wuxing_count = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
    for r in char_results:
        wuxing_count[r.element] += 1

    sorted_items = sorted(wuxing_count.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_items[0][0]
    secondary = sorted_items[1][0] if sorted_items[1][1] > 0 else None

    total = len(chars) or 1
    max_ratio = sorted_items[0][1] / total
    balance = min(95, max(20, round((1 - (max_ratio - 0.2)) * 100)))

    return WuxingAnalysis(
        char_results=char_results,
        wuxing_count=wuxing_count,
        primary=primary,
        secondary=secondary,
        balance=balance,
    )


def _stable_hash(text: str) -> int:
    """稳定 hash，同一 ID 每次结果一致"""
    return int(hashlib.md5(text.encode()).hexdigest(), 16)


def _compute_score(user_id: str, balance: int) -> int:
    """命数分（确定性）"""
    base = 50
    balance_bonus = round(balance * 0.3)
    length_bonus = min(15, len(user_id) * 2)
    h = _stable_hash(user_id)
    jitter = (h % 7) - 3  # -3 ~ +3
    return min(95, max(35, base + balance_bonus + length_bonus + jitter))


def _generate_tags(primary: str, secondary: str | None, user_id: str) -> list[str]:
    """生成 2-3 个确定性标签"""
    trait = WUXING_TRAITS[primary]
    tags = [f'{primary}属·{trait["nature"]}']

    h = _stable_hash(user_id)
    tag_pool = ['暗藏锋芒', '大巧若拙', '以柔克刚', '不鸣则已', '后发先至',
                '静水流深', '外圆内方', '虚怀若谷', '百折不挠', '心如止水',
                '随遇而安', '直觉惊人', '天生反骨', '赤子之心', '冷面热心']
    tags.append(tag_pool[h % len(tag_pool)])
    tags.append(tag_pool[(h // len(tag_pool)) % len(tag_pool)])
    return tags


# ==================== LLM 评语 System Prompt ====================
FORTUNE_SYSTEM_PROMPT = """你是王也——《一人之下》中武当掌门的关门弟子。
你掌握道家拆字术，看到一个人的名字或ID就能读出此人的本质。

你的说话风格：
- 毒舌但不恶意——像一个看透一切但懒得计较的高人
- 偶尔用道家/五行术语，但说人话，不掉书袋
- 洞察力强，一句话戳中要害
- 带点懒散和随意，像在摸鱼时顺便给人批命
- 绝不说"哈哈""呵呵"这种社交敷衍

示例评语（仅风格参考，不要抄）：
- "这名字带火带金，是想把自己烧成铁水吧？行，至少有股不服输的劲儿。"
- "三个字全是木，你是打算在擂台上生根发芽？不过韧劲倒是有了。"
- "英文ID？行走江湖还用英文名，你是打算跟老外过招吧。不过这几个字母拆开看，暗藏水属——脑子够活。"

现在有一个人来了，你需要根据他的ID/名字做一句话评价（50字以内）。"""

FORTUNE_USER_PROMPT_TPL = """这个人的ID是：「{user_id}」
五行分析结果：主属「{primary}」{secondary_text}，{nature}。
前3个字的五行详情：{details}

请用王也的口吻，对这个人做一句话评价（50字以内）。不要重复五行分析的内容，说点有洞察力的。"""


async def run_fortune(user_id: str) -> FortuneResponse:
    """批命师主流程"""
    # 1. 确定性分析
    analysis = analyze_name(user_id)
    trait = WUXING_TRAITS[analysis.primary]

    score = _compute_score(user_id, analysis.balance)
    abnormal = min(5, trait['star_abnormal'] + (1 if analysis.balance > 60 else 0))
    combat = min(5, trait['star_combat'] + (1 if analysis.secondary and WUXING_SHENG.get(analysis.secondary) == analysis.primary else 0))
    tags = _generate_tags(analysis.primary, analysis.secondary, user_id)

    # 2. LLM 生成评语
    details = '，'.join([r.detail for r in analysis.char_results[:3]])
    secondary_text = f'，辅属「{analysis.secondary}」' if analysis.secondary else ''

    user_prompt = FORTUNE_USER_PROMPT_TPL.format(
        user_id=user_id,
        primary=analysis.primary,
        secondary_text=secondary_text,
        nature=trait['nature'],
        details=details,
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
        ai_comment = f'"{user_id}"——{details}。{trait["nature"]}，有点意思。'
        print(f"[批命师] LLM 调用失败，降级到确定性文案: {e}")

    return FortuneResponse(
        session_id="",  # 由上层填充
        user_id=user_id,
        element=analysis.primary,
        element_emoji=ELEMENT_EMOJI[analysis.primary],
        personality_tag=trait['personality'],
        fortune_score=score,
        abnormal_star=abnormal,
        combat_star=combat,
        wuxing_analysis=analysis,
        ai_comment=ai_comment,
        tags=tags,
    )
