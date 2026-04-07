# -*- coding: utf-8 -*-
"""
海克斯大乱斗符文知识库 - 全局配置文件
"""
import os

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
RAW_DATA_DIR = os.path.join(OUTPUT_DIR, "raw")
FINAL_EXCEL_PATH = os.path.join(OUTPUT_DIR, "海克斯大乱斗符文知识库.xlsx")

# 确保输出目录存在
os.makedirs(RAW_DATA_DIR, exist_ok=True)

# ==================== 请求通用配置 ====================
REQUEST_TIMEOUT = 15  # 请求超时（秒）
MAX_RETRIES = 3       # 最大重试次数
RETRY_DELAY = 2       # 重试间隔（秒）
MIN_DELAY = 1.0       # 请求最小间隔（秒）
MAX_DELAY = 3.0       # 请求最大间隔（秒）

# 通用请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# ==================== hextech.dtodo.cn 配置 ====================
HEXTECH_BASE_URL = "https://hextech.dtodo.cn"
HEXTECH_API_URL = "https://hextech.dtodo.cn/api"
HEXTECH_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://hextech.dtodo.cn/zh-CN/augments",
    "Origin": "https://hextech.dtodo.cn",
}
HEXTECH_RAW_FILE = os.path.join(RAW_DATA_DIR, "hextech_augments.json")

# ==================== 掌上英雄联盟配置 ====================
# 掌盟乱斗符文相关接口（通过Playwright浏览器自动化 + Stream抓包确认 2026-03-24）
ZHANGMENG_BASE_URL = "https://game.gtimg.cn"
ZHANGMENG_LOL_URL = "https://lol.qq.com"

# 掌盟符文官方CDN数据源（掌盟页面真正加载的JSON数据）
ZHANGMENG_KIWI_AUGMENTS_URL = "https://game.gtimg.cn/images/lol/act/img/js/kiwi/kiwi_augments.json"
ZHANGMENG_FIGHTING_RUNE_URL = "https://game.gtimg.cn/images/lol/act/img/js/fighting_rune/fighting_rune.js"

# 掌盟符文网页版URL（资料库→乱斗符文，WebView内嵌页面）
ZHANGMENG_AUGMENT_WEB_URL = "https://lol.qq.com/zmlolzonehmtest/page/gamedata/?tab=ldbuff"
# 符文排行/详情页面
ZHANGMENG_RUNE_MELEE_URL = "https://lol.qq.com/zmlolzonehm/page/runeMelee/"

# 掌盟UGC评论接口（真实抓包地址 2026-03-24）
# POST https://mlol.qt.qq.com/go/comment_svr/comment/list?plat=ios&version=10000
ZHANGMENG_COMMENT_API_URL = "https://mlol.qt.qq.com/go/comment_svr/comment/list"
ZHANGMENG_COMMENT_API_PARAMS = {"plat": "ios", "version": "10000"}

# 掌盟评分接口（从JS源码分析发现 2026-03-25）
# POST https://mlol.qt.qq.com/go/vote/get_rate
# 不需要登录态！rate_id = hexaramdatarune_{augment_id}
# 返回：average(10分制)、total_num(评分总数)、distribute(评分分布)
ZHANGMENG_RATE_API_URL = "https://mlol.qt.qq.com/go/vote/get_rate"

# topic_id格式：hexaramdatarune_{符文编号}
# 例如：hexaramdatarune_1346
ZHANGMENG_TOPIC_ID_PREFIX = "hexaramdatarune_"

# 掌盟APP请求头（来自抓包 iPhone掌盟 QTL/12.4.1）
ZHANGMENG_APP_HEADERS = {
    "Host": "mlol.qt.qq.com",
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "QTL/12.4.1 (iPhone; IOS 18.6.2; Scale/3.00)",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "GH-HEADER": "1-2-105-1241-0",
}

# 掌盟网页版请求头（用于爬取符文列表页面）
ZHANGMENG_WEB_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://lol.qq.com/",
    "Origin": "https://lol.qq.com",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6_2 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 lolapp/12.4.1.2898",
}

# 向后兼容
ZHANGMENG_HEADERS = ZHANGMENG_WEB_HEADERS
ZHANGMENG_RAW_FILE = os.path.join(RAW_DATA_DIR, "zhangmeng_augments.json")
ZHANGMENG_UGC_FILE = os.path.join(RAW_DATA_DIR, "zhangmeng_ugc.json")
HEXTECH_CHAMPION_COMBOS_FILE = os.path.join(RAW_DATA_DIR, "hextech_champion_combos.json")
HEXTECH_SYNERGIES_FILE = os.path.join(RAW_DATA_DIR, "hextech_synergies.json")

# ==================== ARAM Mayhem 配置 ====================
ARAMMAYHEM_BASE_URL = "https://arammayhem.com"
ARAMMAYHEM_COMBO_URL = "https://arammayhem.com/zh-cn/combo/"
ARAMMAYHEM_VOTE_API_URL = "https://arammayhem.com/api/combos/feed"
ARAMMAYHEM_RAW_FILE = os.path.join(RAW_DATA_DIR, "arammayhem_combos.json")

# ==================== B站配置 ====================
BILIBILI_SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
BILIBILI_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://search.bilibili.com/",
    "Origin": "https://www.bilibili.com",
}
BILIBILI_SEARCH_KEYWORDS = [
    "海克斯大乱斗 符文推荐",
    "海克斯大乱斗 符文组合",
    "海克斯大乱斗 黑科技",
    "ARAM 符文攻略",
    "海克斯大乱斗 强势符文",
]
BILIBILI_RAW_FILE = os.path.join(RAW_DATA_DIR, "bilibili_content.json")

# ==================== 推荐指数阈值配置 ====================
# 基于胜率 + Tier分级计算推荐指数
RECOMMENDATION_THRESHOLDS = {
    "S": {"min_winrate": 60.0, "tiers": ["T1"]},
    "A": {"min_winrate": 55.0, "tiers": ["T1", "T2"]},
    "B": {"min_winrate": 52.0, "tiers": ["T2", "T3"]},
    "C": {"min_winrate": 49.0, "tiers": ["T3", "T4"]},
    "D": {"min_winrate": 0.0,  "tiers": ["T4", "T5"]},
}

# 推荐icon映射
RECOMMENDATION_ICONS = {
    "S": "推荐选取",   # 强烈推荐
    "A": "推荐选取",   # 推荐
    "B": "一般",       # 中等
    "C": "一般",       # 一般
    "D": "推荐刷新",   # 建议刷新
}

# ==================== 符文等级配置 ====================
AUGMENT_TIERS = ["白银", "黄金", "棱彩"]

# ==================== AI内容生成标签 ====================
AI_GENERATED_TAG = "[AI生成-待审核]"

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
