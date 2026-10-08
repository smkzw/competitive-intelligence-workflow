"""Presentation-only current rebuild family on labelled synthetic fixtures.

This is not browser, source-science, clinical, or release acceptance. Every
clinical value comes from the shared synthetic fixture; the family proves the
presentation-only transaction semantics and their fail-closed negatives.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

import pytest

import ci_workflow.application.latest_delivery as latest_delivery_module
import ci_workflow.application.user_fact_edit as user_fact_edit_module
from ci_workflow.application.latest_delivery import (
    CurrentDeliveryBundle,
    CurrentReportDelivery,
    current_bundle_sha256,
)
from ci_workflow.application.share_export import (
    ShareViewSelection,
    export_current_html_share,
)
from ci_workflow.application.user_fact_edit import (
    CurrentDeliveryConflictError,
    CurrentPresentationRebuildCommand,
    FactEdit,
    PresentationRebuildConflictError,
    UserFactEditService,
    _presentation_render_source_digest,
    _presentation_selection,
    _presentation_source_files,
)
from ci_workflow.cli import main as cli_main
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_w04_user_fact_edit import (
    NOW,
    PROJECT_ID,
    _project,
    _projection,
)
from tests.integration.test_w04_user_fact_edit import (
    _command as _fact_save_command,
)

FROZEN_TABLES = (
    "fact_versions",
    "fact_evidence",
    "evidence_fragments",
    "source_versions",
    "source_portal_consumer_bindings",
    "user_fact_derivations",
    "user_fact_edit_requests",
)
_PRESENTATION_SOURCE_EVENT = "user.presentation.render.source"
_PRESENTATION_CANDIDATE_EVENT = "user.presentation.rebuilt"


def _command(
    *,
    request_id: str = "presentation-r1",
    expected_revision: int = 0,
    reports: tuple[Literal["A", "B", "C"], ...] | None = ("A", "B"),
    project_id: str = PROJECT_ID,
    requested_by: str = "medical-user",
    requested_at: datetime = NOW,
) -> CurrentPresentationRebuildCommand:
    return CurrentPresentationRebuildCommand(
        request_id=request_id,
        project_id=project_id,
        expected_revision=expected_revision,
        reports=reports,
        requested_by=requested_by,
        requested_at=requested_at,
    )


def _frozen_tables(root: Path) -> dict[str, tuple[tuple[object, ...], ...]]:
    with open_database(root / "state/project.sqlite") as database:
        return {
            name: tuple(database.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall())
            for name in FROZEN_TABLES
        }


def _clinical_view(payload: dict[str, object]) -> dict[str, object]:
    """Payload with the source-display column removed from every domain row.

    The initial synthetic fixture sites were rendered without an active-fact
    projection; a rebuilt site displays the committed source quote in
    ``source_text`` exactly like every other existing rebuild path.
    """
    view: dict[str, object] = {}
    for key, value in payload.items():
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and "row_id" in value[0]
        ):
            view[key] = [
                {field: item for field, item in row.items() if field != "source_text"}
                for row in value
                if isinstance(row, dict)
            ]
        else:
            view[key] = value
    return view


def _register_tampered_binding(root: Path) -> None:
    """Declare a source consumer binding whose digest does not verify."""
    with open_database(root / "state/project.sqlite") as database:
        database.execute(
            "INSERT INTO source_portal_consumer_bindings "
            "(binding_id,source_fact_version_id,evidence_snapshot_id,report,collection,"
            "row_id,binding_json,binding_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "tampered-presentation-binding",
                "fact-crude-rate-v1",
                "synthetic-snapshot",
                "B",
                "safety",
                "safe-apply-t-1",
                "{}",
                "0" * 64,
                NOW.isoformat(),
            ),
        )


def _version_dirs(root: Path, report: str) -> list[str]:
    return sorted(path.name for path in (root / "reports" / report).iterdir())


def _report_payload(payload: bytes, report: str) -> dict[str, object]:
    text = payload.decode("utf-8")
    prefix = f"window.REPORT_{report}="
    assert text.startswith(prefix) and text.endswith(";\n")
    parsed = json.loads(text[len(prefix) : -2])
    assert isinstance(parsed, dict)
    return parsed


def test_presentation_rebuild_ab_legal_fixture_preserves_clinical_content(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    before_payloads = {kind: _projection(root, kind) for kind in ("A", "B", "C")}
    before_tables = _frozen_tables(root)
    before_reports = {item.report: item for item in before.reports}

    result = service.rebuild_current_presentation(_command())

    assert result.revision == 1
    assert {item.report: item.revision for item in result.reports} == {"A": 1, "B": 1, "C": 0}
    assert next(item for item in result.reports if item.report == "C") == before_reports["C"]
    assert result.active_fact_version_ids == before.active_fact_version_ids
    assert result.fact_revision_digest == before.fact_revision_digest
    for kind in ("A", "B"):
        rebuilt = next(item for item in result.reports if item.report == kind)
        pinned = before_reports[kind]
        assert rebuilt.report_version == "v1-presentation-r1"
        assert rebuilt.site_relative_path == f"reports/{kind}/v1-presentation-r1/html"
        assert rebuilt.builder_input_relative_path == pinned.builder_input_relative_path
        assert rebuilt.builder_input_sha256 == pinned.builder_input_sha256
        assert rebuilt.fact_version_ids == pinned.fact_version_ids
        assert rebuilt.fact_revision_digest == pinned.fact_revision_digest
        manifest_relative = rebuilt.transaction_manifest_relative_path
        assert manifest_relative is not None
        assert (root / manifest_relative).is_file()
        new_site = root / rebuilt.site_relative_path
        old_site = root / pinned.site_relative_path
        assert (new_site / "data/identity-projection.json").read_bytes() == (
            old_site / "data/identity-projection.json"
        ).read_bytes()
        # A is the only portal that pins a public render context; it must be
        # re-read from the previous hash-bound site, never re-guessed.
        if kind == "A":
            assert (new_site / "data/render-context.json").read_bytes() == (
                old_site / "data/render-context.json"
            ).read_bytes()
            assert rebuilt.file_hashes["data/render-context.json"] == pinned.file_hashes[
                "data/render-context.json"
            ]
        assert _clinical_view(_projection(root, kind)) == _clinical_view(before_payloads[kind])
        old_page = (old_site / "safety.html").read_text(encoding="utf-8")
        new_page = (new_site / "safety.html").read_text(encoding="utf-8")
        assert 'data-current-revision="0"' in old_page
        assert 'data-current-revision="1"' in new_page

    with open_database(root / "state/project.sqlite") as database:
        committed_quote = database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id='fragment-count'"
        ).fetchone()
    assert committed_quote is not None
    safety_rows = _projection(root, "A")["safety"]
    assert isinstance(safety_rows, list)
    rebuilt_a_row = next(
        row for row in safety_rows if row["row_id"] == "safe-apply-t-1"
    )
    # The rebuilt A site displays the committed source quote, never an edit.
    assert rebuilt_a_row["source_text"] == committed_quote[0]

    assert _frozen_tables(root) == before_tables
    events = service.event_store.read_all()
    assert [event.event_type for event in events] == [
        _PRESENTATION_SOURCE_EVENT,
        _PRESENTATION_CANDIDATE_EVENT,
    ]
    candidate = events[1].payload["candidate"]
    assert CurrentDeliveryBundle.model_validate(candidate).model_dump() == result.model_dump()
    assert service.read_current_delivery() == result


def test_presentation_rebuild_c_only_and_default_abc_keep_unselected_deliveries(
    tmp_path: Path,
) -> None:
    c_root, _ = _project(tmp_path / "c-only")
    c_service = UserFactEditService(c_root)
    before = c_service.read_current_delivery()
    before_c = _projection(c_root, "C")

    c_result = c_service.rebuild_current_presentation(
        _command(request_id="presentation-c", reports=("C",))
    )

    assert {item.report: item.revision for item in c_result.reports} == {"A": 0, "B": 0, "C": 1}
    for kind in ("A", "B"):
        assert next(item for item in c_result.reports if item.report == kind) == next(
            item for item in before.reports if item.report == kind
        )
    c_delivery = next(item for item in c_result.reports if item.report == "C")
    c_site = c_root / c_delivery.site_relative_path
    assert json.loads((c_site / "data/research-status.json").read_bytes()) == {
        "schema_version": "1.0",
        "report": "C",
        "delivery_status": "design_gate_passed",
    }
    assert _clinical_view(_projection(c_root, "C")) == _clinical_view(before_c)

    abc_root, _ = _project(tmp_path / "abc")
    abc_service = UserFactEditService(abc_root)
    abc_before = abc_service.read_current_delivery()
    abc_payloads = {kind: _projection(abc_root, kind) for kind in ("A", "B", "C")}

    abc = abc_service.rebuild_current_presentation(
        _command(request_id="presentation-abc", reports=None)
    )

    assert abc.revision == 1
    assert {item.report: item.revision for item in abc.reports} == {"A": 1, "B": 1, "C": 1}
    assert abc.active_fact_version_ids == abc_before.active_fact_version_ids
    assert abc.fact_revision_digest == abc_before.fact_revision_digest
    assert {
        kind: _clinical_view(_projection(abc_root, kind)) for kind in ("A", "B", "C")
    } == {kind: _clinical_view(payload) for kind, payload in abc_payloads.items()}


def test_presentation_rebuild_preflights_all_selected_before_any_staging(
    tmp_path: Path,
) -> None:
    # The default fixture binds A and B to different facts, so the tampered
    # source declaration can break the later report (B) while A stays valid.
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    pointer = root / "reports/current.json"
    before_pointer = pointer.read_bytes()
    before = service.read_current_delivery()
    _register_tampered_binding(root)

    with pytest.raises(PresentationRebuildConflictError, match="B类报告预检"):
        service.rebuild_current_presentation(_command(request_id="presentation-preflight"))

    assert not (root / "reports/A/v1-presentation-r1").exists()
    assert not (root / "reports/B/v1-presentation-r1").exists()
    assert pointer.read_bytes() == before_pointer
    assert service.read_current_delivery() == before


def test_presentation_rebuild_failure_after_a_then_exact_retry_reuses_staged_a(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    pointer = root / "reports/current.json"
    before_pointer = pointer.read_bytes()
    command = _command(request_id="presentation-retry")

    def interrupt(report: str) -> None:
        if report == "A":
            raise OSError("synthetic presentation interruption")

    service._after_report_built = interrupt
    with pytest.raises(OSError, match="presentation interruption"):
        service.rebuild_current_presentation(command)
    assert pointer.read_bytes() == before_pointer
    assert service.read_current_delivery() == before
    staged_manifest = root / "reports/A/v1-presentation-r1/html.manifest.json"
    assert staged_manifest.is_file()
    staged_bytes = staged_manifest.read_bytes()
    assert not (root / "reports/B/v1-presentation-r1").exists()

    service._after_report_built = lambda _report: None
    result = service.rebuild_current_presentation(command)

    assert result.revision == 1
    assert {item.report: item.revision for item in result.reports} == {"A": 1, "B": 1, "C": 0}
    assert staged_manifest.read_bytes() == staged_bytes
    assert _version_dirs(root, "A") == ["v1", "v1-presentation-r1"]
    assert _version_dirs(root, "B") == ["v1", "v1-presentation-r1"]
    assert service.read_current_delivery() == result


def test_presentation_rebuild_refuses_renderer_drift_without_mixing_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    command = _command(request_id="presentation-drift")

    def interrupt(report: str) -> None:
        if report == "A":
            raise OSError("synthetic drift setup interruption")

    service._after_report_built = interrupt
    with pytest.raises(OSError, match="drift setup interruption"):
        service.rebuild_current_presentation(command)
    service._after_report_built = lambda _report: None
    staged_manifest = root / "reports/A/v1-presentation-r1/html.manifest.json"
    staged_bytes = staged_manifest.read_bytes()

    monkeypatch.setattr(
        user_fact_edit_module, "_presentation_render_source_digest", lambda: "f" * 64
    )
    with pytest.raises(PresentationRebuildConflictError, match="呈现资源已变化"):
        service.rebuild_current_presentation(command)
    assert staged_manifest.read_bytes() == staged_bytes
    assert service.read_current_delivery() == before
    assert not (root / "reports/B/v1-presentation-r1").exists()

    monkeypatch.undo()
    result = service.rebuild_current_presentation(command)
    assert result.revision == 1
    assert staged_manifest.read_bytes() == staged_bytes
    assert {item.report: item.revision for item in result.reports} == {"A": 1, "B": 1, "C": 0}


@pytest.mark.parametrize("fault", ("journal_commit", "selector"))
def test_presentation_rebuild_recovers_recorded_candidate_without_rerendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    pointer = root / "reports/current.json"
    before_pointer = pointer.read_bytes()
    command = _command(request_id=f"presentation-{fault}")
    if fault == "journal_commit":
        original_commit = latest_delivery_module.commit_current_transaction
        failed = False

        def fail_commit_once(
            project_root: Path, *, request_id: str, candidate: CurrentDeliveryBundle
        ) -> object:
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected journal commit failure")
            return original_commit(project_root, request_id=request_id, candidate=candidate)

        monkeypatch.setattr(
            "ci_workflow.application.user_fact_edit.commit_current_transaction",
            fail_commit_once,
        )
    else:
        original_publish = latest_delivery_module.publish_current_delivery
        failed = False

        def fail_publish_once(
            project_root: Path,
            bundle: CurrentDeliveryBundle,
            *,
            expected_revision: int,
        ) -> object:
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected selector failure")
            return original_publish(project_root, bundle, expected_revision=expected_revision)

        monkeypatch.setattr(
            "ci_workflow.application.user_fact_edit.publish_current_delivery",
            fail_publish_once,
        )

    with pytest.raises(OSError, match="injected"):
        service.rebuild_current_presentation(command)
    assert pointer.read_bytes() == before_pointer
    assert service.read_current_delivery().revision == 0
    events = service.event_store.read_all()
    recorded = next(
        event for event in events if event.event_type == _PRESENTATION_CANDIDATE_EVENT
    )
    recorded_bundle = CurrentDeliveryBundle.model_validate(recorded.payload["candidate"])
    version_dirs = _version_dirs(root, "A")

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("recovery must not render a new report version")

    monkeypatch.setattr(user_fact_edit_module, "build_current_report", forbidden)
    recovered = service.rebuild_current_presentation(command)

    committed = service.read_current_delivery()
    assert recovered.revision == 1
    assert committed.revision == 1
    assert current_bundle_sha256(committed) == current_bundle_sha256(recorded_bundle)
    assert current_bundle_sha256(recovered) == current_bundle_sha256(recorded_bundle)
    assert _version_dirs(root, "A") == version_dirs

    replay = service.rebuild_current_presentation(command)
    assert current_bundle_sha256(replay) == current_bundle_sha256(committed)
    assert _version_dirs(root, "A") == version_dirs
    assert len(
        [
            event
            for event in service.event_store.read_all()
            if event.event_type == _PRESENTATION_CANDIDATE_EVENT
        ]
    ) == 1


def test_presentation_rebuild_replay_and_negative_requests_fail_closed(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    command = _command(request_id="presentation-negative")
    first = service.rebuild_current_presentation(command)
    assert first.revision == 1
    committed = service.read_current_delivery()
    pointer = root / "reports/current.json"
    before_pointer = pointer.read_bytes()
    version_dirs = _version_dirs(root, "A")

    replay = service.rebuild_current_presentation(command)
    assert current_bundle_sha256(replay) == current_bundle_sha256(committed)
    assert _version_dirs(root, "A") == version_dirs

    with pytest.raises(PresentationRebuildConflictError, match="同一请求标识对应了不同重建载荷"):
        service.rebuild_current_presentation(
            _command(request_id="presentation-negative", reports=("A",))
        )
    with pytest.raises(PresentationRebuildConflictError, match="版本冲突"):
        service.rebuild_current_presentation(
            _command(request_id="presentation-stale", expected_revision=0)
        )
    with pytest.raises(PresentationRebuildConflictError, match="项目身份"):
        service.rebuild_current_presentation(
            _command(
                request_id="presentation-project",
                expected_revision=1,
                project_id="other-project",
            )
        )
    for update in (
        {"reports": ("A", "A")},
        {"reports": ()},
        {"expected_revision": -1},
        {"requested_at": datetime(2026, 1, 1)},
    ):
        with pytest.raises(ValueError):
            service.rebuild_current_presentation(command.model_copy(update=update))

    assert pointer.read_bytes() == before_pointer
    assert service.read_current_delivery().revision == 1
    assert _version_dirs(root, "A") == version_dirs


def test_presentation_rebuild_detects_tampered_site_without_touching_current(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    entry = next(item for item in service.read_current_delivery().reports if item.report == "A")
    page = root / entry.site_relative_path / "safety.html"
    page.write_bytes(page.read_bytes() + b"<!-- tampered -->")
    pointer = root / "reports/current.json"
    before_pointer = pointer.read_bytes()

    with pytest.raises(CurrentDeliveryConflictError, match="哈希"):
        service.rebuild_current_presentation(_command(request_id="presentation-site-tamper"))

    assert pointer.read_bytes() == before_pointer
    assert not (root / "reports/A/v1-presentation-r1").exists()


def test_presentation_selection_rejects_reports_absent_from_the_current_bundle() -> None:
    fact_digest = hashlib.sha256(
        json.dumps(["fact-crude-rate-v1"], separators=(",", ":")).encode()
    ).hexdigest()
    a_only = CurrentDeliveryBundle(
        project_id=PROJECT_ID,
        revision=0,
        active_fact_version_ids=("fact-crude-rate-v1",),
        fact_revision_digest=fact_digest,
        reports=(
            CurrentReportDelivery(
                report="A",
                revision=0,
                report_version="v1",
                site_relative_path="reports/A/v1/html",
                file_hashes={},
                fact_version_ids=("fact-crude-rate-v1",),
                fact_revision_digest=fact_digest,
            ),
        ),
        created_at=NOW,
    )

    assert _presentation_selection(a_only, None) == ("A",)
    assert _presentation_selection(a_only, ("A",)) == ("A",)
    with pytest.raises(PresentationRebuildConflictError, match="不存在所选报告"):
        _presentation_selection(a_only, ("B",))
    with pytest.raises(PresentationRebuildConflictError, match="不存在所选报告"):
        _presentation_selection(a_only, ("A", "B"))

    with pytest.raises(ValueError):
        CurrentPresentationRebuildCommand(
            request_id="presentation-unknown",
            project_id=PROJECT_ID,
            expected_revision=0,
            reports=("D",),  # type: ignore[arg-type]
            requested_by="medical-user",
            requested_at=NOW,
        )
    with pytest.raises(ValueError, match="不得重复"):
        _command(request_id="presentation-duplicate", reports=("A", "A"))
    with pytest.raises(ValueError, match="不能为空"):
        _command(request_id="presentation-empty", reports=())


def test_presentation_render_source_digest_is_content_bound_and_cache_free(
    tmp_path: Path,
) -> None:
    assert _presentation_render_source_digest() == _presentation_render_source_digest()
    assert re.fullmatch(r"[0-9a-f]{64}", _presentation_render_source_digest()) is not None

    tree = tmp_path / "presentation"
    (tree / "templates").mkdir(parents=True)
    page = tree / "templates" / "page.html"
    page.write_bytes(b"<p>synthetic presentation</p>")
    cache = tree / "__pycache__"
    cache.mkdir()
    (cache / "page.cpython-312.pyc").write_bytes(b"stale cache bytes")

    records = _presentation_source_files(tree)

    assert records == (
        ("templates/page.html", hashlib.sha256(b"<p>synthetic presentation</p>").hexdigest()),
    )
    page.write_bytes(b"<p>changed presentation</p>")
    assert _presentation_source_files(tree) != records


def test_presentation_digest_pins_shared_current_builder_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = tmp_path / "user_fact_edit.py"
    shared.write_bytes(b"synthetic shared build implementation v1")
    monkeypatch.setattr(user_fact_edit_module, "__file__", str(shared))
    before = _presentation_render_source_digest()
    shared.write_bytes(b"synthetic shared build implementation v2")
    assert _presentation_render_source_digest() != before


def test_presentation_rebuild_preserves_prior_user_clear_and_original_source(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    service.save(_fact_save_command(request_id="prior-real-save-contract",
                                   edits=FactEdit(normalized_value=None)))
    before = service.read_current_delivery()
    facts = service.current_facts()
    clinical = {kind: _projection(root, kind) for kind in ("A", "B")}
    tables = _frozen_tables(root)
    result = service.rebuild_current_presentation(
        _command(request_id="presentation-after-clear", expected_revision=1))
    assert result.revision == 2
    assert result.active_fact_version_ids == before.active_fact_version_ids
    assert service.current_facts() == facts
    assert _frozen_tables(root) == tables
    assert {kind: _projection(root, kind) for kind in ("A", "B")} == clinical
    assert facts["fact-crude-rate"]["disclosure_state"] == "user_cleared"


@pytest.mark.parametrize("changed_after", ("A", "B"))
def test_presentation_refuses_drift_during_batch_before_current_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed_after: str,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    original_digest = _presentation_render_source_digest()
    changed = False

    def after(report: str) -> None:
        nonlocal changed
        if report == changed_after:
            changed = True

    service._after_report_built = after
    monkeypatch.setattr(user_fact_edit_module, "_presentation_render_source_digest",
                        lambda: "f" * 64 if changed else original_digest)
    with pytest.raises(PresentationRebuildConflictError, match="呈现资源已变化"):
        service.rebuild_current_presentation(_command(request_id="presentation-live-drift"))
    assert service.read_current_delivery() == before
    assert not any(event.event_type == _PRESENTATION_CANDIDATE_EVENT
                   for event in service.event_store.read_all())


def test_presentation_rebuild_share_uses_rebuilt_generation(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = {kind: _projection(root, kind) for kind in ("A", "B", "C")}
    before_a = next(item for item in service.read_current_delivery().reports if item.report == "A")
    old_page = (root / before_a.site_relative_path / "safety.html").read_text(encoding="utf-8")
    assert 'data-current-revision="0"' in old_page

    result = service.rebuild_current_presentation(_command(request_id="presentation-share"))
    current = service.read_current_delivery()
    destination = tmp_path / "presentation-share.zip"
    selections = tuple(
        ShareViewSelection(
            report=item.report,
            revision=item.revision,
            entry_page="safety.html" if item.report in {"A", "B"} else "overview.html",
        )
        for item in current.reports
    )

    receipt = export_current_html_share(root, destination, selections=selections)

    assert receipt.current_revision == 1
    assert result.revision == 1
    with ZipFile(destination) as archive:
        manifest = json.loads(archive.read("share-manifest.json"))
        assert manifest["current_revision"] == 1
        assert manifest["fact_revision_digest"] == current.fact_revision_digest
        for item in current.reports:
            assert manifest["reports"][item.report]["report_revision"] == item.revision
            assert archive.read(f"{item.report}/data/report.js") == (
                root / item.site_relative_path / "data/report.js"
            ).read_bytes()
            assert manifest["reports"][item.report]["file_sha256"]["data/report.js"] == (
                item.file_hashes["data/report.js"]
            )
        assert 'data-current-revision="1"' in archive.read("A/safety.html").decode("utf-8")
        for kind in ("A", "B", "C"):
            assert _clinical_view(
                _report_payload(archive.read(f"{kind}/data/report.js"), kind)
            ) == _clinical_view(before[kind])


def test_presentation_cli_runs_real_service_and_replays_exact_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB", complete_workspace=True)
    command = _command(request_id="presentation-cli")
    path = root / "inputs/presentation-command.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(command.model_dump_json(exclude_unset=True), encoding="utf-8")
    args = ["project", "rebuild-presentation", "--root", str(root), "--command", str(path)]
    assert cli_main(args) == 0
    output = capsys.readouterr()
    assert "PRESENTATION_REBUILT revision=1 reports=A,B" in output.out
    current = UserFactEditService(root).read_current_delivery()
    assert current.revision == 1
    assert cli_main(args) == 0
    assert UserFactEditService(root).read_current_delivery() == current


def test_presentation_cli_invalid_command_does_not_create_project_or_echo_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "not-created"
    command = tmp_path / "invalid.json"
    command.write_text('{"private_marker":"do-not-echo-presentation"}', encoding="utf-8")
    assert cli_main(["project", "rebuild-presentation", "--root", str(root),
                     "--command", str(command)]) == 2
    output = capsys.readouterr()
    assert "do-not-echo-presentation" not in output.out + output.err
    assert not root.exists()
