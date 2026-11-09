"""Repeatable offline E2E: source -> adapter -> rule tool -> bounded construction -> evidence report."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from taxo import evaluator, memory
from taxo.bootstrap import ReportedBrands, construct
from taxo.core.config import DOMAINS_DIR, ROOT
from taxo.core.domain import load
from taxo.core.rules import run_rules
from taxo.core.schemas import Listing, Node, Status
from taxo.lattice.vocab import load as vocab_load, tokens
from taxo.tools.clothing import scope


def snapshot(path):
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    stat = path.stat()
    out = {"path": str(path), "bytes": stat.st_size, "sha256": digest,
           "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
    if path.suffix == ".parquet":
        pf = pq.ParquetFile(path)
        out.update(rows=pf.metadata.num_rows, columns=len(pf.schema_arrow), schema=str(pf.schema_arrow))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--listings", type=Path, required=True)
    ap.add_argument("--raw-root", type=Path, required=True, help="current mounted RAW root; inventory only")
    ap.add_argument("--catalog", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=64, help="construction bound; source profiling covers all rows")
    a = ap.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise FileExistsError("choose a fresh --output directory")
    a.output.mkdir(parents=True, exist_ok=True)
    os.environ["TAXO_CLOTHING_LISTINGS"] = str(a.listings)
    os.environ.pop("TAXO_CLOTHING_SOURCE_ROWS", None)
    os.environ.pop("TAXO_CLOTHING_MANIFEST", None)
    os.environ.pop("TAXO_CLOTHING_TAXONOMY", None)
    from domains.clothing.adapter import source_manifest
    # Smoke before the substantive E2E: configuration, schema and one real Listing.
    domain = load("clothing")
    first = next(domain.listings(limit=1))
    assert first.id and first.title and first.fields["raw_source"]
    assert list(domain.nodes()) == []
    (a.output / "smoke.json").write_text(json.dumps({"passed": True, "rows_loaded": 1, "taxonomy_nodes": 0}) + "\n")
    inventory = []
    for path in sorted(a.raw_root.rglob("*")):
        relative = str(path.relative_to(a.raw_root)).lower()
        if path.is_file() and any(t in relative for t in ("cloth", "foot", "toy", "games")) and (path.suffix == ".parquet" or "manifest" in path.name):
            inventory.append(snapshot(path))
    paths = [a.listings, a.listings.with_name("source_rows.parquet"), a.listings.with_name("manifest.json"), a.catalog]
    before = [snapshot(p) for p in paths]
    evidence = source_manifest()
    assert before[-1]['sha256'] == evidence['source_catalog_sha256']
    listings = list(domain.listings())
    silver = pq.read_table(a.listings).to_pylist()
    side = pq.read_table(a.listings.with_name("source_rows.parquet")).to_pylist()
    by_id = {str(r["observation_key"]): r for r in side}
    source = {r["asin"]: r for r in pq.read_table(a.catalog).to_pylist()}
    for listing, row in zip(listings, silver, strict=True):
        raw = by_id[listing.id]
        assert listing.id == str(row["observation_key"])
        assert all(listing.fields[k] == v for k, v in row.items())
        assert listing.fields["raw_source"] == raw
        assert listing.title == row["listing_name"] and listing.brand == row["brand_name"]
        assert all(raw[k] == v for k, v in source[raw["asin"]].items())
    assert len(listings) == evidence["rows"] == len(by_id)
    assert len({l.id for l in listings}) == len(listings)
    assert list(domain.listings(limit=0)) == []
    assert len(list(domain.listings(limit=3))) == 3
    profile = {"rows": len(listings), "distinct_asins": len({r['source_listing_id'] for r in silver}),
               "missing_brand": sum(not l.brand for l in listings),
               "missing_variant_options": sum(not r["variant_options_json"] for r in silver),
               "missing_source_variant_id": sum(not r["source_variant_id"] for r in silver),
               "missing_source_description": sum(not r['description'] for r in side),
               "brand_merchant_differ": sum(bool(r['brand'] and r['merchant'] and r['brand'].casefold() != r['merchant'].casefold()) for r in side),
               "duplicate_normalized_title_rows": len(side) - len({tokens(r['title']) for r in side}),
               "scope_decisions": dict(Counter(l.fields['domain_scope']['decision'] for l in listings)),
               "scope_reasons": dict(Counter(l.fields['domain_scope']['reason'] for l in listings)),
               "quality_issues": dict(Counter(i for l in listings for i in l.fields['quality_issues']))}
    patterns = {"explicit_style_model": r"\b(?:style|model)\b", "numeric_style_examples": r"\b(?:501|505|550|874|574|G1100|G64000|Og35063)\b",
                "size_age_fit": r"\b(?:size|[2-6]XL|months|years|petite|big and tall)\b",
                "multipack_set_or_2in1": r"\b(?:pack|set|multipack|2 in 1|pieces)\b",
                "licensed_graphic_terms": r"\b(?:toy story|minecraft|pokemon|marvel|disney|nintendo)\b",
                "material_terms": r"\b(?:cotton|linen|polyester|wool|viscose)\b"}
    profile["title_pattern_counts"] = {k: sum(bool(re.search(p, r['title'], re.I)) for r in side) for k, p in patterns.items()}
    boundary = []
    for entry in inventory:
        if 'foot' in entry['path'].lower() and Path(entry['path']).name == 'source_rows.parquet':
            rows = pq.read_table(entry['path']).to_pylist()
            counts = Counter(scope(r)['decision'] for r in rows)
            overlap = len({r['asin'] for r in rows} & {r['asin'] for r in side})
            assert not counts['accept'] and overlap == 0
            boundary.append({'path':entry['path'],'rows':len(rows),'clothing_scope_decisions':dict(counts),'asin_overlap':overlap})
    # Synthetic counterexamples travel through the same scope and rule-tool paths; not taxonomy gold.
    cases = [("Example Toy Story T-Shirt", "Boys' Novelty T-Shirts", "accept"),
             ("Example Game Graphic Hoodie", "Men's Sweatshirts", "accept"),
             ("Example Running Shorts 2 in 1", "Women's Running Shorts", "accept"),
             ("Example Cotton Socks 3 Pack", "Men's Crew Socks", "accept"),
             ("Example Two Piece Lounge Set", "Women's Sweatsuits", "hold"),
             ("Example Dress Shoes", "Men's Oxfords", "reject"),
             ("Example Running Sneakers", "Women's Running Shoes", "reject"),
             ("Example Detachable Collar", "Women's Collars", "reject"),
             ("Example Nipple Covers", "Everyday Bras", "reject"),
             ("Example Doll Dress", "Doll Clothing", "reject"),
             ("Example Product", "Clothing, Shoes & Jewelry", "hold")]
    for title, rank, expected in cases:
        assert scope({"title": title, "best_seller_ranks": [f"#1 in {rank}"]})['decision'] == expected, title
    rules = memory.rules_for("clothing", tuple(domain.pack['families']))
    assert all(r.status == Status.PROPOSAL for r in rules)
    assert memory.agentic_for("clothing") == []
    assert len(memory.agentic_for("clothing", include_proposals=True)) == 3
    assert evaluator.load(ROOT / 'rules/clothing') == []  # RuleSpec must not become an empty-condition evaluator rule.
    vocab = vocab_load(DOMAINS_DIR / 'clothing/vocab.yaml')
    identity = tokens("Example 874 G1100 2 in 1 6-12 months blue cotton")
    tagged = vocab.tag(identity)
    assert not any(tagged.var) and not any(tagged.frag)
    from taxo.pipeline import Item, run as pipeline_run
    from taxo.bootstrap import _slug
    item = Item(id='synthetic:identity', title='Example Pants 2 in 1 [874]', brand_field='Example')
    pipeline_run([item], ReportedBrands({_slug('Example'):'Example'}, suffixes=()), vocab, [], domain='clothing', full_title=True)
    assert item.key == 'pants 2 in 1 874'
    node = Node(id='synthetic:n', domain='clothing', name='Example Shirt Style G1100', path=['Example','Shirt Style G1100'])
    listing = Listing(id='synthetic:l', domain='clothing', title='Example Shirt Style G64000')
    assert not run_rules(rules, listing, node, {node.id: node}).decided
    from agents import RunContextWrapper
    from agents.tool_context import ToolContext
    from taxo.roles.placer import PlaceContext, check_rules, make_placer
    rule = next(r for r in rules if r.id == 'cl-style-code-conflict')
    ctx = PlaceContext('clothing', {node.id: node}, [rule.model_copy(update={'status': Status.SHADOW})], listing)
    params = json.dumps({'listing_title': 'spoofed input', 'node_id': node.id})
    tool_ctx = ToolContext.from_agent_context(RunContextWrapper(context=ctx), 'offline', tool_name='check_rules', tool_arguments=params)
    findings = asyncio.run(check_rules.on_invoke_tool(tool_ctx, params))
    findings = json.loads(findings) if isinstance(findings, str) else findings
    assert findings == [] and len(ctx.shadow) == 1
    ctx.rules = [rule.model_copy(update={'status': Status.ADMITTED})]
    findings = asyncio.run(check_rules.on_invoke_tool(tool_ctx, params))
    findings = json.loads(findings) if isinstance(findings, str) else findings
    assert findings[0]['decision'] == 'veto' and findings[0]['binding']
    assert 'Treat the reported brand' not in make_placer('clothing').instructions
    for check, title, candidate in [('clothing_type_conflict','Example Shirt','Example Pants'),
                                     ('clothing_set_conflict','Example 3 Pack Shirts','Example 2 Piece Lounge Set')]:
        from taxo.tools.checks import run
        assert run(check, Listing(id='s',domain='clothing',title=title), Node(id='n',domain='clothing',name=candidate), {})
    from taxo.tools.checks import run
    assert not run('clothing_set_conflict', Listing(id='s',domain='clothing',title='Example Shorts 2 in 1'), Node(id='n',domain='clothing',name='Example Shorts'), {})
    assert ReportedBrands({'example': 'Example'}, suffixes=()).find(None, None, 'Example') == (None,'missing_source_brand')
    # Adapter failure paths use tiny synthetic exports, never mutate the source dataset.
    import pyarrow as pa
    fixture = a.output / 'synthetic-source'
    fixture.mkdir()
    export_path, side_path = fixture / 'clothing_listings.parquet', fixture / 'source_rows.parquet'
    export = [{"observation_key": -900000000000000001, "listing_key": -123, "source_listing_id": "SYNTHETIC",
               "source_id": "synthetic", "listing_name": "Example Pants Style 874 2 in 1", "brand_name": None}]
    source_row = {"observation_key": export[0]['observation_key'], "listing_key": -123, "asin": "SYNTHETIC",
                  "title": export[0]['listing_name'], "brand": None, "merchant": "SellerOnly",
                  "best_seller_ranks": ["#1 in Men's Pants"]}
    pq.write_table(pa.Table.from_pylist(export), export_path)
    pq.write_table(pa.Table.from_pylist([source_row]), side_path)
    def manifest():
        (fixture / 'manifest.json').write_text(json.dumps({'domain':'clothing','rows':len(export),
            'output_sha256':snapshot(export_path)['sha256'],'source_sidecar_sha256':snapshot(side_path)['sha256']}))
    manifest()
    real_path = os.environ['TAXO_CLOTHING_LISTINGS']
    os.environ['TAXO_CLOTHING_LISTINGS'] = str(export_path)
    synthetic = list(domain.listings())
    assert synthetic[0].id == '-900000000000000001' and synthetic[0].brand is None
    assert synthetic[0].fields['raw_source']['merchant'] == 'SellerOnly'
    with export_path.open('ab') as f:
        f.write(b'changed')
    try:
        list(domain.listings())
        raise AssertionError('hash mismatch was accepted')
    except ValueError as error:
        assert 'hashes' in str(error)
    pq.write_table(pa.Table.from_pylist(export), export_path)
    source_row['asin'] = 'MISMATCH'
    pq.write_table(pa.Table.from_pylist([source_row]), side_path)
    manifest()
    try:
        list(domain.listings())
        raise AssertionError('sidecar mismatch was accepted')
    except ValueError as error:
        assert 'identity mismatch' in str(error)
    source_row['asin'] = 'SYNTHETIC'
    pq.write_table(pa.Table.from_pylist([source_row]), side_path)
    export.append(dict(export[0]))
    pq.write_table(pa.Table.from_pylist(export), export_path)
    manifest()
    try:
        list(domain.listings())
        raise AssertionError('duplicate identity was accepted')
    except ValueError as error:
        assert 'duplicate' in str(error)
    os.environ['TAXO_CLOTHING_LISTINGS'] = real_path
    assert yaml.safe_load((DOMAINS_DIR / 'clothing/validator.yaml').read_text())['checklist'] == []
    guards = []
    for args in [['-m','taxo.pipeline','clothing'], ['-m','taxo.gate','clothing','unused-before','unused-after','--round','1','--label','offline'], ['-m','taxo.cli','place','clothing','--n','1']]:
        proc = subprocess.run([sys.executable,*args], capture_output=True, text=True)
        assert proc.returncode != 0 and ('construct' in proc.stderr or 'bootstrap' in proc.stderr)
        guards.append({'command': args, 'exit_code': proc.returncode, 'message': proc.stderr.splitlines()[-1]})
    bounded = construct('clothing', a.limit, a.output / 'construction')
    assert bounded['input_rows'] == a.limit and bounded['agent_calls'] == 0 and not bounded['gold_loaded']
    assert bounded['accuracy'] is None and bounded['unscoped_rows'] == 0
    assert all(r['status'] == 'proposal' for r in bounded['pair_rules'])
    after = [snapshot(p) for p in paths]
    assert before == after, 'source files changed during verification'
    report = {'status':'PASS','inspected_at_utc':datetime.now(timezone.utc).isoformat(),
              'command': [sys.executable, '-m', 'checks.clothing_readiness', *sys.argv[1:]],
              'source': evidence, 'source_files':before, 'current_raw_inventory':inventory,
              'separate_toys_files_observed': [r['path'] for r in inventory if 'toy' in r['path'].lower() and r['path'].endswith('.parquet')],
              'profile': profile, 'assertions': {'all_97_export_fields_preserved':True,'all_23_original_source_fields_equal':True,
              'signed_observation_ids_preserved':True,'scope_synthetic_cases':len(cases),'actual_placer_rule_tool':True,
              'proposal_and_shadow_nonbinding':True,'numeric_identity_tokens_preserved':True,'source_files_unchanged':True,
              'hash_mismatch_rejected':True,'sidecar_mismatch_rejected':True,'duplicate_ids_rejected':True,'seller_not_brand':True},
              'footwear_boundary':boundary,
              'guards': guards, 'bounded_construction':bounded, 'gold_read':False,'model_calls':0,'accuracy':None}
    (a.output / 'report.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status':report['status'],'profile':profile,'report':str(a.output/'report.json')},indent=2))


if __name__ == '__main__':
    main()
