# -*- coding: utf-8 -*-
"""ccgp_scraper.py - hybrid search + list browsing"""
import re, logging, time, random
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin
from .base_scraper import BaseScraper, RawTenderItem
logger = logging.getLogger(__name__)

# Province -> common city names found in ccgp titles
PROVINCE_CITIES = {
    "陕西": ["西安", "榆林", "府谷", "延安", "宝鸡", "咸阳", "渭南", "汉中", "安康", "商洛", "铜川"],
    "北京": ["北京", "朝阳", "海淀", "丰台", "通州", "大兴", "昌平"],
    "上海": ["上海", "浦东", "徐汇", "静安", "黄浦"],
    "广东": ["广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山"],
    "浙江": ["杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华"],
    "江苏": ["南京", "苏州", "无锡", "常州", "南通", "徐州", "扬州"],
    "四川": ["成都", "绵阳", "德阳", "宜宾", "南充", "泸州"],
    "山东": ["济南", "青岛", "烟台", "潍坊", "临沂", "淄博", "威海"],
    "湖北": ["武汉", "宜昌", "襄阳", "荆州", "黄石", "十堰"],
    "河南": ["郑州", "洛阳", "开封", "南阳", "许昌", "新乡"],
    "福建": ["福州", "厦门", "泉州", "漳州", "莆田"],
    "湖南": ["长沙", "株洲", "湘潭", "衡阳", "岳阳", "常德"],
    "安徽": ["合肥", "芜湖", "蚌埠", "安庆", "马鞍山"],
    "辽宁": ["沈阳", "大连", "鞍山", "抚顺", "锦州"],
}

class CCGPScraper(BaseScraper):
    site_name = "CCGP"
    BASE = "http://www.ccgp.gov.cn"

    def fetch(self, region=None, industry=None, time_range_days=7, raw_query=None):
        if not self.check_robots_allowed(self.BASE):
            return []
        results = []
        cutoff = datetime.now() - timedelta(days=time_range_days)
        start = cutoff.strftime("%Y:%m:%d")
        end = datetime.now().strftime("%Y:%m:%d")
        # 搜索策略: 只用行业词搜(地区在本地过滤)
        # 原因: ccgp公告标题常用市级名(西安)而非省名(陕西)
        search_terms = []
        if industry:
            # 行业词取前2个汉字，覆盖更广
            short = industry[:2] if len(industry) >= 2 else industry
            if short not in search_terms:
                search_terms.append(short)
        if not search_terms and region:
            search_terms.append(region)
        if not search_terms:
            search_terms = ["招标公告"]
        kw = " ".join(search_terms)
        # 本地过滤用的关键词列表
        local_filters = [s for s in [region, industry] if s]
        try:
            results = self._search_api(kw, start, end, local_filters)
            logger.info(f"Search: {len(results)} items")
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        if len(results) < 3:
            try:
                more = self._browse_list(local_filters, cutoff)
                results.extend(more)
                logger.info(f"List: +{len(more)} items")
            except Exception as e:
                logger.warning(f"List failed: {e}")
        results = self._dedup(results)
        logger.info(f"{self.site_name}: {len(results)} unique")
        return results

    def _search_api(self, kw, start, end, local_filters=None):
        items = []
        for p in range(1, 4):
            try:
                page = self._get_page("http://search.ccgp.gov.cn/bxsearch", params={
                    "searchtype":"1","page_index":str(p),"bidSort":"0",
                    "buyerName":"","projectId":"","pinMu":"0","bidType":"0",
                    "dbselect":"bidx","kw":kw,"start_time":start,"end_time":end,
                    "timeType":"6","displayZone":"","zoneId":"","pppStatus":"0",
                    "agentName":"",
                }, timeout=20)
            except Exception:
                break
            rows = page.css("ul.vT-srch-result-list-bid li")
            if not rows:
                break
            for row in rows:
                try:
                    item = self._parse_row(row)
                    if item and self._match(item.title, local_filters):
                        items.append(item)
                except Exception:
                    continue
            time.sleep(random.uniform(2, 4))
        return items

    def _browse_list(self, keywords, cutoff):
        items = []
        urls = ["http://www.ccgp.gov.cn/cggg/dfgg/", "http://www.ccgp.gov.cn/cggg/zygg/"]
        for u in urls:
            try:
                page = self._get_page(u, timeout=20)
            except Exception:
                continue
            links = page.css("a[href]")
            cnt = 0
            for a in links:
                if cnt >= 20:
                    break
                try:
                    title = a.get_all_text(strip=True)
                except Exception:
                    title = a.css("::text").get()
                if not title or len(str(title)) < 10:
                    continue
                title_s = str(title).strip()
                href = str(a.attrib.get("href", ""))
                if href and not href.startswith("http"):
                    href = urljoin(self.BASE, href)
                if not self._match(title_s, keywords):
                    continue
                pd = self._url_date(href)
                if pd:
                    try:
                        if datetime.strptime(pd, "%Y-%m-%d") < cutoff:
                            continue
                    except ValueError:
                        pass
                else:
                    pd = datetime.now().strftime("%Y-%m-%d")
                items.append(RawTenderItem(
                    title=title_s, region="", industry="",
                    amount="详见公告", publish_date=pd, deadline="详见公告",
                    source_url=href, source_site=self.site_name,
                    raw_text=title_s,
                ))
                cnt += 1
            time.sleep(random.uniform(1, 3))
        return items

    def _match(self, title, keywords):
        if not keywords:
            return len(title) >= 15
        skip = ["首页", "下一页", "上一页", "登录", "注册", "返回"]
        if any(w in title for w in skip):
            return False
        if len(title) < 10:
            return False
        if len(keywords) == 1:
            # 只有一个关键词: 直接匹配
            kw = keywords[0]
            if kw in PROVINCE_CITIES:
                return any(c in title for c in [kw] + PROVINCE_CITIES[kw])
            return kw in title
        # 多关键词: 分类AND匹配
        # 地区类关键词 (含城市扩展): 至少命中一个
        # 行业类关键词: 至少命中一个
        region_hit = False
        industry_hit = False
        has_region_kw = False
        has_industry_kw = False
        for kw in keywords:
            if not kw:
                continue
            if kw in PROVINCE_CITIES:
                has_region_kw = True
                cities = [kw] + PROVINCE_CITIES[kw]
                if any(c in title for c in cities):
                    region_hit = True
            else:
                has_industry_kw = True
                if kw in title:
                    industry_hit = True
                # 复合词部分匹配: 教育装备 -> 也检查 教育
                elif len(kw) >= 3:
                    for i in range(2, len(kw)):
                        if kw[:i] in title:
                            industry_hit = True
                            break
        if has_region_kw and has_industry_kw:
            return region_hit and industry_hit
        elif has_region_kw:
            return region_hit
        else:
            return industry_hit

    def _parse_row(self, row):
        links = row.css("a")
        if not links:
            return None
        try:
            title = " ".join(str(links[0].get_all_text(strip=True)).split())
        except Exception:
            title = links[0].css("::text").get()
        href = links[0].attrib.get("href", "")
        if href and not href.startswith("http"):
            href = urljoin(self.BASE, href)
        if not title or len(str(title)) < 4:
            return None
        try:
            rt = row.get_all_text(strip=True)
        except Exception:
            rt = str(title)
        pub = self._re_date(rt) or self._url_date(href) or datetime.now().strftime("%Y-%m-%d")
        return RawTenderItem(
            title=str(title).strip(), region="", industry="",
            amount=self._re_amount(rt) or "详见公告",
            publish_date=pub, deadline="详见公告",
            source_url=href, source_site=self.site_name,
            raw_text=rt,
        )

    def _dedup(self, items):
        seen = set()
        out = []
        for i in items:
            k = i.source_url or i.title
            if k not in seen:
                seen.add(k)
                out.append(i)
        return out

    def _re_date(self, t):
        m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", t)
        if m:
            return m.group(1).replace("年","-").replace("月","-").replace("/","-").replace(".","-")
        return None

    def _url_date(self, url):
        m = re.search(r"/(\d{6})/t(\d{8})_", url)
        if m:
            d = m.group(2)
            return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        return None

    def _re_amount(self, t):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:万元|万|亿元|亿)", t)
        if m:
            a = float(m.group(1))
            if "亿" in m.group(0):
                a *= 10000
            return f"约{a:.0f}万元"
        return None
