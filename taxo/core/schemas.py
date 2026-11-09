"""The shared types every domain and agent speaks. Agents return these (structured output); code writes files."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Listing(BaseModel):
    """One marketplace listing, as an adapter loads it."""
    id: str
    domain: str
    title: str
    source: str | None = None
    brand: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)  # price, year, km, fitment, raw extras


class Node(BaseModel):
    """One taxonomy node. `children` names the next level, so a rule can tell when a placement is too shallow."""
    id: str
    domain: str
    name: str
    parent_id: str | None = None
    level: str | None = None  # brand | line | model | variant | year | trim | ...
    path: list[str] = Field(default_factory=list)
    children: list[str] = Field(default_factory=list)
    fields: dict[str, Any] = Field(default_factory=dict)


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ABSTAIN = "abstain"  # not enough evidence: never a silent accept


class Placement(BaseModel):
    """A claim: this listing belongs at this node."""
    listing_id: str
    node_id: str | None
    path: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reason: str
    by: str  # rules | placer | judge_fast | judge_strong | human


class Verdict(BaseModel):
    """A ruling on a placement, from a rule, a judge or a person."""
    listing_id: str
    node_id: str | None
    decision: Decision
    reason: str
    by: str
    question: str | None = None  # for escalation: what a person (or stronger judge) must settle


class Scope(str, Enum):
    UNIVERSAL = "universal"
    FAMILY = "family"
    DOMAIN = "domain"


class Status(str, Enum):
    PROPOSAL = "proposal"  # written down, never run
    SHADOW = "shadow"      # runs and logs what it would do; decides nothing (until the domain's validator is frozen)
    ADMITTED = "admitted"  # passed the rule-set test on silver against the frozen validator
    RETIRED = "retired"


class RuleSpec(BaseModel):
    """A deterministic rule: one check from taxo/tools/checks.py, the decision it takes when it fires, its params.
    Checks transfer across domains; vocabularies and owner conventions do not."""
    id: str
    check: str  # name in taxo.tools.checks.CHECKS
    decision: str  # veto | abstain | info
    description: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    scope: Scope = Scope.DOMAIN
    status: Status = Status.PROPOSAL
    domains: list[str] = Field(default_factory=list)  # where it is enabled; empty = every domain at its scope
    origin: str = ""  # where it was learned (domain, pedia rule id, incident)
    evidence: str = ""


class AgenticRule(BaseModel):
    """An agentic rule: one instruction line in the Matcher's prompt."""
    id: str
    text: str
    status: Status = Status.PROPOSAL
    origin: str = ""
    evidence: str = ""
