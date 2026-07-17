# -*- coding: utf-8 -*-
"""bidsearch_scraper.py - 招标搜索聚合 (Scrapling)"""
import re, logging, time
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin
from .base_scraper import BaseScraper, RawTenderItem

logger = logging.getLogger(__name__)

SEARCH_SOURCES = [
    {"name": "招标雷达", "base": "https://www.zhaobiao.cn",
     "search": "https://www.zhaobiao.cn/search", "kw": "kw"},
    {"name": "中国招标网", "base": "https://www.chinabidding.cn",
     "search": "https://www.chinabidding.cn/search/search", "kw": "keywords"},
]

class BidSearchScraper(BaseScraper):
    site_name = "招标搜索聚合"

    def fetch(self, region=None, industry=None, time_range_days=7, raw_query=None):
        results = []
        kw = " ".join(filter(None, [region, industry])) or "招标公告"
        for src in SEARCH_SOURCES[:1]:
            if not self.check_robots_allowed(src["base"]):
                continue
            try:
                page = self._get_page(src["search"], params={src["kw"]: kw}, timeout=20)
                items = self._parse(page, src, region, industry, time_range_days)
                results = self._dedup(items)
                if results:
                    logger.info(f"{src['name']}: {len(results)} items")
                    break
            except Exception as e:
                logger.warning(f"{src['name']}: {e}")
            time.sleep(2)
        logger.info(f"{self.site_name}: {len(results)} items total")
        return results

    def _dedup(self, items):
        seen = set()
        out = []
        for i in items:
            if i.source_url not in seen:
                seen.add(i.source_url)
                out.append(i)
        return out

    def _parse(self, page, src, region, industry, days):
        items = []
        cutoff = datetime.now() - timedelta(days=days)
        selectors = ["ul.search-result li", "div.result-item", "ul.list li", "table tr", "li", "a[href]"]
        rows = []
        for sel in selectors:
            rows = page.css(sel)
            if rows and len(rows) >= 2:
                break
        for row in rows:
            try:
                links = row.css("a")
                if not links: continue
                title = links[0].css("::text").get()
                if not title or len(str(title).strip()) < 5: continue
                skip = ["首页","下一页","上一页","登录","注册","返回","更多"]
                if str(title).strip() in skip: continue
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
                    title=str(title).strip(), region=region or self._region(row_text) or "全国",
                    industry=industry or self._industry(str(title)) or "综合",
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

    def _region(self, t):
        rs = ["北京","上海","广东","深圳","广州","浙江","杭州","江苏","四川","湖北","山东","河南","河北","福建","湖南","安徽","辽宁","陕西","重庆","天津","广西","云南","贵州","江西"]
        for r in rs:
            if r in t: return r
        return "全国"

    def _industry(self, t):
        for k, v in [("建筑","建筑工程"),("施工","建筑工程"),("市政","市政工程"),("公路","交通工程"),("道路","交通工程"),("水利","水利工程"),("医疗","医疗设备"),("医院","医疗设备"),("信息","信息技术"),("软件","信息技术"),("系统","信息技术"),("电力","电力工程"),("环保","环保工程"),("绿化","园林绿化"),("采购","政府采购"),("设备","设备采购")]:
            if k in t: return v
        return "综合"

    def _amount(self, t):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:万元|万|亿元|亿)", t)
        if m:
            a = float(m.group(1))
            if "亿" in m.group(0): a *= 10000
            return f"约{a:.0f}万元"
        return None
