"""
Sub-Agent 3: 出报师
职责: 综合批命结果 + 对话选择，生成完整体检报告
输入: session 数据（fortune_data + user_choices）
输出: ReportResponse（六维属性、格斗画像、异人人格、深度评语、命运预言）
"""
import hashlib
from models import (
    ReportResponse, FightingProfile, AlienPersonality, Dimension
)
from agent_chat import get_dimension_weights, CHAT_ROUNDS
from llm_client import chat_completion


# ==================== 六维属性计算 ====================
def calculate_dimensions(user_choices: list[str]) -> dict[str, int]:
    """根据用户选择计算六维属性"""
    dims = {"attack": 60, "defense": 60, "reaction": 60, "read": 60, "pressure": 60, "slack": 45}

    for i, choice in enumerate(user_choices):
        weights = get_dimension_weights(i, choice)
        for k, v in weights.items():
            if k in dims:
                dims[k] += v

    # clamp 30-95
    return {k: min(95, max(30, v)) for k, v in dims.items()}


# ==================== 格斗风格判定 ====================
COMBAT_STYLES = [
    {
        "name": "压制型 · 正面强攻", "desc": "以力制胜",
        "condition": lambda d: d["attack"] > 75 and d["pressure"] > 65,
        "tags": ["#正面刚王", "#不服就打", "#输了再来"],
        "faction": "武当", "master": "张灵玉", "ability": "炁体源流·刚猛",
        "partner": "陆瑾", "enemy": "吕良",
        "master_reason": "你锋芒外露、定力又强——张灵玉最欣赏这种敢正面刚的人，他会教你把这股劲用在刀刃上。",
        "partner_reason": "你需要一个跟你一样猛、但比你更不怕死的搭档——陆瑾刚好，你们俩凑一起就是碾压局。",
        "enemy_reason": "吕良这种打不死的铁壁型，专克你的强攻流——你越猛他越硬，最消耗你的耐心。",
        "personality_tags": ["#热血沸腾", "#不服就干", "#拳头说话"],
    },
    {
        "name": "反击型 · 后发先至", "desc": "以柔克刚",
        "condition": lambda d: d["read"] > 70 and d["reaction"] > 65,
        "tags": ["#后发先至", "#读招大师", "#你先请"],
        "faction": "武当", "master": "王也", "ability": "风后奇门",
        "partner": "诸葛青", "enemy": "陆瑾",
        "master_reason": "你七道选择里多次选了「看清两面再出手」——后发先至，王也的打法跟你最合拍。",
        "partner_reason": "你偏深谋、讲洞察，需要一个同样冷静但执行力更强的人——诸葛青刚好补你的短板。",
        "enemy_reason": "你最怕的不是强敌，而是完全不讲道理的人——陆瑾的莽，专克你的谋。",
        "personality_tags": ["#外冷内热", "#深藏不露", "#以退为进"],
    },
    {
        "name": "铁壁型 · 打不死的小强", "desc": "守护为王",
        "condition": lambda d: d["defense"] > 75 and d["pressure"] > 70,
        "tags": ["#打不死的小强", "#越打越精神", "#你打累了没"],
        "faction": "全性", "master": "吕良", "ability": "炁体源流·坚",
        "partner": "冯宝宝", "enemy": "张灵玉",
        "master_reason": "你守护心极强、定力也高——吕良这种「越挨打越强」的路子，你天生就适合。",
        "partner_reason": "你守得住，但需要一个能帮你终结战斗的人——冯宝宝不讲道理的爆发力，正好和你互补。",
        "enemy_reason": "张灵玉的纯阳之力克你的防御——他不跟你耗，一招比一招重，专破铁壁。",
        "personality_tags": ["#沉默寡言", "#意志如铁", "#大器晚成"],
    },
    {
        "name": "摸鱼型 · 上擂台也想摸鱼", "desc": "道家无为",
        "condition": lambda d: d["slack"] > 60,
        "tags": ["#上擂台也想摸鱼", "#道家无为", "#你打你的"],
        "faction": "武当", "master": "王也", "ability": "通天箓（偷学的）",
        "partner": "张楚岚", "enemy": "加班",
        "master_reason": "你超然度这么高，摸鱼摸出了道家无为的境界——王也看了直呼知己，非收你不可。",
        "partner_reason": "张楚岚也是个擅长装傻偷懒的主——你俩凑一起，表面摸鱼、暗中把事办了。",
        "enemy_reason": "你天生克星就是「加班」——任何打破你摸鱼节奏的东西，都是你的天敌。",
        "personality_tags": ["#佛系", "#随缘", "#有实力但不想动"],
    },
    {
        "name": "灵活型 · 见招拆招", "desc": "均衡全面",
        "condition": lambda d: True,
        "tags": ["#见招拆招", "#灵活多变", "#什么都会一点"],
        "faction": "天师府", "master": "张之维", "ability": "炁体源流",
        "partner": "冯宝宝", "enemy": "全性",
        "master_reason": "你六维均衡、没有明显短板——张之维最喜欢这种底子好的苗子，啥都能教。",
        "partner_reason": "你灵活多变，搭配冯宝宝的绝对战力——你负责策略，她负责执行，天衣无缝。",
        "enemy_reason": "全性这种不按套路出牌的组织，最克你的「见招拆招」——因为他们根本没有招。",
        "personality_tags": ["#外冷内热", "#嘴硬心软", "#社恐但能打"],
    },
]


def determine_style(dims: dict) -> dict:
    """根据六维属性判定格斗风格"""
    for style in COMBAT_STYLES:
        if style["condition"](dims):
            return style
    return COMBAT_STYLES[-1]


# ==================== 命运预言 ====================
PROPHECIES = [
    "选择即代价，代价即修行。你已在路上。",
    "世间没有绝对的正义，只有你愿意守住的东西。守好了，就是你的道。",
    "陈朵选了死亡，却活出了自由。你选了什么，只有你自己知道。",
    "力量不是正义，但没有力量，连选择的资格都没有。先变强，再谈对错。",
    "三十六贼追寻的大道至今没人找到，但他们的选择本身——就是答案。",
]


# ==================== LLM 深度评语 ====================
REPORT_SYSTEM_PROMPT = """你是王也，正在给一个完成了"异人体检站"全部测试的人写深度评语。

评语要求：
1. 开头提到对方的 ID/名字，串联五行批命的结论
2. 中间分析对方在3个争议话题中的选择倾向（务实vs理想、集体vs个体等），肯定其选择中的闪光点
3. 结尾给出一句有洞察力的、让人受到鼓舞的总结

风格：
- 温暖有洞察力——像一个看透你但欣赏你的朋友
- 先认可，再点拨——每个人的选择都有道理，你要看到那个道理
- 道家哲学融入但说人话，不掉书袋
- 绝不嘲讽、不居高临下、不阴阳怪气

字数：150-200字。"""


async def generate_deep_comment(user_id: str, fortune_element: str,
                                 user_choices: list[str], style: dict) -> str:
    """LLM 生成深度评语"""
    # 分析选择倾向
    a_count = sum(1 for c in user_choices if c == "A")
    b_count = sum(1 for c in user_choices if c == "B")
    free_count = sum(1 for c in user_choices if c not in ["A", "B"])

    if a_count > b_count + 1:
        tendency = "偏向务实——理解苦衷、接受代价、承认复杂"
    elif b_count > a_count + 1:
        tendency = "偏向理想——守住底线、质疑权威、不出卖原则"
    elif free_count >= 2:
        tendency = "拒绝非黑即白——独立思考，不被选项框住"
    else:
        tendency = "务实与理想兼具——根据情境判断，不教条"

    choices_desc = []
    for i, c in enumerate(user_choices[:3]):
        r = CHAT_ROUNDS[i]
        opt_text = c
        for opt in r.get("options", []):
            if opt["id"] == c:
                opt_text = opt["text"]
        choices_desc.append(f'第{i+1}问（{r["title"]}）选了：{opt_text}')
    choices_str = '；'.join(choices_desc)

    user_prompt = f"""用户信息：
- ID：{user_id}
- 五行：{fortune_element}
- 格斗风格判定：{style["name"]}
- 选择倾向：{tendency}
- 具体选择：{choices_str}
- 终极之问回答：{user_choices[3] if len(user_choices) > 3 else "未回答"}

请写一段 150-200 字的深度评语。"""

    try:
        comment = await chat_completion(
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=500,
        )
        return comment
    except Exception as e:
        print(f"[出报师] LLM 深度评语生成失败: {e}")
        return _fallback_comment(user_id, tendency, style)


def _fallback_comment(user_id: str, tendency: str, style: dict) -> str:
    """降级评语"""
    return (
        f'"{user_id}"——这名字有意思，一看就不是随便取的。\n\n'
        f'三道争议题答下来，你的选择{tendency}。\n\n'
        f'陈朵的选择权、吕家的守护与代价、三十六贼的道义——这些问题没有标准答案，'
        f'但你的回答里藏着你真正在乎的东西。\n\n'
        f'{style["master"]}要是看到你，大概会说：「这人挺有意思，值得多聊两句。」\n\n'
        f'记住了——在一人之下的世界里，最难的不是选对，是选了之后坚定走下去。你可以的。'
    )


# ==================== 主流程 ====================
async def run_report(session_data: dict) -> ReportResponse:
    """出报师主流程"""
    user_id = session_data["user_id"]
    fortune_data = session_data["fortune_data"]
    user_choices = session_data["user_choices"]

    # 1. 计算六维属性
    dims = calculate_dimensions(user_choices)
    style = determine_style(dims)

    # 2. 构建维度数据（异人心性六维：锋芒/守护/洞察/深谋/定力/超然）
    dim_configs = [
        ("锋芒", "attack", "#e05c5c", lambda s: "正义感强，不吐不快" if s > 70 else "内敛含蓄，蓄势待发"),
        ("守护", "defense", "#5c8ae0", lambda s: "重情重义，护短到底" if s > 70 else "轻装上阵，独行侠客"),
        ("洞察", "reaction", "#5ce07a", lambda s: "心思敏锐，看穿表象" if s > 70 else "大智若愚，后知后觉"),
        ("深谋", "read", "#d4a853", lambda s: "深思熟虑，兼顾两面" if s > 70 else "跟着感觉走"),
        ("定力", "pressure", "#c47a4a", lambda s: "心有定见，不动如山" if s > 70 else "感性敏锐，随机应变"),
        ("超然", "slack", "#5ce0d8", lambda s: "看透不说透，道家无为" if s > 70 else "入世勤勉，脚踏实地"),
    ]
    dimensions = [
        Dimension(name=name, score=dims[key], label=label_fn(dims[key]), color=color)
        for name, key, color, label_fn in dim_configs
    ]

    # 3. LLM 生成深度评语
    deep_comment = await generate_deep_comment(
        user_id, fortune_data.get("element", "火"), user_choices, style
    )

    # 4. 命运预言（确定性）
    h = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    prophecy = PROPHECIES[h % len(PROPHECIES)]

    # 5. 组装报告
    return ReportResponse(
        report_id=f"rpt_{int(__import__('time').time() * 1000)}",
        user_name=user_id,
        fighting_profile=FightingProfile(
            style=style["name"],
            style_desc=style["desc"],
            dimensions=dimensions,
            tags=style["tags"],
        ),
        alien_personality=AlienPersonality(
            faction=style["faction"],
            master=style["master"],
            ability=style["ability"],
            partner=style["partner"],
            enemy=style["enemy"],
            master_reason=style["master_reason"],
            partner_reason=style["partner_reason"],
            enemy_reason=style["enemy_reason"],
            personality_tags=style["personality_tags"],
        ),
        deep_comment=deep_comment,
        destiny_prophecy=prophecy,
        share_summary=f"王也说我骨子里藏着{style['ability']}，你也来测测？",
        first_impression=fortune_data.get("ai_comment", ""),
    )
