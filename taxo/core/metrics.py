"""Scoring against human labels. Only code calls this; agents never get the labels."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Score:
    n: int
    false_accepts: int   # system accepted, human said wrong
    false_rejects: int   # system rejected, human said right
    to_human: int        # abstained / escalated

    @property
    def far(self) -> float:
        return self.false_accepts / self.n if self.n else 0.0

    @property
    def frr(self) -> float:
        return self.false_rejects / self.n if self.n else 0.0

    @property
    def human_share(self) -> float:
        return self.to_human / self.n if self.n else 0.0


def score(decisions: dict[str, str], truth: dict[str, bool]) -> Score:
    """decisions: listing_id -> accept|reject|abstain; truth: listing_id -> placement is correct."""
    ids = [i for i in decisions if i in truth]
    fa = sum(decisions[i] == "accept" and not truth[i] for i in ids)
    fr = sum(decisions[i] == "reject" and truth[i] for i in ids)
    hu = sum(decisions[i] == "abstain" for i in ids)
    return Score(len(ids), fa, fr, hu)
