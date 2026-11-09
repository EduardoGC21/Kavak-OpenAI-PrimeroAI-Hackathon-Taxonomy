# Games domain

Implemented from scaffold `06be9acde9b3964415e900e7d9da23fd0ac8e2a5`.
The adapter and offline checks are ready for integration. Taxonomy construction,
human gold, placement scoring and model runs remain later work.

## Current source evidence

The canonical home is the Drive `DATA/Listings/RAW` root recorded in
`C:/Users/eduar/Desktop/HACKATON/tasks/amazon-silver-format/drive-delivery-report.json`.
That original delivery record is stale. Use the current replacement record at
`tasks/raw-content-audit/delivery-report.json` and each subset's current manifests.
All workspace-relative paths below are relative to
`C:/Users/eduar/Desktop/HACKATON`.

- Current local input: `data/different_lines/silver/games/games_listings.parquet`,
  matching Drive `games/subset-1/games_listings.parquet`: **4,338 rows**, 97 columns,
  SHA-256 `4749cb77a529b202d94a8d1e1b5f41cb7a45f23ae879e17d601f9c1ef26d5054`.
- Required sibling `source_rows.parquet`: 4,338 rows, 24 columns,
  SHA-256 `3b70a84d039353e98bd76c5b1c0cafb4ac75f3fa9d2b6478fa10c591c98fa795`.
- Equivalent original-format selection:
  `tasks/raw-content-audit/new-domain-inputs/games/games_listings.parquet`,
  4,338 rows, 22 columns, SHA-256
  `d3af8090e9e0fe0550159c533f2f05345f7ba0e14c4a3b9f8aac0fc5fa77e190`.
- Original catalogue: `data/different_lines/amazon.parquet`, 100,278 rows,
  SHA-256 `228e808136c7bf5da07bb0d0a07ce6897993f11bcf99e606da45144d807a5a24`.
  All 4,338 selected RAW rows were compared field-for-field against this source.

The old 5,161-row mixed export (`064d64e9...`) was replaced during this task.
Current files were rediscovered after the user's update. No separate `toys`
directory or toys-named parquet was found in the current Drive RAW root or local
candidate sources. The folder called games still mixes actual games, toys and
nonplay objects. Recheck this before a future run; a later toys export is not
automatically games input.

Updated clothing and footwear were inspected only as boundary evidence:
5,000 clothing rows (`f3a47a08...`) and 2,948 footwear rows (`75b7f232...`).
Neither produced games admissions. The committed
[evidence report](../domains/games/e2e/evidence-report.json) records complete
paths, content hashes, schemas, modification times, current manifests, counts
and verification time. RAW files and Drive were read only. The historical audit
and current audit acceptance are machine evidence, never human gold.

## Transport schema and field contract

The 97-column export is **Food Silver format compatibility only**. `food_domain`,
`food_scope_status`, empty category paths and format issue flags carry no games
meaning. No Pedia tree is implied.

| Listing contract | Mapping |
|---|---|
| `id` | Exact string of signed `observation_key`, including zero; no float conversion |
| Original-format ID | `amazon_historical_parsed:<asin>`; observation keys do not exist in this format |
| `source` | `source_id`, or explicit source, or Amazon origin for an ASIN |
| `title` | RAW `title` from sidecar; original canonical `listing_name` also retained |
| `brand` | Nonempty source `brand` / `brand_name` only; generic/unknown becomes null |
| `fields.raw` | Every canonical input field, unchanged |
| `fields.source_raw` | Every joined sidecar field, unchanged |
| `fields.provenance` | Absolute listing and sidecar paths |
| `fields.games` | Versioned scope status, subtype, reason/evidence and identity features |

Sidecars join by exact observation key, not row order. Duplicate, missing,
extra or native-ASIN/listing-key-conflicting joins fail. Full readiness checks
validate the entire file; a limited iterator intentionally stops early.
The original-format path preserves every RAW field in `fields.raw` instead.
IDs are stable within their supplied grain; cross-format reconciliation uses
the preserved ASIN rather than pretending ASIN and observation ID are identical.

RAW retains source ordinal, first source row/search term, scrape status, page
type, title, brand/byline, description, A+ content, analysis text, price, merchant,
rating/review count, categories and bestseller ranks. Capture time, market,
verified seller identity, detailed platform metadata and many brands are absent.
Do not fill these from currency, search term, a store byline, franchise, or a
compatible console. Source brand is an **unverified clue**, not trusted maker
resolution. No seller/character/compatibility-to-brand inference occurs here.

## Scope and identity

`domains.games.scope.decide_scope(row)` returns `accept`, `exclude` or `hold`,
plus stable reason, subtype, evidence and screen version. `read_records()`
exposes all rows for review; `Domain.listings(limit)` yields only accepted ones
and applies the limit after filtering. A missing title, bad capture, unsupported
identity or conflicting kinds is held, with a reason.

Included kinds are `board_game`, `card_game`, `dice_game`, `domino_game`,
`puzzle`, `tabletop_accessory`, `video_game_software`, `video_game_hardware`,
`video_game_accessory`, `video_game_dlc`, `video_game_currency`. Hardware bundles
remain hardware; compatibility targets stay separate from accessory identity.
Subscriptions are explicitly held until their entitlement convention is agreed.

Evidence comes from title, specific source categories/ranks and, for thin board
game titles, description plus a specific board-game category. Broad departments
and search terms never admit a row alone. Titles can establish explicit gaming
accessory identity even with thin categories. Clear figures, dolls, plush,
building sets, RC parts, pretend play and fidgets belong to toys. A figure with
a redemption code remains a toy. Mixed puzzle/decor/dollhouse evidence is held.
Film evidence overrides a bad game rank; pet-only products, nonplay partyware
and generic iPad styluses are excluded. Generic electronics/stationery without
gaming identity remain held. Art-marker/bingo conflicts and miniature/starter
sets with insufficient complete-game evidence are held.

Current deterministic counts: 1,113 accepted, 1,715 excluded, 1,510 held.
Accepted subtype counts: board 199; card 221; dice 12; domino/tile 36; puzzle 69;
tabletop accessory 66; video software 194; hardware 32; accessory 277; currency 7.
No current row establishes the dedicated DLC subtype, though the synthetic
contract verifies it. Conflicting card/board marketing and sparse source titles
cause intentional undercoverage. These are screen outputs, **not precision or
recall measurements**, and the held rows require later review.

The adapter preserves the complete title and an unstripped normalized
`title_key`, including numbered sequels, models and sets. Identity evidence
includes explicit editions, languages, platform generations, compatible
platforms, distribution, expansion/bundle role, base-game requirements,
standalone-play wording and puzzle piece counts. Missing values remain unknown;
no implicit English, standard edition, base game or physical disc is assigned.
Puzzle piece count differs from an outer multipack count. Price, seller,
condition, age/player guidance, playtime and outer pack count are attributes.
Colour or storage capacity may be variants only after product/model identity is
established; neither is stripped generically.

These features are conservative evidence extractors, not complete parsers of
all platform aliases, edition names, languages or bundle contents. Preserve RAW
when unknown. Expansion wording does not by itself prove dependence; separate
`requires_base_game` and `standalone_play` features retain affirmative evidence.

## Rules and integration handoff

- Pack, vocabulary, empty validator checklist and seven agentic proposals live
  in `domains/games/`. Nothing claims human validation.
- Four evaluator-format rules in `rules/games/` are **shadow**. They report kind
  conflict, identity-axis conflict, missing candidate identity and unsupported
  scope without deciding. Scope filtering is explicit ingestion policy, not
  admission of a learned placement rule.
- `domains.games.checks.candidate_facts(listing, node)` supplies the existing
  `taxo.evaluator` fact structure. Candidate nodes must carry
  `fields.games.subtype` and `fields.games.identity`. Missing evidence is reported
  for review; no global check registry or shared engine was modified.
- `vocab.yaml` deliberately overrides the shared numeric size pattern and
  strips nothing. The shared lattice still marks bare numerals as fragments;
  later games matching must retain `title_key`, verify model/sequel identity,
  and partition by subtype before counting. Do not run the fragrance-specific
  pipeline unchanged and call its output games taxonomy.
- `load_taxonomy()` returns `[]`: bootstrap is required. The readiness status
  distinguishes adapter readiness from placement readiness.

The integration owner must register `games` in `taxo.core.domain.DOMAINS` and
any shared command choices; connect games pack/vocabulary/agentic rules and the
four YAML rules; feed `candidate_facts` into evaluation; preserve listing fields
and candidate subtype/identity metadata; and partition candidates by kind before
scoring/lattice grouping. The shared `memory.rules_for` loader does not load
domain-local agentic files or `rules/games` by itself. Do not promote anything
merely because these engineering checks pass. Later work needs a proposed tree,
human review/gold and the appropriate evaluation gate.

On this branch, `taxo/roles/placer.py` still calls `rule_engine.apply_all`, while
`taxo/core/rules.py` exposes `run_rules` instead. This shared integration gap is
confirmed by source inspection, not repaired here. The runnable pipeline/gate
is fragrance-specific and agentic files remain unwired. Clothing/shared owner
owns those fixes; direct-import readiness does not prove a full games run.

## Configuration and repeatable checks

Dependencies used locally: Python 3.13, PyArrow 26, Pydantic 2, PyYAML 6;
PyArrow is optional to the shared project but required for these parquet inputs.
No shared dependency file was changed.

Canonical default: exactly one of `TAXO_DATA_DIR/games/listings.jsonl`,
`games_listings.parquet` or `listings.parquet`. Ambiguous/missing defaults fail.
For the current mixed source set an explicit path; compatibility parquet
automatically uses sibling `source_rows.parquet`. Override the sidecar with
`TAXO_GAMES_SOURCE_ROWS` only when needed. No recursive subset selection or stale
historical fallback is performed.

```powershell
$env:TAXO_GAMES_LISTINGS = 'C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/games/games_listings.parquet'
# TAXO_GAMES_SOURCE_ROWS is optional; the sibling sidecar is used by default.
.venv/Scripts/python -c "from domains.games.adapter import load_listings, load_taxonomy; print(next(load_listings(1)).model_dump_json()); print(load_taxonomy())"
```

Inspect scope decisions (output contains private source IDs; keep it local):

```powershell
.venv/Scripts/python -c "from domains.games.adapter import read_records, listing_id; from domains.games.scope import decide_scope; from itertools import islice; print([(listing_id(r), decide_scope(r).as_dict()) for r in islice(read_records(), 10)])"
```

Smoke before substantive end-to-end (E2E) verification:

```powershell
.venv/Scripts/python -m domains.games.readiness --listings C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/games/games_listings.parquet --smoke-only --report domains/games/e2e/smoke-report.json
```

Exact next readiness run (works before shared registration):

```powershell
.venv/Scripts/python -m domains.games.readiness --listings C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/games/games_listings.parquet --also-listings C:/Users/eduar/Desktop/HACKATON/tasks/raw-content-audit/new-domain-inputs/games/games_listings.parquet --catalog C:/Users/eduar/Desktop/HACKATON/data/different_lines/amazon.parquet --delivery-report C:/Users/eduar/Desktop/HACKATON/tasks/raw-content-audit/delivery-report.json --report domains/games/e2e/evidence-report.json
```

The runner first smokes direct `Domain('games', pack)` loading, then checks real
RAW preservation/joins, limits, synthetic boundary cases, stable signed IDs,
brand noninference, identity conflicts, vocabulary, shadow status and empty
taxonomy. It re-inventories the current Drive root and boundary files, checks
current hashes against manifests/delivery, compares RAW with the catalogue and
saves counts/schemas/hashes without committing raw rows. Synthetic examples are
invented behavior contracts, never gold. Failure modes were recorded before
implementation in `domains/games/e2e/FAILURE-MODES.md`.

If a separate toys file appears, rerun discovery and profile its overlap and
boundary evidence; do not substitute it automatically for mixed games. No
sealed-gold reads, paid calls, full taxonomy run, publication or source writes
are part of this readiness command.

## Run artifacts and later distillation

Readiness now creates a new, non-overwritten directory under ignored
`runs/games/readiness/<UTC-run-id>/`. Pass `--artifacts-dir <new-directory>` to
retain it elsewhere outside Git; paths elsewhere inside the checkout are
rejected. The committed readiness report indexes full artifact paths, hashes,
byte/record counts and limitations. These artifacts are local to the machine,
not attached to the pull request; copy them explicitly if another machine needs
the data-bearing evidence.

- `run.json`: status, invocation, Git HEAD, executed implementation/config/rule
  hashes from the report, source paths/hashes, schemas/counts, sampling scope,
  and explicit model/validator/human execution status. Git HEAD records the
  checkout at execution; implementation hashes identify executed working files.
- `scope-decisions.jsonl`: every configured row's supplied ID/native ID, title,
  source labels and file hash, candidate kinds when available, selected scope
  decision/hold with reason/evidence and screen version. All rows are scanned;
  there is no random sample or seed and no held-out evaluation claim.
- `rule-firings.jsonl`: small synthetic input/candidate contrasts, facts,
  shadow statuses and actual evaluator outputs, including a non-firing matching
  identity contrast. These are behavior contracts, not source or human labels.
- `failure.txt` and failed `run.json`: unexpected error traceback/status while
  preserving artifacts already written. The logging check deliberately supplied
  a missing file and verified failure recording and overwrite prevention; see
  `domains/games/e2e/logging-check-report.json`. This injected setup failure is
  not a domain result.

Implemented logs do **not** contain placements, trees, model routing, tool/agent
calls, validator judgements, human outcomes or fine-tuning examples: none were
run. Review state is explicitly `not_run` / `not_reviewed`. Calls/tokens are
zero; cost is unavailable because no model calls occurred.

The later shared harness should link source/config/code/rule versions and sample
IDs/seed to placement/tree outputs, candidate alternatives, chosen path or
abstention with concise evidence, routes, structured tool/agent responses,
failures, validator/human reviews, measured metrics/usage/cost, and before/after
rule or prompt changes. Preserve counterexamples and regressions. Separate
exploration from held-out evaluation and leave unknown outcomes empty. Capture
reviewable explanations and structured outputs, never private hidden reasoning.
Those shared hooks are pending with the integration owner; no training
infrastructure or performance claim is introduced by this baseline.
