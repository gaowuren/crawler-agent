"""JSON Lines 追加写入。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def append_jsonl(path: str | Path, record: Mapping[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(record), ensure_ascii=False) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
