"""A literal cohort heading cannot absorb later general sections or an unrelated preamble."""
import pytest

from ciw.models import Design, Locator, Trial
from ciw.normalize.design import source_cohort_heading


@pytest.mark.parametrize('text', [
    'Condition A:\nMarker ≥7 mg.\nOther criteria:\nMarker ≥8 mg.',
    'Condition A:\nMarker ≥7 mg.\nExclusion Criteria:\nMarker ≥8 mg.',
    'Unrelated clinical context.\nCondition A:\nMarker ≥7 mg.',
])
def test_cross_section_or_unrelated_context_is_not_a_single_cohort(text):
    trial=Trial(trial_id='synthetic',registry='ctgov',locator=Locator(source_id='s'),
                conditions=['Condition A','Condition B'],design=Design(eligibility_text=text))
    assert source_cohort_heading(trial,'eligibility',text) is None
