# Vendored from pedia-harness@3d980add packages/engine/pedia_engine/lattice/count.py, unchanged.
# Pure (standard library). Do not edit: build the vocabulary in taxo/lattice/vocab.py instead.
"""Names by counting (taxonomy v1 FR-00, N1-N9; v6 package P1, part `count-names`): one brand's name records in, its
counted products (clusters), family roots and the unclear cases for agents out. Pure: no I/O, no word list.

    vocab = CountVocab.from_taxonomy(tv)                 # tv: pedia_engine.contracts.TaxonomyView of the scope
    bc = count_brand(records, vocab, official_groups)    # records: NameRecord per name statement of the brand
    bc.key_map        {old subject_key: cluster key}     (every key of every record; never drops a key)
    bc.clusters       {cluster key: Cluster}             n, families, members, variant values seen, floor status
    bc.families       [FamilyRoot]                       N9 roots of 2+ distinct supported cluster names
    bc.ranges         [RangeParent]                      an official range over 2+ counted families (Harry A2)
    bc.unclear        [dict]                             the agent band: 50-90% shares, under the floor, count vs official
    counts_block(bc)  -> str                             the AGENT-CARD §2 counts block of the brand

Vocabulary comes only from the taxonomy (`CountVocab.from_taxonomy`): a span whose class's effect is in the class model's
`counting.strip_effects` (variant / counterpart with an axis, typed_product, trade_item, strip, ...) or whose class is in
`counting.strip_classes` (edition, C12) is a VARIANT token, taken out before names are counted (N2) and kept as the
record's value on its axis; `bind` classes (particle, function) never end a root; `counting.fragment_classes` (number)
and tokens of <= `fragment_chars` characters or all digits are FRAGMENTS (N3). A word added to a class changes the count
on the next run with no code change.

The steps, per brand:
  N2  tag: variant tokens out (value kept per axis); a fragment token is never taken out as a variant on its own.
  N3  bind: a fragment f binds to the neighbour w it stands next to in >= bind_share of the records that hold f
      (neighbours counted before the variant tokens are taken out, so "l" + "homme" is a unit and "pm" + "9" is one;
      a fragment may bind to a fragment). Bound tokens form one unit. A bound fragment whose partner is missing in a
      record gets it back (a record cut from a longer name: Parfumo "am Dive" is "9 AM Dive"). A fragment that binds
      to nothing is dropped, unless it is the whole name of most of its records and an official / catalog name
      ("212"), or a bind-class word inside a name.
  N5  n(s), fam(s) for every contiguous unit sequence; kept when n >= support_floor or an official / catalog name
      equals it.
  N6  each record joins its MAXIMAL kept sequence (longest, then most records, then leftmost) = its cluster. A cluster
      under the floor that is a piece of exactly one shortest longer cluster name joins it; else it stays (unclear).
  N7  per cluster and axis of `always_axes` (audience): one value on >= always_share of the cluster's records, in
      every source family, no other value -> the word stays in the NAME (YSL L'Homme); 50-90% -> unclear.
  N8  an official name that differs from its cluster's name, a fragment bound on 50-90%, a cluster under the floor
      -> unclear.
  N9  family roots: a leading unit sequence shared by 2+ distinct supported cluster names (names AFTER the variant
      tokens are out), the longest one for a member set; never a lone fragment, a generic root (generic-roots.yaml)
      or a sequence ending in a bind word unless an official / catalog name equals it. A root inside another root's
      family is a nested candidate (unclear, family-in-family).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

DEFAULTS: dict[str, Any] = {
    "strip_effects": ["variant", "counterpart", "typed_product", "trade_item", "strip"],
    "axis_required": ["variant", "counterpart"],
    "strip_classes": [],
    "phrase_classes": [],
    "root_veto_effects": [],
    "phrase_word_effects": ["name", "descriptor"],
    "always_axes": [],
    "fragment_classes": [],
    "fragment_chars": 2,
    "bind_share": 0.9,
    "always_share": 0.9,
    "unclear_band": [0.5, 0.9],
    "support_floor": 2,
    "max_units": 12,
    # part root-not-grouping-words (E18): a root every word of which is of these effects (bind words aside) names no family
    "root_attr_effects": ["grouping", "trade_item", "composition", "other_product"],
}


@dataclass(frozen=True)
class NameRecord:
    """One name statement of a brand. `rid`: the listing (mention) or source record; `key`: its subject_key;
    `source`: listing | catalog | official; `primary`: False for a record's other spellings (official alias / title),
    which are not counted and join the cluster of the record's primary name unless their own name is a cluster."""
    rid: str
    key: str
    family: str
    source: str = "listing"
    primary: bool = True
    orig: str | None = None              # the claim's own subject_key when `key` is a cleaned form of it


@dataclass
class Tagged:
    toks: tuple[str, ...]
    var: tuple[tuple[str, str] | None, ...]      # per token: (axis, value) of a variant token, else None
    bind: tuple[bool, ...]                       # per token: a bind-class word (particle, function)
    frag: tuple[bool, ...]                       # per token: a fragment (N3)
    desc: tuple[bool, ...] = ()                  # per token: a generic word class (descriptor effect or member-word class)
    attr: tuple[bool, ...] = ()                  # per token: only attribute effects (counting.root_attr_effects), no name class
    glue: tuple[bool, ...] = ()                  # per pair (i, i+1): one multi-word taxonomy phrase kept as a name ("le parfum")
    veto: tuple[bool, ...] = ()                  # per token: a word of a class that never roots a family (counting.root_veto_effects)
    memb: tuple[bool, ...] = ()                  # per token: a word of a member-word class (G5 MEMBER-WORD: colour, note, accord)


class CountVocab:
    """What the count reads from the taxonomy: a tagger over token tuples, the generic roots and the thresholds."""

    def __init__(self, tag: Callable[[tuple[str, ...]], Tagged], generic: Iterable[str] = (),
                 settings: dict[str, Any] | None = None):
        self._tag = tag
        self._memo: dict[tuple[str, ...], Tagged] = {}
        self.generic = frozenset(generic)
        self.s = {**DEFAULTS, **(settings or {})}

    def tag(self, toks: tuple[str, ...]) -> Tagged:
        t = self._memo.get(toks)
        if t is None:
            t = self._memo[toks] = self._tag(toks)
        return t

    @classmethod
    def from_taxonomy(cls, tv: Any) -> CountVocab:
        """The vocabulary of a `TaxonomyView`: classes + effects + the class model's `counting` setting."""
        settings = {**DEFAULTS, **(tv.setting("counting", {}) or {})}
        classes = tv.classes()
        strip_eff = set(settings["strip_effects"])
        need_axis = set(settings["axis_required"])
        strip_cls = set(settings["strip_classes"])
        frag_cls = set(settings["fragment_classes"])
        nchars = int(settings["fragment_chars"])
        member = set(tv.member_word_classes() or [])
        phrase_cls = set(settings["phrase_classes"])
        veto_eff = set(settings["root_veto_effects"])
        phrase_eff = set(settings["phrase_word_effects"])
        attr_eff = set(settings["root_attr_effects"])

        def axis_of(c: str | None) -> str | None:
            return ((classes.get(c or "") or {}).get("axis")) or c

        def stripped(span: Any) -> bool:
            c = span.word_class
            if c is None:
                return False
            if c in strip_cls:
                return True
            eff = span.effect
            if eff not in strip_eff:
                return False
            return eff not in need_axis or bool((classes.get(c) or {}).get("axis"))

        def tag(toks: tuple[str, ...]) -> Tagged:
            n = len(toks)
            var: list[tuple[str, str] | None] = [None] * n
            bind = [False] * n
            frag = [len(t) <= nchars or t.isdigit() for t in toks]
            desc = [False] * n
            eff_at: list[str | None] = [None] * n
            attr = [False] * n
            phrases: list[Any] = []
            glue = [False] * max(n - 1, 0)
            veto = [False] * n
            memb = [False] * n
            spans = tv.resolve(list(toks), None)
            for sp in spans:
                effs = set((sp.classes or {sp.word_class: sp.effect}).values())
                for i in range(sp.start, min(sp.end, n)):
                    eff_at[i] = sp.effect
                    attr[i] = bool(effs) and effs <= attr_eff
                    if any(e in veto_eff for e in (sp.classes or {sp.word_class: sp.effect}).values()):
                        veto[i] = True
                    if any(c in member for c in (sp.classes or {sp.word_class: sp.effect})):
                        memb[i] = True
                    if sp.effect == "bind":
                        bind[i] = True
                    if any(e == "descriptor" or c in member for c, e in (sp.classes or {sp.word_class: sp.effect}).items()):
                        desc[i] = True
                    if sp.word_class in frag_cls:
                        frag[i] = True
                if stripped(sp) and not (sp.end - sp.start == 1 and frag[sp.start]):
                    value = sp.canonical or "_".join(toks[sp.start:sp.end])
                    for i in range(sp.start, min(sp.end, n)):
                        var[i] = (axis_of(sp.word_class) or "", value)
                    if sp.word_class in phrase_cls:
                        phrases.append(sp)
            for sp in phrases:              # an edition PHRASE is one variant unit (C12; editions.named_edition_value's shape)
                lo, hi = sp.start, min(sp.end, n)
                bare = (sp.canonical or "") == sp.word_class      # the class's own word ("Edition"): it names with the word before
                j = lo - 1
                if j >= 0 and var[j] is None and not bind[j] and (
                        toks[j].isdigit() or (bare and (eff_at[j] is None or eff_at[j] in phrase_eff))):
                    lo = j                                         # "Gold Edition", "Rainbow Edition", "2024 Limited Edition"
                    while lo - 1 >= 0 and var[lo - 1] is None and bind[lo - 1] and not frag[lo - 1]:
                        lo -= 1                                    # "The Red Edition"
                while hi < n and var[hi] is None and toks[hi].isdigit():
                    hi += 1                                        # "Limited Edition 2024"
                if (lo, hi) != (sp.start, sp.end):
                    value = "_".join(toks[lo:hi])
                    for i in range(lo, hi):
                        var[i] = (axis_of(sp.word_class) or "", value)
            for sp in spans:                # a multi-word phrase of a class that stays in the name is one unit, no fragments
                if sp.word_class is not None and sp.end - sp.start > 1 and var[sp.start] is None:
                    for i in range(sp.start, min(sp.end, n)):
                        frag[i] = False
                        if i + 1 < min(sp.end, n):
                            glue[i] = True
            return Tagged(toks, tuple(var), tuple(bind), tuple(frag), tuple(desc), tuple(attr), tuple(glue), tuple(veto), tuple(memb))

        generic = {str(r.get("canonical") or r.get("spelling") or "") for r in tv.generic_roots()
                   if r.get("status") != "retired"} - {""}
        return cls(tag, generic, settings)


@dataclass
class Cluster:
    key: str                                   # the cluster's name (units joined by spaces) = its C3 key
    base: str                                  # the name before N7 kept an always-there variant word
    units: tuple[str, ...] = ()                # the base name's units (N9 reads these)
    records: set[str] = field(default_factory=set)
    families: set[str] = field(default_factory=set)
    keys: Counter = field(default_factory=Counter)            # old subject_keys -> records
    variants: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))   # axis -> value -> records
    official: str = "none"                     # equal | other name | none (N8)
    catalog: bool = False                      # a catalog record names it exactly
    supported: bool = False                    # n >= floor, or an official / catalog name equals it
    joined_from: list[str] = field(default_factory=list)       # partial clusters folded into it
    sources: Counter = field(default_factory=Counter)          # listing | catalog | official -> records

    @property
    def n(self) -> int:
        return len(self.records)


@dataclass
class FamilyRoot:
    root: str
    members: list[str]                         # cluster keys
    official: bool = False                     # an official / catalog name equals the root
    parent: str | None = None                  # the root of the family it sits in (nested candidate)


@dataclass
class RangeParent:
    name: str                                  # the official range ("9 AM / 9 PM")
    families: list[str]                        # the counted family roots it groups


@dataclass
class BrandCount:
    brand: str
    clusters: dict[str, Cluster]
    key_map: dict[str, str]
    families: list[FamilyRoot]
    nested: list[FamilyRoot]
    ranges: list[RangeParent]
    binds: dict[str, tuple[int, str, int, int]]        # fragment -> (side, word, k, records)
    dropped: Counter                                   # unbound fragments dropped -> records
    unclear: list[dict[str, Any]]
    stats: Counter
    no_name: set[str] = field(default_factory=set)     # keys whose records name nothing (a lone unbound fragment)


# ── helpers ──────────────────────────────────────────────────────────────────────────────────────────────────

def _seqs(u: tuple[str, ...], cap: int) -> set[tuple[str, ...]]:
    m = len(u)
    return {u[i:j] for i in range(m) for j in range(i + 1, min(m, i + cap) + 1)}


def _contains(big: tuple[str, ...], small: tuple[str, ...]) -> bool:
    k = len(small)
    return any(big[i:i + k] == small for i in range(len(big) - k + 1))


def show(units: Iterable[str]) -> str:
    return " ".join(units)


# ── the count ────────────────────────────────────────────────────────────────────────────────────────────────

def count_brand(brand: str, records: list[NameRecord], vocab: CountVocab,
                official_groups: dict[str, set[str]] | None = None, whole_name: bool = False,
                bind_end: bool = False, attr_root: bool = False, brand_words: Iterable[str] = ()) -> BrandCount:
    """`whole_name` (v6 part count-whole-name): a record whose name units go beyond its maximal kept sequence names more
    than that sequence ("Pink Velvet" next to a counted "Velvet", "Musk Code" next to "Musk"): it counts as its own
    name (under the floor it is joined only to a longer name holding it), never as the shorter sequence.
    `bind_end` (v6 part root-no-bind-end, E3/E7): a root whose last word is a bind-class word is never a family root,
    whatever its length ("Fleur de", "Sultana of", "Somow Al") and even when a record names it (a cut name).
    `attr_root` (v6 part root-not-grouping-words, E18): a root every word of which is an attribute word (effects
    `counting.root_attr_effects`: grouping, trade item ...; bind words aside) is no family root ("Signature", "Series",
    "Collection Privee") unless an OFFICIAL name equals it (a catalogue record alone does not)."""
    s = vocab.s
    floor, bshare, ashare = int(s["support_floor"]), float(s["bind_share"]), float(s["always_share"])
    lo, hi = (float(x) for x in s["unclear_band"])
    cap = int(s["max_units"])
    always_axes = set(s["always_axes"])
    stats: Counter = Counter()
    unclear: list[dict[str, Any]] = []

    prim = [r for r in records if r.primary and r.key]
    def _cmp(x: str) -> str:
        return "".join(ch for ch in x.casefold() if ch.isalnum())

    marks = frozenset(m for m in (_cmp(b) for b in brand_words if b) if m)    # compact brand forms

    def unbranded(toks: tuple[str, ...]) -> tuple[str, ...]:
        """N2 / CONNECTIONS chain 1 (part count-strip-brand): a leading brand, alias or sub-brand mark is no name word
        ("DKNY Be Delicious" -> "Be Delicious", "Clean Reserve" -> "Reserve") when a DISTINCTIVE word remains (not a
        variant, fragment, bind or root-veto word); otherwise the mark stays ("Dior Homme")."""
        if not marks:
            return toks
        for k in range(len(toks) - 1, 0, -1):
            if _cmp("".join(toks[:k])) in marks:
                rest = toks[k:]
                t = vocab.tag(rest)
                if any(t.var[i] is None and not t.frag[i] and not t.bind[i] and not (t.veto and t.veto[i])
                       for i in range(len(rest))):
                    stats["brand_stripped"] += 1
                    return rest
                return toks
        return toks

    tagged = {k: vocab.tag(unbranded(tuple(k.split()))) for k in {r.key for r in records if r.key}}
    brand_marks = marks

    # N3: neighbours of each fragment over the records (raw token order: variant words included)
    nf: Counter = Counter()
    nb: dict[str, Counter] = defaultdict(Counter)
    whole: Counter = Counter()
    named_whole: set[str] = set()
    for r in prim:
        t = tagged[r.key]
        seen_f: set[str] = set()
        seen_n: set[tuple[str, int, str]] = set()
        name_idx = [i for i in range(len(t.toks)) if t.var[i] is None]
        for i, tok in enumerate(t.toks):
            if not t.frag[i]:
                continue
            seen_f.add(tok)
            for j in (i - 1, i + 1):
                if 0 <= j < len(t.toks):
                    seen_n.add((tok, j - i, t.toks[j]))
        for tok in seen_f:                      # a fragment standing alone gives no neighbour evidence (N3 exception)
            if any(x[0] == tok for x in seen_n):
                nf[tok] += 1
        for tok, side, w in seen_n:
            nb[tok][(side, w)] += 1
        if len(name_idx) == 1 and t.frag[name_idx[0]]:
            whole[t.toks[name_idx[0]]] += 1
            if r.source in ("official", "catalog"):
                named_whole.add(t.toks[name_idx[0]])
    binds: dict[str, tuple[int, str, int, int]] = {}
    for f, c in nb.items():
        if not c:
            continue
        (side, w), k = min(c.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
        share = k / nf[f]
        if share >= bshare and k >= floor:
            binds[f] = (side, w, k, nf[f])
        elif share >= lo and k >= floor:
            unclear.append({"kind": "fragment_band", "fragment": f, "word": w, "k": k, "n": nf[f],
                            "share": round(share, 3)})

    # an unbound fragment that is the whole name of >= floor records, an official / catalog one among them, is a name
    # of its own (212, CH; N3's exception); a bound fragment never is (Parfumo "am" is "9 AM" cut)
    standalone = {f for f in whole if f in named_whole and whole[f] >= floor and f not in binds}
    dropped: Counter = Counter()

    def units_of(key: str, keep: frozenset[str] = frozenset()) -> tuple[tuple[str, ...], dict[str, str], bool]:
        """(name units, {axis: value}, completed) of one key; variant words of the `keep` axes stay name words."""
        t = tagged[key]
        toks = list(t.toks)
        var = [None if v is not None and v[0] in keep else v for v in t.var]
        bind = list(t.bind)
        frag = list(t.frag)
        glue = list(t.glue) if t.glue else [False] * max(len(toks) - 1, 0)
        completed = False
        # completion: a bound fragment whose partner is missing gets it back
        i = 0
        while i < len(toks):
            b = binds.get(toks[i]) if frag[i] else None
            if b is not None:
                side, w = b[0], b[1]
                j = i + side
                if (j < 0 or j >= len(toks)) and len(toks) > 0:   # the partner's place is outside the name: cut
                    ins = i if side < 0 else i + 1
                    toks.insert(ins, w)
                    var.insert(ins, None)
                    bind.insert(ins, False)
                    frag.insert(ins, w in nf)
                    if len(toks) > 1:
                        glue.insert(0 if ins == 0 else len(glue), False)
                    completed = True
                    i += 1
            i += 1
        n = len(toks)
        link = [False] * max(n - 1, 0)          # link[i]: toks[i] and toks[i+1] are one unit
        for i in range(n - 1):
            if i < len(glue) and glue[i]:
                link[i] = True
                continue
            a, b2 = binds.get(toks[i]) if frag[i] else None, binds.get(toks[i + 1]) if frag[i + 1] else None
            if (a is not None and a[0] == 1 and a[1] == toks[i + 1]) or (b2 is not None and b2[0] == -1 and b2[1] == toks[i]):
                link[i] = True
        values: dict[str, str] = {}
        units: list[str] = []
        i = 0
        while i < n:
            j = i
            while j < n - 1 and link[j]:
                j += 1
            if j > i:                                   # a bound unit
                vs = [var[x] for x in range(i, j + 1) if var[x] is not None]
                if vs:                                  # a fragment bound to a variant word is part of its value
                    ax = vs[0][0]                       # (an edition and its year: "Edition 2024")
                    values.setdefault(ax, "_".join(toks[i:j + 1]))
                else:
                    units.append(" ".join(toks[i:j + 1]))
                i = j + 1
                continue
            tok = toks[i]
            if var[i] is not None:
                ax, v = var[i]
                values.setdefault(ax, v)
            elif frag[i] and tok not in standalone and not (bind[i] and units and i < n - 1):
                dropped[tok] += 1
            else:
                units.append(tok)
            i += 1
        if units and all(u in toks and bind[toks.index(u)] for u in units):
            units = []                                  # function words alone name nothing ("Lot of")
        if not units and not any(frag) and toks:        # only variant words: they are the name ("Pour Homme")
            units = [tok for tok, v in zip(toks, var) if v is not None]
            values = {}
        return tuple(units[:cap * 2]), values, completed

    U: dict[str, tuple[tuple[str, ...], dict[str, str], bool]] = {k: units_of(k) for k in tagged}

    # N5: n(s), fam(s)
    n_s: Counter = Counter()
    fam_s: dict[tuple[str, ...], set[str]] = defaultdict(set)
    seen_rec: dict[tuple[str, ...], set[str]] = defaultdict(set)
    named: dict[tuple[str, ...], set[str]] = defaultdict(set)      # sequences an official / catalog record names
    for r in prim:
        u = U[r.key][0]
        if not u:
            continue
        for q in _seqs(u, cap):
            if r.rid not in seen_rec[q]:
                seen_rec[q].add(r.rid)
                n_s[q] += 1
            fam_s[q].add(r.family)
        if r.source in ("official", "catalog"):
            named[u].add(r.source)
    kept = {q for q, k in n_s.items() if k >= floor} | set(named)

    def maximal(u: tuple[str, ...]) -> tuple[str, ...] | None:
        best, bk = None, None
        m = len(u)
        for i in range(m):
            for j in range(i + 1, m + 1):
                q = u[i:j]
                if q in kept:
                    k = (-len(q), -n_s[q], i)
                    if bk is None or k < bk:
                        best, bk = q, k
        return best

    # N6: each record joins its maximal kept sequence
    cl: dict[tuple[str, ...], Cluster] = {}
    rec_cluster: dict[str, tuple[str, ...]] = {}

    def cluster(q: tuple[str, ...]) -> Cluster:
        c = cl.get(q)
        if c is None:
            c = cl[q] = Cluster(key=show(q), base=show(q), units=q)
        return c

    for r in prim:
        u, values, completed = U[r.key]
        if not u:
            stats["records_no_name"] += 1
            continue
        stats["completed"] += completed
        q = maximal(u) or u
        if whole_name and q != u:                # part count-whole-name: extra name words make another name
            q = u
            stats["whole_name_kept"] += 1
        c = cluster(q)
        c.records.add(r.rid)
        c.families.add(r.family)
        c.sources[r.source] += 1
        c.keys[r.key] += 1
        for ax, v in values.items():
            c.variants[ax][v] += 1
        rec_cluster[r.rid + "\x00" + r.key] = q
        rec_cluster.setdefault(r.rid, q)
    for q, c in cl.items():
        c.catalog = "catalog" in named.get(q, ())
        c.supported = c.n >= floor or bool(named.get(q))

    # partial clusters under the floor: join the unique shortest longer cluster name holding them
    for q in sorted(cl, key=lambda x: (len(x), x)):
        c = cl[q]
        if c.supported:
            continue
        hold = [o for o in cl if o != q and len(o) > len(q) and cl[o].supported and _contains(o, q)]
        if hold:
            m = min(len(o) for o in hold)
            short = [o for o in hold if len(o) == m]
            if len(short) == 1:
                t = cl[short[0]]
                t.records |= c.records
                t.families |= c.families
                t.keys.update(c.keys)
                for ax, vs in c.variants.items():
                    t.variants[ax].update(vs)
                t.joined_from.append(c.key)
                for rid, qq in list(rec_cluster.items()):
                    if qq == q:
                        rec_cluster[rid] = short[0]
                del cl[q]
                stats["partial_joined"] += 1
                continue
        unclear.append({"kind": "under_floor", "cluster": c.key, "n": c.n, "keys": sorted(c.keys)})

    # N6b (E2): "<R> X" next to "X", where R is a counted family root of the brand and "<R> X" is the only name that
    # holds X: one product (the listings that leave the range word out), named by the longer name
    top, sub = _roots(cl, vocab, named, brand_marks)
    root_s = {f.root for f in top + sub}
    ext = {q for q in cl for o in cl if len(o) > len(q) and o[:len(q)] == q}      # names other names extend
    for q in sorted(cl, key=lambda x: (len(x), x)):
        c = cl.get(q)
        if c is None or q in ext:
            continue
        lt = vocab.tag(tuple(show(q).split()))
        if (len(q) == 1 and (lt.frag[0] or lt.desc[0] or q[0] in vocab.generic)) or all(lt.bind):
            continue                                   # a fragment, a generic or function word alone never joins a name
        hold = [o for o in cl if len(o) > len(q) and o[len(o) - len(q):] == q and show(o[:len(o) - len(q)]) in root_s]
        if len(hold) != 1 or not cl[hold[0]].supported:
            if len(hold) > 1:
                unclear.append({"kind": "prefix_twin_ambiguous", "cluster": c.key, "holders": [show(o) for o in hold]})
            continue
        t = cl[hold[0]]
        t.records |= c.records
        t.families |= c.families
        t.keys.update(c.keys)
        for ax, vs in c.variants.items():
            t.variants[ax].update(vs)
        t.joined_from.append(c.key)
        for rid, qq in list(rec_cluster.items()):
            if qq == q:
                rec_cluster[rid] = hold[0]
        del cl[q]
        stats["prefix_twin_joined"] += 1

    # N7: an always-there word of an always-axis stays in the name
    rename: dict[tuple[str, ...], tuple[str, ...]] = {}
    for q, c in cl.items():
        for ax in sorted(always_axes):
            vs = c.variants.get(ax)
            if not vs or c.n == 0:
                continue
            v, k = min(vs.items(), key=lambda kv: (-kv[1], kv[0]))
            share = k / c.n
            fams_with = {r.family for r in prim if rec_cluster.get(r.rid + "\x00" + r.key) == q
                         and (U[r.key][1].get(ax) == v)}
            if share >= ashare and len(vs) == 1 and fams_with >= c.families and c.n >= floor:
                carriers = Counter(r.key for r in prim if rec_cluster.get(r.rid + "\x00" + r.key) == q
                                   and U[r.key][1].get(ax) == v)
                best = min(carriers.items(), key=lambda kv: (-kv[1], kv[0]))[0]
                nq = units_of(best, frozenset({ax}))[0]
                if nq and nq != q and nq not in cl and nq not in rename.values():
                    rename[q] = nq
                    stats["always_kept"] += 1
            elif k >= floor and (lo <= share < ashare or (share >= ashare and len(vs) > 1)):
                unclear.append({"kind": "variant_band", "cluster": c.key, "axis": ax, "value": v, "k": k,
                                "n": c.n, "share": round(share, 3), "values": dict(vs)})
    for q, nq in rename.items():
        c = cl.pop(q)
        c.key = show(nq)
        c.variants.pop(next(ax for ax in sorted(always_axes) if ax in c.variants), None)
        cl[nq] = c

    # official names vs the count (N8)
    for r in records:
        if r.source != "official" or not r.primary or not r.key:
            continue
        q = rec_cluster.get(r.rid + "\x00" + r.key)
        c = cl.get(rename.get(q, q)) if q else None
        if c is None:
            continue
        if c.key == r.key or c.base == r.key:
            c.official = "equal"
        else:
            if c.official != "equal":
                c.official = "other name"
            unclear.append({"kind": "official_differs", "cluster": c.key, "official": r.key})

    # key map: every key of every record
    by_base = {c.base: c.key for c in cl.values()}
    key_map: dict[str, str] = {}
    for r in prim:
        q = rec_cluster.get(r.rid + "\x00" + r.key)
        if q is not None:
            key_map.setdefault(r.key, cl[rename.get(q, q)].key)
    for r in records:
        if r.key in key_map or not r.key:
            continue
        u = U[r.key][0]
        q = maximal(u) if u else None
        if whole_name and q is not None and q != u:
            q = None                             # part count-whole-name: a longer name is not its shorter sequence
        if q is not None and show(q) in by_base and cl[rename.get(q, q)].supported:
            key_map[r.key] = by_base[show(q)]
            stats["secondary_own"] += 1
            continue
        pq = rec_cluster.get(r.rid)
        if pq is not None:
            key_map[r.key] = cl[rename.get(pq, pq)].key
            stats["secondary_record"] += 1
        # else: no name (a lone unbound fragment): the key stays unmapped (the build keeps it as it is)
    for r in records:
        if r.orig and r.key in key_map:
            key_map.setdefault(r.orig, key_map[r.key])

    families, nested = _roots(cl, vocab, named, brand_marks, bind_end, attr_root)
    ranges = _ranges({g: m for g, m in (official_groups or {}).items()
                      if any(v is None for v in vocab.tag(tuple(g.split())).var)}, families, key_map)
    for f in nested:
        unclear.append({"kind": "family_in_family", "root": f.root, "parent": f.parent, "members": f.members})
    stats["clusters"] = len(cl)
    stats["supported"] = sum(c.supported for c in cl.values())
    stats["records"] = len({r.rid for r in prim})
    no_name = {r.key for r in prim if not U[r.key][0]} - set(key_map)
    return BrandCount(brand, {c.key: c for c in cl.values()}, key_map, families, nested, ranges, binds, dropped,
                      unclear, stats, no_name)


def _roots(cl: dict[tuple[str, ...], Cluster], vocab: CountVocab, named: dict, brand_marks: set[str] = frozenset(),
           bind_end: bool = False, attr_root: bool = False) -> tuple[list[FamilyRoot], list[FamilyRoot]]:
    """N9 over the supported clusters' BASE names (variant tokens out), the leading sequence only (Harry A54). Never a
    root: a word of a class in counting.root_veto_effects (concentration, audience, intensity, type ... words alone), a
    generic root (generic-roots.yaml) unless an OFFICIAL name equals it, a brand mark, a root ending on a bind word
    (particle, connector). A ONE-WORD root (one word that is no fragment and no bind word: "Only", "Leau", "Musk") needs a
    signal besides its 2+ names: it is itself a sold product (a listing names it), or an official / catalog name."""
    named_s = {show(q) for q in named}
    official_s = {show(q) for q, src in named.items() if "official" in src}
    sold = {show(c.units) for c in cl.values() if c.supported and c.sources.get("listing")}
    toks_of: dict[str, tuple[str, ...]] = {}
    ends: dict[str, set[int]] = {}               # prefix lengths (in tokens) a root may end at
    supported = {c.key for c in cl.values() if c.supported}
    for c in cl.values():
        if not c.supported:                      # a sold name under the floor is a member only when its last word is a
            last = vocab.tag(tuple(c.units[-1].split())) if c.units else None     # member word (G5 MEMBER-WORD: a colour,
            if not (c.sources.get("listing") and last is not None and last.memb and last.memb[-1]):   # a note):
                continue                         # Goodness Oud Black / Blanc / Rouge; never a retail tail ("9 PM Luxury")
        toks: list[str] = []
        ok: set[int] = set()
        for unit in c.units:
            parts = unit.split()
            for k, t in enumerate(parts):
                toks.append(t)
                # a root may end inside a bound unit only after a whole word (Supremacy | In Heaven), never after a
                # fragment cut from its partner (9 | PM)
                if k == len(parts) - 1 or not vocab.tag((t,)).frag[0]:
                    ok.add(len(toks))
        toks_of[c.key] = tuple(toks)
        ends[c.key] = ok
    by_prefix: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for key, u in toks_of.items():
        for k in sorted(ends[key]):
            by_prefix[u[:k]].add(key)
    cand: dict[frozenset[str], tuple[str, ...]] = {}
    for r, mem in by_prefix.items():
        if len({toks_of[m] for m in mem}) < 2 or not (mem & supported):
            continue
        fs = frozenset(mem)
        if fs not in cand or len(r) > len(cand[fs]):
            cand[fs] = r
    out: list[FamilyRoot] = []
    for fs, r in cand.items():
        rs = show(r)
        off = rs in named_s
        lt = vocab.tag(r)
        words = [i for i in range(len(r)) if not lt.frag[i] and not lt.bind[i]]
        lone_frag = not words and not off
        ends_bind = lt.bind[-1]                                       # never a family on "Art Of", "Club De"
        vetoed = bool(words) and all(lt.veto[i] for i in words) and rs not in official_s   # "Le Parfum", "Intense", "Men"; an official range name stays (Q7)
        generic = len(words) == 1 and (r[words[0]] in vocab.generic or lt.desc[words[0]]) and rs not in official_s
        brandy = "".join(ch for ch in "".join(r).casefold() if ch.isalnum()) in brand_marks
        one_word_unsignalled = len(words) <= 1 and not (off or rs in sold)
        if attr_root and lt.attr and all(a or b for a, b in zip(lt.attr, lt.bind, strict=True)) and not all(lt.bind)                 and "official" not in named.get(r, ()):
            continue                                   # attribute words only name no family (E18: Signature, Series)
        if lone_frag or ends_bind or vetoed or generic or brandy or one_word_unsignalled:
            continue
        out.append(FamilyRoot(rs, sorted(fs), off))
    out.sort(key=lambda f: (-len(f.members), f.root))
    top: list[FamilyRoot] = []
    nested: list[FamilyRoot] = []
    for f in sorted(out, key=lambda f: (len(f.root), f.root)):
        par = [g for g in top if set(f.members) < set(g.members) and f.root.startswith(g.root + " ")]
        if par:
            f.parent = max(par, key=lambda g: len(g.root)).root
            nested.append(f)
        else:
            top.append(f)
    top.sort(key=lambda f: f.root)
    nested.sort(key=lambda f: f.root)
    return top, nested


def _ranges(groups: dict[str, set[str]], families: list[FamilyRoot], key_map: dict[str, str]) -> list[RangeParent]:
    """Harry A2: an official range whose members fall in 2+ counted families (and no other family) is their parent."""
    out = []
    fam_of: dict[str, set[str]] = defaultdict(set)
    for f in families:
        for m in f.members:
            fam_of[m].add(f.root)
    roots = {f.root for f in families}
    for name, members in sorted(groups.items()):
        hit: set[str] = set()
        stray = 0
        for k in members:
            ck = key_map.get(k, k)
            got = fam_of.get(ck, set()) | ({ck} & roots)
            hit |= got
            stray += not got
        if len(hit) >= 2 and name not in hit and not stray:
            out.append(RangeParent(name, sorted(hit)))
    return out


def counts_block(bc: BrandCount, limit: int = 60) -> str:
    """The AGENT-CARD §2 counts block of the brand (clusters by size; families; unclear cases)."""
    fam_of = {m: f.root for f in bc.families for m in f.members}
    lines = [f"brand {bc.brand}: {bc.stats['records']} name records, {len(bc.clusters)} clusters, "
             f"{len(bc.families)} families"]
    for c in sorted(bc.clusters.values(), key=lambda c: (-c.n, c.key))[:limit]:
        lines.append(f'cluster "{c.key}"  n={c.n}  fam={len(c.families)}  official={c.official}'
                     + ("" if c.supported else "  UNDER FLOOR"))
        if c.key in fam_of:
            lines.append(f'  in family: "{fam_of[c.key]}"')
        vs = "   ".join(f"{ax} {{{', '.join(f'{v}: {k}' for v, k in sorted(cnt.items(), key=lambda kv: -kv[1]))}, "
                       f"none: {c.n - sum(cnt.values())}}}" for ax, cnt in sorted(c.variants.items()) if cnt)
        if vs:
            lines.append("  " + vs)
    for f in bc.families:
        lines.append(f'family root "{f.root}" ({len(f.members)} products): {", ".join(f.members)}')
    for f in bc.nested:
        lines.append(f'nested root "{f.root}" in "{f.parent}" ({len(f.members)} products)')
    for r in bc.ranges:
        lines.append(f'official range "{r.name}" over families {", ".join(r.families)}')
    for f, (side, w, k, n) in sorted(bc.binds.items()):
        lines.append(f'fragment: "{f}" bound to "{w}" in {k}/{n}')
    for u in bc.unclear:
        if u["kind"] == "variant_band":
            lines.append(f'unclear: "{u["value"]}" on {round(100 * u["share"])}% of "{u["cluster"]}" ({u["k"]}/{u["n"]})')
        elif u["kind"] == "fragment_band":
            lines.append(f'unclear: fragment "{u["fragment"]}" next to "{u["word"]}" in {u["k"]}/{u["n"]}')
        elif u["kind"] == "official_differs":
            lines.append(f'unclear: official "{u["official"]}" vs count "{u["cluster"]}"')
        elif u["kind"] == "family_in_family":
            lines.append(f'unclear: family "{u["root"]}" inside "{u["parent"]}"')
    return "\n".join(lines)
