"""Replay tooling must verify its fixed source before creating a working copy."""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from tools.replay_r24_current_chain import (
    prepare_working_copy,
    replay_from_source,
    resolve_contained_relative,
    share_product_query,
    validate_current_safety_projection,
    verify_source_binding,
    verify_source_candidate,
    verify_source_receipt,
)

PROJECT_ID = "project_replay_test"


def test_current_share_preserves_identity_with_report_specific_filter_values() -> None:
    payload = {"products": [{"id": "dupilumab-sar231893", "name": "度普利尤单抗注射液"}]}
    assert share_product_query("A", payload, "dupilumab-sar231893") == {
        "product": ("度普利尤单抗注射液",),
    }
    assert share_product_query("B", payload, "dupilumab-sar231893") == {
        "product": ("dupilumab-sar231893",),
    }


@pytest.mark.parametrize("products", [
    [], [{"id": "other", "name": "度普利尤单抗注射液"}],
    [{"id": "dupilumab", "name": ""}],
    [{"id": "dupilumab", "name": "原名"}, {"id": "dupilumab", "name": "正式名"}],
])
def test_share_product_filter_rejects_missing_or_ambiguous_identity(
    products: list[dict[str, str]],
) -> None:
    with pytest.raises(ValueError, match="product identity"):
        share_product_query("A", {"products": products}, "dupilumab")


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _project_yaml(project_id: str, *, workflow_version: str = "0.1.0a0") -> str:
    return json.dumps(
        {
            "schema_version": "1.0",
            "workflow_version": workflow_version,
            "active_contract_version": 1,
            "project_contract_versions": [{
                "schema_version": "1.0", "contract_version": 1, "project_id": project_id,
                "indication": "隔离合同测试", "reports": ["A", "B"], "outputs": ["html"],
                "timezone": "UTC", "data_cutoff": "2026-10-07T00:00:00Z",
                "cutoff_was_user_supplied": True, "created_at": "2026-10-07T00:00:00Z",
            }],
        }
    )


def _build_source_project(parent: Path, *, identity: bool = True) -> Path:
    source = parent / "source"
    (source / "state/checkpoints").mkdir(parents=True)
    for relative in (
        "evidence/raw", "evidence/fragments", "evidence/library", "evidence/manual-inbox",
        "evidence/quarantine", "snapshots/evidence", "reports/A", "reports/B", "reports/C",
        "logs/diagnostics", "blockers/A", "blockers/B", "blockers/C", "coverage", "events",
        "manifests", "receipts", "corrections/inbox", "monitoring/inbox",
    ):
        (source / relative).mkdir(parents=True, exist_ok=True)
    (source / "project.yaml").write_text(_project_yaml(PROJECT_ID), encoding="utf-8")
    database = sqlite3.connect(source / "state/project.sqlite")
    database.execute("CREATE TABLE t(value TEXT)")
    database.execute("INSERT INTO t VALUES ('keep')")
    database.commit()
    database.close()
    (source / "evidence/library/a.json").write_bytes(b'{"report":"A"}')
    (source / "evidence/library/b.json").write_bytes(b'{"report":"B"}')
    if identity:
        (source / "evidence/library/portal-identity-context.json").write_bytes(b"{}")
    (source / "snapshots/evidence/evidence-snapshot_test.json").write_bytes(b'{"schema":"v"}')
    (source / "reports/source-v3/A").mkdir(parents=True)
    (source / "reports/source-v3/A/page.html").write_text("<html>rendered</html>", encoding="utf-8")
    return source


def _build_receipt(source: Path) -> dict[str, Any]:
    a_bytes = (source / "evidence/library/a.json").read_bytes()
    b_bytes = (source / "evidence/library/b.json").read_bytes()
    snapshot = source / "snapshots/evidence/evidence-snapshot_test.json"
    return {
        "schema_version": "r24-test-receipt-1",
        "project_id": PROJECT_ID,
        "snapshot_id": "evidence-snapshot_test",
        "snapshot_sha256": _sha(snapshot.read_bytes()),
        "snapshot_relative_path": "snapshots/evidence/evidence-snapshot_test.json",
        "source_version_ids": ["source-version_test"],
        "fact_bindings": [
            {"row_ref": "safety:safe-test", "fact_version_id": "fact-version_test"},
        ],
        "registered_a_efficacy_consumers": [],
        "registered_a_safety_consumers": ["safe-test"],
        "bound_report_data": {
            "relative_path": "evidence/library/a.json",
            "sha256": _sha(a_bytes),
            "bytes": len(a_bytes),
        },
        "bound_b_report_data": {
            "relative_path": "evidence/library/b.json",
            "sha256": _sha(b_bytes),
            "bytes": len(b_bytes),
        },
    }


def test_public_clear_keeps_chinese_label_and_original_source() -> None:
    row = {"value": None, "source_text": "1", "numerator": None,
           "denominator": None, "disclosure_state": "用户清除，待重新核实"}
    validate_current_safety_projection(row, expected=None, original_source="1")
    for field, value in (("value", 0), ("source_text", ""), ("numerator", 1),
                         ("disclosure_state", "来源未公开")):
        with pytest.raises(AssertionError):
            validate_current_safety_projection(
                {**row, field: value}, expected=None, original_source="1",
            )


def test_replay_rejects_source_drift_before_copying(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    inputs = candidate / "source-project/inputs"
    inputs.mkdir(parents=True)
    for name in ("a", "b"):
        (inputs / f"{name}.json").write_text("{}")
    manifest = {
        "current_generation_switched": False,
        "source_snapshot_sha256": "0" * 64,
        "rendered_files": {
            f"source-project/inputs/{name}.json": sha256(b"{}").hexdigest()
            for name in ("a", "b")
        },
    }
    (candidate / "candidate-manifest.json").write_text(json.dumps(manifest))
    (inputs / "a.json").write_text('{"changed":true}')
    with pytest.raises(ValueError, match="drift"):
        verify_source_candidate(tmp_path, candidate)


def test_replay_rejects_out_of_root_or_symlink_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside"):
        verify_source_candidate(tmp_path, tmp_path.parent)
    target = tmp_path / "source"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        verify_source_candidate(tmp_path, link)


def test_source_receipt_pin_and_shape_fail_closed(tmp_path: Path) -> None:
    source = _build_source_project(tmp_path)
    receipt = _build_receipt(source)
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    digest = _sha(path.read_bytes())
    assert verify_source_receipt(path, digest) == receipt
    with pytest.raises(ValueError, match="sha256"):
        verify_source_receipt(path, "0" * 64)
    incomplete = {key: value for key, value in receipt.items() if key != "snapshot_id"}
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(incomplete), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        verify_source_receipt(broken, _sha(broken.read_bytes()))
    broken.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="object"):
        verify_source_receipt(broken, _sha(broken.read_bytes()))
    orphan = {**receipt, "registered_a_safety_consumers": ["safe-test", "safe-unknown"]}
    path.write_text(json.dumps(orphan), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        verify_source_receipt(path, _sha(path.read_bytes()))


def test_contained_relative_rejects_traversal_and_symlinks(tmp_path: Path) -> None:
    base = tmp_path / "base"
    (base / "inner").mkdir(parents=True)
    (base / "inner/data.json").write_text("{}", encoding="utf-8")
    assert resolve_contained_relative(base, "inner/data.json", what="input") == (
        base / "inner/data.json"
    ).resolve()
    for candidate in ("../outside.json", "/etc/hosts", "inner\\data.json", "", "a/../../x"):
        with pytest.raises(ValueError, match="relative"):
            resolve_contained_relative(base, candidate, what="input")
    link = base / "link"
    link.symlink_to(base / "inner")
    with pytest.raises(ValueError, match="symlink"):
        resolve_contained_relative(base, "link/data.json", what="input")


def test_source_binding_rejects_drift_traversal_and_existing_current(tmp_path: Path) -> None:
    source = _build_source_project(tmp_path)
    receipt = _build_receipt(source)
    binding = verify_source_binding(source, receipt)
    assert binding["project_id"] == PROJECT_ID
    assert binding["source_inputs"]["A"]["sha256"] == receipt["bound_report_data"]["sha256"]

    traversal = {**receipt, "bound_report_data": {"relative_path": "../a.json", "sha256": "x"}}
    with pytest.raises(ValueError, match="relative"):
        verify_source_binding(source, traversal)
    absolute = {**receipt, "bound_report_data": {"relative_path": "/tmp/a.json", "sha256": "x"}}
    with pytest.raises(ValueError, match="relative"):
        verify_source_binding(source, absolute)

    (source / "evidence/library/a.json").write_bytes(b"drifted")
    with pytest.raises(ValueError, match="drifted"):
        verify_source_binding(source, receipt)
    (source / "evidence/library/a.json").write_bytes(b'{"report":"A"}')

    drifted_snapshot = {**receipt, "snapshot_sha256": "1" * 64}
    with pytest.raises(ValueError, match="drifted"):
        verify_source_binding(source, drifted_snapshot)

    (source / "project.yaml").write_text(_project_yaml("project_other"), encoding="utf-8")
    with pytest.raises(ValueError, match="contract"):
        verify_source_binding(source, receipt)
    (source / "project.yaml").write_text(
        _project_yaml(PROJECT_ID, workflow_version="9.9.9"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="workflow version"):
        verify_source_binding(source, receipt)
    (source / "project.yaml").write_text(_project_yaml(PROJECT_ID), encoding="utf-8")

    (source / "reports/current.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="current"):
        verify_source_binding(source, receipt)


def test_prepare_working_copy_fail_closed_before_any_write(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = _build_source_project(root)
    leak = source / "logs/leak.json"
    leak.symlink_to(source / "project.yaml")
    output = root / "output"
    with pytest.raises(ValueError, match="symlink"):
        prepare_working_copy(root, source, output)
    assert not output.exists()
    leak.unlink()

    output.mkdir()
    with pytest.raises(ValueError, match="fresh"):
        prepare_working_copy(root, source, output)
    output.rmdir()

    with pytest.raises(ValueError, match="overlap"):
        prepare_working_copy(root, source, source / "inner")
    with pytest.raises(ValueError, match="authorized"):
        prepare_working_copy(root, source, tmp_path / "outside")


@pytest.mark.parametrize("journal_mode", ["DELETE", "WAL"])
def test_prepare_working_copy_preserves_identity_without_touching_source(
    tmp_path: Path, journal_mode: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = _build_source_project(root)
    connection = sqlite3.connect(source / "state/project.sqlite")
    connection.execute(f"PRAGMA journal_mode={journal_mode}")
    connection.close()
    identity_bytes = (source / "evidence/library/portal-identity-context.json").read_bytes()
    database_bytes = (source / "state/project.sqlite").read_bytes()
    result = prepare_working_copy(root, source, root / "output")
    project = root / "output" / "project"

    assert result["identity_binding_sha256"] == _sha(identity_bytes)
    assert (project / "evidence/library/portal-identity-context.json").read_bytes() == (
        identity_bytes
    )
    assert not (project / "reports/source-v3").exists()
    for relative in ("reports/A", "snapshots/reports/A", "state/checkpoints", "logs/diagnostics"):
        assert (project / relative).is_dir()
    with sqlite3.connect(project / "state/project.sqlite") as captured:
        assert captured.execute("SELECT value FROM t").fetchall() == [("keep",)]
    assert result["source_database"]["sha256"] == _sha(database_bytes)
    assert result["captured_database"]["bytes"] > 0
    assert "reports" in result["excluded_relative_paths"]
    assert (source / "state/project.sqlite").read_bytes() == database_bytes
    assert not (source / "state/project.sqlite-wal").exists()
    assert not (source / "state/project.sqlite-shm").exists()

    bare = _build_source_project(root / "bare", identity=False)
    bare_result = prepare_working_copy(root, bare, root / "output-bare")
    assert bare_result["identity_binding_sha256"] is None


def test_duplicate_scientific_bindings_are_not_last_wins(tmp_path: Path) -> None:
    source = _build_source_project(tmp_path)
    receipt = _build_receipt(source)
    receipt["fact_bindings"].append({
        "row_ref": "safety:safe-test", "fact_version_id": "different-scientific-version",
    })
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="duplicate"):
        verify_source_receipt(path, _sha(path.read_bytes()))


@pytest.mark.parametrize("target", ["project.yaml", "state", "reports/current.json"])
def test_source_binding_refuses_indirect_or_dangling_paths(tmp_path: Path, target: str) -> None:
    source = _build_source_project(tmp_path)
    receipt = _build_receipt(source)
    original = source / target
    if original.exists():
        moved = source / (target.replace("/", "-") + "-original")
        original.rename(moved)
    else:
        moved = source / "missing-current"
    original.symlink_to(moved, target_is_directory=target == "state")
    with pytest.raises(ValueError, match="symlink"):
        verify_source_binding(source, receipt)


def test_replay_never_reads_out_of_authorized_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = _build_source_project(tmp_path / "outside")
    output = root / "output"
    with pytest.raises(ValueError, match="authorized"):
        prepare_working_copy(root, outside, output)

    def forbidden_read(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("boundary was checked after an external read")

    monkeypatch.setattr("tools.replay_r24_current_chain.verify_source_receipt", forbidden_read)
    for source, receipt in ((outside, root / "receipt.json"),
                            (root / "source", tmp_path / "outside-receipt.json")):
        with pytest.raises(ValueError, match="authorized"):
            replay_from_source(root, source, receipt, "0" * 64, output)
    assert not output.exists()


def test_nonempty_wal_rejects_before_any_copy(tmp_path: Path) -> None:
    source = _build_source_project(tmp_path)
    wal = source / "state/project.sqlite-wal"
    wal.write_bytes(b"unsettled-frames")
    with pytest.raises(ValueError, match="WAL"):
        prepare_working_copy(tmp_path, source, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    assert wal.read_bytes() == b"unsettled-frames"


def test_source_contract_validated_before_clone(tmp_path: Path) -> None:
    source = _build_source_project(tmp_path)
    receipt = _build_receipt(source)
    document = json.loads((source / "project.yaml").read_text())
    document["project_contract_versions"][0]["reports"] = []
    (source / "project.yaml").write_text(json.dumps(document))
    with pytest.raises(ValueError, match="contract"):
        verify_source_binding(source, receipt)
