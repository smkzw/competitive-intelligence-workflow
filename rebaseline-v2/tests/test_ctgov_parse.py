import copy

from ciw2.sources.ctgov import ae_facts, all_facts, map_phase, parse_study, result_facts, stat_type_of


def test_parse_design(study):
    s = parse_study(study)
    assert s["nct"] == "NCT03985943"
    assert s["phase"] == "phase3"
    assert s["enrollment"] == 941
    assert s["china_site"] is False
    assert any(i["name"].lower().startswith("nemolizumab") for i in s["interventions"])
    assert s["primary_outcomes"][0]["timeFrame"] == "Week 16"


def test_phase_mapping():
    assert map_phase(["PHASE2", "PHASE3"]) == "phase2_3"
    assert map_phase(["NA"]) == "unknown"
    assert map_phase(None) == "unknown"


def test_result_facts_keep_raw_group_titles(study):
    facts = [f for f in result_facts(study) if f["field"] == "result.primary.value"]
    placebo = next(f for f in facts if f["context"]["group_id"] == "OG000"
                   and f["context"]["endpoint"].startswith("Percentage of Participants With an Investigator"))
    assert placebo["value"] == 24.6
    assert placebo["context"]["arm"] == "Initial Treatment Period (Baseline - Week 16 Predose): Placebo"
    assert placebo["context"]["denominator"] == 321
    assert placebo["context"]["stat_type"] == "proportion"
    assert placebo["tier"] == "critical" and placebo["status"] == "verified"
    an = next(f for f in result_facts(study) if f["field"] == "result.primary.analysis")
    assert an["value"]["paramValue"] == "11.5"


def test_ae_facts_and_unknown(study):
    sae = [f for f in ae_facts(study) if f["field"] == "safety.sae.any"]
    eg0 = next(f for f in sae if f["context"]["group_id"] == "EG000")
    assert (eg0["value"], eg0["context"]["denominator"], eg0["context"]["proportion"]) == (4, 321, 1.2)
    s2 = copy.deepcopy(study)
    del s2["resultsSection"]["adverseEventsModule"]["eventGroups"][0]["seriousNumAffected"]
    eg0b = next(f for f in ae_facts(s2) if f["field"] == "safety.sae.any" and f["context"]["group_id"] == "EG000")
    assert eg0b["value"] is None and eg0b["status"] == "unknown"     # 缺失≠0
    assert eg0b["context"].get("proportion") is None


def test_stat_type():
    assert stat_type_of("NUMBER", "percentage of participants") == "proportion"
    assert stat_type_of("COUNT_OF_PARTICIPANTS", "Participants") == "count_participants"
    assert stat_type_of("LEAST_SQUARES_MEAN", "score") == "ls_mean"


def test_all_facts_nonempty(study):
    fields = {f["field"] for f in all_facts(study)}
    assert {"design.sample_size", "design.primary_endpoint", "result.primary.value", "safety.sae.any",
            "safety.sae.term"} <= fields
