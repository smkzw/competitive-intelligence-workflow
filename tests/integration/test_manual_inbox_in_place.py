from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.domain.enums import DownloadRequestState
from ci_workflow.gates.models import GateSpec
from ci_workflow.ingestion.manual_inbox import ManualInboxService, _canonical_filename

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)


def test_accept_renames_the_existing_inbox_file_without_copying_or_changing_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    for rel in (
        "events",
        "receipts",
        "evidence/manual-inbox",
        "evidence/quarantine",
        "evidence/raw",
        "evidence/library",
        "logs",
        "state/checkpoints",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / "logs/download_requests.md").write_text("# 待补充资料\n", encoding="utf-8")
    service = ManualInboxService(root)
    request = service.create_request(
        project_id="project-1",
        run_id="run-1",
        report_kind="B",
        spec=GateSpec.from_yaml(ROOT / "policies/gates/B-v1.yaml"),
        blocking_priority="blocking",
        product_id="product-1",
        trial_id="NCT00000001",
        registry_identifiers=("NCT00000001",),
        doi="10.1000/example",
        pmid=None,
        document_role="supplementary_material",
        title="主要结果附件",
        publisher="Example",
        landing_page_url="https://example.test/article",
        attachment_url="https://example.test/article.pdf",
        missing_fields=("b_baseline_age",),
        reason_zh="需要补充基线年龄。",
        gap_still_open=True,
        expected_to_close_units=("b_baseline_age",),
    )
    inbox = root / request.inbox_directory
    source = inbox / "原始附件.html"
    content = "NCT00000001 DOI: 10.1000/example\n基线年龄结果。\n".encode()
    source.write_bytes(content)
    inode_before = source.stat().st_ino
    digest_before = hashlib.sha256(source.read_bytes()).hexdigest()

    result = service.scan_and_process_inbox(request.request_id, occurred_at=NOW)

    assert result is not None
    assert result.state is DownloadRequestState.ACCEPTED
    canonical = _canonical_filename(
        basis="NCT00000001",
        document_role="supplementary_material",
        version_or_date=None,
        digest=digest_before,
        original_extension=".html",
    )
    target = inbox / canonical
    assert target.is_file()
    assert target.parent == source.parent
    assert target.stat().st_ino == inode_before
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest_before
    assert result.canonical_relative_path == f"{request.inbox_directory}/{canonical}"
    assert not (root / "evidence/library" / request.request_id / canonical).exists()
    assert not tuple((root / "evidence/raw").rglob("*.bin"))
