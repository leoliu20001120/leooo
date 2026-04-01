# -*- coding: utf-8 -*-
"""
海克斯大乱斗符文知识库 - 主入口
串联爬取 -> 清洗合并 -> AI内容生成 -> 推荐计算 -> Excel输出
"""
import argparse
import logging
import os
import sys
import time

import config
from crawlers.hextech_crawler import HextechCrawler
from crawlers.zhangmeng_crawler import ZhangmengCrawler
from crawlers.bilibili_crawler import BilibiliCrawler
from crawlers.arammayhem_crawler import ARAMMayhemCrawler
from processors.data_merger import DataMerger
from processors.ai_content_generator import AIContentGenerator
from processors.recommendation_calculator import RecommendationCalculator
from generators.excel_generator import ExcelGenerator


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
    )


def run_crawlers(skip_crawl=False):
    """运行所有爬虫"""
    if skip_crawl:
        logging.info("跳过爬取阶段，使用已有数据...")
        return

    logging.info("=" * 60)
    logging.info("阶段1/4: 数据爬取")
    logging.info("=" * 60)

    # hextech.dtodo.cn
    try:
        hextech = HextechCrawler()
        hextech.crawl()
    except Exception as e:
        logging.error(f"hextech爬取失败: {e}")

    # 掌上英雄联盟
    try:
        zhangmeng = ZhangmengCrawler()
        zhangmeng.crawl()
    except Exception as e:
        logging.error(f"掌盟爬取失败: {e}")

    # B站
    try:
        bilibili = BilibiliCrawler()
        bilibili.crawl()
    except Exception as e:
        logging.error(f"B站爬取失败: {e}")

    # ARAM Mayhem
    try:
        arammayhem = ARAMMayhemCrawler()
        arammayhem.crawl()
    except Exception as e:
        logging.error(f"ARAM Mayhem爬取失败: {e}")


def run_merge():
    """合并数据"""
    logging.info("=" * 60)
    logging.info("阶段2/4: 数据合并")
    logging.info("=" * 60)

    merger = DataMerger()
    merged = merger.merge()
    return merged


def run_ai_generate(merged_data):
    """AI内容生成"""
    logging.info("=" * 60)
    logging.info("阶段3/4: AI内容生成 + 推荐计算")
    logging.info("=" * 60)

    # AI内容生成
    generator = AIContentGenerator()
    enriched = generator.generate(merged_data)

    # 推荐指数计算
    calculator = RecommendationCalculator()
    final_data = calculator.calculate(enriched)

    return final_data


def run_excel_output(final_data, output_path=None):
    """生成Excel"""
    logging.info("=" * 60)
    logging.info("阶段4/4: Excel知识库生成")
    logging.info("=" * 60)

    excel_gen = ExcelGenerator()
    path = excel_gen.generate(final_data, output_path)
    return path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="海克斯大乱斗符文知识库生成工具")
    parser.add_argument("--skip-crawl", action="store_true", help="跳过爬取阶段，使用已有数据")
    parser.add_argument("--output", type=str, default=None, help="指定输出Excel路径")
    parser.add_argument("--only-crawl", action="store_true", help="只运行爬虫，不生成Excel")
    args = parser.parse_args()

    setup_logging()

    start_time = time.time()

    logging.info("=" * 60)
    logging.info("  海克斯大乱斗符文知识库 - 生成工具")
    logging.info("=" * 60)

    # 阶段1: 爬取
    run_crawlers(skip_crawl=args.skip_crawl)

    if args.only_crawl:
        logging.info("仅爬取模式，跳过后续处理")
        return

    # 阶段2: 合并
    merged = run_merge()

    # 阶段3: AI生成 + 推荐计算
    final_data = run_ai_generate(merged)

    # 阶段4: 生成Excel
    output_path = run_excel_output(final_data, args.output)

    elapsed = time.time() - start_time
    logging.info("=" * 60)
    logging.info(f"  全部完成！耗时 {elapsed:.1f} 秒")
    logging.info(f"  知识库路径: {output_path}")
    logging.info(f"  符文总数: {final_data.get('total', 0)}")
    logging.info(f"  组合数: {len(final_data.get('combos', []))}")
    logging.info(f"  套装数: {len(final_data.get('sets', []))}")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
