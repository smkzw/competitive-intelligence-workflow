"""C 类新鲜来源研究包：类型化内容、登记优先 GateSpec、多路径非排名、
独立科学复核摘要绑定与 C 报告快照投影。

合同断言（先失败后通过）：
- 类型化内容绑定 C 类门户模型并失败关闭：适应症/截止/版本不一致、
  观察引用包外来源、声明引用未知观察、来源晚于数据截止；
- 登记优先设计事实 GateSpec：官方登记（或登记+方案/SAP）覆盖全部关键
  单元才通过；论文不得替代登记设计事实；每个关键单元独立阻断；
  地区/访视/操作特征仅在指示规则声明为关键时适用；统计扩展缺失不阻断；
- 多路径非排名：候选路径不足两条、设计签名重复、路径引用未知观察或
  元数据携带排名语义均失败关闭；路径本身不含任何排名字段；
- 独立科学复核：拒绝未接受复核与摘要不一致复核；内容摘要不随复核字段变化；
- C 报告快照投影：门槛通过且复核接受后才能锁定 C 报告快照；
  快照身份内容寻址、投影幂等、门户数据绑定锁定快照标识。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.run_service import RunContext, run_project, validate_run_manifest
from ci_workflow.application.terminal_recovery import exhaustion_path
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.exhaustion import DoubleExhaustionRecord
from ci_workflow.gates.models import (
    ConflictDisposition,
    DisclosureMaturity,
    GateBlockingLevel,
    GateSpec,
    GateUnitOutcome,
    ReportDecision,
    SourceRole,
    TrialDesignKind,
)
from ci_workflow.renderers.portal.report_a import ProductRow, TrialRow
from ci_workflow.reports.c import DesignFieldFamily, DesignObservation, evaluate_design_gate

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = datetime(2026, 8, 31, 23, 59, tzinfo=UTC)
PROJECT_ID = "project_000000000000000000000001"


def _module() -> ModuleType:
    """延迟导入 C 类新鲜来源研究包模块；实现前精确失败。"""
    try:
        from ci_workflow.application import fresh_c_research_package as module
    except ModuleNotFoundError as exc:
        pytest.fail(f"C 类新鲜来源研究包模块尚未实现：{exc}", pytrace=False)
    return module


# ─── 夹具工厂 ────────────────────────────────────────────────────────────────


def _locator(source: str = "registry") -> EvidenceLocator:
    if source == "registry":
        return EvidenceLocator(
            document_role="clinical-trial-registry",
            field_path="Eligibility / Study Design",
            url="https://clinicaltrials.gov/study/NCT00000001",
        )
    return EvidenceLocator(
        document_role="protocol-sap",
        field_path="Section 8.1 Endpoints",
        page=42,
        paragraph="Primary endpoint definition",
    )


def _products() -> tuple[ProductRow, ...]:
    return (
        ProductRow(
            id="product-alpha",
            name="阿尔法单抗",
            target="IL-4Rα",
            modality="单抗",
            phase="III",
            status="招募中",
            regions=("全球", "中国"),
            route="皮下注射",
            developer="阿尔法生物",
            mechanism="白介素-4受体α阻断",
        ),
        ProductRow(
            id="product-beta",
            name="贝塔口服液",
            target="JAK1",
            modality="小分子",
            phase="II",
            status="活跃",
            regions=("全球",),
            route="口服",
            developer="贝塔制药",
            mechanism="JAK1选择性抑制",
        ),
    )


def _trials() -> tuple[TrialRow, ...]:
    return (
        TrialRow(
            id="trial-alpha-1",
            display_id="NCT00000001",
            product_id="product-alpha",
            name="阿尔法 III 期关键试验",
            phase="III",
            region="全球",
            status="招募中",
            sample_size=480,
            role="关键注册试验",
        ),
        TrialRow(
            id="trial-alpha-2",
            display_id="NCT00000002",
            product_id="product-alpha",
            name="阿尔法 II 期探索试验",
            phase="II",
            region="中国",
            status="进行中",
            sample_size=120,
            role="概念验证试验",
        ),
        TrialRow(
            id="trial-beta-1",
            display_id="NCT00000003",
            product_id="product-beta",
            name="贝塔 III 期关键试验",
            phase="III",
            region="全球",
            status="招募中",
            sample_size=360,
            role="关键注册试验",
        ),
        TrialRow(
            id="trial-beta-2",
            display_id="NCT00000004",
            product_id="product-beta",
            name="贝塔 II 期剂量探索试验",
            phase="II",
            region="全球",
            status="进行中",
            sample_size=90,
            role="剂量探索试验",
        ),
    )


_COMPARATIVE_TRIALS = frozenset({"trial-alpha-1", "trial-alpha-2"})


def _design_kind(trial_id: str) -> TrialDesignKind:
    return (
        TrialDesignKind.COMPARATIVE
        if trial_id in _COMPARATIVE_TRIALS
        else TrialDesignKind.SINGLE_ARM
    )


_CRITICAL_FAMILIES: tuple[tuple[DesignFieldFamily, str, str], ...] = (
    (DesignFieldFamily.TRIAL_IDENTITY, "trial_identity", "研究身份与阶段"),
    (DesignFieldFamily.POPULATION, "target_population", "成人中重度患者"),
    (DesignFieldFamily.GROUPING, "arm_randomization_blinding", "随机双盲"),
    (DesignFieldFamily.INTERVENTION, "experimental_arm", "试验药与对照"),
    (DesignFieldFamily.DOSE_SCHEDULE, "dose_schedule_followup", "每两周给药"),
    (DesignFieldFamily.ENDPOINT, "primary_endpoint_definition", "湿疹面积评分"),
    (DesignFieldFamily.TIMEPOINT, "primary_endpoint_timepoint", "第16周"),
    (DesignFieldFamily.SAMPLE_SIZE, "planned_sample_size", "计划样本量"),
)


def _observation(
    trial_id: str,
    product_id: str,
    family: DesignFieldFamily,
    field: str,
    text: str,
    *,
    source_role: SourceRole = SourceRole.CLINICAL_TRIAL_REGISTRY,
    source_version_id: str = "source-registry-1",
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    review_state: FactReviewState = FactReviewState.ACCEPTED,
    threshold_value: str | None = None,
    threshold_unit: str | None = None,
    group_id: str | None = None,
    endpoint_key: str | None = None,
) -> DesignObservation:
    effective_group = group_id or f"group-{trial_id}-single"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": f"row-{trial_id}-{field}",
        "source_row_id": f"src-{trial_id}-{field}",
        "observation_id": f"obs-{trial_id}-{field}",
        "product_id": product_id,
        "trial_id": trial_id,
        "cohort_id": f"cohort-{trial_id}",
        "group_id": effective_group,
        "field_family": family,
        "field": field,
        "endpoint_key": endpoint_key,
        "outcome_id": (
            f"{trial_id}-{endpoint_key or 'primary'}-1"
            if family in {DesignFieldFamily.ENDPOINT, DesignFieldFamily.TIMEPOINT}
            else None
        ),
        "source_field_name": f"registry.{field}",
        "period": (
            "overall" if family in {DesignFieldFamily.ENDPOINT, DesignFieldFamily.TIMEPOINT} else None
        ),
        "source_field_definition": f"{field} 的登记字段定义",
        "source_text": text,
        "threshold_value": threshold_value,
        "threshold_unit": threshold_unit,
        "assessment_timepoint": (
            "第16周" if family in {DesignFieldFamily.ENDPOINT, DesignFieldFamily.TIMEPOINT} else None
        ),
        "stage": "III",
        "development_role": "关键注册试验",
        "randomization": "随机" if family is DesignFieldFamily.GROUPING else None,
        "blinding": "双盲" if family is DesignFieldFamily.GROUPING else None,
        "source_version_id": source_version_id,
        "source_locator": _locator(
            "registry" if source_role is SourceRole.CLINICAL_TRIAL_REGISTRY else "protocol"
        ),
        "source_role": source_role,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": review_state,
        "disclosure_state": disclosure_state,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "reported_zero_text": (
            "0" if disclosure_state is FactDisclosureState.REPORTED_ZERO else None
        ),
        "applicability_predicate_id": (
            "region_visit_operational_key"
            if disclosure_state is FactDisclosureState.NOT_APPLICABLE
            else None
        ),
        "compatibility_rule": "c-design-v1",
    }
    return DesignObservation.model_validate(payload)


def _observations(
    *,
    source_role: SourceRole = SourceRole.CLINICAL_TRIAL_REGISTRY,
) -> tuple[DesignObservation, ...]:
    """四项试验 × 八个关键设计族，全部来自给定来源角色。"""
    rows: list[DesignObservation] = []
    for trial in _trials():
        for index, (family, field, text) in enumerate(_CRITICAL_FAMILIES):
            group_id = (
                f"group-{trial.id}-arm-{1 + index % 2}"
                if trial.id in _COMPARATIVE_TRIALS
                else f"group-{trial.id}-single"
            )
            if family in {DesignFieldFamily.ENDPOINT, DesignFieldFamily.TIMEPOINT}:
                group_id = (
                    f"group-{trial.id}-arm-1"
                    if trial.id in _COMPARATIVE_TRIALS
                    else f"group-{trial.id}-single"
                )
            if family is DesignFieldFamily.SAMPLE_SIZE:
                rows.append(
                    _observation(
                        trial.id,
                        trial.product_id,
                        family,
                        field,
                        text,
                        source_role=source_role,
                        threshold_value=str(trial.sample_size),
                        threshold_unit="人",
                        group_id=group_id,
                    )
                )
                continue
            signature = (
                "每天两次口服" if trial.id.startswith("trial-beta") else "皮下注射"
            )
            rows.append(
                _observation(
                    trial.id,
                    trial.product_id,
                    family,
                    field,
                    f"{text}（{signature}）",
                    source_role=source_role,
                    group_id=group_id,
                )
            )
    return tuple(rows)


def _sources(count: int = 2) -> tuple[dict[str, object], ...]:
    payloads: list[dict[str, object]] = []
    for index in range(1, count + 1):
        payloads.append(
            {
                "source_id": f"source-registry-{index}",
                "route_id": "clinicaltrials-gov-api",
                "source_type": "clinical_trial_registry",
                "title": f"官方登记测试记录 {index}",
                "url": f"https://clinicaltrials.gov/study/NCT0000000{index}",
                "query_or_identifier": f"NCT0000000{index}",
                "language": "en",
                "access_method": "public_api",
                "content_text": "官方登记设计字段原文",
                "acquired_at": datetime(2026, 8, 1, tzinfo=UTC),
                "published_at": datetime(2026, 7, 1, tzinfo=UTC),
                "effective_at": None,
                "first_disclosed_at": datetime(2026, 7, 1, tzinfo=UTC),
                "locator": {
                    "document_role": "clinical-trial-registry",
                    "field_path": "Study Design",
                    "url": f"https://clinicaltrials.gov/study/NCT0000000{index}",
                },
            }
        )
    return tuple(payloads)


def _manual_design_paths() -> list[dict[str, object]]:
    """两条证据绑定的候选路径：引用始终存在的贝塔试验观察，无排名语义。"""
    return [
        {
            "path_id": "path-oral-once-daily",
            "design_signature": "口服每两周方案签名",
            "summary_zh": "以口服给药与每两周随访为基础的候选设计。",
            "assumptions_zh": "假设人群可耐受口服给药。",
            "tradeoffs_zh": "给药便利与依从性监测之间的权衡。",
            "observation_ids": [
                "obs-trial-beta-1-arm_randomization_blinding",
                "obs-trial-beta-1-primary_endpoint_definition",
            ],
            "trial_ids": ["trial-beta-1"],
        },
        {
            "path_id": "path-injection-twice-daily",
            "design_signature": "注射双盲方案签名",
            "summary_zh": "以注射给药与双盲设计为基础的候选设计。",
            "assumptions_zh": "假设受试者接受注射给药。",
            "tradeoffs_zh": "给药频率与盲法维持之间的权衡。",
            "observation_ids": [
                "obs-trial-beta-2-arm_randomization_blinding",
                "obs-trial-beta-2-primary_endpoint_timepoint",
            ],
            "trial_ids": ["trial-beta-2"],
        },
    ]


def _trial_designs_payload(
    rows: tuple[DesignObservation, ...] | None = None,
) -> list[dict[str, object]]:
    """每项试验一条设计类型声明，锚定该试验现存观察。"""
    usable = rows if rows is not None else _observations()
    by_trial: dict[str, str] = {}
    for item in usable:
        by_trial.setdefault(item.trial_id, item.observation_id)
    return [
        {
            "trial_id": trial.id,
            "design_kind": _design_kind(trial.id),
            "observation_id": by_trial[trial.id],
        }
        for trial in _trials()
    ]


def _bind_observations_to_source_bytes(
    observation_payloads: list[dict[str, object]],
    source_payloads: list[dict[str, object]],
) -> None:
    """Bind every observation to an exact quote in the persisted source JSON."""
    for source in source_payloads:
        source_id = str(source["source_id"])
        members = [
            item for item in observation_payloads if item["source_version_id"] == source_id
        ]
        source["content_text"] = json.dumps(
            {"observations": [{"source_text": item["source_text"]} for item in members]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for index, item in enumerate(members):
            existing_locator = item.get("source_locator")
            document_role = "clinical-trial-registry"
            if isinstance(existing_locator, dict):
                document_role = str(
                    existing_locator.get("document_role") or document_role
                )
            item["source_locator"] = {
                "document_role": document_role,
                "field_path": f"$.observations[{index}].source_text",
                "url": source["url"],
            }


def _content_payload(**overrides: object) -> dict[str, object]:
    rows = _observations()
    observation_payloads = [item.model_dump(mode="json") for item in rows]
    source_payloads = [dict(item) for item in _sources()]
    _bind_observations_to_source_bytes(observation_payloads, source_payloads)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "indication_id": "atopic-dermatitis",
        "indication": "特应性皮炎",
        "data_cutoff": CUTOFF,
        "report_version": "v1",
        "producer_id": "host-agent-builder",
        "report_data": {
            "schema_version": "c-portal-v1",
            "report_version": "v1",
            "indication_id": "atopic-dermatitis",
            "indication": "特应性皮炎",
            "data_cutoff": CUTOFF,
            "products": [item.model_dump(mode="json") for item in _products()],
            "trials": [item.model_dump(mode="json") for item in _trials()],
            "observations": observation_payloads,
        },
        "sources": source_payloads,
        "route_attempts": [],
        "claims": [
            {
                "claim_id": "claim-design-1",
                "claim_text": "登记设计事实支持两条候选设计路径的陈述。",
                "claim_kind": "direct_evidence",
                "fact_ids": [
                    "row-trial-beta-1-target_population",
                    "row-trial-beta-2-target_population",
                ],
            }
        ],
        "trial_designs": _trial_designs_payload(rows),
        "design_paths": {
            "indication_id": "atopic-dermatitis",
            "patterns": [],
            "differences": [],
            "outliers": [],
            "candidate_paths": _manual_design_paths(),
        },
        "applicable_conditional_predicates": [],
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def test_fresh_c_rejects_multiple_primary_without_per_instance_timepoint(module: ModuleType) -> None:
    payload = _content_payload()
    observations = payload["report_data"]["observations"]
    endpoint = next(item for item in observations if item["field_family"] == "endpoint")
    duplicate = dict(endpoint)
    duplicate.update({
        "row_id": endpoint["row_id"] + "-second",
        "source_row_id": endpoint["source_row_id"] + "-second",
        "observation_id": endpoint["observation_id"] + "-second",
        "source_text": "Second co-primary endpoint",
        "outcome_id": "primary-second",
    })
    observations.append(duplicate)
    with pytest.raises(ValueError, match="outcome_id|时间点|实例"):
        module.FreshCResearchContent.model_validate(payload)


def test_fresh_c_rejects_group_period_window_mismatch(module: ModuleType) -> None:
    payload = _content_payload()
    observations = payload["report_data"]["observations"]
    endpoint = next(item for item in observations if item["field_family"] == "endpoint")
    timepoint = next(
        item for item in observations
        if item["field_family"] == "timepoint" and item["trial_id"] == endpoint["trial_id"]
    )
    endpoint["outcome_id"] = "primary-1"
    timepoint["outcome_id"] = "primary-1"
    timepoint["group_id"] = timepoint["group_id"] + "-wrong"
    with pytest.raises(ValueError, match="时间点|实例|对应终点"):
        module.FreshCResearchContent.model_validate(payload)


def test_fresh_c_new_content_cannot_self_declare_legacy_identity_mode(
    module: ModuleType,
) -> None:
    payload = _content_payload()
    payload["endpoint_identity_mode"] = "legacy_readonly_v0"
    for observation in payload["report_data"]["observations"]:
        if observation["field_family"] in {"endpoint", "timepoint"}:
            observation["outcome_id"] = None
    with pytest.raises(module.FreshCPackageError, match="legacy|instance_v1|endpoint_identity_mode"):
        module.validate_fresh_c_content(payload)


def test_run_service_rejects_new_c_package_that_self_declares_legacy(
    module: ModuleType, tmp_path: Path,
) -> None:
    from ci_workflow.application.run_service import ContractConfigError

    contract = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff="2026-09-01"
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    payload = _ready_package_payload(module)
    payload["endpoint_identity_mode"] = "legacy_readonly_v0"
    for observation in payload["report_data"]["observations"]:
        if observation["field_family"] in {"endpoint", "timepoint"}:
            observation["outcome_id"] = None
    package_path = project_root / "inputs/c-self-declared-legacy.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps({**payload, "scientific_review": _review(module, "invalid")},
                   ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    with pytest.raises(ContractConfigError, match="legacy|instance_v1|endpoint_identity_mode"):
        run_project(
            project_root,
            run_context=RunContext(
                project_root=project_root, contract=contract,
                research_package_path=package_path,
            ),
            capability_probe=StaticCapabilityProbe(),
        )


def test_fresh_c_blocks_explicit_unbound_intervention_relationship(module: ModuleType) -> None:
    payload = _content_payload()
    observation = next(
        item for item in payload["report_data"]["observations"]
        if item["field_family"] == "dose_schedule"
    )
    observation.update({
        "relationship_status": "missing_arm_labels",
        "relationship_reason": "source intervention has no armGroupLabels",
        "relationship_blocking": True,
    })
    with pytest.raises(ValueError, match="arm|关系缺失|阻断"):
        module.FreshCResearchContent.model_validate(payload)


def _synthesis_payload(module: ModuleType, **overrides: object) -> dict[str, object]:
    """由综合层真实生成候选路径，保证夹具路径本身有证据支撑。"""
    from ci_workflow.reports.c.synthesis import synthesize_design_paths

    result = synthesize_design_paths("atopic-dermatitis", _observations())
    payload: dict[str, object] = result.model_dump(mode="json")
    payload.update(overrides)
    return payload


def _review(
    module: ModuleType,
    digest: str,
    *,
    status: str = "accepted",
) -> dict[str, object]:
    return {
        "reviewer_id": "independent-reviewer-1",
        "reviewer_role": "independent_scientific_verifier",
        "status": status,
        "reviewed_at": datetime(2026, 9, 1, tzinfo=UTC),
        "reviewed_content_digest": digest,
        "observations": ("独立复核未发现登记设计事实与原文不一致。",),
    }


def _gate_spec() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "C-v1.yaml")


def _critical_c_unit_ids() -> tuple[str, ...]:
    return tuple(
        unit.unit_id
        for unit in _gate_spec().units
        if unit.blocking_level is GateBlockingLevel.CRITICAL
    )


def _evaluate(module: ModuleType, payload: dict[str, object]) -> object:
    content = module.validate_fresh_c_content(payload)
    return module.evaluate_c_report_gate(
        content,
        project_id=PROJECT_ID,
        evidence_snapshot_id="evidence-snapshot-1",
        contract_version="1",
    )


@pytest.fixture(name="module")
def module_fixture() -> Iterator[ModuleType]:
    yield _module()


# ─── 类型化内容闭合 ──────────────────────────────────────────────────────────


def test_content_binds_c_portal_model_and_validates_closure(module: ModuleType) -> None:
    """类型化内容成功构造：绑定 C 门户模型，摘要稳定且确定可复现。"""
    content = module.validate_fresh_c_content(_content_payload())

    digest = content.content_digest
    assert len(digest) == 64
    assert digest == content.content_digest
    assert content.report_data.observations
    assert content.universe_product_ids == ("product-alpha", "product-beta")
    assert content.universe_trial_ids == (
        "trial-alpha-1",
        "trial-alpha-2",
        "trial-beta-1",
        "trial-beta-2",
    )
    assert content.claim_ids == ("claim-design-1",)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("indication", "结节性痒疹"),
        ("data_cutoff", datetime(2026, 7, 31, tzinfo=UTC)),
        ("report_version", "v2"),
        ("indication_id", "prurigo-nodularis"),
    ),
)
def test_content_fails_closed_on_identity_mismatch(
    module: ModuleType, field: str, value: object
) -> None:
    """适应症、适应症标识、截止或版本不一致必须失败关闭。"""
    payload = _content_payload(**{field: value})
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


def test_content_fails_closed_on_unknown_source_reference(
    module: ModuleType,
) -> None:
    """观察引用研究包外来源必须失败关闭。"""
    rows = list(_observations())
    rows[1] = _observation(
        "trial-alpha-1",
        "product-alpha",
        DesignFieldFamily.POPULATION,
        "target_population",
        "成人中重度患者",
        source_version_id="source-not-in-package",
    )
    payload = _content_payload()
    observation_payloads = [item.model_dump(mode="json") for item in rows]
    source_payloads = payload["sources"]
    assert isinstance(source_payloads, list)
    _bind_observations_to_source_bytes(observation_payloads, source_payloads)
    payload["report_data"]["observations"] = observation_payloads
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


def test_content_fails_closed_on_claim_referencing_unknown_observation(
    module: ModuleType,
) -> None:
    """声明引用未知观察必须失败关闭。"""
    payload = _content_payload()
    payload["claims"] = [
        {
            "claim_id": "claim-design-1",
            "claim_text": "引用不存在观察的声明。",
            "claim_kind": "direct_evidence",
            "fact_ids": ["row-does-not-exist"],
        }
    ]
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


def test_content_fails_closed_when_source_disclosed_after_cutoff(
    module: ModuleType,
) -> None:
    """截止日之后首次披露的来源不得进入当前快照。"""
    payload = _content_payload()
    sources = [dict(item) for item in payload["sources"]]
    sources[0]["first_disclosed_at"] = datetime(2026, 9, 1, tzinfo=UTC)
    payload["sources"] = sources
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


# ─── 登记优先设计事实 GateSpec ───────────────────────────────────────────────


def test_registry_coverage_passes_c_gate_without_protocol(module: ModuleType) -> None:
    """全部关键设计族由官方登记覆盖时门槛通过，无需方案/SAP。"""
    outcome = _evaluate(module, _content_payload())
    assert outcome.result.decision is ReportDecision.PASSED
    for unit_id in _critical_c_unit_ids():
        results = [
            item
            for item in outcome.result.unit_results
            if item.unit_id == unit_id and item.applicable
        ]
        if unit_id == "c_region_visit_operational" and not results:
            # 未声明为关键时明确不适用；声明分支由专项测试覆盖
            continue
        assert results, unit_id
        assert all(item.outcome is GateUnitOutcome.SATISFIED for item in results)


def test_c_gate_bindings_are_deterministic_and_engine_bound(
    module: ModuleType,
) -> None:
    """绑定构建确定性可复现，且只能经共享引擎按 C 规格评估。"""
    content = module.validate_fresh_c_content(_content_payload())
    bindings = module.build_c_gate_bindings(content)
    assert bindings == module.build_c_gate_bindings(content)

    snapshot = module.build_c_gate_snapshot(
        content,
        project_id=PROJECT_ID,
        evidence_snapshot_id="evidence-snapshot-1",
    )
    result = evaluate_report(_gate_spec(), snapshot, bindings, contract_version="1")
    assert result.decision is ReportDecision.PASSED

    # 报告类型不匹配：C 评估入口拒绝 B 规格，报告类型失败关闭
    b_spec = GateSpec.from_yaml(ROOT / "policies" / "gates" / "B-v1.yaml")
    with pytest.raises(module.FreshCPackageError):
        module.evaluate_c_report_gate(
            content,
            project_id=PROJECT_ID,
            evidence_snapshot_id="evidence-snapshot-1",
            contract_version="1",
            spec=b_spec,
        )


def test_publication_cannot_replace_registry_design_fact(module: ModuleType) -> None:
    """论文设计摘要不得替代登记设计事实：人群族仅有论文来源时阻断。"""
    rows = [
        item
        for item in _observations()
        if not (
            item.trial_id == "trial-alpha-1"
            and item.field_family is DesignFieldFamily.POPULATION
        )
    ]
    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.POPULATION,
            "target_population",
            "成人中重度患者（论文摘要）",
            source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        )
    )
    payload = _content_payload()
    payload["report_data"]["observations"] = [
        item.model_dump(mode="json") for item in rows
    ]
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))
    outcome = _evaluate(module, payload)
    population = [
        item
        for item in outcome.result.unit_results
        if item.unit_id == "c_target_population_criteria"
        and item.object_id == "trial-alpha-1"
    ]
    assert len(population) == 1
    assert population[0].outcome is GateUnitOutcome.BLOCKED
    assert outcome.result.decision is ReportDecision.BLOCKED
    # 登记优先语义同时由 C 设计门槛合同保证
    design_gate = evaluate_design_gate(
        rows,
        core_trial_ids=[
            "trial-alpha-1",
            "trial-alpha-2",
            "trial-beta-1",
            "trial-beta-2",
        ],
    )
    assert design_gate.decision.value == "blocked"


def test_each_critical_unit_blocks_independently_when_missing(
    module: ModuleType,
) -> None:
    """逐个关键设计族缺失时独立阻断，不因其他单元满足而通过。

    C-v1 的同一显示单元不能让终点定义和评估时间互相替代；研究包在进入
    GateSpec 前即要求每个核心试验同时具备两者。
    """
    single_unit_families = (
        DesignFieldFamily.ENDPOINT,
        DesignFieldFamily.TIMEPOINT,
    )
    for missing_family in (
        DesignFieldFamily.TRIAL_IDENTITY,
        DesignFieldFamily.POPULATION,
        DesignFieldFamily.GROUPING,
        DesignFieldFamily.INTERVENTION,
        DesignFieldFamily.DOSE_SCHEDULE,
        DesignFieldFamily.SAMPLE_SIZE,
    ):
        rows = tuple(
            item
            for item in _observations()
            if not (
                item.trial_id == "trial-alpha-1"
                and item.field_family is missing_family
            )
        )
        payload = _content_payload()
        payload["report_data"]["observations"] = [
            item.model_dump(mode="json") for item in rows
        ]
        payload["trial_designs"] = _trial_designs_payload(rows)
        outcome = _evaluate(module, payload)
        assert outcome.result.decision is ReportDecision.BLOCKED, missing_family

    # 终点/时间点是一个完整临床语义对：任一缺失即失败关闭。
    for missing_family in single_unit_families:
        rows = tuple(
            item
            for item in _observations()
            if not (
                item.trial_id == "trial-alpha-1"
                and item.field_family is missing_family
            )
        )
        payload = _content_payload()
        payload["report_data"]["observations"] = [
            item.model_dump(mode="json") for item in rows
        ]
        payload["trial_designs"] = _trial_designs_payload(rows)
        with pytest.raises(ValueError, match="终点实例|时间点实例"):
            module.FreshCResearchContent.model_validate(payload)

    both_rows = tuple(
        item
        for item in _observations()
        if not (
            item.trial_id == "trial-alpha-1"
            and item.field_family in single_unit_families
        )
    )
    payload = _content_payload()
    payload["report_data"]["observations"] = [
        item.model_dump(mode="json") for item in both_rows
    ]
    payload["trial_designs"] = _trial_designs_payload(both_rows)
    with pytest.raises(ValueError, match="终点实例|时间点实例"):
        module.FreshCResearchContent.model_validate(payload)


def test_protocol_sap_can_complete_registry_design_coverage(
    module: ModuleType,
) -> None:
    """方案/SAP 属于允许来源角色，可与登记共同覆盖关键设计。"""
    rows = [
        item
        for item in _observations()
        if not (
            item.trial_id == "trial-alpha-1"
            and item.field_family is DesignFieldFamily.ENDPOINT
        )
    ]
    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.ENDPOINT,
            "primary_endpoint_definition",
            "湿疹面积评分（方案第8.1节）",
            source_role=SourceRole.PROTOCOL_SAP,
            source_version_id="source-registry-2",
            group_id="group-trial-alpha-1-arm-1",
        )
    )
    payload = _content_payload()
    payload["report_data"]["observations"] = [
        item.model_dump(mode="json") for item in rows
    ]
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))
    outcome = _evaluate(module, payload)
    assert outcome.result.decision is ReportDecision.PASSED


def test_each_endpoint_requires_its_own_timepoint(module: ModuleType) -> None:
    """同一试验存在多个终点时，不得用一个主要终点时间点覆盖全部终点。"""
    rows = list(_observations())
    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.ENDPOINT,
            "secondary_endpoint_definition",
            "次要终点：瘙痒评分较基线变化",
            endpoint_key="secondary_endpoint",
        )
    )
    payload = _content_payload()
    payload["report_data"]["observations"] = [
        item.model_dump(mode="json") for item in rows
    ]
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))

    with pytest.raises(ValueError, match="缺评估时间点的终点实例.*secondary_endpoint"):
        module.FreshCResearchContent.model_validate(payload)

    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.TIMEPOINT,
            "secondary_endpoint_timepoint",
            "次要终点于第24周评估",
            endpoint_key="secondary_endpoint",
        )
    )
    payload["report_data"]["observations"] = [
        item.model_dump(mode="json") for item in rows
    ]
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))
    content = module.FreshCResearchContent.model_validate(payload)
    assert content.report_data.observations[-1].endpoint_key == "secondary_endpoint"


def test_region_visit_operational_follows_indication_rule(
    module: ModuleType,
) -> None:
    """地区/访视/操作特征仅在指示规则合同声明为关键时适用。"""
    outcome = _evaluate(
        module,
        _content_payload(
            applicable_conditional_predicates=["region_visit_operational_key"]
        ),
    )
    assert outcome.result.decision is ReportDecision.BLOCKED
    region = [
        item
        for item in outcome.result.unit_results
        if item.unit_id == "c_region_visit_operational"
    ]
    assert region
    assert all(item.outcome is GateUnitOutcome.BLOCKED for item in region)

    base = _content_payload()
    operational_rows = [
        _observation(
            trial.id,
            trial.product_id,
            DesignFieldFamily.OPERATIONAL,
            "visit_schedule",
            "每4周访视一次",
        ).model_dump(mode="json")
        for trial in _trials()
    ]
    base["report_data"]["observations"] = [
        *base["report_data"]["observations"],
        *operational_rows,
    ]
    satisfied = _evaluate(
        module,
        _content_payload(
            report_data=base["report_data"],
            applicable_conditional_predicates=["region_visit_operational_key"],
        ),
    )
    assert satisfied.result.decision is ReportDecision.PASSED


def test_statistical_extensions_are_nonblocking(module: ModuleType) -> None:
    """统计扩展单元缺失不阻断。"""
    outcome = _evaluate(module, _content_payload())
    assert outcome.result.decision is ReportDecision.PASSED
    statistical_units = (
        "c_analysis_population",
        "c_comparison_logic",
        "c_statistical_model",
        "c_effect_size",
        "c_multiplicity",
        "c_sample_size_assumptions",
        "c_estimand_intercurrent",
        "c_missing_data_sensitivity",
    )
    for unit_id in statistical_units:
        results = [
            item for item in outcome.result.unit_results if item.unit_id == unit_id
        ]
        assert results, unit_id
        assert all(
            item.outcome is GateUnitOutcome.EXTENSION_MISSING and item.blocking is False
            for item in results
        )


# ─── 多路径非排名约束 ────────────────────────────────────────────────────────


def test_content_requires_two_evidence_backed_candidate_paths(
    module: ModuleType,
) -> None:
    """候选设计路径必须至少两条且证据绑定可解析；真实综合输出满足同一合同。"""
    payload = _content_payload()
    payload["design_paths"] = _synthesis_payload(module)
    content = module.validate_fresh_c_content(payload)
    paths = content.design_paths.candidate_paths
    assert len(paths) >= 2
    signatures = {path.design_signature for path in paths}
    assert len(signatures) == len(paths)
    known = {item.observation_id for item in content.report_data.observations}
    for path in paths:
        assert path.observation_ids
        assert set(path.observation_ids) <= known


def test_content_accepts_single_evidence_backed_precedent_path(module: ModuleType) -> None:
    """一项完整研究可形成 C 先例；不得恢复旧的多候选方案门。"""
    payload = _content_payload()
    synthesis = _synthesis_payload(module)
    synthesis["candidate_paths"] = synthesis["candidate_paths"][:1]
    payload["design_paths"] = synthesis
    content = module.validate_fresh_c_content(payload)
    assert len(content.design_paths.candidate_paths) == 1
    assert content.design_paths.candidate_paths[0].observation_ids


def test_content_rejects_duplicate_design_signatures(module: ModuleType) -> None:
    """重复设计签名的候选路径失败关闭。"""
    payload = _content_payload()
    synthesis = _synthesis_payload(module)
    paths = [dict(item) for item in synthesis["candidate_paths"]]
    paths[1] = {**paths[0], "path_id": "path-duplicate"}
    synthesis["candidate_paths"] = paths
    payload["design_paths"] = synthesis
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


def test_content_rejects_path_referencing_unknown_observation(
    module: ModuleType,
) -> None:
    """候选路径引用未知观察必须失败关闭。"""
    payload = _content_payload()
    synthesis = _synthesis_payload(module)
    paths = [dict(item) for item in synthesis["candidate_paths"]]
    paths[0]["observation_ids"] = ["obs-does-not-exist"]
    synthesis["candidate_paths"] = paths
    payload["design_paths"] = synthesis
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


def test_content_rejects_ranking_semantics_in_metadata(
    module: ModuleType,
) -> None:
    """元数据携带排名/评分/最优等排名语义字段必须失败关闭。"""
    for key in ("rank", "ranking_score", "priority", "best_path", "推荐排名"):
        payload = _content_payload(metadata={key: 1})
        with pytest.raises(module.FreshCPackageError, match=key):
            module.validate_fresh_c_content(payload)


def test_design_paths_indication_must_match_content(module: ModuleType) -> None:
    """路径综合结果的适应症必须与内容一致。"""
    payload = _content_payload()
    payload["design_paths"] = _synthesis_payload(
        module, indication_id="prurigo-nodularis"
    )
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_content(payload)


# ─── 独立科学复核摘要绑定 ────────────────────────────────────────────────────


def _ready_package_payload(module: ModuleType) -> dict[str, object]:
    payload = _content_payload()
    payload["design_paths"] = _synthesis_payload(module)
    return payload


def test_package_binds_accepted_review_to_content_digest(
    module: ModuleType,
) -> None:
    """包构造要求复核接受且摘要与重算内容摘要一致。"""
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)
    package = module.validate_fresh_c_package(
        {**payload, "scientific_review": _review(module, content.content_digest)}
    )
    assert package.research_content_digest == content.content_digest

    # 内容摘要不随复核字段变化
    tampered_review = _review(module, content.content_digest)
    tampered_review["observations"] = ("补充一条无关观察。",)
    package_again = module.validate_fresh_c_package(
        {**payload, "scientific_review": tampered_review}
    )
    assert package_again.research_content_digest == content.content_digest


def test_package_rejects_rejected_or_digest_mismatched_review(
    module: ModuleType,
) -> None:
    """未接受复核或摘要不一致的复核必须失败关闭。"""
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)

    rejected = {
        **payload,
        "scientific_review": _review(
            module, content.content_digest, status="rejected"
        ),
    }
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_package(rejected)

    mismatched = {**payload, "scientific_review": _review(module, "0" * 64)}
    with pytest.raises(module.FreshCPackageError):
        module.validate_fresh_c_package(mismatched)


def test_package_rejects_self_review(module: ModuleType) -> None:
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)
    review = _review(module, content.content_digest)
    review["reviewer_id"] = payload["producer_id"]
    with pytest.raises(module.FreshCPackageError, match="不得由研究包生产者"):
        module.validate_fresh_c_package({**payload, "scientific_review": review})


def test_package_rejects_review_that_predates_sources(module: ModuleType) -> None:
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)
    review = _review(module, content.content_digest)
    review["reviewed_at"] = datetime(2026, 7, 31, tzinfo=UTC)
    with pytest.raises(module.FreshCPackageError, match="不得早于研究包来源获取时间"):
        module.validate_fresh_c_package({**payload, "scientific_review": review})


def test_c_observations_derive_closed_research_facts(module: ModuleType) -> None:
    content = module.validate_fresh_c_content(_ready_package_payload(module))
    facts = module.derive_c_research_facts(content)
    assert {item.fact_id for item in facts} == {
        item.row_id for item in content.report_data.observations
    }
    assert {item.source_id for item in facts} <= {
        item.source_id for item in content.sources
    }
    assert all(item.field_id.startswith("c.") for item in facts)


# ─── C 报告快照投影 ─────────────────────────────────────────────────────────


def _ready_package_and_outcome(module: ModuleType) -> tuple[object, object]:
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)
    package = module.validate_fresh_c_package(
        {**payload, "scientific_review": _review(module, content.content_digest)}
    )
    outcome = module.evaluate_c_report_gate(
        package,
        project_id=PROJECT_ID,
        evidence_snapshot_id="evidence-snapshot-1",
        contract_version="1",
    )
    assert outcome.result.decision is ReportDecision.PASSED
    return package, outcome


def test_projection_locks_c_report_snapshot_after_gate_and_review(
    module: ModuleType, tmp_path: Path
) -> None:
    """门槛通过且独立复核接受后才能锁定 C 报告快照，投影绑定谱系身份。"""
    package, outcome = _ready_package_and_outcome(module)
    projection = module.project_c_report_snapshot(
        package,
        outcome=outcome,
        project_root=tmp_path,
        project_id=PROJECT_ID,
        contract_version=1,
        evidence_snapshot_id="evidence-snapshot-1",
    )
    assert projection.report_snapshot.report == "C"
    snapshot_file = (
        tmp_path
        / "snapshots"
        / "reports"
        / "C"
        / f"{projection.report_snapshot.snapshot_id}.json"
    )
    assert snapshot_file.is_file()
    manifest = json.loads(snapshot_file.read_text(encoding="utf-8"))
    assert manifest["report"] == "C"
    assert manifest["evidence_snapshot_id"] == "evidence-snapshot-1"
    assert manifest["claim_ids"] == list(package.claim_ids)
    assert projection.claim_snapshot_id
    assert projection.coverage_set_id
    assert projection.gate_result_key
    # 门户数据绑定锁定快照标识；本模块不渲染，rendered_unreviewed 快捷路径不受影响
    assert (
        projection.portal_data.report_snapshot_id
        == projection.report_snapshot.snapshot_id
    )


def test_projection_is_idempotent(module: ModuleType, tmp_path: Path) -> None:
    """同一投影输入重复执行得到同一快照身份，不产生第二份内容。"""
    package, outcome = _ready_package_and_outcome(module)
    kwargs: dict[str, object] = dict(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        contract_version=1,
        evidence_snapshot_id="evidence-snapshot-1",
    )
    first = module.project_c_report_snapshot(package, outcome=outcome, **kwargs)
    second = module.project_c_report_snapshot(package, outcome=outcome, **kwargs)
    assert first.report_snapshot == second.report_snapshot
    assert first.claim_snapshot_id == second.claim_snapshot_id
    assert first.coverage_set_id == second.coverage_set_id


def test_run_service_executes_c_research_lineage_before_render(
    module: ModuleType, tmp_path: Path
) -> None:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["C"],
        outputs=["html"],
        cutoff="2026-09-01",
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)
    package_path = project_root / "inputs" / "c-research-package.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(
            {**payload, "scientific_review": _review(module, content.content_digest)},
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    run_context = RunContext(
        project_root=project_root,
        contract=contract,
        research_package_path=package_path,
    )
    result = run_project(
        project_root, run_context=run_context, capability_probe=StaticCapabilityProbe()
    )
    assert result.outcome == "completed"
    assert {
        "ingest",
        "gate:C",
        "snapshot:C",
        "analyze:C",
        "format:C",
    } <= result.node_summary.keys()
    current_manifest = json.loads(
        (project_root / "manifests/current_run.json").read_text(encoding="utf-8")
    )
    assert current_manifest["report_states"] == {"C": "rendered_unreviewed"}
    manifest = json.loads(
        (project_root / "reports/C/v1/html.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["evidence_snapshot_id"].startswith("evidence-snapshot_")
    assert manifest["report_snapshot_id"].startswith("report-snapshot_")

    from tests.unit.reports.b.test_fresh_b_research_package import (
        _write_verified_scientific_review,
    )

    _write_verified_scientific_review(
        project_root, current_manifest["scientific_review_contexts"]["C"]
    )
    promoted = run_project(
        project_root,
        resume=True,
        run_context=run_context,
        capability_probe=StaticCapabilityProbe(),
    )
    assert promoted.outcome == "completed"
    promoted_manifest = json.loads(
        (project_root / "manifests/current_run.json").read_text(encoding="utf-8")
    )
    assert promoted_manifest["report_states"] == {
        "C": "scientifically_reviewed_rendered_candidate"
    }


def test_projection_refuses_blocked_gate(module: ModuleType, tmp_path: Path) -> None:
    """门槛未通过时不得建立报告快照。"""
    payload = _ready_package_payload(module)
    rows = [
        item
        for item in _observations()
        if not (
            item.trial_id == "trial-alpha-1"
            and item.field_family is DesignFieldFamily.POPULATION
        )
    ]
    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.POPULATION,
            "target_population",
            "成人中重度患者（论文摘要）",
            source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        )
    )
    payload["report_data"]["observations"] = [
        item.model_dump(mode="json") for item in rows
    ]
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))
    content = module.validate_fresh_c_content(payload)
    blocked_package = module.validate_fresh_c_package(
        {**payload, "scientific_review": _review(module, content.content_digest)}
    )
    blocked_outcome = module.evaluate_c_report_gate(
        blocked_package,
        project_id=PROJECT_ID,
        evidence_snapshot_id="evidence-snapshot-1",
        contract_version="1",
    )
    assert blocked_outcome.result.decision is ReportDecision.BLOCKED
    with pytest.raises(module.FreshCPackageError):
        module.project_c_report_snapshot(
            blocked_package,
            outcome=blocked_outcome,
            project_root=tmp_path,
            project_id=PROJECT_ID,
            contract_version=1,
            evidence_snapshot_id="evidence-snapshot-1",
        )
    assert not (tmp_path / "snapshots" / "reports" / "C").exists()


def test_run_service_persists_recovery_state_for_blocked_c_evidence(
    module: ModuleType, tmp_path: Path
) -> None:
    """C 门槛阻断进入可恢复运行态，不伪装成报告完成或最终证据不足。"""
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["C"],
        outputs=["html"],
        cutoff="2026-09-01",
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    payload = _ready_package_payload(module)
    rows = [
        item
        for item in _observations()
        if not (
            item.trial_id == "trial-alpha-1"
            and item.field_family is DesignFieldFamily.POPULATION
        )
    ]
    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.POPULATION,
            "target_population",
            "成人中重度患者（论文摘要）",
            source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        )
    )
    observation_payloads = [item.model_dump(mode="json") for item in rows]
    source_payloads = payload["sources"]
    assert isinstance(source_payloads, list)
    _bind_observations_to_source_bytes(observation_payloads, source_payloads)
    payload["report_data"]["observations"] = observation_payloads
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))
    content = module.validate_fresh_c_content(payload)
    package_path = project_root / "inputs" / "c-research-package-blocked.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(
            {**payload, "scientific_review": _review(module, content.content_digest)},
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    result = run_project(
        project_root,
        run_context=RunContext(
            project_root=project_root,
            contract=contract,
            research_package_path=package_path,
        ),
        capability_probe=StaticCapabilityProbe(),
    )
    assert result.outcome == "running"
    assert result.node_summary["gate:C"] == "completed"
    assert result.node_summary["recovery:C"] == "awaiting_recovery"
    recovery = json.loads(
        (project_root / "state/work-items/c-evidence-recovery.json").read_text(
            encoding="utf-8"
        )
    )
    assert "c_target_population_criteria" in recovery["blocked_unit_ids"]
    assert (project_root / "manifests/current_run.json").is_file()
    assert not (project_root / "reports/C/v1/html").exists()


def test_fresh_c_double_exhaustion_publishes_reopenable_terminal_decision(
    module: ModuleType, tmp_path: Path
) -> None:
    from tests.integration.test_no_draft_when_blocked import gap_exhaustion

    contract = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff="2026-09-01"
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    payload = _ready_package_payload(module)
    rows = [
        item
        for item in _observations()
        if not (
            item.trial_id == "trial-alpha-1"
            and item.field_family is DesignFieldFamily.POPULATION
        )
    ]
    rows.append(
        _observation(
            "trial-alpha-1",
            "product-alpha",
            DesignFieldFamily.POPULATION,
            "target_population",
            "成人中重度患者（论文摘要）",
            source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        )
    )
    observation_payloads = [item.model_dump(mode="json") for item in rows]
    source_payloads = payload["sources"]
    assert isinstance(source_payloads, list)
    _bind_observations_to_source_bytes(observation_payloads, source_payloads)
    payload["report_data"]["observations"] = observation_payloads  # type: ignore[index]
    payload["trial_designs"] = _trial_designs_payload(tuple(rows))
    content = module.validate_fresh_c_content(payload)
    package_path = project_root / "inputs" / "c-research-package-blocked.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(
            {**payload, "scientific_review": _review(module, content.content_digest)},
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    context = RunContext(
        project_root=project_root, contract=contract, research_package_path=package_path
    )
    first = run_project(
        project_root, run_context=context, capability_probe=StaticCapabilityProbe()
    )
    assert first.outcome == "running"

    package = module.load_fresh_c_research_package(package_path)
    gate_outcome = module.evaluate_c_report_gate(
        package,
        project_id=contract.project_id,
        evidence_snapshot_id="test-snapshot",
        contract_version=str(contract.contract_version),
        fact_version_by_ref={
            observation.row_id: f"fact-version-{index}"
            for index, observation in enumerate(package.report_data.observations)
        },
    )
    blocked_pairs = sorted(
        (unit.unit_id, unit.object_id)
        for unit in gate_outcome.result.unit_results
        if unit.outcome is GateUnitOutcome.BLOCKED
    )
    record = DoubleExhaustionRecord(
        project_id=contract.project_id,
        report_kind=ReportKind.C,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{index}",
                gate_unit_id=unit_id,
                object_type="trial",
                object_id=object_id,
                current_state="not_reported",
                gate_spec_id=_gate_spec().spec_id,
            )
            for index, (unit_id, object_id) in enumerate(blocked_pairs, start=1)
        ),
        created_at=datetime.now(UTC),
    )
    path = exhaustion_path(project_root, ReportKind.C)
    path.write_text(
        json.dumps(
            record.model_dump(mode="json", exclude_computed_fields=True),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    second = run_project(
        project_root,
        resume=True,
        run_context=context,
        capability_probe=StaticCapabilityProbe(),
    )
    assert second.outcome == "evidence_blocked"
    assert second.exit_code == 4
    assert validate_run_manifest(project_root)["outcome"] == "evidence_blocked"

    third = run_project(
        project_root,
        resume=True,
        run_context=context,
        capability_probe=StaticCapabilityProbe(),
    )
    assert third.outcome == "evidence_blocked"
    assert validate_run_manifest(project_root)["run_id"] == third.run_id


def test_load_fresh_c_research_package_roundtrip(
    module: ModuleType, tmp_path: Path
) -> None:
    """包可落盘并以同一合同读回，内容摘要不变；损坏文件失败关闭。"""
    payload = _ready_package_payload(module)
    content = module.validate_fresh_c_content(payload)
    package = module.validate_fresh_c_package(
        {**payload, "scientific_review": _review(module, content.content_digest)}
    )
    path = tmp_path / "c-research-package.json"
    path.write_text(
        json.dumps(package.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    loaded = module.load_fresh_c_research_package(path)
    assert loaded.research_content_digest == package.research_content_digest

    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")
    with pytest.raises(module.FreshCPackageError):
        module.load_fresh_c_research_package(broken)
