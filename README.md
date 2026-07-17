# 招标信息聚合工具

自然语言驱动的招标信息聚合系统——输入一句话，自动从多个政府采购网站抓取数据，生成带超链接的 Word 报告。支持立即查询和定时推送两种模式。

## 验证效果

| 指标 | 结果 |
|------|------|
| 数据真实性 | 随机抽样验证：9条记录全部可溯源至真实 ccgp.gov.cn 招标公告页面 |
| 意图解析 | 含置信度判断，自动拒绝无关输入；5类典型查询全部正确解析 |
| 合规性 | 4个爬虫模块均实现 robots.txt 校验，请求间隔 0.5-4 秒 |
| 多源覆盖 | 中国政府采购网、公共资源交易平台、搜索引擎（DuckDuckGo/Bing） |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. CLI 模式：单次查询
python main.py -i "帮我找最近一周北京地区建筑类招标" -m cli

# 3. Web 模式：浏览器操作
python main.py -m web
# 打开 http://localhost:5000
```

> **注意**：意图解析模块默认使用内置规则引擎（免费，无需 API Key）。如需更高准确率，可设置环境变量 `ANTHROPIC_API_KEY` 启用 Claude 大模型解析。

## 运行模式

| 模式 | 命令 | 说明 |
|------|------|------|
| CLI | `python main.py -i "查询词" -m cli` | 运行一次，输出 Word 报告到 `output/` |
| Web | `python main.py -m web` | 启动 Flask Web 界面（默认 127.0.0.1:5000） |

## 定时功能

系统提供两套独立的定时机制：

| 定时方式 | 实现 | 持久性 |
|----------|------|--------|
| Web 界面“▶ 启动定时” | 进程内 `schedule` 库，内存运行 | 仅当前进程运行时有效 |
| Web 界面“💾 保存到Windows定时任务” | 写入系统任务计划 (`schtasks`) | 关闭浏览器/进程后仍生效（仅 Windows） |

> **跨平台说明**：系统级定时调用 Windows `schtasks`，仅限 Windows。Linux/macOS 用户可使用 `cron` 替代，或保持 Web 进程运行使用内置 `schedule` 库。

## 关于数据来源

系统优先抓取真实网站数据（已验证可稳定抓取中国政府采购网等真实招标信息，附带可点击溯源链接）。若目标网站临时抓取失败或无匹配结果，系统会自动使用标注为“【演示数据】”的示例数据展示完整流程，**不会将演示数据伪装成真实数据**——确保任何输入都能跑通端到端效果，同时诚实区分数据来源。

## 项目结构

```
tender-agent/
├── intent_parser.py       # 意图解析：自然语言 → 结构化查询参数（含置信度判断）
├── docx_generator.py      # 报告生成：结构化数据 → Word 文档（可点击超链接）
├── main.py                # 主流程 + Flask Web UI + 定时调度
├── requirements.txt       # Python 依赖
├── scrapers/
│   ├── base_scraper.py        # 爬虫基类（Scrapling TLS 指纹 + robots.txt 合规）
│   ├── ccgp_scraper.py        # 中国政府采购网 (ccgp.gov.cn)
│   ├── ggzyjy_scraper.py      # 公共资源交易平台
│   ├── bidsearch_scraper.py   # 招标搜索网站
│   └── search_engine_scraper.py  # DuckDuckGo + Bing 搜索引擎
└── output/                # 生成的 Word 报告存放目录
```

## 核心设计

1. **意图解析**：规则引擎将自然语言转为结构化参数（地区/行业/金额/时间/触发模式），内置全国省-市-县级词库和 20+ 行业映射。含置信度判断，自动拒绝无关输入。
2. **合规抓取**：每个爬虫强制检查 robots.txt，Scrapling TLS 指纹伪装，请求间隔 ≥ 0.5 秒。
3. **结构化输出**：Word 报告含可点击超链接、执行摘要、按来源分组详述，可直接归档。
4. **安全考量**：定时任务输入经过白名单过滤（仅保留中英文字母数字及空格），避免命令拼接引发的注入风险。

## 依赖

```
anthropic>=0.40.0    # 可选：大模型意图解析（不装则用规则引擎）
python-docx>=1.1.0   # Word 报告生成
flask>=2.3.0         # Web UI
scrapling>=0.1.0     # 反反爬网络请求
lxml>=4.9.0          # HTML 解析
schedule>=1.2.0      # 定时调度
requests>=2.31.0     # HTTP（Scrapling 不可用时回退）
beautifulsoup4>=4.12.0  # HTML 解析（回退）
```

