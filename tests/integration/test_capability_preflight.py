from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _selection(
    *,
    outputs: tuple[str, ...] = ("html",),
    source_routes: tuple[str, ...] = ("public-http", "public-browser"),
    needs_document_ingestion: bool = True,
    needs_ocr: bool = False,
) -> object:
    from ci_workflow.application.capability_preflight import CapabilitySelection

    return CapabilitySelection(
        reports=("A", "B"),
        outputs=outputs,
        source_routes=source_routes,
        needs_document_ingestion=needs_document_ingestion,
        needs_ocr=needs_ocr,
    )


def test_optional_authenticated_browser_failure_never_blocks_core_research(
    tmp_path: Path,
) -> None:
    matrix = _run(
        tmp_path,
        blocked=("login_browser",),
        source_routes=("public-http", "public-browser", "authenticated-browser"),
        needs_document_ingestion=False,
    )

    login = matrix.capability("login_browser")
    assert login.state == "blocked"
    assert login.required_by == ()
    assert matrix.overall_state == "ready"
    assert all(item.state == "ready" for item in matrix.research)
    assert all(item.state == "ready" for item in matrix.deliveries)
    assert any("药智网可选路线" in item and "自行登录" in item for item in matrix.user_messages)


def test_runtime_probe_does_not_equate_blank_chromium_with_logged_in_session(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import RuntimeCapabilityProbe

    outcome = RuntimeCapabilityProbe().check("login_browser", project_root=tmp_path)

    assert outcome.available is False
    assert "会话" in outcome.detail


def test_runtime_independent_context_requires_an_executed_probe_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ci_workflow.application.capability_preflight import RuntimeCapabilityProbe

    monkeypatch.setenv("CI_WORKFLOW_INDEPENDENT_CONTEXT", "1")
    blocked = RuntimeCapabilityProbe().check("independent_context", project_root=tmp_path)
    assert blocked.available is False
    assert "子Agent" in blocked.user_action
    assert "独立会话" in blocked.user_action
    assert "兼容执行器" in blocked.user_action

    probe = tmp_path / "independent-context-probe"
    probe.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' '"
        + json.dumps(
            {
                "schema_version": "1.0",
                "available": True,
                "mechanism": "independent_session",
                "producer_context": "producer-1",
                "reviewer_context": "reviewer-2",
                "invocation_id": "probe-run-001",
            }
        )
        + "'\n",
        encoding="utf-8",
    )
    os.chmod(probe, 0o700)

    ready = RuntimeCapabilityProbe(independent_context_probe=probe).check(
        "independent_context", project_root=tmp_path
    )
    assert ready.available is True
    assert "probe-run-001" in ready.detail


def test_project_selection_consumes_available_yaozh_answer_only(tmp_path: Path) -> None:
    from ci_workflow.application.capability_preflight import selection_from_project
    from ci_workflow.application.project_service import create_project_workspace
    from ci_workflow.application.yaozh_access import answer_yaozh_access
    from ci_workflow.domain.contracts import create_project_contract

    def project(name: str, answer: str) -> Path:
        contract = create_project_contract(
            indication="重度哮喘", reports=["A"], outputs=["html"]
        )
        root = create_project_workspace(tmp_path / name, contract)
        answer_yaozh_access(root, answer)
        return root

    available = selection_from_project(project("available", "available"))
    unavailable = selection_from_project(project("unavailable", "unavailable"))
    skipped = selection_from_project(project("skipped", "skipped"))

    assert "authenticated-browser" in available.source_routes
    assert "authenticated-browser" not in unavailable.source_routes
    assert "authenticated-browser" not in skipped.source_routes


def _run(tmp_path: Path, *, blocked: tuple[str, ...] = (), **selection: object) -> object:
    from ci_workflow.application.capability_preflight import (
        StaticCapabilityProbe,
        run_capability_preflight,
    )

    return run_capability_preflight(
        _selection(**selection),
        host="local",
        probe=StaticCapabilityProbe(blocked=blocked),
        project_root=tmp_path,
    )


def test_preflight_checks_project_file_io_and_script_runtime(tmp_path: Path) -> None:
    matrix = _run(tmp_path, blocked=("project_file_io",))
    assert matrix.capability("project_file_io").state == "blocked"
    assert matrix.capability("script_runtime").state == "ready"
    assert all(item.state == "blocked" for item in matrix.research)
    assert all(item.state == "blocked" for item in matrix.deliveries)
    assert any("项目文件" in message and "请" in message for message in matrix.user_messages)


def test_preflight_checks_http_and_browser_only_for_selected_source_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http_only = _run(
        tmp_path,
        source_routes=("public-http",),
        needs_document_ingestion=False,
    )
    assert http_only.capability("http_network").state == "ready"
    assert http_only.capability("search_browser").state == "not_applicable"
    assert http_only.capability("login_browser").state == "not_applicable"

    authenticated = _run(
        tmp_path,
        source_routes=("public-http", "public-browser", "authenticated-browser"),
        needs_document_ingestion=False,
    )
    assert authenticated.capability("http_network").state == "ready"
    assert authenticated.capability("search_browser").state == "ready"
    assert authenticated.capability("login_browser").state == "ready"

    from ci_workflow.application import capability_preflight
    from ci_workflow.application.capability_preflight import RuntimeCapabilityProbe

    class _Response:
        status = 200

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    attempts = 0
    delays: list[float] = []

    def flaky_urlopen(*args: object, **kwargs: object) -> _Response:
        nonlocal attempts
        del args, kwargs
        attempts += 1
        if attempts < 3:
            raise TimeoutError("模拟短暂超时")
        return _Response()

    monkeypatch.setattr(capability_preflight, "urlopen", flaky_urlopen)
    monkeypatch.setattr(capability_preflight.time, "sleep", delays.append)
    outcome = RuntimeCapabilityProbe().check("http_network", project_root=tmp_path)
    assert outcome.available is True
    assert attempts == 3
    assert delays == [0.25, 0.5]

    attempts = 0
    delays.clear()

    def unavailable_urlopen(*args: object, **kwargs: object) -> _Response:
        nonlocal attempts
        del args, kwargs
        attempts += 1
        raise OSError("模拟持续不可达")

    monkeypatch.setattr(capability_preflight, "urlopen", unavailable_urlopen)
    blocked_outcome = RuntimeCapabilityProbe().check(
        "http_network", project_root=tmp_path
    )
    assert blocked_outcome.available is False
    assert attempts == 3
    assert delays == [0.25, 0.5]
    assert "连续 3 次" in blocked_outcome.detail

    from ci_workflow.application.capability_preflight import (
        ProbeOutcome,
        run_capability_preflight,
    )

    class _BlockedNetworkProbe:
        def check(self, capability_id: str, *, project_root: Path) -> ProbeOutcome:
            del project_root
            if capability_id == "http_network":
                return blocked_outcome
            return ProbeOutcome(
                available=True,
                detail="已确认可用",
                user_action="无需处理",
            )

    blocked_matrix = run_capability_preflight(
        _selection(source_routes=("public-http",), needs_document_ingestion=False),
        host="local",
        probe=_BlockedNetworkProbe(),
        project_root=tmp_path,
    )
    assert any("连续 3 次" in message for message in blocked_matrix.user_messages)


def test_preflight_checks_pdf_document_and_ocr_only_when_required(tmp_path: Path) -> None:
    no_documents = _run(tmp_path, needs_document_ingestion=False)
    assert no_documents.capability("document_ingestion").state == "not_applicable"
    assert no_documents.capability("ocr").state == "not_applicable"

    text_pdf = _run(tmp_path, needs_document_ingestion=True, needs_ocr=False)
    assert text_pdf.capability("document_ingestion").state == "ready"
    assert text_pdf.capability("ocr").state == "not_applicable"

    scanned_pdf = _run(
        tmp_path,
        blocked=("ocr",),
        needs_document_ingestion=True,
        needs_ocr=True,
    )
    assert scanned_pdf.capability("document_ingestion").state == "ready"
    assert scanned_pdf.capability("ocr").state == "blocked"
    assert all(item.state == "blocked" for item in scanned_pdf.research)


def test_preflight_checks_real_browser_for_selected_html_outputs(tmp_path: Path) -> None:
    matrix = _run(tmp_path, blocked=("browser_validation",), outputs=("html",))
    assert matrix.capability("browser_validation").state == "blocked"
    assert all(item.state == "ready" for item in matrix.research)
    assert {item.output: item.state for item in matrix.deliveries} == {"html": "blocked"}


def test_preflight_rejects_non_html_outputs(tmp_path: Path) -> None:
    del tmp_path
    for outputs in (("html", "pdf"), ("html", "html-ppt"), ("html", "pptx")):
        with pytest.raises(ValueError, match="html"):
            _selection(outputs=outputs)


def test_non_html_runtime_capabilities_are_absent_from_release_matrix(tmp_path: Path) -> None:
    matrix = _run(tmp_path)
    capability_ids = {item.capability_id for item in matrix.capabilities}
    assert capability_ids.isdisjoint(
        {"native_pdf", "html_ppt_runtime", "ppt_master", "office_renderer"}
    )


def test_environment_recovery_requeues_only_failed_capability_and_downstream_nodes(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import plan_environment_recovery

    before = _run(tmp_path, blocked=("browser_validation",))
    after = _run(tmp_path)
    recovery = plan_environment_recovery(before, after)
    assert recovery.repaired_capability_ids == ("browser_validation",)
    assert set(recovery.requeue_node_ids) == {
        "render:A:html",
        "render:B:html",
        "verify:A:html",
        "verify:B:html",
    }

    research_before = _run(tmp_path, blocked=("http_network",))
    research_after = _run(tmp_path)
    research_recovery = plan_environment_recovery(research_before, research_after)
    assert research_recovery.repaired_capability_ids == ("http_network",)
    assert set(research_recovery.requeue_node_ids) == {
        "research:A",
        "analyze:A",
        "snapshot:A",
        "render:A:html",
        "verify:A:html",
        "research:B",
        "analyze:B",
        "snapshot:B",
        "render:B:html",
        "verify:B:html",
    }
