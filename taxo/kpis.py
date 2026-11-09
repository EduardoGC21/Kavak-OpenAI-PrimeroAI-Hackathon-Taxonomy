"""KPI history: one row per run, appended to runs/<domain>/kpis.jsonl (outside Git), so every loop round can be
compared with the ones before it.

A row: when, which code / vocab / rules ran, which loop (A, B or C) and round, gold scores (dev every run; sealed only
when the run read it), silver scores (null until a validator exists and is scored on gold, SPEC §8), cost and shares.

    uv run python -m taxo.kpis fragrance        print the history as a table
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from taxo.core.config import ROOT, RUNS_DIR


def _hash(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:10]


def _git() -> str:
    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                             encoding="utf-8", check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True,
                               encoding="utf-8").stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _gold(s: dict | None) -> dict | None:
    if not s:
        return None
    keep = ("accept_rows", "exact_rate", "right_or_shallower", "harm_rate", "reject_rows", "rejects_held")
    return {k: s[k] for k in keep} | {"levels": {str(k): v["acc"] for k, v in s["levels"].items()}}


def row(domain: str, result: dict, loop: str, round_: int, label: str, vocab: Path, rules_dirs: list[Path],
        silver: dict | None = None) -> dict:
    sh = result["shares_subset"]
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "domain": domain, "loop": loop, "round": round_, "label": label,
        "code": _git(), "vocab": _hash([vocab]), "rules": _hash([p for d in rules_dirs for p in d.glob("*.yaml")]),
        "gold_dev": _gold(result.get("dev")), "gold_sealed": _gold(result.get("sealed")),
        "silver": silver,                                  # validator version, agreement, flag precision: none yet
        "pedia_dev_in_subset": _gold(result.get("dev_in_subset", {}).get("pedia")),
        "shares": {k: sh[k][1] for k in ("placed_by_lattice", "settled_by_rule", "to_agent", "placed_by_agent") if k in sh},
        "agent_calls": result.get("agent_calls", 0), "sealed_reads_total": result.get("sealed_reads_logged"),
        "secs": result.get("secs"),
    }


def append(domain: str, r: dict) -> Path:
    p = RUNS_DIR / domain / "kpis.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


def history(domain: str) -> list[dict]:
    p = RUNS_DIR / domain / "kpis.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def table(rows: list[dict]) -> str:
    def f(x):
        return "-" if x is None else f"{x:.3f}" if isinstance(x, float) else str(x)
    cols = ["ts", "loop/round", "label", "code", "vocab", "dev exact", "dev right+shallower", "dev harm", "dev L1",
            "sealed exact", "silver agree", "lattice", "to agent"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        d, s, sv = r.get("gold_dev") or {}, r.get("gold_sealed") or {}, r.get("silver") or {}
        cells = [r["ts"], f"{r['loop']}/{r['round']}", r["label"], r["code"], r["vocab"], d.get("exact_rate"),
                 d.get("right_or_shallower"), d.get("harm_rate"), (d.get("levels") or {}).get("1"), s.get("exact_rate"),
                 sv.get("agreement"), r["shares"].get("placed_by_lattice"), r["shares"].get("to_agent")]
        out.append("| " + " | ".join(f(c) for c in cells) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(prog="taxo.kpis")
    ap.add_argument("domain")
    print(table(history(ap.parse_args().domain)))


if __name__ == "__main__":
    main()
