# 给编程 Agent 的任务说明

## 项目背景
这是"2026 AI先锋未来人才大赛"超聚变命题的参赛demo：一个自然语言驱动的招投标信息聚合工具。
架构已经搭好，核心难点（意图解析、Word生成）已经实现并测试通过，现在需要你完成"网站抓取"和"整体串联"部分。

## 已完成的部分（不需要你改动，除非发现bug）
- `intent_parser.py` —— 自然语言转结构化查询参数
- `docx_generator.py` —— 结构化数据转Word报告（已测试可用）
- `scrapers/base_scraper.py` —— 爬虫统一接口的抽象基类

## 需要你完成的任务

### 任务1：实现2-3个网站的爬虫（优先级最高）
- 挑选公开、无需登录、对爬虫友好的招投标信息网站（例如政府采购网、地方公共资源交易中心官网等公示信息页面）
- 每个网站新建一个文件 `scrapers/xxx_scraper.py`，继承 `BaseScraper`，实现 `fetch()` 方法
- 用 `requests` + `BeautifulSoup` 解析网页，提取：标题、地区、行业、金额、发布日期、截止日期、详情链接
- **务必调用 `check_robots_allowed()` 检查合规性，并设置请求间隔 >= 2秒**
- 如果某网站有反爬（如需要验证码、强登录），换一个网站，不要硬破解

### 任务2：主流程串联 main.py
需要实现：
```
python main.py --input "帮我找最近一周北京地区建筑类招投标信息" --mode cli
```
流程：
1. 调用 `IntentParser.parse()` 解析用户输入
2. 遍历已注册的所有scraper，调用 `fetch()` 抓取数据
3. 对抓取结果做去重（按source_url去重）
4. 调用 `docx_generator.generate_report()` 生成Word文件，保存到 `output/` 目录
5. 打印生成的文件路径

### 任务3：定时任务支持
- 用 `schedule` 库（`pip install schedule --break-system-packages`）实现周期性触发
- 当 `IntentQuery.trigger_mode == "scheduled"` 时，按 `schedule_time` 和 `schedule_freq` 注册定时任务
- 当 `trigger_mode == "immediate"` 时，立即执行一次

### 任务4（可选，时间充裕再做）：简单Web UI
- 用 Flask 或 Streamlit 做一个最简单的网页界面：一个输入框 + 一个"生成"按钮 + 下载链接
- 不需要美化，能跑通demo即可

## 验收标准（提交前自检）
- [ ] 跑一次完整流程，真的能生成一份包含真实抓取数据的Word文档
- [ ] 至少测试3种不同的自然语言输入，确认意图解析基本准确
- [ ] 代码里没有硬编码的API Key（用环境变量）
- [ ] README里写清楚如何安装依赖、如何运行

## 边界提醒
- 不要抓取需要登录/付费/明确禁止爬虫的网站
- 不要做高频请求，不要绕过反爬机制
- 遇到某个网站解析不出来，先跳过换下一个，不要卡在一个网站上花太多时间——demo阶段"能跑通"比"覆盖全"更重要
