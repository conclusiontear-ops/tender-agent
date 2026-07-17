# -*- coding: utf-8 -*-
"""
base_scraper.py - 爬虫适配器基类 (Scrapling 版本)
使用 Scrapling Fetcher 替代 requests，自带 TLS 指纹伪装与自适应解析。
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawTenderItem:
    """从网页抓取到的原始信息"""
    title: str
    region: str
    industry: str
    amount: str
    publish_date: str
    deadline: str
    source_url: str
    source_site: str
    raw_text: str = ""


class BaseScraper(ABC):
    site_name: str = "未命名网站"

    def __init__(self):
        # 延迟导入，兼容无 Scrapling 环境
        try:
            from scrapling.fetchers import Fetcher
            self._fetcher = Fetcher
            self._has_scrapling = True
        except ImportError:
            self._has_scrapling = False
            logger.warning(f"{self.site_name}: Scrapling 不可用，回退到 requests")

    def _get_page(self, url: str, **kwargs):
        """统一获取页面，优先 Scrapling"""
        timeout = kwargs.pop("timeout", 20)
        if self._has_scrapling:
            return self._fetcher.get(url, timeout=timeout * 1000, **kwargs)
        else:
            import requests
            resp = requests.get(url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            from scrapling.parser import Selector
            return Selector(resp.text, url=url)

    def _parse_page(self, html: str, url: str = ""):
        """解析 HTML 字符串"""
        from scrapling.parser import Selector
        return Selector(html, url=url)

    @abstractmethod
    def fetch(self, region: str = None, industry: str = None,
              time_range_days: int = 7, raw_query: str = None) -> List[RawTenderItem]:
        raise NotImplementedError

    def check_robots_allowed(self, url: str) -> bool:
        """检查 robots.txt。若不存在(404)或无规则，默认允许。"""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        # 先用 Scrapling 检查 robots.txt 是否存在
        try:
            if self._has_scrapling:
                resp = self._fetcher.get(robots_url, timeout=10)
                if resp.status != 200:
                    return True  # robots.txt 不存在 -> 允许
                # 用 RobotFileParser 解析
                rp = RobotFileParser()
                rp.parse(resp.body.decode("utf-8", errors="replace").splitlines())
                return rp.can_fetch("*", url)
        except Exception:
            pass
        # 回退到标准方式
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            if not rp.entries and rp.default_entry is None:
                return True
            return rp.can_fetch("*", url)
        except Exception:
            return True
