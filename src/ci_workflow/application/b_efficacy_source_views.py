"""B 疗效来源视图：把 A 已核验的直接疗效原子投影为只读来源视图。

只读边界：本模块只读取锁定证据闭包、项目合同与项目数据库，不创建事实、
消费者、当前交付、报告快照，也不把 n/N 派生为比例。缺失的估计目标、方向、
量纲或分析集语义保持未知；现有 B 视图字段只由报告行身份与来源事实直接填充，
A/B 正式名称与科学标识保持不变。
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import ResearchFact, ResearchResultContext
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.source_clause_context import SourceClauseContext, SourceClauseReference
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.renderers.portal.report_a import (
    EfficacyRow,
    ReportAPortalData,
    active_fact_binding_for_a,
)
from ci_workflow.reports.common.evidence_view import (
    clean_evidence_locator,
    precise_locator_anchor,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.source_derivation import extract_locator_quote, source_json_decoder

# 只有直接报告值或登记人数是本文来源视图可证明的原子角色；派生率、离散度
# 或分析集语义必须由独立规则证明，不得在此处被推断为估计目标。
_DIRECT_EFFICACY_ROLES = frozenset({"reported_measure", "participant_count"})
_COUNT_UNIT_EXCLUSIONS = frozenset({"%", "％"})

# 分母作用范围只按登记披露的 denoms 层级命名，不译成 ITT/全分析集等来源未
# 证明的分析集含义；无法由精确路径证明时保持待核。
_SCOPE_MEASURE_ZH = "测量级分析人数"
_SCOPE_CLASS_ZH = "该访视或类别分析人数"
_SCOPE_CATEGORY_ZH = "该子类别分析人数"
_SCOPE_UNRESOLVED_ZH = "分母范围待核"


def denominator_scope_disclosure(
    observation: ResearchResultContext, value_path: str | None,
) -> tuple[str, int | None, str | None]:
    """Return the original-source N with only the scope its exact path proves.

    The scope comes from the single verified ``result_context`` denominator
    candidate of this fact's own group and its precise ``denoms`` path relative
    to the measure path, checked against the fact's exact value path. A visit,
    class or category title never proves a scope, and a measure N is not called
    ITT; missing, duplicated, conflicting, foreign or non-covering candidates
    keep 分母范围待核 without inventing an N.
    """
    candidates = tuple(
        candidate
        for candidate in observation.denominator_candidates
        if candidate.group_id == observation.group_id
    )
    if len(candidates) != 1:
        return (_SCOPE_UNRESOLVED_ZH, None, None)
    candidate = candidates[0]
    measure = observation.source_measure_path
    path = candidate.value_path
    if (
        not measure
        or not isinstance(value_path, str)
        or not value_path
        or ".denoms[" not in path
        or not path.startswith(f"{measure}.")
    ):
        return (_SCOPE_UNRESOLVED_ZH, None, None)
    scope_path = path.rsplit(".denoms[", 1)[0]
    if (
        value_path != f"$.{scope_path}"
        and not value_path.startswith(f"$.{scope_path}.")
    ):
        return (_SCOPE_UNRESOLVED_ZH, None, None)
    suffix = path[len(measure) + 1:]
    segment = suffix.split(".", 1)[0]
    if segment.startswith("denoms["):
        return (_SCOPE_MEASURE_ZH, candidate.parsed_value, f"$.{path}")
    if segment.startswith("classes["):
        nested = suffix[len(segment) + 1:].split(".", 1)[0]
        if nested.startswith("categories["):
            return (_SCOPE_CATEGORY_ZH, candidate.parsed_value, f"$.{path}")
        return (_SCOPE_CLASS_ZH, candidate.parsed_value, f"$.{path}")
    if segment.startswith("categories["):
        return (_SCOPE_CATEGORY_ZH, candidate.parsed_value, f"$.{path}")
    return (_SCOPE_UNRESOLVED_ZH, None, None)


class BEfficacySourceViewError(ValueError):
    """B 疗效来源视图没有被锁定的 A 已核验原子证明。"""


def _canonical_label(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).casefold()
    return normalized or None


def _group_label_matches(
    row_arm: str, row_arm_detail: str | None, source_title: str,
) -> bool:
    """Row arm labels must explicitly name the source group; no fuzzy equivalence."""
    source_label = _canonical_label(source_title)
    if source_label is None:
        return False
    return any(
        _canonical_label(value) == source_label for value in (row_arm, row_arm_detail)
    )


def _denominator_relation_ok(
    observation: ResearchResultContext, row: EfficacyRow, numeric: float,
) -> bool:
    denominators = {
        candidate.parsed_value
        for candidate in observation.denominator_candidates
        if candidate.group_id == row.group_id
    }
    if len(denominators) > 1:
        return False
    if observation.value_role == "participant_count":
        return (
            math.isfinite(numeric)
            and numeric.is_integer()
            and numeric >= 0
            and row.unit not in _COUNT_UNIT_EXCLUSIONS
            and row.numerator == int(numeric)
            and len(denominators) == 1
            and row.denominator in denominators
        )
    # reported_measure: numerator stays unknown unless the source reports one,
    # while an explicit source N is retained only when it is that group's N.
    return (
        row.numerator is None
        and (not denominators or row.denominator in denominators)
        and (bool(denominators) or row.denominator is None)
    )


def _measure_context(
    capture: Mapping[str, Any], observation: ResearchResultContext, source_version_id: str,
) -> tuple[str, SourceClauseContext | None]:
    """Read complete source clauses, not model-normalized scientific equivalents."""
    path = observation.source_measure_path
    if not path:
        return "", None
    try:
        measure = source_json_decoder().decode(extract_locator_quote(
            capture["content_text"], media_type=capture["media_type"],
            locator=EvidenceLocator(document_role="clinical_trial_registry",
                field_path=f"$.{path}", url=capture["url"]),
        ))
        if not isinstance(measure, dict):
            raise ValueError("测量上下文不是对象")
        references = []
        for field, label in (
            ("description", "结局完整定义"), ("populationDescription", "原分析人群"),
            ("analysisPopulationDescription", "原分析人群补充"),
            ("paramType", "原统计形式"), ("timeFrame", "原访视或区间"),
        ):
            text = measure.get(field)
            if text is None or text == "":
                continue
            if not isinstance(text, str):
                raise ValueError("测量语境字段不是来源文本")
            references.append(SourceClauseReference(
                reference_id=stable_id("source-context", source_version_id, path, field),
                source_id=capture["source_id"], label_zh=label,
                locator=EvidenceLocator(document_role="clinical_trial_registry",
                    field_path=f"$.{path}.{field}", url=capture["url"]),
                original_text=text,
            ))
        return measure.get("description") or "", SourceClauseContext(
            label_zh="登记结局语境",
            scope_note_zh="完整原文保留，不代表量表、分析集或估计目标已经等价。",
            scientific_scope={"source_version_id": source_version_id,
                              "source_measure_path": path},
            continuations=tuple(references),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BEfficacySourceViewError("锁定测量语境不能从精确路径重提取") from error


def project_b_efficacy_source_views(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    report: ReportAPortalData,
    row_versions: Mapping[str, str],
) -> tuple[dict[str, Any], ...]:
    """Read-only exact efficacy source views; this does not accept evidence.

    Every admitted ``efficacy:<row_id>`` reference must resolve to the locked
    closure fact, the persisted fact/fragment/source rows and the append-only A
    consumer registration with the same scientific identity. Unknown or
    duplicated references, wrong domain/version/locator/value/group or an
    unproven A consumer are rejected instead of first-wins.
    """
    project_root = Path(project_root)
    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise BEfficacySourceViewError("B 疗效来源视图只能引用证据快照")
    if not row_versions or len(set(row_versions.values())) != len(row_versions):
        raise BEfficacySourceViewError("B 疗效来源视图缺少唯一的来源数值原子")
    snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    contract = verify_project_workspace(project_root).contract
    if (
        snapshot["project_id"] != contract.project_id
        or snapshot["contract_version"] != contract.contract_version
        or report.indication != contract.indication
        or report.data_cutoff != datetime.fromisoformat(snapshot["data_cutoff"])
    ):
        raise BEfficacySourceViewError("B 疗效来源视图、快照与项目合同不一致")
    closure = snapshot.get("closure")
    if not isinstance(closure, dict):
        raise BEfficacySourceViewError("B 疗效来源视图必须引用带原始闭包的证据快照")
    facts = {item["fact_version_id"]: item for item in closure["facts"]}
    fragments = {item["fragment_id"]: item for item in closure["fragments"]}
    sources = {item["source_version_id"]: item for item in closure["sources"]}
    source_versions = {
        item["capture"]["source_id"]: item["source_version_id"] for item in closure["sources"]
    }
    if (
        len(facts) != len(closure["facts"])
        or len(fragments) != len(closure["fragments"])
        or len(sources) != len(closure["sources"])
    ):
        raise BEfficacySourceViewError("B 疗效来源闭包存在重复版本标识")
    rows = {row.row_id: row for row in report.efficacy}
    if len(rows) != len(report.efficacy):
        raise BEfficacySourceViewError("A 疗效行标识不唯一")
    for row_ref in row_versions:
        collection, separator, row_id = row_ref.partition(":")
        if separator != ":" or collection != "efficacy" or row_id not in rows:
            raise BEfficacySourceViewError("B 疗效来源视图只接受已有疗效数值行")
    if not set(row_versions.values()) <= set(snapshot["fact_version_ids"]):
        raise BEfficacySourceViewError("B 疗效来源事实版本不在锁定快照")

    result_views: list[dict[str, Any]] = []
    measure_contexts: dict[tuple[str, str | None], tuple[str, SourceClauseContext | None]] = {}
    database_path = project_root / "state/project.sqlite"
    try:
        with sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True) as database:
            for row in report.efficacy:
                version_id = row_versions.get(f"efficacy:{row.row_id}")
                if version_id is None:
                    continue
                if (
                    row.trial_id is None
                    or row.group_assignment_state != "declared"
                    or not row.group_id
                ):
                    raise BEfficacySourceViewError("疗效来源行缺少研究或明确的组别关系")
                item = facts.get(version_id)
                if item is None:
                    raise BEfficacySourceViewError("疗效来源数值原子缺失")
                try:
                    fact = ResearchFact.model_validate(
                        {**item["fact"], "row_ref": item["consumer_binding"]["row_ref"]}
                    )
                except (KeyError, TypeError, ValueError) as error:
                    raise BEfficacySourceViewError("锁定来源事实不是可核验的疗效原子") from error
                if fact.row_ref != f"efficacy:{row.row_id}":
                    raise BEfficacySourceViewError("锁定来源事实的消费者行引用与当前报告行不一致")
                source = database.execute(
                    "SELECT v.raw_value,v.scientific_context_json,v.primary_fragment_id,"
                    "f.source_version_id,f.locator,f.content_text FROM fact_versions v "
                    "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                    "WHERE v.fact_version_id=?",
                    (version_id,),
                ).fetchone()
                if source is None:
                    raise BEfficacySourceViewError("疗效来源数值原子缺失")
                raw_value, context_json, fragment_id, source_id, locator_json, quote = source
                fragment = fragments.get(fragment_id)
                captured = sources.get(source_id)
                if fragment is None or captured is None:
                    raise BEfficacySourceViewError("疗效来源原子缺少锁定的片段或来源版本")
                try:
                    context = json.loads(str(context_json))
                    locator = json.loads(str(locator_json))
                    numeric = float(str(raw_value))
                    observation = fact.result_context
                    if observation is None:
                        raise ValueError("来源原子缺少结果语境")
                    capture_url = captured["capture"]["url"]
                except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
                    raise BEfficacySourceViewError("来源数值或科学语境不可核验") from error
                exact_locator = clean_evidence_locator(locator)
                if exact_locator is None or precise_locator_anchor(exact_locator) is None:
                    raise BEfficacySourceViewError("疗效来源原子缺少精确非本机定位")
                checks = {
                    "snapshot_fact": (
                        item["primary_fragment_id"] == fragment_id
                        and item["scientific_context_json"] == context_json
                        and context.get("result_context") == item["fact"].get("result_context")
                    ),
                    "snapshot_fragment": (
                        fragment["source_version_id"] == source_id
                        and fragment["locator"] == locator
                        and fragment["original_text"] == quote
                    ),
                    "research_fact": (
                        fact.locator.model_dump(mode="json") == locator
                        and fact.original_text == quote
                        and fact.raw_value == raw_value
                    ),
                    "source_identity": (
                        row.source_version_id == source_id
                        and source_versions.get(fact.source_id) == source_id
                        and locator.get("url") == capture_url
                    ),
                    "source_pointer": (
                        context["locator"] == locator
                        and row.source_field_path == locator.get("field_path")
                    ),
                    "source_value": (
                        context["raw_value"] == raw_value
                        and row.source_text == quote
                        and row.value is not None
                        and math.isfinite(numeric)
                        and math.isclose(row.value, numeric, rel_tol=0, abs_tol=1e-9)
                    ),
                    "efficacy_domain": (
                        observation.domain == "efficacy"
                        and observation.category == "outcome"
                        and observation.value_role != "denominator"
                    ),
                    "trial_and_group": (
                        str(observation.trial_id).casefold() == row.trial_id.casefold()
                        and observation.group_id == row.group_id
                        and _group_label_matches(
                            row.arm, row.arm_detail, observation.group_title
                        )
                    ),
                    "direct_role": observation.value_role in _DIRECT_EFFICACY_ROLES,
                    "denominators": _denominator_relation_ok(observation, row, numeric),
                }
                invalid = [scope for scope, valid in checks.items() if not valid]
                if invalid:
                    raise BEfficacySourceViewError(
                        f"疗效结果 {row.row_id} 与锁定来源不一致：{','.join(invalid)}"
                    )
                _verified_a_consumer_proof(
                    database, evidence_snapshot, report, row, version_id,
                )
                scope_zh, source_n, source_n_path = denominator_scope_disclosure(
                    observation, row.source_field_path,
                )
                measure_key = (source_id, observation.source_measure_path)
                if measure_key not in measure_contexts:
                    measure_contexts[measure_key] = _measure_context(
                        captured["capture"], observation, source_id,
                    )
                definition, clause_context = measure_contexts[measure_key]
                result_views.append(
                    {
                        **row.model_dump(mode="json"),
                        "arm_id": row.group_id,
                        "arm_label": row.arm,
                        "original_definition": row.endpoint,
                        "analysis_population": row.population,
                        "source_locator": exact_locator.model_dump(mode="json"),
                        "source_text": quote,
                        "source_endpoint": observation.endpoint,
                        "source_measure_path": observation.source_measure_path,
                        "source_measure_definition": definition,
                        "source_clause_context": (
                            clause_context.model_dump(mode="json") if clause_context else None
                        ),
                        "source_timepoint": observation.timepoint,
                        "source_observation_timepoint": observation.observation_timepoint,
                        "source_param_type": observation.source_param_type,
                        "source_dispersion_type": observation.source_dispersion_type,
                        "source_class_title": observation.class_title,
                        "source_category_title": observation.category_title,
                        "source_analysis_population": observation.analysis_population,
                        "source_group_id": observation.group_id,
                        "source_group_title": observation.group_title,
                        "source_value_role": observation.value_role,
                        "source_unit": observation.source_unit,
                        "source_raw_value": raw_value,
                        "source_denominator_scope_zh": scope_zh,
                        "source_denominator_value": source_n,
                        "source_denominator_path": source_n_path,
                    }
                )
    except sqlite3.Error as error:
        raise BEfficacySourceViewError("只读来源库不可用") from error
    if len(result_views) != len(row_versions):
        raise BEfficacySourceViewError("B 疗效来源视图未覆盖指定的全部数值行")
    return tuple(result_views)


def _verified_a_consumer_proof(
    database: sqlite3.Connection,
    evidence_snapshot: LockedSnapshot,
    report: ReportAPortalData,
    row: EfficacyRow,
    version_id: str,
) -> None:
    """Fail closed unless the append-only A registration proves this exact atom.

    Only the A consumer registered under this exact evidence snapshot counts;
    the same fact may carry its own identity under another immutable snapshot
    and must never be selected arbitrarily across history.
    """
    declared = database.execute(
        "SELECT collection,row_id,binding_json,binding_sha256,evidence_snapshot_id FROM "
        "source_portal_consumer_bindings WHERE source_fact_version_id=? AND report='A' "
        "AND evidence_snapshot_id=?",
        (version_id, evidence_snapshot.snapshot_id),
    ).fetchall()
    if len(declared) != 1:
        raise BEfficacySourceViewError("疗效来源行缺少唯一已核验 A 来源身份")
    collection, bound_row_id, binding_json, binding_sha256, snapshot_id = declared[0]
    if collection != "efficacy" or bound_row_id != row.row_id:
        raise BEfficacySourceViewError("已核验 A 来源身份与当前候选疗效行不一致")
    if hashlib.sha256(str(binding_json).encode()).hexdigest() != binding_sha256:
        raise BEfficacySourceViewError("A 来源消费者登记摘要不一致")
    if snapshot_id != evidence_snapshot.snapshot_id:
        raise BEfficacySourceViewError("A 来源消费者引用不同证据快照")
    try:
        stored = ActiveFactBinding.model_validate_json(str(binding_json))
    except ValueError as error:
        raise BEfficacySourceViewError("A 来源消费者登记无法核验") from error
    if stored != active_fact_binding_for_a(report, "efficacy", row.row_id):
        raise BEfficacySourceViewError("A 来源消费者科学身份与当前报告行不一致")
