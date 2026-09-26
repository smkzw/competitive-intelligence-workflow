"""C 类协议设计来源原子的精确提取切片。

从一个既有单研究 ``SourceCapture`` 提取资格全文、关键试验设计、明确组别/干预、
主要/次要终点定义与时间窗的 ``ResearchFact`` 来源原子。每条原子绑定精确 JSON
路径并保存原始标量引文，可从固定原始研究逐字段重提取。本层是坦率的来源输入
层：不推断产品或组别—产品关系，不是已接受的 ``DesignObservation``；到设计观察
的映射还需要产品与组别身份的下游决策。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ci_workflow.application.source_research_service import (
    ResearchFact,
    ResearchPackageError,
    SourceCapture,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    source_json_decoder,
)

_PROTOCOL = "$.protocolSection"
_FACT_KIND = "ctgov-protocol-design-fact"


@dataclass(frozen=True)
class CtgovProtocolDesignAtoms:
    """一个登记研究的协议设计来源原子及显式缺失路径清单。"""

    trial_id: str
    source_id: str
    facts: tuple[ResearchFact, ...]
    absent_paths: tuple[str, ...]


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResearchPackageError(f"{path} 必须是对象")
    return value


def _sequence(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ResearchPackageError(f"{path} 必须是列表")
    return value


def _scalar_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchPackageError(f"{path} 缺少非空文本标量")
    return value


def extract_ctgov_protocol_design_atoms(source: SourceCapture) -> CtgovProtocolDesignAtoms:
    """从一条登记研究采集合同提取可回溯的协议设计来源原子。

    关键结构（研究身份、资格全文、终点定义与时间窗、组别标签、干预名称）缺失
    或损坏时整体失败；可选标量缺失时记录精确路径而不补零。组别只保留登记原文
    标签，干预—组别关系仅按来源自身的标签引用核对，不推断任何产品等式。
    """
    if source.source_type != "clinical_trial_registry" or source.media_type != "application/json":
        raise ResearchPackageError("协议设计原子提取需要 JSON 登记来源")
    try:
        record = source_json_decoder().decode(source.content_text)
        if not isinstance(record, dict):
            raise TypeError("登记来源不是对象")
        protocol = record["protocolSection"]
        if not isinstance(protocol, dict):
            raise TypeError("协议模块不是对象")
        trial_id = str(protocol["identificationModule"]["nctId"]).strip()
        if not trial_id or trial_id.casefold() != source.query_or_identifier.casefold():
            raise ValueError("来源试验身份不一致")
    except (KeyError, TypeError, ValueError) as error:
        raise ResearchPackageError("登记来源不能证明试验身份") from error

    facts: list[ResearchFact] = []
    absent: list[str] = []

    def emit(family: str, field_id: str, path: str, value: object) -> None:
        locator = EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path=path,
            url=source.url,
        )
        quote = extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=locator
        )
        expected = (
            value
            if isinstance(value, str)
            else json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
        )
        if quote != expected:
            raise ResearchPackageError(f"{path} 的原文引文与解析标量不一致")
        facts.append(
            ResearchFact(
                fact_id=stable_id(_FACT_KIND, source.source_id, path),
                row_ref=f"registry:{trial_id.casefold()}:protocol-design:{family}",
                entity_id=stable_id("clinical-trial", trial_id),
                entity_type="clinical_trial",
                canonical_name=trial_id,
                field_id=field_id,
                raw_value=quote,
                normalized_value=None,
                disclosure_state="reported_value",
                source_id=source.source_id,
                locator=locator,
                original_text=quote,
            )
        )

    def mark_absent(path: str) -> None:
        absent.append(path)

    def optional_text(
        container: dict[str, Any],
        key: str,
        base: str,
        family: str,
        field_id: str,
    ) -> None:
        if container.get(key) is None:
            mark_absent(f"{base}.{key}")
        else:
            emit(family, field_id, f"{base}.{key}", _scalar_text(container[key], f"{base}.{key}"))

    eligibility_path = f"{_PROTOCOL}.eligibilityModule"
    if "eligibilityModule" not in protocol:
        raise ResearchPackageError("C 协议设计切片缺少登记资格模块；不得静默跳过")
    eligibility = _mapping(protocol["eligibilityModule"], eligibility_path)
    criteria_path = f"{eligibility_path}.eligibilityCriteria"
    if eligibility.get("eligibilityCriteria") is None:
        raise ResearchPackageError(f"{criteria_path} 缺少完整资格标准全文")
    emit(
        "eligibility",
        "ctgov.protocol.eligibility.criteria",
        criteria_path,
        _scalar_text(eligibility["eligibilityCriteria"], criteria_path),
    )
    optional_text(
        eligibility, "sex", eligibility_path, "eligibility", "ctgov.protocol.eligibility.sex"
    )
    optional_text(
        eligibility,
        "minimumAge",
        eligibility_path,
        "eligibility",
        "ctgov.protocol.eligibility.minimum_age",
    )
    optional_text(
        eligibility,
        "maximumAge",
        eligibility_path,
        "eligibility",
        "ctgov.protocol.eligibility.maximum_age",
    )
    healthy_path = f"{eligibility_path}.healthyVolunteers"
    healthy = eligibility.get("healthyVolunteers")
    if healthy is None:
        mark_absent(healthy_path)
    elif isinstance(healthy, bool):
        emit("eligibility", "ctgov.protocol.eligibility.healthy_volunteers", healthy_path, healthy)
    else:
        raise ResearchPackageError(f"{healthy_path} 必须是布尔值")
    std_ages_path = f"{eligibility_path}.stdAges"
    if eligibility.get("stdAges") is None:
        mark_absent(std_ages_path)
    else:
        std_ages = _sequence(eligibility["stdAges"], std_ages_path)
        emit(
            "eligibility",
            "ctgov.protocol.eligibility.std_ages",
            std_ages_path,
            [_scalar_text(age, std_ages_path) for age in std_ages],
        )

    design_path = f"{_PROTOCOL}.designModule"
    design = protocol.get("designModule")
    if design is None:
        mark_absent(design_path)
    else:
        design = _mapping(design, design_path)
        optional_text(
            design,
            "studyType",
            design_path,
            "trial-design",
            "ctgov.protocol.design.study_type",
        )
        phases_path = f"{design_path}.phases"
        if design.get("phases") is None:
            mark_absent(phases_path)
        else:
            for index, phase in enumerate(_sequence(design["phases"], phases_path)):
                phase_path = f"{phases_path}[{index}]"
                emit(
                    "trial-design",
                    "ctgov.protocol.design.phase",
                    phase_path,
                    _scalar_text(phase, phase_path),
                )
        info_path = f"{design_path}.designInfo"
        info = design.get("designInfo")
        if info is None:
            mark_absent(info_path)
        else:
            info = _mapping(info, info_path)
            for key, field_id in (
                ("allocation", "ctgov.protocol.design.allocation"),
                ("interventionModel", "ctgov.protocol.design.intervention_model"),
                (
                    "interventionModelDescription",
                    "ctgov.protocol.design.intervention_model_description",
                ),
                ("primaryPurpose", "ctgov.protocol.design.primary_purpose"),
            ):
                optional_text(info, key, info_path, "trial-design", field_id)
            masking_path = f"{info_path}.maskingInfo"
            masking = info.get("maskingInfo")
            if masking is None:
                mark_absent(f"{masking_path}.masking")
            else:
                optional_text(
                    _mapping(masking, masking_path),
                    "masking",
                    masking_path,
                    "trial-design",
                    "ctgov.protocol.design.masking",
                )
        enrollment_path = f"{design_path}.enrollmentInfo"
        enrollment = design.get("enrollmentInfo")
        if enrollment is None:
            mark_absent(f"{enrollment_path}.count")
            mark_absent(f"{enrollment_path}.type")
        else:
            enrollment = _mapping(enrollment, enrollment_path)
            count_path = f"{enrollment_path}.count"
            count = enrollment.get("count")
            if count is None:
                mark_absent(count_path)
            elif isinstance(count, bool) or not isinstance(count, int):
                raise ResearchPackageError(f"{count_path} 必须是整数")
            else:
                emit("trial-design", "ctgov.protocol.design.enrollment_count", count_path, count)
            optional_text(
                enrollment,
                "type",
                enrollment_path,
                "trial-design",
                "ctgov.protocol.design.enrollment_type",
            )

    arms_path = f"{_PROTOCOL}.armsInterventionsModule"
    arms_module = protocol.get("armsInterventionsModule")
    arm_labels: set[str] = set()
    if arms_module is None:
        mark_absent(f"{arms_path}.armGroups")
        mark_absent(f"{arms_path}.interventions")
    else:
        arms_module = _mapping(arms_module, arms_path)
        arm_groups_path = f"{arms_path}.armGroups"
        if arms_module.get("armGroups") is None:
            mark_absent(arm_groups_path)
        else:
            for index, raw_group in enumerate(_sequence(arms_module["armGroups"], arm_groups_path)):
                group_path = f"{arm_groups_path}[{index}]"
                group = _mapping(raw_group, group_path)
                label = _scalar_text(group.get("label"), f"{group_path}.label")
                if label in arm_labels:
                    raise ResearchPackageError(f"{group_path}.label 与既有组别标签重复：{label}")
                arm_labels.add(label)
                emit("arms", "ctgov.protocol.arm.label", f"{group_path}.label", label)
                optional_text(group, "type", group_path, "arms", "ctgov.protocol.arm.type")
                optional_text(
                    group, "description", group_path, "arms", "ctgov.protocol.arm.description"
                )
                names_path = f"{group_path}.interventionNames"
                if group.get("interventionNames") is None:
                    mark_absent(names_path)
                else:
                    for name_index, name in enumerate(
                        _sequence(group["interventionNames"], names_path)
                    ):
                        name_path = f"{names_path}[{name_index}]"
                        emit(
                            "arms",
                            "ctgov.protocol.arm.intervention_name",
                            name_path,
                            _scalar_text(name, name_path),
                        )
        interventions_path = f"{arms_path}.interventions"
        if arms_module.get("interventions") is None:
            mark_absent(interventions_path)
        else:
            for index, raw_item in enumerate(
                _sequence(arms_module["interventions"], interventions_path)
            ):
                base = f"{interventions_path}[{index}]"
                intervention = _mapping(raw_item, base)
                optional_text(
                    intervention,
                    "type",
                    base,
                    "interventions",
                    "ctgov.protocol.intervention.type",
                )
                optional_text(
                    intervention,
                    "name",
                    base,
                    "interventions",
                    "ctgov.protocol.intervention.name",
                )
                optional_text(
                    intervention,
                    "description",
                    base,
                    "interventions",
                    "ctgov.protocol.intervention.description",
                )
                other_names_path = f"{base}.otherNames"
                if intervention.get("otherNames") is None:
                    mark_absent(other_names_path)
                else:
                    for name_index, name in enumerate(
                        _sequence(intervention["otherNames"], other_names_path)
                    ):
                        name_path = f"{other_names_path}[{name_index}]"
                        emit(
                            "interventions",
                            "ctgov.protocol.intervention.other_name",
                            name_path,
                            _scalar_text(name, name_path),
                        )
                labels_path = f"{base}.armGroupLabels"
                if intervention.get("armGroupLabels") is None:
                    mark_absent(labels_path)
                else:
                    for label_index, raw_label in enumerate(
                        _sequence(intervention["armGroupLabels"], labels_path)
                    ):
                        label_path = f"{labels_path}[{label_index}]"
                        label = _scalar_text(raw_label, label_path)
                        if label not in arm_labels:
                            raise ResearchPackageError(
                                f"{label_path} 引用了登记组别中不存在的标签：{label}"
                            )
                        emit(
                            "interventions",
                            "ctgov.protocol.intervention.arm_group_label",
                            label_path,
                            label,
                        )

    outcomes_path = f"{_PROTOCOL}.outcomesModule"
    outcomes = protocol.get("outcomesModule")
    if outcomes is None:
        mark_absent(f"{outcomes_path}.primaryOutcomes")
        mark_absent(f"{outcomes_path}.secondaryOutcomes")
    else:
        outcomes = _mapping(outcomes, outcomes_path)
        for role, key in (
            ("primary", "primaryOutcomes"),
            ("secondary", "secondaryOutcomes"),
        ):
            list_path = f"{outcomes_path}.{key}"
            if outcomes.get(key) is None:
                mark_absent(list_path)
                continue
            items = _sequence(outcomes[key], list_path)
            if not items:
                mark_absent(list_path)
                continue
            for index, raw_outcome in enumerate(items):
                base = f"{list_path}[{index}]"
                outcome = _mapping(raw_outcome, base)
                for key_name, field_id in (
                    ("measure", f"ctgov.protocol.{role}_outcome.measure"),
                    ("timeFrame", f"ctgov.protocol.{role}_outcome.time_frame"),
                ):
                    scalar_path = f"{base}.{key_name}"
                    if outcome.get(key_name) is None:
                        raise ResearchPackageError(f"{scalar_path} 缺少终点定义或时间窗")
                    emit(
                        f"{role}-endpoints",
                        field_id,
                        scalar_path,
                        _scalar_text(outcome[key_name], scalar_path),
                    )
                optional_text(
                    outcome,
                    "description",
                    base,
                    f"{role}-endpoints",
                    f"ctgov.protocol.{role}_outcome.description",
                )

    return CtgovProtocolDesignAtoms(
        trial_id=trial_id,
        source_id=source.source_id,
        facts=tuple(facts),
        absent_paths=tuple(absent),
    )


__all__ = ["CtgovProtocolDesignAtoms", "extract_ctgov_protocol_design_atoms"]
