"""A joint-identity C bootstrap must share this one project and stay a candidate.

Tiny analogue of the joint A/B/C source bootstrap: the same project receives a
joint (multi-product) source identity and a C source candidate replayed from the
existing fixed registry fixture. The C report library must reach its ordinary
summary/comparison and trial dossier pages, an arm whose protocol type is not an
explicit comparison type must stay unbound and unresolved, and neither evidence
hashes nor the absence of a committed current may drift.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.ctgov_c_design_projection import (
    CtgovCArmBinding,
    CtgovCTrialBinding,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract
from tests.integration.test_r24_c_candidate_materialization import _raw
from tests.integration.test_r24_ctgov_c_design_projection import (
    _CAS_DIGEST,
    _CAS_ROOT,
    _EXPECTED_STUDY_OBSERVATIONS,
)
from tests.integration.test_r24_pdf_page_source_proof import _pdf_pages
from tools.materialize_ctgov_c_candidate import materialize, render_review_preview
from tools.materialize_identity_sources import materialize as materialize_identity

_INDICATION = "阵发性睡眠性血红蛋白尿症"
_CUTOFF = "2026-09-26"
_OBSERVED_AT = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
_WITNESS_CLOCK = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
_URL = "https://cdn.clinicaltrials.gov/large-docs/test/joint-identity.pdf"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_blob_path() -> Path:
    return _CAS_ROOT / f"evidence/raw/sha256/{_CAS_DIGEST[:2]}/{_CAS_DIGEST}.bin"


def _joint_identity_source_set(tmp_path: Path) -> tuple[Path, Path, str]:
    """Two products, one holder/group chain, one pinned synthetic PDF page."""

    from ci_workflow.sources.connectors.public_pdf_availability import (
        PdfHttpPage,
        capture_public_pdf_availability,
    )
    from ci_workflow.storage.content_store import ContentAddressedStore

    source = tmp_path / "joint-identity-source"
    source.mkdir()
    raw = _pdf_pages([[
        "China MAH: Holder Ltd",
        "Group Ltd controls Holder Ltd",
        "Product PEV: Pegcetacoplan",
        "Product DAN: Danicopan",
    ]])
    (source / "joint.pdf").write_bytes(raw)
    asset = ContentAddressedStore(source).put_bytes(raw, media_type="application/pdf")
    captured = capture_public_pdf_availability(
        source, _URL, asset,
        transport=lambda requested, timeout, limit: PdfHttpPage(
            200, "application/pdf", len(raw), raw, requested),
        clock=lambda: _WITNESS_CLOCK,
    )
    assert captured.witness is not None
    proof = captured.witness.model_dump(mode="json")
    observed_at = _WITNESS_CLOCK.isoformat()
    spec = {
        "candidate_only": True,
        "sources": [
            {"key": key, "filename": "joint.pdf",
             "sha256": hashlib.sha256(raw).hexdigest(), "page": 1, "paragraph": paragraph,
             "url": _URL, "public_pdf_availability": proof}
            for key, paragraph in (
                ("holder", "China MAH: Holder Ltd"),
                ("group", "Group Ltd controls Holder Ltd"),
                ("pev", "Product PEV: Pegcetacoplan"),
                ("dan", "Product DAN: Danicopan"),
            )
        ],
        "entities": [
            {"key": "pev", "entity_type": "product", "canonical_name": "Pegcetacoplan",
             "identity_basis": "synthetic-qa-pegcetacoplan"},
            {"key": "dan", "entity_type": "product", "canonical_name": "Danicopan",
             "identity_basis": "synthetic-qa-danicopan"},
            {"key": "legal", "entity_type": "organization", "canonical_name": "Holder Ltd",
             "identity_basis": "synthetic-qa-holder"},
            {"key": "parent", "entity_type": "organization", "canonical_name": "Group Ltd",
             "identity_basis": "synthetic-qa-parent"},
        ],
        "relations": [
            {"subject": "pev", "object": "legal", "predicate": "has_mah", "source_key": "pev",
             "jurisdiction": "CN", "authorization_scope": "synthetic QA license PEV",
             "observed_at": observed_at},
            {"subject": "dan", "object": "legal", "predicate": "has_mah", "source_key": "dan",
             "jurisdiction": "CN", "authorization_scope": "synthetic QA license DAN",
             "observed_at": observed_at},
            {"subject": "legal", "object": "parent", "predicate": "controlled_by",
             "source_key": "group", "observed_at": observed_at},
        ],
        "product_entity_ids": {"pegcetacoplan": "pev", "danicopan": "dan"},
    }
    path = tmp_path / "joint-identity-source-set.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return source, path, _digest(path)


def _bindings() -> tuple[CtgovCTrialBinding, ...]:
    """One fully typed trial plus one trial whose arm types are not explicit."""

    return (
        CtgovCTrialBinding(
            trial_id="nct02264639",
            product_id="pegcetacoplan",
            arms=tuple(
                CtgovCArmBinding(
                    label=f"Cohort {index}",
                    group_id=f"protocol-nct02264639-cohort-{index}",
                    role="experimental_arm",
                )
                for index in (1, 2, 3, 4)
            ),
        ),
        # NCT07413250 has only armGroups entries without a type. The product
        # proposal must not invent a role, group id or arm-product relation.
        CtgovCTrialBinding(trial_id="nct07413250", product_id="danicopan"),
    )


def test_joint_identity_c_bootstrap_shares_project_and_keeps_unknown_arm(tmp_path: Path) -> None:
    root = tmp_path / "joint-shared-project"
    contract = create_project_contract(
        indication=_INDICATION, reports=["A", "B", "C"], outputs=["html"],
        cutoff=_CUTOFF, created_at=datetime(2026, 10, 3, tzinfo=UTC),
    )
    create_project_workspace(root, contract)
    project_yaml_before = (root / "project.yaml").read_bytes()
    fixture_before = _digest(_fixture_blob_path())

    identity_source, identity_spec, identity_digest = _joint_identity_source_set(tmp_path)
    identity_receipt = materialize_identity(
        identity_source, identity_spec, identity_digest, root, project_workspace=True,
    )
    assert identity_receipt["science_accepted"] is False
    assert identity_receipt["current_promoted"] is False
    assert identity_receipt["source_fragments"] == 4

    output = root / "evidence/library/c-candidate"
    result = materialize(
        source_root=_CAS_ROOT, raw_asset=_raw(), output=output, bindings=_bindings(),
        indication_id="pnh", indication=_INDICATION, cutoff=_CUTOFF,
        observed_at=_OBSERVED_AT, project_root=root,
    )
    # Same existing project: no forked C-only project and the same contract.
    assert not (output / "project").exists()
    assert verify_project_workspace(root).contract.project_id == contract.project_id
    assert (root / result["snapshot"]["relative_path"]).is_file()
    saved = json.loads((output / "inputs.json").read_bytes())
    assert saved["contract"]["project_id"] == contract.project_id
    assert result["current_generation_switched"] is False
    assert result["scientific_acceptance"] == "not_accepted"

    projection = json.loads((output / "projection.json").read_bytes())
    observations = projection["observations"]
    assert len([row for row in observations if row["trial_id"] == "nct02264639"]) == (
        _EXPECTED_STUDY_OBSERVATIONS["NCT02264639"]
    )
    assert {row["group_id"] for row in observations if row["field"] == "experimental_arm"} == {
        f"protocol-nct02264639-cohort-{index}" for index in (1, 2, 3, 4)
    }
    # Unknown arm types stay unknown: every arm atom of the second trial is
    # unresolved and no role, group or arm observation is invented for it.
    unresolved = projection["unresolved_atoms"]
    assert {item["trial_id"] for item in unresolved} == {"NCT07413250"}
    assert {item["reason"] for item in unresolved} == {"missing_arm_binding"}
    assert {item["field_id"] for item in unresolved} == {
        "ctgov.protocol.arm.label",
        "ctgov.protocol.arm.description",
        "ctgov.protocol.arm.intervention_name",
    }
    assert all(
        (item["path"] or "").startswith("$.protocolSection.armsInterventionsModule.armGroups")
        for item in unresolved
    )
    assert any(row["trial_id"] == "nct07413250" for row in observations)
    assert not any(
        row["trial_id"] == "nct07413250"
        and row["field"] in {"experimental_arm", "control_arm", "dosing_regimen"}
        for row in observations
    )
    assert not any(
        row["group_id"].startswith("protocol-nct07413250-") for row in observations
    )

    identity_checkpoint = _digest(root / "identity-checkpoint.json")
    identity_binding = _digest(root / "evidence/library/portal-identity-context.json")
    manifest_path = output / "candidate-manifest.json"
    manifest_before = _digest(manifest_path)

    preview = render_review_preview(output, rendered_at=_OBSERVED_AT, project_root=root)
    assert preview["registered_consumers"] == result["observations"]
    assert preview["scientific_acceptance"] is False
    assert preview["current_generation_switched"] is False
    site = root / preview["site_relative_path"]
    overview = (site / "overview.html").read_text(encoding="utf-8")
    assert "view=comparison" in overview
    assert (site / "trials/nct02264639.html").is_file()
    assert (site / "trials/nct07413250.html").is_file()
    identities = json.loads((site / "data/identity-projection.json").read_bytes())
    assert set(identities) == {"pegcetacoplan", "danicopan"}
    assert "Group Ltd｜中国MAH所属集团" in identities["pegcetacoplan"]["company_label"]
    assert json.loads((site / "data/research-status.json").read_bytes())[
        "delivery_status"
    ] == "unreviewed_candidate"
    assert "data-identity-product" in overview

    # Guards: report hashes, identity binding, project contract and the read-only
    # fixture bytes stay fixed; no current delivery is created.
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest["current_generation_switched"] is False
    assert manifest["scientific_acceptance"] == "not_accepted"
    assert _digest(manifest_path) == manifest_before
    assert _digest(root / "identity-checkpoint.json") == identity_checkpoint
    assert _digest(root / "evidence/library/portal-identity-context.json") == identity_binding
    assert (root / "project.yaml").read_bytes() == project_yaml_before
    assert _digest(_fixture_blob_path()) == fixture_before == _CAS_DIGEST
    assert not (root / "reports/current.json").exists()
    for name, expected in manifest["file_sha256"].items():
        assert _digest(output / name) == expected
