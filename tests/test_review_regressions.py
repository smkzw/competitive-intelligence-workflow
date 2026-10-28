"""2026-10-27 独立审查发现的缺陷：每条一个反例（见 docs/REVIEW_2026-10-27.md §5）。"""

import json

import pytest

from ciw.analyze.results import _comparisons, _orient, build_results
from ciw.extract.ctgov import _looks_like_time
from ciw.models import Analysis, Arm, GroupValue, Locator, OutcomeResult, TimePoint, Trial
from ciw.normalize.arms import match_group
from ciw.normalize.semantics import classify, parse_timepoint
from ciw.sources.cde_registry import _phase
from ciw.verify.crosscheck import CrosscheckFailed, ExtractionTask, crosscheck
from ciw.verify.llm import FakeBackend
from ciw.verify.schemas import EventItem


# --- P0-1 概念误归
def test_composite_vas_is_not_nasal_obstruction_vas(cfg):
    t = "Change From Baseline in the Composite VAS Score (Combining VAS Scores for Nasal Obstruction, Nasal Discharge)"
    assert classify(t, cfg)[1] == "vas_composite"


def test_nps_response_without_surgery_is_not_surgery_endpoint(cfg):
    assert classify("Proportion With NPS Improvement >=1 Without Surgery or SCS", cfg)[1] != "surgery_or_scs"


# --- P0-2 比值与差值分开、方向统一
def _trial():
    return Trial(trial_id="NCT0", registry="ctgov", relevance="core", locator=Locator(source_id="s"))


def _result(groups, analyses, kind="ls_mean", title="Change From Baseline in NPS at Week 24"):
    return OutcomeResult(
        result_id="r1",
        trial_id="NCT0",
        outcome_index=0,
        type="PRIMARY",
        title=title,
        time=TimePoint(raw="Week 24", label="第24周", key="W24", weeks=24),
        concept_id="nps",
        domain="efficacy",
        measure_kind=kind,
        groups=groups,
        analyses=analyses,
        locator=Locator(source_id="s"),
    )


G = [
    GroupValue(group_id="OG0", title="Placebo", role="placebo", value=0.1, n=100),
    GroupValue(group_id="OG1", title="Drug", role="experimental", value=-1.7, n=100, product_id="dupilumab"),
]


def test_ratio_is_its_own_family():
    a = Analysis(group_ids=["OG0", "OG1"], param_type="Hazard Ratio", value=0.02, ci_lower=0.01, ci_upper=0.1)
    c = _comparisons(_result(G, [a]), _trial(), {})
    assert c[0]["family"] == "ratio" and c[0]["plot_value"] == 0.02


def test_control_minus_experimental_is_flipped_for_plot():
    a = Analysis(group_ids=["OG0", "OG1"], param_type="LS mean difference", value=1.8, ci_lower=1.5, ci_upper=2.1)
    c = _comparisons(_result(G, [a]), _trial(), {})[0]
    assert (c["value"], c["plot_value"], c["plot_lower"], c["plot_upper"]) == (1.8, -1.8, -2.1, -1.5)
    assert "对照组−试验组" in c["note"]


def test_ambiguous_small_difference_has_no_orientation():
    g1 = GroupValue(group_id="a", title="A", value=0.001)
    g2 = GroupValue(group_id="b", title="B", value=0.0)
    assert _orient(0.001, g1, g2) is None


@pytest.mark.parametrize("unit,expected", [("probability", False), ("percent", True), ("%", True), ("", False)])
def test_fraction_difference_does_not_claim_percentage_points(unit, expected):
    groups = [g.model_copy(update={"value": value}) for g, value in zip(G, (0.1, 0.7), strict=True)]
    result = _result(groups, [], kind="proportion").model_copy(update={"unit": unit})
    comparison = _comparisons(result, _trial(), {})[0]
    assert comparison["value"] == 0.6
    assert ("百分点" in comparison["param_type"]) is expected


# --- P0-3 基线 class 与亚组 class
def test_class_titles():
    assert _looks_like_time("Week 24") and _looks_like_time("Day 169 (EOT)")
    assert not _looks_like_time(">=2 prior surgeries in 12 months")
    assert not _looks_like_time("Baseline")


def test_baseline_class_is_retained_but_not_compared_as_a_followup(cfg, resolver):
    from ciw.extract.ctgov import extract_results
    from ciw.models import Source

    study = {
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "type": "PRIMARY",
                        "title": "Nasal Polyp Score at Week 24",
                        "paramType": "MEAN",
                        "unitOfMeasure": "score",
                        "timeFrame": "Baseline, Week 24",
                        "groups": [{"id": "OG000", "title": "Placebo"}],
                        "denoms": [{"units": "Participants", "counts": [{"groupId": "OG000", "value": "10"}]}],
                        "classes": [
                            {
                                "title": "Baseline",
                                "categories": [{"measurements": [{"groupId": "OG000", "value": "6.1"}]}],
                            },
                            {
                                "title": "Week 24",
                                "categories": [{"measurements": [{"groupId": "OG000", "value": "6.0"}]}],
                            },
                        ],
                    }
                ]
            }
        }
    }
    src = Source(source_id="s", kind="ctgov", url="u", fetched_at="2026-10-27", sha256="0" * 64)
    rs, _ = extract_results(study, _trial().model_copy(update={"arms": []}), src, cfg, resolver)
    assert [r.class_title for r in rs] == ["Baseline", "Week 24"]
    assert [r.time.key for r in rs] == ["BASELINE", "W24"] and rs[1].subgroup == ""
    from ciw.analyze.results import build_results
    trial = _trial()
    b = build_results(cfg, {trial.trial_id: trial}, {}, rs, None)
    assert all(q["time_key"] != "BASELINE" for q in b["questions"])
    assert len(b["observations"]) == 2


# --- P1-4 单药对照不能因联合臂被判为试验组
def test_solo_comparator_vs_combination_arm(resolver):
    arms = [
        Arm(arm_id="A0", label="Lunsekimig + Dupilumab", role="experimental", product_ids=["dupilumab", "lunsekimig"]),
        Arm(arm_id="A1", label="Dupilumab 300 mg Q2W", role="active_comparator", product_ids=["dupilumab"]),
    ]
    assert match_group("Dupilumab", arms, resolver)[1] == "active_comparator"
    assert match_group("Tezepelumab", arms, resolver)[1] == "unknown"  # 产品不在任何臂


# --- P1-5 百分比变化与绝对变化分题
def test_percent_change_is_separate_question(cfg):
    t = _trial()
    a = _result(G, [], title="Change From Baseline in NPS at Week 24")
    b = _result(G, [], title="Percent Change From Baseline in NPS at Week 24").model_copy(update={"result_id": "r2"})
    qs = build_results(cfg, {"NCT0": t}, {}, [a, b], None)["questions"]
    assert len(qs) == 2 and any("百分比" in q["label"] for q in qs)


# --- P1-9 时间点
@pytest.mark.parametrize("text,key", [("Weeks 16 and 24", "W24*"), ("Day 0 to Day 28", "D28")])
def test_timepoint_regressions(text, key):
    assert parse_timepoint(text).key == key


# --- P1-6/7/8 交叉核对
TEXT = "示例公告（合成文本）：2024年3月，度普利尤单抗（Dupixent）在加拿大获批用于慢性鼻窦炎伴鼻息肉。"


def _task(resolver):
    return ExtractionTask(
        task_id="t",
        source_id="s",
        source_text=TEXT,
        instruction="x",
        item_model=EventItem,
        key_fields=("product_mention", "event_type", "region"),
        value_fields=("date",),
        date_fields=("date",),
        key_fn=lambda it: (
            resolver.find_in_text(it["product_mention"]) or it["product_mention"],
            it["event_type"],
            "加拿大" if it["region"] in ("加拿大", "Canada") else it["region"],
        ),
    )


def _b(fam, items=None, choice="A", raw=None):
    def r(system, user):
        if raw is not None:
            return raw
        if "独立核对员" in system:
            return json.dumps({"choice": choice})
        return json.dumps({"items": items or []}, ensure_ascii=False)

    return FakeBackend(family=fam, model=fam, responder=r)


Q = "2024年3月，度普利尤单抗（Dupixent）在加拿大获批"


def test_same_fact_with_different_names_is_one_item(resolver):
    a = {"product_mention": "Dupixent", "event_type": "approval", "region": "加拿大", "date": "2024-03", "quote": Q}
    b = {"product_mention": "dupilumab", "event_type": "approval", "region": "Canada", "date": "2024-03", "quote": Q}
    out = crosscheck(_task(resolver), {"extractor_a": _b("x", [a]), "verifier": _b("y", [b])})
    assert len(out) == 1 and out[0].status == "verified"


def test_date_not_in_quote_fails(resolver):
    a = {"product_mention": "Dupixent", "event_type": "approval", "region": "加拿大", "date": "2023-11", "quote": Q}
    out = crosscheck(
        _task(resolver), {"extractor_a": _b("x", [a]), "verifier": _b("y", [a])}
    )
    assert out[0].status == "needs_review"


def test_both_extractors_failing_raises(resolver):
    with pytest.raises(CrosscheckFailed):
        crosscheck(
            _task(resolver), {"extractor_a": _b("x", raw="bad"), "verifier": _b("y", raw="bad")}
        )


# --- P2 域判定与 CDE 亚期
@pytest.mark.parametrize(
    "title,domain",
    [
        ("Serum Concentration of Dupilumab in Participants Requiring Systemic Corticosteroids", "pk"),
        ("Change From Baseline in Total IgE Concentration", "pd"),
        ("Change From Baseline in Mucociliary Clearance Time", "other"),
        ("Time to First Nasal Polyp Surgery (Safety Population)", "efficacy"),
    ],
)
def test_domain_regressions(cfg, title, domain):
    assert classify(title, cfg)[0] == domain


def test_cde_subphases():
    assert _phase("Ⅰb期")[1] == 2 and _phase("IIa期")[1] == 3 and _phase("Ib/IIa期") == ("I/II", 3)


@pytest.mark.parametrize(
    "cls,time,rest",
    [
        ("Week 21, n=42, 32", "Week 21", ""),
        ("Change in PM Score - Week 12", "Week 12", "Change in PM Score"),
        ("Ethmoid Sinus Anterior", "", "Ethmoid Sinus Anterior"),
        (">=2 prior surgeries in 12 months", "", ">=2 prior surgeries in 12 months"),
        ("Week 24", "Week 24", ""),
    ],
)
def test_split_class(cls, time, rest):
    from ciw.extract.ctgov import _split_class

    assert _split_class(cls) == (time, rest)
