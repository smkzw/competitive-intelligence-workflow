"""R24-90 固定 CT.gov C 候选到门户消费者的有界登记合同测试。

覆盖：显式行→不可变事实版本映射的精确核验（科学语境、试验/产品/组别、逐字
原文或已声明资格分段规则的重放、快照闭包与来源实例）、同批幂等、整批原子性
（任一负例不留下半批登记）、来源事实/review_state/current 不变，以及所有 85 条
候选观察可在一个完整批次内登记。登记本身不发布、不接受科学、不切换 current。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.application.c_portal_consumer_registry import (
    CPortalConsumerRegistrationError,
    register_c_source_consumers,
)
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
    validate_active_fact_binding,
)
from ci_workflow.renderers.portal.report_a import ProductRow, TrialRow
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_ctgov_c_design_projection import (
    _CAS_DIGEST,
    _CAS_ROOT,
    _full_bindings,
)
from tools.materialize_ctgov_c_candidate import materialize

_AT = datetime(2026, 10, 3, tzinfo=UTC)
_CUTOFF = "2026-09-26"
_INDICATION = "阵发性睡眠性血红蛋白尿症"
_CAPTURE_MAIN = "ctgov-nct02264639"
_ALLOCATION = "c-nct02264639-allocation"
_SECTION = "c-nct02264639-inclusion"
_DIRECT = "c-nct02264639-sample-size"
_EXCLUSION = "c-nct02264639-exclusion"

_PRODUCTS = (
    ProductRow(
        id="pegcetacoplan", name="Pegcetacoplan", target="C3", modality="补体C3抑制剂",
        phase="III期", status="已上市", regions=("美国",), route="皮下注射",
        developer="Apellis", mechanism="补体C3抑制",
    ),
    ProductRow(
        id="nomacopan", name="Nomacopan", target="C5", modality="补体C5抑制剂",
        phase="III期", status="在研", regions=("欧洲",), route="皮下注射",
        developer="Akari", mechanism="补体C5抑制",
    ),
)
_TRIALS = (
    TrialRow(
        id="nct02264639", display_id="NCT02264639", product_id="pegcetacoplan",
        name="Pegcetacoplan PNH 研究", phase="I期", region="美国", status="已完成",
        role="关键试验",
    ),
    TrialRow(
        id="nct03829449", display_id="NCT03829449", product_id="nomacopan",
        name="Nomacopan PNH 研究", phase="III期", region="欧洲", status="已完成",
        role="关键试验",
    ),
)


def _raw() -> ContentBlob:
    relative = f"evidence/raw/sha256/{_CAS_DIGEST[:2]}/{_CAS_DIGEST}.bin"
    return ContentBlob(
        sha256=_CAS_DIGEST, relative_path=relative,
        byte_size=(_CAS_ROOT / relative).stat().st_size, media_type="application/json",
    )


def _candidate(
    tmp_path: Path,
) -> tuple[Path, LockedSnapshot, ReportCPortalData, dict[str, str], dict[str, SourceCapture]]:
    """Materialize the fixed C candidate and wrap it as a C portal report."""
    output = tmp_path / "c-source-candidate"
    manifest = materialize(
        source_root=_CAS_ROOT, raw_asset=_raw(), output=output, bindings=_full_bindings(),
        indication_id="pnh", indication=_INDICATION, cutoff=_CUTOFF, observed_at=_AT,
    )
    project = output / "project"
    snapshot = LockedSnapshot.model_validate(manifest["snapshot"])
    projection = json.loads((output / "projection.json").read_text(encoding="utf-8"))
    inputs = json.loads((output / "inputs.json").read_text(encoding="utf-8"))
    captures = {
        item["source_id"]: SourceCapture.model_validate(item) for item in inputs["sources"]
    }
    contract = verify_project_workspace(project).contract
    report = ReportCPortalData(
        schema_version="1.0",
        report_version="r24-c-source-consumer-development",
        indication_id="pnh",
        indication=contract.indication,
        data_cutoff=contract.data_cutoff,
        products=_PRODUCTS,
        trials=_TRIALS,
        observations=tuple(projection["observations"]),
    )
    return project, snapshot, report, dict(manifest["fact_version_by_ref"]), captures


def _binding_count(root: Path) -> int:
    with open_database(root / "state/project.sqlite") as database:
        return int(
            database.execute("SELECT COUNT(*) FROM source_portal_consumer_bindings").fetchone()[0]
        )


def _mutated_report(report: ReportCPortalData, row_id: str, **changes: object) -> ReportCPortalData:
    payload = report.model_dump(mode="json")
    for item in payload["observations"]:
        if item["row_id"] == row_id:
            item.update(changes)
            break
    return ReportCPortalData.model_validate(payload)


def _fact_snapshot(root: Path, version_ids: tuple[str, ...]) -> dict[str, tuple[object, ...]]:
    with open_database(root / "state/project.sqlite") as database:
        return {
            version_id: tuple(
                database.execute(
                    "SELECT content_sha256,scientific_context_json,review_state,"
                    "disclosure_state FROM fact_versions WHERE fact_version_id=?",
                    (version_id,),
                ).fetchone()
            )
            for version_id in version_ids
        }


def test_c_batch_registers_exact_source_versions_idempotently_without_touching_science(
    tmp_path: Path,
) -> None:
    root, snapshot, report, versions, captures = _candidate(tmp_path)
    requested = {
        row_id: versions[row_id]
        for row_id in (
            "c-nct02264639-population",
            _SECTION,
            _EXCLUSION,
            _DIRECT,
            "c-nct02264639-arm-0-label",
            "c-nct02264639-pri0-definition",
            _ALLOCATION,
        )
    }
    before_facts = _fact_snapshot(root, tuple(requested.values()))
    assert _binding_count(root) == 0

    bindings = register_c_source_consumers(
        root, snapshot, report, requested, captures, registered_at=_AT,
    )

    assert tuple(item.row_id for item in bindings) == tuple(sorted(requested))
    for item in bindings:
        assert item == active_fact_binding_for_c(report, item.row_id)
        assert (item.report, item.collection) == ("C", "observations")
    by_row = {item.row_id: item for item in bindings}
    assert by_row[_SECTION].endpoint_definition == "inclusion_criterion"
    assert by_row[_SECTION].statistical_form == "design_text"
    assert by_row[_DIRECT].statistical_form == "threshold"
    assert by_row["c-nct02264639-arm-0-label"].group_id == "group-nct02264639-cohort-1"

    # 同一请求重复登记幂等：不新增行、不改变返回值。
    assert register_c_source_consumers(
        root, snapshot, report, requested, captures, registered_at=_AT,
    ) == bindings
    assert _binding_count(root) == len(requested)
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT COUNT(DISTINCT evidence_snapshot_id) FROM source_portal_consumer_bindings"
        ).fetchone()[0] == 1
        assert database.execute(
            "SELECT COUNT(DISTINCT report) FROM source_portal_consumer_bindings"
        ).fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "UPDATE source_portal_consumer_bindings SET row_id='other' "
                "WHERE source_fact_version_id=?", (requested[_DIRECT],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "DELETE FROM source_portal_consumer_bindings WHERE source_fact_version_id=?",
                (requested[_DIRECT],),
            )
    # 登记不改变来源事实版本的科学内容、披露状态或复核状态。
    assert _fact_snapshot(root, tuple(requested.values())) == before_facts
    # 登记不渲染门户、不切换 current。
    assert read_current_delivery(root) is None
    assert not list((root / "reports" / "C").rglob("*.html"))
    # 现有公开事实读取面能看到已登记消费者声明。
    service = UserFactEditService(root)
    public = service._public_fact(service._fact_row(requested[_DIRECT]))
    assert public["consumer_bindings"] == [by_row[_DIRECT].model_dump(mode="json")]


def test_all_candidate_c_rows_register_in_one_complete_batch(tmp_path: Path) -> None:
    root, snapshot, report, versions, captures = _candidate(tmp_path)
    requested = {row.row_id: versions[row.row_id] for row in report.observations}
    assert len(requested) == 85

    bindings = register_c_source_consumers(
        root, snapshot, report, requested, captures, registered_at=_AT,
    )

    assert len(bindings) == len(requested)
    assert {item.row_id for item in bindings} == set(requested)
    assert all(item == active_fact_binding_for_c(report, item.row_id) for item in bindings)
    assert _binding_count(root) == 85
    assert register_c_source_consumers(
        root, snapshot, report, requested, captures, registered_at=_AT,
    ) == bindings
    assert _binding_count(root) == 85


def test_c_active_projection_resolves_proven_capture_alias_not_warehouse_version(
    tmp_path: Path,
) -> None:
    root, snapshot, report, versions, captures = _candidate(tmp_path)
    (binding,) = register_c_source_consumers(
        root, snapshot, report, {_DIRECT: versions[_DIRECT]}, captures, registered_at=_AT,
    )
    service = UserFactEditService(root)
    public = service._public_fact(service._fact_row(versions[_DIRECT]))
    assert public["source_version_id"].startswith("source-version_")
    assert public["source_id"] == binding.source_version_id == _CAPTURE_MAIN
    fact = ActiveFact.model_validate(public)
    assert validate_active_fact_binding(fact, binding, binding) == binding
    # C capture aliases require explicit persisted identity, not a ctgov prefix
    # heuristic or an unrestricted exemption from the source-version check.
    for changed in ({"source_id": "ctgov-nct99999999"}, {"source_id": None}):
        with pytest.raises(ValueError, match="source_version_id"):
            validate_active_fact_binding(ActiveFact.model_validate({**public, **changed}),
                                         binding, binding)
    wrong = binding.model_copy(update={"source_version_id": "ctgov-nct99999999"})
    with pytest.raises(ValueError, match="source_version_id"):
        validate_active_fact_binding(fact, wrong, wrong)


def test_wrong_identity_rejects_whole_batch_without_partial_write(tmp_path: Path) -> None:
    root, snapshot, report, versions, captures = _candidate(tmp_path)
    baseline = _binding_count(root)
    valid = {_ALLOCATION: versions[_ALLOCATION]}
    exclusion_text = next(
        item.source_text for item in report.observations if item.row_id == _EXCLUSION
    )
    allocation_locator = json.loads(json.dumps(
        next(item.source_locator.model_dump(mode="json")
             for item in report.observations if item.row_id == _DIRECT)
    ))

    def _reject(
        mapping: dict[str, str],
        *,
        changed_report: ReportCPortalData | None = None,
        changed_snapshot: LockedSnapshot | None = None,
        changed_captures: dict[str, SourceCapture] | None = None,
    ) -> None:
        with pytest.raises(CPortalConsumerRegistrationError):
            register_c_source_consumers(
                root,
                snapshot if changed_snapshot is None else changed_snapshot,
                report if changed_report is None else changed_report,
                mapping,
                captures if changed_captures is None else changed_captures,
                registered_at=_AT,
            )
        assert _binding_count(root) == baseline

    # 值：报告行原文与锁定来源标量不一致。
    _reject(
        {**valid, _DIRECT: versions[_DIRECT]},
        changed_report=_mutated_report(report, _DIRECT, source_text="10"),
    )
    # 路径：定位指向另一登记字段。
    _reject(
        {**valid, _DIRECT: versions[_DIRECT]},
        changed_report=_mutated_report(
            report, _DIRECT,
            source_locator={**allocation_locator, "field_path":
                            "$.protocolSection.designModule.enrollmentInfo.type"},
        ),
    )
    # 产品：报告行产品与试验—产品身份不一致。
    _reject(
        {**valid, _DIRECT: versions[_DIRECT]},
        changed_report=_mutated_report(report, _DIRECT, product_id="nomacopan"),
    )
    # 章节：入选行携带排除段原文，父级标量重放结果不一致。
    _reject(
        {**valid, _SECTION: versions[_SECTION]},
        changed_report=_mutated_report(report, _SECTION, source_text=exclusion_text),
    )
    # 章节规则：分段行缺少已声明的确定性派生规则。
    _reject(
        {**valid, _SECTION: versions[_SECTION]},
        changed_report=_mutated_report(
            report, _SECTION, compatibility_rule="ctgov-c-protocol-atoms-v1",
        ),
    )
    # 版本：请求版本属于另一报告行。
    _reject({**valid, _SECTION: versions[_EXCLUSION]})
    # 版本：请求版本不在锁定快照。
    _reject({**valid, _DIRECT: "fact-version_0000000000000000000000"})
    # 版本：空标识。
    _reject({**valid, _DIRECT: " "})
    # 重复映射：同一来源版本不得复制为两个报告行。
    _reject({**valid, _SECTION: versions[_ALLOCATION]})
    # 重复行引用：裸行标识与 observations: 前缀指向同一行。
    _reject({**valid, f"observations:{_ALLOCATION}": versions[_DIRECT]})
    # 未支持的行引用前缀。
    _reject({f"efficacy:{_ALLOCATION}": versions[_ALLOCATION]})
    # 缺失映射：空批次。
    _reject({})
    # 缺失映射：未知报告行。
    _reject({**valid, "c-nct09999999-ghost": versions[_ALLOCATION]})
    # 缺失映射：使用的来源实例没有可核验采集。
    _reject(valid, changed_captures={
        key: value for key, value in captures.items() if key != _CAPTURE_MAIN
    })
    # 来源字节：采集文本与原始资产派生回执不一致。
    main = captures[_CAPTURE_MAIN]
    _reject(valid, changed_captures={
        **captures,
        _CAPTURE_MAIN: main.model_copy(update={"content_text": main.content_text + "\n"}),
    })
    # 来源身份：采集登记号不是报告行试验。
    _reject(valid, changed_captures={
        **captures,
        _CAPTURE_MAIN: main.model_copy(update={"query_or_identifier": "NCT99999999"}),
    })
    # 快照：报告快照不得作为来源权威。
    _reject(valid, changed_snapshot=snapshot.model_copy(
        update={"kind": "report", "report": "C"},
    ))
    # 快照：报告数据截止与锁定快照不一致。
    _reject(valid, changed_report=report.model_copy(
        update={"data_cutoff": report.data_cutoff - timedelta(days=1)},
    ))
    # 项目合同：报告适应症与项目合同不一致。
    _reject(valid, changed_report=report.model_copy(update={"indication": "其他适应症"}))
    # 报告行唯一性：同一设计观察行不得重复出现。
    duplicated = report.model_dump(mode="json")
    duplicated["observations"] = [
        *duplicated["observations"],
        next(
            dict(item) for item in duplicated["observations"] if item["row_id"] == _ALLOCATION
        ),
    ]
    _reject(valid, changed_report=ReportCPortalData.model_validate(duplicated))
    # 组别：显式未解决的 arm 关系不得登记为消费者。
    _reject(
        {**valid, "c-nct02264639-arm-0-label": versions["c-nct02264639-arm-0-label"]},
        changed_report=_mutated_report(
            report, "c-nct02264639-arm-0-label",
            relationship_status="unknown_arm_label", relationship_blocking=True,
        ),
    )
    assert _binding_count(root) == baseline
