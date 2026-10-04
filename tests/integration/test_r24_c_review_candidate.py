"""C review candidates are usable libraries, never accepted current deliveries."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.latest_delivery import (
    CurrentDeliveryBundle,
    CurrentReportDelivery,
    publish_current_delivery,
)
from ci_workflow.domain.enums import FactReviewState
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    ReportCPortalError,
    render_report_c_site,
)
from ci_workflow.storage.migrations import apply_migrations


def _candidate() -> ReportCPortalData:
    data = ReportCPortalData.model_validate_json(Path(
        "fixtures/acceptance/full-matrix-v1/inputs/report-c-data.json",
    ).read_bytes())
    return data.model_copy(update={"observations": tuple(
        row.model_copy(update={"review_state": FactReviewState.CANDIDATE})
        for row in data.observations
    )})


def _render_candidate(data: ReportCPortalData, site: Path) -> tuple[Path, ...]:
    from ci_workflow.renderers.portal import report_c

    renderer = getattr(report_c, "render_report_c_review_candidate", None)
    assert renderer is not None, "C needs an explicit review-only library entry"
    return renderer(data, site)


def test_candidate_ordinary_delivery_gate_remains_closed(tmp_path: Path) -> None:
    with pytest.raises(ReportCPortalError, match="关键设计证据阻断"):
        render_report_c_site(_candidate(), tmp_path / "must-not-render")
    assert not (tmp_path / "must-not-render").exists()


def test_candidate_library_preserves_all_facts_and_labels_every_physical_page(
    tmp_path: Path,
) -> None:
    data = _candidate()
    before = data.model_dump_json()
    site = tmp_path / "review-c"
    pages = _render_candidate(data, site)
    assert len(pages) >= 13
    for page in pages:
        html = page.read_text()
        assert "待复核资料" in html
        assert "不代表科学验收通过" in html
        assert 'data-review-status="unreviewed_candidate"' in html
    payload_text = (site / "data/report.js").read_text()
    payload = json.loads(payload_text.removeprefix("window.REPORT_C=").removesuffix(";\n"))
    assert {row["row_id"] for row in payload["observations"]} == {
        row.row_id for row in data.observations
    }
    assert {row["review_state"] for row in payload["observations"]} == {"candidate"}
    assert data.model_dump_json() == before
    assert json.loads((site / "data/research-status.json").read_bytes()) == {
        "schema_version": "1.0", "report": "C", "delivery_status": "unreviewed_candidate",
    }


def test_candidate_library_cannot_be_committed_as_current(tmp_path: Path) -> None:
    root = tmp_path / "project"
    apply_migrations(root / "state/project.sqlite")
    site = root / "reports/C/review-only/html"
    _render_candidate(_candidate(), site)
    hashes = {path.relative_to(site).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in site.rglob("*") if path.is_file()}
    facts = ("candidate-fact",)
    digest = hashlib.sha256(json.dumps(facts, separators=(",", ":")).encode()).hexdigest()
    report = CurrentReportDelivery(
        report="C", revision=0, report_version="review-only",
        site_relative_path=site.relative_to(root).as_posix(), file_hashes=hashes,
        fact_version_ids=facts, fact_revision_digest=digest,
    )
    current = CurrentDeliveryBundle(
        project_id="review-only-project", revision=0, active_fact_version_ids=facts,
        fact_revision_digest=digest, reports=(report,), created_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="待复核.*current"):
        publish_current_delivery(root, current, expected_revision=0)
    assert not tuple((root / "reports/generations").glob("*.json"))


def test_review_entry_does_not_overwrite_a_previous_site(tmp_path: Path) -> None:
    site = tmp_path / "existing"
    site.mkdir()
    old = site / "keep.txt"
    old.write_text("earlier evidence")
    with pytest.raises(ReportCPortalError, match="新.*目录"):
        _render_candidate(_candidate(), site)
    assert old.read_text() == "earlier evidence"


def test_candidate_and_publication_limits_share_one_notice_without_hiding_either(
    tmp_path: Path,
) -> None:
    from ci_workflow.renderers.portal.report_c import render_report_c_review_candidate

    pages = render_report_c_review_candidate(
        _candidate(), tmp_path / "review-limit",
        publication_limitation_zh="仅两项登记研究，方案全文尚未并入。",
    )
    for page in pages:
        html = page.read_text()
        assert html.count('<aside class="publication-limitation"') == 1
        assert 'aria-label="待复核资料与证据限制"' in html
        assert "不代表科学验收通过" in html
        assert "仅两项登记研究，方案全文尚未并入。" in html
