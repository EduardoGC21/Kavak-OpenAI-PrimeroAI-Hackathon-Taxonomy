"""The pieces load and fit together. No model calls; data tests skip when TAXO_DATA_DIR is not reachable."""
import os
from pathlib import Path

import pytest

from taxo import memory
from taxo.core import domain, rules
from taxo.core.metrics import score
from taxo.core.schemas import Decision, Listing, Node, RuleSpec
from taxo.roles import curator
from taxo.roles.judge import make_judge
from taxo.roles.placer import make_placer
from taxo.roles.proposer import make_proposer


def test_count_rules_fire():
    rs = [r.model_copy(update={"status": "admitted"}) for r in memory.all_rules()]
    node = Node(id="n", domain="t", name="Set of 4", path=["Acme", "Brake pads", "Set of 4"])
    tax = {"n": node}
    pair = Listing(id="a", domain="t", title="Acme brake pads pack of 2")
    silent = Listing(id="b", domain="t", title="Acme brake pads")
    assert rules.run_rules(rs, pair, node, tax).vetoed
    assert rules.run_rules(rs, silent, node, tax).abstain
    assert not rules.run_rules(memory.all_rules(), pair, node, tax).decided  # proposals never decide


def test_ported_checks():
    from taxo.tools import checks
    assert checks.pack_count("Coca-Cola 12 x 330ml cans") == 12
    assert checks.pack_count("Balatas delanteras juego de 4") == 4
    edt = Node(id="e", domain="f", name="Yara EDT", path=["Lattafa", "Yara", "Yara EDT"])
    assert checks.run("concentration_conflict", Listing(id="x", domain="f", title="Lattafa Yara EDP 100ml"), edt, {"e": edt})


def test_universal_rules_reach_every_domain():
    for d in domain.DOMAINS:
        assert {r.id for r in memory.rules_for(d)} >= {"count_agree", "count_omission"}


def test_metrics():
    s = score({"a": "accept", "b": "reject", "c": "abstain"}, {"a": False, "b": True, "c": True})
    assert (s.false_accepts, s.false_rejects, s.to_human) == (1, 1, 1)


def test_curator_needs_a_real_check(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    r = RuleSpec(id="x", check="count_agree", decision="veto")
    assert not curator.admit(r, "cars", caught=50, false_rejects=1, planted_fault_fires=True, known_good_quiet=False)
    assert curator.admit(r, "cars", caught=50, false_rejects=1, planted_fault_fires=True, known_good_quiet=True)
    assert not curator.promotable("x")
    curator.admit(r, "food", caught=10, false_rejects=0, planted_fault_fires=True, known_good_quiet=True)
    assert curator.promotable("x")


@pytest.mark.parametrize("name", domain.DOMAINS)
def test_agents_build_for_every_domain(name):
    d = domain.load(name)
    assert make_placer(name, d.pack.get("conventions", "")).name == f"placer-{name}"
    assert make_judge(name, strong=True).name.startswith("judge-strong")
    assert make_proposer(name).output_type is not None


data = os.environ.get("TAXO_DATA_DIR")


@pytest.mark.skipif(not (data and Path(data).exists()), reason="TAXO_DATA_DIR not reachable")
@pytest.mark.parametrize("name", domain.DOMAINS)
def test_adapters_load(name):
    d = domain.load(name)
    ls = list(d.listings(limit=50))
    assert ls and all(l.title for l in ls)
    nodes = d.nodes()
    if name != "car_parts":
        assert nodes and any(n.children for n in nodes)
