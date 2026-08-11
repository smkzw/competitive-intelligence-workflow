from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> Draft202012Validator:
    payload = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return Draft202012Validator(payload, format_checker=FormatChecker())


def test_event_checkpoint_replay_is_idempotent_without_framework_cache(
    tmp_path: Path,
) -> None:
    from ci_workflow.storage.checkpoint_store import CheckpointStore
    from ci_workflow.storage.event_store import (
        EventConflictError,
        EventStore,
        WorkflowEvent,
    )

    project_root = tmp_path / "项目"
    store = EventStore(project_root)
    checkpoint_store = CheckpointStore(project_root)
    event = WorkflowEvent(
        schema_version="1.0",
        event_id="event_001",
        project_id="project_001",
        run_id="run_001",
        event_type="artifact_published",
        occurred_at="2026-08-11T20:55:00+08:00",
        actor_id="runner_001",
        idempotency_key="publish:B:v1:html",
        payload={"artifact_id": "artifact_001"},
    )
    first = store.append(event)
    duplicate = store.append(event.model_copy(update={"event_id": "event_retry"}))
    assert duplicate == first
    assert len(store.read_all()) == 1

    with pytest.raises(EventConflictError):
        store.append(event.model_copy(update={"payload": {"artifact_id": "different"}}))

    effects: list[str] = []
    checkpoint = checkpoint_store.replay(
        store,
        run_id="run_001",
        initial_state={"published": []},
        reducer=lambda state, item: {
            "published": [*state["published"], item.payload["artifact_id"]]
        },
        side_effect=lambda item: effects.append(item.payload["artifact_id"]),
    )
    assert checkpoint.state == {"published": ["artifact_001"]}
    assert effects == ["artifact_001"]

    private_cache = project_root / ".langgraph-cache"
    private_cache.mkdir(parents=True)
    (private_cache / "state.json").write_text("not canonical", encoding="utf-8")
    (private_cache / "state.json").unlink()
    private_cache.rmdir()

    restored = checkpoint_store.replay(
        store,
        run_id="run_001",
        initial_state={"published": []},
        reducer=lambda state, item: {
            "published": [*state["published"], item.payload["artifact_id"]]
        },
        side_effect=lambda item: effects.append(item.payload["artifact_id"]),
    )
    assert restored == checkpoint
    assert effects == ["artifact_001"]
    lines = (project_root / "events/events.jsonl").read_text(encoding="utf-8").splitlines()
    event_payload = json.loads(lines[0])
    assert event_payload["idempotency_key"] == "publish:B:v1:html"
    _schema("event.schema.json").validate(event_payload)

    checkpoint_paths = tuple((project_root / "state/checkpoints").glob("*.json"))
    assert len(checkpoint_paths) == 1
    checkpoint_payload = json.loads(checkpoint_paths[0].read_text(encoding="utf-8"))
    _schema("checkpoint.schema.json").validate(checkpoint_payload)

    checkpoint_payload["state"]["published"] = ["tampered"]
    checkpoint_paths[0].write_text(
        json.dumps(checkpoint_payload, ensure_ascii=False), encoding="utf-8"
    )
    from ci_workflow.storage.checkpoint_store import CheckpointIntegrityError

    with pytest.raises(CheckpointIntegrityError):
        checkpoint_store.latest(run_id="run_001")

    crash_root = tmp_path / "中断恢复项目"
    crash_events = EventStore(crash_root)
    crash_checkpoints = CheckpointStore(crash_root)
    crash_events.append(
        event.model_copy(
            update={
                "event_id": "event_crash",
                "run_id": "run_crash",
                "idempotency_key": "publish:B:v1:pdf",
                "payload": {"artifact_id": "artifact_crash"},
            }
        )
    )
    completed_effect_keys: set[str] = set()
    completed_effects: list[str] = []
    interrupt_once = True

    def idempotent_effect(item: object) -> None:
        nonlocal interrupt_once
        from ci_workflow.storage.event_store import StoredWorkflowEvent

        assert isinstance(item, StoredWorkflowEvent)
        if item.idempotency_key not in completed_effect_keys:
            completed_effect_keys.add(item.idempotency_key)
            completed_effects.append(item.payload["artifact_id"])
        if interrupt_once:
            interrupt_once = False
            raise RuntimeError("模拟副作用完成后、检查点保存前中断")

    with pytest.raises(RuntimeError, match="模拟副作用"):
        crash_checkpoints.replay(
            crash_events,
            run_id="run_crash",
            initial_state={"published": []},
            reducer=lambda state, item: {
                "published": [*state["published"], item.payload["artifact_id"]]
            },
            side_effect=idempotent_effect,
        )
    recovered_after_crash = crash_checkpoints.replay(
        crash_events,
        run_id="run_crash",
        initial_state={"published": []},
        reducer=lambda state, item: {
            "published": [*state["published"], item.payload["artifact_id"]]
        },
        side_effect=idempotent_effect,
    )
    assert recovered_after_crash.state == {"published": ["artifact_crash"]}
    assert completed_effects == ["artifact_crash"]
