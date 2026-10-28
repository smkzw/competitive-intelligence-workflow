"""确定性语义规则：v1/ciw2 review 中发现的缺陷各有一个反例。"""

import pytest

from ciw.analyze.common import pct
from ciw.models import Arm
from ciw.normalize.arms import match_group
from ciw.normalize.semantics import classify, measure_kind, parse_timepoint, subgroup_of


@pytest.mark.parametrize("text,key", [("Up to Week 148 (end of trial)", "W148_window*"),
    ("Through Week 52", "W52_window*"), ("Until Day 28", "D28_window*"),
    ("Up to Month 12", "M12_window*"), ("Week 148", "W148"),
    ("Week 0 to Week 68", "W0-68"), ("Day 0 to Day 28", "D0-28"),
    ("0-24 weeks", "W0-24"), ("0–24 weeks", "W0-24"), ("0 to 24 weeks", "W0-24"),
    ("0–28 days", "D0-28"), ("0 to 12 months", "M0-12")])
def test_upper_followup_window_is_not_a_single_visit(text, key):
    assert parse_timepoint(text).key == key
    assert parse_timepoint("Week 24", text).key == "W24"


def test_report_preserves_a_source_proportion_without_implying_percent(cfg):
    from ciw.analyze.results import build_results
    from ciw.models import GroupValue, Locator, OutcomeResult, TimePoint, Trial

    loc = Locator(source_id="synthetic-proportion")
    trial = Trial(trial_id="NCT00000001", registry="ctgov", title="Synthetic", locator=loc)
    result = OutcomeResult(result_id="r", trial_id=trial.trial_id, outcome_index=0, type="PRIMARY",
        title="Nasal Polyp Score response", concept_id="nps", domain="efficacy", measure_kind="proportion",
        unit="Proportion of participants", time=TimePoint(raw="Week 1", label="第1周", key="W1", weeks=1),
        groups=[GroupValue(group_id="g", title="Group", value=0.543)], locator=loc)
    report = build_results(cfg, {trial.trial_id: trial}, {}, [result], None)
    question = report["questions"][0]
    assert question["measure_label"] == "比例"
    assert question["units"] == ["Proportion of participants"]
    assert question["rows"][0]["value"] == 0.543


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Serum Concentration of Dupilumab", "pk"),
        ("Area Under the Curve (AUC) of Tezepelumab", "pk"),
        ("Number of Participants With Treatment-Emergent Anti-Drug Antibodies", "immunogenicity"),
        ("Change From Baseline in ADAS-Cog13", "other"),  # v1 误判为免疫原性
        ("Number of Participants With Serious Adverse Events (SAEs)", "safety"),
        ("Clinically Significant Laboratory Abnormalities", "safety"),  # v1 误判为疗效
        ("Change From Baseline in Blood Eosinophil Count", "pd"),
        ("Change From Baseline in Nasal Polyp Score at Week 24", "efficacy"),
        ("Some Unlisted Exploratory Outcome", "other"),  # 字典外不默认疗效
    ],
)
def test_domain(cfg, title, expected):
    assert classify(title, cfg)[0] == expected


def test_concepts_do_not_merge_different_instruments(cfg):
    assert classify("Change From Baseline in Nasal Congestion Score (NCS)", cfg)[1] == "ncs"
    assert classify("Change in Nasal Obstruction VAS Score", cfg)[1] == "nasal_obstruction_vas"
    assert classify("Time to First SCS Use or NP Surgery", cfg)[1] == "surgery_or_scs"


@pytest.mark.parametrize(
    "param,unit,kind",
    [
        ("LEAST_SQUARES_MEAN", "percent change", "ls_mean"),  # v1 误判为比例
        ("NUMBER", "Percentage of participants", "proportion"),
        ("NUMBER", "% of participants", "proportion"),
        ("COUNT_OF_PARTICIPANTS", "Participants", "count"),
        ("COUNT_OF_UNITS", "eyes", "count_units"),
        ("MEDIAN", "Scores on a scale", "median"),
    ],
)
def test_measure_kind(param, unit, kind):
    assert measure_kind(param, unit) == kind


@pytest.mark.parametrize(
    "texts,key,weeks",
    [
        (("Baseline, Week 24",), "W24", 24),
        (("Baseline and Weeks 49 to 52",), "W49-52", 52),
        (("Week 0 to Week 68",), "W0-68", 68),  # explicit window is not the last visit
        (("Baseline (Day 1) and Week 52",), "W52", 52),
        (("Day 169",), "D169", None),  # 不能整除 7 不折算
        (("Month 6",), "M6", None),  # 月不折算成周
        (("Weeks 8, 16, 24, 32, 40, 48 and 52",), "W52*", 52),
    ],
)
def test_timepoints(texts, key, weeks):
    tp = parse_timepoint(*texts)
    assert tp.key == key and tp.weeks == weeks


def test_subgroup():
    assert subgroup_of("Change in NPS: Subgroup of Participants With Asthma").startswith("Subgroup")
    assert subgroup_of("Change in NPS in Participants With Prior Surgery").startswith("in Participants With")
    assert subgroup_of("Change From Baseline in Nasal Polyp Score") == ""


def _arms():
    return [
        Arm(arm_id="A0", label="Drug X 300 mg", type="EXPERIMENTAL", role="experimental", product_ids=["dupilumab"]),
        Arm(arm_id="A1", label="Placebo", type="PLACEBO_COMPARATOR", role="placebo"),
    ]


def test_placebo_with_dose_is_not_treatment(resolver):
    assert match_group("Placebo 0 mg/kg", _arms(), resolver)[1] == "placebo"  # v1 判为治疗组


def test_unknown_group_stays_unknown(resolver):
    assert match_group("Cohort B", _arms(), resolver)[1] == "unknown"


def test_placebo_then_drug_is_not_experimental(resolver):
    assert match_group("Placebo then Dupilumab", _arms(), resolver)[1] == "unknown"


@pytest.mark.parametrize("n,N,expected", [(12, 200, 6.0), (None, 200, None), (0, 0, None), (5, 4, None), (0, 10, 0.0)])
def test_pct_only_from_counts(n, N, expected):
    assert pct(n, N) == expected


def test_pre_retrieval_exclusions_can_use_definition_without_overriding_manual_dictionary():
    from ciw.config import ConceptCfg
    concept = ConceptCfg(id="provisional", label="阈值尚未索引", patterns=["Histologic response"],
                         exclude=["≤6"], provisional=True)
    assert not concept.matches("Histologic response", "Defined as ≤6 cells")
    concept.provisional = False
    assert concept.matches("Histologic response", "Defined as ≤6 cells")
