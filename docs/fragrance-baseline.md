# Fragrance baseline (Loop A, round 0): 2026-11-09

This is the summary of `runs/fragrance/BASELINE.md`. The full report has example titles and stays outside Git. It
holds no listing titles; product names appear only as gold path segments.

**Run it**

```
uv run python -m taxo.pipeline fragrance --sealed --loop A --round 0 --label baseline
```

It takes 56 s, or about 7 s with `--no-experiments`. Each run appends one KPI row to `runs/fragrance/kpis.jsonl`;
`uv run python -m taxo.kpis fragrance` prints them as a table.

**What ran**

- **Pipeline:** parse, then the brand ladder, then Pedia's lattice (vendored) with `domains/fragrance/vocab.yaml`, then
  YAML rules (`rules/fragrance`, `rules/global`): first match, vetoes wired to `taxo/tools/checks.py`. The agent step
  is a stub: no API key was set, so it made 0 calls. There is no registry step.
- **Listings:** Edu's subset, 14,344 listings in 80 brands.
- **Gold:** 690 rows. 135 come from Pedia's fixtures and 555 from Harry's owner reviews.
- **Split:** by whole brand (`sha256("taxo-sealed-v1|brand") < 0.2`). Dev is lattafa, armaf and khadlaj. Sealed is
  afnan and carolina_herrera. Sealed was read once, and the read is logged.

## Where the listings go

| | Share of 14,344 |
|---|---:|
| Placed by the lattice | 75.3% |
| Settled by a rule (brand only, nothing named) | 2.3% |
| To the agent | 22.4% |
| …no brand (`agent_search`) | 14.3% |
| …under the floor, vetoed or ambiguous (`agent_title`) | 8.0% |

**Vetoes that fired:** set 135, concentration 81, audience 21, count 0. The shadow form-conflict rule would have
changed 716 placements.

## Accuracy on gold (accept rows)

| | Dev (431) | Sealed (141) |
|---|---:|---:|
| Exact | 46.6% | 56.7% |
| Right or shallower | 75.6% | 94.3% |
| Harm (deeper, wrong, wrong brand) | 18.1% | 5.7% |
| Level 0 (brand), 1, 2, 3 | 78.9 / 64.3 / 42.4 / 23.9% | 100 / 63.1 / 55.2 / 8.3% |
| Reject rows held | 75/100 | 14/18 |

**Pedia's own placement** on the gold titles that are in the subset:

| | Exact, ours | Exact, Pedia | Harm, ours | Harm, Pedia |
|---|---:|---:|---:|---:|
| Dev (106 rows) | 50.0% | 61.3% | 31.1% | 36.8% |
| Sealed (69 rows) | 52.2% | 71.0% | 1.4% | 11.6% |

Pedia names the exact product more often, and the free steps are wrong less often. Pedia's score has a tailwind: the
gold was labelled while reviewing Pedia's own output.

## Error shapes on dev

| Shape | n | Cause |
|---|---:|---|
| Shallower, placed: stops a level short | 104 | "elixir" and "intense" are tagged as concentration; "for unisex" is not in the vocab; a title joins the longest supported run inside it |
| Wrong brand: Maison Alhambra | 64 | Harry's ruling makes Maison Alhambra a Lattafa sub-brand; Edu's export makes it a brand |
| No brand: a sub-brand title with no maker word | 27 | Niche Emarati (Lattafa), La Fede (Khadlaj) |
| Shallower, under the floor | 17 | the name is seen once |
| Wrong product | 10 | the longest supported run belongs to a different name ("Badee Al Oud …") |
| Deeper | 4 | descriptive words kept in the name |
| Vetoed by set / audience conflict | 4 | a two-scent bundle of one product; a body spray |

## Vocab changes, measured on dev

| Change | Δ exact | Δ harm |
|---|---:|---:|
| **All the helpful edits together** | **+22 (46.6% → 51.7%)** | **−3** |
| `audience += for unisex, for women and men, for men and women` | +10 | −2 |
| `concentration -= elixir` | +9 | 0 |
| `strip += edition`, `strip += natural`, `concentration -= intense` | +1 each | −1, −1, 0 |
| Lattice `whole_name=True` | −41 | −8 |

The vocab is not changed yet; these edits are candidates for round 1 and must pass the gate.

**Biggest fix outside vocab:** a brand registry with sub-brands (Maison Alhambra and Niche Emarati under Lattafa, La
Fede under Khadlaj). This accounts for 82% of the harmful dev answers.
