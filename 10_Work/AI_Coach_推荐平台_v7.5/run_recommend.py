# -*- coding: utf-8 -*-
"""
符文推荐系统 - 运行入口

用法:
    python run_recommend.py                    # 默认火男模拟测试
    python run_recommend.py --hero 亚索         # 指定英雄
    python run_recommend.py --export           # 导出UI数据JSON
    python run_recommend.py --export-table     # 导出英雄×符文推荐总表CSV
"""
import argparse
import io
import json
import logging
import sys

# 修复Windows终端编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from recommend import RecommendSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("RunRecommend")


def print_card(card, index):
    """漂亮地打印一张符文卡片"""
    print(f"\n  {'─'*50}")
    print(f"  卡片 {index+1}: {card['logo']} {card['augment']}  ({card['augment_level']})")
    print(f"  {'─'*50}")
    print(f"  得分: {card['score']}  |  {card['logo_text']}  |  Tier: {card['tier']}")
    print(f"  标签: {card['tag_line']}")
    if card.get("description"):
        print(f"  描述: {card['description']}")
    if card.get("ugc_comment"):
        print(f"  热评: 「{card['ugc_comment']}」")
    if card.get("fun_fact"):
        print(f"  冷知识: {card['fun_fact']}")
    if card.get("combo_hint"):
        print(f"  💡 {card['combo_hint']}")
    if card.get("synergy_hint"):
        print(f"  🔗 套装: {card['synergy_hint']}")

    d = card["detail"]
    print(f"  ──── 评分明细 ────")
    print(f"  胜率: {d['win_rate_raw']:.1f}% → {d['win_rate_norm']:.0f}分 × {d['weights']['W_winrate']}")
    print(f"  选率: {d['pick_rate_raw']:.2f}% → {d['pick_rate_norm']:.0f}分 × {d['weights']['W_pickrate']}")
    print(f"  UGC:  {d['ugc_score_raw']:.1f} → {d['ugc_norm']:.0f}分 × {d['weights']['W_ugc']}")
    print(f"  基础分={d['base_score']:.1f} × 系数{d['streak_multiplier']:.2f} + 黑科技{d['blacktech_bonus']} = {d['final_score']:.1f}")


def simulate_game(system, hero_name, streak=0, seed=42):
    """模拟一局完整游戏"""
    print(f"\n{'='*60}")
    print(f"  🎮 模拟对局: {hero_name}  |  连胜/败: {streak}  |  seed={seed}")
    print(f"{'='*60}")

    stages = system.simulate_full_game(hero_name, streak=streak, seed=seed)

    stage_levels = ["白银", "黄金", "黄金", "棱彩"]
    for i, result in enumerate(stages):
        print(f"\n{'━'*60}")
        print(f"  📌 第{i+1}阶段 ({stage_levels[i]})  |  模式: {result['weight_profile']}")
        print(f"  已选符文: {result['selected_augments'] or '（无）'}")
        print(f"{'━'*60}")

        for j, card in enumerate(result["cards"]):
            is_chosen = card["augment"] == result.get("chosen", "")
            if is_chosen:
                print(f"\n  ★★★ 本阶段选择 ★★★")
            print_card(card, j)

    print(f"\n{'='*60}")
    print(f"  ✅ 最终符文: {[s['chosen'] for s in stages]}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="符文AI Coach推荐系统")
    parser.add_argument("--hero", type=str, default="火男", help="英雄名称")
    parser.add_argument("--streak", type=int, default=0, help="连胜(正)/连败(负)")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--export", action="store_true", help="导出UI数据JSON")
    parser.add_argument("--export-table", action="store_true", help="导出英雄×符文推荐总表")
    parser.add_argument("--heroes", type=str, nargs="+",
                        help="模拟多个英雄，如: --heroes 火男 亚索 蒙多医生")
    args = parser.parse_args()

    system = RecommendSystem()
    system.load_data()

    if args.export:
        path = system.export_json_for_ui()
        print(f"\n✅ UI数据已导出: {path}")
        return

    if args.export_table:
        path = system.export_hero_augment_table()
        print(f"\n✅ 推荐总表已导出: {path}")
        return

    heroes = args.heroes or [args.hero]
    for hero in heroes:
        simulate_game(system, hero, streak=args.streak, seed=args.seed)

        # 也测试连胜和连败
        if len(heroes) == 1:
            print(f"\n\n{'▶'*30} 连胜模式对比 {'◀'*30}")
            simulate_game(system, hero, streak=3, seed=args.seed)
            print(f"\n\n{'▶'*30} 连败模式对比 {'◀'*30}")
            simulate_game(system, hero, streak=-3, seed=args.seed)


if __name__ == "__main__":
    main()
