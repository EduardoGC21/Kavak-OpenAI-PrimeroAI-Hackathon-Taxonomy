"""Proposer agent: turns a cluster of system-vs-human disagreements into ONE candidate rule.
The candidate is not used until the curator admits it on dev labels."""
from __future__ import annotations

from agents import Agent
from pydantic import BaseModel, Field

from taxo.core import config
from taxo.core.rules import EXTRACTORS, OPERATORS
from taxo.core.schemas import Decision, Scope


class RuleProposal(BaseModel):
    id: str = Field(description="snake_case name")
    description: str
    scope: Scope = Field(description="universal only if nothing in it is specific to this domain")
    operator: str
    extractor: str
    policy: Decision
    params_json: str = Field(default="{}", description="operator params as a JSON object string")
    rationale: str = Field(description="which disagreements it explains, and what it would wrongly reject")


INSTRUCTIONS = """You read a cluster of cases where the system's placement and a person's label disagree in the
{domain} domain, and propose ONE rule that would have caught them.
A rule = operator x extractor x policy. Known operators: {operators}. Known extractors: {extractors}.
Prefer an existing operator; say so in the rationale if a new extractor is needed.
Prefer abstain over reject when the evidence is an omission. Never propose a rule that only re-checks the
system's own output (an echo check)."""


def make_proposer(domain: str) -> Agent:
    return Agent(
        name=f"proposer-{domain}",
        instructions=INSTRUCTIONS.format(domain=domain, operators=sorted(OPERATORS), extractors=sorted(EXTRACTORS)),
        model=config.model("proposer"),
        output_type=RuleProposal,
    )
