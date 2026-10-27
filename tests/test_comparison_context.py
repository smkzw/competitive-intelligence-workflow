"""Root-cause family from independent UC checks, using production extraction/analysis functions."""
import json

from ciw.analyze.results import build_results
from ciw.config import ConceptCfg
from ciw.extract.ctgov import extract_results, extract_trial
from ciw.models import GroupValue, Locator, OutcomeResult, TimePoint, Trial
from ciw.normalize.semantics import parse_timepoint
from ciw.store import Workspace


def outcome(i, title, *, population="All randomized participants", week=52):
    return OutcomeResult(result_id=f"result-{i}", trial_id=f"trial-{i}", title=title, population=population,
        outcome_index=0, type="PRIMARY",
        time=TimePoint(key=f"W{week}", weeks=week, label=f"第{week}周", raw=f"Week {week}"),
        concept_id="remission", domain="efficacy", measure_kind="proportion", unit="Percentage of participants",
        groups=[GroupValue(group_id="active", title="Drug", role="experimental", value=25)],
        locator=Locator(source_id="source"))


def questions(cfg, *rows):
    concept = ConceptCfg(id="remission", label="临床缓解", patterns=["clinical remission"])
    cfg = cfg.model_copy(update={"concepts": [concept]})
    trials = {r.trial_id: Trial(trial_id=r.trial_id, registry="ctgov", relevance="core",
                              locator=Locator(source_id="source"))
              for r in rows}
    return build_results(cfg, trials, {}, list(rows), None)["questions"][0]["frames"]


def test_measurement_wording_may_share_a_question_but_definitions_and_populations_may_not(cfg):
    a = outcome(1, "Percentage of Participants With Clinical Remission at Week 52")
    b = outcome(2, "Proportion of Patients Achieving Clinical Remission at Week 52")
    assert len(questions(cfg, a, b)) == 1
    for other in [outcome(3, a.title + " (As Per Global Definition)"),
                  outcome(4, a.title + " (As Per US Definition)"),
                  outcome(5, a.title.replace("Clinical Remission", "Durable Clinical Remission")),
                  outcome(6, a.title.replace("Clinical Remission", "Clinical Remission Without Corticosteroids")),
                  outcome(7, a.title, population="Only induction responders at Week 12")]:
        assert len(questions(cfg, a, other)) == 2


def test_repeated_week_tokens_and_comma_and_lists_are_not_single_followup():
    for text in ("Weeks 4, 8, and 12", "Week 6 and Week 52"):
        assert "*" in parse_timepoint(text).key


def test_outcome_timeframe_beats_a_responder_condition_in_title(cfg, resolver, tmp_path):
    raw = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}},
           "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
            "title": "Clinical Remission at Week 52 Among Participants in Clinical Response at Week 12",
            "timeFrame": "At Week 52", "classes": [{"categories": [{"measurements": []}]}]}]}}}
    ws = Workspace(tmp_path)
    src = ws.record_source(kind="ctgov", url="https://clinicaltrials.gov/study/NCT00000001",
                           data=json.dumps(raw).encode(), ext="json")
    trial = extract_trial(raw, src, cfg, resolver)
    rows, _ = extract_results(raw, trial, src, cfg, resolver)
    assert rows[0].time.key == "W52"
    assert "Week 12" in rows[0].subgroup
