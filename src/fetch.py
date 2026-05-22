"""HTTP 获取封装：超时、简单重试。"""

from __future__ import annotations

import time
from typing import Optional

import httpx

from src import config


def get_text(url: str, *, referer: Optional[str] = None) -> str:
    """GET 页面并返回解码后的 HTML 文本。"""
    headers = dict(config.BASE_HEADERS)
    if referer:
        headers["Referer"] = referer

    last_exc: Optional[Exception] = None
    for attempt in range(1, config.DEFAULT_MAX_RETRIES + 1):
        try:
            with httpx.Client(
                timeout=config.DEFAULT_TIMEOUT_SEC,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except (httpx.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt >= config.DEFAULT_MAX_RETRIES:
                break
            time.sleep(0.6 * attempt)
    assert last_exc is not None
    raise last_exc
