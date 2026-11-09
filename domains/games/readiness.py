"""Bounded offline games adapter/rules E2E; never imports gold or model clients.

python -m domains.games.readiness --listings <file> --report <report.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import yaml

from taxo import evaluator
from taxo.core.domain import Domain
from taxo.core.schemas import AgenticRule, Node
from taxo.lattice.vocab import load as load_vocab, tokens

from . import adapter
from .checks import candidate_facts
from .scope import VERSION, category_labels, decide_scope
from .runlog import RunLog

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@contextmanager
def configured(path, sidecar=None):
    names = ("TAXO_GAMES_LISTINGS", "TAXO_GAMES_SOURCE_ROWS")
    before = {k: os.environ.get(k) for k in names}
    os.environ[names[0]] = str(path)
    if sidecar:
        os.environ[names[1]] = str(sidecar)
    else:
        os.environ.pop(names[1], None)
    try:
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def expect_error(fn, error):
    try:
        fn()
    except error:
        return
    raise AssertionError(f"Expected {error.__name__}")


def domain() -> Domain:
    return Domain("games", yaml.safe_load((HERE / "pack.yaml").read_text(encoding="utf-8")))


def smoke(path: Path) -> dict:
    with configured(path):
        listing = next(domain().listings(limit=1))
        assert listing.domain == "games" and listing.fields["games"]["scope"]["status"] == "accept"
        assert domain().nodes() == []
    assert len(evaluator.load(ROOT / "rules/games")) == 4
    return {"status": "PASS", "direct_import": True, "one_real_listing": True,
            "listing_id_type": type(listing.id).__name__, "taxonomy_nodes": 0}


def synthetic_e2e() -> dict:
    cases = yaml.safe_load((HERE / "e2e/examples.yaml").read_text(encoding="utf-8"))
    for case in cases:
        decision = decide_scope(case)
        assert decision.status == case["status"], (case["title"], decision)
        if "subtype" in case:
            assert decision.subtype == case["subtype"], (case["title"], decision)
    with tempfile.TemporaryDirectory(prefix="taxo-games-e2e-") as tmp:
        import pyarrow as pa
        import pyarrow.parquet as pq
        folder = Path(tmp)
        path = folder / "listings.jsonl"
        rows = [{"id": f"synthetic:{i}", "source": "synthetic", **r} for i, r in enumerate(cases)]
        # Source maker is absent, despite seller and licensed/compatible names.
        rows[10]["seller_name"] = "PlayStation"
        rows[10]["brand"] = None
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        with configured(path):
            loaded = list(domain().listings())
            assert len(loaded) == sum(r["status"] == "accept" for r in cases)
            assert list(domain().listings(0)) == []
            assert list(domain().listings(1)) == loaded[:1]
            assert list(domain().listings(3)) == loaded[:3]
            expect_error(lambda: list(domain().listings(-1)), ValueError)
        assert loaded[10].brand is None
        assert loaded[10].fields["seller"] == "PlayStation"
        assert "4" in loaded[0].fields["games"]["identity"]["title_key"].split()
        assert loaded[5].fields["games"]["identity"]["puzzle_piece_counts"] == [1000]
        assert loaded[8].fields["games"]["identity"]["platforms"] == ["switch_2"]
        assert loaded[8].fields["games"]["identity"]["distribution"] == "digital"
        assert loaded[1].fields["games"]["identity"]["product_role"] == "expansion"

        # Exercise signed 64-bit / zero IDs, out-of-order keyed joins and errors.
        silver = folder / "games_listings.parquet"
        sidecar = folder / "source_rows.parquet"
        projected = [{"observation_key": key, "listing_name": "Acme Board Game", "source_listing_id": asin}
                     for key, asin in [(-9223372036854775807, "SYN-A"), (0, "SYN-B")]]
        raw = [{"observation_key": r["observation_key"], "asin": r["source_listing_id"],
                "title": r["listing_name"], "model": "X2", "brand": None} for r in projected]
        pq.write_table(pa.Table.from_pylist(projected), silver)
        pq.write_table(pa.Table.from_pylist(raw[::-1]), sidecar)
        with configured(silver):
            joined = list(domain().listings())
        assert [x.id for x in joined] == ["-9223372036854775807", "0"]
        assert all(x.fields["source_raw"]["model"] == "X2" for x in joined)
        pq.write_table(pa.Table.from_pylist(raw[:1]), sidecar)
        expect_error(lambda: list(adapter.read_records(silver)), ValueError)
        pq.write_table(pa.Table.from_pylist(raw + raw[:1]), sidecar)
        expect_error(lambda: list(adapter.read_records(silver)), ValueError)
        pq.write_table(pa.Table.from_pylist([{**raw[0], "asin": "WRONG"}, raw[1]]), sidecar)
        expect_error(lambda: list(adapter.read_records(silver)), ValueError)
        sidecar.unlink()
        expect_error(lambda: list(adapter.read_records(silver)), FileNotFoundError)
        path.write_text(json.dumps(rows[0]) + "\n" + json.dumps(rows[0]), encoding="utf-8")
        expect_error(lambda: list(adapter.read_records(path)), ValueError)
        path.write_text(json.dumps({"title": "Acme Board Game"}), encoding="utf-8")
        expect_error(lambda: list(adapter.read_records(path)), ValueError)
    return {"status": "PASS", "examples": len(cases), "labels": "synthetic_behavior_only_not_gold",
            "keyed_join_and_fail_closed_errors": True, "limits_and_brand_noninference": True}


def rules_e2e(log: RunLog) -> dict:
    rules = evaluator.load(ROOT / "rules/games")
    assert len({r.id for r in rules}) == 4 and all(r.status == "shadow" for r in rules)
    agentic = [AgenticRule(**r) for r in yaml.safe_load((HERE / "memory/rules/agentic.yaml").read_text(encoding="utf-8"))]
    assert all(r.status.value == "proposal" and r.origin and r.evidence for r in agentic)
    assert yaml.safe_load((HERE / "validator.yaml").read_text(encoding="utf-8"))["checklist"] == []
    vocab = load_vocab(HERE / "vocab.yaml")
    numeral_tokens = tokens("Realm 2 PS5 Switch 2 M87 Pro Connect 4 1000 Piece")
    assert all(x is None for x in vocab.tag(numeral_tokens).var)
    listing = adapter.to_listing({"id": "synthetic:rule", "title": "Acme Harbor 1000 Piece Puzzle"})
    same = Node(id="synthetic:same", domain="games", name="Synthetic", fields={"games": listing.fields["games"]})
    assert not evaluator.evaluate(rules, "place", candidate_facts(listing, same)).shadow
    changed = json.loads(json.dumps(same.fields))
    changed["games"]["subtype"] = "board_game"
    other = same.model_copy(update={"fields": changed})
    out = evaluator.evaluate(rules, "place", candidate_facts(listing, other))
    assert out.rule is None and not out.then and any(x[0] == "games/kind-conflict" for x in out.shadow)
    changed = json.loads(json.dumps(same.fields))
    changed["games"]["identity"]["puzzle_piece_counts"] = [500]
    out = evaluator.evaluate(rules, "place", candidate_facts(listing, same.model_copy(update={"fields": changed})))
    assert out.rule is None and any(x[0] == "games/identity-conflict" for x in out.shadow)
    out = evaluator.evaluate(rules, "place", candidate_facts(listing, Node(id="blank", domain="games", name="Blank")))
    assert out.rule is None and any(x[0] == "games/missing-identity" for x in out.shadow)
    held = adapter.to_listing({"id": "synthetic:held", "title": "Mystery Box"})
    out = evaluator.evaluate(rules, "route", candidate_facts(held, same))
    assert out.rule is None and any(x[0] == "games/scope-hold" for x in out.shadow)
    # Explicitly verify each identity axis through the real fact/evaluator path.
    for axis, left, right in [("platforms", ["switch"], ["switch_2"]),
                              ("editions", ["deluxe edition"], ["standard edition"]),
                              ("languages", ["japanese"], ["english"]),
                              ("distribution", "physical", "digital"),
                              ("product_role", "expansion", "base_or_standalone"),
                              ("compatible_platforms", ["ps4"], ["ps5"])]:
        lf = {"games": {"subtype": "video_game_software", "identity": {axis: left}}}
        nf = {"games": {"subtype": "video_game_software", "identity": {axis: right}}}
        facts = candidate_facts(listing.model_copy(update={"fields": lf}), same.model_copy(update={"fields": nf}))
        result = evaluator.evaluate(rules, "place", facts)
        assert result.rule is None and any(x[0] == "games/identity-conflict" for x in result.shadow), axis
    # Reviewable synthetic contrasts; these are not model or human judgements.
    from dataclasses import asdict
    for label, item, candidate, stage in [
        ("same_identity", listing, same, "place"),
        ("different_kind", listing, other, "place"),
        ("missing_identity", listing, Node(id="blank", domain="games", name="Blank"), "place"),
        ("scope_hold", held, same, "route"),
    ]:
        facts = candidate_facts(item, candidate)
        log.append("rule-firings.jsonl", {"sample_id": label, "evidence_role": "synthetic_behavior_only",
                   "input": item.model_dump(), "candidate_alternatives": [candidate.model_dump()],
                   "facts": facts, "rule_status": {r.id: r.status for r in rules},
                   "outcome": asdict(evaluator.evaluate(rules, stage, facts)),
                   "validator_outcome": "not_run", "human_outcome": "not_reviewed", "resulting_change": None})
    return {"status": "PASS", "shadow_rules": len(rules), "proposal_agentic_rules": len(agentic),
            "active_decisions": 0, "validator_checklist": 0, "numeric_tokens_preserved": True}


def profile(path: Path, catalog: Path | None, log: RunLog) -> dict:
    records = list(adapter.read_records(path))
    files = [path]
    if records and records[0]["games_provenance"]["source_rows_file"]:
        files.append(Path(records[0]["games_provenance"]["source_rows_file"]))
    before = {str(f): sha256(f) for f in files}
    manifest_path = path.with_name("manifest.json")
    manifest_checks = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest.get("output_sha256") or manifest.get("parquet_sha256")
        if expected:
            assert before[str(path)] == expected, f"Stale output manifest: {path}"
            manifest_checks["output_hash"] = True
        if len(files) > 1:
            expected = manifest.get("source_sidecar_sha256") or manifest.get("source_rows_sha256")
            if expected:
                assert before[str(files[1])] == expected, f"Stale sidecar manifest: {path}"
                manifest_checks["sidecar_hash"] = True
        assert manifest.get("rows", manifest.get("selected_rows")) == len(records)
        manifest_checks["rows"] = True
    status, reasons, kinds, labels = Counter(), Counter(), Counter(), Counter()
    feature_counts = Counter()
    digest = hashlib.sha256()
    accepted = []
    for row in records:
        scope = decide_scope(row)
        raw = {**row, **row["games_source_row"]}
        log.append("scope-decisions.jsonl", {
            "input_file": str(path.resolve()), "input_sha256": before[str(path)],
            "listing_id": adapter.listing_id(row), "native_id": raw.get("asin") or raw.get("source_listing_id"),
            "title": raw.get("title") or raw.get("listing_name"), "source_labels": category_labels(raw),
            "candidate_alternatives": list(scope.evidence) if scope.reason == "conflicting_game_kinds" else [scope.subtype] if scope.subtype else [],
            "scope_decision": scope.as_dict(), "explanation": scope.reason,
            "evidence_role": "exploratory_source_screen_not_gold", "validator_outcome": "not_run",
            "human_outcome": "not_reviewed", "resulting_change": None})
        status[scope.status] += 1
        reasons[scope.reason] += 1
        labels.update(category_labels({**row, **row["games_source_row"]}))
        digest.update(json.dumps([adapter.listing_id(row), scope.as_dict()], sort_keys=True).encode())
        if scope.status != "accept":
            continue
        listing = adapter.to_listing(row)
        accepted.append(listing)
        kinds[scope.subtype] += 1
        assert listing.id == adapter.listing_id(row)
        assert listing.fields["source_raw"] == row["games_source_row"]
        assert listing.fields["raw"] == {k: v for k, v in row.items() if k not in ("games_source_row", "games_provenance")}
        features = listing.fields["games"]["identity"]
        for axis, value in features.items():
            if axis != "title_key" and value not in (None, [], "unknown"):
                feature_counts[axis] += 1
    assert len(accepted) > 0
    assert len({x.id for x in accepted}) == len(accepted)
    with configured(path):
        assert list(domain().listings(5)) == accepted[:5]
        assert list(domain().listings()) == accepted
        assert not domain().nodes()
    catalog_matches = None
    if catalog:
        import pyarrow.parquet as pq
        keys = {r.get("asin") or r["games_source_row"].get("asin") for r in records}
        keys.discard(None)
        raw_matches = {}
        for batch in pq.ParquetFile(catalog).iter_batches(batch_size=2048):
            for raw in batch.to_pylist():
                if raw["asin"] in keys:
                    assert raw["asin"] not in raw_matches
                    raw_matches[raw["asin"]] = raw
        assert raw_matches.keys() == keys
        for row in records:
            raw = row["games_source_row"] or row
            if raw.get("asin"):
                assert all(raw.get(k) == v for k, v in raw_matches[raw["asin"]].items()), "RAW catalog mismatch"
        catalog_matches = len(raw_matches)
    assert before == {str(f): sha256(f) for f in files}
    schema = {}
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        schema = {f.name: str(f.type) for f in pq.ParquetFile(path).schema_arrow}
    return {"input": str(path), "sha256": before, "manifest_checks": manifest_checks,
            "modification_times_utc": {str(f): datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat() for f in files},
            "rows": len(records), "scope_counts": dict(status), "reason_counts": dict(reasons),
            "accepted_subtypes": dict(kinds), "accepted_feature_presence": dict(feature_counts),
            "source_category_counts": dict(labels.most_common(25)), "schema": schema,
            "catalog_rows_matched_exactly": catalog_matches, "decision_digest_sha256": digest.hexdigest(),
            "all_accepted_fields_preserved": True, "source_files_unchanged": True}


def current_raw_inventory(root: Path) -> dict:
    """Rediscover current boundary files; no cached audit counts or labels."""
    import pyarrow.parquet as pq
    files = []
    folders = sorted(p.name for p in root.iterdir() if p.is_dir())
    boundary_counts = {}
    for name in ("clothing", "clothes", "footwear", "foot", "games", "toys"):
        folder = root / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix != ".parquet" and path.name not in ("manifest.json", "parsing-manifest.json"):
                continue
            digest = sha256(path)
            info = {"path": str(path), "sha256": digest, "bytes": path.stat().st_size,
                    "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
            if path.suffix == ".parquet":
                parquet = pq.ParquetFile(path)
                info.update(rows=parquet.metadata.num_rows,
                            schema={f.name: str(f.type) for f in parquet.schema_arrow})
                # Inspect the current schema and bounded source rows before profiling.
                sample = next(parquet.iter_batches(batch_size=2), None)
                info["bounded_rows_inspected"] = len(sample) if sample is not None else 0
                if path.name.endswith("_listings.parquet") and name != "games":
                    counts = Counter(decide_scope(r).status for r in adapter.read_records(path))
                    boundary_counts[str(path)] = dict(counts)
                    if name in ("clothing", "clothes", "footwear", "foot"):
                        assert counts["accept"] == 0, "Apparel boundary accidentally admitted as games"
            else:
                doc = json.loads(path.read_text(encoding="utf-8"))
                info["manifest_rows"] = doc.get("rows")
            assert digest == sha256(path), "RAW input changed during inventory"
            files.append(info)
    return {"root": str(root), "folders": folders, "files": files,
            "separate_toys_directory_found": "toys" in folders,
            "boundary_scope_counts": boundary_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", type=Path, required=True)
    parser.add_argument("--also-listings", type=Path, action="append", default=[])
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--delivery-report", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--artifacts-dir", type=Path, help="New directory outside Git for data-bearing run logs")
    args = parser.parse_args()
    artifacts = args.artifacts_dir or ROOT / "runs/games/readiness" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log = RunLog(artifacts, ROOT, vars(args))
    report = {"scope_version": VERSION,
              "limitations": ["Source screening is exploratory, not held-out evaluation or human gold.",
                              "No placement/tree, model routes, agent/tool traces, validator or human reviews were run.",
                              "Shared registration, fact/agentic wiring and games-capable pipeline/gate remain pending."]}
    report["implementation_hashes"] = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(
        [*HERE.glob("*.py"), *HERE.glob("*.yaml"), *HERE.glob("memory/rules/*.yaml"),
         *HERE.glob("e2e/*.yaml"), *(ROOT / "rules/games").glob("*.yaml")])}
    try:
        execute(args, report, log)
    except Exception as error:
        report["status"] = "FAIL"
        report["artifact_index"] = log.finish(report, error)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    report["artifact_index"] = log.finish(report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(args.report), "artifacts": str(log.root),
                      "profiles": [{"rows": p["rows"], "scope": p["scope_counts"]} for p in report.get("profiles", [])]}))


def execute(args, report: dict, log: RunLog):
    report["smoke"] = smoke(args.listings)
    if not args.smoke_only:
        # Smoke above always precedes the substantive checks.
        report["synthetic_e2e"] = synthetic_e2e()
        report["rules_e2e"] = rules_e2e(log)
        report["profiles"] = [profile(p, args.catalog, log) for p in [args.listings, *args.also_listings]]
        if args.catalog:
            import pyarrow.parquet as pq
            report["catalog"] = {"path": str(args.catalog), "sha256": sha256(args.catalog),
                                 "rows": pq.ParquetFile(args.catalog).metadata.num_rows}
        if args.delivery_report:
            delivery = json.loads(args.delivery_report.read_text(encoding="utf-8"))
            entry = delivery["repaired_domains"]["games"]["subsets"][0]
            drive = Path(entry["path"])
            current_hash = sha256(drive)
            assert current_hash == entry["sha256"], "Current RAW differs from delivery; rediscover manifests"
            assert current_hash == sha256(args.listings), "Selected local source differs from active Drive source"
            report["drive_active_verified"] = {"path": str(drive), "sha256": current_hash, "matches_delivery_and_local": True,
                                                "delivery_report": str(args.delivery_report), "delivery_sha256": sha256(args.delivery_report)}
            report["current_raw_inventory"] = current_raw_inventory(drive.parents[2])
        report["readiness"] = {"adapter": "ready", "placement": "bootstrap_required", "taxonomy_nodes": 0,
                               "gold_read": False, "model_calls": 0, "shared_registration": "integration_owner_required"}
        report["verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "PASS"


if __name__ == "__main__":
    main()
