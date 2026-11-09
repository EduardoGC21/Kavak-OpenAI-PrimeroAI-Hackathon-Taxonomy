"""Fragrance-only candidate text used by the original baseline checks."""
from collections import Counter

from taxo.lattice.vocab import tokens
from taxo.tools.pedia.fragrance import CONC

AUDIENCE = {"women": "for women", "womens": "for women", "for her": "for women", "pour femme": "for women",
            "men": "for men", "mens": "for men", "for him": "for men", "pour homme": "for men"}
CONCENTRATION = {" ".join(tokens(spelled)): canon for spelled, canon in CONC}
HAND_EDITS = [
    ("variant", "audience", ["for unisex", "for women and men", "for men and women"]),
    ("variant", "concentration", ["eau de perfume"]),
    ("strip", None, ["single item", "non toxic", "bottle"]),
]


def node_text(name, variants, n):
    words = [name]
    for axis in ("concentration", "audience", "form", "pack"):
        counts = Counter()
        for value, count in (variants.get(axis) or {}).items():
            counts[(CONCENTRATION if axis == "concentration" else AUDIENCE).get(value, value)] += count
        if counts:
            value, count = counts.most_common(1)[0]
            if count >= 0.6 * n:
                words.append(value)
    return " ".join(words)
