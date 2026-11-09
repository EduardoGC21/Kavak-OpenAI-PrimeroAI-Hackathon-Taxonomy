# Pedia-guided Silver listing subsets

Extract **5,000 unique source listings per domain**, retaining every original
Silver column and value. Pedia identity and hierarchy guide selection only;
no Pedia columns, reduced graph, texts or embeddings are exported.

Only `food_scope_status='confirmed'` food rows and `perfume_status='included'`
fragrance rows are eligible. Candidate, uncertain, excluded, null and any other
Silver statuses are omitted. Every selected row must have an existing placement
to an active Pedia entity on the same brand page; `unplaced` outcomes are omitted.

Run from PowerShell using the existing M4R image:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File pipelines/subset/run.ps1
```

Outputs, outside Git:

```text
HACKATON/data/subsets/silver-n5000-seed42/
  food/listings.parquet
  food/manifest.json
  fragrance/listings.parquet
  fragrance/manifest.json
```

Change `-Size`, `-Seed`, `-Brands`, `-FocusFraction`, `-Sources` or `-Out` to make
another version. Existing output folders are never overwritten. Example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File pipelines/subset/run.ps1 -Seed 73
```

## Sampling

The sampler uses exact signed observation IDs and the checksum-verified retained
identity bridge for older Pedia mentions. Source, listing key and current Silver
identity must agree. Native source/market/listing-or-variant identity comes from
the existing all-product observation bridge, so repeated observations do not
inflate the listing count. If a native listing has conflicting Pedia placements,
it is excluded rather than assigned an invented answer.

Brand-balanced rounds select short groups of up to eight listings per model.
Groups with sibling Pedia variants and multiple sources are preferred; brands
are chosen to cover different sources, and repeated rounds add different models
within the same brand. About 5% of slots retain other identity outcomes such as
gift sets or brand-only placements. Those outcomes remain unchanged; unplaced
listings are never included.

Fragrance is mixed: by default 20% of selected listings come from an explicit
focus list including Lattafa, Armaf, Afnan, Rasasi, Ajmal, Al Haramain, Swiss
Arabian and related brands. The remaining 80% come from other brands. This is
an editable sampling focus list, not an inferred country or ethnicity classifier.

One observation represents each sampled native listing: latest observed time,
then signed observation ID and mention ID for deterministic ties. Selection is
seeded and stable; different sizes are not promised to be nested subsets.

Each manifest records release pins, join coverage, exclusions, selected brands,
sources, relationship counts and a selection digest. Pedia annotations are not
independent ground truth. Source Silver columns and values remain intact; the
classification filter changes which rows are selected, not their classifications.

## Sources and runtime

The local runner reads `HACKATON/data/subset-sources.json`: `pedia_root`, and
`domains.food` / `domains.fragrance` entries with `silver`, `native_bridge`,
`legacy_bridge`, `legacy_bridge_sha256`, and `silver_snapshot`. All are existing local data; no cloud
calls or model inference run. Source locations are also documented in
`HACKATON/data/listings/README.md`.

`subset.py` uses Python, DuckDB and PyArrow supplied by `m4r:b030afac47d1` (DuckDB 2.0).
It can also run directly with `--sources <config.json> --out <new-directory>` in a
compatible environment. No unit or end-to-end tests are included or run.
