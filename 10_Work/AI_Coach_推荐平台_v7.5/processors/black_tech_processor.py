# -*- coding: utf-8 -*-
"""
黑科技标记处理器 v3.0
遍历每个英雄的推荐组合，根据黑科技规则库匹配并标记黑科技玩法

核心升级：
1. 定制化描述：结合英雄特性+符文组合生成描述，不机械重复符文效果
2. 统一标签：同类符文组合使用同一个标签名
3. 英雄专属黑科技推荐：即使当前组合没有黑科技符文，也推荐适合该英雄的黑科技玩法
4. combo全部核心符文在才标，single有就标
5. 不提及组合外内容
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

logger = logging.getLogger("BlackTechProcessor")


class BlackTechProcessor:
    """黑科技标记处理器 v3.0"""

    def __init__(self):
        self.rules = []
        self.combo_tags = {}          # 符文组合 → 统一标签
        self.hero_combo_descs = {}    # 英雄+符文组合 → 定制描述
        self.hero_recommend = {}      # 英雄 → 黑科技推荐

    def load_rules(self):
        """加载黑科技规则库"""
        rules_path = os.path.join(config.RAW_DATA_DIR, "black_tech_rules.json")
        if not os.path.exists(rules_path):
            logger.warning(f"黑科技规则文件不存在: {rules_path}")
            return

        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.rules = data.get("rules", [])
        self.combo_tags = data.get("combo_tags", {})
        self.hero_combo_descs = data.get("hero_combo_descriptions", {})
        self.hero_recommend = data.get("hero_black_tech_recommend", {})

        # 清理说明字段
        self.combo_tags.pop("_说明", None)
        self.hero_combo_descs.pop("_说明", None)
        self.hero_recommend.pop("_说明", None)

        logger.info(
            f"黑科技规则加载成功: {len(self.rules)} 条规则, "
            f"{len(self.combo_tags)} 个组合标签, "
            f"{len(self.hero_combo_descs)} 条定制描述, "
            f"{len(self.hero_recommend)} 个英雄推荐"
        )

    def process(self, champion_combos):
        """为英雄组合数据标记黑科技信息（含英雄级别推荐）"""
        self.load_rules()
        if not self.rules:
            logger.warning("无黑科技规则，跳过标记")
            return champion_combos

        total_tagged = 0
        total_combos = 0
        hero_recommend_count = 0

        for champ in champion_combos:
            champion_name = champ.get("champion_name", "")
            combos = champ.get("combos", [])

            for combo in combos:
                total_combos += 1
                augments = combo.get("augments", [])
                tags, desc = self._match_combo(augments, champion_name)

                combo["black_tech_tags"] = tags
                combo["black_tech_desc"] = desc

                if tags:
                    total_tagged += 1

            # 英雄级别黑科技推荐（写到champ层级）
            hero_rec = self._get_hero_recommend(champion_name)
            champ["hero_black_tech_recommend"] = hero_rec
            if hero_rec:
                hero_recommend_count += 1

        logger.info(
            f"黑科技标记完成: {total_combos} 个组合中 {total_tagged} 个命中黑科技 "
            f"(命中率 {total_tagged / total_combos * 100:.1f}%), "
            f"{hero_recommend_count} 个英雄有黑科技推荐"
            if total_combos > 0
            else "黑科技标记完成: 无组合数据"
        )

        return champion_combos

    def _make_combo_key(self, champion_name, augments):
        """
        生成英雄+符文组合的查找key
        格式：英雄名|符文1|符文2|符文3（符文按字典序排列）
        """
        sorted_augs = sorted(augments)
        return champion_name + "|" + "|".join(sorted_augs)

    def _make_aug_key(self, augments):
        """
        生成纯符文组合的查找key（不含英雄名）
        格式：符文1|符文2|符文3（按字典序排列）
        """
        return "|".join(sorted(augments))

    def _match_combo(self, augments, champion_name):
        """
        对一个组合进行黑科技匹配

        优先级：
        1. 英雄+符文定制描述（hero_combo_descriptions）
        2. 符文组合统一标签（combo_tags）
        3. 规则库匹配（rules）

        参数:
            augments: 该组合的符文名称列表
            champion_name: 英雄名称

        返回:
            (tags_str, desc_str)
        """
        augment_set = set(augments)

        # === 第一优先级：查找英雄+符文的定制描述 ===
        hero_combo_key = self._make_combo_key(champion_name, augments)
        custom_desc = self.hero_combo_descs.get(hero_combo_key, "")

        # === 第二优先级：查找符文组合的统一标签 ===
        aug_key = self._make_aug_key(augments)
        unified_tag = self.combo_tags.get(aug_key, "")

        # === 第三优先级：规则库匹配 ===
        matched_tags = []
        matched_descs = []

        for rule in self.rules:
            tag = rule.get("tag", "")
            rule_type = rule.get("type", "single")
            core_augments = set(rule.get("core_augments", []))
            preferred_champions = rule.get("preferred_champions", [])
            single_note = rule.get("single_augment_note", {})
            combo_note = rule.get("combo_note", "")

            matched_augments = augment_set & core_augments
            match_count = len(matched_augments)

            if match_count == 0:
                continue

            if rule_type == "combo":
                # 组合黑科技：全部核心符文都在才标
                if match_count < len(core_augments):
                    continue
                # 有英雄限制时英雄不对则不标
                if preferred_champions and champion_name not in preferred_champions:
                    continue
                matched_tags.append(tag)
                if not custom_desc:
                    # 没有定制描述时才用combo_note
                    if combo_note:
                        matched_descs.append(combo_note)

            else:
                # 单符文黑科技：有就标
                for aug in augments:  # 保持原始顺序
                    if aug in single_note:
                        if preferred_champions and champion_name not in preferred_champions:
                            # 有英雄限制但英雄不对，不标流派标签，不加描述
                            pass
                        else:
                            matched_tags.append(tag)
                            if not custom_desc:
                                matched_descs.append(f"{aug}：{single_note[aug]}")

        # === 组装结果 ===
        # 标签：统一标签优先，其次规则匹配标签
        all_tags = []
        if unified_tag:
            all_tags.append(unified_tag)
        # 追加规则匹配的标签（去重，不重复统一标签）
        for t in matched_tags:
            if t not in all_tags:
                all_tags.append(t)

        # 去重
        unique_tags = list(dict.fromkeys(all_tags))
        tags_str = "、".join(unique_tags) if unique_tags else ""

        # 描述：定制描述优先，其次规则描述
        if custom_desc:
            desc_str = custom_desc
        elif matched_descs:
            desc_str = "；".join(matched_descs)
        else:
            desc_str = ""

        return tags_str, desc_str

    def _get_hero_recommend(self, champion_name):
        """
        获取英雄专属黑科技推荐

        返回:
            推荐文本字符串，无推荐则返回空字符串
        """
        rec = self.hero_recommend.get(champion_name, {})
        if not rec:
            return ""

        recommend_name = rec.get("recommend", "")
        description = rec.get("description", "")

        if recommend_name and description:
            return f"【{recommend_name}】{description}"
        elif description:
            return description
        return ""
