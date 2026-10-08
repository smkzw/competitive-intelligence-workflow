from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import ci_workflow.application.user_fact_edit as user_fact_edit_module
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    UserFactEditService,
    UserFactSaveConflictError,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_w04_user_fact_edit import (
    PROJECT_ID,
    LoopbackEditServer,
    _project,
    _request_http,
)
from tests.integration.test_w04_user_fact_edit import (
    _command as _fact_save_command,
)

_HISTORY_TABLES = (
    "current_delivery_generations",
    "current_delivery_state",
    "user_fact_edit_requests",
    "user_fact_derivations",
    "fact_versions",
    "fact_evidence",
    "evidence_fragments",
    "source_versions",
    "source_portal_consumer_bindings",
)


def _snapshot(root: Path, service: UserFactEditService) -> dict[str, Any]:
    with open_database(root / "state/project.sqlite") as database:
        rows = {
            table: tuple(database.execute(f"SELECT * FROM {table} ORDER BY rowid"))
            for table in _HISTORY_TABLES
        }
    reports = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "reports").rglob("*"))
        if path.is_file()
    }
    journals = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "state/user-fact-transactions").glob("*.json"))
    }
    return {
        "database": rows,
        "reports": reports,
        "journals": journals,
        "events": service.event_store.path.read_bytes(),
    }


def _committed_then_later_save(
    tmp_path: Path,
) -> tuple[Path, UserFactEditService, Any, Any, Any]:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    original_command = _fact_save_command(request_id="historical-replay-original")
    original_result = service.save(original_command)
    later_result = service.save(
        _fact_save_command(
            request_id="historical-replay-later",
            expected_revision=1,
            fact_version_id=original_result.fact_version_id,
            edits=FactEdit(numerator=26, denominator=80),
        )
    )
    return root, service, original_command, original_result, later_result


def test_exact_historical_retry_after_later_save_clear_and_undo_returns_original_result(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    original_command = _fact_save_command(request_id="historical-replay-original")
    original_result = service.save(original_command)
    assert original_result.project_id == PROJECT_ID
    assert original_result.revision == 1

    cleared = service.save(
        _fact_save_command(
            request_id="historical-replay-clear",
            expected_revision=1,
            fact_version_id=original_result.fact_version_id,
            edits=FactEdit(numerator=None),
        )
    )
    restored = service.save(
        _fact_save_command(
            request_id="historical-replay-later-save",
            expected_revision=2,
            fact_version_id=cleared.fact_version_id,
            edits=FactEdit(numerator=24, denominator=62),
        )
    )
    undone = service.save(
        _fact_save_command(
            request_id="historical-replay-undo",
            expected_revision=3,
            fact_version_id=restored.fact_version_id,
            edits=FactEdit(),
            operation="undo",
        )
    )
    later_current = service.read_current_delivery()
    assert undone.revision == 4
    assert later_current.request_id == "historical-replay-undo"
    before = _snapshot(root, service)

    replayed = service.save(original_command)

    assert replayed == original_result
    assert service.read_current_delivery() == later_current
    assert _snapshot(root, service) == before

    with pytest.raises(UserFactSaveConflictError, match="不同保存载荷"):
        service.save(
            original_command.model_copy(
                update={"edits": FactEdit(numerator=23, denominator=80)}
            )
        )
    assert service.read_current_delivery() == later_current
    assert _snapshot(root, service) == before


def test_loopback_http_replays_historical_save_without_current_rollback(
    tmp_path: Path,
) -> None:
    root, service, command, original_result, later_result = _committed_then_later_save(
        tmp_path
    )
    later_current = service.read_current_delivery()
    assert later_current.revision == later_result.revision
    with LoopbackEditServer(service) as server:
        good_host = f"127.0.0.1:{server.port}"
        status, headers, _ = _request_http(
            server, "GET", "/", headers={"Host": good_host}
        )
        assert status == 200
        cookie = headers["set-cookie"].split(";", 1)[0]
        csrf = headers["x-csrf-token"]
        before = _snapshot(root, service)
        status, _, payload = _request_http(
            server,
            "POST",
            "/api/save",
            body=command.model_dump_json(exclude_unset=True).encode(),
            headers={
                "Host": good_host,
                "Origin": f"http://{good_host}",
                "Cookie": cookie,
                "X-CSRF-Token": csrf,
                "Content-Type": "application/json",
            },
        )
        assert status == 200
        response = json.loads(payload)
        assert response["request_id"] == original_result.request_id
        assert response["revision"] == original_result.revision
        assert response["current_generation_sha256"] == (
            original_result.current_generation_sha256
        )
        assert service.read_current_delivery() == later_current
        assert _snapshot(root, service) == before


@pytest.mark.parametrize(
    "corruption",
    (
        "ledger_project",
        "ledger_request",
        "ledger_revision",
        "ledger_bundle_digest",
        "generation_bytes",
        "journal_phase",
        "journal_request",
        "result_project",
        "result_revision",
        "result_fact",
        "result_digest",
        "request_project",
    ),
)
def test_historical_retry_rejects_corrupt_commit_or_result_identity_without_writes(
    tmp_path: Path,
    corruption: str,
) -> None:
    root, service, command, result, later_result = _committed_then_later_save(tmp_path)
    generation_path = root / "reports/generations" / f"{result.current_generation_sha256}.json"
    journal_path = root / "state/user-fact-transactions" / (
        f"{hashlib.sha256(command.request_id.encode()).hexdigest()}.json"
    )
    with open_database(root / "state/project.sqlite") as database:
        request_row = database.execute(
            "SELECT result_json FROM user_fact_edit_requests WHERE request_id=?",
            (command.request_id,),
        ).fetchone()
        assert request_row is not None
        result_json = json.loads(str(request_row[0]))
        if corruption in {
            "ledger_project",
            "ledger_request",
            "ledger_revision",
            "ledger_bundle_digest",
        }:
            database.execute("DROP TRIGGER current_delivery_generations_no_update")
            if corruption == "ledger_project":
                database.execute(
                    "UPDATE current_delivery_generations SET project_id=? "
                    "WHERE generation_sha256=?",
                    ("wrong-project", result.current_generation_sha256),
                )
            elif corruption == "ledger_request":
                database.execute(
                    "UPDATE current_delivery_generations SET request_id=? "
                    "WHERE generation_sha256=?",
                    ("wrong-request", result.current_generation_sha256),
                )
            elif corruption == "ledger_revision":
                database.execute(
                    "UPDATE current_delivery_generations SET revision=? WHERE generation_sha256=?",
                    (result.revision + 1, result.current_generation_sha256),
                )
            else:
                ledger_bundle = database.execute(
                    "SELECT bundle_json FROM current_delivery_generations "
                    "WHERE generation_sha256=?",
                    (result.current_generation_sha256,),
                ).fetchone()
                assert ledger_bundle is not None
                database.execute(
                    "UPDATE current_delivery_generations SET bundle_json=? "
                    "WHERE generation_sha256=?",
                    (str(ledger_bundle[0]) + " ", result.current_generation_sha256),
                )
        elif corruption == "request_project":
            database.execute("DROP TRIGGER user_fact_edit_requests_no_update")
            database.execute(
                "UPDATE user_fact_edit_requests SET project_id=? WHERE request_id=?",
                ("wrong-project", command.request_id),
            )
        elif corruption.startswith("result_"):
            database.execute("DROP TRIGGER user_fact_edit_requests_no_update")
            field = corruption.removeprefix("result_")
            if field == "project":
                result_json["project_id"] = "wrong-project"
            elif field == "revision":
                result_json["revision"] = result.revision + 1
            elif field == "fact":
                result_json["fact_version_id"] = "wrong-fact-version"
            else:
                result_json["current_generation_sha256"] = "0" * 64
            database.execute(
                "UPDATE user_fact_edit_requests SET result_json=? WHERE request_id=?",
                (json.dumps(result_json, ensure_ascii=False, separators=(",", ":")),
                 command.request_id),
            )
    if corruption == "generation_bytes":
        generation_path.write_bytes(generation_path.read_bytes() + b"corrupt")
    elif corruption.startswith("journal_"):
        journal = json.loads(journal_path.read_bytes())
        if corruption == "journal_phase":
            journal["phase"] = "prepared"
        else:
            journal["request_id"] = "wrong-request"
        journal_path.write_text(json.dumps(journal, ensure_ascii=False) + "\n", encoding="utf-8")

    later_current = service.read_current_delivery()
    assert later_current.revision == later_result.revision
    before = _snapshot(root, service)

    with pytest.raises(UserFactSaveConflictError):
        service.save(command)

    assert service.read_current_delivery() == later_current
    assert _snapshot(root, service) == before


def test_ready_journal_without_committed_ledger_is_not_accepted_and_exact_retry_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    command = _fact_save_command(request_id="ready-without-generation")

    def fail_publish(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected pre-selector publication failure")

    monkeypatch.setattr(user_fact_edit_module, "publish_current_delivery", fail_publish)
    with pytest.raises(OSError, match="pre-selector publication"):
        service.save(command)

    journal_path = root / "state/user-fact-transactions" / (
        f"{hashlib.sha256(command.request_id.encode()).hexdigest()}.json"
    )
    journal = json.loads(journal_path.read_bytes())
    assert journal["phase"] == "ready"
    with open_database(root / "state/project.sqlite") as database:
        request = database.execute(
            "SELECT status,result_fact_version_id,result_revision,result_json "
            "FROM user_fact_edit_requests WHERE request_id=?",
            (command.request_id,),
        ).fetchone()
        assert request is not None and request[0] == "complete"
        result = json.loads(str(request[3]))
        assert result["request_id"] == command.request_id
        assert result["revision"] == request[2] == 1
        generation_count = database.execute(
            "SELECT count(*) FROM current_delivery_generations WHERE request_id=?",
            (command.request_id,),
        ).fetchone()[0]
    assert generation_count == 0
    assert service.read_current_delivery().revision == 0

    monkeypatch.undo()
    recovered = service.save(command)

    assert recovered.revision == 1
    assert service.read_current_delivery().request_id == command.request_id
