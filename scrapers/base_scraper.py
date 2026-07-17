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
import time

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
    """爬虫基类 - 提供统一的网页获取和解析接口"""
    
    site_name: str = "未命名网站"
    request_timeout: int = 20
    request_delay: float = 1.0  # 请求间隔（秒），用于礼貌爬虫

    def __init__(self):
        # 延迟导入，兼容无 Scrapling 环境
        try:
            from scrapling.fetchers import Fetcher
            self._fetcher = Fetcher
            self._has_scrapling = True
            logger.info(f"{self.site_name}: Scrapling 已启用")
        except ImportError:
            self._has_scrapling = False
            logger.warning(f"{self.site_name}: Scrapling 不可用，将回退到 requests")
            self._fetcher = None

    def _get_page(self, url: str, **kwargs):
        """
        统一获取页面，优先使用 Scrapling，回退到 requests
        
        :param url: 目标URL
        :return: 解析器对象（兼容Scrapling Selector接口）
        """
        timeout = kwargs.pop("timeout", self.request_timeout)
        
        if self._has_scrapling:
            try:
                return self._fetcher.get(url, timeout=timeout * 1000, **kwargs)
            except Exception as e:
                logger.warning(f"{self.site_name}: Scrapling请求失败 ({e})，回退到requests")
                self._has_scrapling = False
        
        # 使用 requests 回退
        try:
            import requests
            resp = requests.get(url, timeout=timeout, headers={
                "User-Agent": "TenderAgent/1.0 (+http://localhost/bot)",  # 声明爬虫身份
            })
            resp.raise_for_status()
            
            # 尝试用 Selector（如果Scrapling可用）或用BeautifulSoup
            try:
                from scrapling.parser import Selector
                return Selector(resp.text, url=url)
            except ImportError:
                # 如果Scrapling不可用，用BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 包裹成兼容接口
                class SimpleSelector:
                    def __init__(self, soup, url):
                        self.soup = soup
                        self.url = url
                    
                    def css(self, expr):
                        return self.soup.select(expr)
                    
                    def xpath(self, expr):
                        # 简易XPath支持（转换为CSS）
                        # 这是个受限的实现，实际XPath更复杂
                        if '//' in expr:
                            logger.warning(f"BeautifulSoup不支持完整XPath: {expr}，建议改用CSS选择器")
                            return []
                        return self.soup.select(expr)
                
                return SimpleSelector(soup, url)
        except Exception as e:
            logger.error(f"{self.site_name}: 网页获取失败 - {e}")
            raise

    def _parse_page(self, html: str, url: str = ""):
        """解析 HTML 字符串"""
        try:
            from scrapling.parser import Selector
            return Selector(html, url=url)
        except ImportError:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            class SimpleSelector:
                def __init__(self, soup, url):
                    self.soup = soup
                    self.url = url
                
                def css(self, expr):
                    return self.soup.select(expr)
                
                def xpath(self, expr):
                    if '//' in expr:
                        logger.warning(f"BeautifulSoup不支持完整XPath: {expr}")
                        return []
                    return self.soup.select(expr)
            
            return SimpleSelector(soup, url)

    @abstractmethod
    def fetch(self, region: str = None, industry: str = None,
              time_range_days: int = 7, raw_query: str = None) -> List[RawTenderItem]:
        """
        抓取招标信息
        
        :param region: 地区
        :param industry: 行业
        :param time_range_days: 时间范围（天）
        :param raw_query: 原始用户查询
        :return: RawTenderItem 列表
        """
        raise NotImplementedError

    def check_robots_allowed(self, url: str) -> bool:
        """
        检查 robots.txt。若不存在(404)或无规则，默认允许。
        
        :param url: 目标URL
        :return: 是否允许爬取
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # 先尝试用 Scrapling 检查 robots.txt 是否存在
        if self._has_scrapling:
            try:
                resp = self._fetcher.get(robots_url, timeout=10)
                if resp.status != 200:
                    return True  # robots.txt 不存在 -> 允许
                # 用 RobotFileParser 解析
                rp = RobotFileParser()
                rp.parse(resp.body.decode("utf-8", errors="replace").splitlines())
                return rp.can_fetch("*", url)
            except Exception as e:
                logger.debug(f"{self.site_name}: Scrapling检查robots.txt失败 ({e})，回退到标准方式")
        
        # 回退到标准的 RobotFileParser 方式
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            if not rp.entries and rp.default_entry is None:
                return True  # 没有规则 -> 允许
            return rp.can_fetch("*", url)
        except Exception as e:
            logger.warning(f"{self.site_name}: 无法读取robots.txt ({e})，默认允许")
            return True

    def wait_between_requests(self):
        """请求间隔等待（礼貌爬虫）"""
        time.sleep(self.request_delay)
