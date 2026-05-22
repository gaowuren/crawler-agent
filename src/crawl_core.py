"""爬取编排：列表流式产出、单页抓取、中新网 / 通用解析路由。"""

from __future__ import annotations

import sys
import time
from collections import deque
from typing import Iterator
from urllib.parse import urlparse

from src import config
from src.extract_generic import extract_any_article
from src.fetch import get_text
from src.parse_article import parse_article
from src.parse_list import parse_article_links, parse_hub_links


def _host_matches(netloc: str) -> bool:
    host = netloc.lower().split("@")[-1]
    if ":" in host:
        host = host.split(":")[0]
    return any(
        host == s or host.endswith("." + s) for s in config.ALLOWED_HOST_SUFFIXES
    )


def is_chinanews_url(url: str) -> bool:
    return _host_matches(urlparse(url).netloc)


def extract_article_record(html: str, url: str) -> dict[str, object]:
    if is_chinanews_url(url):
        rec = parse_article(html, url)
        rec["parser"] = "chinanews"
        return rec
    rec = extract_any_article(html, url)
    return rec


def run_list_crawl_gen(
    start_url: str,
    *,
    max_pages: int = 1,
    max_articles: int = 10,
    interval: float = config.DEFAULT_REQUEST_INTERVAL_SEC,
) -> Iterator[dict[str, object]]:
    """从列表页 / 首页发现链接并逐篇抓取，逐条 yield（中新网专用逻辑）。"""
    list_queue: deque[str] = deque([start_url])
    list_seen: set[str] = set()
    article_urls: list[str] = []
    pages_fetched = 0

    while list_queue and pages_fetched < max_pages:
        list_url = list_queue.popleft()
        if list_url in list_seen:
            continue
        list_seen.add(list_url)
        try:
            html = get_text(list_url)
        except Exception as exc:
            print(f"[列表页失败] {list_url}: {exc}", file=sys.stderr)
            pages_fetched += 1
            time.sleep(interval)
            continue
        article_urls.extend(parse_article_links(html, list_url))
        pages_fetched += 1
        if pages_fetched < max_pages:
            for hub in parse_hub_links(html, list_url):
                if hub not in list_seen:
                    list_queue.append(hub)
        time.sleep(interval)

    seen_art: set[str] = set()
    unique_articles: list[str] = []
    for u in article_urls:
        if u not in seen_art:
            seen_art.add(u)
            unique_articles.append(u)

    n = 0
    for art_url in unique_articles:
        if n >= max_articles:
            break
        try:
            body_html = get_text(art_url, referer=start_url)
        except Exception as exc:
            print(f"[正文失败] {art_url}: {exc}", file=sys.stderr)
            time.sleep(interval)
            continue
        record = extract_article_record(body_html, art_url)
        n += 1
        yield record
        time.sleep(interval)


def run_single_article(
    url: str,
    *,
    interval: float = config.DEFAULT_REQUEST_INTERVAL_SEC,
    referer: str | None = None,
) -> dict[str, object]:
    """抓取单个 URL 对应页面并解析为一篇文章记录。"""
    body_html = get_text(url, referer=referer)
    time.sleep(interval)
    return extract_article_record(body_html, url)
