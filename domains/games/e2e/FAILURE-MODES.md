# Games offline verification contract

Written before the adapter and checks. These are engineering failure modes,
not human-labelled taxonomy truth.

- A broad Toys & Games or Video Games department admits unrelated products.
- Licensed figures, building sets, RC parts or fidgets enter games through a
  franchise name, incidental description or a bundled redemption code.
- Partyware, pet products, films or generic electronics enter via bad ranks.
- Specific categories conflict with titles; dual-use items silently get placed.
- A source-key join drops, multiplies, reorders or mismatches sidecar records;
  signed observation keys lose precision, zero keys disappear, duplicate IDs pass.
- Limit is applied before filtering; zero and negative limits behave incorrectly.
- Silver food fields, audit decisions or source brand fields become trusted labels.
- Missing brand is filled from seller, character or compatible console maker.
- Raw fields, identifiers, model codes, sequels or provenance are lost.
- Base games merge with expansions, DLC, currency, accessories or collector sets;
  platform generations, distribution, language and editions collapse.
- Puzzle subject/title is lost or its piece count is confused with outer packs.
- Missing taxonomy is fabricated or silently reported as placement-ready.
- Proposal/shadow rules decide; missing candidate metadata appears compatible.
- Direct import requires shared registration, a model/API call or another domain.
- Reading source files mutates them; stale manifests go unnoticed.
- Run logs overwrite previous evidence, put RAW-bearing traces in Git, omit
  failures, or confuse synthetic exploration with held-out/human outcomes.

Smoke: import the domain, instantiate Domain directly, read one real supported
listing, load YAML and return an empty taxonomy. Then run the full offline
readiness command: scan the finite mixed subset, compare sidecars and source
hashes, check all accepted listings, exercise synthetic positive/negative cases,
load/evaluate shadow rules and vocabulary, and save a JSON report. Synthetic
examples test stated behavior only; neither they nor the old audit are gold.
