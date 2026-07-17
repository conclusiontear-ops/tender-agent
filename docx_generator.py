
class TenderRecord:
    def __init__(self, title, region, industry, amount, publish_date, deadline, source_url, source_site, summary=""):
        self.title = title
        self.region = region
        self.industry = industry
        self.amount = amount
        self.publish_date = publish_date
        self.deadline = deadline
        self.source_url = source_url
        self.source_site = source_site
        self.summary = summary

"""
Word 文档生成模块
------------------
职责：把抓取到的招投标信息（结构化列表），渲染成一份规范的Word文档。

依赖：pip install python-docx --break-system-packages
"""

from datetime import datetime
from typing import List, Dict
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
def _add_hyperlink(paragraph, url, text):
    """在段落中添加可点击的超链接"""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    from docx.oxml.shared import OxmlElement, qn
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "0563C1")
    rPr.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    rSz = OxmlElement("w:sz")
    rSz.set(qn("w:val"), "18")
    rPr.append(rSz)
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return paragraph




from collections import Counter
from datetime import datetime
from typing import List, Dict
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
def _add_hyperlink(paragraph, url, text):
    """在段落中添加可点击的超链接"""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    from docx.oxml.shared import OxmlElement, qn
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "0563C1")
    rPr.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    rSz = OxmlElement("w:sz")
    rSz.set(qn("w:val"), "18")
    rPr.append(rSz)
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return paragraph



def generate_report(records, query_desc, output_path):
    """增强版: 执行摘要 + 按来源分组详述"""
    doc = Document()

    # ---- 标题 ----
    title = doc.add_heading("招标信息汇总报告", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---- 执行摘要 ----
    meta = doc.add_paragraph()
    meta.add_run(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n").font.size = Pt(10)
    meta.add_run(f"查询条件: {query_desc}\n").font.size = Pt(10)
    meta.add_run(f"共检索到 {len(records)} 条信息\n").font.size = Pt(10)

    if not records:
        doc.add_paragraph("本次未检索到符合条件的招标信息。")
        doc.save(output_path)
        return output_path

    # 按来源分组统计
    sources = Counter(r.source_site for r in records)
    doc.add_heading("数据来源", level=1)
    src_para = doc.add_paragraph()
    for src, cnt in sources.most_common():
        src_para.add_run(f"  {src}: {cnt} 条\n").font.size = Pt(10)

    # 最新几条重点展示
    doc.add_heading("重点推荐", level=1)
    latest = sorted(records, key=lambda r: r.publish_date, reverse=True)[:5]
    for idx, rec in enumerate(latest, 1):
        p = doc.add_paragraph()
        p.add_run(f"{idx}. {rec.title}\n").font.bold = True
        p.add_run(f"   地区: {rec.region} | 行业: {rec.industry} | 金额: {rec.amount} | 日期: {rec.publish_date}\n").font.size = Pt(9)
        if rec.source_url and rec.source_url.startswith("http"):
                _add_hyperlink(p, rec.source_url, f"   链接: {rec.source_url}")

    doc.add_paragraph()

    # ---- 汇总表格 ----
    doc.add_heading("全部信息列表", level=1)
    table = doc.add_table(rows=1, cols=6)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, h in enumerate(["项目名称", "地区", "行业", "预算/金额", "发布日期", "截止日期"]):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True

    for rec in records:
        row = table.add_row().cells
        # 项目名称做成可点击链接
        if rec.source_url and rec.source_url.startswith("http"):
            p = row[0].paragraphs[0]
            p.clear()
            _add_hyperlink(p, rec.source_url, rec.title)
        else:
            row[0].text = rec.title
        row[1].text = rec.region
        row[2].text = rec.industry
        row[3].text = rec.amount
        row[4].text = rec.publish_date
        row[5].text = rec.deadline

    doc.add_paragraph()

    # ---- 按来源详述 ----
    doc.add_heading("详情与来源", level=1)
    # 按来源分组
    from collections import defaultdict
    by_source = defaultdict(list)
    for rec in records:
        by_source[rec.source_site].append(rec)

    for src_name, src_records in by_source.items():
        doc.add_heading(f"来源: {src_name}", level=2)
        for idx, rec in enumerate(src_records, 1):
            doc.add_heading(f"{idx}. {rec.title}", level=3)
            p = doc.add_paragraph()
            p.add_run(f"地区: {rec.region} | 行业: {rec.industry}\n").font.size = Pt(10)
            p.add_run(f"金额: {rec.amount} | 日期: {rec.publish_date} | 截止: {rec.deadline}\n").font.size = Pt(10)
            if rec.source_url and rec.source_url.startswith("http"):
                _add_hyperlink(p, rec.source_url, f"原始链接: {rec.source_url}")
            if rec.summary:
                p.add_run(f"摘要: {rec.summary}").font.size = Pt(9)

    doc.save(output_path)
    return output_path
