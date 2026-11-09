# Additional domain packs: shared harness contract

Domain names are discovered from `domains/*/pack.yaml`. Existing
`Domain.listings(limit) -> Iterator[Listing]` and `Domain.nodes() -> Iterable[Node]`
contracts are unchanged. CLI inspection bounds loading and accepts an empty
tree; `place` explains how to bootstrap before any model import/call when nodes
are absent. Each adapter owns explicit source selection, stable IDs, provenance
and domain scope. No shared loader assumes a `games` folder means video games
or toys. There is no new footwear domain.

## Construction and evaluation are separate

`python -m taxo.pipeline <domain> --construct [--limit N] --output <fresh-dir>`
loads the domain adapter and vocabulary, groups by **source-reported brand only**,
counts the existing lattice, and writes `placements.jsonl`, `nodes.jsonl`,
`screened.jsonl` and `metrics.json`. Everything constructed is provisional, as
recorded by `metrics.mode=raw_only_proposals` and node `fields.status=proposal`.
These files are not human gold or a trusted registry. Exact duplicate normalized
name keys contribute once to support. No models or gold loaders are invoked.

Optional adapter field `fields.domain_scope` has `decision: accept|hold|reject`
and a `reason`. Holds/rejects are recorded separately and never counted by the
lattice. An adapter can instead filter at source; `unscoped_rows` makes absence
of this field visible. `fields.source_manifest`, when provided, is carried into
metrics; it must be JSON-serializable and should include current paths/hashes.

Optional `pack.yaml` construction settings:

```yaml
construction:
  full_title: true                 # use full tokens; preserve internal brand-like words
  global_evaluator_rules: false    # no unvalidated transfer of active fragrance-era rules
  node_text_module: package.module # optional node_text(name, variants, n) helper
```

Raw construction uses full titles by default, no title/maker brand inference
and no fragrance brand suffixes. The fragrance legacy baseline retains its
configured suffixes, candidate normalizations and original evaluation command.
Fragrance vocabulary experiments remain in its normalization helper. Optional
`preserve_identity_tokens: true` in vocab.yaml keeps numerals/short tokens from
being discarded as fragments. Raw-only construction also forces this preservation;
the existing fragrance evaluation default is unchanged.

`taxo.pipeline <new-domain>` without `--construct`, and `taxo.gate <new-domain>`,
fail before reading any gold with instructions to collect blind labels and
configure evaluation. This change does **not** pretend a generic scorer or new
gold admission loop exists. The fragrance gate also rejects construction metrics.
`--construct --sealed` and nonzero `--agent-calls` are rejected.

## Rules and prompts

Two formats intentionally retain separate statuses:

- RuleSpec YAML uses top-level `check`, `decision`, `params` and
  `proposal|shadow|admitted|retired`. Shared scoped rules come from
  `memory/rules/*.yaml`. Domain additions come from `rules/<domain>/*.yaml` or
  `domains/<domain>/memory/rules/*.yaml` except `agentic.yaml`.
- Evaluator YAML uses `when`, `then`, `stage` and
  `proposal|shadow|active|retired`, loaded from `rules/<domain>/*.yaml`.
  The evaluator skips RuleSpecs; it never interprets a check proposal as an
  unconditional empty-condition rule. Invalid statuses/formats fail explicitly.
- `domains/<domain>/memory/rules/agentic.yaml` uses AgenticRule entries. Default
  placer prompts include **only admitted** entries. An explicit
  `make_placer(..., include_proposals=True)` creates a labeled prompt experiment;
  it does not promote rules. Shadow instructions are excluded by default since
  adding them to a prompt would change the agent's decisions.

Optional local checks use the explicit pack key
`checks_module: taxo.tools.<domain>`. The module exports:

```python
CHECKS = {"domain_check_name": (check_function, "abstain")}
# check_function(listing: Listing, node: Node, tax: dict[str, Node], **params)
# returns None, a detail string, or (detail, suggested_node_id)
```

Shared names in `taxo.tools.checks.CHECKS` resolve first; use domain-prefixed
names for local checks. Unknown names fail when a runnable rule calls them.
Proposals are never executed in production. The same resolver supports both
RuleSpec and evaluator checks, without mutable cross-domain registration.
The imported toys module has two explicit lazy bindings in shared dispatch:
`toys_identifier_evidence` and `toys_offering_evidence`. Its owned files were
not changed. They remain proposals; shared shadow dispatch was checked offline.

The imported games pack uses the optional conventional module
`domains/<domain>/checks.py`, exporting `candidate_facts(listing, node) -> dict`.
Construction calls this for candidate and route evaluation using the original
Listing. Evidence under `Listing.fields[domain].subtype` and `.identity` partitions
the lattice before counting; `title_key` is excluded from the partition signature.
Only exactly equal subtype/identity evidence shares a partition; unknown versus
known evidence stays separate. Proposed product nodes preserve this metadata,
have distinct IDs across partitions, and placements point to these exact IDs.
This conservative grouping is not proof of product equivalence.

The placer tool calls `run_rules(..., tax)` (the former `apply_all` did not
exist). It uses the current Listing when available, returns admitted findings,
and records shadow findings in context outside the prompt. CLI placement supplies
full listing evidence and checks returned node IDs and binding rules before
recording a result. A pre-existing food agentic YAML scalar needed quoting to
be loadable; its text/status are unchanged.

## Later integration and commands

The completed games source commit `459c07f8fcced97756c8f86b1ef681f6db61dfc6`
and toys source commit `827e37e3acb7f0da578c5104dc12098015db7b4d` were imported
unchanged as `1b3446a` and `ac568c0`. Their domain-local docs describe their
original handoff; the shared gaps listed there are superseded by this integration
note. No owned domain files were edited. Combined offline verification passed:
all three adapters, 64-row construction per domain, source preservation and scope
checks, numeric-token preservation, games partitions/facts, toys shared checks,
proposal/shadow isolation, parent/placement IDs, and artifact hashes/failure logs.
The refreshed full adapter populations have zero toys/games ASIN overlap.
There is no claimed taxonomy accuracy or completed learning loop.

Set explicit source paths before the proposed later full offline commands:

```powershell
$env:TAXO_TOYS_LISTINGS = 'C:/Users/eduar/Desktop/HACKATON/data/different_lines/silver/games/games_listings.parquet'
$env:TAXO_GAMES_LISTINGS = $env:TAXO_TOYS_LISTINGS
# Configure TAXO_CLOTHING_LISTINGS as documented in clothing.md.
.venv/Scripts/python.exe -m taxo.pipeline clothing --construct --output runs/clothing/full-baseline-20261109
.venv/Scripts/python.exe -m taxo.pipeline toys --construct --output runs/toys/full-baseline-20261109
.venv/Scripts/python.exe -m taxo.pipeline games --construct --output runs/games/full-baseline-20261109
```

These full commands were not executed here. Missing source configuration remains
an actionable blocker, not permission to substitute another dataset. Full gold
evaluation and learned rule admission remain later work after human labels and
the corresponding scorer are supplied.

## Run artifacts and distillation evidence

`checks/domain_integration.py` reproduces the combined bounded check. The
[committed artifact index](evidence/domain-integration.json) records local report
locations and hashes. Full source-bearing artifacts stay under ignored `runs/`.

Every fresh construction attempt writes `run-manifest.json`, including failure:
domain, status, timestamp/duration, parent Git revision plus exact code/config/
rule hashes, source-file hashes, adapter-order sample IDs (`seed: null`), artifact
paths/hashes and explicit no-model/no-human-review status. A nonempty output
directory is rejected rather than overwritten. Failures write `errors.jsonl`.

Successful runs also write:

- `observations.jsonl`: emitted IDs/titles, source, scope decision/reason and
  source-brand evidence; human/validator outcomes are null.
- `screened.jsonl`: holds/rejects returned by the adapter contract. Games/toys
  filter before emitting; their full rejected/held populations are covered by
  their separate source-readiness reports, not fabricated as construction events.
- `rule-events.jsonl`: considered lattice candidates, admitted/shadow findings,
  evaluator facts/results and selected/veto/route evidence. The baseline considers
  one lattice candidate per supported item; it does not claim an exhaustive
  alternative search. No hidden reasoning is logged.
- `placements.jsonl`, `nodes.jsonl`, `metrics.json`: provisional placements/tree,
  node IDs/parents/children, partitions, source refs, rule versions/statuses,
  coverage counts and explicit null accuracy. Zero calls/cost are recorded; token
  usage is null because no model was invoked.

The existing CLI placement Ledger is a hash-chained placement event log. It is
not a complete model-run trace and has no token/cost accounting. Before future
paid/learning runs, capture tool/agent structured inputs/outputs, actual usage/
cost/errors, candidate alternatives, validator and human review outcomes, gold
split/version, regression cases, and before/after rule/prompt diffs. Link these
by run, listing and candidate IDs with evidence references and concise decision
explanations. Those future traces do not exist for this offline baseline. This
is an artifact contract for later distillation, not training infrastructure.
