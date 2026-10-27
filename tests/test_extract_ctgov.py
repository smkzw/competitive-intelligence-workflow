"""CT.gov 确定性抽取：数值与来源登记逐一对应（夹具为真实记录裁剪）。"""

from conftest import load_study

from ciw.extract.ctgov import extract_results, extract_safety, extract_trial
from ciw.models import Source


def _src(nct):
    return Source(
        source_id=f"src_{nct}",
        kind="ctgov",
        url=f"https://clinicaltrials.gov/study/{nct}",
        fetched_at="2026-10-27T00:00:00+00:00",
        sha256="0" * 64,
    )


def _all(nct, cfg, resolver):
    study = load_study(nct)
    t = extract_trial(study, _src(nct), cfg, resolver)
    rs, _ = extract_results(study, t, _src(nct), cfg, resolver)
    return t, rs, extract_safety(study, t, _src(nct), resolver)


def test_sinus52_arms_roles_and_products(cfg, resolver):
    t, _, _ = _all("NCT02898454", cfg, resolver)
    assert t.acronym == "SINUS-52" and t.phase == "III" and t.relevance == "core"
    roles = {a.label: (a.role, a.product_ids) for a in t.arms}
    assert roles["Placebo"] == ("placebo", [])
    assert roles["Dupilumab 300 mg q2w"] == ("experimental", ["dupilumab"])
    assert "Mometasone furoate nasal spray" in t.design.background_therapy


def test_pooled_result_group_maps_to_product_not_title_guess(cfg, resolver):
    _, rs, _ = _all("NCT02898454", cfg, resolver)
    nps = next(r for r in rs if r.title == "Change From Baseline at Week 24 in Nasal Polyp Score")
    g = {x.title: x for x in nps.groups}
    pooled = g["Dupilumab 300 mg (24 Weeks Pooled Arm)"]
    assert (pooled.role, pooled.product_id, pooled.n, pooled.value, pooled.spread) == (
        "experimental",
        "dupilumab",
        294,
        -1.71,
        0.11,
    )
    assert g["Placebo"].role == "placebo" and g["Placebo"].value == 0.10
    assert nps.measure_kind == "ls_mean" and nps.concept_id == "nps" and nps.time.key == "W24"
    a = nps.analyses[0]
    assert (a.value, a.ci_lower, a.ci_upper, a.p_value) == (-1.80, -2.10, -1.51, "<0.0001")


def test_subgroup_outcomes_are_flagged(cfg, resolver):
    _, rs, _ = _all("NCT02898454", cfg, resolver)
    subs = [r for r in rs if r.concept_id == "nps" and r.subgroup]
    assert subs and all("Subgroup" in r.subgroup for r in subs)


def test_median_with_range_and_hazard_ratio(cfg, resolver):
    _, rs, _ = _all("NCT03085797", cfg, resolver)  # SYNAPSE
    nps = next(r for r in rs if r.concept_id == "nps" and r.type == "PRIMARY")
    assert nps.measure_kind == "median" and nps.time.key == "W52"
    mep = next(g for g in nps.groups if g.product_id == "mepolizumab")
    assert (mep.value, mep.lower, mep.upper) == (-1.0, -6.0, 3.0)
    surgery = [r for r in rs if r.measure_kind == "proportion" and r.class_title == "Week 16"]
    assert surgery and surgery[0].time.key == "W16"


def test_ae_counts_are_participants_with_their_own_denominator(cfg, resolver):
    _, _, s = _all("NCT02898454", cfg, resolver)
    placebo = next(g for g in s.groups if g.title == "Placebo")
    assert (placebo.serious.n, placebo.serious.N, placebo.deaths.n) == (16, 150, 0)
    assert s.other_threshold == 5.0
    term = next(t for t in s.terms if t.term == "Injection Site Erythema")
    st = next(x for x in term.stats if x.group_id == "EG000")
    assert (st.n, st.N, st.events) == (11, 150, 28)  # 事件数 28 ≠ 人数 11


def test_run_in_and_follow_up_groups_are_not_treatment(cfg, resolver):
    _, _, s = _all("NCT04851964", cfg, resolver)  # WAYPOINT 有 Run-in Period 组
    run_in = next(g for g in s.groups if g.title == "Run-in Period")
    assert run_in.period == "run_in" and run_in.role == "other"
    _, _, s2 = _all("NCT03085797", cfg, resolver)  # SYNAPSE 有 Follow-up 组
    assert {g.period for g in s2.groups if "Follow-up" in g.title} == {"follow_up"}


def test_discontinuation_due_to_ae_from_participant_flow(cfg, resolver):
    _, _, s = _all("NCT02898454", cfg, resolver)
    d = {x.title: (x.n, x.N) for x in s.discontinuations}
    assert d["Placebo"] == (4, 153)


def test_head_to_head_both_experimental(cfg, resolver):
    t, rs, _ = _all("NCT04998604", cfg, resolver)  # EVEREST
    assert {a.role for a in t.arms} == {"experimental"}
    nps = next(r for r in rs if r.concept_id == "nps" and r.type == "PRIMARY")
    assert {g.product_id for g in nps.groups} == {"dupilumab", "omalizumab"}
