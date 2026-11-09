# Taxo data spec: what each domain owner hands over

*For the teammates who organise one domain each: **food**, **fragrance** or **cars**. You do not need to have been in
the design sessions. Read §1 and your domain's checklist in §2, then use §3–§9 as reference. The empty templates to
copy are in [`docs/templates/`](templates/).*

## 1. What the system does with your data, in five lines

Taxo builds a product tree for a domain (brand › product › variant, or make › model › version › year) and puts every
marketplace listing on its node. It works through fixed steps: **parse** the title, find the **brand**, look the name
up in the brand's **registry**, count names across listings (**lattice**), then apply **rules**. An **agent** handles
only what is left ([SPEC.md §4](../SPEC.md)). The tree grows as agents propose rules. A rule is kept only if it
holds on **gold**, the labels a person made. Your job is to give it clean listings, the tree you already have, gold
labels, a few rule proposals and your domain's conventions.

**Two hard rules:**

- **Internal data never goes in this repo.** The repo is public. Data lives on Drive (§8); the repo keeps pointers only.
- **Gold is made by people and edited by people only.** No agent, script or validator writes or changes gold.

## 2. What to hand over: one checklist per domain

Each item is a file in your domain's Drive folder (§8). Every folder has a `SOURCE.md` (template:
[`SOURCE.example.md`](templates/SOURCE.example.md)).

### 2.1 Food

Where you start: Edu's subset at `C:\Work\meta-pedia-data\edu-subsets-2026-11-09\food\` has 12,230 listings over 80
brands and 10,534 nodes. Edu's full exports are at `G:\My Drive\Showcase Data\EDU_FINAL_PEDIA\`, and the build script
is `C:\Work\meta-pedia-data\make_edu_subsets.py`. **There is no gold yet.**

- [ ] `listings/listings.jsonl` in the shape of §3. Map Edu's `id`, `title`, `brand`, `source`, `size`, `pack`,
      `units` and `multipack` into it. Keep `pedia_path` and `pedia_level` in `extra` as a baseline, **never as truth**.
- [ ] `taxonomy/taxonomy.jsonl`: Edu's nodes, mapped to §4.2 (`label` becomes `name`).
- [ ] `gold/round-01.yaml`: **50** blind labels sampled at random (§5), plus **25** of them labelled again by a
      second person (`gold/round-01-second.yaml`).
- [ ] `rules/rules.yaml`: 3 code-rule proposals (§7.1). `rules/agentic.yaml`: 3 agentic proposals (§7.2). Start
      from the examples there, and from the 10 already in `domains/food/memory/rules/agentic.yaml`.
- [ ] `conventions/conventions.yaml`: confirm or change the 4 lines in `domains/food/pack.yaml`, and add yours (§6).
- [ ] A `SOURCE.md` in every folder.

### 2.2 Fragrance

Where you start: Edu's subset at `C:\Work\meta-pedia-data\edu-subsets-2026-11-09\fragrance\` has 14,344 listings
over 80 brands and 15,580 nodes. It also carries the Pedia rule ids that fired (`rule_ids`, `rules_seen.json`).
Gold already exists:

- Harry's **247** labelled rows: `C:\Work\Pedia-Harness\repo\tests\fixtures\fresh150-harry.yaml` (150) and
  `exp01-harry-correct.yaml` (97).
- **1,486** owner reviews, recoverable with
  `git -C C:\Work\Pedia-Harness\repo show 0cd4be60:tests/fixtures/owner-structure.jsonl`.

Tasks:

- [ ] `listings/listings.jsonl` (§3). Map `concentration`, `gender`, `volume_ml`, `product_form`, `seller_name`,
      `brand_name` and `manufacturer_name` into it. `identifiers_json` is empty in Edu's subset, so leave
      `identifiers` empty rather than guess.
- [ ] `taxonomy/taxonomy.jsonl`: Edu's nodes (§4.2).
- [ ] `gold/harry-247.yaml`: Harry's rows, copied **as they are** plus `labelled_by: harry` and `labelled_at`. Do not
      relabel them. Note in `SOURCE.md` that they were **not** sampled at random: they came from labelled brands.
- [ ] `gold/owner-structure.jsonl`: the 1,486 owner reviews, unchanged, with `SOURCE.md` naming commit `0cd4be60`.
- [ ] `gold/round-01.yaml`: **50** new blind labels sampled at random (§5), because the existing gold is not a random
      sample. Add a second labeller on 25.
- [ ] `rules/` and `conventions/` as for food. The repo already has 10 agentic proposals and the 5 conventions in
      `domains/fragrance/pack.yaml`.

### 2.3 Cars

Where you start: the Mexico scrape at `G:\My Drive\meta-pedia-data\subsets-2026-11-09\cars\` has 8,642 used-car
listings from Kavak (2,500), Seminuevos (2,500), Mercado Libre (2,500), Autocosmos (1,000) and Carshop (142). The
taxonomy is 1,574 catalogue versions from Autocosmos (1,222) and brand sites (352). **There is no gold yet.**

The sources name things differently. Seminuevos gives `brand`, `model`, `version`, `year` and `kilometers`; Kavak
gives `make`, `model` and `year` but rarely `version`; Mercado Libre and Carshop give only a `title`. Only **32** rows
have a VIN.

- [ ] `listings/listings.jsonl` (§3), with one shape across all five sources. Put `make`/`brand` into `brand_field`,
      `kilometers`/`km` into `fields.km` and `price`/`price_mxn` into `price` (MXN). Drop the rows whose
      `record_type` is `search` if they are duplicates of a `listing` row, and say so in `SOURCE.md`.
- [ ] `taxonomy/taxonomy.jsonl`: the catalogue, one node per make, model, year and version (§4.2). Keep `msrp_mxn` and
      the source URL on the version node.
- [ ] `identifiers`: put a VIN in `identifiers.vin` only when it is 17 characters. Decoding it with NHTSA vPIC (make,
      model, year) is the system's job; do not decode it by hand. vPIC is weak on Mexico-only versions, so treat it as
      evidence for make, model and year only.
- [ ] `gold/round-01.yaml`: **50** blind labels sampled at random (§5), at least 10 per source if the sample allows,
      plus a second labeller on 25.
- [ ] `rules/` and `conventions/`. The most important convention to decide is **when two version names are the same
      trim** ("Advance" vs "Advance CVT"); `domains/cars/pack.yaml` leaves it as a TODO.

## 3. Listings: `listings/listings.jsonl`

One JSON object per line, UTF-8. Whatever the source called a field, rename it to the names below. Put anything else
you want to keep under `extra`. Template: [`listings.example.jsonl`](templates/listings.example.jsonl).

| Field | Req. | Type | Used by the pipeline? |
|---|---|---|---|
| `id` | **yes** | str | Join key for gold. Stable and unique: `<source>:<source's own id or URL>`. |
| `domain` | **yes** | str | `food` · `fragrance` · `cars`. |
| `source` | **yes** | str | Marketplace or scrape (`amazon`, `kavak`, ...). Used in sampling and in Loop B. |
| `title` | **yes** | str | **Yes, the main input.** Use it exactly as listed; do not clean it. |
| `brand_field` | if present | str | **Yes**, in the brand step. The marketplace's brand field, as given. |
| `seller` | if present | str | **Yes**, to keep shops from being taken as brands ("a shop is not a brand"). |
| `identifiers` | if present | obj | **Yes**, settles the listing when present: `{gtin, upc, ean, vin, part_number}`. |
| `description` | optional | str | **Yes**, on the `agent_evidence` route only. |
| `variant_options` | optional | obj | **Yes**, on `agent_evidence` only, as evidence. Never moves a listing on its own. |
| `fields` | domain | obj | **Yes**: the domain fields below. |
| `url` | optional | str | Carried along. Labellers open it. |
| `price`, `currency` | optional | num, str | Carried along; rolls up the tree once placed. |
| `scraped_at` | **yes** | str | ISO date. Carried along. |
| `extra` | optional | obj | Carried along, never read. Baselines (`pedia_path`), raw blobs. |

Domain `fields`:

| Domain | Field | Notes |
|---|---|---|
| food | `size` (str, e.g. `"11.3 oz"`), `pack_count` (int), `multipack` (bool) | Parsed but **never a node**. Count checks read it. |
| fragrance | `concentration` (`edp`, `edt`, `parfum`, `extrait`, `edc`), `volume_ml` (num), `gender` (`women`, `men`, `unisex`), `form` (`spray`, `body mist`, ...) | Concentration and audience separate products; volume never does. |
| cars | `make`, `model`, `version`, `year` (int, model year), `km` (int), `transmission`, `body_type` | Copy what the source gives. Leave `version` blank rather than guess. |

**Rules for this file.** Leave out empty values instead of writing `""`. Do not translate titles. Do not fix titles.
Do not drop listings because they look hard: hard listings are the point. The only rows to remove are exact duplicates
of the same `id`.

## 4. Taxonomy and registry

### 4.1 Tree levels ([SPEC §3](../SPEC.md))

| Domain | Levels | Example |
|---|---|---|
| Food | brand › product › variant | Oreo › Double Stuf › Mint |
| Fragrance | brand › (sub-brand or family) › product › variant | Lattafa › Khamrah › Khamrah Qahwa |
| Cars | make › model › (generation) › version › year | Volkswagen › Jetta › A7 › Comfortline 1.4 TSI › 2021 |

Size, pack count and multipacks are never levels in any domain. The car catalogue has no generation, so it is optional.
The current car adapter orders year before version; the cars owner settles that order as a convention (§6).

### 4.2 An existing tree: `taxonomy/taxonomy.jsonl`

If a tree exists (Edu's export, the car catalogue), hand it over as one node per line:

```json
{"id": "acme/p_crunch", "brand": "Acme Snacks", "level": "product", "name": "Crunch Bites", "parent_id": "acme/b", "status": "existing", "source": "edu-export-v9f"}
```

`id` must be unique across the file; prefix it with the brand when the source's ids are only unique per brand.
`parent_id` is null only for brands. Keep any extra source fields under `extra`. For cars, the id is the slugged path
(`volkswagen/jetta/2021/comfortline-1-4-tsi`), as `domains/cars/adapter.py` builds it.

An existing tree is a **starting point**, not truth. Pedia's export contains errors that gold is meant to find.

### 4.3 No tree: let the lattice build it

Without a tree, hand over listings only. The lattice counts name sequences across each brand's listings and proposes
products and families ([SPEC §4.1](../SPEC.md)). Your part is the **variant vocabulary**: tokens that are sizes,
packs, concentrations or audiences, not names. Propose additions to `domains/<d>/vocab.yaml` in your conventions file.

### 4.4 Registry: `registry/<brand>.yaml`

A registry holds a brand's **official** structure: its lines and products from the brand's own site or catalogue. An
agent proposes it with web search and code writes it. You only add a file when you already have an official list (a
catalogue PDF, the car catalogue). Every node must have a `basis` saying where it came from:

```yaml
brand: Acme Snacks
aliases: [acme, acme snacks co]
nodes:
  - {id: P_crunch_bites, level: product, name: Crunch Bites}
  - {id: V_crunch_bites_bbq, level: variant, name: BBQ, parent: P_crunch_bites}
basis:
  P_crunch_bites: {source: official, ref: "acme.example/products", found_by: "human:ana@2026-11-09"}
```

## 5. Gold: the only truth

Gold is a person's judgement of where a listing belongs. It is the only thing rules are scored on. The format is that
of Harry's `fresh150-harry.yaml`, plus who labelled the row and when. Template:
[`gold.example.yaml`](templates/gold.example.yaml).

```yaml
- id: gold-food-r01-0007            # unique row id
  listing_id: "amazon:B0EXAMPLE1"    # joins to listings.jsonl
  title: Acme Crunch Bites BBQ 6 x 1.5 oz Snack Packs
  source: amazon
  brand: acme snacks
  expected_path: [Acme Snacks, Crunch Bites, BBQ]
  compare: prefix                    # prefix: the path must start with this | exact: must be exactly this
  expect: accept                     # accept: this path must hold | reject: this path must NOT come back
  why: "Flavour named in the title; 6-pack is a pack, not a node."
  labelled_by: ana
  labelled_at: 2026-11-09
  provenance: blind_random           # blind_random | review (Loop B) | imported:<file>
```

- **`compare: prefix`** is the default: write the deepest path you are sure of. A correct shallower answer passes;
  anything deeper that you did not write is not checked.
- **`compare: exact`** is for when the depth matters, for example "stop at the brand: the title names no product".
- **`expect: reject`** rows record a known-wrong path that must never come back (`expected_path` is the wrong path).
  They come from review (Loop B), not from blind labelling.
- If you cannot tell, write `expected_path: [<brand>]` with `compare: exact` and say why. If the listing is not in
  the domain at all, write `expect: accept`, `expected_path: []` and `why: out of domain`.

### 5.1 Protocol

1. **Sample at random.** Draw uniformly from `listings.jsonl` with a fixed seed, and record the seed in `SOURCE.md`.
   Do not choose rows by hand: hand-picked rows are the easy or interesting ones, and the score will not hold on the
   rest. For example:
   `python -c "import random,json;L=open('listings.jsonl',encoding='utf-8').readlines();random.seed(20261109);print(*random.sample(L,50),sep='')" > gold/sample-r01.jsonl`
2. **Label blind.** Look at the title, the URL, the brand's site and the tree. **Do not look at the system's answer**
   or at `extra.pedia_path`. Hide those columns before you start.
3. **Write a `why`** on every row, one sentence. Reviewers and the rule analyst read it.
4. **Second labeller.** A second person labels 25 rows of the same sample, blind to the first person's labels. Their
   agreement is the **human ceiling**: no system score above it means anything. Save it as `round-NN-second.yaml`.
5. **Sealed split, by brand.** Code puts 20% of brands in sealed gold, chosen by
   `sha256(salt | brand) < 0.20` ([SPEC §6](../SPEC.md)). Do not choose them, and do not mark rows as sealed yourself.
   Only the gate reads sealed gold, and every read is logged.
6. **Never edited by agents.** Once written, a gold row is changed only by a person, with a note in `why`. An agent
   that thinks a label is wrong opens a review item; it does not edit the label.

### 5.2 How many

Each round, label **50** rows. At an accuracy of 85%, 50 rows give a 95% Wilson interval of about **73–92%**
(±10 points). That is enough to see a big change, not a small one.

| Rows | Interval at 85% | Interval at 50% |
|---|---|---|
| 25 | 67–94% | 32–68% |
| 50 | 73–92% | 37–63% |
| 100 | 77–91% | 40–60% |
| 200 | 79–89% | 43–57% |

Add 50 per round. By 200 rows a 5-point change starts to show. Rows from Loop B review count toward the total, but
keep `provenance` so random rows can be scored on their own.

## 6. Domain conventions: `conventions/conventions.yaml`

Conventions are the owner's decisions about how the tree is shaped, where two reasonable people could disagree. Write
each as one plain statement with one example. They become agent instructions and labelling guidance. Template:
[`conventions.example.yaml`](templates/conventions.example.yaml).

```yaml
- id: size-not-node
  statement: Size and pack count are never nodes. A 12-pack of a flavour sits on that flavour.
  example: {title: "Acme Crunch Bites BBQ 12 x 1 oz", path: [Acme Snacks, Crunch Bites, BBQ]}
  decided_by: ana
  decided_at: 2026-11-09
```

These conventions already apply to every domain: size and pack are never nodes; a correct shallower node beats a
wrong deeper one; a shop is not a brand; a gift set of one maker's goods is a node of that maker. Domain examples to
confirm or overrule: OEM vs aftermarket vs "fits <make>" (car parts); model year, not sale year (cars); EDT and EDP
are different products (fragrance); a different format is a separate product while a flavour is a variant (food).
Write down any convention you rely on while labelling: if it is not written down, the second labeller cannot follow it.

## 7. Rule proposals

Rules come in two kinds. **Everything you write starts as `status: proposal`.** It moves on (`shadow`, then
`admitted`) only when it is shown to hold on **gold**; no one promotes it by hand. Keep it small: **3 of each kind per
domain**. Do not put real titles in the rules (they may be copied into the public repo); use short paraphrased
examples.

### 7.1 Code rules: a check, a decision, its params

A code rule switches on one existing check from [`taxo/tools/checks.py`](../taxo/tools/checks.py) and says what
happens when it fires. Template: [`rules.example.yaml`](templates/rules.example.yaml).

| Field | Meaning |
|---|---|
| `id` | short slug, unique in the domain |
| `check` | one of: `count_agree`, `count_omission`, `measure_agree`, `set_conflict`, `concentration_conflict`, `audience_conflict`, `form_conflict`, `title_lacks_product`, `sibling_word`, `too_shallow`, `twin_of` |
| `decision` | `veto` (the candidate node is removed; the agent cannot override) · `abstain` (no auto-accept; it goes on with a question) · `info` (a hint to the agent) |
| `params` | the check's arguments, e.g. `{tolerance: 0.12}` |
| `description` | one sentence, in plain words |
| `origin`, `evidence` | where the idea came from, and what supports it (and whether that evidence is human or LLM) |
| `status` | `proposal` |

If no existing check fits, write the rule with `check: new` and a `description` of what it should test. A developer
writes the check; until then it stays a proposal.

| Domain | `id` | `check` → `decision` | Why |
|---|---|---|---|
| food | `fd-count-agree` | `count_agree` → `veto`, `{tolerance: 0.12}` | A 4-pack node cannot take a 12-pack listing. The one check that held on human labels in Pedia. |
| food | `fd-title-names-product` | `title_lacks_product` → `abstain` | The node's own name words must be in the title. |
| food | `fd-sibling-format` | `sibling_word` → `info` | "Minis" or "zero" in the title points to a sibling node. |
| fragrance | `fr-concentration` | `concentration_conflict` → `veto` | An EDT listing never goes on the EDP product. |
| fragrance | `fr-audience` | `audience_conflict` → `veto` | A women's listing never goes on the men's counterpart. |
| fragrance | `fr-set` | `set_conflict` → `abstain` | A gift set offered for a single bottle, or the reverse. |
| cars | `cr-model-in-title` | `title_lacks_product` → `abstain` | The model name must appear in the title or fields. |
| cars | `cr-version-deeper` | `too_shallow` → `info` | The title names a version the node has as a child. |
| cars | `cr-twin-version` | `twin_of` → `info` | "Advance" vs "Advance CVT" may be one trim (your convention decides). |

### 7.2 Agentic rules: one instruction line for the agent

An agentic rule is one sentence added to the prompt of the agent that places listings and creates entities. Use it
for judgement a check cannot make. Template: [`agentic.example.yaml`](templates/agentic.example.yaml).

```yaml
- id: cr-model-year
  text: The year node is the model year printed in the listing, never the year it was sold or published. With no year, stop at the version.
  origin: cars owner convention
  evidence: "convention; to be tested on gold round 01"
  status: proposal
```

Three to start from per domain:

- **Food:** `fd-size-not-node`, `fd-title-names-child` and `fd-shop-not-brand` (already in
  `domains/food/memory/rules/agentic.yaml`).
- **Fragrance:** `fr-concentration-separates`, `fr-counterparts` and `fr-no-product-named` (already in
  `domains/fragrance/memory/rules/agentic.yaml`).
- **Cars** (new):
  - `cr-model-year` (above);
  - `cr-version-from-catalogue`: "Place on a version only if it matches a catalogue version for that make, model and
    year; otherwise stop at the model.";
  - `cr-dealer-not-make`: "A dealer or seller name is never the make."

**The difference, in one line:** a code rule is a check that code runs on every candidate and that the agent cannot
argue with; an agentic rule is advice the agent reads and may get wrong. Prefer a code rule when a check already
exists.

## 8. Where the data lives

Nothing internal goes in this public repo: no listings, gold, titles or exports. The repo holds code, the templates
and pointers. Data lives on Drive:

```
G:\My Drive\meta-pedia-data\<domain>\          <domain> = food | fragrance | cars
  listings\     listings.jsonl              (§3)        SOURCE.md
  taxonomy\     taxonomy.jsonl              (§4.2)      SOURCE.md
  registry\     <brand-slug>.yaml           (§4.4)      SOURCE.md
  gold\         round-NN.yaml, round-NN-second.yaml, sample-rNN.jsonl, imported files   SOURCE.md
  rules\        rules.yaml, agentic.yaml    (§7)        SOURCE.md
  conventions\  conventions.yaml            (§6)        SOURCE.md
```

- **Formats:** JSONL for rows, YAML for anything a person writes or reads (gold, rules, conventions, registry).
  Parquet is fine for a large raw export, but put it under `listings\raw\` next to the JSONL; the pipeline reads JSONL.
- **`SOURCE.md` in every folder:** where the data came from (path, export or scrape run), the date, the filters and
  sampling (with the seed), the row counts, the field mapping, and anything known to be wrong. Template:
  [`SOURCE.example.md`](templates/SOURCE.example.md).
- **Do not overwrite.** A new export is a new file or a new dated folder. Gold files are append-only: new rounds are
  new files.
- **Pointer:** set `TAXO_DATA_DIR=G:/My Drive/meta-pedia-data` in your `.env` (see [`.env.example`](../.env.example)).
  The adapters (`domains/<d>/adapter.py`) read `<TAXO_DATA_DIR>/<domain>/...`.

## 9. Silver: what it is, and why you do not provide it

**Silver** is what the validator agent says about listings no one has labelled ([SPEC §5.2](../SPEC.md)). It is
useful for finding where to look: the cases where the validator and the pipeline disagree go to a person for review.
It is **never truth**. A rule is never scored on silver, and silver never becomes gold unless a person reviews the
row, which then goes into gold with `provenance: review`. Silver is written by the system under `runs/`, outside Git.
**You do not need to provide any.** If someone gives you a file of "labels" made by a model, it is silver: keep it out
of `gold\`.
