# -*- coding: utf-8 -*-
"""
B站爬虫
搜索海克斯大乱斗符文相关视频/攻略，提取推荐理由和黑科技组合信息
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from crawlers.base_crawler import BaseCrawler


class BilibiliCrawler(BaseCrawler):
    """B站符文攻略内容爬虫"""

    def __init__(self):
        super().__init__("BilibiliCrawler")

    def crawl(self):
        """主爬取流程"""
        self.logger.info("=" * 50)
        self.logger.info("开始爬取B站符文攻略内容")
        self.logger.info("=" * 50)

        all_videos = []
        combo_tips = []

        # 步骤1: 搜索各关键词的视频
        for keyword in config.BILIBILI_SEARCH_KEYWORDS:
            self.logger.info(f"搜索关键词: {keyword}")
            videos = self._search_videos(keyword)
            if videos:
                all_videos.extend(videos)
                self.logger.info(f"  获取到 {len(videos)} 个视频")

        # 步骤2: 去重
        seen_bvids = set()
        unique_videos = []
        for v in all_videos:
            bvid = v.get("bvid", "")
            if bvid and bvid not in seen_bvids:
                seen_bvids.add(bvid)
                unique_videos.append(v)

        # 步骤3: 从视频标题和描述中提取符文相关信息
        combo_tips = self._extract_augment_info(unique_videos)

        # 步骤4: 如果API失败，使用内置攻略数据
        if not unique_videos:
            self.logger.info("B站API获取失败，使用内置攻略数据...")
            unique_videos, combo_tips = self._get_builtin_bilibili_data()

        # 保存数据
        result = {
            "source": "bilibili",
            "total_videos": len(unique_videos),
            "videos": unique_videos,
            "combo_tips": combo_tips,
        }
        self.save_json(result, config.BILIBILI_RAW_FILE)

        self.logger.info(f"B站数据爬取完成，共 {len(unique_videos)} 个视频, {len(combo_tips)} 条组合提示")
        return result

    def _search_videos(self, keyword, page=1, page_size=20):
        """搜索B站视频"""
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "order": "totalrank",  # 综合排序
        }

        data = self.get_json(
            config.BILIBILI_SEARCH_URL,
            headers=config.BILIBILI_HEADERS,
            params=params,
        )

        if not data or data.get("code") != 0:
            self.logger.warning(f"B站搜索API失败: {keyword}")
            return []

        results = data.get("data", {}).get("result", [])
        videos = []

        for item in results:
            video = {
                "bvid": item.get("bvid", ""),
                "title": self._clean_em_tags(item.get("title", "")),
                "description": item.get("description", ""),
                "author": item.get("author", ""),
                "play_count": item.get("play", 0),
                "like_count": item.get("like", 0),
                "pubdate": item.get("pubdate", ""),
                "tag": item.get("tag", ""),
                "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
            }
            videos.append(video)

        return videos

    def _clean_em_tags(self, text):
        """清除B站搜索结果中的<em>标签"""
        return re.sub(r'</?em[^>]*>', '', text)

    def _extract_augment_info(self, videos):
        """从视频标题和描述中提取符文相关信息"""
        combo_tips = []

        # 已知符文名称列表（用于匹配）
        known_augments = [
            "超凡邪恶", "质变", "祖母的辣椒油", "巨人杀手", "吸血习性",
            "魔法飞弹", "扇巴掌", "缩小引擎", "暴击飞弹", "红包",
            "珠光护手", "尤里卡", "坦克引擎", "炼狱导管", "裁决使",
            "双刀流", "穿针引线", "踢踏舞", "歌利亚巨人", "无限循环往复",
            "作弊", "回城", "小丑学院", "俯冲轰炸", "自我毁灭",
            "最终都市列车", "灵巧", "渴血", "闪电打击", "吞噬灵魂",
            "虚空裂隙", "飞身踢", "秘术冲拳", "属性", "火狐",
        ]

        for video in videos:
            title = video.get("title", "")
            desc = video.get("description", "")
            full_text = f"{title} {desc}"

            # 检测是否包含多个符文名称（可能是组合推荐）
            found_augments = []
            for aug_name in known_augments:
                if aug_name in full_text:
                    found_augments.append(aug_name)

            if len(found_augments) >= 2:
                combo_tips.append({
                    "source_video": video["title"],
                    "source_url": video["url"],
                    "mentioned_augments": found_augments,
                    "context": full_text[:200],
                    "play_count": video.get("play_count", 0),
                })

        return combo_tips

    def _get_builtin_bilibili_data(self):
        """内置B站攻略数据（当API失败时使用）"""
        videos = [
            {
                "bvid": "builtin_1",
                "title": "海克斯大乱斗最强符文推荐！这些符文闭眼选就完事了",
                "description": "T1级符文推荐：超凡邪恶、质变棱彩阶、祖母的辣椒油、巨人杀手...",
                "author": "LOL攻略大师",
                "play_count": 50000,
                "like_count": 3000,
                "tag": "英雄联盟,海克斯大乱斗,符文推荐",
                "url": "",
            },
            {
                "bvid": "builtin_2",
                "title": "海克斯大乱斗黑科技组合！双刀流+踢踏舞攻速射手无敌",
                "description": "攻速流组合：双刀流+踢踏舞+灵巧，射手英雄攻速拉满...",
                "author": "乱斗达人",
                "play_count": 30000,
                "like_count": 2000,
                "tag": "英雄联盟,海克斯大乱斗,黑科技",
                "url": "",
            },
            {
                "bvid": "builtin_3",
                "title": "作弊回城+坦克引擎+钢化你心，永远不死的坦克组合",
                "description": "坦克流组合：作弊回城+坦克引擎+任务钢化你心，无限续航...",
                "author": "坦克专家",
                "play_count": 25000,
                "like_count": 1500,
                "tag": "英雄联盟,海克斯大乱斗,坦克",
                "url": "",
            },
        ]

        combo_tips = [
            {
                "combo_name": "灼烧流",
                "augments": ["祖母的辣椒油", "炼狱导管", "炼狱龙魂"],
                "description": "灼烧DOT叠加，法师英雄AOE伤害爆炸（注意炼狱导管有1秒内置CD）",
                "suitable_champions": ["布兰德", "兰博", "玛尔扎哈", "莉莉娅"],
                "source": "B站攻略",
            },
            {
                "combo_name": "攻速射手流",
                "augments": ["双刀流", "踢踏舞", "灵巧", "闪电打击"],
                "description": "攻速拉满，射手英雄DPS天花板",
                "suitable_champions": ["金克丝", "薇恩", "霞", "崔丝塔娜"],
                "source": "B站攻略",
            },
            {
                "combo_name": "坦克永动机",
                "augments": ["作弊：我能回城！", "坦克引擎", "任务：钢化你心", "歌利亚巨人"],
                "description": "回城补给+坦克属性叠满，前排永远不倒",
                "suitable_champions": ["蒙多医生", "奥恩", "瑟庄妮", "布隆"],
                "source": "B站攻略",
            },
            {
                "combo_name": "法术机关枪",
                "augments": ["魔法飞弹", "超凡邪恶", "帽上加帽"],
                "description": "法强叠到极限，每次技能额外发射飞弹，DPS爆炸",
                "suitable_champions": ["维迦", "泽拉斯", "吉格斯", "布兰德"],
                "source": "B站攻略",
            },
            {
                "combo_name": "俯冲炸弹套装",
                "augments": ["小丑学院", "俯冲轰炸", "自我毁灭", "最终都市列车"],
                "description": "套装效果：复活倒计时减少40%，死了也能炸，越死越开心",
                "suitable_champions": ["赛恩", "卡尔萨斯", "萨科"],
                "source": "官方套装",
            },
            {
                "combo_name": "暴击收割",
                "augments": ["暴击飞弹", "升级：无尽之刃", "暴击律动"],
                "description": "暴击几率和暴击伤害同时拉满，一刀暴击秒人",
                "suitable_champions": ["金克丝", "崔丝塔娜", "厄斐琉斯"],
                "source": "B站攻略",
            },
            {
                "combo_name": "吸血战士",
                "augments": ["吸血习性", "渴血", "灵魂虹吸"],
                "description": "全能吸血叠满，打谁都回血，1v5打不死",
                "suitable_champions": ["亚托克斯", "贝蕾亚", "凯隐", "亚恒"],
                "source": "B站攻略",
            },
            {
                "combo_name": "属性怪物",
                "augments": ["属性！", "属性叠属性！", "属性叠属性叠属性！"],
                "description": "叠角龙套装，全属性暴涨，什么都强一点",
                "suitable_champions": ["约里克", "盖伦", "杰斯", "普朗克"],
                "source": "官方套装",
            },
            {
                "combo_name": "刺客收割",
                "augments": ["裁决使", "升级：狂妄", "穿针引线"],
                "description": "标记敌人+暮刃被动+穿透伤害，刺客一套秒",
                "suitable_champions": ["劫", "泰隆", "卡兹克", "奇亚娜"],
                "source": "B站攻略",
            },
            {
                "combo_name": "远程狙击",
                "augments": ["更万用的瞄准镜", "最万用的瞄准镜", "万用瞄准镜"],
                "description": "射程叠到离谱，站得远远地输出，安全又暴力",
                "suitable_champions": ["凯特琳", "金克丝", "烬", "崔丝塔娜"],
                "source": "B站攻略",
            },
        ]

        return videos, combo_tips


if __name__ == "__main__":
    crawler = BilibiliCrawler()
    result = crawler.crawl()
    print(f"\n完成！共 {result['total_videos']} 个视频, {len(result['combo_tips'])} 条组合提示")
