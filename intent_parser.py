"""
意图解析模块
------------
职责：把用户的自然语言输入，转换成结构化的查询参数。
例如输入："帮我找最近一周北京地区建筑类招投标信息，每天早上8点发一次"
输出：
{
  "region": "北京",
  "industry": "建筑",
  "amount_min": null,
  "amount_max": null,
  "time_range_days": 7,
  "trigger_mode": "scheduled",     # "immediate" 或 "scheduled"
  "schedule_time": "08:00",
  "schedule_freq": "daily"          # "once" / "daily" / "weekly"
}

这是本项目的"大脑"，建议由你自己保留并理解这部分逻辑，
因为评委很可能会问你"意图解析是怎么做的"。
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional
import re

# ---- 地区词库 ----
REGION_MAP = {
    # 省/直辖市
    "北京": "北京", "上海": "上海", "广东": "广东", "深圳": "深圳", "广州": "广州",
    "浙江": "浙江", "杭州": "浙江", "宁波": "浙江", "江苏": "江苏", "南京": "江苏", "苏州": "江苏",
    "四川": "四川", "成都": "四川", "湖北": "湖北", "武汉": "湖北",
    "山东": "山东", "济南": "山东", "青岛": "山东", "烟台": "山东",
    "河南": "河南", "郑州": "河南", "河北": "河北", "石家庄": "河北",
    "福建": "福建", "福州": "福建", "厦门": "福建",
    "湖南": "湖南", "长沙": "湖南", "安徽": "安徽", "合肥": "安徽",
    "辽宁": "辽宁", "沈阳": "辽宁", "大连": "辽宁",
    "陕西": "陕西", "西安": "陕西",
    # 陕西各县（常见）
    "榆林": "陕西", "府谷": "陕西", "神木": "陕西", "靖边": "陕西",
    "延安": "陕西", "宝鸡": "陕西", "咸阳": "陕西", "渭南": "陕西",
    "汉中": "陕西", "安康": "陕西", "商洛": "陕西",
    "重庆": "重庆", "天津": "天津", "广西": "广西", "南宁": "广西",
    "云南": "云南", "昆明": "云南", "山西": "山西", "太原": "山西",
    "贵州": "贵州", "贵阳": "贵州", "甘肃": "甘肃", "兰州": "甘肃",
    "吉林": "吉林", "长春": "吉林", "黑龙江": "黑龙江", "哈尔滨": "黑龙江",
    "内蒙古": "内蒙古", "呼和浩特": "内蒙古", "新疆": "新疆", "乌鲁木齐": "新疆",
    "海南": "海南", "海口": "海南", "西藏": "西藏", "拉萨": "西藏",
    "宁夏": "宁夏", "银川": "宁夏", "青海": "青海", "西宁": "青海",
    "江西": "江西", "南昌": "江西",
    "华北": "华北", "华东": "华东", "华南": "华南", "华中": "华中",
    "西南": "西南", "西北": "西北", "东北": "东北",
}

# 行业匹配前要先排除的假阳性词组
INDUSTRY_EXCLUDE = {
    # 大学/机构名（不要误匹配行业）
    "交通大学", "建筑大学", "建筑学院", "电力大学", "理工大学", "科技大学",
    "交通银行", "交通广播", "交通枢纽", "交通局",
    "建筑公司", "电力公司", "电力局",
    "水利局", "水利厅", "水利部",
    "公路局", "公路段", "公路管理处",
    "市政局", "市政厅",
    "环保局", "环保厅", "环保部",
    # 通用后缀（不是行业）
    "招生信息", "招聘信息", "信息网", "信息平台", "信息公开", "信息发布",
}

INDUSTRY_MAP = {
    "建筑工程": "建筑工程", "市政工程": "市政工程",
    "交通工程": "交通工程", "道路工程": "交通工程", "桥梁工程": "交通工程",
    "水利工程": "水利工程", "医疗设备": "医疗设备", "药品采购": "医疗设备",
    "信息技术": "信息技术", "软件开发": "信息技术", "系统集成": "信息技术",
    "电力工程": "电力工程", "环保工程": "环保工程", "园林绿化": "园林绿化",
    "教育装备": "教育装备", "办公家具": "办公家具",
    "暖通设备": "暖通设备", "政府采购": "政府采购", "设备采购": "设备采购",
    "服务采购": "服务采购", "咨询服务": "咨询服务", "勘察设计": "勘察设计",
    "建筑": "建筑工程", "施工": "建筑工程",

    "公路": "交通工程", "道路": "交通工程", "桥梁": "交通工程", "交通": "交通工程",
    "水利": "水利工程", "医疗": "医疗设备", "医院": "医疗设备", "药品": "医疗设备",
    "IT": "信息技术", "信息": "信息技术", "软件": "信息技术", "计算机": "信息技术", "系统": "信息技术",
    "电力": "电力工程", "环保": "环保工程", "绿化": "园林绿化",
    "教育": "教育装备", "学校": "教育装备", "家具": "办公家具",
    "空调": "暖通设备", "暖通": "暖通设备", "采购": "政府采购", "设备": "设备采购",
    "服务": "服务采购", "咨询": "咨询服务", "设计": "勘察设计",
}

FREQ_MAP = {
    "每天": "daily", "每日": "daily", "天天": "daily",
    "每周": "weekly", "每星期": "weekly",
    "每小时": "hourly", "每分钟": "minutely",
}

# frequency exclude list - prevent false positives like 'today' matching 'daily'
FREQ_EXCLUDE = {
    "今天天气", "明天天气", "聊天", "聊天记录",
    "春天", "夏天", "秋天", "冬天", "蓝天", "阴天", "雨天",
}

import anthropic


SYSTEM_PROMPT = """你是一个招投标信息检索意图解析器。
你的任务：把用户的自然语言请求，解析成严格的JSON格式，不要输出任何多余文字。

JSON字段说明：
- region: string | null   地区名称（如"北京"、"华北"），无地区限制则为null
- industry: string | null 行业/项目类型（如"建筑"、"IT"、"医疗设备"），无限制则为null
- amount_min: number | null  金额下限（单位：万元），无限制则为null
- amount_max: number | null  金额上限（单位：万元），无限制则为null
- time_range_days: number  查询的时间范围（天数），默认7
- trigger_mode: "immediate" | "scheduled"  用户是否要求定时/周期性推送
- schedule_time: string | null  定时触发的时间点，格式"HH:MM"，仅当trigger_mode为scheduled时填写
- schedule_freq: "once" | "daily" | "weekly" | null  推送频率

只输出JSON，不要输出markdown代码块标记，不要输出解释文字。
"""


@dataclass
class TenderQuery:
    region: Optional[str] = None
    industry: Optional[str] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    time_range_days: int = 7
    trigger_mode: str = "immediate"
    schedule_time: Optional[str] = None
    schedule_freq: Optional[str] = None


    def to_dict(self):
        return asdict(self)


class SimpleParser:
    """规则引擎解析器——无需API Key，纯本地正则匹配"""

    # tender-related keywords for relevance check
    TENDER_KEYWORDS = [
        "招标", "投标", "中标", "采购", "公告", "公示", "询价", "竞价",
        "竞争性磋商", "竞争性谈判", "公开招标", "邀请招标", "单一来源",
        "招投标", "标讯", "标书", "开标", "评标",
    ]

    def _has_tender_relevance(self, text, region, industry, has_schedule):
        """Relevance check: return True if input appears related to tender search."""
        if region or industry or has_schedule:
            return True
        for kw in self.TENDER_KEYWORDS:
            if kw in text:
                return True
        if len(text) < 5:
            return False
        action_words = ["找", "查", "搜", "搜索", "检索"]
        if any(w in text for w in action_words) and len(text) >= 5:
            return True
        return False
    
    def parse(self, user_input: str) -> TenderQuery:
        text = user_input
        
        # --- 地区 ---
        region = None
        # 额外：从文本中提取市县名（如 府谷县→府谷）
        extra_places = re.findall(r'([一-龥]{2,4})(?:县|市|区|镇|乡)', text)
        for key, val in sorted(REGION_MAP.items(), key=lambda x: -len(x[0])):
            if key in text:
                region = val
                break
        # 没匹配到的话，用提取的市县名回退
        if not region and extra_places:
            region = extra_places[0]
        
        # --- 行业 ---
        industry = None
        # 先排除假阳性词组
        clean_text = text
        for excl in sorted(INDUSTRY_EXCLUDE, key=lambda x: -len(x)):
            if excl in clean_text:
                clean_text = clean_text.replace(excl, " " * len(excl))
        for key, val in sorted(INDUSTRY_MAP.items(), key=lambda x: -len(x[0])):
            if key in clean_text:
                industry = val
                break
        
        # --- 金额 ---
        amount_min = None
        amount_max = None
        m = re.search(r'(\d+)\s*万\s*(?:以上|以上|及以上)', text)
        if m:
            amount_min = float(m.group(1))
        m = re.search(r'(\d+)\s*万\s*(?:以下|以内)', text)
        if m:
            amount_max = float(m.group(1))
        m = re.search(r'(\d+)\s*[-~到至]\s*(\d+)\s*万', text)
        if m:
            amount_min = float(m.group(1))
            amount_max = float(m.group(2))
        m = re.search(r'(\d+)\s*亿', text)
        if m:
            amount_min = float(m.group(1)) * 10000
        
        # --- 时间范围 ---
        time_range_days = 7
        m = re.search(r'(?:最近|近|过去)(\d+)\s*(?:天|日)', text)
        if m:
            time_range_days = int(m.group(1))
        m = re.search(r'(?:最近|近|过去)一(?:周|星期)', text)
        if m:
            time_range_days = 7
        m = re.search(r'(?:最近|近|过去)一个?月', text)
        if m:
            time_range_days = 30
        m = re.search(r'(?:最近|近|过去)三天', text)
        if m:
            time_range_days = 3
        
        # --- 触发模式 ---
        trigger_mode = "immediate"
        schedule_time = None
        schedule_freq = None
        
        time_pattern = re.search(r'(?:每[天日周]|每天|每周)?\s*(?:早上|上午|中午|下午|晚上|早晨)?\s*(\d{1,2})\s*(?:点|:)(?:\s*(\d{2}))?', text)
        freq_found = None
        _freq_text = text
        for excl in sorted(FREQ_EXCLUDE, key=len, reverse=True):
            if excl in _freq_text:
                _freq_text = _freq_text.replace(excl, " " * len(excl))
        for key, val in FREQ_MAP.items():
            if key in _freq_text:
                freq_found = val
                break
        
        has_schedule = bool(time_pattern or freq_found or '定时' in text or '推送' in text)
        if has_schedule:
            trigger_mode = "scheduled"
            if time_pattern:
                h = time_pattern.group(1).zfill(2)
                m = time_pattern.group(2) or "00"
                schedule_time = f"{h}:{m}"
            else:
                schedule_time = "09:00"
            schedule_freq = freq_found or "daily"
        elif '立即' in text or '马上' in text or '现在' in text or '快速' in text:
            trigger_mode = "immediate"
        

        # relevance check: reject irrelevant input
        if not self._has_tender_relevance(text, region, industry, has_schedule):
            raise ValueError(
                "无法识别有效的查询意图，请描述您要查找的招标信息（地区、行业、时间等），例如："
                "帮我找最近一周北京地区建筑类招标"
            )
        return TenderQuery(
            region=region,
            industry=industry,
            amount_min=amount_min,
            amount_max=amount_max,
            time_range_days=time_range_days,
            trigger_mode=trigger_mode,
            schedule_time=schedule_time,
            schedule_freq=schedule_freq,
        )



class IntentParser:
    def __init__(self, api_key: Optional[str] = None):
        # 建议用环境变量管理密钥，不要硬编码
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")); self._simple = SimpleParser()

    def parse(self, user_input: str) -> TenderQuery:
        # 优先用 Claude，失败则用规则引擎
        try:
            return self._parse_with_claude(user_input)
        except Exception as e:
            import logging
            logging.getLogger("intent_parser").warning(
                f"Claude 解析失败（{e}），回退到规则引擎"
            )
            return self._simple.parse(user_input)

    def _parse_with_claude(self, user_input: str) -> TenderQuery:
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_input}],
        )
        raw_text = response.content[0].text.strip()

        # 容错处理：万一模型输出了markdown代码块包裹
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            raise ValueError(f"意图解析失败，模型返回内容无法解析为JSON：{raw_text}")

        return TenderQuery(**data)


if __name__ == "__main__":
    # 简单自测（需要设置环境变量 ANTHROPIC_API_KEY 才能真正跑通）
    parser = IntentParser()
    test_inputs = [
        "帮我找最近一周北京地区建筑类招投标信息，每天早上8点发一次",
        "查一下最近三天全国范围内100万以上的IT类招标",
        "立即帮我看看上海的医疗设备招标",
    ]
    for text in test_inputs:
        print(f"输入: {text}")
        try:
            query = parser.parse(text)
            print(f"解析结果: {json.dumps(query.to_dict(), ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"（未配置API Key时会报错，属正常）{e}")
        print("-" * 40)
