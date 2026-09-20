"""Raw assets and normalized text are separate immutable evidence objects."""

import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest

from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    capture_source_text,
    verify_source_text_derivation,
)


def test_utf8_raw_bytes_survive_normalization_and_reopen(tmp_path: Path) -> None:
    raw = " \n原始公开来源正文\r\n ".encode()
    text, receipt = capture_source_text(tmp_path, raw, media_type="text/plain")
    assert text == "原始公开来源正文"
    assert receipt.raw_asset.sha256 == hashlib.sha256(raw).hexdigest()
    assert receipt.text_sha256 == hashlib.sha256(text.encode()).hexdigest()
    assert receipt.raw_asset.sha256 != receipt.text_sha256
    assert ContentAddressedStore(tmp_path).read_bytes(receipt.raw_asset) == raw
    verify_source_text_derivation(tmp_path, receipt, text)
    assert capture_source_text(tmp_path, raw, media_type="text/plain") == (text, receipt)


@pytest.mark.parametrize("failure", ["raw_drift", "text_drift", "missing", "symlink"])
def test_derivation_rechecks_actual_asset_and_text(tmp_path: Path, failure: str) -> None:
    text, receipt = capture_source_text(tmp_path, b" original text \n", media_type="text/plain")
    path = tmp_path / receipt.raw_asset.relative_path
    if failure == "raw_drift":
        path.write_bytes(b"changed")
    elif failure == "missing":
        path.unlink()
    elif failure == "symlink":
        other = tmp_path / "other.txt"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
    else:
        text = "unrelated text"
    with pytest.raises(SourceDerivationError):
        verify_source_text_derivation(tmp_path, receipt, text)


def test_binary_mislabeled_as_pdf_cannot_become_text_evidence(tmp_path: Path) -> None:
    with pytest.raises(SourceDerivationError):
        capture_source_text(tmp_path, b"not a PDF", media_type="application/pdf")
    assert not (tmp_path / "evidence").exists()


def _pdf(text_layer: bool) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=100)
    if text_layer:
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }),
            }),
        })
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 50 Td (Primary trial results) Tj ET")
        page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_asset_is_not_replaced_by_extracted_text(tmp_path: Path) -> None:
    raw = _pdf(True)
    text, receipt = capture_source_text(tmp_path, raw, media_type="application/pdf")
    assert "Primary trial results" in text
    assert receipt.method == "pypdf-text-v1"
    assert ContentAddressedStore(tmp_path).read_bytes(receipt.raw_asset) == raw
    verify_source_text_derivation(tmp_path, receipt, text)


def test_pdf_without_text_requires_recovery_not_empty_evidence(tmp_path: Path) -> None:
    with pytest.raises(SourceDerivationError, match="OCR"):
        capture_source_text(tmp_path, _pdf(False), media_type="application/pdf")
    assert not (tmp_path / "evidence").exists()


def test_derivation_is_bound_at_submission_ingestion_and_reopen(tmp_path: Path) -> None:
    from ci_workflow.application.research_package_submission import (
        load_product_research_submission,
        submit_product_research_package,
    )
    from ci_workflow.application.source_research_service import (
        FreshAResearchPackage,
        compute_research_content_digest,
        ingest_fresh_a_research_package,
    )
    from ci_workflow.storage.content_store import ContentIntegrityError, EvidenceRepository
    from ci_workflow.storage.sqlite import open_database
    from tests.integration.test_research_package_submission import (
        _audit_payload,
        _project,
        _source_payload,
    )

    project = _project(tmp_path)
    path, payload = _source_payload(tmp_path)
    capture = payload["sources"][0]
    raw = (" \n" + capture["content_text"].strip() + "\n ").encode()
    text, receipt = capture_source_text(project, raw, media_type=capture["media_type"])
    capture.update(content_text=text, text_derivation=receipt.model_dump(mode="json"))
    payload["scientific_review"]["reviewed_content_digest"] = compute_research_content_digest(
        payload
    )
    data = json.dumps(payload, ensure_ascii=False).encode()
    path.write_bytes(data)
    project_id = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0][
        "project_id"
    ]
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(_audit_payload(project_id, data, payload)))
    submit_product_research_package(project, audit_package=audit_path, report_packages={"A": path})
    load_product_research_submission(project)
    lineage = ingest_fresh_a_research_package(
        project_root=project, project_id=project_id, contract_version=1,
        package=FreshAResearchPackage.model_validate(payload),
    )
    repository = EvidenceRepository(
        project / "state/project.sqlite", ContentAddressedStore(project)
    )
    with open_database(project / "state/project.sqlite") as database:
        source = repository._read_source_version(database, lineage.source_version_ids[0])
        assert source.text_derivation == receipt
        assert database.execute("SELECT count(*) FROM source_text_derivations").fetchone()[0] == 1
    assert (project / receipt.raw_asset.relative_path).read_bytes() == raw
    (project / receipt.raw_asset.relative_path).write_bytes(b"raw drift")
    fragment = repository.read_fragment(lineage.fragment_ids[0])
    with pytest.raises(ContentIntegrityError):
        repository.verify_reopened_fragment_record(
            fragment, reopened_original_text=text,
            source_version_id=lineage.source_version_ids[0],
        )
    with pytest.raises(ValueError, match="来源绑定：原始资产缺失或摘要漂移"):
        load_product_research_submission(project)


def test_legacy_database_without_derivation_table_is_readable(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
    from ci_workflow.storage.content_store import EvidenceRepository
    from ci_workflow.storage.migrations import apply_migrations, migration_directory
    from ci_workflow.storage.sqlite import open_database

    old = tmp_path / "old-migrations"
    old.mkdir()
    for migration in sorted(migration_directory().glob("*.sql"))[:9]:
        shutil.copyfile(migration, old / migration.name)
    database_path = tmp_path / "state/project.sqlite"
    apply_migrations(database_path, old)
    locator = EvidenceLocator(document_role="registry", field_path="posted")
    date = DateEvidence(state="reported", value=datetime(2025, 1, 1, tzinfo=UTC), locator=locator)
    repository = EvidenceRepository(database_path, ContentAddressedStore(tmp_path))
    source = repository.add_source_version(
        source_id="historical-source", content=b"historical public text", media_type="text/plain",
        acquired_at=datetime(2025, 2, 1, tzinfo=UTC),
        published_at=date, effective_at=date, first_disclosed_at=date,
    )
    assert source.text_derivation is None
    with open_database(database_path) as database:
        assert repository._read_source_version(database, source.source_version_id) == source
        assert database.execute("PRAGMA user_version").fetchone()[0] == 9


def test_capture_cli_persists_payload_without_printing_source_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    from ci_workflow.cli import main
    from tests.integration.test_research_package_submission import _project

    project = _project(tmp_path)
    original = tmp_path / "public-source.txt"
    raw = b" \nPublic original source text\n "
    original.write_bytes(raw)
    args = ["research", "capture", "--project", str(project),
            "--input", str(original), "--media-type", "text/plain"]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "Public original source text" not in output
    pointer = json.loads(output)
    capture = json.loads((project / pointer["capture_path"]).read_bytes())
    assert capture["content_text"] == "Public original source text"
    assert capture["text_derivation"]["raw_asset"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert original.read_bytes() == raw
    assert main(args) == 0
    assert capsys.readouterr().out == output


@pytest.mark.parametrize("case", ["missing", "symlink", "invalid_pdf"])
def test_capture_cli_rejects_unusable_input_without_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], case: str,
) -> None:
    from ci_workflow.cli import main
    from tests.integration.test_research_package_submission import _project

    project = _project(tmp_path)
    source = tmp_path / "public-source.pdf"
    if case == "invalid_pdf":
        source.write_bytes(b"not a PDF")
    elif case == "symlink":
        target = tmp_path / "original.pdf"
        target.write_bytes(_pdf(True))
        source.symlink_to(target)
    assert main([
        "research", "capture", "--project", str(project), "--input", str(source),
        "--media-type", "application/pdf",
    ]) == 2
    output = capsys.readouterr()
    assert "CONTRACT_ERROR" in output.err
    assert "not a PDF" not in output.err
    assert not output.out
    assert not tuple((project / "evidence/raw").rglob("*.bin"))


def test_pdf_capture_without_raw_receipt_is_rejected(tmp_path: Path) -> None:
    from ci_workflow.application.source_research_service import SourceCapture
    from tests.integration.test_research_package_submission import _source_payload

    _, payload = _source_payload(tmp_path)
    source = payload["sources"][0]
    source["media_type"] = "application/pdf"
    source.pop("text_derivation", None)
    with pytest.raises(ValueError, match="原始资产及派生回执"):
        SourceCapture.model_validate(source)
