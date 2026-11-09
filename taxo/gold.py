"""Gold: the only truth (SPEC §2, §6). Read in place, split by whole brand, every sealed read logged.

Sources (fragrance):
  - Pedia fixtures (fresh150-harry.yaml, exp01-harry-correct.yaml): title, expected_path (brand first),
    compare prefix|exact, expect accept|reject.
  - Harry's owner reviews (owner-structure.jsonl at a Pedia commit), listing rows only: a "right" shown path becomes an
    accept/prefix row, a "wrong" one a reject/exact row (that path must not come back).
A title seen in both keeps the fixture row.

Split: frac(brand) = sha256(salt|brand) as a fraction; brands under `share` are sealed. Pedia's harness/verdicts/holdout.py.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from taxo.lattice.vocab import tokens

SALT = "taxo-sealed-v1"
SHARE = 0.2


@dataclass
class GoldRow:
    id: str
    title: str
    brand: str
    expected_path: list[str]
    compare: str = "prefix"        # prefix | exact
    expect: str = "accept"         # accept | reject
    brand_field: str | None = None
    origin: str = ""
    extra: dict = field(default_factory=dict)


def frac(key: str, salt: str = SALT) -> float:
    return int(hashlib.sha256(f"{salt}|{key}".encode()).hexdigest()[:12], 16) / 16 ** 12


def is_sealed(brand: str, salt: str = SALT, share: float = SHARE) -> bool:
    return frac(brand, salt) < share


def read_fixtures(paths: list[Path], brands: set[str] | None = None) -> list[GoldRow]:
    out = []
    for p in paths:
        for r in yaml.safe_load(Path(p).read_text(encoding="utf-8")) or []:
            if brands is not None and r.get("brand") not in brands:
                continue
            out.append(GoldRow(id=r["id"], title=r["title"], brand=r["brand"], expected_path=list(r["expected_path"]),
                               compare=r.get("compare", "prefix"), expect=r.get("expect", "accept"),
                               brand_field=r.get("brand_field"), origin=Path(p).name))
    return out


def owner_rows(lines: list[str], brands: set[str] | None = None) -> list[GoldRow]:
    out = []
    for line in lines:
        if not line.strip():
            continue
        o = json.loads(line)
        if o.get("kind") != "listing" or o.get("class") not in ("right", "wrong"):
            continue
        if brands is not None and o.get("brand") not in brands:
            continue
        s = o["subject"]
        path = [seg[0].split(" · ")[0].replace("(colour)", "").strip() for seg in s.get("path") or []]
        right = o["class"] == "right"
        out.append(GoldRow(id=o["id"], title=s.get("title") or "", brand=o["brand"], expected_path=path,
                           compare="prefix" if right else "exact", expect="accept" if right else "reject",
                           origin="owner-structure", extra={"verdicts": o.get("verdicts"), "comment": o.get("comment")}))
    return out


def read_owner_git(repo: Path, ref: str, path: str, brands: set[str] | None = None) -> list[GoldRow]:
    try:
        text = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True, check=True,
                              encoding="utf-8").stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return owner_rows(text.splitlines(), brands)


def dedupe(rows: list[GoldRow]) -> list[GoldRow]:
    seen, out = set(), []
    for r in rows:
        k = (r.brand, tokens(r.title))
        if k not in seen and r.title:
            seen.add(k)
            out.append(r)
    return out


class Gold:
    """Rows split by brand. `dev` is free to read; `sealed(purpose)` logs every read to `log`."""

    def __init__(self, rows: list[GoldRow], log: Path, salt: str = SALT, share: float = SHARE):
        self.rows, self.log, self.salt, self.share = rows, Path(log), salt, share

    def sealed_brands(self) -> set[str]:
        return {r.brand for r in self.rows if is_sealed(r.brand, self.salt, self.share)}

    @property
    def dev(self) -> list[GoldRow]:
        return [r for r in self.rows if not is_sealed(r.brand, self.salt, self.share)]

    def sealed(self, purpose: str) -> list[GoldRow]:
        rows = [r for r in self.rows if is_sealed(r.brand, self.salt, self.share)]
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "purpose": purpose, "rows": len(rows),
                                "brands": sorted({r.brand for r in rows}), "salt": self.salt}) + "\n")
        return rows

    def reads(self) -> int:
        return sum(1 for _ in open(self.log, encoding="utf-8")) if self.log.exists() else 0
