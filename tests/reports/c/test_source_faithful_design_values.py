"""A source clause cannot turn background therapy, placebo or a vial into a drug dose."""

from pathlib import Path

import pytest

from ci_workflow.application.ctgov_c_design_projection import project_ctgov_c_design_observations
from ci_workflow.application.ctgov_design_atoms import extract_ctgov_protocol_design_atoms
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _chart_row,
    _table_rows,
    _value_text,
)
from tests.integration.test_r24_ctgov_c_design_projection import _full_bindings, _mutated_capture


@pytest.fixture(scope="module")
def report():
    return ReportCPortalData.model_validate_json(Path(
        "fixtures/acceptance/full-matrix-v1/inputs/report-c-data.json"
    ).read_bytes())


@pytest.mark.parametrize(("field", "source"), [
    ("experimental_arm", "Drug: Moisturizers"),
    ("control_arm", "Drug: Low to medium potent topical corticosteroids"),
    ("experimental_arm", "Drug: Topical calcineurin inhibitors"),
    ("experimental_arm", "Drug: Nemolizumab 30 mg"),
    ("control_arm", "Placebo matched to the active injection"),
    ("dosing_regimen", "Placebo matched to dupilumab 600 mg on Day 1 followed by "
     "placebo matched to dupilumab 300 mg q2w added to background TCS/TCI."),
    ("dosing_regimen", "Participants <90 kg received 60 mg loading then 30 mg Q4W; "
     "participants >=90 kg received 60 mg with no loading dose, then 60 mg Q4W."),
    ("dosing_regimen", "Two matching placebo injections at baseline, then one Q4W; "
     "two Q4W injections for participants >=90 kg for 16 weeks."),
    ("primary_endpoint_definition", "Percentage of Participants With >=4-point Improvement "
     "in Worst Itch Numeric Rating Scale (WI-NRS) at Week 24"),
    ("secondary_endpoint_definition", "Kaplan-Meier Probability of >=4-point Improvement "
     "in WI-NRS at Week 24"),
    ("secondary_endpoint_definition", "IGA PN-S Score of 0 or 1 at Week 24"),
    ("secondary_endpoint_definition", "IGA PN-A Score of 0 or 1 at Week 24"),
    ("primary_endpoint_definition", "Number of Participants With IGA Success at Week 16"),
    ("secondary_endpoint_definition", "Number of Participants With PP NRS <2 at Week 4"),
    ("secondary_endpoint_definition", "Hemoglobin change >=2 g/dL without transfusion by Week 26"),
])
def test_all_value_consumers_keep_the_full_untranslated_source(report, field, source):
    observation = report.observations[0].model_copy(update={
        "field": field, "source_text": source, "display_text": None,
        "scale": None, "threshold_value": None, "threshold_unit": None, "operator": None,
    })
    before = observation.model_dump_json()
    assert _value_text(report, observation) == source
    chart = _chart_row(report, observation, chart_type="status_matrix")
    assert chart["value"] == source
    table = _table_rows(report, (observation,), page_id="trial-detail")
    assert all(source in row["value"] for row in table)
    assert observation.model_dump_json() == before


def test_explicit_source_bound_display_text_is_not_replaced_by_product_guess(report):
    observation = report.observations[0].model_copy(update={
        "field": "control_arm", "source_text": "Placebo matching active injection",
        "display_text": "与活性注射剂匹配的安慰剂",
    })
    assert _value_text(report, observation) == "与活性注射剂匹配的安慰剂"


@pytest.mark.parametrize("feature", ["maximum_age", "non_mass_regimen"])
def test_maximum_age_and_non_mass_placebo_regimen_reach_the_design_projection(feature):
    def mutate(record):
        protocol = record["protocolSection"]
        protocol["eligibilityModule"]["maximumAge"] = "80 Years"
        protocol["armsInterventionsModule"]["armGroups"][0]["description"] = (
            "Two matching placebo injections at baseline, then one injection Q4W for 16 weeks."
        )

    source = _mutated_capture("NCT03829449", mutate)
    atoms = extract_ctgov_protocol_design_atoms(source)
    projection = project_ctgov_c_design_observations(
        (atoms,), captures={source.source_id: source},
        bindings=(_full_bindings()[1],), indication_id="pnh",
    )
    if feature == "maximum_age":
        upper = [row for row in projection.observations if row.source_field_name == "maximumAge"]
        assert len(upper) == 1
        assert (upper[0].operator, upper[0].threshold_value, upper[0].threshold_unit) == (
            "≤", "80", "岁"
        )
        return
    regimen = [row for row in projection.observations
               if row.field == "dosing_regimen" and "matching placebo" in row.source_text]
    assert len(regimen) == 1
    assert regimen[0].source_locator.field_path.endswith("armGroups[0].description")
    assert "Q4W" in regimen[0].source_text
    assert not any(atom.reason.value == "arm_description_without_explicit_dose"
                   and atom.path.endswith("armGroups[0].description")
                   for atom in projection.unresolved_atoms)
