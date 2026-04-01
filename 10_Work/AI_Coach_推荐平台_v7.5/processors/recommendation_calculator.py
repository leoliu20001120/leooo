# -*- coding: utf-8 -*-
"""
推荐指数计算器
基于胜率 + 选取率 + UGC评分 + Tier分级加权计算 S/A/B/C/D 推荐等级
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

logger = logging.getLogger("RecommendationCalculator")


class RecommendationCalculator:
    """推荐指数计算器"""

    def calculate(self, merged_data):
        """计算所有符文的推荐指数"""
        logger.info("开始计算推荐指数...")
        augments = merged_data.get("augments", [])

        for aug in augments:
            # 计算推荐指数
            grade = self._calculate_grade(aug)
            aug["recommendation_grade"] = grade
            aug["recommendation_icon"] = config.RECOMMENDATION_ICONS.get(grade, "一般")

            # 计算适配英雄类型
            aug["champion_types"] = self._infer_champion_types(aug)

        logger.info(f"推荐指数计算完成: {len(augments)} 个符文")

        # 统计各等级分布
        grade_dist = {}
        for aug in augments:
            g = aug["recommendation_grade"]
            grade_dist[g] = grade_dist.get(g, 0) + 1
        logger.info(f"推荐等级分布: {grade_dist}")

        return merged_data

    def _calculate_grade(self, aug):
        """
        计算单个符文的推荐等级

        评分逻辑：
        1. 综合分 = 胜率权重(0.5) + Tier权重(0.3) + UGC评分权重(0.1) + 选取率权重(0.1)
        2. 胜率归一化: (winrate - 45) / (70 - 45) * 100
        3. Tier归一化: T1=100, T2=80, T3=60, T4=40, T5=20
        4. UGC归一化: score / 10 * 100
        5. 选取率归一化: min(pickrate / 2.0, 1.0) * 100
        """
        win_rate = aug.get("win_rate", 0)
        tier = aug.get("tier", "")
        ugc_score = aug.get("ugc_score", 0)
        pick_rate = aug.get("pick_rate", 0)

        # 胜率归一化 (45-70% -> 0-100)
        wr_score = max(0, min(100, (win_rate - 45) / 25 * 100))

        # Tier归一化
        tier_scores = {"T1": 100, "T2": 80, "T3": 60, "T4": 40, "T5": 20, "": 50}
        tier_score = tier_scores.get(tier, 50)

        # UGC评分归一化 (0-10 -> 0-100)
        ugc_norm = ugc_score / 10 * 100 if ugc_score > 0 else 50

        # 选取率归一化 (0-2% -> 0-100)
        pr_score = min(pick_rate / 2.0, 1.0) * 100

        # 加权综合分
        total_score = (
            wr_score * 0.5 +
            tier_score * 0.3 +
            ugc_norm * 0.1 +
            pr_score * 0.1
        )

        # 映射到等级
        if total_score >= 75:
            return "S"
        elif total_score >= 60:
            return "A"
        elif total_score >= 45:
            return "B"
        elif total_score >= 30:
            return "C"
        else:
            return "D"

    def _infer_champion_types(self, aug):
        """根据适配英雄推断英雄类型"""
        champions = aug.get("top_champions", [])
        if not champions:
            return []

        # 英雄类型映射
        champion_types = {
            # 法师
            "维迦": "法师", "泽拉斯": "法师", "布兰德": "法师", "吉格斯": "法师",
            "辛德拉": "法师", "卡尔萨斯": "法师", "兰博": "法师", "玛尔扎哈": "法师",
            "婕拉": "法师", "莉莉娅": "法师", "奥瑞利安·索尔": "法师", "安妮": "法师",
            "佐伊": "法师", "拉克丝": "法师", "奥莉安娜": "法师", "维克兹": "法师",
            "塔莉垭": "法师", "瑞兹": "法师", "卡西奥佩娅": "法师",
            "弗拉基米尔": "法师", "斯维因": "法师", "阿狸": "法师",
            "维克托": "法师", "丽桑卓": "法师", "彗": "法师",
            "薇古丝": "法师", "妮蔻": "法师", "艾尼维亚": "法师",
            "黑默丁格": "法师", "梅尔": "法师", "卡萨丁": "法师",
            # 射手
            "金克丝": "射手", "薇恩": "射手", "霞": "射手", "崔丝塔娜": "射手",
            "凯特琳": "射手", "艾希": "射手", "希维尔": "射手", "厄斐琉斯": "射手",
            "泽丽": "射手", "阿克尚": "射手", "烬": "射手", "德莱文": "射手",
            "卡莉丝塔": "射手", "卑尔维斯": "射手", "图奇": "射手", "奎因": "射手",
            "卡莎": "射手", "斯莫德": "射手", "库奇": "射手", "芸阿娜": "射手",
            "赛娜": "射手", "格雷福斯": "射手",
            # 刺客
            "劫": "刺客", "泰隆": "刺客", "卡兹克": "刺客", "奇亚娜": "刺客",
            "派克": "刺客", "纳亚菲利": "刺客", "萨科": "刺客", "伊芙琳": "刺客",
            "菲兹": "刺客", "乐芙兰": "刺客", "凯隐": "刺客", "雷恩加尔": "刺客",
            "卡特琳娜": "刺客",
            # 战士
            "亚托克斯": "战士", "菲奥娜": "战士", "锐雯": "战士", "贾克斯": "战士",
            "安蓓萨": "战士", "贝蕾亚": "战士", "亚恒": "战士", "克烈": "战士",
            "乌迪尔": "战士", "蔚": "战士", "赫卡里姆": "战士", "永恩": "战士",
            "莎弥拉": "战士", "伊泽瑞尔": "战士", "普朗克": "战士", "杰斯": "战士",
            "约里克": "战士", "艾瑞莉娅": "战士", "卡蜜尔": "战士",
            "奥拉夫": "战士", "泰达米尔": "战士", "易": "战士",
            "瑟提": "战士", "潘森": "战士", "德莱厄斯": "战士",
            "盖伦": "战士", "辛吉德": "战士", "佛耶戈": "战士",
            "奎桑提": "战士", "凯尔": "战士", "纳尔": "战士",
            "俄洛伊": "战士", "嘉文四世": "战士", "李青": "战士",
            "孙悟空": "战士", "特朗德尔": "战士", "雷克塞": "战士",
            "厄加特": "战士", "阿兹尔": "战士",
            # 坦克
            "蒙多医生": "坦克", "奥恩": "坦克", "瑟庄妮": "坦克", "布隆": "坦克",
            "芮尔": "坦克", "蕾欧娜": "坦克", "诺提勒斯": "坦克", "赛恩": "坦克",
            "科加斯": "坦克", "拉莫斯": "坦克", "阿利斯塔": "坦克", "波比": "坦克",
            "墨菲特": "坦克", "扎克": "坦克", "加里奥": "坦克",
            "阿木木": "坦克", "茂凯": "坦克", "斯卡纳": "坦克",
            "莫德凯撒": "坦克", "塔姆": "坦克",
            # 辅助
            "索拉卡": "辅助", "悠米": "辅助", "娑娜": "辅助", "璐璐": "辅助",
            "娜美": "辅助", "洛": "辅助", "塔里克": "辅助", "米利欧": "辅助",
            "烈娜塔·戈拉斯克": "辅助", "迦娜": "辅助", "艾翁": "辅助",
            "巴德": "辅助", "布里茨": "辅助", "莫甘娜": "辅助",
            # 特殊（可能属于多类型）
            "提莫": "法师", "崔斯特": "法师", "阿罗拉": "法师",
            "塞拉斯": "战士", "古拉加斯": "坦克",
            "凯南": "法师", "费德提克": "法师",
            "艾克": "刺客", "格温": "战士",
            "伊莉丝": "战士", "希瓦娜": "战士",
            "奈德丽": "法师", "努努和威朗普": "坦克",
            "魔腾": "刺客",
        }

        types = set()
        for champ in champions:
            if champ in champion_types:
                types.add(champion_types[champ])

        return list(types) if types else ["通用"]
