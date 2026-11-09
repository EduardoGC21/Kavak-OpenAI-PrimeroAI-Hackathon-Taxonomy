# Kavak × OpenAI — PrimeroAI Hackathon: Taxonomy

Scalable judgment: placing a listing in a product taxonomy is easy for a person and impossible at 5M items. Agents
place listings in four separate domains (food, fragrance, cars, car parts). Rules that prove themselves on human
labels go into one shared memory, so the next domain starts with checks that already have a track record.

## Layout

```
memory/        the ONLY thing domains share
  rules/       rule specs (operator x extractor x policy), scope universal | family | domain
  record.jsonl each rule's outcomes per domain (caught, false rejects, admitted)
  lessons.md   how improvements turned out fake before
taxo/core/     domain-agnostic: schemas, rule engine, metrics, ledger, domain loader
taxo/roles/    agents (OpenAI Agents SDK): placer, judge (fast/strong), proposer; curator is code
domains/<d>/   pack.yaml (levels, families, conventions) + adapter.py (Drive subset -> Listing/Node)
tests/         isolation (no domain imports another) + smoke
```

Agents never see labels. The curator is plain code: it admits a rule only if the rule is a real check (it fires
on a planted fault and stays quiet on a known-good case) and it pays on dev labels. A rule becomes universal once
it was admitted in two domains.

## Run

```bash
uv sync --extra dev
cp .env.example .env        # set OPENAI_API_KEY and TAXO_DATA_DIR
uv run pytest -q
uv run python -m taxo.cli inspect cars
uv run python -m taxo.cli place fragrance --n 5
```

Data (listings, taxonomies, labels) is internal and lives on Drive, never in this repo.
