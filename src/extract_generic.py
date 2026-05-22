"""任意站点单页 HTML 的通用正文抽取（trafilatura）。"""

from __future__ import annotations

import re
from typing import Any

from trafilatura import extract, metadata


def extract_any_article(html: str, url: str) -> dict[str, Any]:
    """与 parse_article 字段对齐；无法解析的字段留空字符串。"""
    doc = metadata.extract_metadata(html, default_url=url)
    text = extract(html, url=url) or ""

    title = ""
    author = ""
    published_at = ""
    source = ""
    if doc is not None:
        title = (doc.title or "").strip()
        raw_author = doc.author
        if isinstance(raw_author, (list, tuple)):
            author = ", ".join(str(x).strip() for x in raw_author if x)
        else:
            author = (str(raw_author).strip() if raw_author else "")
        if doc.date:
            published_at = str(doc.date).strip()
        source = (doc.sitename or doc.hostname or "").strip()

    paragraphs: list[str] = []
    if text:
        chunks = re.split(r"\n\s*\n", text.strip())
        paragraphs = [re.sub(r"\s+", " ", c).strip() for c in chunks if c.strip()]
        if not paragraphs:
            paragraphs = [re.sub(r"\s+", " ", text).strip()]

    body = "\n\n".join(paragraphs)

    return {
        "url": url,
        "title": title,
        "published_at": published_at,
        "author": author,
        "editor": "",
        "source": source,
        "paragraphs": paragraphs,
        "body": body,
        "parser": "generic",
    }
