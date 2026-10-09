"""同一科学事实在不同新候选快照下的消费者作用域合同测试。

真实链路（真实项目合同、真实摄取与证据快照、真实 C 门户渲染事务、真实登记
与恢复；不写手写接受 SQL、不伪造回执、不渲染假 current）：

- 正向迁移只把唯一性范围从 (事实, 报告) 扩为 (事实, 报告, 证据快照)，既有权
  字节、标识、摘要与时间逐字节保留，append-only 守卫仍在；
- 新候选快照可以原样复用科学事实：同一事实在旧快照与新快照各自登记，旧行
  不被覆盖，新行使用包含证据快照的限定标识，重复登记幂等；
- 无 current 的 C 预览中，公开事实查询只在唯一候选时保留既有行为，同一报告
  行出现跨快照冲突声明时失败关闭，不按插入顺序取用；
- 有 current 时按实际当前渲染/锁定来源作用域裁决冲突；
- 同一快照内同一事实的冲突绑定整批拒绝，不留下半批写入；
- 恢复只接受精确快照作用域：新标识必须携带被恢复的精确快照，历史遗留标识
  只在各自原始作用域下接受，不能被另一作用域复用。
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.c_portal_consumer_registry import (
    CPortalConsumerRegistrationError,
    register_c_source_consumers,
)
from ci_workflow.application.latest_delivery import (
    CurrentDeliveryBundle,
    CurrentReportDelivery,
    read_current_delivery,
)
from ci_workflow.application.portal_consumer_binding_recovery import (
    PortalConsumerBindingRecoveryError,
    export_verified_consumer_bindings,
    recover_verified_consumer_bindings,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.application.user_fact_edit import (
    UserFactEditService,
    UserFactSaveError,
    fact_revision_digest,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)
from ci_workflow.storage.migrations import apply_migrations, migration_directory
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tests.integration.test_1007_c_source_review_entry import (
    _AT,
    _CONTRACT_CUTOFF,
    _open_readonly,
    _pending_content_payload,
    _prepare,
    _write_content,
)

_BINDING_KIND = "source-portal-binding"


@dataclass(frozen=True)
class _EpochWorld:
    root: Path
    payload: dict[str, object]
    first: Any
    second: Any
    second_input: Path
    first_rows: tuple[tuple[str, ...], ...]
    first_fact_count: int

    @property
    def row_count(self) -> int:
        return len(self.payload["report_data"]["observations"])  # type: ignore[index]

    @property
    def changed_row(self) -> str:
        return str(self.payload["report_data"]["observations"][0]["row_id"])  # type: ignore[index]

    @property
    def unchanged_row(self) -> str:
        return str(self.payload["report_data"]["observations"][1]["row_id"])  # type: ignore[index]


def _two_epochs(tmp_path: Path) -> _EpochWorld:
    contract = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff=_CONTRACT_CUTOFF
    )
    root = create_project_workspace(tmp_path / "快照项目", contract)
    payload = _pending_content_payload()
    first_input = _write_content(root, payload)
    first = _prepare(root, first_input)
    first_rows = _binding_rows(root)
    first_fact_count = _fact_count(root)
    changed = json.loads(json.dumps(payload, default=str))
    changed["report_version"] = "v2"
    changed["report_data"]["report_version"] = "v2"
    changed["report_data"]["observations"][0]["display_text"] = "经原文核对的新中文呈现"
    second_input = first_input.with_name("corrected-content.json")
    second_input.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    second = _prepare(root, second_input, produced_at=_AT + timedelta(minutes=5))
    return _EpochWorld(
        root=root,
        payload=payload,
        first=first,
        second=second,
        second_input=second_input,
        first_rows=first_rows,
        first_fact_count=first_fact_count,
    )


def _binding_rows(root: Path) -> tuple[tuple[str, ...], ...]:
    database = _open_readonly(root)
    try:
        return tuple(
            tuple(str(value) for value in row)
            for row in database.execute(
                "SELECT binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at "
                "FROM source_portal_consumer_bindings ORDER BY binding_id"
            ).fetchall()
        )
    finally:
        database.close()


def _fact_count(root: Path) -> int:
    database = _open_readonly(root)
    try:
        return int(database.execute("SELECT COUNT(*) FROM fact_versions").fetchone()[0])
    finally:
        database.close()


def _closure_fact_versions(root: Path, snapshot_id: str) -> dict[str, str]:
    payload = json.loads(
        (root / "snapshots" / "evidence" / f"{snapshot_id}.json").read_bytes()
    )
    return {
        str(item["fact"]["fact_id"]): str(item["fact_version_id"])
        for item in payload["closure"]["facts"]
    }


def _locked(root: Path, snapshot_id: str) -> LockedSnapshot:
    manifest = root / "snapshots" / "evidence" / f"{snapshot_id}.json"
    return LockedSnapshot(
        snapshot_id=snapshot_id,
        kind="evidence",
        report=None,
        sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        relative_path=manifest.relative_to(root).as_posix(),
        byte_size=manifest.stat().st_size,
    )


def _captures(payload: dict[str, object]) -> dict[str, SourceCapture]:
    return {
        item["source_id"]: SourceCapture.model_validate(item)
        for item in payload["sources"]  # type: ignore[union-attr]
    }


def _report_of(outcome: Any) -> ReportCPortalData:
    return ReportCPortalData.model_validate_json(outcome.report_data_path.read_bytes())


def _restore_target(tmp_path: Path, root: Path, snapshot_id: str, name: str) -> Path:
    manifest_copy = tmp_path / f"{name}-manifest.json"
    shutil.copy2(root / "snapshots" / "evidence" / f"{snapshot_id}.json", manifest_copy)
    target = tmp_path / name
    SnapshotStore(target).restore_evidence_manifest(manifest_copy)
    return target


def _legacy_sidecar(source: Path, destination: Path) -> Path:
    """Rebuild one exported sidecar with pre-snapshot legacy binding ids."""
    payload = json.loads(source.read_text(encoding="utf-8"))
    for entry in payload["bindings"]:
        entry["binding_id"] = stable_id(
            _BINDING_KIND,
            str(entry["source_fact_version_id"]),
            str(entry["report"]),
            str(entry["collection"]),
            str(entry["row_id"]),
        )
    destination.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return destination


def test_forward_migration_preserves_binding_rows_and_rescopes_uniqueness(
    tmp_path: Path,
) -> None:
    legacy_root = tmp_path / "legacy-migrations"
    legacy_root.mkdir()
    source = migration_directory()
    for path in sorted(source.glob("*.sql"))[:17]:
        shutil.copy2(path, legacy_root / path.name)
    database_path = tmp_path / "state" / "project.sqlite"
    apply_migrations(database_path, migrations_root=legacy_root)

    now = "2026-10-01T00:00:00+00:00"
    seeded = (
        (
            "source-portal-binding_legacy-c", "fact-version-legacy-c",
            "evidence-snapshot-legacy-1", "C", "observations", "c-row-legacy-1",
            '{"row_id":"c-row-legacy-1","report":"C"}',
            hashlib.sha256(b'{"row_id":"c-row-legacy-1","report":"C"}').hexdigest(),
            "2026-10-01T00:00:00+00:00",
        ),
        (
            "source-portal-binding_legacy-a", "fact-version-legacy-a",
            "evidence-snapshot-legacy-1", "A", "efficacy", "eff-legacy-1",
            '{"row_id":"eff-legacy-1","report":"A"}',
            hashlib.sha256(b'{"row_id":"eff-legacy-1","report":"A"}').hexdigest(),
            "2026-10-01T00:00:01+00:00",
        ),
    )
    database = sqlite3.connect(database_path)
    try:
        database.execute("PRAGMA foreign_keys = ON")
        for entity_id, name in (("entity-legacy-c", "Legacy C"), ("entity-legacy-a", "Legacy A")):
            database.execute(
                "INSERT INTO entities (entity_id,entity_type,canonical_name,created_at) "
                "VALUES (?,?,?,?)",
                (entity_id, "trial", name, now),
            )
        database.execute(
            "INSERT INTO source_versions (source_version_id,source_id,content_sha256,"
            "acquired_at,created_at) VALUES (?,?,?,?,?)",
            (
                "source-version-legacy", "source-legacy",
                hashlib.sha256(b"legacy source").hexdigest(), now, now,
            ),
        )
        database.execute(
            "INSERT INTO evidence_fragments (fragment_id,source_version_id,locator,"
            "content_text,content_sha256,created_at) VALUES (?,?,?,?,?,?)",
            (
                "fragment-legacy", "source-version-legacy", '{"field_path":"$.legacy"}',
                "legacy text", hashlib.sha256(b"legacy text").hexdigest(), now,
            ),
        )
        for version_id, fact_id, entity_id in (
            ("fact-version-legacy-c", "c-row-legacy-1", "entity-legacy-c"),
            ("fact-version-legacy-a", "eff-legacy-1", "entity-legacy-a"),
        ):
            database.execute(
                "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,"
                "raw_value,normalized_value,disclosure_state,review_state,"
                "primary_fragment_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    version_id, fact_id, entity_id, "legacy.field", "1", "1",
                    "reported_value", "candidate", "fragment-legacy", now,
                ),
            )
        database.executemany(
            "INSERT INTO source_portal_consumer_bindings (binding_id,"
            "source_fact_version_id,evidence_snapshot_id,report,collection,row_id,"
            "binding_json,binding_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            seeded,
        )
        database.commit()
    finally:
        database.close()

    applied = apply_migrations(database_path)
    assert [migration.version for migration in applied] == [18]
    assert [migration.version for migration in apply_migrations(database_path)] == []

    database = sqlite3.connect(database_path)
    try:
        rows = tuple(
            database.execute(
                "SELECT binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at "
                "FROM source_portal_consumer_bindings ORDER BY binding_id"
            ).fetchall()
        )
        assert rows == tuple(
            sorted(tuple(value for value in row) for row in seeded)
        )
        assert database.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0] == 18
        assert database.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' "
            "AND name='idx_source_portal_one_row_per_fact_report'"
        ).fetchone()[0] == 0
        assert database.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' "
            "AND name='idx_source_portal_bindings_snapshot'"
        ).fetchone()[0] == 1
        # 同一事实、同一报告行可以在新的不可变快照下追加，旧行不受影响。
        database.execute(
            "INSERT INTO source_portal_consumer_bindings (binding_id,"
            "source_fact_version_id,evidence_snapshot_id,report,collection,row_id,"
            "binding_json,binding_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "source-portal-binding_scoped-c", "fact-version-legacy-c",
                "evidence-snapshot-legacy-2", "C", "observations", "c-row-legacy-1",
                '{"row_id":"c-row-legacy-1","report":"C"}',
                hashlib.sha256(b'{"row_id":"c-row-legacy-1","report":"C"}').hexdigest(),
                "2026-10-02T00:00:00+00:00",
            ),
        )
        # 同一快照内的同一事实仍只有一个消费者身份。
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            database.execute(
                "INSERT INTO source_portal_consumer_bindings (binding_id,"
                "source_fact_version_id,evidence_snapshot_id,report,collection,row_id,"
                "binding_json,binding_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    "source-portal-binding_scoped-c-conflict", "fact-version-legacy-c",
                    "evidence-snapshot-legacy-2", "C", "observations", "c-row-legacy-1",
                    '{"row_id":"c-row-legacy-1","report":"C"}',
                    hashlib.sha256(b'{"row_id":"c-row-legacy-1","report":"C"}').hexdigest(),
                    "2026-10-02T00:00:01+00:00",
                ),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "UPDATE source_portal_consumer_bindings SET row_id='other' "
                "WHERE binding_id='source-portal-binding_legacy-c'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "DELETE FROM source_portal_consumer_bindings "
                "WHERE binding_id='source-portal-binding_legacy-c'"
            )
        database.rollback()
    finally:
        database.close()


def test_second_candidate_snapshot_reuses_facts_and_registers_alongside_original_rows(
    tmp_path: Path,
) -> None:
    world = _two_epochs(tmp_path)
    root = world.root
    assert world.second.evidence_snapshot_id != world.first.evidence_snapshot_id
    rows = _binding_rows(root)
    before_by_id = {row[0]: row for row in world.first_rows}
    after_by_id = {row[0]: row for row in rows}
    # 旧快照行逐字节保留；新快照只追加。
    assert set(before_by_id) < set(after_by_id)
    for binding_id, row in before_by_id.items():
        assert after_by_id[binding_id] == row
    added = [row for row in rows if row[0] not in before_by_id]
    assert len(added) == world.row_count
    assert {row[2] for row in added} == {world.second.evidence_snapshot_id}
    assert {row[2] for row in world.first_rows} == {world.first.evidence_snapshot_id}
    for row in added:
        assert row[0] == stable_id(
            _BINDING_KIND, row[1], "C", "observations", row[5], row[2]
        )
    # 科学事实原样复用：两个快照的闭包事实版本一致，且没有新建事实版本。
    assert _closure_fact_versions(
        root, world.first.evidence_snapshot_id
    ) == _closure_fact_versions(root, world.second.evidence_snapshot_id)
    assert _fact_count(root) == world.first_fact_count

    def _row_for(snapshot_id: str, row_id: str) -> tuple[str, ...]:
        return next(
            row for row in rows if row[2] == snapshot_id and row[5] == row_id
        )

    # 已修正显示的行：同一科学事实、不同原始行身份，各自持有快照限定标识。
    changed_first = _row_for(world.first.evidence_snapshot_id, world.changed_row)
    changed_second = _row_for(world.second.evidence_snapshot_id, world.changed_row)
    assert changed_first[1] == changed_second[1]
    assert changed_first[6] != changed_second[6]
    assert changed_first[0] != changed_second[0]
    # 未变化的行：科学身份与行身份逐字节一致，只是快照限定标识不同。
    unchanged_first = _row_for(world.first.evidence_snapshot_id, world.unchanged_row)
    unchanged_second = _row_for(world.second.evidence_snapshot_id, world.unchanged_row)
    assert unchanged_first[6] == unchanged_second[6]
    assert unchanged_first[7] == unchanged_second[7]
    assert unchanged_first[0] != unchanged_second[0]

    # 精确重放不新增、不覆盖既有行。
    _prepare(root, world.second_input, produced_at=None)
    assert _binding_rows(root) == rows


def test_public_fact_without_current_fails_on_conflicting_snapshots_and_keeps_unique_candidate(
    tmp_path: Path,
) -> None:
    world = _two_epochs(tmp_path)
    root = world.root
    assert read_current_delivery(root) is None
    service = UserFactEditService(root)
    versions = _closure_fact_versions(root, world.second.evidence_snapshot_id)
    # 显示修正行在两个快照下身份不同：无 current 不得按插入顺序取一行。
    with pytest.raises(UserFactSaveError, match="作用域"):
        service._public_fact(service._fact_row(versions[world.changed_row]))
    # 未变化行只有唯一候选：保留既有单快照读法。
    public = service._public_fact(service._fact_row(versions[world.unchanged_row]))
    assert len(public["consumer_bindings"]) == 1
    (selected,) = (
        ActiveFactBinding.model_validate(item) for item in public["consumer_bindings"]
    )
    assert selected == active_fact_binding_for_c(_report_of(world.second), world.unchanged_row)


def test_current_delivery_selects_the_legitimate_rendered_source_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """有 current 时，冲突声明必须由实际当前渲染/锁定来源作用域裁决。

    本测试只供给“已提交 current 指针”这一层（真实 builder 输入字节与其哈希仍
    逐字节核验）；发布门槛本身由既有 current/verify 套件覆盖，未审候选不会被
    伪造为已通过设计门槛的站点。
    """
    world = _two_epochs(tmp_path)
    root = world.root
    contract = verify_project_workspace(root).contract
    versions = _closure_fact_versions(root, world.second.evidence_snapshot_id)
    service = UserFactEditService(root)
    # 无 current：冲突无法裁决，失败关闭。
    with pytest.raises(UserFactSaveError, match="作用域"):
        service._public_fact(service._fact_row(versions[world.changed_row]))

    active_ids = tuple(sorted(versions.values()))
    builder_bytes = world.second.report_data_path.read_bytes()
    delivery = CurrentReportDelivery(
        report="C",
        revision=0,
        report_version=str(json.loads(builder_bytes)["report_version"]),
        site_relative_path=str(json.loads(world.second.receipt_path.read_bytes())["site_relative"]),
        file_hashes={},
        fact_version_ids=active_ids,
        fact_revision_digest=fact_revision_digest(active_ids),
        builder_input_relative_path=world.second.report_data_path.relative_to(root).as_posix(),
        builder_input_sha256=hashlib.sha256(builder_bytes).hexdigest(),
    )
    bundle = CurrentDeliveryBundle(
        project_id=contract.project_id,
        revision=0,
        active_fact_version_ids=active_ids,
        fact_revision_digest=fact_revision_digest(active_ids),
        reports=(delivery,),
        created_at=_AT + timedelta(minutes=10),
    )

    from ci_workflow.application import user_fact_edit as user_fact_edit_module

    current = [bundle]
    monkeypatch.setattr(user_fact_edit_module, "read_current_delivery", lambda _root: current[0])
    fresh = UserFactEditService(root)
    public = fresh._public_fact(fresh._fact_row(versions[world.changed_row]))
    (selected,) = (
        ActiveFactBinding.model_validate(item) for item in public["consumer_bindings"]
    )
    # 只选择实际当前渲染来源作用域（第二次候选）的声明，不是旧快照声明。
    assert selected == active_fact_binding_for_c(_report_of(world.second), world.changed_row)
    assert selected != active_fact_binding_for_c(_report_of(world.first), world.changed_row)

    # A long-lived service must not retain the previous generation's source
    # scope when the committed delivery changes between user requests.
    old_bytes = world.first.report_data_path.read_bytes()
    old_delivery = delivery.model_copy(update={
        "report_version": "v1",
        "builder_input_relative_path": world.first.report_data_path.relative_to(root).as_posix(),
        "builder_input_sha256": hashlib.sha256(old_bytes).hexdigest(),
    })
    current[0] = bundle.model_copy(update={"reports": (old_delivery,), "revision": 1})
    switched = fresh._public_fact(fresh._fact_row(versions[world.changed_row]))
    assert switched["consumer_bindings"] == [
        active_fact_binding_for_c(
            _report_of(world.first), world.changed_row,
        ).model_dump(mode="json")
    ]

    # The source scope belongs to the current report, not just matching row IDs.
    # A renamed historical display row must not remain an extra consumer.
    old_binding = active_fact_binding_for_c(_report_of(world.first), world.changed_row)
    new_binding = active_fact_binding_for_c(_report_of(world.second), world.changed_row)
    stale = old_binding.model_copy(update={"row_id": "old-display-row"}).model_dump_json()
    active = new_binding.model_dump_json()
    records = (
        ("C", "observations", "old-display-row", stale,
         hashlib.sha256(stale.encode()).hexdigest(), world.first.evidence_snapshot_id),
        ("C", "observations", world.changed_row, active,
         hashlib.sha256(active.encode()).hexdigest(), world.second.evidence_snapshot_id),
    )
    current[0] = bundle
    assert fresh._scoped_source_bindings(records) == (new_binding,)

    # A complete fact query validates one current scope, not the entire report
    # directory again for every fact. The next query must revalidate afresh.
    reads = 0

    def counted_current(_root: Path) -> CurrentDeliveryBundle:
        nonlocal reads
        reads += 1
        return current[0]

    monkeypatch.setattr(user_fact_edit_module, "read_current_delivery", counted_current)
    all_facts = fresh.current_facts()
    assert len(all_facts) == len(active_ids)
    assert reads <= 2
    first_reads = reads
    fresh.current_facts()
    assert first_reads < reads <= first_reads + 2


def test_conflicting_binding_for_the_same_snapshot_is_rejected_without_partial_write(
    tmp_path: Path,
) -> None:
    world = _two_epochs(tmp_path)
    root = world.root
    rows_before = _binding_rows(root)
    versions = _closure_fact_versions(root, world.second.evidence_snapshot_id)
    tampered = _report_of(world.second).model_dump(mode="json")
    for item in tampered["observations"]:
        if item["row_id"] == world.changed_row:
            item["display_text"] = "第三次未核对的呈现"
    conflicting = ReportCPortalData.model_validate(tampered)
    with pytest.raises(CPortalConsumerRegistrationError, match="冲突"):
        register_c_source_consumers(
            root,
            _locked(root, world.second.evidence_snapshot_id),
            conflicting,
            {world.changed_row: versions[world.changed_row]},
            _captures(world.payload),
            registered_at=_AT + timedelta(minutes=15),
        )
    assert _binding_rows(root) == rows_before


def test_recovery_new_ids_are_bound_to_the_exact_snapshot_scope(tmp_path: Path) -> None:
    world = _two_epochs(tmp_path)
    root = world.root
    sidecar = tmp_path / "scoped-sidecar.json"
    export_verified_consumer_bindings(
        root,
        _locked(root, world.second.evidence_snapshot_id),
        sidecar,
        c_report_data_path=world.second.report_data_path,
    )
    entries = json.loads(sidecar.read_bytes())["bindings"]
    assert len(entries) == world.row_count
    for entry in entries:
        assert entry["binding_id"] == stable_id(
            _BINDING_KIND,
            str(entry["source_fact_version_id"]),
            str(entry["report"]),
            str(entry["collection"]),
            str(entry["row_id"]),
            world.second.evidence_snapshot_id,
        )
    rows_before = _binding_rows(root)
    recovered = recover_verified_consumer_bindings(
        root, sidecar, c_report_data_path=world.second.report_data_path
    )
    assert len(recovered) == world.row_count
    assert _binding_rows(root) == rows_before

    # 新标识必须携带被恢复的精确快照；另一快照的分量不是该事实身份。
    forged_payload = json.loads(sidecar.read_bytes())
    for entry in forged_payload["bindings"]:
        entry["binding_id"] = stable_id(
            _BINDING_KIND,
            str(entry["source_fact_version_id"]),
            str(entry["report"]),
            str(entry["collection"]),
            str(entry["row_id"]),
            world.first.evidence_snapshot_id,
        )
    forged = tmp_path / "wrong-scope-sidecar.json"
    forged.write_text(json.dumps(forged_payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(PortalConsumerBindingRecoveryError, match="标识"):
        recover_verified_consumer_bindings(
            root, forged, c_report_data_path=world.second.report_data_path
        )
    assert _binding_rows(root) == rows_before


def test_recovery_legacy_ids_are_accepted_only_in_their_original_scope(
    tmp_path: Path,
) -> None:
    world = _two_epochs(tmp_path)
    root = world.root
    sidecars: dict[str, Path] = {}
    for label, outcome in (("s1", world.first), ("s2", world.second)):
        scoped = tmp_path / f"{label}-scoped.json"
        export_verified_consumer_bindings(
            root,
            _locked(root, outcome.evidence_snapshot_id),
            scoped,
            c_report_data_path=outcome.report_data_path,
        )
        sidecars[label] = _legacy_sidecar(scoped, tmp_path / f"{label}-legacy.json")

    target_s1 = _restore_target(tmp_path, root, world.first.evidence_snapshot_id, "scope-s1")
    target_s2 = _restore_target(tmp_path, root, world.second.evidence_snapshot_id, "scope-s2")
    assert _binding_rows(target_s1) == ()
    assert _binding_rows(target_s2) == ()
    recovered_s1 = recover_verified_consumer_bindings(
        target_s1, sidecars["s1"], c_report_data_path=world.first.report_data_path
    )
    recovered_s2 = recover_verified_consumer_bindings(
        target_s2, sidecars["s2"], c_report_data_path=world.second.report_data_path
    )
    assert len(recovered_s1) == world.row_count
    assert len(recovered_s2) == world.row_count
    # 历史标识各自保留在其原始作用域下，不因恢复而改变形态。
    for target, snapshot_id in (
        (target_s1, world.first.evidence_snapshot_id),
        (target_s2, world.second.evidence_snapshot_id),
    ):
        rows = _binding_rows(target)
        assert {row[2] for row in rows} == {snapshot_id}
        assert all(
            row[0] == stable_id(_BINDING_KIND, row[1], "C", "observations", row[5])
            for row in rows
        )
    # 重复恢复历史标识侧车幂等。
    assert recover_verified_consumer_bindings(
        target_s2, sidecars["s2"], c_report_data_path=world.second.report_data_path
    ) == recovered_s2
    assert len(_binding_rows(target_s2)) == world.row_count

    # 同一历史标识不能被另一个作用域复用：S2 侧车不能进入已有 S1 历史行的目标。
    shutil.copy2(
        root / "snapshots" / "evidence" / f"{world.second.evidence_snapshot_id}.json",
        target_s1 / "snapshots" / "evidence" / f"{world.second.evidence_snapshot_id}.json",
    )
    rows_s1_before = _binding_rows(target_s1)
    with pytest.raises(PortalConsumerBindingRecoveryError, match="冲突"):
        recover_verified_consumer_bindings(
            target_s1, sidecars["s2"], c_report_data_path=world.second.report_data_path
        )
    assert _binding_rows(target_s1) == rows_s1_before

    # 同一精确作用域不允许两个身份方案并存：已恢复历史标识后，快照限定标识
    # 不得重新占有同一报告行。
    scoped_s2 = tmp_path / "s2-scoped.json"
    export_verified_consumer_bindings(
        root,
        _locked(root, world.second.evidence_snapshot_id),
        scoped_s2,
        c_report_data_path=world.second.report_data_path,
    )
    with pytest.raises(PortalConsumerBindingRecoveryError, match="冲突"):
        recover_verified_consumer_bindings(
            target_s2, scoped_s2, c_report_data_path=world.second.report_data_path
        )
    assert len(_binding_rows(target_s2)) == world.row_count
