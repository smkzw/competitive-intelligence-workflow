from __future__ import annotations

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


def test_preflight_checks_native_pdf_for_selected_pdf_output(tmp_path: Path) -> None:
    matrix = _run(
        tmp_path,
        blocked=("native_pdf",),
        outputs=("html", "pdf"),
    )
    states = {(item.report, item.output): item.state for item in matrix.deliveries}
    assert all(states[(report, "html")] == "ready" for report in ("A", "B"))
    assert all(states[(report, "pdf")] == "blocked" for report in ("A", "B"))
    assert matrix.capability("html_ppt_runtime").state == "not_applicable"


def test_preflight_checks_html_ppt_runtime_for_selected_html_ppt_output(
    tmp_path: Path,
) -> None:
    matrix = _run(
        tmp_path,
        blocked=("html_ppt_runtime",),
        outputs=("html", "html-ppt"),
    )
    states = {(item.report, item.output): item.state for item in matrix.deliveries}
    assert all(states[(report, "html")] == "ready" for report in ("A", "B"))
    assert all(states[(report, "html-ppt")] == "blocked" for report in ("A", "B"))


def test_preflight_checks_ppt_master_and_powerpoint_for_selected_pptx_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix = _run(
        tmp_path,
        blocked=("ppt_master",),
        outputs=("html", "pdf", "pptx"),
    )
    assert matrix.capability("ppt_master").state == "blocked"
    assert matrix.capability("office_renderer").state == "ready"
    states = {(item.report, item.output): item.state for item in matrix.deliveries}
    assert all(states[(report, "html")] == "ready" for report in ("A", "B"))
    assert all(states[(report, "pdf")] == "ready" for report in ("A", "B"))
    assert all(states[(report, "pptx")] == "blocked" for report in ("A", "B"))
    assert any(
        "可编辑 PPTX" in message and "不受影响" in message
        for message in matrix.user_messages
    )

    from ci_workflow.application import capability_preflight
    from ci_workflow.application.capability_preflight import RuntimeCapabilityProbe

    monkeypatch.delenv("CI_WORKFLOW_OFFICE_COMMAND", raising=False)
    monkeypatch.setattr(
        capability_preflight.Path,
        "exists",
        lambda path: str(path).endswith("LibreOffice.app"),
    )
    monkeypatch.setattr(
        capability_preflight.shutil,
        "which",
        lambda command: "/usr/local/bin/soffice" if command == "soffice" else None,
    )
    office = RuntimeCapabilityProbe().check("office_renderer", project_root=tmp_path)
    assert office.available is False


def test_environment_recovery_requeues_only_failed_capability_and_downstream_nodes(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import plan_environment_recovery

    before = _run(
        tmp_path,
        blocked=("ppt_master",),
        outputs=("html", "pdf", "pptx"),
    )
    after = _run(tmp_path, outputs=("html", "pdf", "pptx"))
    recovery = plan_environment_recovery(before, after)
    assert recovery.repaired_capability_ids == ("ppt_master",)
    assert set(recovery.requeue_node_ids) == {
        "render:A:pptx",
        "render:B:pptx",
        "verify:A:pptx",
        "verify:B:pptx",
    }
    assert all("html" not in node and "pdf" not in node for node in recovery.requeue_node_ids)

    still_blocked = _run(
        tmp_path,
        blocked=("office_renderer",),
        outputs=("html", "pptx"),
    )
    both_blocked = _run(
        tmp_path,
        blocked=("ppt_master", "office_renderer"),
        outputs=("html", "pptx"),
    )
    not_yet_requeued = plan_environment_recovery(both_blocked, still_blocked)
    assert not_yet_requeued.repaired_capability_ids == ("ppt_master",)
    assert not_yet_requeued.requeue_node_ids == ()

    research_before = _run(
        tmp_path,
        blocked=("http_network",),
        outputs=("html", "pdf"),
    )
    research_after = _run(tmp_path, outputs=("html", "pdf"))
    research_recovery = plan_environment_recovery(research_before, research_after)
    assert research_recovery.repaired_capability_ids == ("http_network",)
    assert set(research_recovery.requeue_node_ids) == {
        "research:A",
        "analyze:A",
        "snapshot:A",
        "render:A:html",
        "verify:A:html",
        "render:A:pdf",
        "verify:A:pdf",
        "research:B",
        "analyze:B",
        "snapshot:B",
        "render:B:html",
        "verify:B:html",
        "render:B:pdf",
        "verify:B:pdf",
    }
