"""Rule engine: extractors pull facts from text, operators compare listing vs node, the policy decides.

Stub: one extractor (count) and two operators (agree, omission) to show the shape. Add more as rules are ported.
"""
from __future__ import annotations

import re
from typing import Callable

from taxo.core.schemas import Decision, Listing, Node, RuleSpec, Verdict

# -- extractors: text -> value or None --------------------------------------
_COUNT = re.compile(r"\b(?:pack of|set of|x|paquete de|juego de)\s*(\d{1,3})\b|\b(\d{1,3})\s*(?:pk|pack|ct|count|piezas|pzs)\b",
                    re.I)


def extract_count(text: str) -> int | None:
    m = _COUNT.search(text or "")
    return int(m.group(1) or m.group(2)) if m else None


EXTRACTORS: dict[str, Callable[[str], object]] = {"count": extract_count}


# -- operators: (listing value, node value, params) -> fires? ----------------
def op_agree(a, b, params) -> bool:
    """Fires when both sides state a value and they disagree beyond tolerance."""
    if a is None or b is None:
        return False
    tol = params.get("tolerance", 0)
    return abs(a - b) > tol * max(abs(a), abs(b))


def op_omission(a, b, params) -> bool:
    """Fires when the node states a value the listing omits: unexamined, so abstain rather than accept."""
    return a is None and b is not None


OPERATORS = {"agree": op_agree, "omission": op_omission}


def apply(rule: RuleSpec, listing: Listing, node: Node) -> Verdict | None:
    """Run one rule on a proposed placement. None = the rule has nothing to say."""
    extract = EXTRACTORS[rule.extractor]
    a = extract(listing.title)
    b = extract(" ".join(node.path) or node.name)
    if OPERATORS[rule.operator](a, b, rule.params):
        return Verdict(listing_id=listing.id, node_id=node.id, decision=rule.policy,
                       reason=f"{rule.id}: listing {rule.extractor}={a!r} vs node {b!r}", by=f"rule:{rule.id}")
    return None


def apply_all(rules: list[RuleSpec], listing: Listing, node: Node) -> list[Verdict]:
    return [v for r in rules if (v := apply(r, listing, node)) is not None]


def combine(verdicts: list[Verdict]) -> Decision | None:
    """Reject beats abstain beats accept; no verdicts = rules are silent."""
    ds = {v.decision for v in verdicts}
    for d in (Decision.REJECT, Decision.ABSTAIN, Decision.ACCEPT):
        if d in ds:
            return d
    return None
