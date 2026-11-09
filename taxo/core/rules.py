"""Rule engine: runs a domain's deterministic rules (checks ported from pedia-harness, taxo/tools/checks.py) on a
(listing, candidate node) pair.

Only ADMITTED rules decide. SHADOW rules run and are logged with what they would have done. PROPOSAL and RETIRED
rules never run. A veto removes the candidate (the agent cannot override); an abstain blocks an auto-accept.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from taxo.core.schemas import Listing, Node, RuleSpec, Status
from taxo.tools import checks
from taxo.tools.checks import Finding


@dataclass
class RuleRun:
    decided: list[Finding] = field(default_factory=list)  # from admitted rules
    shadow: list[Finding] = field(default_factory=list)   # what shadow rules would have done

    @property
    def vetoed(self) -> bool:
        return any(f.decision == "veto" for f in self.decided)

    @property
    def abstain(self) -> bool:
        return any(f.decision == "abstain" for f in self.decided)


def run_rules(rules: list[RuleSpec], listing: Listing, node: Node, tax: dict[str, Node]) -> RuleRun:
    out = RuleRun()
    for r in rules:
        if r.status not in (Status.ADMITTED, Status.SHADOW):
            continue
        f = checks.run(r.check, listing, node, tax, r.decision, **r.params)
        if f is None:
            continue
        f.check = r.id
        (out.decided if r.status == Status.ADMITTED else out.shadow).append(f)
    return out
