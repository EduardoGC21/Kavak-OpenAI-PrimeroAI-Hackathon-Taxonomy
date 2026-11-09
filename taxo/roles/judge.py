"""Judge agents: rule on a proposed placement. The fast judge runs first; the strong one only on doubt.
Stub: prompts and the escalation thresholds are to be tuned per domain on dev labels."""
from __future__ import annotations

from agents import Agent
from pydantic import BaseModel, Field

from taxo.core import config
from taxo.core.schemas import Decision


class JudgeOut(BaseModel):
    decision: Decision
    reason: str
    question: str | None = Field(default=None, description="if abstaining: the one question a person must settle")


INSTRUCTIONS = """You check whether a listing was placed on the right {domain} taxonomy node.
Accept only if every product-defining fact in the title (brand, product, variant, count, size, year, fitment)
agrees with the node path. Reject on any clear conflict. Abstain when the title omits a fact the node states,
or when it is a convention question, and write the one question a person must answer."""


def make_judge(domain: str, strong: bool = False) -> Agent:
    return Agent(
        name=f"judge-{'strong' if strong else 'fast'}-{domain}",
        instructions=INSTRUCTIONS.format(domain=domain),
        model=config.model("judge_strong" if strong else "judge_fast"),
        output_type=JudgeOut,
    )
