"""A pinned candidate restores evidence and registered consumers as one unit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_binding_recovery import (
    export_verified_consumer_bindings,
)
from ci_workflow.application.verified_candidate_recovery import (
    VerifiedCandidateRecoveryError,
    restore_verified_candidate,
    seal_verified_candidate,
)
from tests.integration.test_w04_consumer_binding_recovery import (
    _binding_count,
    _registered_project,
)


def _canonical(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def test_pinned_candidate_restores_both_parts_and_preserves_existing_target(
    tmp_path: Path,
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    sidecar = tmp_path / "consumers.json"
    export_verified_consumer_bindings(root, snapshot, sidecar)
    candidate = tmp_path / "candidate.json"
    pinned_digest = seal_verified_candidate(root, snapshot, sidecar, candidate)
    assert hashlib.sha256(candidate.read_bytes()).hexdigest() == pinned_digest
    assert "state/project.sqlite" not in candidate.read_text(encoding="utf-8")

    target = tmp_path / "recovered"
    locked, bindings = restore_verified_candidate(
        candidate, root / snapshot.relative_path, sidecar, target,
        expected_manifest_sha256=pinned_digest,
    )
    assert locked == snapshot
    assert {binding.report for binding in bindings} == {"A", "B"}
    assert _binding_count(target) == 2

    empty_target = tmp_path / "preexisting-empty"
    empty_target.mkdir()
    empty_locked, empty_bindings = restore_verified_candidate(
        candidate, root / snapshot.relative_path, sidecar, empty_target,
        expected_manifest_sha256=pinned_digest,
    )
    assert empty_locked == snapshot and empty_bindings == bindings
    assert _binding_count(empty_target) == 2

    with pytest.raises(VerifiedCandidateRecoveryError, match="非空|已存在"):
        restore_verified_candidate(
            candidate, root / snapshot.relative_path, sidecar, target,
            expected_manifest_sha256=pinned_digest,
        )
    assert _binding_count(target) == 2


def test_untrusted_or_late_incomplete_consumer_set_never_publishes_target(
    tmp_path: Path,
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    sidecar = tmp_path / "consumers.json"
    export_verified_consumer_bindings(root, snapshot, sidecar)
    candidate = tmp_path / "candidate.json"
    digest = seal_verified_candidate(root, snapshot, sidecar, candidate)

    wrong_pin = tmp_path / "wrong-pin"
    with pytest.raises(VerifiedCandidateRecoveryError, match="摘要"):
        restore_verified_candidate(
            candidate, root / snapshot.relative_path, sidecar, wrong_pin,
            expected_manifest_sha256="0" * 64,
        )
    assert not wrong_pin.exists()

    tampered = tmp_path / "tampered-sidecar.json"
    sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    sidecar_payload["bindings"] = [sidecar_payload["bindings"][0]]
    tampered.write_bytes(_canonical(sidecar_payload))
    with pytest.raises(VerifiedCandidateRecoveryError, match="登记集合"):
        seal_verified_candidate(
            root, snapshot, tampered, tmp_path / "subset-should-not-seal.json"
        )
    assert not (tmp_path / "subset-should-not-seal.json").exists()
    modified = json.loads(candidate.read_text(encoding="utf-8"))
    modified["consumer_sidecar_sha256"] = hashlib.sha256(tampered.read_bytes()).hexdigest()
    modified["consumer_sidecar_bytes"] = tampered.stat().st_size
    forged_candidate = tmp_path / "forged-candidate.json"
    forged_candidate.write_bytes(_canonical(modified))
    forged_digest = hashlib.sha256(forged_candidate.read_bytes()).hexdigest()
    late_failure = tmp_path / "late-failure"
    with pytest.raises(VerifiedCandidateRecoveryError, match="数量"):
        restore_verified_candidate(
            forged_candidate, root / snapshot.relative_path, tampered, late_failure,
            expected_manifest_sha256=forged_digest,
        )
    assert not late_failure.exists()

    damaged_sidecar = tmp_path / "damaged-sidecar.json"
    damaged_sidecar.write_bytes(sidecar.read_bytes() + b" ")
    mismatch = tmp_path / "mismatch"
    with pytest.raises(VerifiedCandidateRecoveryError, match="摘要|字节"):
        restore_verified_candidate(
            candidate, root / snapshot.relative_path, damaged_sidecar, mismatch,
            expected_manifest_sha256=digest,
        )
    assert not mismatch.exists()
