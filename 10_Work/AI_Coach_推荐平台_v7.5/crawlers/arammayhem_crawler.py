# -*- coding: utf-8 -*-
"""
ARAM Mayhem 英雄符文搭配爬虫
数据源: https://arammayhem.com/zh-cn/combo/
- HTML解析: 英雄名、符文名、评级、标签、中文描述（SSR直出）
- API接口: 点赞/点踩/分数数据
"""
import json
import logging
import os
import re
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from crawlers.base_crawler import BaseCrawler

logger = logging.getLogger("ARAMMayhemCrawler")


class ARAMMayhemCrawler(BaseCrawler):
    """ARAM Mayhem 英雄符文搭配爬虫"""

    COMBO_URL = "https://arammayhem.com/zh-cn/combo/"
    VOTE_API_URL = "https://arammayhem.com/api/combos/feed"

    # 标签英文→中文映射
    TAG_MAP = {
        "god": "神级",
        "strong": "强力",
        "entertainment": "娱乐",
        "trap": "陷阱",
        "blackTech": "黑科技",
        "fun": "娱乐",
        "bug": "黑科技",
        "niche": "小众",
    }

    # 评级中文映射（用于badge文本解析）
    TIER_VALUES = {"S", "A", "B", "C"}

    # 标签中文映射（用于badge文本解析）
    TAG_CN_MAP = {
        "神级": "神级",
        "强力": "强力",
        "娱乐": "娱乐",
        "陷阱": "陷阱",
        "黑科技": "黑科技",
        "小众": "小众",
    }

    def __init__(self):
        super().__init__("ARAMMayhemCrawler")

    def crawl(self):
        """主爬取方法"""
        logger.info("开始爬取 ARAM Mayhem 英雄符文搭配...")

        # Step 1: 获取HTML页面
        html = self._fetch_combo_page()
        if not html:
            logger.error("获取组合页面失败")
            return []

        # Step 2: 解析HTML获取英雄+符文+评级+标签+描述
        combos = self._parse_html(html)
        logger.info(f"HTML解析完成: {len(combos)} 个英雄符文搭配")

        # Step 3: 通过API获取投票数据
        vote_data = self._fetch_vote_data()
        logger.info(f"API获取投票数据: {len(vote_data)} 条")

        # Step 4: 合并投票数据到组合
        self._merge_vote_data(combos, vote_data)

        # Step 5: 按英雄分组统计
        champions = {}
        for combo in combos:
            champ = combo["champion_name"]
            if champ not in champions:
                champions[champ] = []
            champions[champ].append(combo)

        logger.info(f"共 {len(champions)} 个英雄, {len(combos)} 个组合")

        # Step 6: 保存数据
        save_path = config.ARAMMAYHEM_RAW_FILE
        self.save_json(combos, save_path)

        return combos

    def _fetch_combo_page(self):
        """获取组合页面HTML"""
        headers = {
            "User-Agent": config.DEFAULT_HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = self.get(self.COMBO_URL, headers=headers, timeout=30)
        if resp:
            # 服务器返回的Content-Type没有charset，requests默认用ISO-8859-1
            # 实际编码是UTF-8（HTML meta charset="UTF-8"），需要手动解码
            return resp.content.decode("utf-8")
        return None

    def _parse_html(self, html):
        """解析HTML中的combo-card数据"""
        soup = BeautifulSoup(html, "html.parser")
        combos = []

        # 找到所有combo-card
        cards = soup.find_all("article", class_=lambda c: c and "combo-card" in c)
        logger.info(f"找到 {len(cards)} 个combo-card")

        # 当前英雄上下文（通过遍历之前的兄弟元素获取）
        current_champion = ""
        current_combo_count = 0

        for card in cards:
            combo = self._parse_card(card)
            if combo:
                combos.append(combo)

        return combos

    def _parse_card(self, card):
        """解析单个combo-card"""
        try:
            # 英雄名 (data-champion)
            champion_name = card.get("data-champion", "").strip()
            # 符文名 (data-augment)
            augment_name = card.get("data-augment", "").strip()
            # 评级 (data-tier)
            tier = card.get("data-tier", "").strip()
            # combo引用 (data-combo-ref)
            combo_ref = card.get("data-combo-ref", "").strip()

            if not champion_name or not augment_name:
                return None

            # 解析badges获取标签
            tags = []
            is_curated = False
            badges = card.find_all("span", attrs={"data-slot": "badge"})
            for badge in badges:
                text = badge.get_text(strip=True)
                if text == "Curated":
                    is_curated = True
                    continue
                if text in self.TIER_VALUES:
                    continue  # 跳过评级badge
                if text in self.TAG_CN_MAP:
                    tags.append(self.TAG_CN_MAP[text])
                elif text:
                    # 尝试英文标签
                    cn = self.TAG_MAP.get(text.lower(), "")
                    if cn:
                        tags.append(cn)
                    else:
                        tags.append(text)

            # 解析描述文本
            description = ""
            # 找描述段落 - 描述通常在badges之后的p标签或文本段中
            desc_p = card.find("p", class_=lambda c: c and "text-sm" in c)
            if desc_p:
                description = desc_p.get_text(strip=True)
            else:
                # 备选：找所有p标签
                for p in card.find_all("p"):
                    text = p.get_text(strip=True)
                    if len(text) > 10 and text != champion_name and text != augment_name:
                        description = text
                        break

            if not description:
                # 更深层次的搜索：在flex-1容器中找文本
                flex_div = card.find("div", class_=lambda c: c and "flex-1" in c and "min-w-0" in c)
                if flex_div:
                    # 找a标签后面的文本
                    for child in flex_div.children:
                        if hasattr(child, 'get_text'):
                            text = child.get_text(strip=True)
                            # 排除符文名和badges
                            if len(text) > 20 and augment_name not in text[:10]:
                                description = text
                                break

            return {
                "champion_name": champion_name,
                "augment_name": augment_name,
                "tier": tier,
                "tags": tags,
                "description": description,
                "combo_ref": combo_ref,
                "is_curated": is_curated,
                "upvotes": 0,
                "downvotes": 0,
                "score": 0,
            }

        except Exception as e:
            logger.warning(f"解析combo-card失败: {e}")
            return None

    def _fetch_vote_data(self):
        """通过API获取投票数据"""
        headers = {
            "User-Agent": config.DEFAULT_HEADERS["User-Agent"],
            "Accept": "application/json",
        }
        # API最多返回约240条，但实际可能更少
        params = {"scope": "all", "limit": "500"}
        resp = self.get(self.VOTE_API_URL, headers=headers, params=params, timeout=15)
        if not resp:
            return {}

        try:
            data = resp.json()
            if data.get("success") and "items" in data:
                vote_map = {}
                for item in data["items"]:
                    ref = item.get("comboRef", "")
                    vote_map[ref] = {
                        "upvotes": item.get("upvotes", 0),
                        "downvotes": item.get("downvotes", 0),
                        "score": item.get("score", 0),
                        # API中也有英文描述和types，但我们优先用HTML中文数据
                        "api_types": item.get("types", []),
                    }
                return vote_map
        except Exception as e:
            logger.warning(f"解析投票API失败: {e}")

        return {}

    def _merge_vote_data(self, combos, vote_data):
        """将API的投票数据合并到HTML解析结果"""
        matched = 0
        for combo in combos:
            ref = combo.get("combo_ref", "")
            if ref in vote_data:
                vote = vote_data[ref]
                combo["upvotes"] = vote["upvotes"]
                combo["downvotes"] = vote["downvotes"]
                combo["score"] = vote["score"]
                # 如果HTML没解析到标签，用API的types补充
                if not combo["tags"] and vote.get("api_types"):
                    combo["tags"] = [
                        self.TAG_MAP.get(t, t) for t in vote["api_types"]
                    ]
                matched += 1

        logger.info(f"投票数据匹配: {matched}/{len(combos)} 个组合")


def main():
    """独立运行"""
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)
    crawler = ARAMMayhemCrawler()
    combos = crawler.crawl()

    # 打印统计
    champions = {}
    for c in combos:
        name = c["champion_name"]
        if name not in champions:
            champions[name] = 0
        champions[name] += 1

    print(f"\n=== 爬取完成 ===")
    print(f"英雄数: {len(champions)}")
    print(f"组合数: {len(combos)}")
    print(f"\n前10个英雄:")
    for name, count in sorted(champions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {name}: {count} 个组合")

    # 打印几个示例
    print(f"\n=== 示例数据 ===")
    for combo in combos[:5]:
        print(f"\n英雄: {combo['champion_name']}")
        print(f"符文: {combo['augment_name']}")
        print(f"评级: {combo['tier']}")
        print(f"标签: {', '.join(combo['tags'])}")
        print(f"描述: {combo['description'][:80]}...")
        print(f"点赞: {combo['upvotes']} | 点踩: {combo['downvotes']} | 分数: {combo['score']}")


if __name__ == "__main__":
    main()
