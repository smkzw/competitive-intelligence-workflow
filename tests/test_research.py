import json

import pytest

from ciw.config import IndicationConfig
from ciw.research import QueryPlan, ResearchInputError, plan_query, registry_config, run_research
from ciw.store import Workspace
from ciw.verify.llm import FakeBackend


def plan(**changes):
    return dict(name_en="Example disease", name_zh="示例疾病", conditions=["Example disease"],
                concepts=[dict(label="应答75", terms=["Response (75%)"], direction="higher_better")], **changes)


def study(ws, name="Drug-A", kind="DRUG"):
    raw = {"protocolSection": {"armsInterventionsModule": {
        "interventions": [{"name": name, "type": kind}]}}}
    source = ws.record_source(kind="ctgov", url="https://clinicaltrials.gov/study/NCT00000001",
                             data=json.dumps(raw).encode(), ext="json")
    return source, raw


def test_registry_candidates_keep_scientific_unknowns_and_literal_concepts(tmp_path):
    ws = Workspace(tmp_path)
    item = study(ws)
    cfg, bindings = registry_config(QueryPlan.model_validate(plan()), {"one": item})
    drug = cfg.products[0]
    assert drug.innovative is None and drug.target == drug.name_zh == drug.company == ""
    assert bindings[drug.id][0]["source_id"] == item[0].source_id
    assert bindings[drug.id][0]["quote"] == "Drug-A"
    assert cfg.concepts[0].matches("Response (75%)")
    assert not cfg.concepts[0].matches("Response (90%)")
    assert IndicationConfig.model_validate(cfg.model_dump()).products[0].innovative is None


@pytest.mark.parametrize("name,kind,count", [("Placebo", "DRUG", 0), ("dummy", "DRUG", 0),
                                          ("Device", "DEVICE", 0), ("Drug-A", "BIOLOGICAL", 1)])
def test_registry_candidate_scope_does_not_invent_drug_identity(tmp_path, name, kind, count):
    ws = Workspace(tmp_path)
    cfg, _ = registry_config(QueryPlan.model_validate(plan()), {"one": study(ws, name, kind)})
    assert len(cfg.products) == count


def test_two_role_plan_is_not_a_scientific_fact_and_ambiguity_stops(tmp_path):
    ws = Workspace(tmp_path)
    roles = {"extractor_a": FakeBackend("deepseek", "a", lambda *_: json.dumps(plan())),
             "verifier": FakeBackend("glm", "b", lambda *_: json.dumps(plan(ambiguous=True)))}
    with pytest.raises(ResearchInputError, match="含义不明确"):
        plan_query("疾病", "", roles, ws)
    roles["verifier"].responder = lambda *_: json.dumps(plan())
    # FakeBackend has no network receipt, as also permitted by the Backend protocol.
    result = plan_query("疾病", "观察终点", roles, ws)
    assert result.name_en == "Example disease"
    assert "not facts" in ws.read_stage("research-query-plan")["purpose"]


def test_research_failure_keeps_persisted_state_and_old_current(tmp_path, monkeypatch):
    ws = Workspace(tmp_path)
    ws.set_current("rel_old")
    def fail(*args, **kwargs):
        raise ResearchInputError("请补充疾病全称")
    monkeypatch.setattr("ciw.research._research", fail)
    with pytest.raises(ResearchInputError):
        run_research("疾病", tmp_path, queue_lock=tmp_path / "queue.lock")
    assert ws.read_stage("research-run")["state"] == "failed"
    assert json.loads((ws.releases_dir / "current.json").read_text())["release_id"] == "rel_old"
