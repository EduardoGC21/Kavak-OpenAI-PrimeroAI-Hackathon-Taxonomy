# Toys domain

This domain is a source-backed bootstrap, not a constructed taxonomy. All new
placement rules are proposals; no human gold or trusted product tree exists.

## Failure modes and verification design (before implementation)

The offline end-to-end (E2E) check must cover:

- Contaminated department membership admitting games, puzzles, partyware, pets,
  stationery, cosmetics, costumes, household utilities or professional devices.
- Character/franchise mentions overriding the actual product (a game about dolls
  remains a game); title/rank conflict; root-only evidence; missing titles.
- Toy accessories merging with complete products; compatibility targets or
  sellers being inferred as makers; missing brand fields being fabricated.
- Numeric set/model identifiers, scales, numbered characters, editions, piece
  contents, pack multiplicity and random variants being erased or conflated.
- Sidecar joins by row order, duplicate keys, missing rows, wrong ASINs, lost
  signed observation keys, altered titles or discarded raw/provenance fields.
- Limits applying before scope filtering, zero/negative limits, unstable IDs
  across source order or raw/compatibility formats, duplicate listing identities.
- Proposal rules becoming active, unavailable checks being silently enabled,
  missing taxonomy producing fake nodes, invalid taxonomy links being accepted.
- A readiness scan exceeding its configured population bound or overwriting RAW.

Local proposal-check failure modes: absent structured candidate identifiers must
not invent a model; a number merely present in a title cannot prove identity;
partial numeric matches must not satisfy an identifier; complete toys supplied
with accessories must not be labeled accessory-only; random color/character
offers must not auto-select an exact variant. These checks only ask for review.

Synthetic cases check implementation behavior only and are never gold. Run a
smoke check before the substantive E2E check; both write repeatable JSON reports.

## Current sources and exploration evidence

Re-discovered **2026-11-09 20:53 UTC**, after the RAW update. There is **no
separate toys Parquet** under the current local data/audit or Drive RAW roots.
The authoritative current mixed delivery is still named `games/subset-1`.
The adapter accepts an explicit future toys file without changing checkout or
shared registration. Do not rename or overwrite the delivered data.

Local source directory:
`C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/games/`.
Drive RAW root is recorded in
`C:/Users/eduar/Desktop/HACKATON/tasks/amazon-silver-format/drive-delivery-report.json`;
its `games/subset-1` files currently match the local files byte for byte.
That old delivery report's **5,161-row count is stale**. Current evidence is
`tasks/raw-content-audit/delivery-report.json`, the delivered manifests and
freshly computed hashes. No file from the older snapshot supplies current counts.

| Current input | Rows / columns | Modified UTC | SHA-256 |
|---|---|---|---|
| `silver/games/games_listings.parquet` | 4,338 / 97 | 2026-11-09 20:41:37.886 | `4749cb77a529b202d94a8d1e1b5f41cb7a45f23ae879e17d601f9c1ef26d5054` |
| `silver/games/source_rows.parquet` | 4,338 / 24 | 2026-11-09 20:41:37.933 | `3b70a84d039353e98bd76c5b1c0cafb4ac75f3fa9d2b6478fa10c591c98fa795` |
| `new-domain-inputs/games/games_listings.parquet` | 4,338 / 22 | 2026-11-09 20:41:16.682615 | `d3af8090e9e0fe0550159c533f2f05345f7ba0e14c4a3b9f8aac0fc5fa77e190` |
| Original `data/different_lines/amazon.parquet` | 100,278 / 22 | recorded in evidence | `228e808136c7bf5da07bb0d0a07ce6897993f11bcf99e606da45144d807a5a24` |

The selection input is under `tasks/raw-content-audit/`; it is an audit-selected
subset of the original Amazon source, not human gold. The full current 4,338-row
RAW sidecar was matched exactly against original Amazon records by Amazon
Standard Identification Number (ASIN), including all 22 original columns.
The source catalogue was filtered to those ASINs for this lineage check.

The updated clothing file has 5,000 rows, hash
`f3a47a08b7513f4885c9917b48940ec419491e29de5ab01b26b8db892403e8b5`;
updated footwear has 2,948 rows, hash
`75b7f232e3d963ca35594a5f484f2a85e9f69a56562bede16792796eaabd6601`.
Both retain the 97-column compatibility schema. They are boundary evidence only;
no additional domain was implemented. The toys screen admitted none of their
7,948 rows (7,907 excluded, 41 held). Character graphics and plush footwear
cannot establish toy scope.

Full schema strings, current manifests, paths, modification times and hashes are
in [inputs.json](../domains/toys/evidence/inputs.json) and the title-free
[baseline.json](../domains/toys/evidence/baseline.json). RAW titles/payloads and
per-row decision ledgers are not committed. Prior `other-domains/REVIEW.md` and
`other_domain_rules.py` informed exploration of contamination; they are not
imported or used as labels by this adapter.

## Contract and field mapping

`Domain("toys", pack).listings(limit)` yields `Listing` objects after scope
filtering; a limit counts included listings, not input rows. Duplicate ASINs,
missing identities and broken sidecar joins fail explicitly. `source_records()`
exposes every candidate with an include/exclude/hold reason so filtered rows are
auditable. The readiness command writes that ledger outside Git.

| Listing value | Source |
|---|---|
| `id` | `amazon:<asin>`; identical across RAW/compatibility files and row order |
| `title` | RAW `title` verbatim; never the cleaned compatibility title |
| `source` | export `source_id`, otherwise `amazon_historical_parsed` |
| `brand` | RAW `brand` claim only; placeholders become null, never seller/byline inference |
| `fields.raw` | complete RAW sidecar record or original RAW row |
| `fields.source_export` | complete export row, including all 97 compatibility columns |
| observation / listing keys | original signed integers preserved separately from ASIN identity |
| description / A+ / seller | RAW `description`, `aplus_content`, `merchant`, with export fallback |
| provenance / identifiers | original `bronze_reference_json`, `identifiers_json` and export fields |
| `identity_text` | whitespace-normalized full title; numerals and punctuation preserved |
| `identity_hints` | quoted title spans for numbers, scales, contents, packs, editions, random offers and compatibility |

The RAW schema also carries `byline`, `first_source_row`, `first_term`, `ordinal`,
`scrape_status`, `page_type`, source categories, bestseller ranks, prices,
availability and review fields. Nothing is discarded. Food-named export fields
are format compatibility fields and supply no food semantics or trusted scope.
No maker, character or licensor entity is fabricated from title spans.

`Domain.nodes()` returns `[]` when `TAXO_DATA_DIR/toys/taxonomy.jsonl` is absent.
An explicitly supplied tree must contain `Node`-compatible records with unique
IDs, supported levels and valid acyclic parent links. Children are linked from
parents. Empty bootstrap output is not a trusted Pedia tree.

## Conservative scope and identity baseline

The deterministic screen uses broad product-type/rank evidence, never ASIN or
brand exceptions. A root `Toys & Games` rank alone is insufficient. It retains
clear building sets, dolls/figures/plush, pretend-play products, sensory/fidget
toys, remote-control (RC) toys and directly evidenced toy accessories. Clear
board/card/dice/domino games, puzzles and video-game goods belong to games.
Conflicting toy titles and games ranks are held. Source failures or insufficient
evidence are held; nonplay partyware, pet-only goods and unsupported utilities
are excluded or held with explicit reasons. Incidental party wording does not
erase a clear toy, but genuine toy/decoration conflicts stay unresolved.

Initial conventions distinguish product/set/model identity from color/style
variants and listing quantities. Piece contents are not repeated-unit pack
counts. Scale, edition, numbered names and set/model numerals survive loading;
random/assorted offers do not imply a chosen variant. A figure stand or RC part
is not the complete toy it supports. `identity_hints` are lexical observations,
not resolved attributes: for example, `Set of 4` may describe a mixed set rather
than identical units, and a bare `2` may be an age, quantity or numbered name.

There are three code proposals and three agentic proposals, with explicit origin
and evidence. No rules have been promoted. The validator checklist starts empty.
`title_lacks_product` is an existing shared check. Two simple local checks in
`taxo.tools.toys` ask for review when a candidate's explicit identifier is absent,
or when accessory/random-offer evidence conflicts with a complete toy/exact
variant. They abstain; silence never confirms identity. Candidate fields are
`identity_identifiers: {set_number: '...', model_number: '...'}`,
`offering_kind: complete_toy`, and `variant_axis: color|character|style` on a
variant node. A later tree builder must ground those fields in source evidence.

## Configuration and repeatable commands

Canonical inputs are exactly one of `TAXO_DATA_DIR/toys/listings.parquet` or
`listings.jsonl`. Both RAW schemas and the observed compatibility schema are
supported. For a compatibility file, `source_rows.parquet` beside it is required;
join keys are `observation_key`, verified against ASIN and `listing_key`, never
row position. An optional `TAXO_TOYS_SOURCE_ROWS` overrides the sidecar path.
Set `TAXO_TOYS_LISTINGS` to read the current mixed file in place. No data copying
or shared registration is required for these commands.

From the repository root, with Python 3.11+ and `pydantic`, `pyyaml`, `pyarrow`
installed (Parquet support is optional and was not added to shared packaging):

```powershell
$env:TAXO_TOYS_LISTINGS = 'C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/games/games_listings.parquet'
.venv/Scripts/python.exe -m taxo.tools.toys --smoke --output runs/toys/baseline-smoke
.venv/Scripts/python.exe -m domains.toys.e2e --source $env:TAXO_TOYS_LISTINGS --boundary-source C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/clothing/clothing_listings.parquet --boundary-source C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/footwear/footwear_listings.parquet --output runs/toys/baseline-e2e
.venv/Scripts/python.exe -m taxo.tools.toys --catalog C:/Users/eduar/Desktop/HACKATON/data/different_lines/amazon.parquet --max-rows 6000 --output runs/toys/baseline-lineage
.venv/Scripts/python.exe -m pytest tests/test_isolation.py -q
```

To inspect decisions without loading the shared registry, use
`from domains.toys.adapter import source_records, source_path` and iterate
`source_records(source_path())`. To inspect Parquet schema/counts use
`pyarrow.parquet.ParquetFile(path).schema_arrow` and `.metadata.num_rows`.
Check current manifests/hashes before comparing later runs against this baseline.

## Recorded baseline and later work

Smoke passed; E2E passed **123 assertions**, including all 2,341 admitted RAW
records and both updated boundary datasets. Existing isolation checks: 2 passed.
No model calls, sealed-gold reads, taxonomy construction, Drive writes or source
mutations occurred.

The 4,338 mixed rows yield **2,341 include, 1,352 exclude, 645 hold**. Included
rows have 1,771 numeric-token hints, 99 scale hints, 314 piece-content hints,
180 explicit pack hints, 110 random/assorted hints and 25 edition hints. These
overlap and describe explored data, not independent validation or accuracy.

Coverage is intentionally frozen here. The largest unresolved group is 530 rows
without specific positive toy evidence; other holds include generic art supplies,
play-versus-utility electronics/jewelry, professional tools, shared pet use and
conflicting ranks. Some genuine toys will remain held. Do not add per-listing or
brand exceptions to recover them: sample holds for human review in later loops.

The integration owner still needs to:

1. Add `toys` to shared domain registration and load this pack's three code and
   three agentic proposals. `adapter.load_rules()` already loads the code specs.
2. If enabling local code checks in the future, register
   `toys_identifier_evidence -> (taxo.tools.toys.identifier_evidence, 'abstain')`
   and `toys_offering_evidence -> (taxo.tools.toys.offering_evidence, 'abstain')`
   in the shared check registry. They are intentionally inert proposals now.
3. Review shared parsing/lattice assumptions: bare numerals are still marked as
   fragments by the shared vocabulary loader, title parsing cuts at colons and
   the brand ladder can infer from title text. This adapter preserves the full
   identity evidence, but the later pipeline must consume it safely. The empty
   vocabulary strips no tokens; it does not fix those shared heuristics.
4. Keep universal food count/omission proposals unvalidated for toys; do not
   inherit their admission from another domain. Build source-backed candidates,
   obtain human gold, and use the actual learning/evaluation gates before rule
   promotion. No exact full-taxonomy command is authorized or ready yet.
