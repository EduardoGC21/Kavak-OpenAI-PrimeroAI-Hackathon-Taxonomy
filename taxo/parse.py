"""Steps 1 and 2 of SPEC §4: parse a title, then find its brand. Free, deterministic, no word lists beyond vocab.yaml
and the brand names of the domain.

    parse(title, vocab)          -> Parsed: tokens, the name head, the maker after "by", variant values per axis
    Brands(names).find(...)      -> (brand slug, how) by the ladder: field, title_by, title_lead, maker field, title_any
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from taxo.lattice.count import CountVocab
from taxo.lattice.vocab import tokens

# the name sits before the first of these; what follows is size, notes and marketing
_CUT = re.compile(r"\s[-–—|]\s|[,(\[{|:;]|\s-\s?")
_BRACKET = re.compile(r"\s*\[[^\]]*\]\s*$")
_BY = re.compile(r"\bby\s+", re.I)


@dataclass
class Parsed:
    title: str
    toks: tuple[str, ...]                       # the whole title
    head: tuple[str, ...]                       # the name part: before the first separator, before "by <maker>"
    by: tuple[str, ...] = ()                    # the words after "by" (the maker, for the brand step)
    variants: dict[str, str] = field(default_factory=dict)   # axis -> first value seen in the whole title


def parse(title: str, vocab: CountVocab | None = None) -> Parsed:
    t = _BRACKET.sub("", title or "")
    head_text = _CUT.split(t, maxsplit=1)[0]
    by: tuple[str, ...] = ()
    m = _BY.search(t)
    if m:
        by = tokens(t[m.end():])[:4]
        if m.start() < len(head_text):
            before = head_text[:m.start()]
            # "Asad by Lattafa" -> Asad; "By Kilian Love" -> the name follows the maker
            head_text = before if tokens(before) else head_text[m.end():]
    toks = tokens(t)
    head = tokens(head_text) or toks
    variants: dict[str, str] = {}
    if vocab is not None:
        tg = vocab.tag(toks)
        for v in tg.var:
            if v is not None:
                variants.setdefault(v[0], v[1])
    return Parsed(title=title, toks=toks, head=head, by=by, variants=variants)


def strip_seq(toks: tuple[str, ...], seqs: list[tuple[str, ...]]) -> tuple[str, ...]:
    """Remove every occurrence of the given token runs (longest first)."""
    out: list[str] = []
    i = 0
    seqs = sorted((s for s in seqs if s), key=len, reverse=True)
    while i < len(toks):
        for s in seqs:
            if toks[i:i + len(s)] == s:
                i += len(s)
                break
        else:
            out.append(toks[i])
            i += 1
    return tuple(out)


class Brands:
    """The domain's known brands: slug -> display name, and the token runs that name each one."""

    def __init__(self, names: dict[str, str], suffixes: tuple[str, ...] | None = None):
        if suffixes is None:  # Legacy baseline callers; new domains pass their own configuration explicitly.
            from taxo.core.domain import load
            suffixes = tuple(load("fragrance").pack.get("construction", {}).get("brand_suffixes", []))
        self.names = names
        self.alias: dict[tuple[str, ...], str] = {}
        for slug, name in names.items():
            for base in {tokens(name), tuple(slug.split("_"))}:
                if not base:
                    continue
                self.alias.setdefault(base, slug)
                for s in suffixes:
                    self.alias.setdefault(base + (s,), slug)
        self._by_len = sorted(self.alias, key=len, reverse=True)

    def runs(self, slug: str) -> list[tuple[str, ...]]:
        return [a for a, s in self.alias.items() if s == slug]

    def lead(self, toks: tuple[str, ...]) -> str | None:
        for a in self._by_len:
            if toks[:len(a)] == a:
                return self.alias[a]
        return None

    def exact(self, text: str | None) -> str | None:
        t = tokens(text)
        return self.alias.get(t) if t else None

    def anywhere(self, toks: tuple[str, ...]) -> str | None:
        hits = {self.alias[a] for a in self._by_len if any(toks[i:i + len(a)] == a for i in range(len(toks)))}
        return hits.pop() if len(hits) == 1 else None

    def find(self, p: Parsed, brand_field: str | None = None, maker_field: str | None = None) -> tuple[str | None, str]:
        """The brand ladder (Pedia ladder.py, trimmed): the first rung that names exactly one known brand wins."""
        rungs = (("brand_field", lambda: self.exact(brand_field) or self.lead(tokens(brand_field))),
                 ("title_by", lambda: self.lead(p.by)),
                 ("title_lead", lambda: self.lead(p.toks)),
                 ("maker_field", lambda: self.exact(maker_field) or self.lead(tokens(maker_field))),
                 ("title_any", lambda: self.anywhere(p.toks)))
        for how, rung in rungs:
            s = rung()
            if s:
                return s, how
        return None, "none"
