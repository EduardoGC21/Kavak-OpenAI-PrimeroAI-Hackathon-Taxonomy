"""Score placements against gold (SPEC §7). Our tree and the gold tree have different levels, so paths are compared by
the NAME WORDS they carry, not by position.

Both paths are reduced to word sets per segment below the brand, with a fixed list of words removed (brand, size,
concentration, audience, generic product words). The list is the scorer's own and never reads vocab.yaml, so a vocab
change cannot move the yardstick.

    E   the gold path's words (all segments), E_k its first k segments
    P   the predicted path's words (all segments), leaf = the deepest predicted segment's words

    exact      E <= P and leaf <= E                     the same product, by name
    shallower  leaf <= E, E not <= P                     right but stopped early (brand only counts here)
    deeper     E <= P, leaf not <= E                     right, then a wrong step down: worse than shallower
    wrong      neither                                   a different product
    wrong_brand / no_brand

Level k (1 = first segment below the brand) is right when E_k <= P and leaf <= E. A deeper answer fails every level.
Reject rows (Pedia fixtures): the shown path must not match (exact: P == E; prefix: E <= P).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from taxo.lattice.vocab import tokens

DROP = set("""
eau de du parfum parfums toilette cologne edp edt edc extrait perfume perfumes fragrance fragrances spray
for men women man woman mens womens him her pour homme femme unisex ladies
the of and by a an la le l el d
ml oz fl floz ounce ounces size set gift colour color
""".split())
SIZES = {"100", "125", "150", "200", "250"}

CLASSES = ("exact", "shallower", "deeper", "wrong", "wrong_brand", "no_brand")


def _keep(t: str, brand_toks: set[str]) -> bool:
    if t in DROP or t in brand_toks:
        return False
    if t[:1].isdigit():                       # sizes go; a bare 3-digit name ("212") stays
        return t.isdigit() and len(t) == 3 and t not in SIZES
    return True


def words(seg: str, brand_toks: set[str] = frozenset()) -> frozenset[str]:
    return frozenset(t for t in tokens(seg) if _keep(t, brand_toks))


def segs(path: list[str], brand_toks: set[str]) -> list[frozenset[str]]:
    """Word sets of the segments below the brand; empty segments (a pure variant level) dropped."""
    return [w for w in (words(s, brand_toks) for s in path[1:]) if w]


@dataclass
class Judged:
    cls: str
    levels: dict[int, bool]          # level -> right (0 = brand; only levels the gold path has)
    reject_ok: bool | None = None    # reject rows: True when the bad path did not come back
    extra: frozenset = frozenset()   # leaf words not in gold
    missing: frozenset = frozenset() # gold words not in the prediction


def judge(pred_brand: str | None, pred_path: list[str], gold_brand: str, gold_path: list[str],
          brand_toks: set[str], compare: str = "prefix", expect: str = "accept") -> Judged:
    E = segs(gold_path, brand_toks)
    Eall = frozenset().union(*E)
    ok_brand = pred_brand == gold_brand
    Pseg = segs(pred_path, brand_toks) if ok_brand else []
    P = frozenset().union(*Pseg)
    leaf = Pseg[-1] if Pseg else frozenset()
    if pred_brand is None:
        cls = "no_brand"
    elif not ok_brand:
        cls = "wrong_brand"
    else:
        covers, inside = Eall <= P, leaf <= Eall
        cls = "exact" if covers and inside else "shallower" if inside else "deeper" if covers else "wrong"
    levels = {0: ok_brand}
    for k in range(1, len(E) + 1):
        levels[k] = ok_brand and frozenset().union(*E[:k]) <= P and leaf <= Eall
    reject_ok = None
    if expect == "reject":
        reject_ok = not (ok_brand and ((P == Eall) if compare == "exact" else (Eall <= P)))
    return Judged(cls, levels, reject_ok, leaf - Eall, Eall - P)


@dataclass
class Report:
    n: int = 0
    classes: Counter = field(default_factory=Counter)
    level_n: Counter = field(default_factory=Counter)
    level_ok: Counter = field(default_factory=Counter)
    rejects: int = 0
    rejects_ok: int = 0

    def add(self, j: Judged, expect: str = "accept") -> None:
        if expect == "reject":
            self.rejects += 1
            self.rejects_ok += bool(j.reject_ok)
            return
        self.n += 1
        self.classes[j.cls] += 1
        for k, ok in j.levels.items():
            self.level_n[k] += 1
            self.level_ok[k] += ok

    def acc(self, k: int) -> float | None:
        return self.level_ok[k] / self.level_n[k] if self.level_n[k] else None

    def summary(self) -> dict:
        n = self.n or 1
        c = self.classes
        return {"accept_rows": self.n, **{k: c[k] for k in CLASSES},
                "exact_rate": round(c["exact"] / n, 3),
                "right_or_shallower": round((c["exact"] + c["shallower"]) / n, 3),
                "harm_rate": round((c["deeper"] + c["wrong"] + c["wrong_brand"]) / n, 3),
                "levels": {k: {"n": self.level_n[k], "acc": round(self.acc(k), 3)} for k in sorted(self.level_n)},
                "reject_rows": self.rejects, "rejects_held": self.rejects_ok}
