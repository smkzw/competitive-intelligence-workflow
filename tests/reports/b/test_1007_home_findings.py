"""Home findings quote current observations, not generated medical conclusions."""

import copy

import pytest

from ci_workflow.renderers.portal import report_b
from tests.reports.b.test_1007_source_longitudinal_projection import _observations


def _workspace():
    records = _observations()
    for row, _ in records:
        row.update(unit="percentage of participants", product_zh="正式药名",
                   clinical_concept_label_zh="瘙痒NRS改善至少4分", value=20)
    records[1][0]["value"] = 0
    records[0][0]["value"] = 57.7
    groups = report_b._groups_for_page("efficacy", records)
    workspace = report_b._comparison_workspace(records, groups, ("trial-a",))
    return records, groups, workspace


def test_home_quotes_real_first_last_source_visits_without_recalculation():
    records, groups, workspace = _workspace()
    before = copy.deepcopy((records, groups, workspace))
    findings = report_b._overview_findings(workspace, groups)
    assert len(findings) == 1
    assert findings[0]["label"] == "瘙痒NRS改善至少4分"
    assert findings[0]["observation_count"] == 5
    assert findings[0]["study_count"] == 1
    points = findings[0]["observations"][0]["points"]
    assert [(p["row_id"], p["value_text"]) for p in points] == [
        ("week-1", "0 受试者百分比"), ("week-24", "57.7 受试者百分比"),
    ]
    assert all("周" in p["time"] for p in points)
    assert (records, groups, workspace) == before


@pytest.mark.parametrize("state", ("user_cleared", "not_reported"))
def test_current_clear_missing_never_reuses_a_source_value_or_becomes_zero(state):
    records, _, _ = _workspace()
    records[0][0].update(value=None, numeric_value=None, renderable=False,
                         disclosure_state=state)
    groups = report_b._groups_for_page("efficacy", records)
    workspace = report_b._comparison_workspace(records, groups, ())
    point = report_b._overview_findings(workspace, groups)[0]["observations"][0]["points"][-1]
    assert point["row_id"] == "week-24"
    assert "None" not in point["value_text"] and point["value_text"] != "0"
    if state == "user_cleared":
        assert point["value_text"] == "用户清除，待重新核实"


def test_unknown_or_untranslated_question_is_not_a_fabricated_home_conclusion():
    _, groups, workspace = _workspace()
    workspace["columns"][0]["question_known"] = False
    assert report_b._overview_findings(workspace, groups) == ()
    workspace["columns"][0].update(
        question_known=True, question_label="Very long original endpoint",
    )
    assert report_b._overview_findings(workspace, groups) == ()


def test_distinct_source_series_and_single_observations_stay_independently_linked():
    records, _, _ = _workspace()
    extra = dict(records[0][0], row_id="other-study", trial_id="trial-b",
                 product_id="product-b", product_zh="产品乙", value=42,
                 source_measure_path="other-measure")
    records.append((extra, None))
    groups = report_b._groups_for_page("efficacy", records)
    workspace = report_b._comparison_workspace(records, groups, ())
    finding = report_b._overview_findings(workspace, groups)[0]
    assert finding["study_count"] == 2 and finding["observation_count"] == 6
    assert {p["row_id"] for entry in finding["observations"] for p in entry["points"]} == {
        "week-1", "week-24", "other-study",
    }


@pytest.mark.parametrize("raw, expected", (
    ("From the first IMP administration to the last IMP administration + 14 weeks "
     "(i.e., up to 36 weeks)", "首次研究药物给药至末次给药后14周（最长36周）"),
    ("From Baseline up to End of Treatment period (16 weeks)", "基线至治疗期结束（16周）"),
    ("From Baseline up to End of Treatment period (24 weeks)", "基线至治疗期结束（24周）"),
))
def test_real_source_exposure_intervals_share_one_complete_native_time_path(raw, expected):
    assert report_b._native_timepoint_zh(raw) == expected
