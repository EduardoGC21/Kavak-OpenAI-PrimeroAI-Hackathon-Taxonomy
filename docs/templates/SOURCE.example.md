# SOURCE: <domain>/<folder>

*One per Drive folder. See docs/DATA-SPEC.md §8. Synthetic example below.*

- **What:** used-car listings, normalised to the shape in DATA-SPEC §3.
- **From:** `<path or URL of the raw export or scrape run>` (run id `20261109T090000Z`).
- **Date:** pulled 2026-11-09; listings scraped 2026-11-09.
- **Made by:** luis, with `<script path>`.
- **Filters and sampling:** dropped exact duplicate ids; dropped `record_type: search` rows when a `listing` row had
  the same URL. Random sample with seed `20261109`.
- **Row counts:** 2,500 in, 2,431 out (69 duplicates). By source: examplesource 1,200; othersource 1,231.
- **Field mapping:** `make`/`brand` → `brand_field`; `kilometers`/`km` → `fields.km`; `price_mxn` → `price`.
- **Known problems:** version missing on most rows from examplesource; only 32 VINs.
- **Truth status:** none of this is gold. (In `gold/`, say who labelled, when, whether blind, whether random.)
