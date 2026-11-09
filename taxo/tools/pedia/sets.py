"""Vendored from pedia-harness@3d980add check/ratchets/pack_as_product.py (set/bundle words: title_set_word, node_hit). Pure code; only imports adjusted. Do not edit by hand:
port fixes into taxo/tools/checks.py or re-vendor."""
import re
import unicodedata

from taxo.tools.pedia.text import words

CONVENTION = "food.cnv.20"  # a variety pack is never a product

SET_NOUNS = {"pack", "box", "case", "sampler", "set", "bundle", "tin", "tray", "flavor", "flavour", "mix", "of", "gift"}
TITLE_TOKENS = {"assortment", "sampler", "combo", "kit"}
TITLE_RUNS = [("build", "your", "own"), ("mix", "pack"), ("multi", "flavor", "pack"), ("starter", "set")]
# node names that alone make a pack node
STRONG_NODE = TITLE_TOKENS | {"bundle", "starter"}
STRONG_RUNS = [("build", "your", "own"), ("mix", "pack"), ("starter", "set")]
# node names that make a pack node only when the listing's title names a set too
WEAK_NODE = {"variety", "assortment", "multipack", "set", "collection"}
WEAK_RUNS = [("multi", "pack"), ("gift", "set"), ("value", "pack"), ("pack", "of")]
SINGLE_SERVE = re.compile(r"single[\s-]*serv(e|es|ing|ings)\b", re.IGNORECASE)
KITKAT = ("kit", "kat")
N_FLAVORS = re.compile(r"\b([3-9]|[1-9]\d)\s*(?:different\s+)?flavou?rs?\b", re.IGNORECASE)
SEPARATORS = re.compile(r",|&|\+|/|\band\b", re.IGNORECASE)

DEFINITION = (
    "listings on a model or variant node whose title names a set of different items (variety next to a set noun, "
    "assortment, sampler, combo, kit, build-your-own, mix pack, N flavors, a bundle that lists items), or that sit on or "
    "under a pack node (single-serve, kit, starter, combo, sampler, bundle; variety / assortment / multipack / pack of "
    "only when the title also names a set); page brand words removed (food.cnv.20). One mixed bag `assorted` and one "
    "product x N are not flagged (food.cnv.19); nor are listings on or under a node with role set (food.cnv.20; "
    "counted apart: on_set_nodes, products_on_set_nodes; pack_as_product_v1 = the count without this exclusion)"
)


def _ascii(s: str | None) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def _find(tokens: list, singles: set, runs: list) -> str | None:
    for i, w in enumerate(tokens):
        if w == "kit" and tokens[i : i + 2] == list(KITKAT):
            continue
        if w in singles:
            return w
    for run in runs:
        k = len(run)
        for i in range(len(tokens) - k + 1):
            if tuple(tokens[i : i + k]) == run:
                return " ".join(run)
    return None


def title_set_word(title: str, bw: set) -> str | None:
    """The word that makes a title a set of different items, or None."""
    toks = [w for w in words(title) if w not in bw]
    h = _find(toks, TITLE_TOKENS, TITLE_RUNS)
    if h:
        return h
    for i, w in enumerate(toks):
        if w == "variety" and (
            (i + 1 < len(toks) and toks[i + 1] in SET_NOUNS) or (i and toks[i - 1] in ("flavor", "flavour", "multi"))
        ):
            return "variety"
        if w == "bundle" and len(SEPARATORS.findall(_ascii(title))) >= 2:
            return "bundle"
    if N_FLAVORS.search(_ascii(title)):
        return "n flavors"
    return None


def _node_hit(label: str, bw: set) -> tuple[str, bool] | None:
    """(word, needs_title_set) when the node's own name is a pack / set node."""
    if SINGLE_SERVE.search(_ascii(label)):
        return "single-serve", False
    toks = [w for w in words(label) if w not in bw]
    h = _find(toks, STRONG_NODE, STRONG_RUNS)
    if h:
        return h, False
    h = _find(toks, WEAK_NODE, WEAK_RUNS)
    if h:
        return h, True
    if toks and all(w in ("pack", "set", "collection", "of", "box") or w.isdigit() for w in toks):
        return " ".join(toks), True  # a bare 'Pack' / 'Pack of 3' node
    return None
