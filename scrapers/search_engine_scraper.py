# -*- coding: utf-8 -*-
"""search_engine_scraper.py - 多引擎并行搜索 + 去重合并"""
import re, logging, time, random, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List
from .base_scraper import BaseScraper, RawTenderItem

logger = logging.getLogger(__name__)

# User-Agent 池 (from BidMonitor-AI best practice)
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
]

# 搜索引擎配置
ENGINES = [
    {
        "name": "DuckDuckGo",
        "url": "https://html.duckduckgo.com/html/?q={query}",
        "row_sel": ".result", "link_sel": "a.result__a",
        "url_decode": True,  # DDG 用重定向包真实URL
    },
    {
        "name": "Bing",
        "url": "https://www.bing.com/search?q={query}&count=20",
        "row_sel": "#b_results .b_algo", "link_sel": "h2 a",
        "url_decode": False,
    },
]

class SearchEngineScraper(BaseScraper):
    site_name = "多引擎搜索"

    def fetch(self, region=None, industry=None, time_range_days=7, raw_query=None):
        # 构建搜索词
        if raw_query:
            clean = raw_query
            for w in ["帮我","找","查","一下","最近","看看","搜索","一周","三天","今天"]:
                clean = clean.replace(w, "")
            query = clean.strip()
        else:
            parts = [s for s in [region, industry] if s]
            query = " ".join(parts) if parts else "招标公告"
        query += " 招标 site:ccgp.gov.cn"

        # 并行搜索多个引擎
        all_items = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(self._search_one, eng, query): eng["name"] for eng in ENGINES}
            for future in as_completed(futures, timeout=30):
                name = futures[future]
                try:
                    items = future.result(timeout=25)
                    all_items.extend(items)
                    logger.info(f"{name}: {len(items)} items")
                except Exception as e:
                    logger.warning(f"{name}: {e}")

        # 去重 + 日期过滤
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=time_range_days)
        seen = set()
        results = []
        for item in all_items:
            key = item.source_url or item.title
            if key not in seen:
                seen.add(key)
                # 日期过滤
                if item.publish_date:
                    try:
                        if datetime.strptime(item.publish_date, "%Y-%m-%d") < cutoff:
                            continue
                    except ValueError:
                        pass
                results.append(item)

        logger.info(f"{self.site_name}: {len(results)} unique items")
        return results

    def _search_one(self, engine, query):
        url = engine["url"].format(query=urllib.parse.quote(query))
        time.sleep(random.uniform(0.5, 1.5))  # 错开请求
        if not self.check_robots_allowed(url):
            logger.info(f"{engine['name']}: blocked by robots.txt, skipping")
            return []
        try:
            page = self._get_page(url, timeout=15)
        except Exception:
            return []

        rows = page.css(engine["row_sel"])
        if not rows:
            rows = page.css("a[href]")

        items = []
        for r in rows[:20]:
            try:
                links = r.css(engine["link_sel"]) or r.css("a")
                if not links:
                    continue
                title = ""
                href = ""
                for a in links:
                    try:
                        t = a.get_all_text(strip=True)
                    except Exception:
                        t = a.css("::text").get()
                    if t and len(str(t)) > len(title):
                        title = str(t)
                    h = a.attrib.get("href", "")
                    if "ccgp.gov.cn" in h:
                        href = h

                if not title or len(title) < 8:
                    continue
                if not href:
                    continue

                # DDG URL 解码
                if engine.get("url_decode"):
                    m = re.search(r'uddg=([^&]+)', href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))

                # 过滤导航链接
                skip = ["首页","下一页","上一页","登录","注册","返回"]
                if any(w == title.strip() for w in skip):
                    continue

                title = " ".join(title.split())
                pub = self._date(title) or datetime.now().strftime("%Y-%m-%d")

                items.append(RawTenderItem(
                    title=title, region="", industry="",
                    amount="详见公告", publish_date=pub,
                    deadline="详见公告", source_url=href,
                    source_site=f"{engine['name']}搜索",
                    raw_text=title,
                ))
            except Exception:
                continue

        return items

    def _date(self, t):
        m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", t)
        if m:
            return m.group(1).replace("年","-").replace("月","-").replace("/","-").replace(".","-")
        m = re.search(r"/(\d{6})/t(\d{8})_", t)
        if m:
            d = m.group(2)
            return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        return None
