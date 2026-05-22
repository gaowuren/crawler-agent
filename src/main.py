"""命令行入口：列表页发现 URL → 拉正文 → 写入 JSONL。"""

from __future__ import annotations

import argparse
import sys

from src import config
from src.crawl_core import run_list_crawl_gen
from src.storage import append_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="中国新闻网静态练手爬虫（个人学习，请遵守 robots 与站点条款）。"
    )
    parser.add_argument(
        "--start-url",
        default=config.DEFAULT_START_URL,
        help="列表页或首页 URL",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="最多抓取多少个列表/栏目页（>1 时会从页面中收集 channel 栏目链接）",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=10,
        help="最多抓取多少篇详情页",
    )
    parser.add_argument(
        "--output",
        default=config.DEFAULT_OUTPUT_PATH,
        help="JSONL 输出路径",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=config.DEFAULT_REQUEST_INTERVAL_SEC,
        help="每次 HTTP 请求后的休眠秒数（礼貌限速）",
    )
    args = parser.parse_args(argv)

    n = 0
    for record in run_list_crawl_gen(
        args.start_url,
        max_pages=args.max_pages,
        max_articles=args.max_articles,
        interval=args.interval,
    ):
        append_jsonl(args.output, record)
        n += 1
        print(record.get("title") or record.get("url"))

    print(f"已写入 {n} 条到 {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
