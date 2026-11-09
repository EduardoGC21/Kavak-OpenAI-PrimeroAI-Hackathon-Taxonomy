"""Small data helpers adapters share. Format-level only: nothing here knows a domain."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from taxo.core.schemas import Node


def read_jsonl(path: Path, limit: int | None = None) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                return
            if line.strip():
                yield json.loads(line)


def link_children(nodes: list[Node]) -> list[Node]:
    """Fill each node's `children` from the others' parent_id."""
    by_id = {n.id: n for n in nodes}
    for n in nodes:
        if n.parent_id in by_id:
            by_id[n.parent_id].children.append(n.id)
    return nodes
