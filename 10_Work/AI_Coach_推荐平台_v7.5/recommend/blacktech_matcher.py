# -*- coding: utf-8 -*-
"""
黑科技匹配 + 话术生成模块
负责：通用黑科技组合匹配、英雄专属黑科技、套装羁绊、话术生成
"""
import logging

logger = logging.getLogger("BlacktechMatcher")


class BlacktechMatcher:
    """
    黑科技匹配器

    规则（按优先级）：
    1. 英雄专属黑科技（任何阶段）→ 最佳拍档标签 + 专属话术
    2. 通用组合成型（已选过组合件）→ 潜力组合标签 + 成型话术
    3. S1/S2 + 通用组合适配英雄 → 潜力组合标签 + 组合话术
    4. S1/S2 + 通用组合不适配英雄 → 强力单卡/趣味（按单卡强度标）
    5. S3/S4 + 未选过组合件 + 非专属 → 强力单卡/趣味
    """

    def __init__(self, data_loader):
        self.dl = data_loader

    def match(self, augment_name, champion_name, stage, selected_augments):
        """
        对一个符文进行黑科技匹配判定

        Args:
            augment_name: 当前待判定的符文名
            champion_name: 当前英雄名
            stage: 当前阶段 (1-4)
            selected_augments: 已选符文列表

        Returns:
            {
                "bonus": int,          # 黑科技加成分(0-30)
                "tag": str,            # 标签: "黑科技"/"强牌"/"趣味"
                "pitch": str,          # ≤10字推荐话术
                "details": list,       # 匹配详情
                "synergy_bonus": int,  # 套装羁绊加成
                "synergy_info": str,   # 套装信息
            }
        """
        bonus = 0
        tag = None
        pitch = ""
        details = []
        synergy_bonus = 0
        synergy_info = ""

        # ========== 一、英雄专属黑科技（不受阶段限制） ==========
        # 尝试多种英雄名匹配（标准名、称号名等）
        hero_bt = self._find_hero_blacktech(champion_name, augment_name)
        if hero_bt:
            bonus += 20
            tag = "最佳拍档"
            # 优先用AI Coach标签建议，其次用标签，最后用原因
            pitch = hero_bt.get("coach_tag", "") or hero_bt.get("标签", "") or hero_bt.get("原因", "")
            if len(pitch) > 15:
                pitch = pitch[:15]
            details.append({
                "type": "hero_exclusive",
                "desc": f"英雄专属黑科技: {champion_name}+{augment_name}",
                "评级": hero_bt.get("评级", ""),
                "bonus": 20,
            })

        # ========== 二、通用黑科技组合（阶段系数在这里体现） ==========
        for combo in self.dl.blacktech_combos:
            aug1, aug2 = combo["aug1"], combo["aug2"]
            # 当前符文必须是组合中的一员
            if augment_name not in [aug1, aug2]:
                continue

            # 判断组合是否适配当前英雄
            hero_fit = self._hero_fits_combo(champion_name, combo)

            # 找到组合的另一半
            other = aug2 if augment_name == aug1 else aug1
            already_have_other = other in selected_augments

            if already_have_other and hero_fit:
                # ★ 组合成型 + 适配英雄！任何阶段都给最高加成
                combo_bonus = 25
                bonus += combo_bonus
                tag = "潜力组合"
                pitch = f"组合成型！{combo.get('pitch', combo.get('流派', ''))}"
                if len(pitch) > 15:
                    pitch = pitch[:15]
                details.append({
                    "type": "combo_complete",
                    "desc": f"组合成型: {aug1}+{aug2} ({combo.get('流派', '')})",
                    "bonus": combo_bonus,
                    "other_augment": other,
                })
            elif already_have_other and not hero_fit:
                # 组合成型但不适配英雄 → 给小幅加成（毕竟组合效果在）
                combo_bonus = 5
                bonus += combo_bonus
                details.append({
                    "type": "combo_complete_nofit",
                    "desc": f"组合成型但不适配{champion_name}: {aug1}+{aug2} ({combo.get('流派', '')})",
                    "bonus": combo_bonus,
                    "other_augment": other,
                })
            elif stage <= 2 and hero_fit:
                # ★ S1/S2 + 适配英雄 → 给潜力组合加成
                combo_bonus = 10
                bonus += combo_bonus
                if tag != "潜力组合":
                    tag = "潜力组合"
                    pitch = combo.get("pitch", combo.get("流派", ""))
                    if len(pitch) > 15:
                        pitch = pitch[:15]
                details.append({
                    "type": "combo_potential_fit",
                    "desc": f"S{stage}阶段+适配英雄: {aug1}+{aug2} ({combo.get('流派', '')})",
                    "bonus": combo_bonus,
                    "need": other,
                })
            elif stage <= 2 and not hero_fit:
                # S1/S2但不适配英雄 → 跳过，不加分
                pass
            elif stage > 2 and hero_fit:
                # S3/S4 + 适配英雄但没有另一半 → 小幅加成（还有一点凑齐的希望）
                combo_bonus = 3
                bonus += combo_bonus
                details.append({
                    "type": "combo_late_stage",
                    "desc": f"S{stage}晚期适配组合: {combo.get('流派', '')}组合件",
                    "bonus": combo_bonus,
                })
            else:
                # S3/S4 + 不适配英雄 + 没有另一半 → 跳过，不加分
                pass

        # ========== 三、套装羁绊加成（独立于黑科技标签） ==========
        all_augments = set(selected_augments + [augment_name])
        for syn in self.dl.synergies:
            syn_augments = set(syn.get("augments", []))
            overlap = all_augments & syn_augments
            if len(overlap) >= 2:
                syn_bonus = 5 * len(overlap)
                synergy_bonus += syn_bonus
                tier_effects = syn.get("tier_effects", {})
                # 找到当前件数对应的效果
                tier_key = f"{len(overlap)}件"
                effect = tier_effects.get(tier_key, "")
                synergy_info_part = f"{syn['name']}({len(overlap)}件)"
                if effect:
                    synergy_info_part += f": {effect[:20]}"
                synergy_info += ("; " if synergy_info else "") + synergy_info_part
                details.append({
                    "type": "synergy",
                    "desc": f"套装: {syn['name']} {len(overlap)}件",
                    "bonus": syn_bonus,
                })

        bonus += synergy_bonus

        # ========== 四、标签兜底 ==========
        if tag is None:
            tag = self._fallback_tag(augment_name)
            if not pitch:
                pitch = self._generate_fallback_pitch(augment_name, champion_name)

        # Cap bonus
        final_bonus = min(bonus, 30)

        return {
            "bonus": final_bonus,
            "tag": tag,
            "pitch": pitch,
            "details": details,
            "synergy_bonus": synergy_bonus,
            "synergy_info": synergy_info,
        }

    def _find_hero_blacktech(self, champion_name, augment_name):
        """查找英雄专属黑科技，支持多种英雄名匹配"""
        # 直接查找
        result = self.dl.hero_blacktech.get((champion_name, augment_name))
        if result:
            return result

        # 通过别名反向查找：遍历hero_blacktech中的英雄名，看是否能映射到同一标准名
        std_name = self.dl.resolve_hero_name(champion_name)
        for (hero, aug), info in self.dl.hero_blacktech.items():
            if aug != augment_name:
                continue
            hero_std = self.dl.resolve_hero_name(hero)
            if hero_std == std_name:
                return info
        return None

    def _hero_fits_combo(self, champion_name, combo):
        """判断英雄是否适配黑科技组合（支持别名匹配）"""
        heroes = combo.get("heroes", [])
        std_name = self.dl.resolve_hero_name(champion_name)
        # 方式1：英雄在推荐英雄列表中（直接或通过别名）
        if champion_name in heroes or std_name in heroes:
            return True
        for h in heroes:
            if self.dl.resolve_hero_name(h) == std_name:
                return True
        # 方式2：英雄类型匹配
        return False

    def _fallback_tag(self, augment_name):
        """
        兜底标签判定（非黑科技时）
        注意：强力单卡和娱乐标签的判定已经在scoring_engine.determine_tag中完成
        这里返回空字符串，表示无特殊标签的普通符文
        """
        return ""

    @staticmethod
    def _clean_tag(text):
        """清理标签中的[AI生成-待审核]前缀"""
        if not text:
            return text
        return text.replace("[AI生成-待审核] ", "").replace("[AI生成-待审核]", "").strip()

    def _generate_fallback_pitch(self, augment_name, champion_name):
        """生成非黑科技的话术"""
        # 优先使用符文推荐理由
        rec = self.dl.augment_recommend.get(augment_name, {})
        tag = self._clean_tag(rec.get("tag", ""))
        comment = self._clean_tag(rec.get("short_comment", ""))
        if tag:
            return tag[:10]
        if comment:
            return comment[:10]

        # 其次使用人话描述摘要
        desc = self.dl.plain_desc.get(augment_name, "")
        if desc and desc != "nan":
            # 人话描述也可能有前缀
            desc = self._clean_tag(desc)
            return desc[:10]

        # 最后兜底
        info = self.dl.augment_info.get(augment_name, {})
        tier = info.get("tier", "")
        if tier in ["T1"]:
            return "版本强势符文"
        elif tier in ["T2"]:
            return "数据优秀"
        else:
            return "可以一试"

    # ==================== 话术组装 ====================

    def generate_card_text(self, augment_name, champion_name, stage,
                           selected_augments, final_score, match_result):
        """
        组装完整的符文卡片展示文本

        Returns:
            {
                "tag_line": "黑科技 | 双灼烧叠加",
                "description": "符文描述（人话版）",
                "ugc_comment": "玩家热评...",
                "fun_fact": "冷知识...",
                "synergy_hint": "套装提示...",
                "combo_hint": "组合提示...",
            }
        """
        tag = match_result["tag"]
        pitch = match_result["pitch"]

        # 标签行
        tag_line = f"{tag} | {pitch}" if pitch else tag

        # 符文描述
        desc = self.dl.plain_desc.get(augment_name, "")
        if not desc or desc == "nan":
            info = self.dl.augment_info.get(augment_name, {})
            desc = info.get("official_desc", info.get("hextech_desc", ""))

        # UGC热评
        hot_comments = self.dl.get_ugc_hot_comment(augment_name, max_count=1)
        ugc_comment = hot_comments[0] if hot_comments else ""

        # 冷知识
        facts = self.dl.fun_facts.get(augment_name, [])
        fun_fact = facts[0] if facts else ""

        # 套装提示
        synergy_hint = match_result.get("synergy_info", "")

        # 组合提示
        combo_hint = ""
        for d in match_result.get("details", []):
            if d["type"] == "combo_complete":
                combo_hint = f"潜力组合成型！已有{d.get('other_augment', '')}+{augment_name}"
            elif d["type"] == "combo_potential_fit":
                combo_hint = f"后续凑{d.get('need', '')}可成型"

        return {
            "tag_line": tag_line,
            "description": desc[:50] if desc else "",
            "ugc_comment": ugc_comment[:50] if ugc_comment else "",
            "fun_fact": fun_fact[:50] if fun_fact else "",
            "synergy_hint": synergy_hint,
            "combo_hint": combo_hint,
        }
