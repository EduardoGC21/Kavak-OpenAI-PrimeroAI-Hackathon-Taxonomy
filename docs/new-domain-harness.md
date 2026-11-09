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
being discarded as fragments; default behavior is unchanged for existing packs.

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

The placer tool calls `run_rules(..., tax)` (the former `apply_all` did not
exist). It uses the current Listing when available, returns admitted findings,
and records shadow findings in context outside the prompt. CLI placement supplies
full listing evidence and checks returned node IDs and binding rules before
recording a result. A pre-existing food agentic YAML scalar needed quoting to
be loadable; its text/status are unchanged.

## Later integration and commands

The toys and games branch tips were still the scaffold base
`06be9acde9b3964415e900e7d9da23fd0ac8e2a5` when checked. Their domain files were
not edited, imported or merged; combined readiness is not claimed. Their final
commits still need integration. Check their documented source configuration and
align any optional local checks with the contract above. No shared pack
placeholders were manufactured.

After their completed packs are integrated and explicitly configured, proposed
full offline construction commands are:

```powershell
.venv/Scripts/python.exe -m taxo.pipeline clothing --construct --output runs/clothing/full-baseline-20261109
.venv/Scripts/python.exe -m taxo.pipeline toys --construct --output runs/toys/full-baseline-20261109
.venv/Scripts/python.exe -m taxo.pipeline games --construct --output runs/games/full-baseline-20261109
```

Run bounded checks first; these full commands were not executed here. A missing
pack remains an unknown-domain error. Missing vocabulary/source configuration
is an actionable blocker, not permission to use another domain's data. Full
gold evaluation and learned rule admission remain later work after human labels
and the corresponding scorer are supplied.
