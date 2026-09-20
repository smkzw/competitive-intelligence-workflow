"""Access observations are hints for one run, never durable login authority."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.application.run_service import run_project
from ci_workflow.application.yaozh_access import (
    YaozhSessionObservation,
    answer_yaozh_access,
    check_yaozh_runtime_access,
    persist_yaozh_route_access_receipt,
)
from tests.integration.test_research_package_submission import _project


def test_runtime_check_reuses_only_current_run_and_latest_success(tmp_path: Path) -> None:
    root = _project(tmp_path)
    answer = answer_yaozh_access(root, "available")
    run = run_project(root)
    now = datetime.now(UTC)
    observation = YaozhSessionObservation(
        project_id=answer.record.project_id, run_id=run.run_id,
        answer_digest=hashlib.sha256(answer.record_path.read_bytes()).hexdigest(),
        observed_at=now, host="codex", observer_id="browser-adapter",
        origin="https://vip.yaozh.com", technical_state="ready", page_marker_sha256="a" * 64,
    )
    assert not check_yaozh_runtime_access(root, host="codex", now=now).reuse_allowed
    persist_yaozh_route_access_receipt(root, observation)
    assert check_yaozh_runtime_access(root, host="codex", now=now).reuse_allowed
    assert not check_yaozh_runtime_access(root, host="hermes", now=now).reuse_allowed
    expired = check_yaozh_runtime_access(root, host="codex", now=now + timedelta(minutes=6))
    assert not expired.reuse_allowed
    failed = observation.model_copy(update={
        "technical_state": "session_expired", "observed_at": now + timedelta(seconds=1),
    })
    persist_yaozh_route_access_receipt(root, failed)
    state = check_yaozh_runtime_access(root, host="codex", now=now + timedelta(seconds=2))
    assert not state.reuse_allowed
    assert state.state == "access_blocked"
    run_project(root, resume=True)
    assert not check_yaozh_runtime_access(root, host="codex").reuse_allowed


@pytest.mark.parametrize("answer", ["skipped", "unavailable"])
def test_optional_disabled_route_does_not_require_run(tmp_path: Path, answer: str) -> None:
    root = _project(tmp_path)
    answer_yaozh_access(root, answer)
    result = check_yaozh_runtime_access(root, host="codex")
    assert result.state == "not_applicable"
    assert result.blocks_core_research is False


def test_legacy_observation_cannot_authorize_current_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    from ci_workflow.cli import main

    root = _project(tmp_path)
    answer = answer_yaozh_access(root, "available")
    run = run_project(root)
    legacy = YaozhSessionObservation(
        project_id=answer.record.project_id,
        answer_digest=hashlib.sha256(answer.record_path.read_bytes()).hexdigest(),
        observed_at=datetime.now(UTC), host="codex", observer_id="browser-adapter",
        origin="https://vip.yaozh.com", technical_state="ready", page_marker_sha256="b" * 64,
    )
    persisted = persist_yaozh_route_access_receipt(root, legacy)
    assert "run_id" not in json.loads(persisted.receipt_path.read_bytes())
    assert main(["yaozh", "check", "--project", str(root), "--host", "codex"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["run_id"] == run.run_id
    assert result["reuse_allowed"] is False
    assert result["state"] == "recheck_required"
