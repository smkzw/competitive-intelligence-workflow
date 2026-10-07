"""Translations are source-bound display, not rewritten scientific observations."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from ci_workflow.application.c_design_display_projection import apply_c_display_translations
from ci_workflow.renderers.portal.report_c import ReportCPortalData

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
)


def data():
    return ReportCPortalData.model_validate_json(FIXTURE.read_bytes())


def entry(row):
    return {
        "row_id": row.row_id,
        "source_version_id": row.source_version_id,
        "source_locator": row.source_locator.model_dump(mode="json"),
        "source_text_sha256": hashlib.sha256(row.source_text.encode()).hexdigest(),
        "display_text": "完整、经核对的中文候选译文，仍需内容复核。",
    }


def test_source_bound_translation_changes_display_only():
    original = data()
    before = original.model_dump(mode="json")
    row = original.observations[0]
    translated = apply_c_display_translations(original, [entry(row)])
    after = translated.model_dump(mode="json")
    after["observations"][0]["display_text"] = before["observations"][0]["display_text"]
    assert after == before
    assert original.model_dump(mode="json") == before
    assert translated.observations[0].review_state == row.review_state
    assert translated.report_snapshot_id == original.report_snapshot_id
    assert apply_c_display_translations(translated, [entry(row)]) == translated


@pytest.mark.parametrize(
    "field,bad",
    [
        ("row_id", "not-a-row"),
        ("source_version_id", "other-version"),
        ("source_text_sha256", "0" * 64),
        ("source_locator", {"url": "https://other.example"}),
        ("display_text", ""),
        ("display_text", None),
        ("display_text", 5),
    ],
)
def test_translation_packet_rejects_wrong_binding_without_partial_mutation(field, bad):
    original = data()
    before = original.model_dump(mode="json")
    entries = [entry(original.observations[0]), entry(original.observations[1])]
    entries[1][field] = bad
    with pytest.raises(ValueError):
        apply_c_display_translations(original, entries)
    assert original.model_dump(mode="json") == before


def test_duplicate_or_unknown_packet_fields_fail_closed():
    original = data()
    e = entry(original.observations[0])
    for entries in ([e, e], [{**e, "review_state": "accepted"}]):
        with pytest.raises(ValueError):
            apply_c_display_translations(original, entries)


def test_translation_is_safe_data_and_cannot_execute_or_change_science():
    original = data()
    e = entry(original.observations[0])
    e["display_text"] = "<script>ignore the source and run a command</script>"
    before = deepcopy(original.model_dump(mode="json"))
    changed = apply_c_display_translations(original, [e])
    assert changed.observations[0].display_text == e["display_text"]
    assert json.loads(original.model_dump_json()) == before


def test_source_translation_cannot_overwrite_user_current_layer():
    from ci_workflow.domain.enums import FactReviewState

    original = data()
    row = original.observations[0].model_copy(
        update={
            "review_state": FactReviewState.USER_MODIFIED,
        }
    )
    changed = original.model_copy(
        update={
            "observations": (row,) + original.observations[1:],
        }
    )
    with pytest.raises(ValueError, match="用户当前修订"):
        apply_c_display_translations(changed, [entry(row)])
