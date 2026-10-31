"""Registry intervention descriptions are distinct source fields, never invented arm descriptions."""
from copy import deepcopy

from ciw.extract.ctgov import extract_trial
from ciw.models import Source, Trial
from ciw.normalize.design import design_passages
from ciw.verify.design_clauses import _check


def source_trial(cfg, resolver):
    source = Source(source_id="synthetic", kind="ctgov", url="https://example.test/study",
                    fetched_at="2026-10-31", sha256="0" * 64)
    study = dict(protocolSection=dict(identificationModule=dict(nctId="synthetic"),
        conditionsModule=dict(conditions=[cfg.name_en]), armsInterventionsModule=dict(
            armGroups=[dict(label="Arm X", type="EXPERIMENTAL", description="Treatment for 1 year",
                            interventionNames=["Drug: Compound X"])],
            interventions=[dict(name="Compound X", type="DRUG", armGroupLabels=["Arm X"],
                                description="Compound X 500 mg twice daily"),
                           dict(name="Compound X", type="DRUG", armGroupLabels=["Unresolved arm"],
                                description="Compound X 250 mg once daily")])) )
    original = deepcopy(study)
    trial = extract_trial(study, source, cfg, resolver)
    assert study == original
    return trial


def test_all_intervention_descriptions_keep_explicit_relationships_and_exact_locators(cfg, resolver):
    trial = source_trial(cfg, resolver)
    assert [i.description for i in trial.interventions] == [
        "Compound X 500 mg twice daily", "Compound X 250 mg once daily"]
    assert [i.arm_group_labels for i in trial.interventions] == [["Arm X"], ["Unresolved arm"]]
    assert all(i.locator.source_id == trial.locator.source_id for i in trial.interventions)
    assert trial.interventions[1].locator.path == (
        "protocolSection.armsInterventionsModule.interventions[1].description")
    assert trial.arms[0].description == "Treatment for 1 year"
    assert len(trial.arms) == 1  # An unresolved source label does not manufacture another arm.


def test_model_source_check_consumes_each_literal_intervention_field_not_a_concatenated_arm(cfg, resolver):
    trial = source_trial(cfg, resolver)
    passages = design_passages(trial)
    field = "protocolSection.armsInterventionsModule.interventions[0].description"
    text = "Compound X 500 mg twice daily"
    assert [(value, key) for _, value, key in passages if key == field] == [(text, field)]
    item = dict(topic_id="dose", quote=text, clauses=[dict(field=field, text=text, quote=text,
                condition="", cohort_quote="", protocol_quote="", criterion_role="unspecified")])
    topics = dict(dose=dict(kind="dosing_regimen"))
    assert _check(item, topics, passages)[0]
    wrong = deepcopy(item)
    wrong["clauses"][0]["field"] = "protocolSection.armsInterventionsModule.interventions[1].description"
    assert not _check(wrong, topics, passages)[0]
    wrong = deepcopy(item)
    wrong["clauses"][0]["cohort_quote"] = "Arm X"
    assert not _check(wrong, topics, passages)[0]  # Metadata cannot become a quote in another field.


def test_legacy_trial_without_intervention_records_remains_readable_and_has_no_fake_source(cfg, resolver):
    raw = source_trial(cfg, resolver).model_dump()
    raw.pop("interventions", None)
    legacy = Trial.model_validate(raw)
    assert legacy.interventions == []
    assert not any("armsInterventionsModule.interventions[" in key for _, _, key in design_passages(legacy))
