"""从列表页 / 首页收集文章链接。"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src import config

# 正文页常见路径：…/2026/05-07/10616687.shtml 或 …/shipin/…/news….shtml 等
_ARTICLE_PATH = re.compile(r"/\d{4}/\d{2}-\d{2}/[^/]+\.shtml$", re.IGNORECASE)


def _host_ok(netloc: str) -> bool:
    host = netloc.lower().split("@")[-1]
    if ":" in host:
        host = host.split(":")[0]
    return any(host == s or host.endswith("." + s) for s in config.ALLOWED_HOST_SUFFIXES)


def parse_article_links(html: str, base_url: str) -> list[str]:
    """从 HTML 中解析出疑似文章详情页 URL（去重、保序）。"""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    out: list[str] = []

    for a in soup.find_all("a", href=True):
        raw = a["href"].strip()
        if not raw or raw.startswith("#") or raw.lower().startswith("javascript:"):
            continue
        abs_url = urljoin(base_url, raw)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _host_ok(parsed.netloc):
            continue
        path = parsed.path or ""
        if not _ARTICLE_PATH.search(path):
            continue
        # 去掉 fragment，统一 https
        normalized = parsed._replace(fragment="", scheme="https").geturl()
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def parse_hub_links(html: str, base_url: str, *, limit: int = 40) -> list[str]:
    """频道 / 栏目聚合页链接（用于 --max-pages 时多抓几页列表）。"""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    out: list[str] = []

    for a in soup.find_all("a", href=True):
        if len(out) >= limit:
            break
        raw = a["href"].strip()
        if not raw or raw.startswith("#") or raw.lower().startswith("javascript:"):
            continue
        abs_url = urljoin(base_url, raw)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _host_ok(parsed.netloc):
            continue
        path = (parsed.path or "").lower()
        if not path.endswith(".shtml"):
            continue
        if _ARTICLE_PATH.search(path):
            continue
        if "channel.chinanews.com.cn" not in parsed.netloc.lower():
            continue
        if "/cns/cl/" not in path and not re.match(r"^/u/[^/]+\.shtml$", path):
            continue
        normalized = parsed._replace(fragment="", scheme="https").geturl()
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out
