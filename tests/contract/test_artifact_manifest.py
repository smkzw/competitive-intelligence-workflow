from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

ROOT = Path(__file__).resolve().parents[2]


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "manifest_id": "artifact-manifest_001",
        "project_id": "project_001",
        "contract_version": 1,
        "report": "B",
        "report_version": "v1",
        "data_cutoff": "2026-08-10T23:59:59.999999+08:00",
        "producer_run_id": "run_001",
        "source_commit": "a" * 40,
        "package_digest": "b" * 64,
        "evidence_snapshot_id": "evidence-snapshot_001",
        "claim_snapshot_id": "claim-snapshot_001",
        "report_snapshot_id": "report-snapshot_001",
        "coverage_set_id": "coverage-set_001",
        "coverage_projection_id": "coverage-projection_001",
        "structured_exceptions": [],
        "pages_or_sections": ["首页", "疗效", "安全性"],
        "product_ids": ["drug_001"],
        "trial_ids": ["trial_001"],
        "claim_ids": ["claim_001"],
        "chart_ids": ["chart_001"],
        "table_ids": ["table_001"],
        "evidence_reference_ids": ["fragment_001"],
        "design_contract": {
            "roles": ["core", "project_profile", "site"],
            "digest": "c" * 64,
            "applicable_sections": ["首页", "疗效", "安全性"],
        },
        "renderer": {"name": "portal-renderer", "version": "0.1.0"},
        "filter_state": {"target": ["TSLP"], "trial": ["trial_001"]},
        "generated_at": "2026-08-11T20:55:00+08:00",
        "deterministic_checks": [
            {"check_id": "coverage_diff", "status": "passed", "receipt": "0"}
        ],
        "render_verdict": {
            "verdict_id": "render-verdict_001",
            "status": "accepted",
            "verified_at": "2026-08-11T20:56:00+08:00",
            "anchor_ids": ["chromium-index", "webkit-index"],
        },
        "accepted_by": "visual-verifier_001",
        "artifact": {
            "relative_path": "reports/B/v1/html/index.html",
            "sha256": "d" * 64,
            "byte_size": 12345,
            "modified_at": "2026-08-11T20:55:30+08:00",
            "media_type": "text/html",
        },
        "status": "accepted",
        "supersedes_manifest_id": None,
    }


def test_artifact_manifest_requires_every_appendix_c_field(tmp_path: Path) -> None:
    from ci_workflow.storage.manifest_store import (
        ArtifactManifest,
        ManifestIntegrityError,
        ManifestStore,
        ManifestWriteContext,
    )

    schema = json.loads(
        (ROOT / "schemas" / "artifact-manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    payload = _manifest()
    validator.validate(payload)
    ArtifactManifest.model_validate(payload)

    for required in payload:
        invalid = deepcopy(payload)
        invalid.pop(required)
        with pytest.raises(ValidationError):
            validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            ArtifactManifest.model_validate(invalid)

    with pytest.raises(ValidationError):
        validator.validate({**payload, "accepted_by": None})
    with pytest.raises(PydanticValidationError):
        ArtifactManifest.model_validate({**payload, "accepted_by": None})

    for parent, child in (
        ("design_contract", "digest"),
        ("renderer", "version"),
        ("render_verdict", "anchor_ids"),
        ("artifact", "sha256"),
    ):
        invalid = deepcopy(payload)
        nested = invalid[parent]
        assert isinstance(nested, dict)
        nested.pop(child)
        with pytest.raises(ValidationError):
            validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            ArtifactManifest.model_validate(invalid)

    invalid_check = deepcopy(payload)
    checks = invalid_check["deterministic_checks"]
    assert isinstance(checks, list)
    assert isinstance(checks[0], dict)
    checks[0].pop("receipt")
    with pytest.raises(ValidationError):
        validator.validate(invalid_check)
    with pytest.raises(PydanticValidationError):
        ArtifactManifest.model_validate(invalid_check)

    for invalid in (
        {**payload, "artifact": {**payload["artifact"], "relative_path": "/tmp/fake"}},
        {
            **payload,
            "deterministic_checks": [
                {"check_id": "coverage_diff", "status": "failed", "receipt": "1"}
            ],
        },
        {
            **payload,
            "render_verdict": {**payload["render_verdict"], "status": "rejected"},
        },
    ):
        with pytest.raises(ValidationError):
            validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            ArtifactManifest.model_validate(invalid)

    project_root = tmp_path / "项目"
    artifact_path = project_root / "reports/B/v1/html/index.html"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    content = b"<!doctype html><title>test</title>"
    artifact_path.write_bytes(content)
    modified_at = datetime.fromisoformat("2026-08-11T20:55:30+08:00")
    os.utime(artifact_path, (modified_at.timestamp(), modified_at.timestamp()))
    bound_payload = {
        **payload,
        "artifact": {
            **payload["artifact"],
            "sha256": hashlib.sha256(content).hexdigest(),
            "byte_size": len(content),
        },
    }
    manifest = ArtifactManifest.model_validate(bound_payload)
    store = ManifestStore(project_root)
    context = ManifestWriteContext.model_validate(
        {key: bound_payload[key] for key in ManifestWriteContext.model_fields}
    )
    with pytest.raises(ManifestIntegrityError, match="当前运行"):
        store.write(manifest)
    with pytest.raises(ManifestIntegrityError, match="不是当前接受对象"):
        store.write(
            manifest,
            current_context=context.model_copy(update={"producer_run_id": "run_old"}),
        )
    with pytest.raises(ManifestIntegrityError, match="不是当前接受对象"):
        store.write(
            manifest,
            current_context=context.model_copy(
                update={"report_snapshot_id": "report-snapshot_old"}
            ),
        )
    stored_path = store.write(manifest, current_context=context)
    assert stored_path.is_file()
    artifact_path.write_bytes(b"tampered")
    with pytest.raises(ManifestIntegrityError):
        store.write(manifest, current_context=context)
