"""PPT Master 八项确认推荐、结果覆盖和一次性会话测试。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.renderers.pptx_master.confirmation import (
    CONFIRMATION_KEYS,
    ConfirmationSessionStore,
    PptxConfirmationError,
    apply_confirmation_result,
    build_confirmation_result,
    build_recommendations,
    close_confirmation_session,
    load_confirmation_result,
    load_recommendations,
    open_confirmation_session,
    validate_confirmation_artifact,
    validate_confirmation_result,
    write_confirmation_result,
    write_recommendations,
)

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 31, 12, tzinfo=UTC)


def _source_pack(report: str = "A", *, snapshot_id: str = "snapshot-001") -> dict[str, Any]:
    return {
        "project_id": "project-three-report",
        "report": report,
        "report_version": "v-fixture-001",
        "source_pack_id": f"source-pack-{report.lower()}-001",
        "source_pack_sha256": ("a" if report == "A" else "b" if report == "B" else "c") * 64,
        "snapshot_id": snapshot_id,
        "snapshot_sha256": "1" * 64,
        "claim_snapshot_id": "claim-snapshot-001",
        "evidence_snapshot_id": "evidence-snapshot-001",
        "coverage_set_id": f"coverage-set-{report.lower()}-001",
        "data_cutoff": "2026-08-31",
        "page_count": 12,
    }


def _recommendations(report: str = "A", **kwargs: Any) -> Any:
    return build_recommendations(_source_pack(report), generated_at=NOW, **kwargs)


def test_recommendations_are_eight_ordered_chinese_items_and_are_deterministic() -> None:
    first = _recommendations("A")
    second = _recommendations("A")

    assert tuple(item.item_id for item in first.items) == CONFIRMATION_KEYS
    assert len(first.items) == 8
    assert all("确认" not in item.label_zh for item in first.items)
    assert all(item.recommended_value_zh in item.options_zh for item in first.items)
    assert first == second
    assert first.recommendations_sha256 == second.recommendations_sha256
    assert first.item("page_range").recommended_value_zh == (
        "覆盖来源包全部 12 页（第 1 页至第 12 页）"
    )


def test_report_result_and_effective_values_bind_and_override_recommendation() -> None:
    recommendations = _recommendations("B")
    values = {item.item_id: item.recommended_value_zh for item in recommendations.items}
    values["style_goal"] = "管理层摘要、结论优先"
    result = build_confirmation_result(
        recommendations,
        values,
        confirmed_by="medical-reviewer",
        confirmed_at=NOW + timedelta(minutes=5),
    )

    assert validate_confirmation_result(result, recommendations) == result
    effective = apply_confirmation_result(recommendations, result)
    assert effective["style_goal"] == "管理层摘要、结论优先"
    assert effective["canvas_format"] == recommendations.item("canvas_format").recommended_value_zh
    assert effective.source == "user_confirmed"


def test_result_missing_unknown_and_cross_snapshot_are_rejected() -> None:
    recommendations = _recommendations()
    values = {item.item_id: item.recommended_value_zh for item in recommendations.items}

    with pytest.raises(PptxConfirmationError, match="缺字段|覆盖八项"):
        build_confirmation_result(
            recommendations,
            {key: value for key, value in values.items() if key != "image_strategy"},
            confirmed_at=NOW,
        )

    result = build_confirmation_result(recommendations, values, confirmed_at=NOW)
    changed = result.model_dump(mode="json")
    changed["snapshot_id"] = "snapshot-drifted"
    with pytest.raises(PydanticValidationError):
        type(result).model_validate(changed | {"result_sha256": result.result_sha256})

    changed_result = result.model_copy(update={"snapshot_id": "snapshot-drifted"})
    with pytest.raises(PptxConfirmationError, match="快照"):
        validate_confirmation_result(changed_result, recommendations)

    unknown = dict(values)
    unknown["new_option"] = "新增"
    with pytest.raises(PptxConfirmationError, match="未知|八项"):
        build_confirmation_result(recommendations, unknown, confirmed_at=NOW)


def test_result_digest_and_recommendation_digest_drift_fail_closed() -> None:
    recommendations = _recommendations()
    result = build_confirmation_result(recommendations, confirmed_at=NOW)
    result_payload = result.model_dump(mode="json")
    result_payload["confirmed_values"]["color_scheme"] = "漂移后的颜色"
    with pytest.raises(PydanticValidationError, match="摘要"):
        type(result).model_validate(result_payload)

    recommendation_payload = recommendations.model_dump(mode="json")
    recommendation_payload["items"][0]["recommended_value_zh"] = "漂移后的画布"
    with pytest.raises(PydanticValidationError, match="摘要|推荐值"):
        type(recommendations).model_validate(recommendation_payload)

    result_payload = result.model_dump(mode="json")
    result_payload["recommendations_sha256"] = "f" * 64
    # Recompute result digest so the failure specifically exercises recommendation drift.
    with pytest.raises(PydanticValidationError):
        type(result).model_validate(result_payload)


def test_session_close_is_one_time_and_replay_is_idempotent(tmp_path: Path) -> None:
    recommendations = _recommendations("C")
    result = build_confirmation_result(recommendations, confirmed_at=NOW + timedelta(minutes=2))
    session = open_confirmation_session(recommendations, opened_at=NOW)
    closed = close_confirmation_session(session, result, closed_at=NOW + timedelta(minutes=3))
    replay = close_confirmation_session(closed, result, closed_at=NOW + timedelta(minutes=30))

    assert closed.state == "closed"
    assert replay == closed
    assert replay.closed_at == NOW + timedelta(minutes=3)

    other_values = {item.item_id: item.recommended_value_zh for item in recommendations.items}
    other_values["image_strategy"] = "不使用图片，改用中文结构化事实卡片"
    different = build_confirmation_result(
        recommendations,
        other_values,
        confirmed_at=NOW + timedelta(minutes=4),
    )
    with pytest.raises(PptxConfirmationError, match="已经关闭"):
        close_confirmation_session(closed, different)


def test_persistence_is_atomic_and_same_payload_is_idempotent(tmp_path: Path) -> None:
    recommendations = _recommendations()
    result = build_confirmation_result(recommendations, confirmed_at=NOW)
    recommendation_path = tmp_path / "confirm_ui" / "recommendations.json"
    result_path = tmp_path / "confirm_ui" / "result.json"
    session_path = tmp_path / "confirm_ui" / "session.json"

    assert write_recommendations(recommendations, recommendation_path) == recommendation_path
    assert write_recommendations(recommendations, recommendation_path) == recommendation_path
    assert load_recommendations(recommendation_path) == recommendations
    assert write_confirmation_result(result, result_path) == result_path
    assert load_confirmation_result(result_path) == result
    session = open_confirmation_session(recommendations, opened_at=NOW)
    store = ConfirmationSessionStore(session_path)
    store.save(session)
    closed = store.close(recommendations, result, closed_at=NOW + timedelta(minutes=1))
    assert store.close(recommendations, result, closed_at=NOW + timedelta(minutes=9)) == closed
    assert store.load() == closed


def test_root_and_packaged_schema_validate_all_confirmation_artifacts(tmp_path: Path) -> None:
    root_schema = ROOT / "schemas" / "pptx-confirmation.schema.json"
    packaged_schema = ROOT / "src" / "ci_workflow" / "schemas" / "pptx-confirmation.schema.json"
    assert root_schema.read_text(encoding="utf-8") == packaged_schema.read_text(encoding="utf-8")
    schema = json.loads(root_schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    recommendations = _recommendations()
    result = build_confirmation_result(recommendations, confirmed_at=NOW)
    session = open_confirmation_session(recommendations, opened_at=NOW)
    closed = close_confirmation_session(session, result, closed_at=NOW + timedelta(minutes=1))
    for model in (recommendations, result, session, closed):
        validator.validate(model.model_dump(mode="json"))
        validate_confirmation_artifact(model)

    # A persisted result cannot be mistaken for an open UI session.
    assert not list(tmp_path.rglob("*.pptx"))
