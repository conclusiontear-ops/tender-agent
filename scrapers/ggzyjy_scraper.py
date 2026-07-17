# -*- coding: utf-8 -*-
"""ggzyjy_scraper.py - 公共资源交易平台 (Scrapling)"""
import re, logging, time
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin
from .base_scraper import BaseScraper, RawTenderItem

logger = logging.getLogger(__name__)

SOURCES = [
    {"name": "北京市公共资源交易", "base": "https://ggzyfw.beijing.gov.cn",
     "list": "https://ggzyfw.beijing.gov.cn/jyxx/gggs/"},
    {"name": "深圳公共资源交易", "base": "https://www.szggzy.com",
     "list": "https://www.szggzy.com/jyxx/zfcg/index.html"},
    {"name": "中国招标投标平台", "base": "https://www.ctbpsp.com",
     "list": "https://www.ctbpsp.com/index/list.html"},
]

class GGZYJYScraper(BaseScraper):
    site_name = "公共资源交易平台"

    def fetch(self, region=None, industry=None, time_range_days=7, raw_query=None):
        results = []
        sources = self._filter(region)
        for src in sources:
            if not self.check_robots_allowed(src["base"]):
                continue
            try:
                items = self._scrape(src, region, industry, time_range_days)
                results.extend(items)
            except Exception as e:
                logger.warning(f"{src['name']}: {e}")
            time.sleep(2)
        logger.info(f"{self.site_name}: {len(results)} items")
        return results

    def _filter(self, region):
        if not region: return SOURCES
        m = {"北京": ["北京"], "深圳": ["深圳"], "广东": ["深圳"]}
        names = m.get(region, [])
        if not names: return SOURCES
        return [s for s in SOURCES if any(n in s["name"] for n in names)]

    def _scrape(self, src, region, industry, days):
        page = self._get_page(src["list"], timeout=20)
        items = []
        cutoff = datetime.now() - timedelta(days=days)
        selectors = ["ul.list li", "ul.info-list li", "table tr", ".list-content li", "a[href]"]
        rows = []
        for sel in selectors:
            rows = page.css(sel)
            if rows and len(rows) >= 3:
                break
        for row in rows:
            try:
                links = row.css("a")
                if not links: continue
                title = links[0].css("::text").get()
                if not title or len(str(title).strip()) < 4: continue
                href = links[0].attrib.get("href", "")
                if href and not href.startswith("http"):
                    href = urljoin(src["base"], href)
                try:
                    row_text = row.get_all_text(strip=True)
                except Exception:
                    row_text = str(title)
                pub = self._date(row_text)
                if pub:
                    try:
                        if datetime.strptime(pub, "%Y-%m-%d") < cutoff: continue
                    except ValueError: pass
                items.append(RawTenderItem(
                    title=str(title).strip(), region=region or src["name"],
                    industry=industry or self._guess(str(title)),
                    amount=self._amount(row_text) or "详见公告",
                    publish_date=pub or datetime.now().strftime("%Y-%m-%d"),
                    deadline="详见公告", source_url=href,
                    source_site=f"{self.site_name}-{src['name']}", raw_text=row_text,
                ))
            except Exception:
                continue
        return items

    def _date(self, t):
        m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", t)
        if m: return m.group(1).replace("年","-").replace("月","-").replace("/","-").replace(".","-")
        return None

    def _amount(self, t):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:万元|万|亿元|亿)", t)
        if m:
            a = float(m.group(1))
            if "亿" in m.group(0): a *= 10000
            return f"约{a:.0f}万元"
        return None

    def _guess(self, t):
        for k, v in [("建筑","建筑工程"),("施工","建筑工程"),("市政","市政工程"),("公路","交通工程"),("水利","水利工程"),("医疗","医疗设备"),("IT","信息技术"),("信息","信息技术"),("电力","电力工程"),("环保","环保工程")]:
            if k in t: return v
        return "政府采购"
