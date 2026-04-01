# -*- coding: utf-8 -*-
"""
hextech.dtodo.cn (ARAM.GG) 实时爬虫
从两个真实数据源获取数据：
  1. /data/aram-mayhem-augments.zh_cn.json  - 符文描述（名称、稀有度、说明等）
  2. /data/augments-stats-raw.json          - 符文统计（胜率、选取率、Tier、适配英雄等）
英雄ID到中文名映射从 CommunityDragon 获取。
"""
import json
import os
import re
import sys
from datetime import datetime

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from crawlers.base_crawler import BaseCrawler


# ============================================================
# hextech 真实数据 API 地址（通过浏览器网络请求抓包确认）
# ============================================================
HEXTECH_DESC_URL = "https://hextech.dtodo.cn/data/aram-mayhem-augments.zh_cn.json"
HEXTECH_STATS_URL = "https://hextech.dtodo.cn/data/augments-stats-raw.json"

# CommunityDragon 英雄中文名映射
CDRAGON_CHAMPION_URL = (
    "https://raw.communitydragon.org/latest/plugins/"
    "rcp-be-lol-game-data/global/zh_cn/v1/champion-summary.json"
)

# 稀有度数字 -> 中文名称
RARITY_MAP = {0: "白银", 1: "黄金", 2: "棱彩"}

# Tier数字 -> 字符串
TIER_MAP = {1: "T1", 2: "T2", 3: "T3", 4: "T4", 5: "T5"}


class HextechCrawler(BaseCrawler):
    """hextech.dtodo.cn 实时符文数据爬虫"""

    def __init__(self):
        super().__init__("HextechCrawler")
        self._champion_map = {}  # champion_id -> 中文名

    # ----------------------------------------------------------
    # 主入口
    # ----------------------------------------------------------
    def crawl(self):
        """主爬取流程 — 优先实时获取，失败才降级到内置数据"""
        self.logger.info("=" * 50)
        self.logger.info("开始实时爬取 hextech.dtodo.cn 符文数据")
        self.logger.info("=" * 50)

        # 步骤0: 获取英雄ID映射
        self._load_champion_map()

        # 步骤1: 实时获取符文描述 + 统计
        augments = self._fetch_realtime_data()

        if not augments:
            self.logger.warning("实时数据获取失败，降级使用内置数据...")
            augments = self._get_builtin_data()

        # 步骤2: 获取套装/羁绊数据（仍使用内置，hextech无单独API）
        sets_data = self._get_builtin_sets_data()

        # 保存
        result = {
            "source": "hextech.dtodo.cn (ARAM.GG)",
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "realtime": bool(augments and len(augments) > 150),
            "total_augments": len(augments),
            "augments": augments,
            "sets": sets_data,
        }
        self.save_json(result, config.HEXTECH_RAW_FILE)

        self.logger.info(
            f"hextech数据爬取完成，共 {len(augments)} 个符文 "
            f"({'实时' if result['realtime'] else '内置'}数据)"
        )
        return result

    # ----------------------------------------------------------
    # 实时数据获取
    # ----------------------------------------------------------
    def _fetch_realtime_data(self):
        """从 hextech 真实数据API获取实时符文数据"""
        self.logger.info("正在获取符文描述数据...")
        desc_data = self._fetch_augment_descriptions()
        if not desc_data:
            return None

        self.logger.info("正在获取符文统计数据...")
        stats_map = self._fetch_augment_stats()
        if not stats_map:
            return None

        # 合并
        augments = []
        for aug_id, desc in desc_data.items():
            if not desc.get("enabled"):
                continue

            name = desc.get("displayName", "")
            rarity_num = desc.get("rarity", 0)
            rarity = RARITY_MAP.get(rarity_num, str(rarity_num))

            # 获取模板数值（用于填充描述中的模板变量）
            spell_values = desc.get("spellDataValues", {})

            # 第三方描述（hextech description字段）— 填充数值（与网站列表页显示一致）
            raw_desc = desc.get("description", "")
            official_desc = self._clean_description(raw_desc, spell_values)

            # 玩家补充描述（hextech tooltip字段）— 填充数值
            raw_tooltip = desc.get("tooltip", "")
            tooltip_desc = self._clean_description(raw_tooltip, spell_values)

            # 统计数据
            stats = stats_map.get(str(aug_id), {})
            win_rate = self._parse_rate(stats.get("win_rate", 0))
            pick_rate = self._parse_rate(stats.get("pick_rate", 0))
            num_games = stats.get("num_games", 0)
            if isinstance(num_games, str):
                num_games = int(num_games)
            tier_num = stats.get("tier", "")
            if isinstance(tier_num, str) and tier_num.isdigit():
                tier_num = int(tier_num)
            tier = TIER_MAP.get(tier_num, "")

            # 适配英雄TOP5
            top_champs = self._parse_top_champions(stats.get("top_champions"))

            # 阶段数据
            stage_stats = self._parse_stage_stats(stats.get("augment_stage_stats"))

            augments.append({
                "name": name,
                "tier": tier,
                "rarity": rarity,
                "win_rate": round(win_rate, 2),
                "pick_rate": round(pick_rate, 2),
                "num_games": num_games,
                "top_champions": top_champs,
                "description": official_desc,
                "tooltip_desc": tooltip_desc,
                "description_raw": raw_desc,
                "tooltip_raw": raw_tooltip,
                "icon_url": desc.get("iconSmall", desc.get("iconLarge", "")),
                "augment_id": int(aug_id),
                "stage_stats": stage_stats,
            })

        # 按胜率排序
        augments.sort(key=lambda x: x["win_rate"], reverse=True)

        self.logger.info(f"实时获取成功: {len(augments)} 个启用符文")

        # 打印tier统计
        tier_counts = {}
        for a in augments:
            t = a.get("tier") or "暂无数据"
            tier_counts[t] = tier_counts.get(t, 0) + 1
        self.logger.info(f"Tier分布: {tier_counts}")

        return augments

    def _get_json_headers(self):
        """获取专用于JSON数据请求的header（避免br编码问题）"""
        return {
            "User-Agent": config.DEFAULT_HEADERS["User-Agent"],
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://hextech.dtodo.cn/zh-CN/augments",
        }

    def _fetch_augment_descriptions(self):
        """获取符文描述数据"""
        data = self.get_json(HEXTECH_DESC_URL, headers=self._get_json_headers())
        if data and isinstance(data, dict) and len(data) > 50:
            total = len(data)
            enabled = sum(1 for v in data.values() if v.get("enabled"))
            self.logger.info(f"符文描述: 总共 {total} 个, 启用 {enabled} 个")
            return data
        self.logger.warning("符文描述数据获取失败")
        return None

    def _fetch_augment_stats(self):
        """获取符文统计数据"""
        data = self.get_json(HEXTECH_STATS_URL, headers=self._get_json_headers())
        if not data or not isinstance(data, list):
            self.logger.warning("符文统计数据获取失败")
            return None

        stats_map = {}
        for item in data:
            try:
                aug_id = str(item[0])
                aug_stats = json.loads(item[1]) if isinstance(item[1], str) else item[1]
                stats_map[aug_id] = aug_stats
            except (json.JSONDecodeError, IndexError, TypeError) as e:
                self.logger.debug(f"解析统计项失败: {e}")

        self.logger.info(f"符文统计: {len(stats_map)} 个符文有数据")
        return stats_map

    # ----------------------------------------------------------
    # 英雄ID映射
    # ----------------------------------------------------------
    def _load_champion_map(self):
        """加载英雄ID到中文名映射"""
        # 优先从缓存文件加载
        cache_path = os.path.join(config.RAW_DATA_DIR, "champion_id_map.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self._champion_map = json.load(f)
                self.logger.info(
                    f"从缓存加载英雄映射: {len(self._champion_map)} 个"
                )
                return
            except Exception:
                pass

        # 从CommunityDragon获取
        self.logger.info("从 CommunityDragon 获取英雄名映射...")
        data = self.get_json(CDRAGON_CHAMPION_URL)
        if data and isinstance(data, list):
            for champ in data:
                cid = str(champ.get("id", ""))
                # description字段 = 中文名（安妮、亚托克斯等）
                name = champ.get("description", "") or champ.get("name", "")
                if cid and cid != "-1" and name:
                    self._champion_map[cid] = name

            # 缓存到文件
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(self._champion_map, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            self.logger.info(f"英雄映射加载完成: {len(self._champion_map)} 个")
        else:
            self.logger.warning("英雄映射获取失败，英雄名将显示为ID")

    def _get_champion_name(self, champion_id):
        """根据ID获取英雄中文名"""
        return self._champion_map.get(str(champion_id), f"英雄{champion_id}")

    # ----------------------------------------------------------
    # 数据解析辅助
    # ----------------------------------------------------------
    @staticmethod
    def _parse_rate(value):
        """将比率转为百分比 (0.6212 -> 62.12)"""
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return 0.0
        if isinstance(value, (int, float)):
            if value <= 1.0:
                return value * 100
            return value
        return 0.0

    def _parse_top_champions(self, top_champions):
        """解析TOP英雄列表 -> 中文名列表"""
        if not top_champions:
            return []
        names = []
        for c in top_champions[:5]:
            if isinstance(c, dict):
                cid = str(c.get("champion_id", ""))
                name = self._get_champion_name(cid)
                names.append(name)
            elif isinstance(c, str):
                names.append(c)
        return names

    def _parse_stage_stats(self, stage_data):
        """解析各阶段统计数据"""
        if not stage_data:
            return []
        stages = []
        for stage in stage_data:
            if isinstance(stage, dict):
                stages.append({
                    "stage": stage.get("stage", ""),
                    "win_rate": round(self._parse_rate(stage.get("win_rate", 0)), 2),
                    "pick_rate": round(self._parse_rate(stage.get("pick_rate", 0)), 2),
                    "num_games": stage.get("num_games", 0),
                    "tier": TIER_MAP.get(stage.get("tier"), str(stage.get("tier", ""))),
                })
        return stages

    @staticmethod
    def _fill_template_values(text, spell_values):
        """将模板变量 @xxx@ 替换为实际数值（支持简单运算如 @var*100@）"""
        if not text or not spell_values:
            # 即使没有spell_values也要清理残留的模板变量
            if text:
                text = re.sub(r"@\w+(\*\d+)?@", "", text)
            return text or ""

        def replacer(m):
            expr = m.group(1)  # 如 "APPerProc" 或 "ADAmp*100"
            if "*" in expr:
                parts = expr.split("*", 1)
                var_name = parts[0]
                try:
                    multiplier = float(parts[1])
                except ValueError:
                    return m.group(0)
                val = spell_values.get(var_name)
                if val is not None:
                    result = float(val) * multiplier
                    if result == int(result):
                        return str(int(result))
                    return str(round(result, 2))
                return m.group(0)
            else:
                val = spell_values.get(expr)
                if val is not None:
                    if isinstance(val, float) and val == int(val):
                        return str(int(val))
                    return str(val)
                return m.group(0)

        # 替换 @xxx@ 和 @xxx*N@ 格式
        result = re.sub(r"@([\w*]+)@", replacer, text)
        # 清理残留的未匹配模板变量（如 @f1@ 运行时变量）
        result = re.sub(r"@\w+@", "", result)
        return result

    @staticmethod
    def _clean_html(text):
        """清理HTML标签，将<br>转为换行"""
        if not text:
            return ""
        # <br>替换为空格（Excel单行显示更友好）
        text = text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
        # 移除所有HTML标签
        text = re.sub(r"<[^>]+>", "", text)
        # 移除%i:xxx%
        text = re.sub(r"%i:\w+%", "", text)
        # 移除 {{xxx}} 模板引用
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        # 清理多余空白
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def _clean_description(cls, raw_desc, spell_values=None):
        """清理符文描述：填充数值 + 移除HTML标签"""
        if not raw_desc:
            return ""
        # 先填充模板变量
        text = cls._fill_template_values(raw_desc, spell_values)
        # 再清理HTML
        text = cls._clean_html(text)
        return text

    # ----------------------------------------------------------
    # 套装/羁绊系统（hextech无单独API，使用内置数据）
    # ----------------------------------------------------------
    def _get_builtin_sets_data(self):
        """
        内置完整的羁绊/套装系统数据
        包含套装名称、效果、组成符文、评级、策略建议和相关英雄
        数据来源: hextech.dtodo.cn 页面信息
        """
        sets = [
            {
                "name": "俯冲炸弹",
                "set_type": "死亡触发",
                "effect": "使你的复活倒计时减少40%",
                "detailed_effect": "当你拥有2个或以上俯冲炸弹系列符文时，你的死亡后复活等待时间缩短40%。这意味着你可以更快回到战场，配合死亡触发效果形成独特的'越死越强'打法。",
                "augments": ["小丑学院", "俯冲轰炸", "自我毁灭", "最终都市列车"],
                "min_trigger": 2,
                "tier": "A",
                "synergy_strength": "强",
                "strategy": "适合敢于冲锋的坦克和战士，死亡时的爆炸伤害配合快速复活，可以持续给对方施压。赛恩和卡尔萨斯是最佳使用者。",
                "best_champions": ["赛恩", "卡尔萨斯", "萨科", "李青", "派克"],
                "combo_tips": "俯冲轰炸+自我毁灭是核心组合，死亡时双重爆炸。如果能再拿到最终都市列车，死后的复仇伤害非常可观。",
            },
            {
                "name": "神龙烈焰",
                "set_type": "灼烧/DOT",
                "effect": "爆竹弹跳额外的次数至相距最近的敌人并造成伤害",
                "detailed_effect": "当你拥有2个或以上神龙烈焰系列符文时，双生火焰的爆竹会额外弹跳，命中更多敌人并造成伤害。灼烧效果叠加后伤害极其可观。",
                "augments": ["祖母的辣椒油", "双生火焰", "炼狱导管", "炼狱龙魂", "火上浇油", "火狐"],
                "min_trigger": 2,
                "tier": "S",
                "synergy_strength": "极强",
                "strategy": "DOT流法师的终极套装。注意：炼狱导管有1秒内置CD限制，火男等英雄的被动不算灼烧效果。核心是祖母的辣椒油+炼狱导管组合。",
                "best_champions": ["布兰德", "兰博", "玛尔扎哈", "莉莉娅", "婕拉"],
                "combo_tips": "祖母的辣椒油是套装核心，炼狱导管是棱彩级增强（但有1秒内置CD）。注意炼狱导管装备无法叠层，只有技能命中才能叠加灼烧。",
            },
            {
                "name": "掷骰狂人",
                "set_type": "升级/赌博",
                "effect": "随机获得额外骰子效果，可能获得额外属性或符文升级",
                "detailed_effect": "当你拥有2个或以上掷骰狂人系列符文时，每次升级符文有概率触发额外随机效果，包括属性加成或再次升级。赌狗的终极快乐。",
                "augments": ["质变：黄金阶", "质变：棱彩阶", "质变：混沌"],
                "min_trigger": 2,
                "tier": "A",
                "synergy_strength": "强（看运气）",
                "strategy": "高风险高回报的赌博流。质变：黄金阶→质变：棱彩阶是黄金升级路线。质变：混沌是终极赌博，全换棱彩。",
                "best_champions": ["约里克", "盖伦", "弗拉基米尔", "佛耶戈", "克烈"],
                "combo_tips": "先拿黄金阶把白银升为黄金，再拿棱彩阶把黄金升为棱彩。运气好等于白给一个棱彩符文。",
            },
            {
                "name": "叠角龙",
                "set_type": "属性叠加",
                "effect": "在你叠层时，获得额外百分比的层数",
                "detailed_effect": "当你拥有2个或以上叠角龙系列符文时，所有叠加类效果的层数获得额外百分比加成。",
                "augments": ["属性！", "属性叠属性！", "属性叠属性叠属性！", "超凡邪恶", "负重爆气", "狂热者"],
                "min_trigger": 2,
                "tier": "S",
                "synergy_strength": "极强",
                "strategy": "属性叠加流的核心羁绊。超凡邪恶本身就是最强符文之一，配合叠角龙效果法强叠加更快。",
                "best_champions": ["维迦", "卡尔萨斯", "奥瑞利安·索尔", "辛德拉", "弗拉基米尔"],
                "combo_tips": "超凡邪恶+属性叠属性！是最强组合。维迦被动+超凡邪恶+叠角龙加成=法强无上限。",
            },
            {
                "name": "喂呜喂呜",
                "set_type": "治疗/辅助",
                "effect": "朝着低生命值友军时获得移动速度、治疗与护盾强度",
                "detailed_effect": "当你拥有2个或以上喂呜喂呜系列符文时，当你朝着低生命值的友军移动时，获得额外的移动速度和治疗与护盾强度。",
                "augments": ["急救用具", "会心治疗", "全心为你", "咏叹奏鸣", "天音爆", "圣火"],
                "min_trigger": 2,
                "tier": "A",
                "synergy_strength": "强",
                "strategy": "辅助/奶妈的专属套装。会心治疗让治疗有概率暴击翻倍，配合喂呜喂呜的治疗强度加成，奶量爆表。",
                "best_champions": ["索拉卡", "悠米", "娑娜", "璐璐", "娜美"],
                "combo_tips": "急救用具+会心治疗是基础组合。治疗暴击+治疗强度加成=队友永远满血。",
            },
            {
                "name": "完全自动化",
                "set_type": "攻击特效",
                "effect": "你的自动释放技能冷却时间基于你的技能急速获得增益",
                "detailed_effect": "当你拥有2个或以上完全自动化系列符文时，你的自动攻击特效触发间隔会基于你的技能急速缩短。",
                "augments": ["台风", "暴击律动", "接二连三", "闪电打击", "狂热者"],
                "min_trigger": 2,
                "tier": "A",
                "synergy_strength": "强",
                "strategy": "攻速流射手的核心套装。闪电打击+暴击律动的组合让攻速流射手的DPS翻倍。",
                "best_champions": ["金克丝", "卡莉丝塔", "崔丝塔娜", "霞", "艾希"],
                "combo_tips": "闪电打击+台风是AOE输出核心，再加暴击律动提供攻速循环。",
            },
            {
                "name": "狙击精英",
                "set_type": "远程输出",
                "effect": "远距离攻击和技能造成的伤害大幅提升",
                "detailed_effect": "当你拥有2个或以上狙击精英系列符文时，你对远距离目标造成的伤害大幅提升。",
                "augments": ["万用瞄准镜", "更万用的瞄准镜", "最万用的瞄准镜", "基石法师", "老练狙神"],
                "min_trigger": 2,
                "tier": "A",
                "synergy_strength": "强",
                "strategy": "远程射手和法师的射程流套装。万用瞄准镜三件套逐级增强。",
                "best_champions": ["凯特琳", "金克丝", "泽拉斯", "拉克丝", "吉格斯"],
                "combo_tips": "更万用的瞄准镜是核心。再配老练狙神或基石法师的远距离加伤，安全输出拉满。",
            },
            {
                "name": "重装坦克",
                "set_type": "防御/坦克",
                "effect": "获得额外的护甲、魔法抗性和生命回复",
                "detailed_effect": "当你拥有2个或以上重装坦克系列符文时，获得额外的坦度加成。坦克越肉，额外加成越高。",
                "augments": ["坦克引擎", "歌利亚巨人", "重量级打击手", "任务：钢化你心", "星界躯体", "坚韧"],
                "min_trigger": 2,
                "tier": "S",
                "synergy_strength": "极强",
                "strategy": "坦克的终极套装。坦克引擎让坦度转化为伤害，歌利亚巨人提供海量血量。",
                "best_champions": ["蒙多医生", "奥恩", "瑟庄妮", "布隆", "赛恩"],
                "combo_tips": "坦克引擎+歌利亚巨人+任务：钢化你心是三核心。蒙多拿到这三个符文，血量能突破8000。",
            },
            {
                "name": "暗影刺客",
                "set_type": "爆发/刺客",
                "effect": "脱离视野后的首次攻击或技能造成额外伤害",
                "detailed_effect": "当你拥有2个或以上暗影刺客系列符文时，脱离敌方视野后对敌方英雄的首次攻击或技能伤害大幅提升。",
                "augments": ["升级：狂妄", "暗影疾奔", "裁决使", "小丑学院", "杀意翻涌"],
                "min_trigger": 2,
                "tier": "A",
                "synergy_strength": "强",
                "strategy": "刺客的专属羁绊。升级：狂妄提供脱离视野后的爆发，暗影疾奔提供隐身和移速。",
                "best_champions": ["劫", "泰隆", "派克", "卡兹克", "奇亚娜"],
                "combo_tips": "升级：狂妄+暗影疾奔是基础组合。脱战隐身→接近目标→爆发一套。",
            },
            {
                "name": "吸血鬼",
                "set_type": "生命偷取",
                "effect": "吸血效果大幅增强，并获得额外的全能吸血",
                "detailed_effect": "当你拥有2个或以上吸血鬼系列符文时，你的所有吸血效果增强。",
                "augments": ["吸血习性", "渴血", "灵魂虹吸", "古式佳酿"],
                "min_trigger": 2,
                "tier": "S",
                "synergy_strength": "极强",
                "strategy": "战士/刺客的终极续航套装。吸血习性是核心，放弃队友治疗换取超强全能吸血。",
                "best_champions": ["亚托克斯", "安蓓萨", "贝蕾亚", "凯隐", "亚恒"],
                "combo_tips": "吸血习性+渴血是万能组合。亚托克斯的被动+吸血习性+渴血=打谁都回满血。",
            },
            {
                "name": "雪球连击",
                "set_type": "雪球增强",
                "effect": "雪球技能增强，命中后获得额外效果",
                "detailed_effect": "当你拥有2个或以上雪球连击系列符文时，大乱斗的雪球技能获得增强效果。",
                "augments": ["升级：雪球", "雪球扭蛋机", "弹球", "史上最大雪球"],
                "min_trigger": 2,
                "tier": "B",
                "synergy_strength": "中等",
                "strategy": "偏娱乐的雪球流套装。适合突进型英雄。",
                "best_champions": ["努努和威朗普", "妮蔻", "凯南", "乌迪尔", "佐伊"],
                "combo_tips": "升级：雪球+雪球扭蛋机提供基础增强，史上最大雪球是终极进化。",
            },
            {
                "name": "龙魂之力",
                "set_type": "龙魂效果",
                "effect": "龙魂效果增强，获得额外的元素加成",
                "detailed_effect": "当你拥有2个或以上龙魂系列符文时，你拥有的龙魂效果增强。",
                "augments": ["炼狱龙魂", "海洋龙魂", "山脉龙魂", "海克斯科技龙魂", "全能龙魂"],
                "min_trigger": 2,
                "tier": "B",
                "synergy_strength": "中等",
                "strategy": "龙魂系列符文提供不同的被动效果。炼狱龙魂适合输出，海洋龙魂适合续航，山脉龙魂适合坦克。",
                "best_champions": ["普朗克", "杰斯", "约里克", "伊莉丝", "希瓦娜"],
                "combo_tips": "炼狱龙魂+祖母的辣椒油可以叠加灼烧效果。全能龙魂是万能选择。",
            },
        ]
        return sets

    # ----------------------------------------------------------
    # 内置数据（仅在API完全不可用时使用的极端降级方案）
    # ----------------------------------------------------------
    def _get_builtin_data(self):
        """极端降级：当所有网络请求都失败时使用的空列表"""
        self.logger.error(
            "无法获取任何实时数据！请检查网络连接。"
            "hextech.dtodo.cn 的数据API可能已变更。"
        )
        return []


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    crawler = HextechCrawler()
    result = crawler.crawl()
    print(f"\n完成！共爬取 {result['total_augments']} 个符文，{len(result['sets'])} 个套装")
    if result["augments"]:
        print("\nTOP 10:")
        for i, a in enumerate(result["augments"][:10], 1):
            champs = ", ".join(a.get("top_champions", [])[:3])
            print(f"  {i}. {a['name']} ({a['rarity']}) {a['tier']} "
                  f"胜率={a['win_rate']}% 选取率={a['pick_rate']}% "
                  f"适配: {champs}")
