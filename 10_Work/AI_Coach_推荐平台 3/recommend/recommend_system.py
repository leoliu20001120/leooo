# -*- coding: utf-8 -*-
"""
符文推荐系统 - 主入口
串联：DataLoader → ScoringEngine → BlacktechMatcher → 结果输出
"""
import json
import logging
import os
import random

from .data_loader import DataLoader
from .scoring_engine import ScoringEngine
from .blacktech_matcher import BlacktechMatcher

logger = logging.getLogger("RecommendSystem")


class RecommendSystem:
    """
    符文AI Coach推荐系统

    用法:
        system = RecommendSystem()
        system.load_data()
        result = system.recommend(
            champion_name="火男",
            stage=1,
            candidate_augments=["超凡邪恶", "扇巴掌", "俯冲轰炸"],
            selected_augments=[],
            streak=0
        )
    """

    def __init__(self, data_dir=None):
        self.dl = DataLoader(data_dir)
        self.scorer = ScoringEngine(self.dl)
        self.matcher = BlacktechMatcher(self.dl)
        self.loaded = False

    def load_data(self):
        """加载所有数据"""
        self.dl.load_all()
        self.loaded = True
        logger.info("推荐系统数据加载完成")

    def recommend(self, champion_name, stage, candidate_augments,
                  selected_augments=None, streak=0):
        """
        核心推荐接口

        Args:
            champion_name: 英雄名称（如"火男"）
            stage: 当前阶段 (1-4)
            candidate_augments: 本轮3张候选符文
            selected_augments: 已选符文列表（前几轮选的）
            streak: 连胜/连败数（正=连胜, 负=连败）

        Returns:
            {
                "champion": "火男",
                "stage": 1,
                "streak": 0,
                "weight_profile": "standard",
                "cards": [
                    {
                        "augment": "超凡邪恶",
                        "score": 78.5,
                        "logo": "👍",
                        "logo_text": "推荐选取",
                        "logo_color": "#22c55e",
                        "tag": "黑科技",
                        "tag_line": "黑科技 | 灼烧叠法强",
                        "description": "...",
                        "ugc_comment": "...",
                        "fun_fact": "...",
                        "synergy_hint": "...",
                        "combo_hint": "...",
                        "icon_url": "...",
                        "augment_level": "黄金",
                        "detail": { ... }   # 评分细节
                    },
                    ...
                ]
            }
        """
        if not self.loaded:
            self.load_data()

        selected = selected_augments or []
        # 统一英雄名（支持俗称/称号/标准名）
        std_champion_name = self.dl.resolve_hero_name(champion_name)
        champion_id = self.dl.get_champion_id(std_champion_name)

        cards = []
        for aug_name in candidate_augments:
            # 0. 获取符文基础信息（需要在评分前获取等级信息）
            info = self.dl.augment_info.get(aug_name, {})
            aug_level = info.get("等级", "")

            # 1. 黑科技匹配（使用标准名和原始名都尝试）
            bt_result = self.matcher.match(
                aug_name, std_champion_name, stage, selected
            )

            # 2. 评分 (v3.0: 含英雄胜率纠偏)
            score, detail = self.scorer.calc_final_score(
                aug_name, champion_id, streak, bt_result["bonus"],
                stage=stage, augment_level=aug_level
            )

            # 3. v3.0 新标签判定
            new_tag = self.scorer.determine_tag(
                aug_name, std_champion_name, bt_result, streak
            )
            # 如果新标签为None，使用原有标签兜底
            display_tag = new_tag or bt_result["tag"]

            # 4. 话术生成
            card_text = self.matcher.generate_card_text(
                aug_name, std_champion_name, stage, selected, score, bt_result
            )

            # 5. 组装结果卡片 (v3.0: 使用分英雄自适应阈值)
            card = {
                "augment": aug_name,
                "score": score,
                "logo": self.scorer.get_logo_emoji(score, stage, aug_level, champion_id),
                "logo_text": self.scorer.get_logo(score, stage, aug_level, champion_id),
                "logo_color": self.scorer.get_logo_color(score, stage, aug_level, champion_id),
                "tag": display_tag,
                "tag_line": f"{display_tag} | {bt_result.get('pitch', '')}" if bt_result.get('pitch') else display_tag,
                "pitch": bt_result["pitch"],
                "description": card_text["description"],
                "ugc_comment": card_text["ugc_comment"],
                "fun_fact": card_text["fun_fact"],
                "synergy_hint": card_text["synergy_hint"],
                "combo_hint": card_text["combo_hint"],
                "icon_url": info.get("icon_url", ""),
                "augment_level": info.get("等级", ""),
                "tier": info.get("tier", ""),
                "win_rate": detail.get("win_rate_raw", 0),
                "pick_rate": detail.get("pick_rate_raw", 0),
                "ugc_score": detail.get("ugc_score_raw", 0),
                "hero_correction": detail.get("hero_correction", 0),
                "detail": detail,
                "blacktech_details": bt_result["details"],
            }
            cards.append(card)

        # 按得分降序
        cards.sort(key=lambda c: c["score"], reverse=True)

        # v3.0: 连胜用户应用娱乐逻辑
        if streak >= 3:
            cards = self.scorer.apply_winning_entertainment(cards, streak)

        _, profile_name = self.scorer.get_weight_profile(streak)

        return {
            "champion": std_champion_name,
            "champion_input": champion_name,
            "champion_id": champion_id,
            "stage": stage,
            "streak": streak,
            "weight_profile": profile_name,
            "selected_augments": selected,
            "cards": cards,
        }

    # ==================== 模拟4阶段完整流程 ====================

    def simulate_full_game(self, champion_name, streak=0, seed=None):
        """
        模拟一局完整的4阶段符文选择

        自动随机生成每阶段3个同等级候选符文（白银→黄金→黄金→棱彩）
        每阶段自动选择得分最高的符文

        Returns:
            list of 4个阶段的recommend结果 + 每阶段选的符文
        """
        if not self.loaded:
            self.load_data()

        if seed is not None:
            random.seed(seed)

        # 按等级分类符文
        level_groups = {"白银": [], "黄金": [], "棱彩": []}
        for name, info in self.dl.augment_info.items():
            level = info.get("等级", "")
            if level in level_groups:
                level_groups[level].append(name)

        # 4个阶段的等级序列
        stage_levels = ["白银", "黄金", "黄金", "棱彩"]

        selected = []
        stages_result = []

        for stage_idx, level in enumerate(stage_levels):
            stage = stage_idx + 1
            pool = level_groups.get(level, [])
            # 排除已选的
            available = [a for a in pool if a not in selected]
            if len(available) < 3:
                available = pool[:3]
            candidates = random.sample(available, min(3, len(available)))

            result = self.recommend(
                champion_name=champion_name,
                stage=stage,
                candidate_augments=candidates,
                selected_augments=selected,
                streak=streak,
            )

            # 自动选择得分最高的
            best = result["cards"][0] if result["cards"] else None
            chosen = best["augment"] if best else candidates[0]
            selected.append(chosen)

            result["chosen"] = chosen
            stages_result.append(result)

        return stages_result

    # ==================== 批量导出所有英雄推荐表 ====================

    def export_hero_augment_table(self, output_path=None):
        """
        导出"英雄×符文"推荐总表

        对每个英雄，对所有符文评分，输出标签和话术
        格式: champion, augment, score, logo, tag, pitch, ...
        """
        if not self.loaded:
            self.load_data()

        import csv

        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "output", "hero_augment_recommend_table.csv"
            )

        all_augments = list(self.dl.augment_info.keys())
        all_champions = list(self.dl.champion_name_map.keys())

        logger.info(f"开始导出推荐表: {len(all_champions)} 英雄 × {len(all_augments)} 符文")

        rows = []
        for champ in all_champions:
            champ_id = self.dl.get_champion_id(champ)
            for aug in all_augments:
                aug_info = self.dl.augment_info.get(aug, {})
                aug_level = aug_info.get("等级", "")
                bt_result = self.matcher.match(aug, champ, 1, [])
                score, detail = self.scorer.calc_final_score(
                    aug, champ_id, 0, bt_result["bonus"],
                    stage=1, augment_level=aug_level
                )
                # v3.0: 使用新标签
                new_tag = self.scorer.determine_tag(aug, champ, bt_result, 0)
                display_tag = new_tag or bt_result["tag"]
                rows.append({
                    "英雄": champ,
                    "符文": aug,
                    "等级": aug_level,
                    "最终得分": score,
                    "Logo": self.scorer.get_logo_emoji(score, 1, aug_level, champ_id),
                    "标签": display_tag,
                    "话术": bt_result["pitch"],
                    "胜率(%)": detail.get("win_rate_raw", 0),
                    "选取率(%)": detail.get("pick_rate_raw", 0),
                    "UGC评分": detail.get("ugc_score_raw", 0),
                    "黑科技加成": bt_result["bonus"],
                    "英雄纠偏分": detail.get("hero_correction", 0),
                })

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"推荐表导出完成: {output_path} ({len(rows)} 行)")
        return output_path

    # ==================== 导出JSON数据（供HTML界面使用） ====================

    def export_json_for_ui(self, output_path=None):
        """
        导出完整JSON数据，供交互式HTML界面使用

        包含：所有英雄列表、所有符文信息、黑科技组合、套装
        评分逻辑在HTML的JS中实现（这里只导出原始数据）
        """
        if not self.loaded:
            self.load_data()

        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "output", "recommend_ui_data.json"
            )

        # 英雄列表
        heroes = []
        for name, cid in sorted(self.dl.champion_name_map.items()):
            heroes.append({"id": cid, "name": name})

        # 符文信息（含评分需要的所有数据）
        augments = []
        for name, info in self.dl.augment_info.items():
            ugc = self.dl.get_ugc_score(name)
            hot_comments = self.dl.get_ugc_hot_comment(name, 2)
            facts = self.dl.fun_facts.get(name, [])
            rec = self.dl.augment_recommend.get(name, {})

            augments.append({
                "name": name,
                "level": info.get("等级", ""),
                "tier": info.get("tier", ""),
                "win_rate": info.get("win_rate", 50),
                "pick_rate": info.get("pick_rate", 0),
                "ugc_score": ugc,
                "icon_url": info.get("icon_url", ""),
                "official_desc": info.get("official_desc", ""),
                "plain_desc": info.get("plain_desc", ""),
                "set_name": info.get("所属套装", ""),
                "rec_tag": rec.get("tag", ""),
                "rec_comment": rec.get("short_comment", ""),
                "hot_comments": hot_comments,
                "fun_facts": facts[:1] if facts else [],
            })

        # 通用黑科技组合
        blacktech = []
        for combo in self.dl.blacktech_combos:
            blacktech.append({
                "id": combo.get("id", 0),
                "流派": combo.get("流派", ""),
                "aug1": combo["aug1"],
                "aug2": combo["aug2"],
                "pitch": combo.get("pitch", ""),
                "mechanism": combo.get("mechanism", ""),
                "hero_type": combo.get("hero_type", ""),
                "heroes": combo.get("heroes", []),
            })

        # 英雄专属黑科技
        hero_bt = []
        for (hero, aug), info in self.dl.hero_blacktech.items():
            hero_bt.append({
                "hero": hero,
                "augment": aug,
                "评级": info.get("评级", ""),
                "标签": info.get("标签", ""),
                "coach_tag": info.get("coach_tag", ""),
            })

        # 套装
        synergies = []
        for syn in self.dl.synergies:
            synergies.append({
                "name": syn.get("name", ""),
                "tier": syn.get("tier", ""),
                "effect": syn.get("effect", ""),
                "tier_effects": syn.get("tier_effects", {}),
                "augments": syn.get("augments", []),
            })

        # 英雄×符文统计（如果有SQL数据）
        champion_augment_stats = {}
        for (cid, aug_name), stats in self.dl.champion_augment_stats.items():
            hero_name = self.dl.get_champion_name(cid)
            key = f"{hero_name}|{aug_name}"
            champion_augment_stats[key] = {
                "win_rate": stats["win_rate"],
                "show_rate": stats["show_rate"],
            }

        data = {
            "heroes": heroes,
            "augments": augments,
            "blacktech_combos": blacktech,
            "hero_blacktech": hero_bt,
            "synergies": synergies,
            "champion_augment_stats": champion_augment_stats,
            "meta": {
                "total_heroes": len(heroes),
                "total_augments": len(augments),
                "total_blacktech_combos": len(blacktech),
                "total_hero_blacktech": len(hero_bt),
                "total_synergies": len(synergies),
                "has_sql_data": len(self.dl.augment_stats) > 0
                                and any(k for k in self.dl.champion_augment_stats),
            }
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"UI数据导出完成: {output_path}")
        return output_path
