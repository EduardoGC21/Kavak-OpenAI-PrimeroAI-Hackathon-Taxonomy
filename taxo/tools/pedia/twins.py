"""Vendored from pedia-harness@3d980add pipeline/populate/loop/ladder.py (nesting, twin_among, same_product). Pure code; only imports adjusted. Do not edit by hand:
port fixes into taxo/tools/checks.py or re-vendor."""
TWIN_WORDS_MIN = 2  # scopes/food/rules/loop/settings.yaml twin_words_min


def nesting(mine: set[str], theirs: set[str]) -> int:
    """How two product names' words (brand words off) nest: 3 one inside the other and the smaller has >= 2 words (the
    same product named longer or shorter: "Oud for Glory" in "Badee Al Oud For Glory"), 2 one inside the other, 1 at
    least two shared words and half the shorter, 0 not at all."""
    if not mine or not theirs:
        return 0
    if mine <= theirs or theirs <= mine:
        return 3 if min(len(mine), len(theirs)) >= TWIN_WORDS_MIN else 2
    shared = len(mine & theirs)
    return 1 if shared >= TWIN_WORDS_MIN and 2 * shared >= min(len(mine), len(theirs)) else 0


def twin_among(mine: set[str], pool: list[tuple[set[str], object]]) -> tuple[int, object] | None:
    """(strength, existing) for the existing name that nests best with `mine` (strength, then shared words; the first
    of equals)."""
    ranked = sorted(((nesting(mine, w), len(mine & w), i) for i, (w, _) in enumerate(pool)), key=lambda x: (-x[0], -x[1], x[2]))
    if not ranked or ranked[0][0] == 0:
        return None
    return ranked[0][0], pool[ranked[0][2]][1]


def same_product(mine: tuple[str, ...], audience: frozenset, pool: list[tuple[tuple[str, ...], bool, frozenset, object]]
                 ) -> object | None:
    """The existing node a new product is, by its name's words in order (brand, concentration, edition and audience words
    off), from `pool` (words, is a line, audience, node): the same name; else the one existing name that ends with it,
    two words or more ("Oud for Glory" is "Badee Al Oud For Glory": the line said first); else the longest line whose
    name starts it ("Al Dur Al Maknoon Lulu Al Abyedh" belongs to the line Al Dur Al Maknoon). A name inside another
    ("Star Men" in "Star Men Nebula") is a different product; a name that states an audience is not a product of
    another or an unknown one ("Code for Women" is not the men's "Code"; a line takes any). Of same-named nodes the
    first in `pool` wins: pass the plainest first. A space whose new products pass no check lands them there; food's
    judge checks its twins."""
    pool = [(w, line, x) for w, line, aud, x in pool if line or not audience or aud == audience]
    if not mine:
        return None
    n = len(mine)
    same = [(w, x) for w, _, x in pool if w == mine]
    ends = [(w, x) for w, _, x in pool if n >= 2 and len(w) > n and w[-n:] == mine]
    for found in (same, ends):
        if found and len({w for w, _ in found}) == 1:
            return found[0][1]
        if found:
            return None
    lines = [(w, x) for w, line, x in pool if line and 2 <= len(w) < n and mine[:len(w)] == w]
    return max(lines, key=lambda t: len(t[0]))[1] if lines else None
