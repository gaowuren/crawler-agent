"""站点常量与默认请求配置（练手：集中改 headers / 延迟）。"""

from __future__ import annotations

import os

DEFAULT_START_URL = "https://www.chinanews.com/"
DEFAULT_REQUEST_INTERVAL_SEC = 1.5
DEFAULT_TIMEOUT_SEC = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_OUTPUT_PATH = "data/articles.jsonl"

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "spider_agent")
# 启动探测超时（毫秒），避免 Mongo 未启动时卡死 30 秒
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(
    os.environ.get("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "4000")
)

ALLOWED_HOST_SUFFIXES = (
    "chinanews.com",
    "chinanews.com.cn",
    "channel.chinanews.com.cn",
)

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SpiderAgent/1.0; "
        "+https://example.invalid/educational-use-only)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
