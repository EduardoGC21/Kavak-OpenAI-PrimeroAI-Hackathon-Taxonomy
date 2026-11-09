"""Small readiness artifact writer; not shared harness/training infrastructure."""
from __future__ import annotations

import hashlib
import json
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path


class RunLog:
    def __init__(self, root: Path, code_root: Path, arguments: dict):
        self.root = root.resolve()
        if self.root.is_relative_to(code_root) and not self.root.is_relative_to(code_root / "runs"):
            raise ValueError("Data-bearing games logs must be outside the checkout or under ignored runs/")
        self.root.mkdir(parents=True, exist_ok=False)
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=code_root, capture_output=True, text=True, check=True)
        self.manifest = {"format": "games-readiness-run/v1", "started_at_utc": datetime.now(timezone.utc).isoformat(),
                         "code_head": revision.stdout.strip(), "arguments": {k: str(v) for k, v in arguments.items()},
                         "population": "full configured finite inputs; no random sampling", "sample_seed": None,
                         "evaluation_role": "exploratory_engineering_not_held_out_or_gold",
                         "model_calls": 0, "tokens": 0, "cost": None, "cost_status": "no model calls",
                         "validator_outcome": "not_run", "human_outcome": "not_reviewed"}

    def append(self, filename: str, record: dict):
        with (self.root / filename).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")

    def finish(self, report: dict, error: Exception | None = None) -> dict:
        if error:
            (self.root / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        self.manifest.update(status="FAIL" if error else "PASS", finished_at_utc=datetime.now(timezone.utc).isoformat(),
                             report=report, failure_type=type(error).__name__ if error else None)
        (self.root / "run.json").write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        index = []
        for path in sorted(self.root.iterdir()):
            index.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "bytes": path.stat().st_size,
                          "records": sum(1 for _ in path.open(encoding="utf-8")) if path.suffix == ".jsonl" else None})
        return {"root": str(self.root), "status": self.manifest["status"], "artifacts": index,
                "evaluation_role": self.manifest["evaluation_role"], "sample_seed": None,
                "sampling": self.manifest["population"]}
