# -*- coding: utf-8 -*-
"""
数据加载模块
统一加载所有数据源：SQL结果(CSV) + Excel知识库 + JSON知识库
"""
import json
import os
import logging
import pandas as pd

logger = logging.getLogger("DataLoader")

# 默认路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
DATA_DIR = os.path.join(BASE_DIR, "recommend", "data")


class DataLoader:
    """
    统一数据加载器

    数据来源：
    1. SQL取数结果（你跑完放到 recommend/data/ 目录下的CSV）：
       - step1_1_augment_stats.csv      → 单个符文全局胜率&选取率
       - step1_2_champion_augment_stats.csv → 英雄×符文胜率&选取率
       - step1_3_champion_pick_rate.csv  → 英雄出场率
       - step1_4_pair_stats.csv         → 符文×符文组合胜率
       - step1_5_champion_pair_stats.csv → 英雄×符文×符文组合胜率

    2. Excel知识库（output/ 目录）：
       - 海克斯大乱斗符文知识库.xlsx  → 符文基础信息+UGC+套装
       - 黑科技组合分析_v2.2_2符文核心.xlsx → 通用/英雄专属黑科技

    3. JSON知识库（output/raw/ 目录）：
       - zhangmeng_ugc.json   → UGC评分+热评
       - hextech_synergies.json → 官方套装
    """

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

        # === 加载后的数据 ===
        # SQL数据
        self.augment_stats = {}        # {符文名: {win_rate, show_rate}}
        self.champion_augment_stats = {}  # {(英雄id, 符文名): {win_rate, show_rate}}
        self.champion_pick_rate = {}   # {英雄id: pick_rate}
        self.pair_stats = {}           # {(符文A, 符文B): {win_rate, show_rate}}
        self.champion_pair_stats = {}  # {(英雄id, 符文A, 符文B): {win_rate, show_rate}}

        # Excel/JSON知识库
        self.augment_info = {}         # {符文名: {等级, tier, ugc_score, ...}}
        self.ugc_comments = {}         # {符文名: {score, hot_comments}}
        self.blacktech_combos = []     # 25个通用黑科技组合
        self.hero_blacktech = {}       # {(英雄, 符文): {评级, 标签, 原因, ...}}
        self.synergies = []            # 9个官方套装
        self.plain_desc = {}           # 符文人话描述
        self.fun_facts = {}            # 符文冷知识
        self.augment_recommend = {}    # 符文推荐理由 {符文名: {tag, 短评}}
        self.champion_id_map = {}      # {英雄id: 英雄名} 和 {英雄名: 英雄id}
        self.champion_name_map = {}    # 反向映射
        self.hero_alias_map = {}       # {别名/称号: 标准名} 英雄别名映射
        self.augment_id_map = {}       # {数字ID字符串(不带.0): 中文名}
        self.augment_name_to_id = {}   # {中文名: 数字ID字符串(不带.0)}

    def load_all(self):
        """加载所有数据"""
        logger.info("=" * 50)
        logger.info("开始加载全部数据...")
        self._load_champion_id_map()
        self._load_augment_id_map()
        self._load_sql_results()
        self._load_excel_knowledge()
        self._load_json_knowledge()
        self._load_plain_desc_and_fun_facts()
        self._calc_normalization_params()
        logger.info("=" * 50)
        logger.info(f"数据加载完成！")
        self._print_summary()

    def _print_summary(self):
        logger.info(f"  单符文统计: {len(self.augment_stats)} 条")
        logger.info(f"  英雄×符文统计: {len(self.champion_augment_stats)} 条")
        logger.info(f"  英雄出场率: {len(self.champion_pick_rate)} 条")
        logger.info(f"  符文对统计: {len(self.pair_stats)} 条")
        logger.info(f"  英雄×符文对统计: {len(self.champion_pair_stats)} 条")
        logger.info(f"  符文基础信息: {len(self.augment_info)} 条")
        logger.info(f"  UGC评分: {len(self.ugc_comments)} 条")
        logger.info(f"  通用黑科技组合: {len(self.blacktech_combos)} 条")
        logger.info(f"  英雄专属黑科技: {len(self.hero_blacktech)} 条")
        logger.info(f"  官方套装: {len(self.synergies)} 条")
        logger.info(f"  英雄ID映射: {len(self.champion_id_map)} 条")

    # ==================== SQL结果加载 ====================

    def _load_sql_results(self):
        """加载SQL取数结果CSV"""
        logger.info("加载SQL取数结果...")

        # Step 1.1: 单个符文全局胜率&选取率
        path = os.path.join(self.data_dir, "step1_1_augment_stats.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                name = str(row["player_augment"])
                self.augment_stats[name] = {
                    "win_rate": float(row["win_rate"]) * 100,    # 转为百分比
                    "show_rate": float(row["show_rate"]) * 100,
                }
            logger.info(f"  Step1.1 单符文统计: {len(self.augment_stats)} 条")
        else:
            logger.warning(f"  Step1.1 文件不存在: {path}，将使用Excel知识库中的数据")
            self._fallback_augment_stats_from_excel()

        # Step 1.2: 英雄×符文胜率&选取率
        path = os.path.join(self.data_dir, "step1_2_champion_augment_stats.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                key = (str(row["championid"]), str(row["player_augment"]))
                self.champion_augment_stats[key] = {
                    "win_rate": float(row["win_rate"]) * 100,
                    "show_rate": float(row["show_rate"]) * 100,
                }
            logger.info(f"  Step1.2 英雄×符文统计: {len(self.champion_augment_stats)} 条")
        else:
            logger.warning(f"  Step1.2 文件不存在: {path}")

        # Step 1.3: 英雄出场率 & 英雄胜率
        self.champion_win_rate = {}  # {英雄id: win_rate(百分比)}
        path = os.path.join(self.data_dir, "step1_3_champion_pick_rate.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                cid = str(row["championid"])
                self.champion_pick_rate[cid] = float(row["pick_rate"]) * 100
                if "win_rate" in df.columns and pd.notna(row.get("win_rate")):
                    self.champion_win_rate[cid] = float(row["win_rate"]) * 100
            logger.info(f"  Step1.3 英雄出场率: {len(self.champion_pick_rate)} 条, "
                        f"英雄胜率: {len(self.champion_win_rate)} 条")
            # 计算全英雄平均胜率，写回scoring_engine作为纠偏基准
            self._calc_hero_avg_winrate()
        else:
            logger.warning(f"  Step1.3 文件不存在: {path}")

        # Step 1.4: 符文×符文组合胜率
        path = os.path.join(self.data_dir, "step1_4_pair_stats.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                a, b = str(row["aug_a"]), str(row["aug_b"])
                key = tuple(sorted([a, b]))
                self.pair_stats[key] = {
                    "win_rate": float(row["pair_win_rate"]) * 100,
                    "show_rate": float(row["pair_show_rate"]) * 100,
                }
            logger.info(f"  Step1.4 符文对统计: {len(self.pair_stats)} 条")
        else:
            logger.warning(f"  Step1.4 文件不存在: {path}")

        # Step 1.5: 英雄×符文×符文组合胜率
        path = os.path.join(self.data_dir, "step1_5_champion_pair_stats.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                cid = str(row["championid"])
                a, b = str(row["aug_a"]), str(row["aug_b"])
                pair = tuple(sorted([a, b]))
                key = (cid, pair[0], pair[1])
                self.champion_pair_stats[key] = {
                    "win_rate": float(row["pair_win_rate"]) * 100,
                    "show_rate": float(row["pair_show_rate"]) * 100,
                }
            logger.info(f"  Step1.5 英雄×符文对统计: {len(self.champion_pair_stats)} 条")
        else:
            logger.warning(f"  Step1.5 文件不存在: {path}")

    def _fallback_augment_stats_from_excel(self):
        """从Excel知识库回退加载符文胜率（当SQL数据不可用时）"""
        excel_path = os.path.join(OUTPUT_DIR, "海克斯大乱斗符文知识库.xlsx")
        if not os.path.exists(excel_path):
            return
        df = pd.read_excel(excel_path, sheet_name="符文基础信息")
        for _, row in df.iterrows():
            name = str(row["符文名称"])
            wr = row.get("胜率(%)", 0)
            pr = row.get("选取率(%)", 0)
            if pd.notna(wr) and pd.notna(pr):
                self.augment_stats[name] = {
                    "win_rate": float(wr),
                    "show_rate": float(pr),
                }
        logger.info(f"  [回退] 从Excel加载符文统计: {len(self.augment_stats)} 条")

    # ==================== Excel知识库加载 ====================

    def _load_excel_knowledge(self):
        """加载Excel知识库"""
        logger.info("加载Excel知识库...")

        # 1. 符文基础信息
        excel_path = os.path.join(OUTPUT_DIR, "海克斯大乱斗符文知识库.xlsx")
        if os.path.exists(excel_path):
            self._load_augment_info(excel_path)
            self._load_augment_recommend(excel_path)
        else:
            logger.warning(f"  符文知识库不存在: {excel_path}")

        # 2. 黑科技组合（优先v5验证版，回退v3，再回退v2.2）
        bt_path_v5 = os.path.join(OUTPUT_DIR, "黑科技组合分析_v5.xlsx")
        bt_path_v3 = os.path.join(OUTPUT_DIR, "黑科技组合分析_v3.xlsx")
        bt_path = os.path.join(OUTPUT_DIR, "黑科技组合分析_v2.2_2符文核心.xlsx")
        if os.path.exists(bt_path_v5):
            self._load_blacktech(bt_path_v5)
        elif os.path.exists(bt_path_v3):
            self._load_blacktech(bt_path_v3)
        elif os.path.exists(bt_path):
            self._load_blacktech(bt_path)
        else:
            logger.warning(f"  黑科技组合分析不存在")

    def _load_augment_info(self, excel_path):
        """加载符文基础信息"""
        df = pd.read_excel(excel_path, sheet_name="符文基础信息")
        for _, row in df.iterrows():
            name = str(row["符文名称"])
            self.augment_info[name] = {
                "等级": str(row.get("等级", "")),
                "tier": str(row.get("Tier分级", "")),
                "win_rate": float(row["胜率(%)"]) if pd.notna(row.get("胜率(%)")) else 0,
                "pick_rate": float(row["选取率(%)"]) if pd.notna(row.get("选取率(%)")) else 0,
                "ugc_score": float(row["UGC评分"]) if pd.notna(row.get("UGC评分")) else 0,
                "ugc_count": int(row["评分样本数"]) if pd.notna(row.get("评分样本数")) else 0,
                "official_desc": str(row.get("官方描述（掌盟）", "")),
                "hextech_desc": str(row.get("第三方描述（hextech）", "")),
                "plain_desc": str(row.get("人话描述", "")),
                "所属套装": str(row.get("所属套装", "")),
                "icon_url": str(row.get("icon_URL", "")),
            }
        logger.info(f"  符文基础信息: {len(self.augment_info)} 条")

    def _load_augment_recommend(self, excel_path):
        """加载符文推荐理由"""
        try:
            df = pd.read_excel(excel_path, sheet_name="符文推荐理由")
            for _, row in df.iterrows():
                name = str(row["符文名称"])
                self.augment_recommend[name] = {
                    "tag": str(row.get("推荐tag", "")),
                    "short_comment": str(row.get("短评（5-10字）", "")),
                    "hero_type": str(row.get("适配英雄类型", "")),
                }
            logger.info(f"  符文推荐理由: {len(self.augment_recommend)} 条")
        except Exception as e:
            logger.warning(f"  加载符文推荐理由失败: {e}")

    def _load_blacktech(self, bt_path):
        """加载黑科技组合数据"""
        # 通用黑科技组合
        df1 = pd.read_excel(bt_path, sheet_name="通用黑科技组合")
        for _, row in df1.iterrows():
            combo = {
                "id": int(row["序号"]),
                "流派": str(row.get("流派", "")),
                "aug1": str(row["符文1"]),
                "aug1_tier": str(row.get("符文1等级", "")),
                "aug2": str(row["符文2"]),
                "aug2_tier": str(row.get("符文2等级", "")),
                "pitch": str(row.get("推荐话术", "")),
                "套装归属": str(row.get("套装归属", "")),
                "mechanism": str(row.get("为什么协同(机制)", "")),
                "hero_type": str(row.get("适配英雄类型", "")),
                "heroes_str": str(row.get("适配英雄", "")),
                "hero_count": int(row.get("组合出现英雄数", 0)) if pd.notna(row.get("组合出现英雄数")) else 0,
                "avg_winrate": float(row.get("平均胜率", 0)) if pd.notna(row.get("平均胜率")) else 0,
            }
            # 解析适配英雄列表
            heroes_str = combo["heroes_str"]
            if heroes_str and heroes_str != "nan":
                combo["heroes"] = [h.strip() for h in heroes_str.replace("、", ",").split(",") if h.strip()]
            else:
                combo["heroes"] = []
            self.blacktech_combos.append(combo)
        logger.info(f"  通用黑科技组合: {len(self.blacktech_combos)} 条")

        # 英雄专属黑科技
        df2 = pd.read_excel(bt_path, sheet_name="英雄专属黑科技")
        bt_hero_names = set()  # 收集Excel中出现的所有英雄名(称号名)
        for _, row in df2.iterrows():
            hero = str(row.get("英雄", ""))
            aug = str(row.get("符文", ""))
            if hero and aug:
                self.hero_blacktech[(hero, aug)] = {
                    "评级": str(row.get("评级", "")),
                    "标签": str(row.get("社区标签", "")),
                    "分数": int(row.get("社区分数", 0)) if pd.notna(row.get("社区分数")) else 0,
                    "原因": str(row.get("黑科技原因", "")),
                    "coach_tag": str(row.get("AI Coach标签建议", "")),
                }
                bt_hero_names.add(hero)
        logger.info(f"  英雄专属黑科技: {len(self.hero_blacktech)} 条")

        # 自动建立称号名→标准名映射（黑科技Excel中用称号名，需映射到champion_id_map中的标准名）
        self._build_bt_hero_alias(bt_hero_names)

    # ==================== JSON知识库加载 ====================

    def _load_json_knowledge(self):
        """加载JSON知识库"""
        logger.info("加载JSON知识库...")

        # UGC评论
        ugc_path = os.path.join(RAW_DIR, "zhangmeng_ugc.json")
        if os.path.exists(ugc_path):
            with open(ugc_path, "r", encoding="utf-8") as f:
                ugc_raw = json.load(f)
            # JSON格式: {"source": "...", "ugc": [{...}, ...]}
            ugc_data = ugc_raw.get("ugc", ugc_raw) if isinstance(ugc_raw, dict) else ugc_raw
            for item in ugc_data:
                name = item.get("augment_name", "")
                if name:
                    self.ugc_comments[name] = {
                        "score": item.get("score", 0),
                        "score_count": item.get("score_count", 0),
                        "hot_comments": item.get("hot_comments", []),
                        "all_comments": item.get("all_comments", []),
                    }
            logger.info(f"  UGC评论: {len(self.ugc_comments)} 条")
            # 计算UGC评分的均值和标准差，用于下限截断
            self._calc_ugc_clip_floor()
        else:
            logger.warning(f"  UGC文件不存在: {ugc_path}")

        # 官方套装
        syn_path = os.path.join(RAW_DIR, "hextech_synergies.json")
        if os.path.exists(syn_path):
            with open(syn_path, "r", encoding="utf-8") as f:
                self.synergies = json.load(f)
            logger.info(f"  官方套装: {len(self.synergies)} 条")
        else:
            logger.warning(f"  套装文件不存在: {syn_path}")

    def _calc_hero_avg_winrate(self):
        """
        从step1_3的真实数据计算全英雄平均胜率，写回scoring_engine模块
        用于英雄胜率纠偏: delta = avg_winrate - hero_winrate
        """
        from recommend import scoring_engine as se_module

        if not self.champion_win_rate:
            logger.warning("  无英雄胜率数据，使用默认50%作为纠偏基准")
            return

        import numpy as np
        winrates = np.array(list(self.champion_win_rate.values()))
        avg_wr = float(winrates.mean())

        se_module.HERO_AVG_WINRATE = round(avg_wr, 4)

        self.hero_avg_winrate_stats = {
            "avg_winrate": round(avg_wr, 4),
            "std": round(float(winrates.std()), 4),
            "min": round(float(winrates.min()), 2),
            "max": round(float(winrates.max()), 2),
            "hero_count": len(winrates),
        }
        logger.info(f"  全英雄平均胜率(step1_3): {avg_wr:.2f}% "
                    f"(范围: {winrates.min():.2f}%~{winrates.max():.2f}%, "
                    f"σ={winrates.std():.2f}%, N={len(winrates)})")

    def _calc_normalization_params(self):
        """
        v3.6: 基于英雄×符文(step1_2)真实数据计算归一化参数，并自动覆盖默认值
        
        归一化策略（三维度统一P2/P98线性映射）:
        - WR_FLOOR / WR_CEILING = 英雄×符文胜率的P2/P98
        - PR_FLOOR / PR_CEILING = 英雄×符文选率的P2/P98
        - PR_SATURATION 保留兼容但不再使用
        
        用P2/P98代替min/max，是因为英雄×符文数据中存在小样本造成的
        极端值（胜率0%或100%，选率0%），会导致归一化区间过大。
        用分位数更鲁棒。
        """
        import numpy as np
        from recommend import scoring_engine as se_module

        # 优先用英雄×符文(step1_2)数据，更精确
        if self.champion_augment_stats:
            wrs = np.array([s["win_rate"] for s in self.champion_augment_stats.values()])
            prs = np.array([s["show_rate"] for s in self.champion_augment_stats.values()])
            data_source = "Step1.2(英雄×符文)"
        elif self.augment_stats:
            wrs = np.array([s["win_rate"] for s in self.augment_stats.values()])
            prs = np.array([s["show_rate"] for s in self.augment_stats.values()])
            data_source = "Step1.1(全局符文)"
        else:
            logger.warning("  无胜率/选率数据，使用默认归一化参数")
            return

        # v3.6: 三维度统一P2/P98
        wr_floor_new = round(float(np.percentile(wrs, 2)), 2)
        wr_ceiling_new = round(float(np.percentile(wrs, 98)), 2)
        pr_floor_new = round(float(np.percentile(prs, 2)), 4)
        pr_ceiling_new = round(float(np.percentile(prs, 98)), 4)
        pr_sat_new = round(float(np.percentile(prs, 99)), 4)  # 保留兼容
        
        # 安全保护：确保区间有效
        if wr_ceiling_new <= wr_floor_new:
            wr_floor_new = round(float(wrs.min()), 2)
            wr_ceiling_new = round(float(wrs.max()), 2)
        if pr_ceiling_new <= pr_floor_new:
            pr_floor_new = round(float(prs.min()), 4)
            pr_ceiling_new = round(float(prs.max()), 4)
        if pr_sat_new <= 0:
            pr_sat_new = round(float(prs.max()), 4)

        # 记录旧值
        old_wr_floor = se_module.WR_FLOOR
        old_wr_ceiling = se_module.WR_CEILING
        old_pr_sat = se_module.PR_SATURATION

        # 自动覆盖默认值
        se_module.WR_FLOOR = wr_floor_new
        se_module.WR_CEILING = wr_ceiling_new
        se_module.PR_FLOOR = pr_floor_new
        se_module.PR_CEILING = pr_ceiling_new
        se_module.PR_SATURATION = pr_sat_new  # 保留兼容

        self.normalization_stats = {
            "data_source": data_source,
            "method": "P2/P98分位数(三维度统一鲁棒归一化)",
            "wr_data": {
                "min": round(float(wrs.min()), 2),
                "max": round(float(wrs.max()), 2),
                "mean": round(float(wrs.mean()), 2),
                "P2": round(float(np.percentile(wrs, 2)), 2),
                "P5": round(float(np.percentile(wrs, 5)), 2),
                "P50": round(float(np.median(wrs)), 2),
                "P95": round(float(np.percentile(wrs, 95)), 2),
                "P98": round(float(np.percentile(wrs, 98)), 2),
            },
            "pr_data": {
                "min": round(float(prs.min()), 4),
                "max": round(float(prs.max()), 4),
                "mean": round(float(prs.mean()), 4),
                "P2": round(float(np.percentile(prs, 2)), 4),
                "P50": round(float(np.median(prs)), 4),
                "P90": round(float(np.percentile(prs, 90)), 4),
                "P95": round(float(np.percentile(prs, 95)), 4),
                "P98": round(float(np.percentile(prs, 98)), 4),
            },
            "applied": {
                "WR_FLOOR": wr_floor_new,
                "WR_CEILING": wr_ceiling_new,
                "PR_FLOOR": pr_floor_new,
                "PR_CEILING": pr_ceiling_new,
                "PR_SATURATION": pr_sat_new,
            },
            "previous": {
                "WR_FLOOR": old_wr_floor,
                "WR_CEILING": old_wr_ceiling,
                "PR_SATURATION": old_pr_sat,
            },
        }
        logger.info(f"  [v3.6] 归一化参数已自动覆盖(基于{data_source}):")
        logger.info(f"    胜率归一化: [{wr_floor_new}%, {wr_ceiling_new}%] "
                    f"(旧: [{old_wr_floor}%, {old_wr_ceiling}%])")
        logger.info(f"    选率归一化: [{pr_floor_new}%, {pr_ceiling_new}%] "
                    f"(旧: 饱和点{old_pr_sat}%)")
        logger.info(f"    数据分布: 胜率[{wrs.min():.2f}%~{wrs.max():.2f}%], "
                    f"选率[{prs.min():.4f}%~{prs.max():.4f}%], "
                    f"N={len(wrs)}条")

        # v3.8: 归一化参数更新后，自动根据新区间反推权重
        se_module.recalc_weights()

    def _calc_ugc_clip_floor(self):
        """
        计算UGC评分的统计量，用于：
        1. 分位数截断（替代3σ法，不依赖正态假设）
        2. 全局均值（用于贝叶斯收缩）
        3. v3.6: P2/P98归一化参数（UGC_FLOOR/UGC_CEILING）
        """
        import numpy as np
        from recommend import scoring_engine as se_module

        # 收集所有有效的UGC评分 (> 0) 及样本数
        valid_scores = []
        valid_counts = []
        for name, data in self.ugc_comments.items():
            s = data.get("score", 0)
            c = data.get("score_count", 0)
            if s and s > 0:
                valid_scores.append(s)
                valid_counts.append(c if c else 0)
        # 也从augment_info中补充
        for name, info in self.augment_info.items():
            s = info.get("ugc_score", 0)
            c = info.get("ugc_count", 0)
            if s and s > 0 and name not in self.ugc_comments:
                valid_scores.append(s)
                valid_counts.append(c if c else 0)

        if len(valid_scores) < 10:
            logger.warning("  UGC有效样本不足10个，跳过截断计算")
            return

        scores = np.array(valid_scores)
        counts = np.array(valid_counts)
        mean = float(scores.mean())
        std = float(scores.std())
        
        # 1. 分位数截断
        pctl = se_module.UGC_CLIP_PERCENTILE
        clip_floor = float(np.percentile(scores, pctl))
        se_module.UGC_CLIP_FLOOR = round(clip_floor, 3)
        
        # 2. 全局均值（用于贝叶斯收缩）
        se_module.UGC_GLOBAL_MEAN = round(mean, 3)
        
        # 3. v3.6: 计算UGC的P2/P98归一化参数
        # 注意: 这里用原始分数（未经贝叶斯收缩），因为收缩是在归一化函数内部做的
        # 但收缩后的分数范围更集中，P2/P98更紧凑 → 区分度更好
        # 先模拟贝叶斯收缩后的分数分布来确定归一化区间
        prior_w = se_module.UGC_BAYESIAN_PRIOR_WEIGHT
        shrunk_scores = []
        for s, c in zip(valid_scores, valid_counts):
            if c > 0 and prior_w > 0:
                shrunk = (c * s + prior_w * mean) / (c + prior_w)
            else:
                shrunk = s
            shrunk_scores.append(shrunk)
        shrunk_arr = np.array(shrunk_scores)
        
        ugc_floor_new = round(float(np.percentile(shrunk_arr, 2)), 3)
        ugc_ceiling_new = round(float(np.percentile(shrunk_arr, 98)), 3)
        
        # 安全保护
        if ugc_ceiling_new <= ugc_floor_new:
            ugc_floor_new = round(float(shrunk_arr.min()), 3)
            ugc_ceiling_new = round(float(shrunk_arr.max()), 3)
        
        se_module.UGC_FLOOR = ugc_floor_new
        se_module.UGC_CEILING = ugc_ceiling_new

        # 统计截断影响
        clipped_count = int((scores < clip_floor).sum())
        
        # 统计贝叶斯收缩影响
        prior_w = se_module.UGC_BAYESIAN_PRIOR_WEIGHT
        low_sample_count = int((counts < prior_w).sum())
        
        self.ugc_clip_stats = {
            "mean": round(mean, 3),
            "std": round(std, 3),
            "clip_percentile": pctl,
            "clip_floor": round(clip_floor, 3),
            "total_valid": len(valid_scores),
            "clipped_count": clipped_count,
            "bayesian_prior_weight": prior_w,
            "low_sample_count": low_sample_count,
            "sample_count_stats": {
                "min": int(counts.min()),
                "max": int(counts.max()),
                "median": int(np.median(counts)),
                "below_prior": low_sample_count,
            },
        }
        logger.info(f"  UGC截断: 均值={mean:.3f}, P{pctl}={clip_floor:.3f}, "
                    f"被截断={clipped_count}/{len(valid_scores)}")
        logger.info(f"  UGC贝叶斯收缩: 先验权重={prior_w}, "
                    f"低样本(样本<{prior_w})={low_sample_count}/{len(valid_scores)}, "
                    f"全局均值={mean:.3f}")

    def _load_augment_id_map(self):
        """
        加载符文ID映射（augment_id_map.json）
        用于将中文名转换为CSV中使用的数字ID（带.0后缀）
        """
        map_path = os.path.join(RAW_DIR, "augment_id_map.json")
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for aid, name in raw.items():
                self.augment_id_map[str(aid)] = name
                self.augment_name_to_id[name] = str(aid)
            logger.info(f"  符文ID映射: {len(self.augment_id_map)} 条")
        else:
            logger.warning(f"  符文ID映射文件不存在: {map_path}")

    def _aug_name_to_stat_key(self, augment_name):
        """
        将中文符文名转为augment_stats中的key格式（如 '1342.0'）
        CSV中 player_augment 列读入后被 str() 转为 '1342.0' 格式
        """
        if augment_name in self.augment_name_to_id:
            aid = self.augment_name_to_id[augment_name]
            # augment_stats的key是 str(row["player_augment"]) → pandas读int为float → "1342.0"
            # 尝试两种格式
            key_with_dot = f"{aid}.0"
            if key_with_dot in self.augment_stats:
                return key_with_dot
            if aid in self.augment_stats:
                return aid
        return None

    def _champion_aug_stat_key(self, champion_id, augment_name):
        """
        构建champion_augment_stats的key: (champion_id_str, augment_id_str)
        CSV中两列都是数字，pandas读入后 str() 转为 '56.0', '1038.0' 格式
        """
        # champion_id可能是 '56' 或 '56.0'
        cid = str(champion_id)
        cid_dot = f"{cid}.0" if "." not in cid else cid

        aug_id = self.augment_name_to_id.get(augment_name)
        if not aug_id:
            return None
        aug_id_dot = f"{aug_id}.0"

        # 尝试不同组合
        for c in [cid_dot, cid]:
            for a in [aug_id_dot, aug_id]:
                key = (c, a)
                if key in self.champion_augment_stats:
                    return key
        return None

    def _load_champion_id_map(self):
        """加载英雄ID映射"""
        map_path = os.path.join(RAW_DIR, "champion_id_map.json")
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # 建立双向映射
            for cid, name in raw.items():
                self.champion_id_map[str(cid)] = name
                self.champion_name_map[name] = str(cid)
            logger.info(f"  英雄ID映射: {len(self.champion_id_map)} 条")
        else:
            logger.warning(f"  英雄ID映射文件不存在: {map_path}")

        # 加载英雄别名（称号/俗称 → 标准名）
        self._build_hero_alias_map()

    def _build_hero_alias_map(self):
        """
        建立英雄别名映射
        黑科技Excel中用的是称号名（如"复仇焰魂"），champion_id_map用的是标准名（如"布兰德"）
        用户可能说俗称（如"火男"）
        需要统一映射
        """
        # 从arammayhem_combos.json获取称号→标准名映射
        aram_path = os.path.join(RAW_DIR, "arammayhem_combos.json")
        if os.path.exists(aram_path):
            with open(aram_path, "r", encoding="utf-8") as f:
                aram_data = json.load(f)
            # arammayhem_combos.json格式: [{"champion": "布兰德", "title": "复仇焰魂", ...}, ...]
            for item in aram_data:
                if isinstance(item, dict):
                    name = item.get("champion", "")
                    title = item.get("title", "")
                    if name and title and title != name:
                        self.hero_alias_map[title] = name
                        # 标准名也映射到自己
                        self.hero_alias_map[name] = name

        # 手动添加常见俗称
        COMMON_ALIASES = {
            "火男": "布兰德", "大头": "黑默丁格", "蒙多": "蒙多医生",
            "老鼠": "图奇", "猴子": "孙悟空", "蛤蟆": "塔姆·肯奇",
            "锤石": "锤石", "机器人": "布里茨", "小法": "维迦",
            "石头人": "墨菲特", "狗头": "内瑟斯", "瞎子": "李青",
            "剑圣": "易", "提莫": "提莫", "亚索": "亚索",
            "男刀": "泰隆", "女枪": "厄运小姐", "女警": "凯特琳",
            "EZ": "伊泽瑞尔", "ez": "伊泽瑞尔", "VN": "薇恩", "vn": "薇恩",
        }
        self.hero_alias_map.update(COMMON_ALIASES)

        # 所有标准名也映射到自己
        for name in self.champion_name_map:
            self.hero_alias_map[name] = name

        logger.info(f"  英雄别名映射: {len(self.hero_alias_map)} 条")

    def _build_bt_hero_alias(self, bt_hero_names):
        """
        从黑科技Excel的称号名自动映射到champion_id_map的标准名
        策略：
        1. 优先用hextech_champion_combos.json的champion_title→champion_name映射（172个英雄，100%覆盖）
        2. 其次尝试arammayhem_combos.json的champion_name字段（也是称号名）
        3. 最后用模糊匹配
        """
        # 方法1：从hextech_champion_combos.json获取 title(称号) → name(标准名) 映射
        title_to_name = {}
        combos_path = os.path.join(RAW_DIR, "hextech_champion_combos.json")
        if os.path.exists(combos_path):
            with open(combos_path, "r", encoding="utf-8") as f:
                combos_data = json.load(f)
            for item in combos_data:
                if isinstance(item, dict):
                    title = item.get("champion_title", "")
                    name = item.get("champion_name", "")
                    if title and name:
                        title_to_name[title] = name
            logger.info(f"  hextech_champion_combos称号映射: {len(title_to_name)}条")

        mapped = 0
        unmapped = []
        for bt_name in bt_hero_names:
            # 已经在hero_alias_map中的跳过
            if bt_name in self.hero_alias_map:
                continue
            # 在champion_name_map中（已经是标准名）
            if bt_name in self.champion_name_map:
                self.hero_alias_map[bt_name] = bt_name
                continue
            # hextech_champion_combos的title→name映射（最准确）
            if bt_name in title_to_name:
                self.hero_alias_map[bt_name] = title_to_name[bt_name]
                mapped += 1
                continue
            # 尝试反向：champion_id_map的值（标准名）中，看有没有跟bt_name相关的
            found = False
            for std_name in self.champion_name_map:
                if bt_name in std_name or std_name in bt_name:
                    self.hero_alias_map[bt_name] = std_name
                    mapped += 1
                    found = True
                    break
            if not found:
                unmapped.append(bt_name)

        if unmapped:
            logger.warning(f"  黑科技英雄未映射({len(unmapped)}个): {unmapped[:20]}")

        logger.info(f"  黑科技称号→标准名映射: 新增{mapped}条, 未映射{len(unmapped)}条")

    def resolve_hero_name(self, name):
        """将任何形式的英雄名（称号/俗称/标准名）统一转为标准名"""
        # 直接匹配
        if name in self.champion_name_map:
            return name
        # 通过别名映射
        if name in self.hero_alias_map:
            return self.hero_alias_map[name]
        # 模糊匹配（简单包含）
        for alias, std_name in self.hero_alias_map.items():
            if name in alias or alias in name:
                return std_name
        return name  # 没找到就返回原名

    def _load_plain_desc_and_fun_facts(self):
        """从ai_content_generator.py提取人话描述和冷知识"""
        # 直接从Excel知识库的'符文冷知识'sheet加载
        excel_path = os.path.join(OUTPUT_DIR, "海克斯大乱斗符文知识库.xlsx")
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path, sheet_name="符文冷知识")
                for _, row in df.iterrows():
                    name = str(row.get("符文名称", ""))
                    content = str(row.get("冷知识内容", ""))
                    if name and content and content != "nan":
                        if name not in self.fun_facts:
                            self.fun_facts[name] = []
                        self.fun_facts[name].append(content)
                logger.info(f"  符文冷知识: {len(self.fun_facts)} 个符文有冷知识")
            except Exception as e:
                logger.warning(f"  加载冷知识失败: {e}")

        # 人话描述优先从augment_info中获取（已在_load_augment_info中加载）
        for name, info in self.augment_info.items():
            desc = info.get("plain_desc", "")
            if desc and desc != "nan":
                self.plain_desc[name] = desc
        logger.info(f"  符文人话描述: {len(self.plain_desc)} 条")

    # ==================== 便捷查询方法 ====================

    def get_augment_winrate(self, augment_name, champion_id=None):
        """
        获取符文胜率（优先英雄×符文，回退全局）
        
        注意：augment_name 是中文名，但 augment_stats / champion_augment_stats
        中的 key 都是数字ID字符串（如 '1342.0'），需要通过 augment_id_map 转换

        返回: win_rate (百分比，如 62.5)
        """
        # 优先：英雄×符文（CSV数据，最精确）
        if champion_id:
            ca_key = self._champion_aug_stat_key(champion_id, augment_name)
            if ca_key and ca_key in self.champion_augment_stats:
                return self.champion_augment_stats[ca_key]["win_rate"]

        # 其次：全局符文统计（CSV数据）
        stat_key = self._aug_name_to_stat_key(augment_name)
        if stat_key and stat_key in self.augment_stats:
            return self.augment_stats[stat_key]["win_rate"]

        # 最终回退：Excel知识库
        info = self.augment_info.get(augment_name, {})
        return info.get("win_rate", 50.0)

    def get_augment_pickrate(self, augment_name, champion_id=None):
        """
        获取符文选取率
        
        注意：augment_name 是中文名，但 augment_stats / champion_augment_stats
        中的 key 都是数字ID字符串（如 '1342.0'），需要通过 augment_id_map 转换
        """
        # 优先：英雄×符文（CSV数据，最精确）
        if champion_id:
            ca_key = self._champion_aug_stat_key(champion_id, augment_name)
            if ca_key and ca_key in self.champion_augment_stats:
                return self.champion_augment_stats[ca_key]["show_rate"]

        # 其次：全局符文统计（CSV数据）
        stat_key = self._aug_name_to_stat_key(augment_name)
        if stat_key and stat_key in self.augment_stats:
            return self.augment_stats[stat_key]["show_rate"]

        # 最终回退：Excel知识库
        info = self.augment_info.get(augment_name, {})
        return info.get("pick_rate", 0.5)

    def get_ugc_score(self, augment_name):
        """获取UGC评分 (0-10)"""
        if augment_name in self.ugc_comments:
            return self.ugc_comments[augment_name].get("score", 0)
        info = self.augment_info.get(augment_name, {})
        return info.get("ugc_score", 0)

    def get_ugc_sample_count(self, augment_name):
        """获取UGC评分的样本数"""
        if augment_name in self.ugc_comments:
            return self.ugc_comments[augment_name].get("score_count", 0)
        info = self.augment_info.get(augment_name, {})
        return info.get("ugc_count", 0)

    def get_ugc_hot_comment(self, augment_name, max_count=1):
        """获取UGC热评"""
        if augment_name in self.ugc_comments:
            comments = self.ugc_comments[augment_name].get("hot_comments", [])
            result = []
            for c in comments[:max_count]:
                if isinstance(c, dict):
                    result.append(c.get("content", str(c)))
                else:
                    result.append(str(c))
            return result
        return []

    def get_pair_winrate(self, aug_a, aug_b, champion_id=None):
        """获取符文对组合胜率（支持中文名和数字ID两种格式）"""
        # 将中文名转为数字ID（pair_stats的key是数字ID带.0后缀）
        aid_a = self.augment_name_to_id.get(aug_a, aug_a)
        aid_b = self.augment_name_to_id.get(aug_b, aug_b)

        # champion_pair_stats优先
        if champion_id:
            cid = str(champion_id)
            cid_dot = f"{cid}.0" if "." not in cid else cid
            for c in [cid_dot, cid]:
                for a_fmt in [f"{aid_a}.0", aid_a, aug_a]:
                    for b_fmt in [f"{aid_b}.0", aid_b, aug_b]:
                        pair_sorted = tuple(sorted([a_fmt, b_fmt]))
                        key = (c, pair_sorted[0], pair_sorted[1])
                        if key in self.champion_pair_stats:
                            return self.champion_pair_stats[key]["win_rate"]

        # 全局pair_stats
        for a_fmt in [f"{aid_a}.0", aid_a, aug_a]:
            for b_fmt in [f"{aid_b}.0", aid_b, aug_b]:
                pair_sorted = tuple(sorted([a_fmt, b_fmt]))
                if pair_sorted in self.pair_stats:
                    return self.pair_stats[pair_sorted]["win_rate"]
        return None

    def get_champion_name(self, champion_id):
        """英雄ID转名称"""
        return self.champion_id_map.get(str(champion_id), str(champion_id))

    def get_champion_id(self, champion_name):
        """英雄名称转ID（支持别名/称号/俗称）"""
        # 先尝试直接查找
        if champion_name in self.champion_name_map:
            return self.champion_name_map[champion_name]
        # 通过别名映射
        std_name = self.resolve_hero_name(champion_name)
        if std_name in self.champion_name_map:
            return self.champion_name_map[std_name]
        return champion_name

    def get_synergy_for_augment(self, augment_name):
        """查询符文所属的官方套装"""
        results = []
        for syn in self.synergies:
            if augment_name in syn.get("augments", []):
                results.append(syn)
        return results
