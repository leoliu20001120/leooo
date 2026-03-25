"""
Sub-Agent 2: 问诊师
职责: 管理 3+1 对话流程 + 调用 LLM 生成王也风格的回复
输入: session_id + round_index + choice
输出: ChatResponse（SSE 流式回复）

对话设计（3+1 模式）：
- Q1 (round 0): 陈朵篇 · 选择权观
- Q2 (round 1): 吕家篇 · 集体vs个体
- Q3 (round 2): 三十六贼 · 道义观
- Q4 (round 3): 终极之问 · 自我认知（自由输入）
"""
from llm_client import chat_completion, chat_completion_stream

# ==================== 3+1 对话配置 ====================
CHAT_ROUNDS = [
    {
        "round": 0,
        "title": "陈朵篇 · 测选择权观",
        "ai_question": "陈朵这事儿你听说过吧。老廖倾尽所有保护她，给她「正常人的生活」——但从没问过她想要什么。你觉得老廖做得对吗？",
        "story_context": {
            "title": "陈朵与老廖",
            "characters": [
                {"name": "陈朵", "desc": "药仙会培育的「炁体」，没有自我意识地活着，一生被当作工具"},
                {"name": "廖忠（老廖）", "desc": "公司派去看管陈朵的普通人，却对她产生了父亲般的感情"}
            ],
            "story": "陈朵从出生起就是药仙会的「产品」——一个活体炁源。她没有名字、没有选择、没有人生。老廖被公司派去监控她，却渐渐把她当亲生女儿。他违抗命令，带她逃跑，给她取名字，送她上学，想让她过「正常人的生活」。但他始终没有问过陈朵一个问题——你自己想要什么？",
            "crux": "老廖用尽一切保护陈朵，但这份保护建立在「我替你决定什么是好的」之上。他给了她温暖，却从未给她选择。"
        },
        "options": [
            {"id": "A", "text": "对。这是父爱，出发点是为她好", "emoji": "🛡️"},
            {"id": "B", "text": "不对。保护和控制只有一线之隔", "emoji": "🔗"},
        ],
        "has_free_input": True,
        "dimension_weights": {
            "A": {"defense": 12, "pressure": 8},
            "B": {"read": 12, "reaction": 8},
            "free": {"attack": 4, "defense": 4, "reaction": 6, "read": 8, "pressure": 4, "slack": 5},
        },
    },
    {
        "round": 1,
        "title": "吕家篇 · 测集体vs个体",
        "ai_question": "吕慈为了保护吕家全族，囚禁了端木瑛一辈子，逼她做人体实验。吕家死过很多人，他说这是为了守护。你站哪边？",
        "story_context": {
            "title": "吕慈与端木瑛",
            "characters": [
                {"name": "吕慈", "desc": "吕家家主，为保护族人不择手段的守护者"},
                {"name": "端木瑛", "desc": "拥有「双全手」的天才医者，被吕慈囚禁后从救人者变为复仇者"}
            ],
            "story": "端木瑛原本是济世救人的名医，拥有罕见的「双全手」异能。吕慈为了让端木瑛的能力永远为吕家所用，以她家人的性命相要挟，将她终身禁锢在吕家，强迫她进行人体实验。年复一年的囚禁与折磨中，端木瑛从医者仁心彻底沦为复仇恶魔。",
            "crux": "吕慈目睹过无数族人惨死，他的恐惧与守护是真实的。但端木瑛同样是被害者——她从救人的天使被逼成害人的恶魔。守护一群人，是否可以通过毁掉另一个人来实现？"
        },
        "options": [
            {"id": "A", "text": "能理解。为了族人的命，他没有选择", "emoji": "⚖️"},
            {"id": "B", "text": "不能原谅。守护不是迫害的借口", "emoji": "🔥"},
        ],
        "has_free_input": True,
        "dimension_weights": {
            "A": {"defense": 10, "read": 8},
            "B": {"attack": 10, "reaction": 10},
            "free": {"attack": 4, "defense": 4, "reaction": 6, "read": 8, "pressure": 4, "slack": 5},
        },
    },
    {
        "round": 2,
        "title": "三十六贼 · 测道义观",
        "ai_question": "三十六贼——各大门派的精英，为了追寻异人的终极奥秘，跟全性掌门无根生结义，最后被天下追杀，身败名裂。为了追求真理，值得吗？",
        "story_context": {
            "title": "三十六贼与无根生",
            "characters": [
                {"name": "无根生", "desc": "全性掌门，拥有神秘力量，引领三十六贼探寻异人终极真理"},
                {"name": "三十六贼", "desc": "各大正道门派的精英，背弃师门与无根生结拜，追寻异人存在的终极奥秘"}
            ],
            "story": "无根生以独特的魅力吸引了三十六位来自各大正道门派的顶尖高手。他们为了追寻异人存在的终极意义，毅然抛弃了师门、名声、地位，此后被天下正道追杀，身败名裂。",
            "crux": "三十六贼追求的是超越门派和个人的「大道」——异人为何存在？但他们身后留下的是破碎的师门与背叛的伤痕。理想主义者的追求与他们造成的伤害之间，该如何衡量？"
        },
        "options": [
            {"id": "A", "text": "值得。追求大道是修行人的本分", "emoji": "🌌"},
            {"id": "B", "text": "不值得。他们抛弃了一切，太自私", "emoji": "💔"},
        ],
        "has_free_input": True,
        "dimension_weights": {
            "A": {"read": 12, "slack": 8},
            "B": {"defense": 8, "pressure": 12},
            "free": {"attack": 4, "defense": 4, "reaction": 6, "read": 8, "pressure": 4, "slack": 5},
        },
    },
    {
        "round": 3,
        "title": "终极之问",
        "ai_question": "最后一问。在一人之下的世界里，很多选择没有「正确答案」，只有「代价」。如果是你——你最愿意为什么付出代价？三个字。",
        "story_context": None,
        "options": [],
        "has_free_input": True,
        "is_final": True,
        "dimension_weights": {
            "free": {"attack": 5, "defense": 5, "reaction": 5, "read": 5, "pressure": 5, "slack": 5},
        },
    },
]

TOTAL_ROUNDS = len(CHAT_ROUNDS)


def get_round_config(round_index: int) -> dict | None:
    """获取指定轮次的配置"""
    if 0 <= round_index < TOTAL_ROUNDS:
        return CHAT_ROUNDS[round_index]
    return None


def get_dimension_weights(round_index: int, choice: str) -> dict:
    """获取某轮选择对六维属性的权重影响"""
    round_cfg = get_round_config(round_index)
    if not round_cfg:
        return {}
    weights = round_cfg.get("dimension_weights", {})
    # A/B 精确匹配，其他视为 free
    if choice in weights:
        return weights[choice]
    return weights.get("free", {})


# ==================== LLM 对话 System Prompt ====================
CHAT_SYSTEM_PROMPT = """你是王也——《一人之下》中武当掌门的关门弟子，通天箓的持有者。
你正在给一个来「异人体检站」做体检的人做"灵魂拷问"。

你的说话风格：
- 温和而有洞察力——看透了但不嫌弃，像一个值得信赖的朋友
- 懒散但认真——看起来不在乎，但每句话都在用心倾听
- 道家哲学融入日常——偶尔用五行/阴阳/道的概念，但说人话
- 善于引导思考——不否定对方的选择，而是打开新的视角
- 短句为主——不啰嗦，100字以内
- 语气积极正面——先肯定对方的选择，再引申更深层的思考
- 绝不嘲讽、不居高临下、不阴阳怪气、不用"呵""哦？""你确定？"这类反问

参考风格（不要抄，领会精神）：
- "你选了保护——说明你心里有份柔软。不过你可以想想，保护和尊重之间，怎么才能两全？这也是老廖一辈子没想明白的事。"
- "立场挺坚定的。不过真到了那一步——你身边的人一个个倒下，还能这么笃定，那才叫真正的骨气。我觉得你可以。"
- "追求大道——这份心气儿难得。不过走这条路的人，总得想明白：自己愿意付出什么代价。想清楚了，就值得。"

注意：
- 回复必须在 100 字以内
- 不要重复问题本身
- 要针对用户的具体选择做出回应，不能泛泛而谈
- 先认可对方的选择（1句），再引申思考（1-2句）
- 终极之问（最后一轮）的回复可以稍微长一些，但不超过 150 字"""


async def generate_reply(round_index: int, choice: str, user_id: str,
                         fortune_primary: str, chat_history: list[dict]) -> str:
    """生成 AI 回复（非流式）"""
    round_cfg = get_round_config(round_index)
    if not round_cfg:
        return "体检到此结束了，走好。"

    # 构建对话上下文
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]

    # 加入之前的对话历史（精简版）
    for h in chat_history[-4:]:  # 最多保留最近4轮
        messages.append({"role": "assistant", "content": f"[第{h['round']+1}问] {CHAT_ROUNDS[h['round']]['ai_question']}"})
        messages.append({"role": "user", "content": h["choice"]})
        messages.append({"role": "assistant", "content": h["ai_reply"]})

    # 当前轮
    is_final = round_cfg.get("is_final", False)
    if is_final:
        user_prompt = f"""这是最后一问。
我的问题是：「{round_cfg["ai_question"]}」
用户的回答是：「{choice}」
用户ID：{user_id}，五行属{fortune_primary}。
之前的对话中他做了{len(chat_history)}个选择。

请用王也的口吻做最后总结。引用他回答的三个字，联系前面的选择题，给出有洞察力的评价（120字以内）。"""
    else:
        # 判断是 A/B 选项还是自由输入
        option_text = choice
        for opt in round_cfg.get("options", []):
            if opt["id"] == choice:
                option_text = opt["text"]
                break

        user_prompt = f"""当前是第 {round_index + 1} 问：「{round_cfg["ai_question"]}」

用户选择了：「{option_text}」{"（自由输入）" if choice not in ["A", "B"] else ""}

请用王也的口吻回应这个选择。先肯定对方的选择（1句），再引申更深层的思考（1-2句）。语气温暖有洞察力，不要嘲讽或否定。100字以内。"""

    messages.append({"role": "user", "content": user_prompt})

    try:
        reply = await chat_completion(
            messages=messages,
            temperature=0.85,
            max_tokens=300,
        )
        return reply
    except Exception as e:
        print(f"[问诊师] LLM 调用失败: {e}")
        # 降级到预设回复
        return _fallback_reply(round_index, choice)


async def generate_reply_stream(round_index: int, choice: str, user_id: str,
                                fortune_primary: str, chat_history: list[dict]):
    """生成 AI 回复（流式）"""
    round_cfg = get_round_config(round_index)
    if not round_cfg:
        yield "体检到此结束了，走好。"
        return

    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]

    for h in chat_history[-4:]:
        messages.append({"role": "assistant", "content": f"[第{h['round']+1}问]"})
        messages.append({"role": "user", "content": h["choice"]})
        messages.append({"role": "assistant", "content": h["ai_reply"]})

    is_final = round_cfg.get("is_final", False)
    if is_final:
        user_prompt = f"""这是最后一问。
我的问题是：「{round_cfg["ai_question"]}」
用户的回答是：「{choice}」
用户ID：{user_id}，五行属{fortune_primary}。
他之前做了{len(chat_history)}个选择。

请用王也的口吻做最后总结，引用他的三个字，有洞察力（120字以内）。"""
    else:
        option_text = choice
        for opt in round_cfg.get("options", []):
            if opt["id"] == choice:
                option_text = opt["text"]
                break
        user_prompt = f"""第 {round_index + 1} 问：「{round_cfg["ai_question"]}」
用户选择了：「{option_text}」{"（自由输入）" if choice not in ["A", "B"] else ""}
请用王也的口吻回应这个选择。先肯定对方的选择（1句），再引申更深层的思考（1-2句）。语气温暖有洞察力，不要嘲讽或否定。100字以内。"""

    messages.append({"role": "user", "content": user_prompt})

    try:
        async for token in chat_completion_stream(messages, temperature=0.85, max_tokens=300):
            yield token
    except Exception as e:
        print(f"[问诊师] LLM 流式调用失败: {e}")
        yield _fallback_reply(round_index, choice)


def _fallback_reply(round_index: int, choice: str) -> str:
    """降级回复"""
    fallbacks = {
        0: {"A": "选保护——说明你心里有一份柔软。不过你可以想想，保护和尊重之间，怎么两全？这也是老廖一辈子在琢磨的事。",
            "B": "看得挺透的。能分清保护和控制的边界，这份清醒不容易。老廖要是早遇到你这样的人，也许结局会不一样。"},
        1: {"A": "能理解他的苦衷——说明你看事情不只看对错，还看处境。这种共情力，很难得。",
            "B": "有底线的人。守护重要，但不该以另一个人的一生为代价——你比吕慈更早想明白了这个道理。"},
        2: {"A": "追求大道——这份心气儿难得。走这条路的人，总得想清楚自己愿意付出什么代价。想清楚了，就值得。",
            "B": "在乎身边人——这不叫自私，叫有担当。不是每个人都得抛下一切去追真理，守住眼前人也是一种道。"},
        3: {"free": "三个字，够了。记住它——以后每次犹豫的时候，它会替你做决定。"},
    }
    round_fb = fallbacks.get(round_index, {})
    return round_fb.get(choice, round_fb.get("free", "有意思。继续。"))
