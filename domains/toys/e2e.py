"""Offline behavioral E2E checks; synthetic expectations are not human gold."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from domains.toys import adapter
from taxo.core.domain import Domain
from taxo.core.schemas import AgenticRule, Node, RuleSpec, Status
from taxo.core.rules import run_rules
from taxo.lattice.vocab import load as load_vocab, tokens
from taxo.tools.toys import inspect_source, identifier_evidence, offering_evidence


def run(source: Path, output: Path, boundary_sources: list[Path] | None = None) -> dict:
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    # Full synthetic product descriptions, not excerpts of actual source titles.
    examples = [
        ("Building set 40721 Space Station 312 pieces", "Toy Building Sets", "include"),
        ("Mira 2 action figure collector edition", "Action Figures", "include"),
        ("Soft plush dragon stuffed animal", "Plush Figure Toys", "include"),
        ("Fashion doll with miniature sleeping bag", "Dolls", "include"),
        ("Pretend play doctor kit 4 pieces", "Toy Medical Kits", "include"),
        ("Sensory fidget squeeze toy random color pack of 1", "Squeeze Toys", "include"),
        ("RX42 1:16 scale RC truck with 2 batteries", "Hobby RC Trucks", "include"),
        ("Replacement axle compatible with RX42 RC truck", "RC Vehicle Axles", "include"),
        ("Miniature dress for 18 inch dolls", "Doll Clothing", "include"),
        ("Action figure display stand compatible with Galaxy 2", "Toy Interlocking Building Accessories", "include"),
        ("Beach ball for pool play", "Beach Balls", "include"),
        ("Toy clay activity craft kit", "Kids' Art Clay & Dough", "include"),
        ("Doll adventures board game", "Board Games", "exclude"),
        ("Galaxy deck card game", "Dedicated Deck Card Games", "exclude"),
        ("300 piece wooden jigsaw puzzle", "Jigsaw Puzzles", "exclude"),
        ("Domino tile game double 12", "Domino & Tile Games", "exclude"),
        ("Galaxy role playing dice set", "Role Playing Dice", "exclude"),
        ("Galaxy 2 PlayStation 5 game", "PlayStation 5 Games", "exclude"),
        ("Controller compatible with Nintendo Switch", "Nintendo Switch Controllers", "exclude"),
        ("Robot party paper plates and napkins", "Kids' Party Plates", "exclude"),
        ("Catnip plush toy for cats", "Catnip Toys", "exclude"),
        ("Vinyl stickers for laptop and water bottle", "Kids' Stickers", "exclude"),
        ("Tablet stylus for iPad", "Nintendo 3DS & 2DS Stylus Pens", "exclude"),
        ("Baby white noise sound machine", "Baby Car Toys & Stroller Toys", "exclude"),
        ("Movie disc", "Plug & Play Video Games", "exclude", ["Video DVD"]),
        ("Real washable makeup kit for kids", "Dress-Up Toy Makeup", "hold"),
        ("Portable swimming pool for kids and dogs", "Kiddie Pools", "hold"),
        ("School glue for classroom", "Kids' Arts & Crafts Adhesives", "hold"),
        ("Collector surprise box", "Toys & Games", "hold"),
        ("Professional bait release fishing drone", "Hobby RC Quadcopters & Multirotors", "hold"),
        ("Toy dinosaur figure", "Board Games", "hold"),
        ("Endo-2 collector figure 6-inch", "Action Figures", "include"),
        ("Dragon plush toy party favors", "Stuffed Animals & Teddy Bears", "include"),
        ("Pretend play tea party set with cups", "Toy Tea Sets", "include"),
        ("Action figure from The Garden Diaries", "Action Figures", "include"),
        ("Tactical gaming keypad 42 keys", "PC Gaming Keyboards", "exclude"),
        ("RC toy graphic T-Shirt", "Clothing, Shoes & Jewelry", "exclude"),
        ("Plush slippers for women", "Clothing, Shoes & Jewelry", "hold"),
        ("Animal action figures also usable as cake toppers", "Action Figures", "include"),
        ("Animal figurine cake topper", "Non-Edible Cake Toppers", "hold"),
        ("Yellow school bus with flashing lights", "Kids' Play Buses", "include"),
        ("Space battle figure 6 pack", "Kids' Play Fantastic Creature Figures", "include"),
    ]
    rows = []
    for i, (title, rank, expected, *categories) in enumerate(examples):
        r = {"asin": f"SYN{i:07d}", "title": title, "brand": None,
             "merchant": "Shop Is Not Maker", "byline": "Visit the Franchise Store",
             "categories": categories[0] if categories else ["Toys"],
             "best_seller_ranks": [f"#1 in {rank}"], "scrape_status": "ok"}
        decision = adapter.scope_decision(r)
        check(f"scope-{i}-{expected}", decision["decision"] == expected)
        check(f"reason-{i}", bool(decision["reason"]))
        rows.append(r)

    with tempfile.TemporaryDirectory(prefix="taxo-toys-e2e-") as temp:
        base = Path(temp)
        path = base / "listings.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        env = {"TAXO_TOYS_LISTINGS": str(path), "TAXO_DATA_DIR": str(base), "TAXO_TOYS_SOURCE_ROWS": ""}
        with patch.dict(os.environ, env):
            domain = Domain("toys", yaml.safe_load((adapter.HOME / "pack.yaml").read_text()))
            listings = list(domain.listings())
            check("listing-contract", all(x.domain == "toys" for x in listings))
            check("post-scope-limit", len(list(domain.listings(limit=3))) == 3)
            check("zero-limit", list(domain.listings(limit=0)) == [])
            check("missing-tree-bootstrap", list(domain.nodes()) == [])
            check("no-brand-inference", all(x.brand is None for x in listings))
            check("raw-preservation", listings[0].fields["raw"] == rows[0])
            check("identity-text", "40721" in listings[0].fields["identity_text"])
            hint = adapter.identity_hints("RX42 Set 40721 1:16 Scale 312 pieces Pack of 2 Color May Vary")
            check("piece-count-not-pack", hint["piece_contents"] == ["312 pieces"] and hint["pack_multiplicity"] == ["Pack of 2"])
            check("scale-and-model-survive", hint["scale"] == ["1:16 Scale"] and "RX42" in hint["numeric_tokens"] and "40721" in hint["numeric_tokens"])
            check("random-offer-preserved", hint["assorted_random"] == ["Color May Vary"])
            before = {x.id: x.title for x in listings}
            path.write_text("\n".join(json.dumps(r) for r in reversed(rows)), encoding="utf-8")
            check("order-independent-ids", {x.id: x.title for x in domain.listings()} == before)
            path.write_text("\n".join(json.dumps(r) for r in [rows[0], rows[0]]), encoding="utf-8")
            try:
                list(domain.listings())
            except ValueError:
                checks.append("duplicate-identity-fails")
            else:
                raise AssertionError("duplicate identity accepted")
            try:
                list(domain.listings(limit=-1))
            except ValueError:
                checks.append("negative-limit-fails")
            else:
                raise AssertionError("negative limit accepted")
            # Explicit canonical tree input uses the existing Node contract only.
            tree = base / "toys" / "taxonomy.jsonl"
            tree.parent.mkdir()
            tree.write_text(json.dumps({"id": "synthetic-maker", "domain": "toys", "name": "Maker", "level": "brand"}), encoding="utf-8")
            check("explicit-node-contract", isinstance(domain.nodes()[0], Node))
            for label, invalid in [
                ("tree-missing-parent", [{"id": "a", "name": "A", "level": "product", "parent_id": "absent"}]),
                ("tree-cycle", [{"id": "a", "name": "A", "level": "product", "parent_id": "a"}]),
                ("tree-duplicate", [{"id": "a", "name": "A", "level": "brand"}] * 2),
                ("tree-no-pack-level", [{"id": "a", "name": "A", "level": "pack"}]),
            ]:
                tree.write_text("\n".join(json.dumps(r) for r in invalid), encoding="utf-8")
                try:
                    domain.nodes()
                except ValueError:
                    checks.append(label)
                else:
                    raise AssertionError(label)

        # Join by stable keys even when the two parquet files have opposite order.
        import pyarrow as pa
        import pyarrow.parquet as pq
        silver = [{"observation_key": -7, "listing_key": -11, "source_listing_id": rows[0]["asin"],
                   "source_id": "amazon_historical_parsed", "listing_name": rows[0]["title"],
                   "brand_name": None, "identifiers_json": "[]", "bronze_reference_json": "{}"},
                  {"observation_key": 8, "listing_key": 12, "source_listing_id": rows[1]["asin"],
                   "source_id": "amazon_historical_parsed", "listing_name": rows[1]["title"],
                   "brand_name": None, "identifiers_json": "[]", "bronze_reference_json": "{}"}]
        sidecar = [dict(rows[1], observation_key=8, listing_key=12),
                   dict(rows[0], observation_key=-7, listing_key=-11)]
        sp, rp = base / "mixed.parquet", base / "source_rows.parquet"
        pq.write_table(pa.Table.from_pylist(silver), sp)
        pq.write_table(pa.Table.from_pylist(sidecar), rp)
        with patch.dict(os.environ, {"TAXO_TOYS_LISTINGS": str(sp), "TAXO_TOYS_SOURCE_ROWS": str(rp)}):
            got = list(adapter.load_listings())
            check("signed-key-preservation", got[0].fields["observation_key"] == -7)
            check("sidecar-key-join", got[0].title == rows[0]["title"])
            check("cross-format-ids", got[0].id == next(k for k in before if k.endswith(rows[0]["asin"])))
            for label, bad in [("missing-sidecar-row", sidecar[:1]),
                               ("duplicate-sidecar-key", [sidecar[0], sidecar[0]]),
                               ("wrong-sidecar-asin", [sidecar[0], dict(sidecar[1], asin="WRONG")])]:
                pq.write_table(pa.Table.from_pylist(bad), rp)
                try:
                    list(adapter.load_listings())
                except ValueError:
                    checks.append(label)
                else:
                    raise AssertionError(label)

    code = adapter.load_rules()
    agentic = [AgenticRule(**r) for r in yaml.safe_load((adapter.HOME / "memory/rules/agentic.yaml").read_text())]
    check("three-code-proposals", len(code) == 3 and all(isinstance(r, RuleSpec) and r.status == Status.PROPOSAL for r in code))
    check("three-agentic-proposals", len(agentic) == 3 and all(r.status == Status.PROPOSAL for r in agentic))
    check("proposal-engine-inert", not run_rules(code, listings[0], Node(id="probe", domain="toys", name="Other"), {}).decided)
    check("empty-validator-checklist", yaml.safe_load((adapter.HOME / "validator.yaml").read_text())["checklist"] == [])
    vocab = load_vocab(adapter.HOME / "vocab.yaml")
    numeric = tokens("40721 RX42 1:16 4WD Series 2 312 pieces")
    check("numeric-vocab-not-stripped", all(v is None for v in vocab.tag(numeric).var))
    sample = listings[0]
    candidate = Node(id="set", domain="toys", name="Station", fields={"identity_identifiers": {"set_number": "40721"}})
    check("number-proposal-supported", identifier_evidence(sample, candidate, {}) is None)
    candidate.fields["identity_identifiers"]["set_number"] = "4072"
    check("number-proposal-no-partial", bool(identifier_evidence(sample, candidate, {})))
    candidate.fields["identity_identifiers"]["set_number"] = "99999"
    check("number-proposal-absent", bool(identifier_evidence(sample, candidate, {})))
    check("number-proposal-no-invention", identifier_evidence(sample, Node(id="n", domain="toys", name="Unknown"), {}) is None)
    complete = Node(id="c", domain="toys", name="Truck", fields={"offering_kind": "complete_toy"})
    replacement = sample.model_copy(update={"title": "Replacement axle compatible with RX42 RC truck"})
    check("accessory-proposal-blocks-complete", bool(offering_evidence(replacement, complete, {})))
    supplied = sample.model_copy(update={"title": "RX42 RC truck with replacement axle and accessories"})
    check("accessory-proposal-complete-with-parts", offering_evidence(supplied, complete, {}) is None)
    random = sample.model_copy(update={"title": "Squeeze toy Color May Vary"})
    variant = Node(id="v", domain="toys", name="Red", level="variant", fields={"variant_axis": "color"})
    check("random-proposal-blocks-specific", bool(offering_evidence(random, variant, {})))
    report = inspect_source(source, max_rows=6000, output=output / "real-input")
    check("real-input-field-preservation", report["preservation_checked"] == report["decisions"].get("include", 0) > 0)
    boundaries = []
    for i, boundary in enumerate(boundary_sources or []):
        inspected = inspect_source(boundary, max_rows=6000, output=output / f"boundary-{i}")
        check(f"boundary-{i}-no-toys-admitted", inspected["decisions"].get("include", 0) == 0)
        boundaries.append(inspected)
    result = {"status": "PASS", "kind": "offline behavioral E2E; synthetic expectations are not gold",
              "checks_passed": len(checks), "checks": checks, "real_input": report, "boundary_inputs": boundaries}
    output.mkdir(parents=True, exist_ok=True)
    (output / "e2e.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--boundary-source", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        result = run(args.source, args.output, args.boundary_source)
    except Exception as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "e2e-failure.json").write_text(
            json.dumps({"status": "FAIL", "error": str(exc), "type": type(exc).__name__}, indent=2), encoding="utf-8")
        raise
    print(json.dumps({"status": result["status"], "checks_passed": result["checks_passed"]}))
