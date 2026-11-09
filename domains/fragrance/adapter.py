"""Fragrance: Pedia brand-page subset (listings + taxonomy) on Drive. Node ids are only unique within a brand,
so they are keyed `brand/id`. Pedia's own placement is kept in fields as a baseline, never as truth."""
from __future__ import annotations

from typing import Iterator

from taxo.core import config
from taxo.core.io import link_children, read_jsonl
from taxo.core.schemas import Listing, Node

DOMAIN = "fragrance"


def _key(brand, node_id):
    return f"{brand}/{node_id}" if node_id else None


def load_listings(limit: int | None = None) -> Iterator[Listing]:
    for r in read_jsonl(config.data_dir() / DOMAIN / "listings.jsonl", limit):
        yield Listing(id=r.get("mention_id") or r.get("natural_key"), domain=DOMAIN, title=r.get("title") or "",
                      source=r.get("source"), brand=r["brand"],
                      fields={"pedia_node": _key(r["brand"], r.get("placed_node_id")), "pedia_path": r.get("path"),
                              "pedia_depth": r.get("depth"), "gender": r.get("gender")})


def load_taxonomy() -> list[Node]:
    nodes = [Node(id=_key(r["brand"], r["id"]), domain=DOMAIN, name=r.get("name") or "",
                  parent_id=_key(r["brand"], r.get("parent_id")), level=r.get("level"),
                  path=(r.get("path") or "").split(" > "),
                  fields={k: r.get(k) for k in ("kind", "status", "concentration", "listings_here")})
             for r in read_jsonl(config.data_dir() / DOMAIN / "taxonomy.jsonl")]
    return link_children(nodes)
