# 招投标信息聚合工具（超聚变命题 Demo）

自然语言驱动的招投标信息聚合系统，支持输入一句话触发多网站抓取，
自动汇总生成 Word 报告，支持定时/立即两种触发模式。

## 快速开始
```bash
pip install -r requirements.txt --break-system-packages
export ANTHROPIC_API_KEY=你的key
python main.py --input "帮我找最近一周北京地区建筑类招投标信息" --mode cli
```

## 项目结构
```
tender-agent/
├── intent_parser.py      # 自然语言 -> 结构化查询参数
├── docx_generator.py     # 结构化数据 -> Word报告
├── scrapers/
│   └── base_scraper.py   # 爬虫统一接口
├── main.py                # 主流程（待实现）
├── AGENT_TASKS.md          # 开发任务清单
└── output/                 # 生成的Word报告存放目录
```

## 核心设计
1. **意图解析**：大模型将自然语言转为结构化参数（地区/行业/金额/时间/触发方式）
2. **合规抓取**：爬虫适配器强制检查 robots.txt，控制请求频率
3. **结构化输出**：抓取结果统一渲染为可编辑、可归档的 Word 文档
