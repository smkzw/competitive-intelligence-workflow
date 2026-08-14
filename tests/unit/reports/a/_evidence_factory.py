"""Task 5.2 REVISE 共享证据快照夹具工厂。

使用真实合同（``EvidenceRepository`` + ``ScientificLineageRegistry`` +
``SnapshotStore`` + ``ProjectContract``）构造与锁定快照闭合的证据上下文，
供全部视图测试共用；不在每个测试里散落无法审计的伪摘要。页面记录引用的
事实字段由调用方按记录类型封闭集合指定。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from ci_workflow.capabilities.extraction_normalization import verify_reopened_fragment
from ci_workflow.capabilities.lineage_registry import (
    ScientificLineageRegistry,
    compute_scientific_content_digest,
)
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, OutputFormat, ReportKind
from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
from ci_workflow.domain.facts import AtomicFactVersion, NormalizationRecord
from ci_workflow.reports.a.pages import AEvidenceContext
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.project_contract_store import ProjectContractStore
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    SnapshotStore,
)

# fact_version_id -> (entity_id, field_id, raw_value, locator)
FactSpec = tuple[str, str, str, str]

# 结果型事实（core_efficacy/safety_summary）的强类型字段：与标准绑定一致，
# 供 ``_assert_result_binding_matches_fact`` 正向闭合。事实原文保留数值+单位。
_RESULT_FACT_FIELDS: dict[str, dict[str, object]] = {
    "fact-v-1": {
        "population": "意向治疗集",
        "timepoint": "第 16 周",
        "time_window": None,
        "arm_id": "度普利尤单抗 300mg 每两周",
        "cohort_id": None,
        "denominator": 224,
        "numerator": None,
        "unit": "应答率 %",
        "normalized_unit": "应答率 %",
        "normalized_value": 52.3,
    },
    "fact-v-2": {
        "population": "意向治疗集",
        "timepoint": None,
        "time_window": "治疗期间",
        "arm_id": "度普利尤单抗 300mg 每两周",
        "cohort_id": None,
        "denominator": 224,
        "numerator": None,
        "unit": "%",
        "normalized_unit": "%",
        "normalized_value": 52.3,
    },
}


def _split_locator(locator: str) -> EvidenceLocator:
    """渲染可逆的定位：``document_role/paragraph``，页面渲染拼接后精确还原。"""
    role, _, paragraph = locator.partition("/")
    return EvidenceLocator(
        document_role=role,
        paragraph=paragraph or None,
    )


def build_evidence_context(
    tmp_path: Path,
    *,
    project_id: str,
    facts: dict[str, FactSpec],
    contract_version: int = 1,
    data_cutoff: datetime | None = None,
    created_at: datetime | None = None,
) -> AEvidenceContext:
    """由真实项目真源库构造证据上下文（锁定快照 kind=evidence）。

    ``facts`` 的每个条目为：事实版本 ID -> (实体 ID, 字段 ID, 原文, 定位)。
    返回的 ``locked.snapshot_id`` 即该证据清单的内容寻址锁定 ID，调用方
    必须把它作为适用宇宙快照的 ``evidence_snapshot_id``。项目合同（真实
    ``ProjectContract``）与清单绑定同一 contract_version / data_cutoff；
    权威合同存储（``ProjectContractStore``）持久化当前合同供视图调用边界
    重载；清单携带科学证据内容摘要（``compute_scientific_content_digest``）。
    结果型事实携带与标准绑定一致的强类型字段（population/timepoint/
    time_window/arm_id/denominator/normalized_value/normalized_unit）。
    """
    project_root = tmp_path / f"evidence-store-{uuid.uuid4().hex[:8]}"
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    timestamp = created_at or datetime.now().astimezone()
    cutoff = data_cutoff or timestamp
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("数据截止日必须包含明确时区偏移")
    source_locator = EvidenceLocator(
        document_role="测试证据来源",
        paragraph="测试证据来源正文",
    )
    source_version = repository.add_source_version(
        source_id="evidence-source",
        content="\n".join(spec[2] for spec in facts.values()).encode("utf-8"),
        media_type="text/plain",
        acquired_at=timestamp,
        published_at=DateEvidence(state="not_applicable", value=None, locator=source_locator),
        effective_at=DateEvidence(state="not_applicable", value=None, locator=source_locator),
        first_disclosed_at=DateEvidence(
            state="not_publicly_disclosed", value=None, locator=source_locator
        ),
    )

    verified_by_id: dict[str, object] = {}
    fragment_ids: list[str] = []
    for fact_version_id, (_entity_id, _field_id, raw_value, locator) in facts.items():
        fragment = repository.add_fragment(
            source_version_id=source_version.source_version_id,
            locator=_split_locator(locator),
            original_text=raw_value,
            created_at=timestamp,
        )
        fragment_ids.append(fragment.fragment_id)
        verified_by_id[fact_version_id] = verify_reopened_fragment(
            fragment,
            reopened_original_text=raw_value,
            source_version_id=fragment.source_version_id,
            repository=repository,
        )

    registry = ScientificLineageRegistry.from_verified_fragments(tuple(verified_by_id.values()))
    for fact_version_id, (entity_id, field_id, raw_value, _locator) in facts.items():
        fragment = verified_by_id[fact_version_id].fragment
        fields = dict(_RESULT_FACT_FIELDS.get(fact_version_id, {}))
        normalized_value = fields.pop("normalized_value", None)
        normalized_unit = fields.pop("normalized_unit", None)
        normalization = None
        if normalized_value is not None or normalized_unit is not None:
            normalization = NormalizationRecord(
                rule_id="result-fact-normalization-v1",
                rule_version="1.0",
                method_zh="数值与单位规范化",
                original_raw_value=raw_value,
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
                reversible=True,
                reverse_expression=raw_value,
                created_at=timestamp,
            )
        candidate = AtomicFactVersion(
            fact_id=f"fact-{fact_version_id}",
            fact_version_id=fact_version_id,
            entity_id=entity_id,
            field_id=field_id,
            raw_value=raw_value,
            unit=fields.get("unit"),
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
            context="测试证据上下文",
            arm_id=fields.get("arm_id"),
            cohort_id=fields.get("cohort_id"),
            population=fields.get("population", "测试人群"),
            timepoint=fields.get("timepoint", "第 1 期"),
            time_window=fields.get("time_window"),
            numerator=fields.get("numerator"),
            denominator=fields.get("denominator"),
            primary_fragment_id=fragment.fragment_id,
            source_fragment_ids=(fragment.fragment_id,),
            extraction_method="测试抽取",
            quality_state="已核验",
            disclosure_maturity="registry_result_or_primary_report",
            source_role="primary_trial_report",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            review_state=FactReviewState.CANDIDATE,
            normalization=normalization,
            published_at=timestamp,
            effective_at=timestamp,
            created_at=timestamp,
        )
        registry, _ = registry.accept_candidate_fact(candidate)

    project_contract = ProjectContract(
        schema_version="1.0",
        contract_version=contract_version,
        project_id=project_id,
        indication="测试适应症",
        reports=(ReportKind.A,),
        outputs=(OutputFormat.HTML,),
        timezone="Asia/Shanghai",
        data_cutoff=cutoff,
        cutoff_was_user_supplied=False,
        created_at=timestamp,
    )
    contract_store = ProjectContractStore(project_root / "contracts")
    contract_store.save(project_contract)
    manifest = EvidenceSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        data_cutoff=cutoff,
        source_version_ids=(source_version.source_version_id,),
        fragment_ids=tuple(fragment_ids),
        fact_version_ids=tuple(sorted(facts)),
        scientific_content_digest=compute_scientific_content_digest(registry),
        created_at=timestamp,
    )
    store = SnapshotStore(project_root / "snapshots")
    locked = store.lock_evidence_snapshot(manifest.model_dump(mode="json"))
    return AEvidenceContext(
        locked=locked,
        manifest=manifest,
        registry=registry,
        project_contract=project_contract,
        store=store,
        contract_store=contract_store,
    )
