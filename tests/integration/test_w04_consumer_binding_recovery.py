"""Verified portal consumers survive a locked-snapshot restore through one sidecar.

The v2 evidence snapshot is locked *before* A/B consumers are registered, so its
``closure.facts[].consumer_binding`` values are ingestion hints (report kind and
row reference), never accepted bindings.  Recovery of the verified registry is
therefore an explicit, snapshot-bound sidecar whose import re-verifies snapshot
identity, referenced facts, binding identity/digest and report/row semantics
before writing anything.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_binding_recovery import (
    PortalConsumerBindingRecoveryError,
    export_verified_consumer_bindings,
    recover_verified_consumer_bindings,
)
from ci_workflow.application.portal_consumer_registry import (
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.storage.snapshot_store import (
    LockedSnapshot,
    SnapshotIntegrityError,
    SnapshotStore,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_w04_source_consumer_registry import (
    _b_direct_source_view,
    _candidate,
)

AT = datetime(2026, 9, 26, tzinfo=UTC)


def _registered_project(
    tmp_path: Path, *, source_unit: str = "Participants",
) -> tuple[Path, LockedSnapshot, str, str]:
    """Build one ingested project with verified A and B consumers on one atom."""
    root, snapshot, a_report, version_id = _candidate(tmp_path, source_unit=source_unit)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    register_a_source_consumers(
        root, snapshot, a_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version_id,),
        ).fetchone()
    register_b_shared_source_consumers(
        root, snapshot, _b_direct_source_view(a_report, locator, source_text=quote),
        {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )
    return root, snapshot, version_id, row_id


def _export(root: Path, snapshot: LockedSnapshot, path: Path) -> dict[str, object]:
    export_verified_consumer_bindings(root, snapshot, path)
    return json.loads(path.read_text(encoding="utf-8"))


def _restore(tmp_path: Path, root: Path, snapshot: LockedSnapshot) -> tuple[Path, Path]:
    manifest_path = tmp_path / "exported-manifest.json"
    shutil.copy2(root / snapshot.relative_path, manifest_path)
    restored = tmp_path / "restored"
    SnapshotStore(restored).restore_evidence_manifest(manifest_path)
    return restored, manifest_path


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _binding_count(project_root: Path) -> int:
    with open_database(project_root / "state/project.sqlite") as database:
        return int(
            database.execute(
                "SELECT COUNT(*) FROM source_portal_consumer_bindings"
            ).fetchone()[0]
        )


def _public_bindings(project_root: Path, version_id: str) -> tuple[ActiveFactBinding, ...]:
    service = UserFactEditService(project_root)
    public = service._public_fact(service._fact_row(version_id))
    return tuple(
        ActiveFactBinding.model_validate(item)
        for item in public.get("consumer_bindings", ())
    )


def _reissued_row(entry: dict[str, object], row_id: str) -> dict[str, object]:
    """Same fact claimed for another report row, with every digest recomputed."""
    binding = ActiveFactBinding.model_validate_json(str(entry["binding_json"]))
    encoded = binding.model_copy(update={"row_id": row_id}).model_dump_json()
    return {
        **entry,
        "row_id": row_id,
        "binding_json": encoded,
        "binding_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "binding_id": stable_id(
            "source-portal-binding", str(entry["source_fact_version_id"]),
            str(entry["report"]), str(entry["collection"]), row_id,
        ),
    }


def _reissued_fact(entry: dict[str, object], version_id: str) -> dict[str, object]:
    return {
        **entry,
        "source_fact_version_id": version_id,
        "binding_id": stable_id(
            "source-portal-binding", version_id,
            str(entry["report"]), str(entry["collection"]), str(entry["row_id"]),
        ),
    }


def test_restore_keeps_ingestion_hints_unaccepted_and_import_restores_exact_set(
    tmp_path: Path,
) -> None:
    root, snapshot, version_id, row_id = _registered_project(tmp_path)
    sidecar_path = tmp_path / "bindings.json"
    _export(root, snapshot, sidecar_path)
    expected = _public_bindings(root, version_id)
    assert {binding.report for binding in expected} == {"A", "B"}

    restored, manifest_path = _restore(tmp_path, root, snapshot)
    closure = json.loads(manifest_path.read_text(encoding="utf-8"))["closure"]
    hint = next(
        item["consumer_binding"]
        for item in closure["facts"] if item["fact_version_id"] == version_id
    )
    assert hint == {"report_kind": "A", "row_ref": f"efficacy:{row_id}"}
    assert _binding_count(restored) == 0
    assert _public_bindings(restored, version_id) == ()

    recovered = recover_verified_consumer_bindings(restored, sidecar_path)
    assert recovered == expected
    assert _public_bindings(restored, version_id) == expected
    assert _binding_count(restored) == 2

    assert recover_verified_consumer_bindings(restored, sidecar_path) == recovered
    assert _binding_count(restored) == 2


def test_restore_rejects_closure_context_that_disagrees_with_fact_bytes(
    tmp_path: Path,
) -> None:
    root, snapshot, version_id, row_id = _registered_project(tmp_path)
    payload = json.loads((root / snapshot.relative_path).read_text(encoding="utf-8"))
    item = next(
        entry
        for entry in payload["closure"]["facts"]
        if entry["fact_version_id"] == version_id
    )
    context = json.loads(item["scientific_context_json"])
    context["consumer_bindings"] = [{
        "report": "A",
        "collection": "efficacy",
        "row_id": row_id,
        "consumer_binding": {"report_kind": "A", "row_ref": f"efficacy:{row_id}"},
    }]
    item["scientific_context_json"] = json.dumps(
        context, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    manifest_path = tmp_path / "injected-manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    target = tmp_path / "injected-restore"
    with pytest.raises(SnapshotIntegrityError, match="科学语境"):
        SnapshotStore(target).restore_evidence_manifest(manifest_path)
    assert not (target / "state/project.sqlite").exists()


def test_export_contains_only_verified_registry_entries_of_one_locked_snapshot(
    tmp_path: Path,
) -> None:
    root, snapshot, version_id, row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    manifest = json.loads((root / snapshot.relative_path).read_text(encoding="utf-8"))

    assert exported["schema_version"] == "1.0"
    assert exported["evidence_snapshot_id"] == snapshot.snapshot_id
    assert exported["evidence_snapshot_sha256"] == snapshot.sha256
    assert exported["project_id"] == manifest["project_id"]
    assert exported["contract_version"] == manifest["contract_version"]
    assert len(exported["bindings"]) == 2
    assert {item["report"] for item in exported["bindings"]} == {"A", "B"}
    assert {item["row_id"] for item in exported["bindings"]} == {row_id}
    assert {item["source_fact_version_id"] for item in exported["bindings"]} == {version_id}
    for item in exported["bindings"]:
        binding = ActiveFactBinding.model_validate_json(str(item["binding_json"]))
        assert binding.source_version_id and binding.original_row_sha256
        assert item["binding_sha256"] == hashlib.sha256(
            str(item["binding_json"]).encode()
        ).hexdigest()
        assert item["binding_id"] == stable_id(
            "source-portal-binding", str(item["source_fact_version_id"]),
            str(item["report"]), str(item["collection"]), str(item["row_id"]),
        )
        assert "consumer_binding" not in binding.model_dump()

    again = tmp_path / "bindings-again.json"
    export_verified_consumer_bindings(root, snapshot, again)
    assert again.read_bytes() == (tmp_path / "bindings.json").read_bytes()


def test_export_does_not_overwrite_a_different_existing_sidecar(
    tmp_path: Path,
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    destination = tmp_path / "existing-sidecar.json"
    destination.write_bytes(b"older-candidate\n")
    with pytest.raises(PortalConsumerBindingRecoveryError, match="目标已存在"):
        export_verified_consumer_bindings(root, snapshot, destination)
    assert destination.read_bytes() == b"older-candidate\n"

    destination.unlink()
    export_verified_consumer_bindings(root, snapshot, destination)
    same_bytes = destination.read_bytes()
    export_verified_consumer_bindings(root, snapshot, destination)
    assert destination.read_bytes() == same_bytes


def test_export_fails_closed_before_registration(tmp_path: Path) -> None:
    root, snapshot, _report, _version_id = _candidate(tmp_path)
    destination = tmp_path / "bindings.json"
    with pytest.raises(PortalConsumerBindingRecoveryError, match="没有已核验消费者绑定"):
        export_verified_consumer_bindings(root, snapshot, destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"binding_json": '{"report":"A","row_ref":"efficacy:eff-1"}'},
        {"binding_sha256": "0" * 64},
        {"collection": "safety"},
        {"row_id": "eff-tampered"},
    ],
)
def test_recovery_rejects_tampered_entries_without_writing(
    tmp_path: Path, changes: dict[str, object],
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, _manifest_path = _restore(tmp_path, root, snapshot)
    entry = {**exported["bindings"][0], **changes}
    payload = {**exported, "bindings": [entry, *exported["bindings"][1:]]}
    path = _write(tmp_path / "tampered.json", payload)

    with pytest.raises(PortalConsumerBindingRecoveryError):
        recover_verified_consumer_bindings(restored, path)
    assert _binding_count(restored) == 0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"evidence_snapshot_sha256": "0" * 64}, "快照"),
        ({"evidence_snapshot_id": "evidence-snapshot_000000000000000000000000"}, "快照"),
        ({"project_id": "another-project"}, "项目身份"),
        ({"contract_version": 99}, "合同版本"),
    ],
)
def test_recovery_rejects_wrong_snapshot_or_project_identity(
    tmp_path: Path, changes: dict[str, object], message: str,
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, _manifest_path = _restore(tmp_path, root, snapshot)
    path = _write(tmp_path / "wrong-snapshot.json", {**exported, **changes})

    with pytest.raises(PortalConsumerBindingRecoveryError, match=message):
        recover_verified_consumer_bindings(restored, path)
    assert _binding_count(restored) == 0


def test_recovery_rejects_hint_only_sidecar_built_from_snapshot_closure(
    tmp_path: Path,
) -> None:
    root, snapshot, version_id, row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, manifest_path = _restore(tmp_path, root, snapshot)
    closure = json.loads(manifest_path.read_text(encoding="utf-8"))["closure"]
    hint = next(
        item["consumer_binding"]
        for item in closure["facts"] if item["fact_version_id"] == version_id
    )
    hinted = json.dumps(hint, ensure_ascii=False)
    payload = {
        **exported,
        "bindings": [{
            "binding_id": stable_id(
                "source-portal-binding", version_id, "A", "efficacy", row_id,
            ),
            "source_fact_version_id": version_id,
            "report": "A",
            "collection": "efficacy",
            "row_id": row_id,
            "binding_json": hinted,
            "binding_sha256": hashlib.sha256(hinted.encode()).hexdigest(),
            "created_at": AT.isoformat(),
        }],
    }
    path = _write(tmp_path / "hint-only.json", payload)

    with pytest.raises(PortalConsumerBindingRecoveryError, match="科学身份"):
        recover_verified_consumer_bindings(restored, path)
    assert _binding_count(restored) == 0


def test_recovery_rejects_duplicate_or_conflicting_entries(tmp_path: Path) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, _manifest_path = _restore(tmp_path, root, snapshot)

    duplicated = {
        **exported, "bindings": [*exported["bindings"], exported["bindings"][0]],
    }
    with pytest.raises(PortalConsumerBindingRecoveryError, match="重复"):
        recover_verified_consumer_bindings(
            restored, _write(tmp_path / "duplicate.json", duplicated)
        )

    conflicting = {
        **exported,
        "bindings": [
            *exported["bindings"],
            _reissued_row(exported["bindings"][0], "eff-other-row"),
        ],
    }
    with pytest.raises(PortalConsumerBindingRecoveryError, match="冲突"):
        recover_verified_consumer_bindings(
            restored, _write(tmp_path / "conflicting.json", conflicting)
        )
    assert _binding_count(restored) == 0


def test_recovery_rejects_fact_outside_locked_snapshot_closure(tmp_path: Path) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    _foreign_root, _foreign_snapshot, foreign_version_id, _foreign_row = (
        _registered_project(
            tmp_path / "foreign", source_unit="Percentage of responders",
        )
    )
    assert foreign_version_id != _version_id
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, _manifest_path = _restore(tmp_path, root, snapshot)
    payload = {
        **exported,
        "bindings": [
            _reissued_fact(entry, foreign_version_id) for entry in exported["bindings"]
        ],
    }
    path = _write(tmp_path / "foreign-fact.json", payload)

    with pytest.raises(PortalConsumerBindingRecoveryError, match="传递闭包"):
        recover_verified_consumer_bindings(restored, path)
    assert _binding_count(restored) == 0


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    (("trial_id", "nct99999999"), ("group_id", "OG-OTHER")),
)
def test_recovery_rejects_rehashed_binding_with_wrong_source_identity(
    tmp_path: Path, field: str, wrong_value: str,
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, _manifest_path = _restore(tmp_path, root, snapshot)
    changed = []
    for entry in exported["bindings"]:
        binding = ActiveFactBinding.model_validate_json(str(entry["binding_json"]))
        encoded = binding.model_copy(update={field: wrong_value}).model_dump_json()
        changed.append({
            **entry,
            "binding_json": encoded,
            "binding_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        })
    path = _write(tmp_path / "wrong-science.json", {**exported, "bindings": changed})

    with pytest.raises(PortalConsumerBindingRecoveryError, match="来源事实"):
        recover_verified_consumer_bindings(restored, path)
    assert _binding_count(restored) == 0


def test_recovery_does_not_accept_unregistered_c_consumer_claim(
    tmp_path: Path,
) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    exported = _export(root, snapshot, tmp_path / "bindings.json")
    restored, _manifest_path = _restore(tmp_path, root, snapshot)
    original = exported["bindings"][0]
    binding = ActiveFactBinding.model_validate_json(str(original["binding_json"]))
    claimed = binding.model_copy(update={"report": "C", "collection": "observations"})
    encoded = claimed.model_dump_json()
    entry = {
        **original,
        "report": "C",
        "collection": "observations",
        "binding_json": encoded,
        "binding_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "binding_id": stable_id(
            "source-portal-binding", str(original["source_fact_version_id"]),
            "C", "observations", str(original["row_id"]),
        ),
    }
    path = _write(tmp_path / "claimed-c.json", {**exported, "bindings": [entry]})

    with pytest.raises(PortalConsumerBindingRecoveryError, match="C 消费者"):
        recover_verified_consumer_bindings(restored, path)
    assert _binding_count(restored) == 0


def test_recovery_never_overwrites_a_conflicting_registered_row(tmp_path: Path) -> None:
    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    sidecar_path = tmp_path / "bindings.json"
    _export(root, snapshot, sidecar_path)
    assert len(recover_verified_consumer_bindings(root, sidecar_path)) == 2
    assert _binding_count(root) == 2

    exported = json.loads(sidecar_path.read_text(encoding="utf-8"))
    payload = {
        **exported,
        "bindings": [
            _reissued_row(exported["bindings"][0], "eff-other-row"),
            *exported["bindings"][1:],
        ],
    }
    path = _write(tmp_path / "conflicting-reimport.json", payload)
    with pytest.raises(PortalConsumerBindingRecoveryError, match="冲突"):
        recover_verified_consumer_bindings(root, path)
    assert _binding_count(root) == 2
