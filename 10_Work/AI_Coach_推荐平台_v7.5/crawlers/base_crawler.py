# -*- coding: utf-8 -*-
"""
爬虫基类 - 封装通用的请求方法、重试机制、延迟控制、日志记录
"""
import json
import logging
import os
import random
import time
from typing import Any, Dict, Optional

import requests

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


class BaseCrawler:
    """爬虫基类"""

    def __init__(self, name: str = "BaseCrawler"):
        self.name = name
        self.session = requests.Session()
        self.logger = logging.getLogger(name)
        self._setup_logging()
        self._last_request_time = 0

    def _setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format=config.LOG_FORMAT,
        )

    def _random_delay(self):
        """随机延迟，避免触发反爬"""
        elapsed = time.time() - self._last_request_time
        min_wait = config.MIN_DELAY
        if elapsed < min_wait:
            delay = random.uniform(min_wait - elapsed, config.MAX_DELAY - elapsed)
            if delay > 0:
                self.logger.debug(f"等待 {delay:.1f}s...")
                time.sleep(delay)
        self._last_request_time = time.time()

    def get(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = None,
        max_retries: int = None,
    ) -> Optional[requests.Response]:
        """
        发送GET请求，带重试和延迟
        """
        headers = headers or config.DEFAULT_HEADERS
        timeout = timeout or config.REQUEST_TIMEOUT
        max_retries = max_retries or config.MAX_RETRIES

        for attempt in range(1, max_retries + 1):
            try:
                self._random_delay()
                self.logger.debug(f"GET {url} (attempt {attempt}/{max_retries})")
                resp = self.session.get(
                    url, headers=headers, params=params, timeout=timeout
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                self.logger.warning(
                    f"请求失败 (attempt {attempt}/{max_retries}): {url} -> {e}"
                )
                if attempt < max_retries:
                    time.sleep(config.RETRY_DELAY * attempt)
                else:
                    self.logger.error(f"请求最终失败: {url}")
                    return None

    def get_json(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        """发送GET请求并返回JSON数据"""
        resp = self.get(url, headers=headers, params=params)
        if resp is None:
            return None
        try:
            return resp.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {url} -> {e}")
            # 尝试处理JSONP格式
            text = resp.text.strip()
            if text.startswith("(") or text.startswith("callback("):
                try:
                    # 移除JSONP包装
                    json_str = text[text.index("(") + 1 : text.rindex(")")]
                    return json.loads(json_str)
                except (ValueError, json.JSONDecodeError):
                    pass
            return None

    def get_text(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[str]:
        """发送GET请求并返回文本"""
        resp = self.get(url, headers=headers, params=params)
        if resp is None:
            return None
        return resp.text

    def save_json(self, data: Any, filepath: str):
        """保存数据为JSON文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"数据已保存: {filepath}")

    def load_json(self, filepath: str) -> Optional[Any]:
        """从JSON文件加载数据"""
        if not os.path.exists(filepath):
            self.logger.warning(f"文件不存在: {filepath}")
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def crawl(self):
        """爬取主方法 - 子类需要重写"""
        raise NotImplementedError("子类必须实现 crawl() 方法")
