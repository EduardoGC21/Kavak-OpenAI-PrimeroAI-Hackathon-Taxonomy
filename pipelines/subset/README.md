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
  food/food_listings.parquet
  food/manifest.json
  fragrance/fragrance_listings.parquet
  fragrance/manifest.json
```

Change `-Size`, `-Seed`, `-Brands`, `-FocusFraction`, `-Sources` or `-Out` to make
another version. Existing output folders are never overwritten. Example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File pipelines/subset/run.ps1 -Seed 73
```

`-Domain food` or `-Domain fragrance` exports just that domain. Optional
`required_groups` in a domain's local sources configuration reserve listings by
Pedia brand and title pattern. The current food configuration reserves ten each
for Coca-Cola, Diet Coke and Coke Zero, still requiring confirmed Silver status
and an active Pedia placement. Required groups replace slots; they never increase
the sample size. No matching rules or output columns are changed.

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

## Original Gold subsets, in batches of 500 listings

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File pipelines/subset/run-gold.ps1
```

This mode covers **all listing IDs connected to the existing Gold labels**, across
all configured views and hierarchy levels. It partitions those IDs into disjoint
batches of 500, retaining a smaller final batch. The population comes from the
original Gold assignments and catalog memberships, independently of the existing
5,000-row Silver samples. No classification, review-state or current Pedia filter
removes Gold-linked listings.

Each batch contains:

```text
data/subsets/gold-batches-n500/<domain>/
  listing_index.parquet
  report.json
  batch-00001/
    listing_gold_links.parquet
    manifest.json
    gold/<view>_labels.parquet
```

The Gold files contain **only filtered original rows, with every original column,
type, value and schema metadata preserved**. Their row counts can differ from
500 because labels are shared by listings. `listing_gold_links.parquet` connects
the 500 exact listing IDs to those original Gold rows through `view`,
`hierarchy_id`, and `cluster_id`. It retains the original `product_key` and
assignment `level`. Every available original level and view is kept. Gold label
rows can therefore occur in several batches; listing IDs occur in only one batch.
Silver listing payloads are not copied or enriched.

Batch ordering groups listings by their original deepest label, then original
catalog brand/product, with stable ID ties. This keeps related examples together
while retaining the whole population. Food prefers its listing view for ordering;
Fragrance prefers its innermost-model view. No labels or clusters are generated.

The signed 64-bit `silver_id` joins to `observation_key` for Food and
`source_record_key` for Fragrance. It must never be converted to floating point.
For example, using DuckDB Structured Query Language (SQL):

```sql
SELECT s.*, g.*
FROM read_parquet('batch-00001/listing_gold_links.parquet') b
JOIN read_parquet('/path/to/food_listings.listings.parquet') s
  ON s.observation_key = b.silver_id AND s.source_id = b.source_id
JOIN read_parquet('batch-00001/gold/brand_v1_labels.parquet') g
  ON g.hierarchy_id = b.hierarchy_id AND g.cluster_id = b.cluster_id
WHERE b.view = 'brand_v1';
```

The index records current and historical Silver join availability. Historical
Fragrance Gold IDs can require a retained older export; reports pin those source
paths and checksums. A historical Silver export may contain repeated observation
IDs across assemblies, so scope the read to the intended assembly before joining.
No Gold ID is removed when its unlabeled record is absent from current Silver.

`run-gold.ps1` uses the existing `data/subset-sources.json` for current Silver and
`data/gold-sources.json` for original Gold inputs. The latter has this shape
(repeat `views` entries for every available view and add the Fragrance domain):

```json
{
  "domains": {
    "food": {
      "release": "<original Gold release ID>",
      "views": {
        "brand_v1": {
          "labels": "/path/to/brand_v1_labels.parquet",
          "labels_sha256": "<checksum from the original release manifest>",
          "assignments": "/path/to/original/mantis/tables/assignments.parquet",
          "members": "/path/to/original/catalog/tables/members.parquet",
          "products": "/path/to/original/catalog/tables/products.parquet"
        }
      },
      "unlabeled_history": []
    }
  }
}
```

The Food `listing` view needs labels and original binary assignments, without
catalog members/products. `unlabeled_history` optionally lists retained Silver
Parquet paths for join-availability reporting. Inputs mount read-only and runs
use `--network none`. Source pins, output checksums and the container input
configuration are recorded. Existing output directories are refused. Use
`-Domain food`, `-Domain fragrance`, `-Size`, `-Sources`, `-GoldSources` or `-Out`
as needed. The normal extraction does not run smoke, end-to-end or unit tests.
