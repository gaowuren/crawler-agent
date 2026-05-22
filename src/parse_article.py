"""从文章详情页抽取标题、时间、作者、编辑、来源、正文段落。"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag


def _text(el: Tag | NavigableString | None) -> str:
    if el is None:
        return ""
    if isinstance(el, NavigableString):
        return str(el).strip()
    return el.get_text(strip=True)


def _strip_prefixes(text: str, *prefixes: str) -> str:
    t = text.strip()
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p) :].strip()
    return t


def _clean_paragraphs(left_zw: Tag) -> list[str]:
    paragraphs: list[str] = []
    for p in left_zw.find_all("p"):
        t = p.get_text(" ", strip=True)
        t = re.sub(r"\s+", " ", t)
        if t:
            paragraphs.append(t)
    return paragraphs


def parse_article(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one("h1.content_left_title") or soup.select_one(
        "#second-title h1"
    )
    title = _text(title_el) or ""

    pub_el = soup.select_one("#pubtime_baidu")
    published_at = _text(pub_el)
    if not published_at:
        time_div = soup.select_one(".content_left_time")
        if time_div:
            published_at = time_div.get_text(" ", strip=True)
            published_at = re.split(r"\s*来源\s*:", published_at)[0].strip()

    author = ""
    author_el = soup.select_one("#author_baidu")
    if author_el:
        author = _strip_prefixes(_text(author_el), "作者：", "作者:")

    editor = ""
    editor_el = soup.select_one("#editor_baidu")
    if editor_el:
        editor = _strip_prefixes(_text(editor_el), "责任编辑：", "责任编辑:")
    if not editor:
        editor_inp = soup.select_one("input#editorname")
        if editor_inp and editor_inp.get("value"):
            editor = str(editor_inp["value"]).strip()

    source = ""
    source_el = soup.select_one("#source_baidu")
    if source_el:
        source = _strip_prefixes(_text(source_el), "来源：", "来源:")
    if not source:
        src_a = soup.select_one(".content_left_time a.source")
        if src_a:
            source = _text(src_a)

    body_el = soup.select_one("div.left_zw")
    paragraphs: list[str] = []
    if body_el and isinstance(body_el, Tag):
        paragraphs = _clean_paragraphs(body_el)

    body = "\n\n".join(paragraphs)

    return {
        "url": url,
        "title": title,
        "published_at": published_at,
        "author": author,
        "editor": editor,
        "source": source,
        "paragraphs": paragraphs,
        "body": body,
    }
