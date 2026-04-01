# -*- coding: utf-8 -*-
"""
掌上英雄联盟爬虫
采集符文基础信息（icon/等级/名字/描述/数值）和UGC数据（评分/评论/排行榜）

数据源（均为掌盟页面真正加载的官方CDN）：
1. kiwi_augments.json — 掌盟符文列表页加载，包含name_cn/desc/tooltip/icon/level/isNew
2. fighting_rune.js  — 掌盟乱斗符文数据，包含name/desc(带数值)/tooltip(带数值)/data_values/icon/rarity
3. UGC评论接口      — POST mlol.qt.qq.com/go/comment_svr/comment/list（已抓包确认）
"""
import json
import os
import re
import sys
import time

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from crawlers.base_crawler import BaseCrawler


class ZhangmengCrawler(BaseCrawler):
    """掌上英雄联盟符文数据爬虫"""

    # kiwi_augments.json 的等级映射
    KIWI_LEVEL_MAP = {
        "kSilver": "白银",
        "kGold": "黄金",
        "kPrismatic": "棱彩",
    }

    # fighting_rune.js 的稀有度映射
    FIGHTING_RARITY_MAP = {
        "0": "白银",
        "1": "黄金",
        "2": "棱彩",
        0: "白银",
        1: "黄金",
        2: "棱彩",
    }

    # 官方CDN数据源URL（Playwright浏览器自动化确认，掌盟页面真正加载的数据）
    KIWI_AUGMENTS_URL = "https://game.gtimg.cn/images/lol/act/img/js/kiwi/kiwi_augments.json"
    FIGHTING_RUNE_URL = "https://game.gtimg.cn/images/lol/act/img/js/fighting_rune/fighting_rune.js"

    def __init__(self):
        super().__init__("ZhangmengCrawler")

    def crawl(self):
        """主爬取流程"""
        self.logger.info("=" * 50)
        self.logger.info("开始爬取掌盟符文数据（官方CDN数据源）")
        self.logger.info("=" * 50)

        # 步骤1: 从kiwi_augments.json获取基础数据（掌盟页面主要数据源）
        kiwi_augments = self._crawl_kiwi_augments()

        # 步骤2: 从fighting_rune.js获取详细数据（带完整数值和data_values）
        fighting_augments = self._crawl_fighting_rune()

        # 步骤3: 合并两个数据源
        augments = self._merge_official_sources(kiwi_augments, fighting_augments)

        if not augments:
            self.logger.error("所有官方数据源获取失败！")
            return {"augments": [], "ugc": []}

        # 步骤4: 获取UGC数据（评分/评论）
        ugc_data = self._crawl_ugc_data(augments)

        # 保存基础数据
        self.save_json({
            "source": "掌上英雄联盟（官方CDN）",
            "data_urls": [self.KIWI_AUGMENTS_URL, self.FIGHTING_RUNE_URL],
            "total_augments": len(augments),
            "augments": augments,
        }, config.ZHANGMENG_RAW_FILE)

        # 保存UGC数据
        self.save_json({
            "source": "掌上英雄联盟-UGC",
            "ugc": ugc_data,
        }, config.ZHANGMENG_UGC_FILE)

        self.logger.info(f"掌盟数据爬取完成，共 {len(augments)} 个符文")
        return {"augments": augments, "ugc": ugc_data}

    def _crawl_kiwi_augments(self):
        """
        从kiwi_augments.json获取符文数据
        这是掌盟符文列表页（https://lol.qq.com/zmlolzonehmtest/page/gamedata/?tab=ldbuff）
        真正加载的数据源，通过Playwright浏览器自动化确认。
        
        字段：augmentID, name_en, name_cn, level, isPBE, isNew, desc, tooltip, large_Icon, small_Icon
        """
        self.logger.info(f"从kiwi_augments.json获取数据: {self.KIWI_AUGMENTS_URL}")
        data = self.get_json(self.KIWI_AUGMENTS_URL, headers=config.ZHANGMENG_HEADERS)

        if not data or not isinstance(data, list):
            self.logger.warning("kiwi_augments.json 获取失败或格式异常")
            return {}

        self.logger.info(f"kiwi_augments.json: 获取到 {len(data)} 条符文数据")

        augments = {}
        for item in data:
            name = item.get("name_cn", "").strip()
            if not name:
                continue

            augments[name] = {
                "augment_id": str(item.get("augmentID", "")),
                "name": name,
                "name_en": item.get("name_en", ""),
                "icon_url": item.get("large_Icon", ""),
                "icon_small": item.get("small_Icon", ""),
                "rarity": self.KIWI_LEVEL_MAP.get(item.get("level", ""), ""),
                "official_desc": self._clean_html(item.get("tooltip", "")),  # tooltip = 掌盟页面显示的简洁描述
                "official_desc_raw": item.get("desc", ""),  # desc = 带HTML模板的完整描述
                "is_new": bool(item.get("isNew", 0)),
                "is_pbe": bool(item.get("isPBE", 0)),
            }

        self.logger.info(f"kiwi数据解析完成: {len(augments)} 个符文 "
                         f"(白银:{sum(1 for a in augments.values() if a['rarity']=='白银')}, "
                         f"黄金:{sum(1 for a in augments.values() if a['rarity']=='黄金')}, "
                         f"棱彩:{sum(1 for a in augments.values() if a['rarity']=='棱彩')})")
        return augments

    def _crawl_fighting_rune(self):
        """
        从fighting_rune.js获取详细符文数据
        同样是掌盟页面加载的数据源，包含完整数值参数。
        
        字段：id, name, api_name, data_values, desc, icon_large, icon_small, rarity, tooltip
        """
        self.logger.info(f"从fighting_rune.js获取数据: {self.FIGHTING_RUNE_URL}")

        try:
            response = self.session.get(
                self.FIGHTING_RUNE_URL,
                headers=config.ZHANGMENG_HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )
            if response.status_code != 200:
                self.logger.warning(f"fighting_rune.js 返回 {response.status_code}")
                return {}

            text = response.text
            # 尝试直接解析JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # 可能是JSONP格式
                match = re.search(r'(\{.*\})', text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                else:
                    self.logger.warning("fighting_rune.js 无法解析")
                    return {}
        except Exception as e:
            self.logger.warning(f"fighting_rune.js 请求失败: {e}")
            return {}

        items = data.get("list", []) if isinstance(data, dict) else data
        self.logger.info(f"fighting_rune.js: 获取到 {len(items)} 条符文数据 "
                         f"(版本: {data.get('version', '?')}, 更新时间: {data.get('time', '?')})")

        augments = {}
        for item in items:
            name = item.get("name", "").strip()
            if not name:
                continue

            # 解析data_values字段
            data_values_str = item.get("data_values", "{}")
            try:
                data_values = json.loads(data_values_str) if isinstance(data_values_str, str) else data_values_str
            except json.JSONDecodeError:
                data_values = {}

            augments[name] = {
                "fighting_id": str(item.get("id", "")),
                "name": name,
                "api_name": item.get("api_name", ""),
                "icon_url": item.get("icon_large", ""),
                "icon_small": item.get("icon_small", ""),
                "rarity": self.FIGHTING_RARITY_MAP.get(item.get("rarity", ""), ""),
                "desc_with_values": self._clean_html(item.get("desc", "")),  # 带真实数值的描述
                "tooltip_with_values": self._clean_html(item.get("tooltip", "")),  # 带真实数值的tooltip
                "data_values": data_values,  # 原始数值参数
            }

        self.logger.info(f"fighting_rune数据解析完成: {len(augments)} 个符文")
        return augments

    def _merge_official_sources(self, kiwi_data, fighting_data):
        """
        合并kiwi_augments和fighting_rune两个数据源
        
        策略：
        - 基础信息（名称、等级、isNew、icon）以kiwi为准（更完整、有中英文名）
        - official_desc 以kiwi的tooltip为准（掌盟页面显示的简洁描述）
        - fighting的desc_with_values作为补充（带完整数值的描述）
        - icon优先用kiwi的（格式更统一），没有则用fighting的
        """
        merged = []
        all_names = set()

        if kiwi_data:
            all_names.update(kiwi_data.keys())
        if fighting_data:
            all_names.update(fighting_data.keys())

        if not all_names:
            self.logger.error("两个数据源都为空！")
            return []

        for name in sorted(all_names):
            kiwi = kiwi_data.get(name, {})
            fighting = fighting_data.get(name, {})

            # 合并数据
            augment = {
                "augment_id": kiwi.get("augment_id", "") or fighting.get("fighting_id", ""),
                "name": name,
                "name_en": kiwi.get("name_en", "") or fighting.get("api_name", ""),
                # icon优先kiwi（有large_Icon和small_Icon），其次fighting
                "icon_url": kiwi.get("icon_url", "") or fighting.get("icon_url", ""),
                "icon_small": kiwi.get("icon_small", "") or fighting.get("icon_small", ""),
                # 等级优先kiwi
                "rarity": kiwi.get("rarity", "") or fighting.get("rarity", ""),
                # 掌盟页面显示的简洁描述（kiwi tooltip）
                "official_desc": kiwi.get("official_desc", ""),
                # 带完整数值的描述（fighting desc）
                "desc_with_values": fighting.get("desc_with_values", ""),
                "tooltip_with_values": fighting.get("tooltip_with_values", ""),
                # 原始数值参数
                "data_values": fighting.get("data_values", {}),
                "is_new": kiwi.get("is_new", False),
                "is_pbe": kiwi.get("is_pbe", False),
                # 来源标记
                "sources": [],
            }

            if kiwi:
                augment["sources"].append("kiwi_augments")
            if fighting:
                augment["sources"].append("fighting_rune")

            # 如果kiwi没有official_desc，用fighting的desc_with_values代替
            if not augment["official_desc"] and augment["desc_with_values"]:
                augment["official_desc"] = augment["desc_with_values"]

            merged.append(augment)

        # 统计
        both = sum(1 for a in merged if len(a["sources"]) == 2)
        kiwi_only = sum(1 for a in merged if a["sources"] == ["kiwi_augments"])
        fighting_only = sum(1 for a in merged if a["sources"] == ["fighting_rune"])
        with_icon = sum(1 for a in merged if a["icon_url"])
        with_desc = sum(1 for a in merged if a["official_desc"])
        with_values = sum(1 for a in merged if a["desc_with_values"])

        self.logger.info(f"数据合并完成: 共 {len(merged)} 个符文")
        self.logger.info(f"  两源都有: {both}, 仅kiwi: {kiwi_only}, 仅fighting: {fighting_only}")
        self.logger.info(f"  有icon: {with_icon}, 有描述: {with_desc}, 有数值描述: {with_values}")

        return merged

    def _clean_html(self, text):
        """清除HTML标签"""
        if not text:
            return ""
        # 使用BeautifulSoup清除HTML标签
        clean = BeautifulSoup(text, "html.parser").get_text()
        # 清理多余空白
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _crawl_ugc_data(self, augments):
        """
        爬取UGC评分和评论数据
        
        逻辑：
        1. 对每个符文，调用 go/vote/get_rate 获取掌盟真实评分（不需要登录态）
        2. 调用评论接口获取热门评论 + 全部评论
        3. 评分来自掌盟评分系统（所有用户评分的加权平均，10分制）
        """
        ugc_list = []
        total = len(augments)
        success_count = 0
        has_score_count = 0

        for idx, augment in enumerate(augments):
            name = augment["name"]
            augment_id = augment.get("augment_id", "")
            topic_id = f"{config.ZHANGMENG_TOPIC_ID_PREFIX}{augment_id}" if augment_id else ""

            self.logger.info(f"[{idx+1}/{total}] 获取UGC: {name}" +
                             (f" (topic: {topic_id})" if topic_id else " (无topic_id)"))

            ugc = {
                "augment_name": name,
                "topic_id": topic_id,
                "augment_id": augment_id,
                "score": 0,
                "score_count": 0,       # 评分总数
                "score_distribute": [],  # 评分分布
                "total_comments": 0,     # 总数（评分+评论）
                "comment_count": 0,      # 纯评论数
                "hot_comments": [],      # 热门评论（按点赞排序）
                "all_comments": [],      # 全部评论（按时间排序）
            }

            if topic_id:
                # 步骤1: 获取掌盟真实评分（go/vote/get_rate）
                rate_data = self._fetch_rate_from_api(topic_id, name)
                if rate_data:
                    ugc["score"] = rate_data["score"]
                    ugc["score_count"] = rate_data["score_count"]
                    ugc["score_distribute"] = rate_data.get("distribute", [])
                    if rate_data["score"] > 0:
                        has_score_count += 1

                # 步骤2: 获取评论数据
                comment_data = self._fetch_full_ugc(topic_id, name)
                if comment_data:
                    ugc["total_comments"] = comment_data.get("total_comments", 0)
                    ugc["comment_count"] = comment_data.get("comment_count", 0)
                    ugc["hot_comments"] = comment_data.get("hot_comments", [])
                    ugc["all_comments"] = comment_data.get("all_comments", [])
                    ugc["detail_url"] = comment_data.get("detail_url", "")
                    success_count += 1

            ugc_list.append(ugc)

            # 每爬50个打一次进度日志
            if (idx + 1) % 50 == 0:
                self.logger.info(f"  进度: {idx+1}/{total}, 成功: {success_count}, 有评分: {has_score_count}")

        self.logger.info(f"UGC数据获取完成: 成功 {success_count}/{total}, 有评分: {has_score_count}")
        return ugc_list

    def _fetch_rate_from_api(self, topic_id, augment_name):
        """
        通过 go/vote/get_rate 接口获取掌盟真实评分
        
        这个接口不需要登录态！直接返回：
        - average: 平均分（10分制，如7.5）
        - total_num: 评分总数（如80）
        - distribute: 评分分布（1-5星各有多少人）
        """
        url = config.ZHANGMENG_RATE_API_URL
        payload = {"rate_id": topic_id}

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=config.ZHANGMENG_APP_HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )

            if response.status_code != 200:
                self.logger.debug(f"评分接口返回 {response.status_code}: {augment_name}")
                return None

            data = response.json()
            if data.get("result") != 0:
                self.logger.debug(f"评分接口返回结果码: {data.get('result')} - {augment_name}")
                return None

            d = data.get("data", {})
            average = d.get("average", 0)
            total_num = d.get("total_num", 0)
            distribute = d.get("distribute", [])

            if average > 0:
                self.logger.info(f"  {augment_name}: 评分={average} ({total_num}条评分)")

            return {
                "score": average,       # 已经是10分制
                "score_count": total_num,
                "distribute": distribute,
            }

        except Exception as e:
            self.logger.warning(f"评分接口请求失败: {augment_name} - {e}")
            return None

    def _fetch_full_ugc(self, topic_id, augment_name):
        """
        获取符文的评论数据：热门评论 + 全部评论
        
        注意：评分已从 go/vote/get_rate 接口获取，此方法只负责评论。
        
        步骤1: 获取热门评论（list_key="hot*"，按点赞排序）
        步骤2: 翻页获取全部最新评论（list_key="new*"）
        """
        url = config.ZHANGMENG_COMMENT_API_URL
        params = config.ZHANGMENG_COMMENT_API_PARAMS
        full_url = f"{url}?plat={params['plat']}&version={params['version']}"

        # ===== 步骤1: 获取热门评论 =====
        hot_comments = []
        try:
            payload_hot = {
                "app_id": 1,
                "topic_id": topic_id,
                "top_comment_list": [{"comment_id": "", "reply_id_list": [""]}],
                "start_time": str(int(time.time())),
                "game_zone": "lol",
                "source_game_zone": "lol",
                "list_key": "hot*",
            }
            resp = self.session.post(
                full_url, json=payload_hot,
                headers=config.ZHANGMENG_APP_HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("result") == 0:
                    for c in data.get("data", {}).get("comment_list", []):
                        comment = self._extract_comment(c)
                        if comment:
                            hot_comments.append(comment)
            self._random_delay()
        except Exception as e:
            self.logger.debug(f"热门评论获取失败: {augment_name} - {e}")

        # ===== 步骤2: 翻页获取全部评论 =====
        all_comments = []       # 所有评论
        total_num = 0           # 总数（评分+评论）
        comment_total_num = 0   # 纯评论数
        next_time = str(int(time.time()))
        list_key = "new*"
        max_pages = 50          # 最多翻50页（500条），防止无限循环

        for page_idx in range(max_pages):
            try:
                payload = {
                    "app_id": 1,
                    "topic_id": topic_id,
                    "top_comment_list": [{"comment_id": "", "reply_id_list": [""]}],
                    "start_time": next_time,
                    "game_zone": "lol",
                    "source_game_zone": "lol",
                    "list_key": list_key,
                }
                resp = self.session.post(
                    full_url, json=payload,
                    headers=config.ZHANGMENG_APP_HEADERS,
                    timeout=config.REQUEST_TIMEOUT,
                )

                if resp.status_code != 200:
                    self.logger.debug(f"评论第{page_idx+1}页: HTTP {resp.status_code}")
                    break

                data = resp.json()
                if data.get("result") != 0:
                    break

                d = data.get("data", {})

                # 第一页获取总数信息
                if page_idx == 0:
                    total_num = d.get("total_num", 0)
                    comment_total_num = d.get("comment_total_num", 0)
                    if total_num == 0:
                        break  # 没有任何评论/评分

                comments_page = d.get("comment_list", [])
                if not comments_page:
                    break  # 没有更多评论

                # 收集评论
                for c in comments_page:
                    comment = self._extract_comment(c)
                    if comment:
                        all_comments.append(comment)

                # 获取下一页参数
                next_time = d.get("next_start_time", "")
                if d.get("list_key"):
                    list_key = d["list_key"]

                if not next_time:
                    break  # 没有下一页

                self._random_delay()

            except Exception as e:
                self.logger.debug(f"评论第{page_idx+1}页异常: {augment_name} - {e}")
                break

        if all_comments:
            self.logger.info(
                f"  {augment_name}: "
                f"评论={len(all_comments)}条, 热门={len(hot_comments)}条, "
                f"翻页={page_idx+1}页"
            )

        # 如果没有数据，返回None
        if total_num == 0 and not all_comments and not hot_comments:
            return None

        return {
            "total_comments": total_num,
            "comment_count": comment_total_num,
            "hot_comments": hot_comments,
            "all_comments": all_comments,
            "detail_url": self._build_detail_url(topic_id),
        }

    def _extract_comment(self, comment_data):
        """从评论数据中提取评论信息"""
        content = comment_data.get("content", "")
        if not content:
            topic_data = comment_data.get("topic_data", {})
            content = topic_data.get("digest", "")

        if not content:
            return None

        # 获取评分
        rate_info = comment_data.get("rate_info", {})
        my_rate = rate_info.get("my_rate", 0) if rate_info else 0

        return {
            "content": content,
            "from_addr": comment_data.get("from_addr", ""),
            "likes": comment_data.get("favour_num", 0),
            "timestamp": comment_data.get("timestamp", 0),
            "comment_uuid": comment_data.get("comment_uuid", ""),
            "scene": comment_data.get("scene", ""),
            "rate": my_rate,  # 该评论者给的评分（0=未评分, 1-5=评分值）
        }

    def _build_detail_url(self, topic_id):
        """构建符文详情页URL"""
        if not topic_id:
            return ""
        rune_id = topic_id.replace(config.ZHANGMENG_TOPIC_ID_PREFIX, "")
        return (f"https://lol.qq.com/zmlolzonehm/page/runeMelee/"
                f"?tabkey=buffRanking&id={rune_id}&open_comment=1")


if __name__ == "__main__":
    crawler = ZhangmengCrawler()
    result = crawler.crawl()
    print(f"\n完成！共 {len(result['augments'])} 个符文, {len(result['ugc'])} 条UGC")
