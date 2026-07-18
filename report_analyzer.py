# -*- coding: utf-8 -*-
"""
report_analyzer.py - AI 分析模块
输入：抓取结果列表
输出：统计数据 + AI 分析文本 + AI 建议
"""
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict



def _parse_amount_wan(amount_str):
    """解析金额字符串为万元数值。兼容: '约1200万元' '1200万' '3.5亿元' '500万元'"""
    import re
    if not amount_str:
        return None
    # 亿元
    m = re.search(r"([\d.]+)\s*亿", amount_str)
    if m:
        return float(m.group(1)) * 10000
    # 万元
    m = re.search(r"([\d.]+)\s*万", amount_str)
    if m:
        return float(m.group(1))
    # 纯数字（视为万元）
    try:
        return float(amount_str.strip())
    except:
        return None


def analyze(records, query_desc: str = "", elapsed_sec: float = 0) -> Dict:
    """对抓取结果做全面分析，返回结构化数据"""
    
    total = len(records)
    if not total:
        return _empty_result(query_desc)

    sources = Counter(r.source_site for r in records)
    regions = Counter(r.region for r in records if r.region)
    industries = Counter(r.industry for r in records if r.industry)

    # 金额分层
    amount_buckets = {"<100万": 0, "100-500万": 0, "500万以上": 0, "未公开": 0}
    for r in records:
        num = _parse_amount_wan(r.amount)
        if num is not None:
            if num < 100:
                amount_buckets["<100万"] += 1
            elif num < 500:
                amount_buckets["100-500万"] += 1
            else:
                amount_buckets["500万以上"] += 1
        else:
            amount_buckets["未公开"] += 1

    # 时间分布
    dates = [r.publish_date for r in records if r.publish_date]
    recent_3d = sum(1 for d in dates if _days_ago(d) <= 3)
    recent_7d = sum(1 for d in dates if _days_ago(d) <= 7)

    # 生成 AI 分析文本
    ai_summary = _generate_ai_summary(total, sources, regions, industries, 
                                       amount_buckets, recent_3d, recent_7d, query_desc)

    # AI 建议
    ai_suggestions = _generate_suggestions(records, industries, amount_buckets, recent_3d)

    return {
        "total": total,
        "query_desc": query_desc,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "report_id": f"TA-{datetime.now().strftime('%Y%m%d')}-{total:03d}",
        "elapsed_sec": elapsed_sec,
        "sources": dict(sources.most_common()),
        "regions": dict(regions.most_common()),
        "industries": dict(industries.most_common()),
        "amount_buckets": amount_buckets,
        "recent_3d": recent_3d,
        "recent_7d": recent_7d,
        "ai_summary": ai_summary,
        "ai_suggestions": ai_suggestions,
    }


def _empty_result(query_desc):
    return {
        "total": 0,
        "query_desc": query_desc,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "report_id": f"TA-{datetime.now().strftime('%Y%m%d')}-000",
        "elapsed_sec": 0,
        "sources": {},
        "regions": {},
        "industries": {},
        "amount_buckets": {},
        "recent_3d": 0,
        "recent_7d": 0,
        "ai_summary": "本次未检索到符合条件的招标信息。",
        "ai_suggestions": [],
    }


def _days_ago(date_str):
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (datetime.now() - d).days
    except:
        return 999


def _generate_ai_summary(total, sources, regions, industries, amount_buckets, 
                          recent_3d, recent_7d, query_desc):
    """基于规则生成 AI 分析文本"""
    lines = []
    
    lines.append(f"本次查询覆盖 {len(sources)} 个招投标信息平台，共获取 {total} 条有效项目信息。")
    
    # 行业洞察
    if industries:
        top_ind = industries.most_common(3)
        ind_names = "、".join(k for k, _ in top_ind)
        lines.append(f"从行业分布来看，{ind_names}类项目占比较高，是当前招标市场的活跃领域。")
    
    # 金额洞察
    high_val = amount_buckets.get("500万以上", 0)
    mid_val = amount_buckets.get("100-500万", 0)
    if high_val:
        lines.append(f"其中预算超过500万元的项目有 {high_val} 个，具备较高的关注价值。")
    elif mid_val:
        lines.append(f"项目预算主要集中在100-500万元区间（{mid_val}个），整体规模适中。")
    
    # 时效性
    if recent_3d:
        lines.append(f"近3天内新发布的项目有 {recent_3d} 个，建议优先关注这些时效性较强的招标信息。")
    
    # 地区
    if regions:
        top_reg = regions.most_common(1)[0]
        lines.append(f"从地区来看，{top_reg[0]} 地区采购活跃度最高（{top_reg[1]}条），是当前关注重点。")
    
    # 综合建议一句
    if high_val or mid_val or recent_3d:
        lines.append("建议投标方重点关注预算300万元以上、发布时间在3天以内的项目，提前准备投标材料。")
    
    return "\n\n".join(lines)


def _generate_suggestions(records, industries, amount_buckets, recent_3d):
    """生成 AI 建议列表"""
    suggestions = []
    
    if recent_3d:
        suggestions.append(f"近3天内有 {recent_3d} 条新发布项目，建议优先关注并及时下载招标文件。")
    else:
        suggestions.append("近期新发布项目较少，可适当扩大查询时间范围或关注即将截止的项目。")
    
    high_count = amount_buckets.get("500万以上", 0)
    if high_count:
        suggestions.append(f"有 {high_count} 个项目预算超过500万元，建议组建专项投标团队跟进。")
    
    if industries:
        top_ind = industries.most_common(1)[0][0]
        suggestions.append(f"「{top_ind}」行业当前招标数量较多，建议关注竞争态势和评分标准变化。")
    
    suggestions.append("建议关注各平台公告更新频率，设置定时推送以确保不遗漏新增项目。")
    suggestions.append("未来一周预计招标市场将保持当前活跃度，建议提前做好投标规划。")
    
    return suggestions


def analyze_with_llm(records, query_desc="", api_key=None):
    """可选：使用LLM生成更深入的AI分析"""
    # 先用规则引擎生成基础数据
    result = analyze(records, query_desc)
    
    if not api_key or not records:
        return result
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        brief = _build_context_for_llm(records, result)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system="你是一位招投标分析专家。根据提供的招标数据，生成专业、简洁的分析文本。语言正式但不生硬，适合放入企业报告。",
            messages=[{"role": "user", "content": brief}],
        )
        llm_text = response.content[0].text.strip()
        parts = llm_text.split("---")
        if len(parts) >= 2:
            result["ai_summary"] = parts[0].strip()
            result["ai_suggestions"] = [s.strip("- ") for s in parts[1].strip().split("\n") if s.strip()]
        else:
            result["ai_summary"] = llm_text
    except Exception:
        pass  # LLM 不可用时使用规则引擎结果
    
    return result


def _build_context_for_llm(records, stats):
    """构建给 LLM 的上下文"""
    lines = ["以下是一次招投标查询的结果摘要：", ""]
    lines.append(f"共 {stats['total']} 条记录")
    lines.append(f"数据来源：{stats['sources']}")
    lines.append(f"地区分布：{stats['regions']}")
    lines.append(f"行业分布：{stats['industries']}")
    lines.append(f"金额分布：{stats['amount_buckets']}")
    lines.append(f"近3天发布：{stats['recent_3d']} 条")
    lines.append("")
    lines.append("请生成两段内容，用「---」分隔：")
    lines.append("第一段：AI综合分析（150-200字，行业洞察+金额分析+时效性建议）")
    lines.append("第二段：3-5条具体建议（每条一行，以「- 」开头）")
    return "\n".join(lines)
