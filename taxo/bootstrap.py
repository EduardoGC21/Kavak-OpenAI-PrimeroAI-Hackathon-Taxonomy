"""Offline construction proposals through domain contracts. Never loads gold, calls models or admits rules."""
from __future__ import annotations

import hashlib
import importlib
import json
from collections import Counter, defaultdict
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
    # Optional domain-local contract used by games: facts(listing, node), with evidence in fields[domain].
    hook_path = DOMAINS_DIR / name / "checks.py"
    hook = getattr(importlib.import_module(f"domains.{name}.checks"), "candidate_facts", None) if hook_path.is_file() else None
    by_id = {l.id: l for l in listings}
    partitions = defaultdict(list)
    metadata = {}
    for item in items:
        evidence = by_id[item.id].fields.get(name) or {}
        identity = {k: v for k, v in (evidence.get("identity") or {}).items() if k != "title_key"}
        part = {"subtype": evidence.get("subtype"), "identity": identity} if evidence.get("subtype") else {}
        key = json.dumps(part, sort_keys=True)
        partitions[key].append(item)
        metadata[item.id] = part
    stats = Counter()
    vocab = load_vocab(vocab_path, preserve_identity_tokens=True)  # raw construction never discards numeric identifiers
    for key, group in partitions.items():
        part = json.loads(key)
        stats.update(run(group, brands, vocab, route_rules, domain=name,
                         full_title=construction.get("full_title", True), candidate_rules=pair_rules, dedupe_support=True,
                         listings=by_id, candidate_facts=hook, node_fields={name: part} if part else {}))
    nodes = {}
    placements = []
    for item in items:
        for i in range(len(item.path)):
            path = item.path[:i + 1]
            def node_id(parts):
                context = metadata[item.id] if len(parts) > 1 else {}
                return f"{name}:proposal:{_slug(json.dumps([parts, context], sort_keys=True, ensure_ascii=False))}"
            nid = node_id(path)
            parent = node_id(path[:-1]) if i else None
            nodes[nid] = {"id": nid, "domain": name, "name": path[-1], "path": path, "parent_id": parent,
                          "level": "brand" if i == 0 else "product", "fields": {"status": "proposal", "basis": "raw_lattice_no_human_gold",
                          **({name: metadata[item.id]} if i and metadata[item.id] else {})}}
        placements.append({**asdict(item), "node_id": nid if item.path else None, "status": "proposal",
                           "identity_partition": metadata[item.id]})
    for node in nodes.values():
        node["children"] = []
    for node in nodes.values():
        if node["parent_id"] in nodes:
            nodes[node["parent_id"]]["children"].append(node["id"])
    result = {"domain": name, "mode": "raw_only_proposals", "input_rows": len(listings), "limit": limit,
              "eligible_rows": len(items), "screened": dict(Counter(r["decision"] for r in screened)),
              "unscoped_rows": sum(not l.fields.get("domain_scope") for l in listings),
              "reported_brands": len(names), "proposed_nodes": len(nodes), "lattice": dict(stats),
              "identity_partitions": len(partitions), "candidate_facts_hook": hook.__module__ if hook else None,
              "raw_identity_tokens_preserved": True,
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
    for filename, records in [("placements.jsonl", placements), ("nodes.jsonl", list(nodes.values())),
                              ("screened.jsonl", screened)]:
        (out / filename).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
