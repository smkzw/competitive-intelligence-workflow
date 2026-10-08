"""C 类新鲜来源研究包：类型化内容、登记优先 GateSpec、多路径非排名约束、
独立科学复核摘要绑定与 C 报告快照投影。

本模块是宿主 Agent 与确定性执行器之间的 C 类交接合同：

- 类型化内容只绑定 C 类门户模型 ``ReportCPortalData``，不复制 A 类门户模型；
- 设计事实沿用 ``reports.c`` 的强类型 ``DesignObservation``，并以官方登记
  来源为唯一关键设计权威（论文只作身份交叉核验，方案/SAP 可补充）；
- GateSpec 评估复用共享证据门槛引擎（当前 ``policies/gates/C-v2.yaml``，
  旧 C-v1 保持产品根兼容）：
  内容确定性推导适用宇宙快照与证据绑定，不接受调用方传入门槛结论；
- 多路径是证据支持的选项空间；先例数量不设两条最低门，签名重复或元数据
  携带排名语义仍失败关闭，不生成唯一"最佳方案"；
- 独立科学复核绑定重算内容摘要：未接受或摘要不一致的包不得进入投影；
- 报告快照仅在确定性 GateSpec 通过且独立复核接受后锁定，投影幂等，
  门户数据回绑锁定快照标识；``rendered_unreviewed`` 快捷路径不受影响。

来源/事实/声明/复核的通用原语通过 ``fresh_research_primitives`` 的稳定
导入面复用既有 report-agnostic 模型。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.application.ctgov_c_design_projection import (
    ELIGIBILITY_SECTION_COMPATIBILITY_RULE,
    replay_ctgov_eligibility_section,
)
from ci_workflow.application.ctgov_design_atoms import extract_ctgov_protocol_design_atoms
from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    RouteAttempt,
    ScientificReview,
    SourceCapture,
)
from ci_workflow.domain.enums import (
    FactDisclosureState,
    FactReviewState,
    ReportKind,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    EmptySetProof,
    EmptySetReasonCode,
    FactDomain,
    GateEvidenceBinding,
    GateObjectType,
    GateSpec,
    ObservationKind,
    ReportDecision,
    ReportGateResult,
    SourceRole,
    TrialDesignEvidence,
    TrialDesignKind,
    UniverseEdge,
    compute_gate_result_key,
    compute_universe_summary,
    evidence_binding_qualifies,
)
from ci_workflow.renderers.portal.report_c import ReportCPortalData
from ci_workflow.reports.c import DesignFieldFamily, DesignObservation
from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    validate_endpoint_timepoint_pairs,
)
from ci_workflow.reports.c.synthesis import DesignPathSynthesisResult
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    ReportSnapshotManifest,
    SnapshotIntegrityError,
    SnapshotStore,
    compute_locked_snapshot,
)
from ci_workflow.storage.source_derivation import SourceDerivationError, extract_locator_quote

_C_GATE_SPEC_PATH = (
    Path(__file__).resolve().parents[3] / "policies" / "gates" / "C-v2.yaml"
)

# C 研究角色与指示规则集合的稳定标识：登记优先设计事实的封闭来源角色
# 由 GateSpec 单元的 allowed_source_roles 承载，本标识只用于宇宙摘要绑定。
_C_RESEARCH_ROLE_SET_ID = "c-design-source-roles-v1"
_C_INDICATION_RULE_SET_ID = "c-design-indication-rules-v1"

# 登记优先设计事实族 → C GateSpec 单元（关键 + 扩展）。
_FAMILY_UNIT_BY_FAMILY: Mapping[DesignFieldFamily, str] = {
    DesignFieldFamily.TRIAL_IDENTITY: "c_trial_identity_stage_role",
    DesignFieldFamily.POPULATION: "c_target_population_criteria",
    DesignFieldFamily.GROUPING: "c_arm_randomization_blinding",
    DesignFieldFamily.INTERVENTION: "c_intervention_control_rescue",
    DesignFieldFamily.DOSE_SCHEDULE: "c_dose_schedule_followup",
    DesignFieldFamily.SAMPLE_SIZE: "c_planned_or_actual_sample_size",
    DesignFieldFamily.OPERATIONAL: "c_region_visit_operational",
}

# 统计扩展按字段映射到非阻断扩展单元；未登记字段不产生绑定。
_STATISTICAL_FIELD_UNITS: Mapping[str, str] = {
    "analysis_population": "c_analysis_population",
    "comparison_logic": "c_comparison_logic",
    "statistical_model": "c_statistical_model",
    "effect_size": "c_effect_size",
    "multiplicity": "c_multiplicity",
    "sample_size_assumptions": "c_sample_size_assumptions",
    "estimand_intercurrent": "c_estimand_intercurrent",
    "missing_data_sensitivity": "c_missing_data_sensitivity",
}

# 多路径非排名：元数据不得携带排名/评分/优先/最优等裁决语义字段。
_RANKING_KEY_RE = re.compile(
    r"(?:rank|rating|score|priority|best|prefer|排名|评分|排序|优先|最优|最佳)",
    re.IGNORECASE,
)


class FreshCPackageError(ValueError):
    """C 类新鲜来源研究包不能形成可审计科学真源。"""


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("C 类研究包时间必须包含明确时区")
    return value


def _locator_text(locator: EvidenceLocator) -> str:
    """把精确证据定位确定为稳定文本，用作绑定的来源定位。"""
    parts = [
        part
        for part in (
            locator.document_role,
            locator.field_path,
            locator.heading,
            locator.table,
            locator.row,
            locator.column,
            f"第{locator.page}页" if locator.page is not None else None,
            locator.paragraph,
            locator.url,
        )
        if part
    ]
    return " / ".join(parts)


class CTrialDesign(BaseModel):
    """一项试验的设计类型声明；证据锚定该试验的一条设计观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    design_kind: TrialDesignKind
    observation_id: str

    @field_validator("trial_id", "observation_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("试验设计声明字段不能为空")
        return normalized


class FreshCResearchContent(BaseModel):
    """独立复核前可规范化、可摘要的 C 类科学内容。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    indication_id: str
    indication: str
    data_cutoff: datetime
    report_version: str
    producer_id: str
    endpoint_identity_mode: Literal["instance_v1"] = "instance_v1"
    report_data: ReportCPortalData
    sources: tuple[SourceCapture, ...] = Field(min_length=1)
    route_attempts: tuple[RouteAttempt, ...] = ()
    claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    trial_designs: tuple[CTrialDesign, ...] = Field(min_length=1)
    design_paths: DesignPathSynthesisResult
    applicable_conditional_predicates: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = {}

    @field_validator("indication_id", "indication", "report_version", "producer_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("C 类研究包身份字段不能为空")
        return normalized

    @field_validator("data_cutoff")
    @classmethod
    def _cutoff_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("applicable_conditional_predicates")
    @classmethod
    def _predicates_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(" ".join(item.split()) for item in values)
        if any(not item for item in normalized):
            raise ValueError("条件适用性谓词不能为空")
        if len(set(normalized)) != len(normalized):
            raise ValueError("条件适用性谓词不得重复")
        if "always_applicable" in normalized:
            raise ValueError("条件谓词集合不得包含无条件谓词")
        return normalized

    @property
    def universe_product_ids(self) -> tuple[str, ...]:
        return self.report_data.product_ids

    @property
    def universe_trial_ids(self) -> tuple[str, ...]:
        return self.report_data.trial_ids

    @property
    def claim_ids(self) -> tuple[str, ...]:
        return tuple(claim.claim_id for claim in self.claims)

    @property
    def content_digest(self) -> str:
        """规范化 C 类科学内容摘要；独立科学复核必须绑定该摘要。"""
        return _digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def _content_is_closed(self) -> FreshCResearchContent:
        if any(
            item.disclosure_state is FactDisclosureState.USER_CLEARED
            for item in self.report_data.observations
        ):
            raise FreshCPackageError("用户清除属于修订当前层，不得进入原始 C 研究包")
        if self.indication != self.report_data.indication:
            raise FreshCPackageError("研究包与报告数据的适应症不一致")
        if self.indication_id != self.report_data.indication_id:
            raise FreshCPackageError("研究包与报告数据的适应症标识不一致")
        if self.data_cutoff != self.report_data.data_cutoff:
            raise FreshCPackageError("研究包与报告数据的数据截止不一致")
        if self.report_version != self.report_data.report_version:
            raise FreshCPackageError("研究包与报告数据的报告版本不一致")
        if self.design_paths.indication_id != self.indication_id:
            raise FreshCPackageError("候选设计路径与研究包的适应症标识不一致")
        if any(not item.is_available_by(self.data_cutoff)
               for item in self.sources):
            raise FreshCPackageError("截止日之后或无法证明截止时点前首次披露的来源不得进入当前快照")

        source_ids = {item.source_id for item in self.sources}
        observation_rows = self.report_data.observations
        row_ids = [item.row_id for item in observation_rows]
        if len(row_ids) != len(set(row_ids)):
            raise FreshCPackageError("设计观察行标识重复")
        for observation in observation_rows:
            if observation.source_version_id not in source_ids:
                raise FreshCPackageError(
                    f"设计观察引用了研究包外来源：{observation.row_id}"
                )
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise FreshCPackageError("声明标识重复")
        row_id_set = set(row_ids)
        for claim in self.claims:
            unknown = set(claim.fact_ids) - row_id_set
            if unknown:
                raise FreshCPackageError(f"声明引用了研究包外观察：{claim.claim_id}")
        self._validate_trial_designs()
        self._validate_intervention_relationships()
        self._validate_endpoint_timepoint_pairs()
        self._validate_design_paths()
        self._reject_ranking_metadata()
        return self

    def _validate_intervention_relationships(self) -> None:
        gaps = [
            item for item in self.report_data.observations
            if getattr(item, "relationship_blocking", False)
        ]
        if gaps:
            details = "、".join(
                f"{item.trial_id}:{item.relationship_status or 'unknown'}"
                for item in gaps
            )
            raise FreshCPackageError(f"干预与 arm 的显式关系缺失，设计包阻断：{details}")

    def _validate_endpoint_timepoint_pairs(self) -> None:
        """新 Fresh C 内容只接受逐 outcome 实例身份。"""
        from ci_workflow.reports.c.endpoint_instances import (
            validate_endpoint_timepoint_pairs,
        )

        validate_endpoint_timepoint_pairs(
            self.report_data.observations,
            universe_trial_ids=set(self.universe_trial_ids),
            protocol_sources={
                source.source_id: source.content_text for source in self.sources
                if source.media_type == "application/json"
                and source.source_type == "clinical_trial_registry"
            },
        )

    def _validate_trial_designs(self) -> None:
        design_trial_ids = [item.trial_id for item in self.trial_designs]
        if len(design_trial_ids) != len(set(design_trial_ids)):
            raise FreshCPackageError("每项试验只能有一条设计类型声明")
        if set(design_trial_ids) != set(self.universe_trial_ids):
            raise FreshCPackageError("设计类型声明必须恰好覆盖全部试验")
        observation_ids_by_trial: dict[str, set[str]] = {}
        for observation in self.report_data.observations:
            observation_ids_by_trial.setdefault(observation.trial_id, set()).add(
                observation.observation_id
            )
        for design in self.trial_designs:
            if design.observation_id not in observation_ids_by_trial.get(
                design.trial_id, set()
            ):
                raise FreshCPackageError(
                    f"设计类型声明引用了该试验之外的观察：{design.trial_id}"
                )

    def _validate_design_paths(self) -> None:
        # 独立审阅 R09（C01）：删除"候选路径不足两条"门槛——
        # 设计先例库合同下一项完整研究即可交付，有几条先例展示几条；
        # 旧门槛是 v1.3 全景比较时代的产物，不再约束新 C 输入
        paths = self.design_paths.candidate_paths
        signatures = [path.design_signature for path in paths]
        if len(set(signatures)) != len(signatures):
            raise FreshCPackageError("候选设计路径的设计签名不得重复")
        observation_ids = {
            item.observation_id for item in self.report_data.observations
        }
        trial_ids = set(self.universe_trial_ids)
        for path in paths:
            if set(path.observation_ids) - observation_ids:
                raise FreshCPackageError(
                    f"候选设计路径引用了研究包外观察：{path.path_id}"
                )
            if set(path.trial_ids) - trial_ids:
                raise FreshCPackageError(
                    f"候选设计路径引用了研究包外试验：{path.path_id}"
                )

    def _reject_ranking_metadata(self) -> None:
        for key in self.metadata:
            key_text = str(key)
            if _RANKING_KEY_RE.search(key_text):
                raise FreshCPackageError(
                    f"C 类研究包元数据不得携带排名语义字段：{key_text}"
                )


def validate_fresh_c_content(
    payload: FreshCResearchContent | Mapping[str, Any],
) -> FreshCResearchContent:
    """公共边界：校验 C 类科学内容，全部合同错误统一为 FreshCPackageError。"""
    if isinstance(payload, FreshCResearchContent):
        payload = payload.model_dump(mode="json", exclude={"scientific_review"})
    try:
        return FreshCResearchContent.model_validate(payload)
    except ValidationError as error:
        raise FreshCPackageError(f"C 类科学内容不符合合同：{error}") from error


class FreshCResearchPackage(FreshCResearchContent):
    """可由任意宿主 Agent 生成、由本地执行器验真的完整 C 类交接包。"""

    scientific_review: ScientificReview

    @property
    def content_digest(self) -> str:
        """包上的内容摘要排除独立复核字段，与纯内容摘要一致。"""
        return self.research_content_digest

    @property
    def research_content(self) -> dict[str, Any]:
        return FreshCResearchContent.model_validate(
            self.model_dump(mode="json", exclude={"scientific_review"})
        ).model_dump(mode="json")

    @property
    def research_content_digest(self) -> str:
        return _digest(self.research_content)

    @model_validator(mode="after")
    def _package_is_independently_accepted(self) -> FreshCResearchPackage:
        if self.scientific_review.status != "accepted":
            raise FreshCPackageError("独立科学复核未接受，不得生成报告")
        if self.scientific_review.reviewer_id == self.producer_id:
            raise FreshCPackageError("独立科学复核不得由研究包生产者身份自行批准")
        if self.scientific_review.reviewed_at < max(
            source.acquired_at for source in self.sources
        ):
            raise FreshCPackageError("独立科学复核时间不得早于研究包来源获取时间")
        if self.scientific_review.reviewed_content_digest != self.research_content_digest:
            raise FreshCPackageError("独立科学复核与当前研究内容摘要不一致")
        return self


def derive_c_research_facts(
    content: FreshCResearchContent,
) -> tuple[ResearchFact, ...]:
    """Project typed design observations into shared atomic evidence facts."""
    trial_names = {item.id: item.name for item in content.report_data.trials}
    return research_facts_from_c_observations(
        content.report_data.observations, sources=content.sources, trial_names=trial_names,
    )


def research_facts_from_c_observations(
    observations: Sequence[DesignObservation], *, sources: Sequence[SourceCapture],
    trial_names: Mapping[str, str],
) -> tuple[ResearchFact, ...]:
    """Prepare C candidate atoms for shared ingestion; never approve or persist here.

    CT.gov derived eligibility text is the normalized section, not an invented
    scalar quote. Its original/raw value remains the full source scalar. Generic
    legacy documents retain their original contract and ingestion's locator gate.
    """
    by_source = {source.source_id: source for source in sources}
    if len(by_source) != len(sources):
        raise FreshCPackageError("C 事实来源实例重复")
    facts = []
    for item in observations:
        source = by_source.get(item.source_version_id)
        if source is None or item.trial_id not in trial_names:
            raise FreshCPackageError("C 事实引用了集合外的来源或试验")
        original = item.source_text
        path = item.source_locator.field_path or ""
        if (source.media_type == "application/json"
                and source.source_type == "clinical_trial_registry"
                and path.startswith("$.protocolSection.")):
            try:
                record = json.loads(source.content_text)
                nct_id = record["protocolSection"]["identificationModule"]["nctId"]
                original = extract_locator_quote(
                    source.content_text, media_type=source.media_type, locator=item.source_locator,
                )
            except (ValueError, KeyError, TypeError, SourceDerivationError) as error:
                raise FreshCPackageError("C 登记事实不能从来源精确重提取") from error
            if (str(nct_id).casefold() != item.trial_id.casefold()
                    or item.source_locator.url != source.url):
                raise FreshCPackageError("C 登记事实的试验或来源链接不匹配")
            if original != item.source_text:
                if (path != "$.protocolSection.eligibilityModule.eligibilityCriteria"
                        or item.compatibility_rule != ELIGIBILITY_SECTION_COMPATIBILITY_RULE):
                    raise FreshCPackageError("C 原文与精确来源不一致，且没有合法分段规则")
                try:
                    section = replay_ctgov_eligibility_section(original, item.field)
                except ValueError as error:
                    raise FreshCPackageError("C 入排段落不能按已声明规则重放") from error
                if section != item.source_text:
                    raise FreshCPackageError("C 入排段落与完整来源的确定性分段不一致")
        facts.append(ResearchFact.model_validate({
                "fact_id": item.row_id,
                "row_ref": item.row_id,
                "entity_id": item.trial_id,
                "entity_type": "trial",
                "canonical_name": trial_names[item.trial_id],
                "field_id": f"c.{item.field_family.value}.{item.field}",
                "raw_value": original,
                "normalized_value": item.source_text,
                "disclosure_state": item.disclosure_state.value,
                "source_id": item.source_version_id,
                "locator": item.source_locator,
                "original_text": original,
                **({"source_clause_context": item.source_clause_context}
                   if item.source_clause_context is not None else {}),
            }))
    return tuple(facts)


def validate_fresh_c_package(
    payload: FreshCResearchPackage | Mapping[str, Any],
) -> FreshCResearchPackage:
    """公共边界：校验完整 C 类交接包，合同错误统一为 FreshCPackageError。"""
    if isinstance(payload, FreshCResearchPackage):
        payload = payload.model_dump(mode="json")
    try:
        return FreshCResearchPackage.model_validate(payload)
    except ValidationError as error:
        raise FreshCPackageError(f"C 类新鲜来源研究包不符合合同：{error}") from error


# ── GateSpec 绑定：内容 → 适用宇宙快照 + 证据绑定 ───────────────────────────


def _unit_id_for(observation: DesignObservation) -> str | None:
    if observation.field_family in {DesignFieldFamily.ENDPOINT, DesignFieldFamily.TIMEPOINT}:
        # ENDPOINT is a scientific domain, not proof of primary/key-secondary
        # status. Preserve all other endpoint facts in the report, without
        # using them to fill the critical C-v1 coverage unit.
        if observation.endpoint_key in {
            "primary_endpoint", "important_secondary_endpoint", "key_secondary_endpoint",
        }:
            return "c_endpoint_definitions_timepoints"
        return None
    if observation.field_family is DesignFieldFamily.STATISTICAL:
        return _STATISTICAL_FIELD_UNITS.get(observation.field)
    return _FAMILY_UNIT_BY_FAMILY.get(observation.field_family)


def build_c_gate_bindings(
    content: FreshCResearchContent,
    *,
    fact_version_by_ref: Mapping[str, str] | None = None,
    study_first: bool = False,
    spec: GateSpec | None = None,
) -> tuple[GateEvidenceBinding, ...]:
    """从设计观察确定性推导 C 类证据绑定。

    - 每条设计观察映射到其字段族的 GateSpec 单元；统计扩展按字段映射；
    - 绑定保留真实复核/披露/冲突状态，不合格事实由共享引擎过滤；
    - C 单元均为试验级：绑定以试验为对象，不携带组别作用域；
    - 样本量单元的必需上下文来自观察的阈值数值与单位；已报告零值保留
      显式零值原文，不适用事实不携带数值。
    """
    bindings: list[GateEvidenceBinding] = []
    binding_by_observation: dict[str, GateEvidenceBinding] = {}
    observations = {row.observation_id: row for row in content.report_data.observations}
    qualified_design_trials = {
        design.trial_id for design in content.trial_designs
        if (observations[design.observation_id].field_family is DesignFieldFamily.GROUPING
            and observations[design.observation_id].review_state is FactReviewState.ACCEPTED
            and observations[design.observation_id].source_role in {
                SourceRole.CLINICAL_TRIAL_REGISTRY, SourceRole.PROTOCOL_SAP,
            }
            and observations[design.observation_id].disclosure_state in {
                FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO,
            })
    }
    for observation in content.report_data.observations:
        unit_id = _unit_id_for(observation)
        if unit_id is None:
            continue
        if (study_first and unit_id == "c_arm_randomization_blinding"
                and observation.trial_id not in qualified_design_trials):
            # Other accepted grouping rows cannot launder a wrong-family or
            # unaccepted design anchor into critical coverage. Keep the source
            # observations; the existing engine reports missing evidence.
            continue
        numeric_value: float | None = None
        unit_text: str | None = None
        if observation.threshold_value is not None:
            try:
                numeric_value = float(observation.threshold_value.replace(",", ""))
            except ValueError:
                numeric_value = None
            unit_text = observation.threshold_unit
        if observation.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
            numeric_value = None
            unit_text = None
        elif (
            observation.disclosure_state is FactDisclosureState.REPORTED_ZERO
            and numeric_value is None
        ):
            numeric_value = 0.0
        bindings.append(
            GateEvidenceBinding(
                schema_version="1.0",
                binding_id=stable_id(
                    "c-gate-binding",
                    observation.observation_id,
                    unit_id,
                    observation.disclosure_state.value,
                ),
                unit_id=unit_id,
                object_id=observation.trial_id,
                fact_version_id=(
                    fact_version_by_ref[observation.row_id]
                    if fact_version_by_ref is not None
                    else stable_id(
                        "c-fact-version",
                        observation.row_id,
                        observation.source_version_id,
                        observation.observation_id,
                    )
                ),
                trial_id=observation.trial_id,
                fact_domain=FactDomain.TRIAL_DESIGN,
                observation_kind=ObservationKind.PLANNED_VALUE,
                numeric_value=numeric_value,
                unit=unit_text,
                definition=observation.source_text,
                source_location=_locator_text(observation.source_locator),
                route_receipt_id=observation.route_receipt_id,
                review_state=observation.review_state,
                disclosure_state=observation.disclosure_state,
                disclosure_maturity=observation.disclosure_maturity,
                source_role=observation.source_role,
                conflict_disposition=observation.conflict_disposition,
                applicability_predicate_id=observation.applicability_predicate_id,
                reported_zero_text=observation.reported_zero_text,
            )
        )
        binding_by_observation[observation.observation_id] = bindings[-1]
    if study_first:
        gate_spec = spec if spec is not None else GateSpec.from_yaml(_C_GATE_SPEC_PATH)
        incomplete = _incomplete_c_compound_units(content, binding_by_observation, gate_spec)
        return tuple(binding for binding in bindings
                     if (binding.trial_id, binding.unit_id) not in incomplete)
    return tuple(bindings)


def _incomplete_c_compound_units(
    content: FreshCResearchContent,
    bindings: Mapping[str, GateEvidenceBinding],
    spec: GateSpec,
) -> set[tuple[str, str]]:
    """Only complete qualified source families may prove a compound C unit.

    Preserve original observations and candidate status. This filters proof
    bindings, not report facts; the existing evaluator reports a blocked unit.
    No counts, new ontology or approval path substitute for scientific coverage.
    """
    units = {unit.unit_id: unit for unit in spec.units}
    source_text = {source.source_id: source.content_text for source in content.sources
                   if source.media_type == "application/json"
                   and source.source_type == "clinical_trial_registry"}
    design_by_trial = {design.trial_id: design for design in content.trial_designs}
    incomplete: set[tuple[str, str]] = set()
    for trial_id in content.universe_trial_ids:
        rows = tuple(row for row in content.report_data.observations if row.trial_id == trial_id)

        def eligible(
            unit_id: str, candidates: tuple[DesignObservation, ...] = rows,
        ) -> tuple[DesignObservation, ...]:
            return tuple(row for row in candidates
                         if (binding := bindings.get(row.observation_id)) is not None
                         and binding.unit_id == unit_id
                         and evidence_binding_qualifies(binding, units[unit_id]))

        population_unit = "c_target_population_criteria"
        population = eligible(population_unit)
        # The current native adapter assigns both minimumAge and the complete
        # eligibility scalar to target_population. The age scalar cannot prove
        # the combined population/criteria requirement.
        population_complete = any(
            row.field == "target_population"
            and (row.source_locator.field_path ==
                 "$.protocolSection.eligibilityModule.eligibilityCriteria"
                 if row.source_locator.field_path and
                 row.source_locator.field_path.startswith("$.protocolSection.")
                 else row.source_field_name not in {"minimumAge", "maximumAge", "age"})
            for row in population
        )
        if not population_complete:
            incomplete.add((trial_id, population_unit))

        grouping_unit = "c_arm_randomization_blinding"
        grouping = eligible(grouping_unit)
        grouping_complete = any(
            row.randomization is not None and row.blinding is not None
            and not (row.source_locator.field_path or "").startswith("$.protocolSection.")
            for row in grouping
        )
        required_paths = {
            "$.protocolSection.designModule.designInfo.allocation",
            "$.protocolSection.designModule.designInfo.interventionModel",
            "$.protocolSection.designModule.designInfo.maskingInfo.masking",
        }
        for source_id in {row.source_version_id for row in grouping}:
            native = [row for row in grouping if row.source_version_id == source_id]
            if not required_paths <= {row.source_locator.field_path for row in native}:
                continue
            model_values = {row.source_text for row in native if row.source_locator.field_path ==
                            "$.protocolSection.designModule.designInfo.interventionModel"}
            design = design_by_trial[trial_id]
            single = design.design_kind is TrialDesignKind.SINGLE_ARM
            recognized_models = {"SINGLE_GROUP", "PARALLEL", "CROSSOVER", "FACTORIAL", "SEQUENTIAL"}
            if (len(model_values) == 1 and model_values <= recognized_models
                    and (("SINGLE_GROUP" in model_values) == single)):
                grouping_complete = True
        if not grouping_complete:
            incomplete.add((trial_id, grouping_unit))

        endpoint_unit = "c_endpoint_definitions_timepoints"
        critical = tuple(row for row in rows if _unit_id_for(row) == endpoint_unit)
        try:
            original_instances = set(validate_endpoint_timepoint_pairs(
                critical, universe_trial_ids={trial_id}, protocol_sources=source_text,
            ))
            qualified_instances = set(validate_endpoint_timepoint_pairs(
                eligible(endpoint_unit), universe_trial_ids={trial_id},
                protocol_sources=source_text,
            ))
            endpoint_complete = (bool(original_instances)
                                 and original_instances == qualified_instances)
        except EndpointInstanceError:
            endpoint_complete = False
        if not endpoint_complete:
            incomplete.add((trial_id, endpoint_unit))

        # Coverage must not shrink with submitted rows. Reuse the source-atom
        # extractor to enumerate independently retained official source paths;
        # do not rebuild expected objects from the surviving observations.
        # A complete selected source version may prove a unit. Other historical
        # versions are not silently merged into that version's coverage.
        native_expected: set[str] = set()
        native_complete: set[str] = set()
        native_fields = {
            "ctgov.protocol.design.study_type": "c_trial_identity_stage_role",
            "ctgov.protocol.design.phase": "c_trial_identity_stage_role",
            "ctgov.protocol.arm.intervention_name": "c_intervention_control_rescue",
            "ctgov.protocol.arm.description": "c_dose_schedule_followup",
            "ctgov.protocol.primary_outcome.measure": endpoint_unit,
            "ctgov.protocol.primary_outcome.time_frame": endpoint_unit,
        }
        for source in content.sources:
            if (source.source_id not in source_text
                    or source.query_or_identifier.casefold() != trial_id.casefold()):
                continue
            record = json.loads(source.content_text)
            if not isinstance(record, dict) or "protocolSection" not in record:
                continue  # Generic documents retain their existing contracts.
            atoms = extract_ctgov_protocol_design_atoms(source)
            expected_by_unit: dict[str, set[tuple[str | None, str | None]]] = {}
            for atom in atoms.facts:
                if (unit_id := native_fields.get(atom.field_id)) is not None:
                    expected_by_unit.setdefault(unit_id, set()).add(
                        (atom.locator.field_path, atom.raw_value)
                    )
            for unit_id, expected in expected_by_unit.items():
                native_expected.add(unit_id)
                observed = {
                    (row.source_locator.field_path, row.source_text)
                    for row in eligible(unit_id)
                    if row.source_version_id == source.source_id
                    and (unit_id not in {"c_intervention_control_rescue",
                                         "c_dose_schedule_followup"}
                         or row.relationship_status == "bound")
                }
                if expected <= observed:
                    native_complete.add(unit_id)
        incomplete.update((trial_id, unit_id) for unit_id in native_expected - native_complete)
    return incomplete


def build_c_gate_snapshot(
    content: FreshCResearchContent,
    *,
    project_id: str,
    evidence_snapshot_id: str,
    study_first: bool = False,
) -> ApplicableUniverseSnapshot:
    """从 C 内容枚举当前输入内的适用对象，非全球/中国发现闭包证明。

    C GateSpec 单元全部为试验级：比较/组别对象仅在设计类型声明为比较
    试验且观察携带组别作用域时按证据推导，其余对象类为带类型化证明的
    空集合；每项试验必须恰好对应一条设计类型声明。
    """
    product_ids = content.universe_product_ids
    trial_ids = content.universe_trial_ids
    indication_rule_set_id = ("c-design-source-object-coverage-v2" if study_first
                              else _C_INDICATION_RULE_SET_ID)
    observations_by_trial: dict[str, list[DesignObservation]] = {
        trial_id: [] for trial_id in trial_ids
    }
    for observation in content.report_data.observations:
        observations_by_trial[observation.trial_id].append(observation)
    group_ids_by_trial: dict[str, tuple[str, ...]] = {
        trial_id: tuple(sorted({item.group_id for item in rows if item.group_id}))
        for trial_id, rows in observations_by_trial.items()
    }

    edges: list[UniverseEdge] = []
    group_ids: set[str] = set()
    comparison_ids: list[str] = []
    endpoint_ids: list[str] = []
    timepoint_ids: list[str] = []
    for trial in content.report_data.trials:
        if trial.product_id is None:
            if not study_first:
                raise FreshCPackageError("旧产品根合同不接受待核产品关联的试验")
        else:
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.PRODUCT,
                    parent_id=trial.product_id,
                    child_type=GateObjectType.TRIAL,
                    child_id=trial.id,
                )
            )
        for group_id in group_ids_by_trial[trial.id]:
            group_ids.add(group_id)
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.TRIAL,
                    parent_id=trial.id,
                    child_type=GateObjectType.GROUP,
                    child_id=group_id,
                )
            )
    for design in content.trial_designs:
        if design.design_kind is not TrialDesignKind.COMPARATIVE:
            continue
        trial_groups = group_ids_by_trial[design.trial_id]
        if len(trial_groups) < 2:
            raise FreshCPackageError(
                f"比较设计试验必须存在至少两个组别作用域证据：{design.trial_id}"
            )
        comparison_id = stable_id("c-comparison", design.observation_id)
        comparison_ids.append(comparison_id)
        edges.append(
            UniverseEdge(
                parent_type=GateObjectType.TRIAL,
                parent_id=design.trial_id,
                child_type=GateObjectType.COMPARISON,
                child_id=comparison_id,
            )
        )
        for group_id in trial_groups:
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.COMPARISON,
                    parent_id=comparison_id,
                    child_type=GateObjectType.GROUP,
                    child_id=group_id,
                )
            )

    if study_first:
        # Reuse the source-backed instance validator, including exact protocol
        # parent checks. Do not collapse different sources/groups/windows by
        # endpoint role or invent a missing results-period field.
        instances = validate_endpoint_timepoint_pairs(
            content.report_data.observations,
            universe_trial_ids=set(trial_ids),
            protocol_sources={
                source.source_id: source.content_text for source in content.sources
                if source.media_type == "application/json"
                and source.source_type == "clinical_trial_registry"
            },
        )
        for instance in instances:
            endpoint_id = stable_id("c-endpoint-instance", _digest(vars(instance)))
            timepoint_id = stable_id("c-timepoint-instance", endpoint_id, instance.timepoint or "")
            endpoint_ids.append(endpoint_id)
            timepoint_ids.append(timepoint_id)
            edges.extend((
                UniverseEdge(parent_type=GateObjectType.TRIAL, parent_id=instance.trial_id,
                             child_type=GateObjectType.ENDPOINT, child_id=endpoint_id),
                UniverseEdge(parent_type=GateObjectType.ENDPOINT, parent_id=endpoint_id,
                             child_type=GateObjectType.GROUP, child_id=instance.group_id),
                UniverseEdge(parent_type=GateObjectType.ENDPOINT, parent_id=endpoint_id,
                             child_type=GateObjectType.TIMEPOINT, child_id=timepoint_id),
            ))

    observation_by_id = {row.observation_id: row for row in content.report_data.observations}
    source_by_id = {source.source_id: source for source in content.sources}

    def design_evidence_id(design: CTrialDesign) -> str:
        if not study_first:
            return stable_id("c-design-evidence", design.observation_id, design.design_kind.value)
        anchor = observation_by_id[design.observation_id]
        # Consumer row/display choices do not constitute scientific change.
        scientific = anchor.model_dump(mode="json", exclude={
            "row_id", "source_row_id", "display_text", "difference_labels_zh",
        })
        source = source_by_id[anchor.source_version_id]
        source_material = {"source_id": source.source_id, "url": source.url,
                           "source_type": source.source_type, "media_type": source.media_type,
                           "content_text": source.content_text}
        return stable_id("c-design-evidence", design.observation_id, design.design_kind.value,
                         _digest(scientific), _digest(source_material))

    trial_design_evidence = tuple(
        TrialDesignEvidence(
            trial_id=design.trial_id,
            design_kind=design.design_kind,
            evidence_version_id=design_evidence_id(design),
            explanation_zh="试验设计类型声明，证据锚定该试验的设计观察",
        )
        for design in content.trial_designs
    )

    single_arm_only = study_first and all(
        row.design_kind is TrialDesignKind.SINGLE_ARM for row in content.trial_designs
    )
    empty_set_proofs = tuple(
        EmptySetProof(
            object_type=object_type,
            reason_code=(EmptySetReasonCode.STUDY_DESIGN_SINGLE_ARM
                         if single_arm_only and object_type is GateObjectType.COMPARISON
                         else EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS),
            evidence_version_id=(stable_id("c-empty-comparison", *(
                row.evidence_version_id for row in trial_design_evidence
            )) if single_arm_only and object_type is GateObjectType.COMPARISON
                else f"c-empty-{object_type.value}-v1"),
            explanation_zh=("当前输入的研究声明为单组设计；不表示已完成竞品发现闭包"
                            if single_arm_only and object_type is GateObjectType.COMPARISON
                            else "登记设计事实按试验级门槛评估，该对象类无适用对象"),
        )
        for object_type, member_ids in (
            (GateObjectType.TRIAL, trial_ids),
            (GateObjectType.COMPARISON, tuple(comparison_ids)),
            (GateObjectType.GROUP, tuple(sorted(group_ids))),
            (GateObjectType.ENDPOINT, tuple(endpoint_ids)),
            (GateObjectType.TIMEPOINT, tuple(timepoint_ids)),
        )
        if not member_ids
    )

    universe_summary = compute_universe_summary(
        project_id=project_id,
        evidence_snapshot_id=evidence_snapshot_id,
        research_role_set_id=_C_RESEARCH_ROLE_SET_ID,
        product_ids=product_ids,
        trial_ids=trial_ids,
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(sorted(group_ids)),
        endpoint_ids=tuple(endpoint_ids),
        timepoint_ids=tuple(timepoint_ids),
        empty_set_proofs=empty_set_proofs,
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id=indication_rule_set_id,
        applicable_conditional_predicates=content.applicable_conditional_predicates,
        root_object_type=(GateObjectType.TRIAL if study_first else GateObjectType.PRODUCT),
    )
    return ApplicableUniverseSnapshot(
        schema_version="1.1" if study_first else "1.0",
        project_id=project_id,
        evidence_snapshot_id=evidence_snapshot_id,
        research_role_set_id=_C_RESEARCH_ROLE_SET_ID,
        product_ids=product_ids,
        trial_ids=trial_ids,
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(sorted(group_ids)),
        endpoint_ids=tuple(endpoint_ids),
        timepoint_ids=tuple(timepoint_ids),
        empty_set_proofs=empty_set_proofs,
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id=indication_rule_set_id,
        applicable_conditional_predicates=content.applicable_conditional_predicates,
        universe_summary=universe_summary,
        enumeration_complete=True,
    )


@dataclass(frozen=True)
class CReportGateOutcome:
    """C 类确定性门槛评估结果：绑定内容摘要、规则指纹与宇宙摘要。"""

    report_kind: ReportKind
    spec_id: str
    spec_version: str
    spec_fingerprint: str
    contract_version: str
    project_id: str
    evidence_snapshot_id: str
    candidate_content_digest: str
    universe_summary: str
    gate_result_key: str
    snapshot: ApplicableUniverseSnapshot
    bindings: tuple[GateEvidenceBinding, ...]
    result: ReportGateResult

    @property
    def review_result(self) -> ReportGateResult:
        """Bind the evaluated units to C's scientific-content review key.

        The engine result identifies the gate universe/bindings; the existing
        C outcome identifies the actual research content. Preserve both old
        identities and derive this request-only projection from those same
        evaluated units, never from a supplied PASS flag.
        """
        return ReportGateResult.from_unit_results(
            report_kind=self.report_kind, unit_results=self.result.unit_results,
            evidence_snapshot_id=self.evidence_snapshot_id,
            candidate_snapshot_digest=self.candidate_content_digest,
            spec_version=self.spec_version, contract_version=self.contract_version,
            universe_summary=self.universe_summary, spec_fingerprint=self.spec_fingerprint,
        )


def evaluate_c_report_gate(
    content: FreshCResearchContent,
    *,
    project_id: str,
    evidence_snapshot_id: str,
    contract_version: str,
    spec: GateSpec | None = None,
    fact_version_by_ref: Mapping[str, str] | None = None,
) -> CReportGateOutcome:
    """用共享证据门槛引擎对 C 类内容做确定性逐单元评估。

    适用性谓词、来源角色与披露成熟度全部由引擎从绑定推导；调用方只能
    提供身份与版本，不能传入门槛结论。报告类型不匹配即失败关闭。
    """
    content = validate_fresh_c_content(content)
    gate_spec = (GateSpec.model_validate(spec.model_dump(mode="json"))
                 if spec is not None else GateSpec.from_yaml(_C_GATE_SPEC_PATH))
    if gate_spec.report_kind is not ReportKind.C:
        raise FreshCPackageError("C 类研究包只能使用 C 类证据门槛规格")
    if (gate_spec.spec_id, gate_spec.version) not in {
        ("gate-spec-c-v1", "1.0"), ("gate-spec-c-v2", "2.0"),
    }:
        raise FreshCPackageError("C 门槛规格标识与支持的规则版本不一致")
    snapshot = build_c_gate_snapshot(
        content,
        project_id=project_id,
        evidence_snapshot_id=evidence_snapshot_id,
        study_first=gate_spec.spec_id == "gate-spec-c-v2",
    )
    bindings = build_c_gate_bindings(
        content, fact_version_by_ref=fact_version_by_ref,
        study_first=gate_spec.spec_id == "gate-spec-c-v2",
        spec=gate_spec,
    )
    result = evaluate_report(
        gate_spec, snapshot, bindings, contract_version=contract_version
    )
    candidate_content_digest = content.content_digest
    return CReportGateOutcome(
        report_kind=gate_spec.report_kind,
        spec_id=gate_spec.spec_id,
        spec_version=gate_spec.version,
        spec_fingerprint=gate_spec.spec_fingerprint,
        contract_version=contract_version,
        project_id=project_id,
        evidence_snapshot_id=evidence_snapshot_id,
        candidate_content_digest=candidate_content_digest,
        universe_summary=snapshot.universe_summary,
        gate_result_key=compute_gate_result_key(
            ReportKind.C,
            evidence_snapshot_id,
            candidate_content_digest,
            gate_spec.version,
            contract_version,
            snapshot.universe_summary,
            spec_fingerprint=gate_spec.spec_fingerprint,
        ),
        snapshot=snapshot,
        bindings=bindings,
        result=result,
    )


# ── C 报告快照投影 ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CReportProjection:
    """C 报告快照投影：锁定报告快照与回绑的 C 类门户数据。"""

    report_snapshot: LockedSnapshot
    claim_snapshot_id: str
    coverage_set_id: str
    gate_result_key: str
    package_digest: str
    portal_data: ReportCPortalData


def project_c_report_snapshot(
    package: FreshCResearchPackage,
    *,
    outcome: CReportGateOutcome,
    project_root: Path,
    project_id: str,
    contract_version: int,
    evidence_snapshot_id: str,
    evidence_snapshot: LockedSnapshot | None = None,
    fact_version_ids: tuple[str, ...] = (),
) -> CReportProjection:
    """在确定性门槛通过且独立复核接受后锁定 C 报告快照。

    - 报告快照绑定证据快照标识（由共享谱系摄取产生）、声明快照、覆盖
      集合与门槛结果键；同一输入重复投影得到同一内容寻址快照身份；
    - 门槛未通过、复核未接受或评估对象与当前包内容摘要不一致时失败
      关闭，不建立任何报告快照；
    - 返回的门户数据回绑锁定快照标识；渲染本身不在本层发生，
      ``rendered_unreviewed`` 快捷路径保持不变。
    """
    if not isinstance(package, FreshCResearchPackage):
        raise FreshCPackageError("C 报告快照投影只接受 C 类新鲜来源研究包")
    if not isinstance(outcome, CReportGateOutcome):
        raise FreshCPackageError("C 报告快照投影只接受 C 类门槛评估结果")
    package = validate_fresh_c_package(package)
    if outcome.report_kind is not ReportKind.C:
        raise FreshCPackageError("报告快照投影的报告类型必须为 C")
    if package.scientific_review.status != "accepted":
        raise FreshCPackageError("独立科学复核未接受，不得锁定报告快照")
    if outcome.candidate_content_digest != package.research_content_digest:
        raise FreshCPackageError("门槛评估对象与当前研究包内容摘要不一致")
    if (outcome.project_id != project_id
            or outcome.contract_version != str(contract_version)
            or outcome.evidence_snapshot_id != evidence_snapshot_id):
        raise FreshCPackageError("门槛评估与当前项目、合同或证据快照身份不一致")
    policy_paths = {("gate-spec-c-v1", "1.0"): "C-v1.yaml",
                    ("gate-spec-c-v2", "2.0"): "C-v2.yaml"}
    policy_name = policy_paths.get((outcome.spec_id, outcome.spec_version))
    if policy_name is None:
        raise FreshCPackageError("门槛评估的规格身份或版本不受支持")
    spec = GateSpec.from_yaml(_C_GATE_SPEC_PATH.parent / policy_name)
    if outcome.spec_fingerprint != spec.spec_fingerprint:
        raise FreshCPackageError("门槛评估与当前规则指纹不一致")
    expected_snapshot = build_c_gate_snapshot(
        package, project_id=project_id, evidence_snapshot_id=evidence_snapshot_id,
        study_first=outcome.spec_id == "gate-spec-c-v2",
    )
    if expected_snapshot.model_dump(mode="json") != outcome.snapshot.model_dump(mode="json"):
        raise FreshCPackageError("门槛候选快照与当前研究包绑定不一致")
    # Version IDs come from immutable ingestion; all scientific binding fields
    # must still exactly project from the current source observations.
    expected_bindings = {binding.binding_id: binding for binding in build_c_gate_bindings(
        package, study_first=outcome.spec_id == "gate-spec-c-v2",
        spec=spec,
    )}
    actual_bindings = {binding.binding_id: binding for binding in outcome.bindings}
    if (len(actual_bindings) != len(outcome.bindings)
            or actual_bindings.keys() != expected_bindings.keys()
            or any(binding.model_dump(mode="json", exclude={"fact_version_id"})
                   != expected_bindings[key].model_dump(mode="json", exclude={"fact_version_id"})
                   for key, binding in actual_bindings.items())):
        raise FreshCPackageError("门槛科学绑定与当前研究观察不一致")
    recomputed_result = evaluate_report(
        spec, outcome.snapshot, outcome.bindings, contract_version=str(contract_version),
    )
    expected_key = compute_gate_result_key(
        ReportKind.C, evidence_snapshot_id, package.research_content_digest,
        spec.version, str(contract_version), expected_snapshot.universe_summary,
        spec_fingerprint=spec.spec_fingerprint,
    )
    if (outcome.universe_summary != expected_snapshot.universe_summary
            or outcome.gate_result_key != expected_key
            or outcome.result.model_dump(mode="json") != recomputed_result.model_dump(mode="json")):
        raise FreshCPackageError("门槛结果、候选或评估键与当前规则绑定不一致")
    if outcome.result.decision is not ReportDecision.PASSED:
        raise FreshCPackageError("确定性证据门槛未通过，不得锁定 C 报告快照")
    if evidence_snapshot is not None:
        try:
            evidence_payload = SnapshotStore(project_root).read(evidence_snapshot)
            evidence_manifest = EvidenceSnapshotManifest.model_validate(evidence_payload)
            recomputed = compute_locked_snapshot(
                kind="evidence", report=None, manifest=evidence_payload
            )
        except (OSError, ValueError, SnapshotIntegrityError) as error:
            raise FreshCPackageError("C 类证据快照不存在或不可信") from error
        if (
            recomputed.snapshot_id != evidence_snapshot_id
            or evidence_manifest.project_id != project_id
            or evidence_manifest.data_cutoff != package.data_cutoff
            or evidence_manifest.scientific_content_digest
            != package.research_content_digest
        ):
            raise FreshCPackageError("C 类证据快照与当前研究内容不一致")
    if fact_version_ids and not set(
        fact_version_id
        for result in outcome.result.unit_results
        for fact_version_id in result.fact_version_ids
    ) <= set(fact_version_ids):
        raise FreshCPackageError("C 类门槛引用了证据快照之外的事实版本")

    claim_ids = package.claim_ids
    claim_snapshot_id = stable_id(
        "claim-snapshot", project_id, package.research_content_digest, *claim_ids
    )
    coverage_set_id = stable_id(
        "coverage-set", project_id, "C", evidence_snapshot_id, claim_snapshot_id
    )
    manifest = ReportSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        report="C",
        report_version=package.report_version,
        data_cutoff=package.data_cutoff,
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        claim_ids=claim_ids,
        # 快照固定于独立复核接受时刻：同一包重复投影身份不变（内容寻址幂等）。
        created_at=package.scientific_review.reviewed_at,
    )
    locked = SnapshotStore(project_root).lock_report_snapshot(
        report="C", manifest=manifest.model_dump(mode="json")
    )
    return CReportProjection(
        report_snapshot=locked,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        gate_result_key=outcome.gate_result_key,
        package_digest=package.research_content_digest,
        portal_data=package.report_data.model_copy(
            update={
                "report_snapshot_id": locked.snapshot_id,
                # 独立复核 C r19：包内设计路径综合随门户数据下发
                "design_paths": package.design_paths.model_dump(mode="json"),
            }
        ),
    )


def load_fresh_c_research_package(path: Path) -> FreshCResearchPackage:
    """读取并校验 C 类新鲜来源研究包；文件或合同失败均失败关闭。"""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FreshCPackageError("无法读取 C 类新鲜来源研究包") from error
    return validate_fresh_c_package(value)


__all__ = [
    "CReportGateOutcome",
    "CReportProjection",
    "CTrialDesign",
    "FreshCPackageError",
    "FreshCResearchContent",
    "FreshCResearchPackage",
    "build_c_gate_bindings",
    "build_c_gate_snapshot",
    "evaluate_c_report_gate",
    "derive_c_research_facts",
    "load_fresh_c_research_package",
    "project_c_report_snapshot",
    "validate_fresh_c_content",
    "validate_fresh_c_package",
]
