"""Keep scientific domains and missing/qualified source values reachable in B."""
from ciw.analyze.results import build_results
from ciw.models import GroupValue, Locator, OutcomeResult, Trial


def test_all_domains_remain_queryable_without_entering_efficacy_axes(cfg):
    trial = Trial(trial_id="T", registry="ctgov", locator=Locator(source_id="s"))
    domains = ("pk", "pd", "immunogenicity", "other", "safety", "efficacy")
    results = [OutcomeResult(result_id=d, trial_id="T", outcome_index=i, type="SECONDARY", title=d,
                             domain=d, measure_kind="other", locator=Locator(source_id="s"),
                             groups=[GroupValue(group_id="g", title="Unknown", value=None, value_raw="<5")])
               for i, d in enumerate(domains)]
    b = build_results(cfg, {"T": trial}, {}, results, None)
    assert b["questions"] == []
    assert {r["result_id"] for r in b["observations"]} == set(domains)
    assert all(r["groups"][0]["value"] is None and r["groups"][0]["value_raw"] == "<5" for r in b["observations"])


def test_zero_missing_and_different_groups_are_not_collapsed(cfg):
    trial = Trial(trial_id="T", registry="ctgov", relevance="core", locator=Locator(source_id="s"))
    result = OutcomeResult(result_id="r", trial_id="T", outcome_index=0, type="OTHER_PRE_SPECIFIED", title="PD",
                           domain="pd", measure_kind="mean", locator=Locator(source_id="s"),
                           groups=[GroupValue(group_id="g1", title="A", value=0, n=0),
                                   GroupValue(group_id="g2", title="B", value=None, n=None)])
    obs = build_results(cfg, {"T": trial}, {}, [result], None)["observations"]
    assert [(g["value"], g["n"]) for g in obs[0]["groups"]] == [(0, 0), (None, None)]
    trial.relevance = "background"
    assert build_results(cfg, {"T": trial}, {}, [result], None)["observations"] == []
