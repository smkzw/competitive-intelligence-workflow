"""Yaozh 访问选择的项目级持久化、一次回答、幂等重放与无凭据 CLI 边界。

v1.3 §1.2/§5.3：每个新项目只询问一次药智网访问条件；回答持久化后不可改写；
相同回答幂等重放；任何用户名、密码、Cookie、令牌、授权头或任意元数据
都不得进入 CLI 表面或持久化记录。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECORD_RELATIVE_PATH = Path("state") / "yaozh-access.json"
ALLOWED_RECORD_KEYS = {
    "schema_version",
    "project_id",
    "answer",
    "asked_at",
    "ask_count",
    "route_enabled",
    "source_role_zh",
}
CREDENTIAL_ARGUMENTS = (
    ("--username", "someone"),
    ("--password", "hunter2"),
    ("--cookie", "SESSIONID=abc"),
    ("--token", "Bearer abc"),
    ("--header", "Authorization: Bearer abc"),
    ("--authorization", "Bearer abc"),
    ("--api-key", "abc"),
    ("--session", "abc"),
    ("--metadata", '{"cookie": "x"}'),
    ("--note", "用户名 someone"),
)
CREDENTIAL_TOKENS = (
    "username",
    "password",
    "cookie",
    "token",
    "authorization",
    "api-key",
    "api_key",
    "secret",
    "bearer ",
    "sessionid",
)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ci_workflow", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _create_project(tmp_path: Path, name: str = "哮喘竞品项目") -> Path:
    project_root = tmp_path / name
    created = _run(
        "project",
        "create",
        "--root",
        str(project_root),
        "--indication",
        "重度哮喘",
        "--reports",
        "A,B",
        "--outputs",
        "html",
    )
    assert created.returncode == 0, created.stderr
    return project_root


def _answer(project_root: Path, answer: str) -> subprocess.CompletedProcess[str]:
    return _run("yaozh", "answer", "--root", str(project_root), "--answer", answer)


def _read_record(project_root: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((project_root / RECORD_RELATIVE_PATH).read_text(encoding="utf-8")),
    )


@pytest.mark.parametrize(
    ("answer", "route_enabled"),
    [
        ("available", True),
        ("unavailable", False),
        ("skipped", False),
    ],
)
def test_yaozh_answer_persists_closed_record_once_per_project(
    tmp_path: Path, answer: str, route_enabled: bool
) -> None:
    project_root = _create_project(tmp_path)
    result = _answer(project_root, answer)
    assert result.returncode == 0, result.stderr
    assert "YAOZH_ANSWER_RECORDED" in result.stdout
    assert "不再询问" in result.stdout

    record_path = project_root / RECORD_RELATIVE_PATH
    assert record_path.is_file()
    record = _read_record(project_root)
    assert set(record) == ALLOWED_RECORD_KEYS
    assert record["answer"] == answer
    assert record["ask_count"] == 1
    assert record["route_enabled"] is route_enabled
    assert record["schema_version"] == "1.0"
    project = json.loads((project_root / "project.yaml").read_text(encoding="utf-8"))
    active = project["active_contract_version"]
    contract = next(
        item for item in project["project_contract_versions"] if item["contract_version"] == active
    )
    assert record["project_id"] == contract["project_id"]
    serialized = json.dumps(record, ensure_ascii=False)
    assert not any(token in serialized.lower() for token in CREDENTIAL_TOKENS)

    verified = _run("project", "verify", "--root", str(project_root))
    assert verified.returncode == 0, verified.stderr


def test_yaozh_identical_replay_is_idempotent_and_byte_stable(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    first = _answer(project_root, "unavailable")
    assert first.returncode == 0, first.stderr
    record_path = project_root / RECORD_RELATIVE_PATH
    original_bytes = record_path.read_bytes()
    original_stat = record_path.stat()

    replay = _answer(project_root, "unavailable")
    assert replay.returncode == 0, replay.stderr
    assert "YAOZH_ANSWER_REPLAYED" in replay.stdout
    assert "幂等" in replay.stdout
    assert record_path.read_bytes() == original_bytes
    assert record_path.stat().st_mtime_ns == original_stat.st_mtime_ns


def test_yaozh_different_second_answer_fails_closed_in_chinese(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    assert _answer(project_root, "available").returncode == 0
    record_path = project_root / RECORD_RELATIVE_PATH
    original_bytes = record_path.read_bytes()

    conflict = _answer(project_root, "skipped")
    assert conflict.returncode == 2
    assert "CONTRACT_ERROR" in conflict.stderr
    assert "只能" in conflict.stderr
    assert "一次" in conflict.stderr
    assert "available" in conflict.stderr
    assert "skipped" in conflict.stderr
    assert "Traceback" not in conflict.stderr
    assert record_path.read_bytes() == original_bytes


@pytest.mark.parametrize("answer", ["maybe", "session_expired", "SKIP", ""])
def test_yaozh_answer_rejects_values_outside_ask_options(tmp_path: Path, answer: str) -> None:
    project_root = _create_project(tmp_path)
    result = _answer(project_root, answer)
    assert result.returncode == 2
    assert "CONTRACT_ERROR" in result.stderr or "参数值不在允许范围内" in result.stderr
    assert not (project_root / RECORD_RELATIVE_PATH).exists()


def test_yaozh_cli_surface_has_no_credential_or_metadata_options(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)

    help_text = _run("yaozh", "answer", "--help")
    assert help_text.returncode == 0, help_text.stderr
    assert "--answer" in help_text.stdout
    assert "--root" in help_text.stdout
    for token in ("--username", "--password", "--cookie", "--token", "--header"):
        assert token not in help_text.stdout

    for flag, value in CREDENTIAL_ARGUMENTS:
        result = _run(
            "yaozh",
            "answer",
            "--root",
            str(project_root),
            "--answer",
            "available",
            flag,
            value,
        )
        assert result.returncode == 2, (flag, result.stdout, result.stderr)
        assert "无法识别的参数" in result.stderr
    assert not (project_root / RECORD_RELATIVE_PATH).exists()


def test_yaozh_answer_requires_a_verified_project_workspace(tmp_path: Path) -> None:
    empty_root = tmp_path / "不是项目"
    empty_root.mkdir()
    result = _answer(empty_root, "available")
    assert result.returncode == 2
    assert "CONTRACT_ERROR" in result.stderr
    assert "项目" in result.stderr
    assert not (empty_root / RECORD_RELATIVE_PATH).exists()


def _valid_record_payload(project_root: Path, answer: str) -> dict[str, object]:
    first = _answer(project_root, answer)
    assert first.returncode == 0, first.stderr
    return _read_record(project_root)


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda payload: {**payload, "cookie": "SESSIONID=abc"}, id="extra-cookie"),
        pytest.param(lambda payload: {**payload, "metadata": {"token": "x"}}, id="extra-metadata"),
        pytest.param(lambda payload: {**payload, "ask_count": 2}, id="ask-count-edited"),
        pytest.param(
            lambda payload: {**payload, "project_id": "other-project"}, id="wrong-project"
        ),
    ],
)
def test_yaozh_tampered_or_foreign_record_fails_closed(
    tmp_path: Path, mutate: Callable[[dict[str, object]], dict[str, object]]
) -> None:
    project_root = _create_project(tmp_path)
    payload = _valid_record_payload(project_root, "available")
    record_path = project_root / RECORD_RELATIVE_PATH
    answer = payload["answer"]
    assert isinstance(answer, str)
    record_path.write_text(
        json.dumps(mutate(payload), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tampered_bytes = record_path.read_bytes()

    result = _answer(project_root, answer)
    assert result.returncode == 2
    assert "CONTRACT_ERROR" in result.stderr
    assert "药智" in result.stderr
    assert "Traceback" not in result.stderr
    assert record_path.read_bytes() == tampered_bytes


def test_yaozh_corrupt_record_file_fails_closed(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    payload = _valid_record_payload(project_root, "skipped")
    record_path = project_root / RECORD_RELATIVE_PATH
    corrupt = "这不是 JSON"
    record_path.write_text(corrupt, encoding="utf-8")

    result = _answer(project_root, str(payload["answer"]))
    assert result.returncode == 2
    assert "CONTRACT_ERROR" in result.stderr
    assert record_path.read_text(encoding="utf-8") == corrupt


def test_yaozh_record_is_a_regular_file_only(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    record_path = project_root / RECORD_RELATIVE_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "外部文件.json"
    outside.write_text("{}", encoding="utf-8")
    os.symlink(outside, record_path)

    result = _answer(project_root, "available")
    assert result.returncode == 2
    assert "CONTRACT_ERROR" in result.stderr
    assert record_path.is_symlink()


def test_yaozh_dangling_record_symlink_fails_closed_without_replacing_it(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    record_path = project_root / RECORD_RELATIVE_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(tmp_path / "不存在.json", record_path)

    result = _answer(project_root, "available")

    assert result.returncode == 2
    assert "CONTRACT_ERROR" in result.stderr
    assert record_path.is_symlink()


def test_session_expiry_is_a_typed_nonblocking_route_receipt_not_a_new_answer(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.yaozh_access import (
        YaozhSessionObservation,
        build_yaozh_route_access_receipt,
        load_yaozh_access_record,
    )

    project_root = _create_project(tmp_path)
    assert _answer(project_root, "available").returncode == 0
    answer_path = project_root / RECORD_RELATIVE_PATH
    answer_bytes = answer_path.read_bytes()
    answer = load_yaozh_access_record(project_root)
    assert answer is not None

    observation = YaozhSessionObservation(
        project_id=answer.project_id,
        answer_digest=__import__("hashlib").sha256(answer_bytes).hexdigest(),
        observed_at=datetime(2026, 9, 5, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        host="codex",
        observer_id="codex-browser-adapter",
        origin="https://vip.yaozh.com",
        technical_state="session_expired",
        page_marker_sha256="a" * 64,
    )
    receipt = build_yaozh_route_access_receipt(answer, observation)

    assert receipt.technical_state == "session_expired"
    assert receipt.result_class == "access_blocked"
    assert receipt.blocks_core_research is False
    assert receipt.observation_digest
    assert receipt.observed_at == observation.observed_at
    assert receipt.host == observation.host
    assert "自行登录" in receipt.user_action_zh
    assert answer_path.read_bytes() == answer_bytes
    serialized = receipt.model_dump_json().lower()
    assert not any(token in serialized for token in CREDENTIAL_TOKENS)


@pytest.mark.parametrize(
    "technical_state",
    ["captcha_required", "permission_denied", "tool_unavailable", "parser_error"],
)
def test_yaozh_session_observation_keeps_technical_failures_distinct_and_nonblocking(
    tmp_path: Path, technical_state: str
) -> None:
    from ci_workflow.application.yaozh_access import (
        YaozhSessionObservation,
        build_yaozh_route_access_receipt,
        load_yaozh_access_record,
    )

    project_root = _create_project(tmp_path)
    assert _answer(project_root, "available").returncode == 0
    answer = load_yaozh_access_record(project_root)
    assert answer is not None
    answer_digest = __import__("hashlib").sha256(
        (project_root / RECORD_RELATIVE_PATH).read_bytes()
    ).hexdigest()
    observation = YaozhSessionObservation(
        project_id=answer.project_id,
        answer_digest=answer_digest,
        observed_at=datetime(2026, 9, 5, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        host="hermes",
        observer_id="hermes-browser-adapter",
        origin="https://vip.yaozh.com",
        technical_state=technical_state,
        page_marker_sha256="b" * 64,
    )

    receipt = build_yaozh_route_access_receipt(answer, observation)

    assert receipt.technical_state == technical_state
    assert receipt.result_class != "ready"
    assert receipt.blocks_core_research is False


def test_yaozh_session_observation_rejects_foreign_origin_secrets_and_local_paths() -> None:
    from pydantic import ValidationError

    from ci_workflow.application.yaozh_access import YaozhSessionObservation

    base = {
        "project_id": "project-1",
        "answer_digest": "a" * 64,
        "observed_at": "2026-09-05T20:00:00+08:00",
        "host": "omp",
        "observer_id": "omp-browser-adapter",
        "origin": "https://vip.yaozh.com",
        "technical_state": "ready",
        "page_marker_sha256": "b" * 64,
    }
    for payload in (
        {**base, "origin": "https://example.com"},
        {**base, "origin": "http://vip.yaozh.com"},
        {**base, "origin": "https://vip.yaozh.com/member"},
        {**base, "origin": "https://vip.yaozh.com?token=x"},
        {**base, "observer_id": "sessionid-collector"},
        {**base, "cookie": "SESSIONID=secret"},
        {**base, "profile_path": "/Users/example/Edge/Profile"},
    ):
        with pytest.raises(ValidationError):
            YaozhSessionObservation.model_validate(payload)

    with pytest.raises(ValidationError):
        YaozhSessionObservation.model_validate(
            {
                **base,
                "observed_at": (
                    datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(hours=1)
                ).isoformat(),
            }
        )


def test_yaozh_observe_cli_persists_immutable_receipt_and_replays_idempotently(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    assert _answer(project_root, "available").returncode == 0
    answer = _read_record(project_root)
    observation_path = tmp_path / "yaozh-observation.json"
    observation_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_id": answer["project_id"],
                "answer_digest": __import__("hashlib").sha256(
                    (project_root / RECORD_RELATIVE_PATH).read_bytes()
                ).hexdigest(),
                "observed_at": "2026-09-05T21:00:00+08:00",
                "host": "codex",
                "observer_id": "codex-browser-adapter",
                "origin": "https://vip.yaozh.com",
                "technical_state": "ready",
                "page_marker_sha256": "c" * 64,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    first = _run(
        "yaozh", "observe", "--root", str(project_root), "--observation", str(observation_path)
    )
    assert first.returncode == 0, first.stderr
    assert "YAOZH_ROUTE_RECEIPT_RECORDED" in first.stdout
    receipts = tuple((project_root / "state/yaozh-route-access").glob("*.json"))
    assert len(receipts) == 1
    first_bytes = receipts[0].read_bytes()
    first_mtime = receipts[0].stat().st_mtime_ns
    assert not any(token in first_bytes.decode().lower() for token in CREDENTIAL_TOKENS)

    replay = _run(
        "yaozh", "observe", "--root", str(project_root), "--observation", str(observation_path)
    )
    assert replay.returncode == 0, replay.stderr
    assert "YAOZH_ROUTE_RECEIPT_REPLAYED" in replay.stdout
    assert receipts[0].read_bytes() == first_bytes
    assert receipts[0].stat().st_mtime_ns == first_mtime
