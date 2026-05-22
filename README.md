# spider_agent

面向个人学习的轻量爬虫项目：在网页中提交 URL，后台抓取结构化内容并写入 MongoDB；同时保留命令行导出 JSONL。

## 功能

- **Web 界面**：FastAPI + 表单，支持两种模式  
  - **单页抓取**：任意公开网页，使用 [trafilatura](https://github.com/adbar/trafilatura) 通用抽取标题、正文等  
  - **列表爬取**：中国新闻网首页/频道页，发现文章链接后批量抓取（专用 HTML 解析）
- **命令行**：`python -m src.main`，结果追加到 JSONL
- **存储**：MongoDB（`crawl_jobs` / `crawl_articles`），Docker 一键启动
- **礼貌抓取**：可配置请求间隔、失败重试

## 技术栈

| 组件 | 用途 |
|------|------|
| httpx | HTTP 请求 |
| BeautifulSoup + lxml | 中国新闻网页面解析 |
| trafilatura | 通用正文抽取 |
| FastAPI + Jinja2 | Web 与任务 API |
| pymongo | MongoDB |
| Docker Compose | 本地 MongoDB 7 |

## 项目结构

```
spider_agent/
├── docker-compose.yml
├── requirements.txt
├── templates/index.html
├── src/
│   ├── web_app.py          # Web 入口
│   ├── main.py             # CLI 入口
│   ├── crawl_core.py       # 抓取编排
│   ├── fetch.py            # HTTP 封装
│   ├── parse_list.py       # 列表页链接发现（中新网）
│   ├── parse_article.py    # 文章页解析（中新网）
│   ├── extract_generic.py  # 通用抽取
│   ├── mongo_store.py      # MongoDB 读写
│   ├── storage.py          # JSONL 写入
│   └── config.py
└── data/                   # JSONL 输出目录（本地，不入库）
```

## 快速开始

### 1. 克隆与依赖

```bash
git clone <你的仓库地址>
cd spider_agent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 启动 MongoDB

```bash
docker compose up -d
```

默认连接：`mongodb://localhost:27017`，数据库名 `spider_agent`。

可通过环境变量覆盖：

```bash
export MONGODB_URI=mongodb://localhost:27017
export MONGODB_DB=spider_agent
```

### 3. 启动 Web

```bash
uvicorn src.web_app:app --reload --host 0.0.0.0 --port 8000
```

浏览器访问：<http://127.0.0.1:8000/>

若首页提示 MongoDB 未连接，请确认容器已启动后**重启** uvicorn。

### 4. 命令行（可选）

```bash
python -m src.main --start-url https://www.chinanews.com/ --max-articles 10 --interval 1.5
```

输出默认：`data/articles.jsonl`。

## API 示例

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 提交表单页面 |
| POST | `/crawl` | 创建抓取任务 |
| GET | `/api/jobs/{job_id}` | 查询任务状态 |
| GET | `/api/jobs/{job_id}/articles` | 查询该任务下的文章 |

## 抓取结果字段

每条文章大致包含：

`url`、`title`、`published_at`、`author`、`editor`、`source`、`paragraphs`、`body`、`parser`（`chinanews` 或 `generic`）

## 合规说明

本项目仅供**个人学习**使用。请遵守目标网站 `robots.txt`、服务条款与版权规定；控制访问频率，勿用于对外数据服务或压测。

## 已知限制

- **虎扑、强 JS 站点**等需浏览器渲染或接口分析，当前静态 HTTP 方案效果有限
- **列表模式**仅适配中国新闻网 URL 规则
- 通用抽取对复杂版式页面可能标题/正文不完整

## License

MIT（练手项目，按需调整）
