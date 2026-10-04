"""当前 127 条 C 门户消费者在钉固证据+消费者对中的可移植恢复家族测试。

C 消费者的 ``ActiveFactBinding`` 以捕获实例标识（如 ``pdf-page-source_...`` 或
``ctgov-nct...``）承载来源身份，而持久化片段保存的是不可变来源版本标识；恢复
必须用外部钉固的原始 C 报告数据（``review-portal-data.json``）重建每一行的完整
科学身份，再与锁定闭包和已登记来源事实逐项对照：捕获实例→不可变版本的闭包映射、
字段/族/试验、产品—试验关联、完整来源语境与定位、逐字原文及已声明资格分段。
自洽的 ``binding_json`` 本身不构成证明，缺省 C 证明不得改变 A/B 字节与 API。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.c_portal_consumer_registry import (
    register_c_source_consumers,
)
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.portal_consumer_binding_recovery import (
    PortalConsumerBindingRecoveryError,
    export_verified_consumer_bindings,
    recover_verified_consumer_bindings,
)
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.application.verified_candidate_recovery import (
    VerifiedCandidateManifest,
    VerifiedCandidateRecoveryError,
    restore_verified_candidate,
    seal_verified_candidate,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_c_clause_context import build_candidate

_AT = datetime(2026, 10, 4, tzinfo=UTC)
_FIXED_OBSERVATIONS = 127
_PDF_ROW = "c-pdf-prop-c-nct02264639-sap-p24-concomitant-conservative-lead-in"
_REGISTRY_ROW = "c-nct02264639-inclusion"


@dataclass(frozen=True)
class _RegisteredC:
    project: Path
    snapshot: LockedSnapshot
    report_data: ReportCPortalData
    report_data_path: Path
    versions: dict[str, str]


@pytest.fixture(scope="module")
def registered_c(tmp_path_factory: pytest.TempPathFactory) -> _RegisteredC:
    """Build the current native candidate including qualified planned terms.

    R174's frozen 122-row replay and its receipts remain unchanged; this family
    constructs a fresh candidate through the current production projector.
    """
    output, result, data = build_candidate(tmp_path_factory.mktemp("c-consumer-recovery"))
    project = output / "project"
    locked = LockedSnapshot.model_validate(result["snapshot"])
    payload = SnapshotStore(project).read(locked)
    captures = {
        str(item["capture"]["source_id"]): SourceCapture.model_validate(item["capture"])
        for item in payload["closure"]["sources"]
    }
    versions = {str(key): str(value) for key, value in result["fact_version_by_ref"].items()}
    assert len(data.observations) == _FIXED_OBSERVATIONS
    register_c_source_consumers(
        project, locked, data, versions, captures, registered_at=_AT,
    )
    return _RegisteredC(
        project=project,
        snapshot=locked,
        report_data=data,
        report_data_path=output / "review-portal-data.json",
        versions=versions,
    )


@pytest.fixture(scope="module")
def restored_target(registered_c: _RegisteredC, tmp_path_factory: pytest.TempPathFactory):
    """Factory restoring the pinned evidence into a fresh target without consumers."""
    root = tmp_path_factory.mktemp("c-restored")
    counter = iter(range(64))

    def _make() -> Path:
        target = root / f"target-{next(counter)}"
        SnapshotStore(target).restore_evidence_manifest(
            registered_c.project / registered_c.snapshot.relative_path
        )
        return target

    return _make


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _binding_count(project_root: Path) -> int:
    with open_database(project_root / "state/project.sqlite") as database:
        return int(
            database.execute(
                "SELECT COUNT(*) FROM source_portal_consumer_bindings"
            ).fetchone()[0]
        )


def _fact_rows(project_root: Path) -> dict[str, tuple[str, ...]]:
    with open_database(project_root / "state/project.sqlite") as database:
        return {
            str(row[0]): tuple(str(value) for value in row[1:])
            for row in database.execute(
                "SELECT fact_version_id,review_state,disclosure_state,content_sha256,"
                "scientific_context_json FROM fact_versions ORDER BY fact_version_id"
            )
        }


def _export_c(
    registered: _RegisteredC, destination: Path
) -> tuple[ActiveFactBinding, ...]:
    return export_verified_consumer_bindings(
        registered.project,
        registered.snapshot,
        destination,
        c_report_data_path=registered.report_data_path,
    )


def _sidecar_payload(destination: Path) -> dict[str, object]:
    return json.loads(destination.read_text(encoding="utf-8"))


def _report_payload(registered: _RegisteredC) -> dict[str, object]:
    return json.loads(registered.report_data_path.read_text(encoding="utf-8"))


def _observation(payload: dict[str, object], row_id: str) -> dict[str, object]:
    for item in payload["observations"]:  # type: ignore[index]
        if isinstance(item, dict) and item.get("row_id") == row_id:
            return item
    raise AssertionError(f"missing observation {row_id}")


def _write_report(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    path = tmp_path / f"{name}-report.json"
    path.write_bytes(_canonical_bytes(payload))
    return path


def _pin_sidecar(
    tmp_path: Path, name: str, payload: dict[str, object], report_path: Path
) -> Path:
    payload["c_report_data_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    path = tmp_path / f"{name}-sidecar.json"
    path.write_bytes(_canonical_bytes(payload))
    return path


def _forge_manifest(
    real_manifest: Path, sidecar_path: Path, destination: Path
) -> str:
    """Re-seal a manifest around forged bytes, as an untrusted producer would."""
    payload = json.loads(real_manifest.read_text(encoding="utf-8"))
    payload["consumer_sidecar_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    payload["consumer_sidecar_bytes"] = sidecar_path.stat().st_size
    destination.write_bytes(_canonical_bytes(payload))
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def _clean_pins(
    registered: _RegisteredC, tmp_path: Path
) -> tuple[Path, Path, str]:
    sidecar = tmp_path / "clean-sidecar.json"
    _export_c(registered, sidecar)
    manifest = tmp_path / "clean-manifest.json"
    digest = seal_verified_candidate(
        registered.project,
        registered.snapshot,
        sidecar,
        manifest,
        c_report_data_path=registered.report_data_path,
    )
    return sidecar, manifest, digest


def test_current_c_consumers_survive_pinned_restore_and_idempotent_replay(
    registered_c: _RegisteredC, tmp_path: Path
) -> None:
    registered = registered_c
    sidecar = tmp_path / "c-consumers.json"
    exported = _export_c(registered, sidecar)

    assert len(exported) == _FIXED_OBSERVATIONS
    assert {binding.report for binding in exported} == {"C"}
    assert {binding.collection for binding in exported} == {"observations"}
    payload = _sidecar_payload(sidecar)
    assert payload["c_report_data_sha256"] == hashlib.sha256(
        registered.report_data_path.read_bytes()
    ).hexdigest()
    assert len(payload["bindings"]) == _FIXED_OBSERVATIONS
    assert any(str(item["row_id"]).startswith("c-pdf-") for item in payload["bindings"])
    assert any(str(item["row_id"]) == _REGISTRY_ROW for item in payload["bindings"])
    for entry in payload["bindings"]:
        binding = ActiveFactBinding.model_validate_json(str(entry["binding_json"]))
        assert binding.source_version_id
        assert entry["binding_sha256"] == hashlib.sha256(
            str(entry["binding_json"]).encode()
        ).hexdigest()
        assert entry["binding_id"] == stable_id(
            "source-portal-binding",
            str(entry["source_fact_version_id"]),
            "C",
            "observations",
            str(entry["row_id"]),
        )
    again = tmp_path / "c-consumers-again.json"
    _export_c(registered, again)
    assert again.read_bytes() == sidecar.read_bytes()

    candidate_manifest = tmp_path / "candidate.json"
    pinned = seal_verified_candidate(
        registered.project,
        registered.snapshot,
        sidecar,
        candidate_manifest,
        c_report_data_path=registered.report_data_path,
    )
    assert hashlib.sha256(candidate_manifest.read_bytes()).hexdigest() == pinned
    manifest_text = candidate_manifest.read_text(encoding="utf-8")
    assert "review-portal-data.json" not in manifest_text
    assert "bindings" not in manifest_text

    target = tmp_path / "recovered"
    locked, bindings = restore_verified_candidate(
        candidate_manifest,
        registered.project / registered.snapshot.relative_path,
        sidecar,
        target,
        expected_manifest_sha256=pinned,
        c_report_data_path=registered.report_data_path,
    )
    assert locked == registered.snapshot
    assert bindings == exported
    assert _binding_count(target) == _FIXED_OBSERVATIONS
    assert read_current_delivery(target) is None
    assert _fact_rows(target) == _fact_rows(registered.project)
    assert {value[0] for value in _fact_rows(target).values()} == {"candidate"}

    assert recover_verified_consumer_bindings(
        target, sidecar, c_report_data_path=registered.report_data_path
    ) == exported
    assert _binding_count(target) == _FIXED_OBSERVATIONS

    empty_target = tmp_path / "preexisting-empty"
    empty_target.mkdir()
    empty_locked, empty_bindings = restore_verified_candidate(
        candidate_manifest,
        registered.project / registered.snapshot.relative_path,
        sidecar,
        empty_target,
        expected_manifest_sha256=pinned,
        c_report_data_path=registered.report_data_path,
    )
    assert empty_locked == registered.snapshot and empty_bindings == exported

    with pytest.raises(VerifiedCandidateRecoveryError, match="非空|已存在"):
        restore_verified_candidate(
            candidate_manifest,
            registered.project / registered.snapshot.relative_path,
            sidecar,
            target,
            expected_manifest_sha256=pinned,
            c_report_data_path=registered.report_data_path,
        )
    assert _binding_count(target) == _FIXED_OBSERVATIONS


def test_c_export_requires_original_report_proof_and_ab_bytes_unchanged(
    registered_c: _RegisteredC, tmp_path: Path
) -> None:
    destination = tmp_path / "no-proof.json"
    with pytest.raises(PortalConsumerBindingRecoveryError, match="C 消费者"):
        export_verified_consumer_bindings(
            registered_c.project, registered_c.snapshot, destination
        )
    assert not destination.exists()

    from tests.integration.test_w04_consumer_binding_recovery import _registered_project

    root, snapshot, _version_id, _row_id = _registered_project(tmp_path / "ab")
    ab_sidecar = tmp_path / "ab-sidecar.json"
    export_verified_consumer_bindings(root, snapshot, ab_sidecar)
    ab_payload = _sidecar_payload(ab_sidecar)
    assert set(ab_payload) == {
        "schema_version",
        "project_id",
        "contract_version",
        "evidence_snapshot_id",
        "evidence_snapshot_sha256",
        "bindings",
    }
    assert {str(item["report"]) for item in ab_payload["bindings"]} == {"A", "B"}


def test_c_recovery_rejects_missing_or_wrong_report_proof_before_registry_write(
    registered_c: _RegisteredC, restored_target, tmp_path: Path
) -> None:
    registered = registered_c
    clean_sidecar, _manifest, _digest = _clean_pins(registered, tmp_path)
    base = _sidecar_payload(clean_sidecar)

    unpinned = tmp_path / "unpinned.json"
    unpinned_payload = {
        key: value for key, value in base.items() if key != "c_report_data_sha256"
    }
    unpinned.write_bytes(_canonical_bytes(unpinned_payload))
    restored = restored_target()
    with pytest.raises(PortalConsumerBindingRecoveryError, match="C 消费者"):
        recover_verified_consumer_bindings(restored, unpinned)
    assert _binding_count(restored) == 0

    with pytest.raises(PortalConsumerBindingRecoveryError, match="C 消费者"):
        recover_verified_consumer_bindings(restored, clean_sidecar)
    assert _binding_count(restored) == 0

    wrong_pin = tmp_path / "wrong-pin.json"
    wrong = {**base, "c_report_data_sha256": "0" * 64}
    wrong_pin.write_bytes(_canonical_bytes(wrong))
    with pytest.raises(PortalConsumerBindingRecoveryError, match="摘要"):
        recover_verified_consumer_bindings(
            restored, wrong_pin, c_report_data_path=registered.report_data_path
        )
    assert _binding_count(restored) == 0

    missing_file = tmp_path / "absent-report.json"
    with pytest.raises(PortalConsumerBindingRecoveryError, match="C 消费者"):
        recover_verified_consumer_bindings(
            restored, clean_sidecar, c_report_data_path=missing_file
        )
    assert _binding_count(restored) == 0


def _rebuild_binding(
    entry: dict[str, object], payload: dict[str, object], row_id: str
) -> None:
    """Adaptive forger: re-derive the binding from the forged pinned report."""
    forged = active_fact_binding_for_c(ReportCPortalData.model_validate(payload), row_id)
    encoded = forged.model_dump_json()
    entry["binding_json"] = encoded
    entry["binding_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()


def _rename_row(payload: dict[str, object]) -> None:
    _observation(payload, _REGISTRY_ROW)["row_id"] = "c-nct02264639-ghost"


def _swap_source_version(payload: dict[str, object]) -> str:
    _observation(payload, _REGISTRY_ROW)["source_version_id"] = "ctgov-nct99999999"
    return _REGISTRY_ROW


def _swap_product(payload: dict[str, object]) -> str:
    _observation(payload, _REGISTRY_ROW)["product_id"] = "nomacopan"
    return _REGISTRY_ROW


def _swap_trial(payload: dict[str, object]) -> str:
    _observation(payload, "c-nct02264639-sample-size")["trial_id"] = "nct03829449"
    return "c-nct02264639-sample-size"


def _shift_page(payload: dict[str, object]) -> str:
    _observation(payload, _PDF_ROW)["source_locator"]["page"] = 25  # type: ignore[index]
    return _PDF_ROW


def _rewrite_clause_context(payload: dict[str, object]) -> str:
    _observation(payload, _PDF_ROW)["source_clause_context"]["label_zh"] = "伪造来源主题"
    return _PDF_ROW


def _rewrite_source_text(payload: dict[str, object]) -> str:
    _observation(payload, _PDF_ROW)["source_text"] = "伪造原文，未经锁定来源证明"
    return _PDF_ROW


def _drop_row(payload: dict[str, object]) -> None:
    payload["observations"] = [  # type: ignore[index]
        item for item in payload["observations"] if item.get("row_id") != _REGISTRY_ROW
    ]


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        pytest.param(_rename_row, "不在原始报告", id="row"),
        pytest.param(_swap_source_version, "来源实例", id="source-version"),
        pytest.param(_swap_product, "产品—试验关联", id="product"),
        pytest.param(_swap_trial, "产品—试验关联", id="trial"),
        pytest.param(_shift_page, "来源定位", id="locator"),
        pytest.param(_rewrite_clause_context, "语境", id="clause-context"),
        pytest.param(_rewrite_source_text, "原文|规范值", id="quote"),
        pytest.param(_drop_row, "不在原始报告", id="incomplete"),
    ],
)
def test_forged_c_original_report_proof_fails_closed_before_publish(
    registered_c: _RegisteredC,
    restored_target,
    tmp_path: Path,
    mutate,
    match: str,
) -> None:
    registered = registered_c
    clean_sidecar, clean_manifest, _digest = _clean_pins(registered, tmp_path)
    payload = _report_payload(registered)
    touched = mutate(payload)
    report_path = _write_report(tmp_path, "forged", payload)
    sidecar_payload = _sidecar_payload(clean_sidecar)
    if touched is not None:
        entry = next(
            item for item in sidecar_payload["bindings"] if item["row_id"] == touched
        )
        _rebuild_binding(entry, payload, touched)
    forged_sidecar = _pin_sidecar(tmp_path, "forged", sidecar_payload, report_path)
    forged_manifest = tmp_path / "forged-manifest.json"
    forged_digest = _forge_manifest(clean_manifest, forged_sidecar, forged_manifest)

    target = tmp_path / "must-not-exist"
    with pytest.raises(VerifiedCandidateRecoveryError):
        restore_verified_candidate(
            forged_manifest,
            registered.project / registered.snapshot.relative_path,
            forged_sidecar,
            target,
            expected_manifest_sha256=forged_digest,
            c_report_data_path=report_path,
        )
    assert not target.exists()

    restored = restored_target()
    with pytest.raises(PortalConsumerBindingRecoveryError, match=match):
        recover_verified_consumer_bindings(
            restored, forged_sidecar, c_report_data_path=report_path
        )
    assert _binding_count(restored) == 0


def test_self_consistent_forged_binding_json_is_not_a_proof(
    registered_c: _RegisteredC, restored_target, tmp_path: Path
) -> None:
    registered = registered_c
    clean_sidecar, _manifest, _digest = _clean_pins(registered, tmp_path)
    payload = _sidecar_payload(clean_sidecar)
    entry = next(
        item for item in payload["bindings"] if item["row_id"] == _REGISTRY_ROW
    )
    binding = ActiveFactBinding.model_validate_json(str(entry["binding_json"]))
    encoded = binding.model_copy(
        update={"unit": "mg", "normalized_unit": "mg"}
    ).model_dump_json()
    entry["binding_json"] = encoded
    entry["binding_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    forged = tmp_path / "rehashed.json"
    forged.write_bytes(_canonical_bytes(payload))

    restored = restored_target()
    with pytest.raises(PortalConsumerBindingRecoveryError, match="身份不一致"):
        recover_verified_consumer_bindings(
            restored, forged, c_report_data_path=registered.report_data_path
        )
    assert _binding_count(restored) == 0


def test_capture_instance_alias_cannot_be_replaced_by_warehouse_version(
    registered_c: _RegisteredC, restored_target, tmp_path: Path
) -> None:
    registered = registered_c
    clean_sidecar, _manifest, _digest = _clean_pins(registered, tmp_path)
    payload = _sidecar_payload(clean_sidecar)
    entry = next(
        item for item in payload["bindings"] if item["row_id"] == _REGISTRY_ROW
    )
    with open_database(registered.project / "state/project.sqlite") as database:
        immutable = str(
            database.execute(
                "SELECT f.source_version_id FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?",
                (entry["source_fact_version_id"],),
            ).fetchone()[0]
        )
    assert immutable.startswith("source-version_")

    report_payload = _report_payload(registered)
    _observation(report_payload, _REGISTRY_ROW)["source_version_id"] = immutable
    report_path = _write_report(tmp_path, "alias", report_payload)
    _rebuild_binding(entry, report_payload, _REGISTRY_ROW)
    forged_sidecar = _pin_sidecar(tmp_path, "alias", payload, report_path)

    restored = restored_target()
    with pytest.raises(PortalConsumerBindingRecoveryError, match="来源实例"):
        recover_verified_consumer_bindings(
            restored, forged_sidecar, c_report_data_path=report_path
        )
    assert _binding_count(restored) == 0


def test_duplicate_or_conflicting_c_entries_never_write_partial_registry(
    registered_c: _RegisteredC, restored_target, tmp_path: Path
) -> None:
    registered = registered_c
    clean_sidecar, _manifest, _digest = _clean_pins(registered, tmp_path)
    payload = _sidecar_payload(clean_sidecar)
    entry = next(
        item for item in payload["bindings"] if item["row_id"] == _REGISTRY_ROW
    )

    duplicated = tmp_path / "duplicated.json"
    duplicated.write_bytes(
        _canonical_bytes({**payload, "bindings": [*payload["bindings"], entry]})
    )
    restored = restored_target()
    with pytest.raises(PortalConsumerBindingRecoveryError, match="重复"):
        recover_verified_consumer_bindings(
            restored, duplicated, c_report_data_path=registered.report_data_path
        )
    assert _binding_count(restored) == 0

    other = next(
        item for item in payload["bindings"]
        if item["row_id"] == "c-nct02264639-sample-size"
    )
    conflicted = tmp_path / "conflicted.json"
    conflicted.write_bytes(
        _canonical_bytes(
            {**payload, "bindings": [entry, {**other, "binding_id": entry["binding_id"]}]}
        )
    )
    restored = restored_target()
    with pytest.raises(PortalConsumerBindingRecoveryError):
        recover_verified_consumer_bindings(
            restored, conflicted, c_report_data_path=registered.report_data_path
        )
    assert _binding_count(restored) == 0


def test_ab_entry_reissued_as_c_still_raises_c_identity_error(tmp_path: Path) -> None:
    from tests.integration.test_w04_consumer_binding_recovery import (
        _registered_project,
        _restore,
    )

    root, snapshot, _version_id, _row_id = _registered_project(tmp_path)
    exported = tmp_path / "ab.json"
    export_verified_consumer_bindings(root, snapshot, exported)
    payload = _sidecar_payload(exported)
    original = payload["bindings"][0]
    binding = ActiveFactBinding.model_validate_json(str(original["binding_json"]))
    claimed = binding.model_copy(update={"report": "C", "collection": "observations"})
    encoded = claimed.model_dump_json()
    forged_entry = {
        **original,
        "report": "C",
        "collection": "observations",
        "binding_json": encoded,
        "binding_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "binding_id": stable_id(
            "source-portal-binding",
            str(original["source_fact_version_id"]),
            "C",
            "observations",
            str(original["row_id"]),
        ),
    }
    forged = tmp_path / "ab-as-c.json"
    forged.write_bytes(_canonical_bytes({**payload, "bindings": [forged_entry]}))

    restored, _manifest_path = _restore(tmp_path, root, snapshot)
    with pytest.raises(PortalConsumerBindingRecoveryError, match="C 消费者"):
        recover_verified_consumer_bindings(restored, forged)
    assert _binding_count(restored) == 0

    target = tmp_path / "ab-as-c-target"
    manifest_payload = VerifiedCandidateManifest(
        schema_version="1.0",
        project_id=str(json.loads((root / snapshot.relative_path).read_text())[
            "project_id"
        ]),
        evidence_snapshot_id=snapshot.snapshot_id,
        evidence_snapshot_sha256=snapshot.sha256,
        evidence_snapshot_bytes=snapshot.byte_size,
        consumer_sidecar_sha256=hashlib.sha256(forged.read_bytes()).hexdigest(),
        consumer_sidecar_bytes=forged.stat().st_size,
        consumer_binding_count=1,
    )
    manifest_path = tmp_path / "ab-as-c-manifest.json"
    manifest_path.write_bytes(_canonical_bytes(manifest_payload.model_dump(mode="json")))
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    with pytest.raises(VerifiedCandidateRecoveryError):
        restore_verified_candidate(
            manifest_path,
            root / snapshot.relative_path,
            forged,
            target,
            expected_manifest_sha256=digest,
        )
    assert not target.exists()


@pytest.mark.parametrize("column", ["raw_value", "normalized_value", "review_state"])
def test_persisted_c_fact_columns_cannot_drift_from_the_locked_closure(
    registered_c: _RegisteredC, restored_target, tmp_path: Path, column: str,
) -> None:
    sidecar, _manifest, _pin = _clean_pins(registered_c, tmp_path)
    restored = restored_target()
    version = registered_c.versions[_REGISTRY_ROW]
    # Simulate a damaged recovery DB, not a permitted source edit. Only this
    # disposable fixture loses its append-only triggers; originals remain frozen.
    with open_database(restored / "state/project.sqlite") as database:
        triggers = database.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='fact_versions'"
        ).fetchall()
        for (name,) in triggers:
            database.execute('DROP TRIGGER "' + str(name).replace('"', '""') + '"')
        value = "accepted" if column == "review_state" else "damaged persisted column"
        database.execute(
            f"UPDATE fact_versions SET {column}=? WHERE fact_version_id=?", (value, version),
        )
    with pytest.raises(PortalConsumerBindingRecoveryError, match="锁定闭包"):
        recover_verified_consumer_bindings(
            restored, sidecar, c_report_data_path=registered_c.report_data_path,
        )
    assert _binding_count(restored) == 0
