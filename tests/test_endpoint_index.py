"""Clinical index regressions use stub models, never claim real-source/E2E acceptance."""
import json
from copy import deepcopy
from unittest.mock import Mock

import pytest

from ciw.config import ConceptCfg
from ciw.models import Locator, OutcomeResult
from ciw.normalize.semantics import classify
from ciw.verify.endpoint_index import _catalog, enrich_endpoint_index
from ciw.verify.llm import FakeBackend

TITLE = "Percentage of Participants With Peak Esophageal Intraepithelial Eosinophil Count of ≤6 eos/hpf"


def result(title=TITLE, definition="Histologic response is ≤6 eos/hpf.", identity="r1"):
    return OutcomeResult(result_id=identity, trial_id="NCT00000001", outcome_index=0, type="PRIMARY",
        title=title, description=definition, domain="pd", measure_kind="proportion", unit="Percentage of participants",
        locator=Locator(source_id="unit-source", quote=title))


def roles_for(cfg, rows, *, omit=False, wrong_quote=False, domain="efficacy", label="组织学应答"):
    descriptors = _catalog(cfg, rows)
    items = [dict(descriptor_id=key, title=value["title"], label=label, domain=domain,
                  direction="higher_better", quote="unrelated invented quotation" if wrong_quote else value["title"])
             for key, value in descriptors.items()]
    if omit:
        items = []
    output = json.dumps(dict(items=items))
    return {"extractor_a": FakeBackend("deepseek", "source-extractor", Mock(return_value=output)),
            "verifier": FakeBackend("glm", "source-checker", Mock(return_value=output))}


def test_explicit_clinical_tissue_endpoint_is_not_forced_into_pd(cfg):
    cfg = cfg.model_copy(deep=True)
    cfg.concepts.append(ConceptCfg(id="clinical-tissue", label="组织学应答", patterns=["^" + TITLE + "$"],
                                  source_definition="Histologic response is ≤6 eos/hpf."))
    assert classify(TITLE, cfg, "Histologic response is ≤6 eos/hpf.") == ("efficacy", "clinical-tissue")
    assert classify(TITLE, cfg, "Different definition") == ("pd", None)
    assert classify("Change From Baseline in Blood Eosinophil Count", cfg) == ("pd", None)
    assert classify("Number of Participants With Anti-Drug Antibodies", cfg)[0] == "immunogenicity"
    assert classify("Serum Concentration of Drug X", cfg)[0] == "pk"


def test_source_index_fills_literal_miss_without_changing_numeric_or_original_context(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result()]
    before = rows[0].model_dump()
    roles = roles_for(cfg, rows)
    assert enrich_endpoint_index(ws, cfg, rows, roles) == []
    after = rows[0].model_dump()
    assert after["domain"] == "efficacy" and after["concept_id"].startswith("source-endpoint-")
    for key in before.keys() - {"domain", "concept_id"}:
        assert after[key] == before[key]
    assert roles["extractor_a"].responder.call_count == roles["verifier"].responder.call_count == 1


def test_same_title_different_threshold_definitions_do_not_share_a_mapping(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result("Histologic response", "Response is <6 eos/hpf.", "less"),
            result("Histologic response", "Response is ≤6 eos/hpf.", "less-equal")]
    roles = roles_for(cfg, rows)
    assert enrich_endpoint_index(ws, cfg, rows, roles) == []
    assert rows[0].concept_id != rows[1].concept_id
    assert classify("Histologic response", cfg, "Response is ≤6 eos/hpf.")[1] == rows[1].concept_id
    assert classify("Histologic response", cfg, "New unresolved definition") == ("other", None)


def test_many_observations_reuse_one_descriptor_and_c_can_apply_checked_index_without_calls(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result(identity=f"r{i}") for i in range(50)]
    roles = roles_for(cfg, rows)
    enrich_endpoint_index(ws, cfg, rows, roles)
    assert roles["extractor_a"].responder.call_count == roles["verifier"].responder.call_count == 1
    fresh_cfg = deepcopy(cfg)
    fresh_cfg.concepts = [c for c in fresh_cfg.concepts if not c.id.startswith("source-endpoint-")]
    fresh = [result(identity="current-source-result")]
    assert enrich_endpoint_index(ws, fresh_cfg, fresh, roles=None) == []
    assert fresh[0].domain == "efficacy" and fresh[0].concept_id == rows[0].concept_id


@pytest.mark.parametrize("mode", ["omit", "wrong_quote", "pd"])
def test_unconfirmed_or_nonclinical_mapping_does_not_create_efficacy(cfg, ws, mode):
    cfg = cfg.model_copy(deep=True)
    rows = [result()]
    roles = roles_for(cfg, rows, omit=mode == "omit", wrong_quote=mode == "wrong_quote",
                      domain="pd" if mode == "pd" else "efficacy")
    issues = enrich_endpoint_index(ws, cfg, rows, roles)
    assert rows[0].domain == "pd" and rows[0].concept_id is None
    if mode != "pd":
        assert issues


def test_call_failure_is_a_parse_issue_not_no_efficacy_data(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result()]
    roles = roles_for(cfg, rows)
    roles["extractor_a"].responder = lambda *_: "invalid output"
    issues = enrich_endpoint_index(ws, cfg, rows, roles)
    assert issues[0]["kind"] == "endpoint_index_failed"
    assert rows[0].domain == "pd"


def test_committed_clinical_mapping_survives_later_report_without_index_stage(cfg, seeded_ws):
    import re

    from ciw.pipeline import run
    from ciw.release import load_release

    base = cfg.model_copy(deep=True)
    initial = run(base, seeded_ws, offline=True, log=lambda *_: None)
    row = next(r for r in load_release(initial.release_path)["results"] if r["concept_id"] == "nps")
    base.concepts = [c for c in base.concepts if c.id != "nps"]
    clinical = ConceptCfg(id="source-endpoint-unit-proof", label="来源定义的NPS",
                          patterns=["^" + re.escape(row["title"]) + "$"],
                          source_definition=row["description"])
    first_cfg = base.model_copy(deep=True)
    first_cfg.concepts.append(clinical)
    first = run(first_cfg, seeded_ws, offline=True, report_scope="B", render_reports=["B"], log=lambda *_: None)
    assert any(c["id"] == clinical.id for c in load_release(first.release_path)["clinical_concepts"])
    assert seeded_ws.read_stage("research-endpoint-index") is None
    later = run(base, seeded_ws, offline=True, report_scope="C", render_reports=["B", "C"], log=lambda *_: None)
    loaded = load_release(later.release_path)
    current = next(r for r in loaded["results"] if r["result_id"] == row["result_id"])
    assert current["concept_id"] == clinical.id and current["domain"] == "efficacy"
    assert any(q["concept_id"] == clinical.id for q in loaded["b"]["questions"])


@pytest.mark.parametrize("label,accepted", [("组织学≤6", True), ("组织学<6", False), ("组织学≤7", False)])
def test_model_generated_labels_cannot_invent_a_threshold_or_change_its_operator(cfg, ws, label, accepted):
    cfg = cfg.model_copy(deep=True)
    rows = [result()]
    issues = enrich_endpoint_index(ws, cfg, rows, roles_for(cfg, rows, label=label))
    assert (rows[0].domain == "efficacy") is accepted
    assert bool(issues) is not accepted


def test_continuous_biomarker_change_cannot_be_labeled_remission_by_model_agreement(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    row = result("Mean Change From Baseline in Peak Esophageal Eosinophil Counts",
                 "Measured peak eosinophil counts before and after treatment.")
    row.measure_kind = "mean"
    issues = enrich_endpoint_index(ws, cfg, [row], roles_for(cfg, [row], label="组织学缓解"))
    assert row.domain == "pd" and row.concept_id is None
    assert issues


def test_omitted_threshold_operator_is_rejected(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result()]
    issues = enrich_endpoint_index(ws, cfg, rows, roles_for(cfg, rows, label="组织学应答 6 eos/hpf"))
    assert rows[0].domain == "pd" and issues


def test_unattempted_index_is_recorded_without_calling_a_model(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result("Change in Dysphagia Symptom Score", "A patient-reported symptom questionnaire.")]
    rows[0].domain = "other"
    issues = enrich_endpoint_index(ws, cfg, rows, roles=None)
    assert any(i["kind"] == "endpoint_index_not_run" for i in issues)
    assert rows[0].domain == "other"


def test_a_pre_retrieval_generic_concept_does_not_preempt_a_checked_source_definition(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    # Runtime search plans may carry broad terms; they are not evidence of complete indexing.
    generic = ConceptCfg(id="search-plan", label="组织学（阈值未明确）", patterns=["Histologic response"])
    generic.provisional = True
    cfg.concepts.append(generic)
    rows = [result("Histologic response", "Histologic remission means ≤6 eos/hpf.")]
    rows[0].domain, rows[0].concept_id = classify(rows[0].title, cfg, rows[0].description)
    roles = roles_for(cfg, rows, label="组织学缓解≤6")
    for role in roles.values():
        payload = json.loads(role.responder.return_value)
        payload["items"][0]["quote"] = rows[0].description
        role.responder.return_value = json.dumps(payload)
    assert enrich_endpoint_index(ws, cfg, rows, roles) == []
    assert rows[0].concept_id != generic.id
    assert classify(rows[0].title, cfg, rows[0].description)[1] == rows[0].concept_id


def test_a_separate_remission_sentence_cannot_relabel_a_continuous_measure(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result("Mean Change From Baseline in Peak Esophageal Eosinophil Counts",
                   "Measured mean counts. Histologic remission is defined as ≤6 eos/hpf.")]
    roles = roles_for(cfg, rows, label="组织学缓解≤6")
    for role in roles.values():
        payload = json.loads(role.responder.return_value)
        payload["items"][0]["quote"] = rows[0].description
        role.responder.return_value = json.dumps(payload)
    issues = enrich_endpoint_index(ws, cfg, rows, roles)
    assert rows[0].domain == "pd" and issues


def test_current_manual_dictionary_wins_over_an_adopted_source_mapping(cfg, ws):
    cfg = cfg.model_copy(deep=True)
    rows = [result()]
    enrich_endpoint_index(ws, cfg, rows, roles_for(cfg, rows))
    derived = next(c for c in cfg.concepts if c.id == rows[0].concept_id)
    assert derived.origin == "source_index"
    manual = ConceptCfg(id="current-manual", label="用户当前核实的组织学定义", patterns=["Eosinophil Count"])
    cfg.concepts.append(manual)
    assert classify(rows[0].title, cfg, rows[0].description)[1] == manual.id
