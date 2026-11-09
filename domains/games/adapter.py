"""Games listings from canonical JSONL or explicitly configured mixed Amazon parquet.

Food Silver is a transport schema only. All admitted rows are screened again.
No trusted catalogue exists; load_taxonomy deliberately returns no nodes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

from taxo.core import config
from taxo.core.schemas import Listing, Node

from .scope import decide_scope, evidence_row, identity_features

DOMAIN = "games"


def input_paths() -> tuple[Path, Path | None]:
    explicit = os.environ.get("TAXO_GAMES_LISTINGS")
    if explicit:
        path = Path(explicit)
    else:
        root = config.data_dir() / DOMAIN
        paths = [p for p in (root / "listings.jsonl", root / "games_listings.parquet", root / "listings.parquet") if p.is_file()]
        if len(paths) != 1:
            raise RuntimeError(f"Expected exactly one games input under {root}; found {len(paths)}. Set TAXO_GAMES_LISTINGS explicitly.")
        path = paths[0]
    sidecar = os.environ.get("TAXO_GAMES_SOURCE_ROWS")
    return path, Path(sidecar) if sidecar else None


def _rows(path: Path) -> Iterator[dict]:
    if path.suffix == ".parquet":
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("Games parquet needs pyarrow; install it in your local environment.") from exc
        for batch in pq.ParquetFile(path).iter_batches(batch_size=256):
            yield from batch.to_pylist()
    elif path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
    else:
        raise ValueError(f"Unsupported games input: {path}; use JSONL or parquet")


def listing_id(row: dict) -> str:
    if row.get("observation_key") is not None:
        return str(row["observation_key"])
    for key in ("id", "mention_id", "natural_key"):
        if row.get(key) is not None and str(row[key]).strip():
            return str(row[key])
    native = row.get("asin") or row.get("source_listing_id")
    if native:
        return f"{row.get('source_id') or row.get('source') or 'amazon_historical_parsed'}:{native}"
    raise ValueError("Games row has no stable identifier; positional IDs are forbidden")


def read_records(path: Path | None = None, sidecar: Path | None = None) -> Iterator[dict]:
    """Join sidecars by exact signed key, never by row order; preserve both inputs.

    A compatibility parquet requires a complete sidecar. Ordinary raw parquet and
    canonical JSONL do not. No source writes or on-disk staging are performed.
    """
    if path is None:
        path, configured_sidecar = input_paths()
        sidecar = sidecar or configured_sidecar
    path = Path(path)
    iterator = iter(_rows(path))
    first = next(iterator, None)
    if first is None:
        return
    compatibility = "listing_name" in first and "observation_key" in first
    if compatibility and sidecar is None:
        sidecar = path.with_name("source_rows.parquet")
    if compatibility and not sidecar.is_file():
        raise FileNotFoundError(f"Games compatibility input needs its RAW sidecar: {sidecar}")
    source_rows: dict[str, dict] = {}
    if sidecar is not None:
        for row in _rows(Path(sidecar)):
            key = listing_id(row)
            if key in source_rows:
                raise ValueError(f"Duplicate games sidecar key {key}")
            source_rows[key] = row
    seen = set()

    def joined(row):
        key = listing_id(row)
        if key in seen:
            raise ValueError(f"Duplicate games listing key {key}")
        seen.add(key)
        if source_rows:
            if key not in source_rows:
                raise ValueError(f"Games sidecar missing key {key}")
            raw = source_rows[key]
            native = row.get("source_listing_id") or row.get("asin")
            if native and raw.get("asin") and native != raw["asin"]:
                raise ValueError(f"Games sidecar native ID mismatch for {key}")
            if row.get("listing_key") is not None and raw.get("listing_key") is not None and row["listing_key"] != raw["listing_key"]:
                raise ValueError(f"Games sidecar listing_key mismatch for {key}")
        elif sidecar is not None:
            raise ValueError("Empty games sidecar")
        else:
            raw = {}
        if "games_source_row" in row or "games_provenance" in row:
            raise ValueError("Input uses reserved games adapter fields")
        return {**row, "games_source_row": raw, "games_provenance": {
            "listing_file": str(path.resolve()), "source_rows_file": str(Path(sidecar).resolve()) if sidecar else None}}

    yield joined(first)
    for row in iterator:
        yield joined(row)
    if source_rows and seen != source_rows.keys():
        raise ValueError("Games sidecar has extra unmatched keys")


def to_listing(row: dict) -> Listing:
    raw = evidence_row(row)
    scope = decide_scope(row)
    source_brand = raw.get("brand") or raw.get("brand_name")
    brand = source_brand.strip() if isinstance(source_brand, str) and source_brand.strip() else None
    if brand and brand.lower() in ("generic", "unknown", "unbranded", "n/a"):
        brand = None
    canonical = {k: v for k, v in row.items() if k not in ("games_source_row", "games_provenance")}
    return Listing(
        id=listing_id(row), domain=DOMAIN,
        title=raw.get("title") or raw.get("listing_name") or "",
        source=row.get("source_id") or row.get("source") or ("amazon_historical_parsed" if raw.get("asin") else None),
        brand=brand,
        fields={"raw": canonical, "source_raw": row.get("games_source_row", {}),
                "provenance": row.get("games_provenance", {}),
                "source_brand": source_brand, "brand_status": "unverified_source_field" if brand else "missing_or_generic",
                "description": raw.get("description") or raw.get("description_text") or raw.get("aplus_content"),
                "seller": raw.get("merchant") or raw.get("seller_name") or raw.get("amazon_seller_text"),
                "games": {"scope": scope.as_dict(), "subtype": scope.subtype,
                          "identity": identity_features(row, scope.subtype)}})


def load_listings(limit: int | None = None) -> Iterator[Listing]:
    if limit is not None and limit < 0:
        raise ValueError("Games limit must be nonnegative")
    if limit == 0:
        return
    count = 0
    for row in read_records():
        if decide_scope(row).status != "accept":
            continue
        yield to_listing(row)
        count += 1
        if limit is not None and count >= limit:
            return


def load_taxonomy() -> list[Node]:
    return []  # bootstrap required; category ranks and format exports are not nodes
