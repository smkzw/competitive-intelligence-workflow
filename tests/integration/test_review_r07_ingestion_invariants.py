# 独立审阅 R07（SCI08/SCI09）：真实摄取上的版本完整性与精确片段定位。
# 夹具复用既有提交测试构造器；断言走生产 SQLite，不用脚手架探针。
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.integration.test_research_package_submission import (  # noqa: E402
    _project,
    _source_payload,
)

from ci_workflow.application.fresh_research_ingestion import (  # noqa: E402
    ResearchIngestionError,
    ingest_research_evidence,
)
from ci_workflow.application.source_research_service import (  # noqa: E402
    FreshAResearchPackage,
    compute_research_content_digest,
)
from ci_workflow.storage.content_store import (  # noqa: E402
    ContentAddressedStore,
    EvidenceRepository,
)
from ci_workflow.storage.sqlite import open_database  # noqa: E402


def _prepare(tmp_path: Path, *, mutate_fact=None):
    project = _project(tmp_path)
    _, payload = _source_payload(tmp_path)
    if mutate_fact is not None:
        mutate_fact(payload)
    digest = compute_research_content_digest(payload)
    payload["scientific_review"]["reviewed_content_digest"] = digest
    package = FreshAResearchPackage.model_validate(payload)
    return project, package, digest


def _ingest(project, package, digest):
    from ci_workflow.application.project_service import verify_project_workspace

    contract = verify_project_workspace(project).contract
    return ingest_research_evidence(
        project_root=project,
        project_id=contract.project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=package.data_cutoff,
        scientific_content_digest=digest,
        created_at=package.scientific_review.reviewed_at,
        sources=package.sources,
        route_attempts=package.route_attempts,
        facts=package.facts,
        claims=package.claims,
    )


def test_sci08_disclosure_state_change_forms_new_version(tmp_path: Path) -> None:
    base_project, base_package, base_digest = _prepare(tmp_path / "a")
    base_lineage = _ingest(base_project, base_package, base_digest)
    flipped_fact = base_package.facts[0]

    def _flip_state(payload):
        payload["facts"][0]["disclosure_state"] = "not_publicly_disclosed"

    other_project, other_package, other_digest = _prepare(
        tmp_path / "b", mutate_fact=_flip_state
    )
    other_lineage = _ingest(other_project, other_package, other_digest)
    # 仅披露状态变化也必须形成新版本，不得静默折叠进旧版本
    assert (
        base_lineage.fact_version_by_ref[flipped_fact.row_ref]
        != other_lineage.fact_version_by_ref[flipped_fact.row_ref]
    )
    # 未变事实的版本标识保持一致（同内容寻址的幂等面）
    unchanged = [
        fact for fact in base_package.facts if fact.fact_id != flipped_fact.fact_id
    ]
    assert unchanged, "夹具必须包含未变化事实"
    for fact in unchanged:
        assert (
            base_lineage.fact_version_by_ref[fact.row_ref]
            == other_lineage.fact_version_by_ref[fact.row_ref]
        )


def test_sci08_replay_is_idempotent_without_duplicate_versions(tmp_path: Path) -> None:
    project, package, digest = _prepare(tmp_path)
    first = _ingest(project, package, digest)
    second = _ingest(project, package, digest)
    assert sorted(first.fact_version_ids) == sorted(second.fact_version_ids)
    with open_database(project / "state/project.sqlite") as database:
        count = database.execute(
            "SELECT COUNT(*) FROM fact_versions"
        ).fetchone()[0]
    assert count == len(set(first.fact_version_ids))


def test_sci08_same_version_id_storage_is_append_only(tmp_path: Path) -> None:
    project, package, digest = _prepare(tmp_path)
    _ingest(project, package, digest)
    # 内容寻址版本标识 + append-only 存储：同版本标识携带不同载荷在
    # 存储层不可达（UPDATE/DELETE 被拒），摄取层的冲突守卫是纵深防御
    fact = package.facts[0]
    with pytest.raises(sqlite3.IntegrityError):
        with open_database(project / "state/project.sqlite") as database:
            database.execute(
                """UPDATE fact_versions SET normalized_value=?
                WHERE fact_id=?""",
                (str((fact.normalized_value or "") + "篡改"), fact.fact_id),
            )


def test_sci09_fact_fragment_locates_own_field_not_whole_capture(
    tmp_path: Path,
) -> None:
    project, package, digest = _prepare(tmp_path)
    lineage = _ingest(project, package, digest)
    repository = EvidenceRepository(
        project / "state/project.sqlite", ContentAddressedStore(project)
    )
    precise = 0
    with open_database(project / "state/project.sqlite") as database:
        for version_id in lineage.fact_version_ids:
            row = database.execute(
                """SELECT f.locator FROM fact_versions v
                JOIN evidence_fragments f ON f.fragment_id = v.primary_fragment_id
                WHERE v.fact_version_id=?""",
                (version_id,),
            ).fetchone()
            assert row is not None, f"事实版本 {version_id} 缺主片段"
            locator = json.loads(row[0])
            if locator.get("field_path") or locator.get("row"):
                precise += 1
    # 携带精确 locator 的事实必须落逐事实片段，而非全部共用整篇全文片段
    with_field = [
        item for item in package.facts
        if item.locator.field_path or item.locator.row
    ]
    assert with_field, "夹具必须包含带精确 locator 的事实"
    assert precise >= len(with_field)
