"""A threshold is not a replacement for its source definition or alternative clinical criteria."""
import pytest

from ciw.models import Design, Locator, Trial
from ciw.normalize.design import design_passages
from ciw.verify.design_clauses import DesignTopicReview, _check


@pytest.mark.parametrize("source,selected,role", [
    ("Severe organ impairment is defined as an eGFR ≤30 mL/min at screening "
     "or the need for dialysis or replacement therapy.",
     "eGFR ≤30 mL/min at screening", "exclusion"),
    ("Relapsed disease is defined as documented CR or PR after IST followed by reappearance of proteinuria ≥3 g/g.",
     "proteinuria ≥3 g/g", "inclusion"),
    ("严重肾功能损害定义为筛选时eGFR ≤30 mL/min或需要透析治疗。", "eGFR ≤30 mL/min", "exclusion"),
    ("Patients have eGFR ≤30 mL/min or require maintenance dialysis.", "eGFR ≤30 mL/min", "exclusion"),
    ("Patients have eGFR ≥40 mL/min and documented stable background therapy before screening.",
     "eGFR ≥40 mL/min", "inclusion"),
])
@pytest.mark.parametrize("preserve", ["truncated", "text", "condition"])
def test_predicate_definition_and_boolean_alternatives_remain_complete(source, selected, role, preserve):
    trial = Trial(trial_id="synthetic", registry="ctgov", locator=Locator(source_id="source"),
                  design=Design(eligibility_text=role.title() + " criteria:\n* " + source))
    item = DesignTopicReview(topic_id="topic", quote=source, clauses=[dict(
        field="eligibility", text=source if preserve == "text" else selected, quote=source,
        condition=source if preserve == "condition" else "", criterion_role=role)]).model_dump()
    okay, _ = _check(item, {"topic": dict(kind="eligibility_threshold")}, design_passages(trial))
    assert okay == (preserve != "truncated")


def test_numeric_comparison_or_is_not_a_boolean_alternative_and_peer_predicate_is_not_borrowed():
    from ciw.normalize.design import dependency_contexts

    selected = "eGFR greater than or equal to 40 mL/min"
    sentence = "Age ≥18 years; " + selected + "."
    peer = "Other participants have eGFR <30 mL/min or require dialysis."
    assert dependency_contexts(sentence + "\n\n" + peer, selected, sentence) == []
