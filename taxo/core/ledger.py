"""Append-only, hash-chained log of every claim, ruling and outcome, so a run can be audited afterwards."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from taxo.core.config import RUNS_DIR


class Ledger:
    def __init__(self, path: Path = RUNS_DIR / "ledger.jsonl"):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prev = self._last_hash()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = None
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                last = line
        return json.loads(last)["hash"] if last else "0" * 64

    def append(self, kind: str, **payload) -> str:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "prev": self.prev, **payload}
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        self.prev = entry["hash"]
        return entry["hash"]
