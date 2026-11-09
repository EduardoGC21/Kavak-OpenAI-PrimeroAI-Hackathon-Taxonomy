"""Car parts: listings from 8 Shopify parts stores, Refaccionaria California and BigAuto (Mexico).
No taxonomy is given: it is the new problem, to be proposed from the listings with reused rules."""
from __future__ import annotations

from typing import Iterator

from taxo.core import config
from taxo.core.io import read_jsonl
from taxo.core.schemas import Listing, Node

DOMAIN = "car_parts"


def load_listings(limit: int | None = None) -> Iterator[Listing]:
    for r in read_jsonl(config.data_dir() / DOMAIN / "listings.jsonl", limit):
        yield Listing(id=f"{r['_source']}:{r.get('id') or r.get('url')}", domain=DOMAIN, title=r.get("title") or "",
                      source=r["_source"], brand=r.get("brand"),
                      fields={k: r.get(k) for k in ("part_type", "category", "line", "fitment_text", "condition",
                                                     "condition_hint", "price_mxn", "price_min_mxn", "store", "url")
                              if r.get(k) is not None})


def load_taxonomy() -> list[Node]:
    return []  # none given yet: built during the run
