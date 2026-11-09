"""Offline construction proposals through domain contracts. Never loads gold, calls models or admits rules."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from taxo import evaluator, memory
from taxo.core.config import DOMAINS_DIR, ROOT, RUNS_DIR
from taxo.core.domain import load
from taxo.lattice.vocab import load as load_vocab
from taxo.parse import Brands


def _slug(value: str) -> str:
    return hashlib.sha256(value.strip().casefold().encode()).hexdigest()[:20]


class ReportedBrands(Brands):
    """Only the adapter's reported brand; no seller, title, character or compatibility inference."""
    def find(self, p, brand_field=None, maker_field=None):
        key = _slug(brand_field) if brand_field else None
        return (key, "source_reported_unverified") if key in self.names else (None, "missing_source_brand")


def construct(name: str, limit: int | None = None, output: Path | None = None) -> dict:
    from taxo.pipeline import Item, run

    if limit is not None and limit <= 0:
        raise ValueError("construction --limit must be positive")
    domain = load(name)
    vocab_path = DOMAINS_DIR / name / "vocab.yaml"
    if not vocab_path.exists():
        raise ValueError(f"{name} has no vocab.yaml; supply domain vocabulary before construction")
    out = output or RUNS_DIR / name / "construction"
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} is nonempty; choose a fresh --output directory to preserve evidence")
    listings = list(domain.listings(limit))
    if not listings:
        raise ValueError(f"{name}: no listings; configure the domain adapter source (see docs/{name}.md)")
    if len({l.id for l in listings}) != len(listings):
        raise ValueError(f"{name}: duplicate Listing.id")
    families = tuple(domain.pack.get("families", []))
    pair_rules = memory.rules_for(name, families)
    construction = domain.pack.get("construction") or {}
    dirs = [ROOT / "rules" / name]
    if construction.get("global_evaluator_rules", False):
        dirs.append(ROOT / "rules" / "global")
    route_rules = evaluator.load(*dirs)
    names = {_slug(l.brand): l.brand.strip() for l in listings if l.brand and l.brand.strip().casefold() not in {"generic", "unknown", "unbranded", "n/a"}}
    brands = ReportedBrands(names, suffixes=())
    items, screened = [], []
    for listing in listings:
        screen = listing.fields.get("domain_scope") or {}
        if screen.get("decision") in {"reject", "hold"}:
            screened.append({"id": listing.id, "decision": screen["decision"], "reason": screen.get("reason")})
        else:
            items.append(Item(id=listing.id, title=listing.title, source=listing.source or "", brand_field=listing.brand))
    stats = run(items, brands, load_vocab(vocab_path), route_rules, domain=name,
                full_title=construction.get("full_title", True), candidate_rules=pair_rules, dedupe_support=True)
    nodes = {}
    for item in items:
        for i in range(len(item.path)):
            path = item.path[:i + 1]
            nid = f"{name}:proposal:{_slug(json.dumps(path, ensure_ascii=False))}"
            parent = f"{name}:proposal:{_slug(json.dumps(path[:-1], ensure_ascii=False))}" if i else None
            nodes[nid] = {"id": nid, "domain": name, "name": path[-1], "path": path, "parent_id": parent,
                          "level": "brand" if i == 0 else "product", "fields": {"status": "proposal", "basis": "raw_lattice_no_human_gold"}}
    result = {"domain": name, "mode": "raw_only_proposals", "input_rows": len(listings), "limit": limit,
              "eligible_rows": len(items), "screened": dict(Counter(r["decision"] for r in screened)),
              "unscoped_rows": sum(not l.fields.get("domain_scope") for l in listings),
              "reported_brands": len(names), "proposed_nodes": len(nodes), "lattice": stats,
              "pair_rules": [{"id": r.id, "status": r.status.value} for r in pair_rules],
              "evaluator_rules": [{"id": r.id, "status": r.status} for r in route_rules],
              "agentic_instructions": [r.id for r in memory.agentic_for(name)],
              "vocab_sha256": hashlib.sha256(vocab_path.read_bytes()).hexdigest(),
              "pack_sha256": hashlib.sha256((DOMAINS_DIR / name / "pack.yaml").read_bytes()).hexdigest(),
              "source_manifests": list({json.dumps(l.fields["source_manifest"], sort_keys=True): l.fields["source_manifest"]
                                        for l in listings if "source_manifest" in l.fields}.values()),
              "gold_loaded": False, "accuracy": None, "agent_calls": 0,
              "limitations": ["Source brand reports and lattice support are not official maker/product evidence.",
                              "Exact duplicate normalized names count once; near-duplicate marketplace pages still need review.",
                              "Proposed nodes require review and blind human gold before accuracy scoring or rule admission."],
              "output": str(out)}
    out.mkdir(parents=True, exist_ok=True)
    for filename, records in [("placements.jsonl", [asdict(i) for i in items]), ("nodes.jsonl", list(nodes.values())),
                              ("screened.jsonl", screened)]:
        (out / filename).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
