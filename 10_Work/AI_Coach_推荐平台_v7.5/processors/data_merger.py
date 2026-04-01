# -*- coding: utf-8 -*-
"""
多源数据合并器
通过符文名称匹配合并掌盟、hextech、B站三个数据源
优先级：掌盟（官方描述）> hextech（胜率/Tier数据）> B站（UGC内容）
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from processors.black_tech_processor import BlackTechProcessor

logger = logging.getLogger("DataMerger")


class DataMerger:
    """多源数据合并器"""

    # 符文名称别名映射（处理不同数据源的命名差异）
    NAME_ALIASES = {
        "质变棱彩阶": "质变：棱彩阶",
        "质变黄金阶": "质变：黄金阶",
        "质变混沌": "质变：混沌",
        "钢化你心": "任务：钢化你心",
        "作弊回城": "作弊：我能回城！",
        "荆棘之甲": "升级：荆棘之甲",
        "收集者": "升级：收集者",
        "无尽之刃": "升级：无尽之刃",
        "狂妄": "升级：狂妄",
        "中娅": "升级：中娅",
        "耀光": "升级：耀光",
        "献祭": "升级：献祭",
        "雪球": "升级：雪球",
        "米凯尔的祝福": "升级：米凯尔的祝福",
    }

    def __init__(self):
        self.hextech_data = None
        self.zhangmeng_data = None
        self.zhangmeng_ugc = None
        self.bilibili_data = None
        self.hextech_champion_combos = None
        self.hextech_synergies = None
        self.arammayhem_combos = None

    def load_data(self):
        """加载所有原始数据"""
        logger.info("加载原始数据...")

        if os.path.exists(config.HEXTECH_RAW_FILE):
            with open(config.HEXTECH_RAW_FILE, "r", encoding="utf-8") as f:
                self.hextech_data = json.load(f)
            logger.info(f"hextech数据加载成功: {self.hextech_data.get('total_augments', 0)} 个符文")

        if os.path.exists(config.ZHANGMENG_RAW_FILE):
            with open(config.ZHANGMENG_RAW_FILE, "r", encoding="utf-8") as f:
                self.zhangmeng_data = json.load(f)
            logger.info(f"掌盟数据加载成功: {self.zhangmeng_data.get('total_augments', 0)} 个符文")

        if os.path.exists(config.ZHANGMENG_UGC_FILE):
            with open(config.ZHANGMENG_UGC_FILE, "r", encoding="utf-8") as f:
                self.zhangmeng_ugc = json.load(f)
            logger.info("掌盟UGC数据加载成功")

        if os.path.exists(config.BILIBILI_RAW_FILE):
            with open(config.BILIBILI_RAW_FILE, "r", encoding="utf-8") as f:
                self.bilibili_data = json.load(f)
            logger.info(f"B站数据加载成功: {self.bilibili_data.get('total_videos', 0)} 个视频")

        if os.path.exists(config.HEXTECH_CHAMPION_COMBOS_FILE):
            with open(config.HEXTECH_CHAMPION_COMBOS_FILE, "r", encoding="utf-8") as f:
                self.hextech_champion_combos = json.load(f)
            has_combos = sum(1 for d in self.hextech_champion_combos if d.get("combos"))
            logger.info(f"hextech英雄组合数据加载成功: {len(self.hextech_champion_combos)} 个英雄, {has_combos} 个有组合")

        if os.path.exists(config.HEXTECH_SYNERGIES_FILE):
            with open(config.HEXTECH_SYNERGIES_FILE, "r", encoding="utf-8") as f:
                self.hextech_synergies = json.load(f)
            logger.info(f"hextech套装/羁绊数据加载成功: {len(self.hextech_synergies)} 个套装")

        if os.path.exists(config.ARAMMAYHEM_RAW_FILE):
            with open(config.ARAMMAYHEM_RAW_FILE, "r", encoding="utf-8") as f:
                self.arammayhem_combos = json.load(f)
            logger.info(f"ARAM Mayhem数据加载成功: {len(self.arammayhem_combos)} 个英雄符文搭配")

    def merge(self):
        """合并所有数据源"""
        logger.info("开始合并数据...")
        self.load_data()

        # 以hextech数据为主（数据最全），掌盟数据补充官方描述
        merged = {}

        # 步骤1: 导入hextech数据（作为基础骨架）
        if self.hextech_data:
            for aug in self.hextech_data.get("augments", []):
                name = aug["name"]
                merged[name] = {
                    "name": name,
                    "rarity": aug.get("rarity", ""),
                    "tier": aug.get("tier", ""),
                    "win_rate": aug.get("win_rate", 0),
                    "pick_rate": aug.get("pick_rate", 0),
                    "top_champions": aug.get("top_champions", []),
                    "icon_url": aug.get("icon_url", ""),
                    "hextech_desc": aug.get("description", ""),  # 第三方描述（hextech）
                    "tooltip_desc": aug.get("tooltip_desc", ""),
                    "zhangmeng_desc": "",  # 官方描述（掌盟）
                    "is_new": False,
                    "ugc_score": 0,
                    "ugc_total_comments": 0,
                    "ugc_comments": [],
                    "related_sets": [],  # 所属套装
                }

        # 步骤2: 用掌盟数据补充（来自官方CDN: kiwi_augments.json + fighting_rune.js）
        if self.zhangmeng_data:
            for aug in self.zhangmeng_data.get("augments", []):
                name = aug["name"]
                if name in merged:
                    # 掌盟官方描述独立存储
                    if aug.get("official_desc"):
                        merged[name]["zhangmeng_desc"] = aug["official_desc"]
                    # 掌盟带数值的描述（来自fighting_rune.js）
                    if aug.get("desc_with_values"):
                        merged[name]["zhangmeng_desc_values"] = aug["desc_with_values"]
                    # 掌盟官方icon优先（来自官方CDN，比hextech的更可靠）
                    if aug.get("icon_url"):
                        merged[name]["icon_url"] = aug["icon_url"]
                    if aug.get("is_new"):
                        merged[name]["is_new"] = True
                    if not merged[name]["rarity"] and aug.get("rarity"):
                        merged[name]["rarity"] = aug["rarity"]
                else:
                    # 掌盟有但hextech没有的符文
                    merged[name] = {
                        "name": name,
                        "rarity": aug.get("rarity", ""),
                        "tier": "",
                        "win_rate": 0,
                        "pick_rate": 0,
                        "top_champions": [],
                        "icon_url": aug.get("icon_url", ""),
                        "hextech_desc": "",
                        "tooltip_desc": "",
                        "zhangmeng_desc": aug.get("official_desc", ""),
                        "zhangmeng_desc_values": aug.get("desc_with_values", ""),
                        "is_new": aug.get("is_new", False),
                        "ugc_score": 0,
                        "ugc_total_comments": 0,
                        "ugc_comments": [],
                        "related_sets": [],
                    }

        # 步骤3: 合并UGC数据（评分 + 热门评论 + 全部评论）
        if self.zhangmeng_ugc:
            for ugc in self.zhangmeng_ugc.get("ugc", []):
                name = ugc.get("augment_name", "")
                if name in merged:
                    merged[name]["ugc_score"] = ugc.get("score", 0)
                    merged[name]["ugc_score_count"] = ugc.get("score_count", 0)
                    merged[name]["ugc_total_comments"] = ugc.get("total_comments", 0)
                    merged[name]["ugc_comment_count"] = ugc.get("comment_count", 0)
                    # 优先用热门评论，其次全部评论
                    hot = ugc.get("hot_comments", [])
                    all_c = ugc.get("all_comments", [])
                    # 合并去重：热门评论 + 全部评论
                    seen_uuids = set()
                    combined_comments = []
                    for c in hot + all_c:
                        uuid = c.get("comment_uuid", "")
                        if uuid and uuid in seen_uuids:
                            continue
                        if uuid:
                            seen_uuids.add(uuid)
                        combined_comments.append(c)
                    merged[name]["ugc_comments"] = combined_comments
                    # 兼容旧字段（top_comments）
                    if not combined_comments:
                        merged[name]["ugc_comments"] = ugc.get("top_comments", [])

        # 步骤4: 提取B站组合数据
        combo_data = []
        if self.bilibili_data:
            combo_tips = self.bilibili_data.get("combo_tips", [])
            if isinstance(combo_tips, list):
                for tip in combo_tips:
                    if isinstance(tip, dict) and tip.get("augments"):
                        combo_data.append(tip)

        # 步骤5: 提取套装数据并建立符文→套装的反向映射
        # 优先使用从hextech.dtodo.cn/synergy爬取的真实套装数据
        sets_data = []
        if self.hextech_synergies:
            sets_data = self.hextech_synergies
            logger.info(f"使用hextech爬取的套装/羁绊数据: {len(sets_data)} 个套装")
        elif self.hextech_data:
            sets_data = self.hextech_data.get("sets", [])
            logger.info(f"使用hextech API的套装数据: {len(sets_data)} 个套装")

        # 为套装添加策略建议和组合技巧
        self._enrich_sets_data(sets_data)

        # 建立反向映射：符文名 → 所属套装名列表
        for s in sets_data:
            set_name = s.get("name", "")
            for aug_name in s.get("augments", []):
                if aug_name in merged:
                    if set_name not in merged[aug_name].get("related_sets", []):
                        merged[aug_name]["related_sets"].append(set_name)

        # 转为列表
        augment_list = list(merged.values())

        # 按胜率排序
        augment_list.sort(key=lambda x: x.get("win_rate", 0), reverse=True)

        # 步骤6: 为英雄组合标记黑科技玩法
        champion_combos_data = self.hextech_champion_combos or []
        if champion_combos_data:
            try:
                black_tech = BlackTechProcessor()
                champion_combos_data = black_tech.process(champion_combos_data)
            except Exception as e:
                logger.error(f"黑科技标记失败: {e}")

        result = {
            "augments": augment_list,
            "combos": combo_data,
            "sets": sets_data,
            "champion_combos": champion_combos_data,
            "arammayhem_combos": self.arammayhem_combos or [],
            "total": len(augment_list),
        }

        # 统计信息
        with_desc = sum(1 for a in augment_list if a.get("hextech_desc") or a.get("zhangmeng_desc"))
        with_ugc = sum(1 for a in augment_list if a.get("ugc_score", 0) > 0)
        with_sets = sum(1 for a in augment_list if a.get("related_sets"))
        logger.info(
            f"数据合并完成: {len(augment_list)} 个符文 "
            f"(有描述: {with_desc}, 有UGC: {with_ugc}, 有套装: {with_sets}), "
            f"{len(combo_data)} 个组合, {len(sets_data)} 个套装"
        )
        return result

    def _enrich_sets_data(self, sets_data):
        """为套装数据添加策略建议和组合技巧"""
        # 基于套装名称和效果的策略建议/组合技巧知识库
        SETS_STRATEGY = {
            "叠角龙": {
                "strategy": "优先选择有叠层机制的符文（如扇巴掌、吞噬灵魂、缩小引擎等），配合叠角龙可以获得额外层数加成。S级套装，尽量凑齐4件获得200%额外层数。适合选择有持续叠层能力的英雄，如近战持续输出型。",
                "combo_tips": "核心组合：扇巴掌+超凡邪恶+缩小引擎/吞噬灵魂/无限循环往复。3件即可获得100%额外层数，性价比最高。注意优先拿任务：钢化你心（叠层型符文），配合升级：狂妄可以滚雪球。4件200%是质变门槛，如果前期拿到2件可以考虑all in叠角龙路线。"
            },
            "神龙烈焰 套装": {
                "strategy": "适合有AOE弹射/多段伤害的英雄和符文，如连拨击锤、魔法飞弹、台风等。2件门槛低（2次弹跳+25%原伤害），适合过渡；4件是质变（3次弹跳+50%原伤害），可以打出爆炸AOE。注意：炼狱导管有1秒内置CD，装备无法叠层。",
                "combo_tips": "核心组合：连拨击锤+台风+点亮他们！或魔法飞弹。2件即可有不错的群伤效果。配合双生火焰可以打出双重弹跳的连锁反应。注意炼狱导管只有技能命中才能叠灼烧（1秒CD），火男被动不算灼烧效果。"
            },
            "完全自动化": {
                "strategy": "专为自动施放技能的英雄设计（如索拉卡、琴女、璐璐等辅助和控制型英雄）。2件缩短30%自动施放冷却，3件更进一步让自动施放受益于技能急速，可以实现近乎无缝施放。A级套装，配合高技能急速出装效果拉满。",
                "combo_tips": "核心组合：回力OK镖+咏叹奏鸣+舞会女王/火狐。自我毁灭适合搭配俯冲炸弹套装交叉使用。量子计算是核心件，如果拿到量子计算优先组这个套装。神圣干预提供保命能力，适合脆皮英雄。配合冰霜幽灵可以打出持续控制。"
            },
            "金币雨": {
                "strategy": "经济型套装，提升从强化符文和击杀中获得的金币。2件+15%，3件+30%，4件+50%。适合前期投资，中后期通过金币优势兑换更强装备。A级套装，适合打经济战术的玩家。",
                "combo_tips": "核心组合：夺金+红包+升级：收集者/升级：献祭。有始有终适合作为终结收割手段，击杀加金。当心小蛋糕提供额外金币来源。建议前期优先凑2件门槛低收益稳，如果运气好拿到更多可以冲3件甚至4件。捐赠可以将金币优势转化为团队优势。"
            },
            "俯冲炸弹 套装": {
                "strategy": "死后复活型套装，减少25%复活倒计时。B级套装，适合经常冲在前线容易阵亡的英雄。配合俯冲轰炸可以在死亡时造成爆炸伤害，死后也能输出。",
                "combo_tips": "核心组合：俯冲轰炸+小丑学院+最终都市列车。自我毁灭提供死亡时伤害，与俯冲轰炸叠加效果很好。适合近战战士/坦克型英雄，死亡后快速复活继续前线压制。注意：这个套装只有2件效果（-25%复活时间），不需要凑太多件。"
            },
            "下雪天": {
                "strategy": "雪球专属套装，大幅提升雪球的技能急速和伤害。B级套装，但如果你是雪球流玩家可以打出很高的上限。2件+50急速+30%伤害，3件+100急速+50%伤害，4件+150急速+100%伤害翻倍！",
                "combo_tips": "核心组合：史上最大雪球+升级：雪球+雪球扭蛋机/弹球/神圣雪球。这个套装需要至少2件才有感觉，3件是甜点。雪球流英雄首选：有位移/突进技能的英雄（如李青、艾克等）搭配效果更好。神圣雪球提供雪球控制加强，弹球增加弹射。"
            },
            "喂呜喂呜": {
                "strategy": "辅助/治疗型套装，朝向低血量友军时获得移速和治疗护盾加成。C级套装但在双人或辅助玩法中很强。2件30%移速+10%治疗，3件40%移速+20%治疗，4件50%移速+30%治疗。",
                "combo_tips": "核心组合：风语者的祝福+全心为你+会心治疗/急救用具。升级：米凯尔的祝福提供解控能力，搭配高移速很适合救人。小猫咪找妈妈和咏叹奏鸣都是治疗增强型符文。适合索拉卡、娜美、璐璐等奶妈型英雄，或者有护盾的辅助。"
            },
            "掷骰狂人": {
                "strategy": "赌博型套装，小兵阵亡时有几率掉落属性锻造器。C级评级但如果运气好可以打出超高上限。3件+20%获得黄金/棱彩锻造器几率，4件+50%几率。适合喜欢博弈的玩家。",
                "combo_tips": "核心组合：质变：混沌+质变：棱彩阶+属性叠属性！。质变：黄金阶也可以搭配使用。潘朵拉的盒子增加随机性但上限更高。这个套装的关键是尽早凑齐，前期投资中后期回报。注意：锻造器是永久属性，越早开始积累越有优势。"
            },
            "大法师": {
                "strategy": "技能连发型套装，施放技能时返还另一个随机技能的冷却时间。C级套装但配合多技能英雄效果很好。2件返还30%冷却。适合技能CD短且频繁施放的英雄。",
                "combo_tips": "核心组合：溢流+由心及物+海洋龙魂/注魔。霸符兄弟提供额外技能互动。海洋龙魂带来的法力回复与技能连发完美搭配。适合法师/AP英雄，特别是多个低CD技能的英雄如锐雯、伊泽瑞尔等。注意只有2件效果（30%返还），不需要凑太多件。"
            },
        }

        for s in sets_data:
            name = s.get("name", "")
            if name in SETS_STRATEGY:
                s["strategy"] = SETS_STRATEGY[name]["strategy"]
                s["combo_tips"] = SETS_STRATEGY[name]["combo_tips"]
            else:
                # 基于效果自动生成简要策略
                effect = s.get("effect", "")
                tier = s.get("tier", "")
                aug_count = len(s.get("augments", []))
                tier_effects = s.get("tier_effects", {})

                strategy_parts = []
                if tier:
                    strategy_parts.append(f"{tier}级套装")
                if aug_count:
                    strategy_parts.append(f"共{aug_count}个可选海克斯")
                if tier_effects:
                    levels = list(tier_effects.keys())
                    strategy_parts.append(f"支持{'/'.join(levels)}层级效果")
                if effect:
                    strategy_parts.append(f"核心效果：{effect}")

                s["strategy"] = "。".join(strategy_parts) + "。" if strategy_parts else ""
                s["combo_tips"] = f"从{aug_count}个羁绊内海克斯中选择搭配，建议优先凑齐最低触发件数以获得基础效果。" if aug_count else ""

        logger.info(f"套装策略建议和组合技巧已生成: {len(sets_data)} 个套装")

    def normalize_name(self, name):
        """标准化符文名称"""
        name = name.strip()
        return self.NAME_ALIASES.get(name, name)
