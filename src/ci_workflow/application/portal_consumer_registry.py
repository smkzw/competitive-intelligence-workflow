"""Append-only bridge from verified source atoms to portal row consumers.

Registration is a development/candidate action. It does not accept evidence,
publish a report, or change the source fact's scientific content/version.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    ResearchFact,
    ctgov_direct_safety_measure_identity,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
    canonical_sha256,
    canonical_source_pointer,
)
from ci_workflow.renderers.portal.report_a import (
    EfficacyRow,
    ReportAPortalData,
    SafetyRow,
    active_fact_binding_for_a,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    _b_source_view_row,
    active_fact_binding_for_b,
)
from ci_workflow.reports.b.safety_concepts import (
    describe_measured_safety_concept,
    safety_category_zh,
)
from ci_workflow.reports.b.source_baseline import build_source_baseline_view
from ci_workflow.reports.common.evidence_view import (
    clean_evidence_locator,
    precise_locator_anchor,
)
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.sqlite import open_database


class PortalConsumerRegistrationError(ValueError):
    """A proposed portal consumer is not proven by the locked source fact."""


@dataclass(frozen=True)
class SourceRowContext:
    """Original labels from a previously audited exact row-source sidecar."""

    endpoint: str
    timepoint: str
    group_title: str
    value_path: str


def register_b_baseline_source_consumers(
    project_root: Path, evidence_snapshot: LockedSnapshot, report: ReportBPortalData,
    row_versions: Mapping[str, str], *, registered_at: datetime,
) -> tuple[ActiveFactBinding, ...]:
    """Attach study-only scalar baseline consumers without guessing a product.

    Rebuild expected view rows from the locked ResearchFacts, then prove both
    that complete row and the persisted original fragment. No new scientific
    version, source alteration, current promotion, or rate derivation occurs.
    Count/N editing is not admitted by this scalar bridge.
    """
    if registered_at.tzinfo is None or registered_at.utcoffset() is None:
        raise PortalConsumerRegistrationError("基线消费者登记时间缺少时区")
    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise PortalConsumerRegistrationError("基线消费者只能引用证据快照")
    if not row_versions or len(set(row_versions.values())) != len(row_versions):
        raise PortalConsumerRegistrationError("基线消费者缺少唯一明确来源原子")
    snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    contract = verify_project_workspace(project_root).contract
    if (snapshot["project_id"] != contract.project_id
            or snapshot["contract_version"] != contract.contract_version
            or report.indication != contract.indication
            or report.data_cutoff != datetime.fromisoformat(snapshot["data_cutoff"])):
        raise PortalConsumerRegistrationError("基线报告、来源快照与项目合同不一致")
    closure = snapshot.get("closure")
    if not isinstance(closure, dict):
        raise PortalConsumerRegistrationError("基线来源缺少完整闭包")
    facts = {item["fact_version_id"]: item for item in closure["facts"]}
    fragments = {item["fragment_id"]: item for item in closure["fragments"]}
    source_versions = {item["capture"]["source_id"]: item["source_version_id"]
                       for item in closure["sources"]}
    if (len(facts) != len(closure["facts"]) or len(fragments) != len(closure["fragments"])
            or len(source_versions) != len(closure["sources"])):
        raise PortalConsumerRegistrationError("基线闭包存在重复身份")
    source_facts: list[ResearchFact] = []
    versions_by_fact: dict[str, str] = {}
    for row_id, version_id in row_versions.items():
        item = facts.get(version_id)
        if item is None or version_id not in snapshot["fact_version_ids"]:
            raise PortalConsumerRegistrationError("基线事实版本不在本次来源闭包")
        # Row references live in the separate consumer declaration, not in the
        # scientific content hash. Reconstruct only that explicit source ref.
        fact = ResearchFact.model_validate({**item["fact"],
            "row_ref": item["consumer_binding"]["row_ref"]})
        if (fact.fact_id != row_id or fact.result_context is None
                or fact.result_context.category != "baseline"):
            raise PortalConsumerRegistrationError("基线行与原始来源事实身份不一致")
        source_facts.append(fact)
        versions_by_fact[fact.fact_id] = version_id
    expected = {row["row_id"]: row for row in build_source_baseline_view(
        source_facts, source_versions=source_versions, fact_versions=versions_by_fact,
    )["facts"]}
    candidates: list[tuple[str, ActiveFactBinding]] = []
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        for row_id, version_id in sorted(row_versions.items()):
            view = _b_source_view_row(report, "baseline", row_id)
            if canonical_sha256(view) != canonical_sha256(expected.get(row_id)):
                raise PortalConsumerRegistrationError("基线报告行与锁定原子、上下文或原文不一致")
            item = facts[version_id]
            fragment = fragments.get(item["primary_fragment_id"])
            persisted = database.execute(
                "SELECT v.content_sha256,v.scientific_context_json,v.primary_fragment_id,"
                "f.source_version_id,f.locator,f.content_text FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?", (version_id,),
            ).fetchone()
            if fragment is None or persisted is None or tuple(persisted) != (
                item["content_sha256"], item["scientific_context_json"],
                item["primary_fragment_id"], fragment["source_version_id"],
                canonical_source_pointer(fragment["locator"]), fragment["original_text"],
            ):
                raise PortalConsumerRegistrationError("基线持久化事实与锁定来源片段不一致")
            binding = active_fact_binding_for_b(report, "baseline", row_id)
            candidates.append((version_id, binding))
        # Preflight the entire set before inserting append-only declarations.
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            existing = database.execute(
                "SELECT collection,row_id,binding_json,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? AND report='B'",
                (version_id,),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                "baseline", binding.row_id, encoded, evidence_snapshot.snapshot_id,
            ):
                raise PortalConsumerRegistrationError("已登记基线消费者与当前候选冲突")
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            database.execute(
                "INSERT INTO source_portal_consumer_bindings "
                "(binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(binding_id) DO NOTHING",
                (stable_id("source-portal-binding", version_id, "B", "baseline", binding.row_id),
                 version_id, evidence_snapshot.snapshot_id, "B", "baseline", binding.row_id,
                 encoded, hashlib.sha256(encoded.encode()).hexdigest(), registered_at.isoformat()),
            )
    return tuple(binding for _, binding in candidates)


def _source_pointer(locator_text: str) -> str | None:
    try:
        locator = json.loads(locator_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(locator, dict):
        return None
    path = locator.get("field_path")
    return path if isinstance(path, str) else None


def _safety_source_context_matches(
    context: Mapping[str, Any],
    row: SafetyRow,
    numeric: float,
) -> bool:
    """Prove raw event counts and direct safety outcomes without inventing rates."""
    if context.get("domain") != "adverse_events" or not math.isfinite(numeric):
        return False
    endpoint = context.get("endpoint")
    direct = isinstance(endpoint, str) and bool(endpoint.strip())
    expected_window = (
        context.get("observation_timepoint") or context.get("timepoint")
        if direct
        else context.get("timepoint")
    )
    if row.time_window != expected_window:
        return False
    if direct:
        assert isinstance(endpoint, str)
        source_class = context.get("class_title") or ""
        source_category = context.get("category_title") or ""
        raw_unit = context.get("source_unit")
        if not isinstance(raw_unit, str):
            return False
        # Count facts carry the normalized unit from research_facts_from_ctgov_atom.
        # Recover this *typed* participant-count identity, not an arbitrary label
        # heuristic: reported estimates must never be converted into n/N.
        if (
            raw_unit == "人"
            and context.get("value_role") == "participant_count"
            and context.get("metric") == "participant_count"
        ):
            raw_unit = "Participants"
        unit, measure, basis = ctgov_direct_safety_measure_identity(
            endpoint,
            source_class,
            source_category,
            raw_unit,
        )
        semantic = describe_measured_safety_concept(endpoint, source_class, source_category)
        if (
            row.term != endpoint
            or row.term_key != semantic.key
            or row.category != safety_category_zh(semantic.key)
            or row.source_class_title != (source_class or None)
            or row.source_category_title != (source_category or None)
            or (row.unit, row.measure_object, row.count_basis) != (unit, measure, basis)
            or context.get("value_role")
            != ("participant_count" if measure == "participant_count" else "reported_measure")
        ):
            return False
        if measure != "participant_count":
            return (
                row.numerator is None
                and row.denominator is None
                and (measure != "event_count" or (numeric >= 0 and numeric.is_integer()))
            )
    elif (
        context.get("value_role") != "affected_count"
        or row.measure_object != "participant_count"
        or row.unit != "人"
        or (context.get("category"), row.term_key, row.term)
        not in {
            ("sae", "any_sae", "严重不良事件组别汇总计数"),
            ("death", "death", "死亡病例组别汇总计数"),
        }
    ):
        return False
    if not numeric.is_integer() or numeric < 0:
        return False
    denoms = {
        item["parsed_value"]
        for item in context.get("denominator_candidates") or ()
        if isinstance(item, dict)
        and item.get("group_id") == row.group_id
        and type(item.get("parsed_value")) in {int, float}
    }
    if direct and row.count_basis == "mixed":
        return row.numerator is None and row.denominator is None
    if len(denoms) > 1:
        return False
    denominator = next(iter(denoms), None)
    expected = (
        (int(numeric), denominator) if denominator is not None and denominator > 0 else (None, None)
    )
    return (row.numerator, row.denominator) == expected


def project_b_safety_source_views(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    report: ReportAPortalData,
    row_versions: Mapping[str, str],
) -> tuple[dict[str, Any], ...]:
    """Read-only exact source views; these do not grant B edit/product bindings.

    An unknown arm can retain its original observation, quote and locator in B,
    while registration and product comparison still require a separately proven
    arm--intervention relationship.  The locked closure is checked against the
    append-only database before exposing any of its locations as precise.
    """
    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise PortalConsumerRegistrationError("来源视图只能引用证据快照")
    if not row_versions or len(set(row_versions.values())) != len(row_versions):
        raise PortalConsumerRegistrationError("来源视图缺少唯一的来源数值原子")
    snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    contract = verify_project_workspace(project_root).contract
    if (
        snapshot["project_id"] != contract.project_id
        or snapshot["contract_version"] != contract.contract_version
        or report.indication != contract.indication
        or report.data_cutoff != datetime.fromisoformat(snapshot["data_cutoff"])
    ):
        raise PortalConsumerRegistrationError("B 来源视图、快照与项目合同不一致")
    closure = snapshot.get("closure")
    if not isinstance(closure, dict):
        raise PortalConsumerRegistrationError("来源视图必须引用带原始闭包的证据快照")
    facts = {item["fact_version_id"]: item for item in closure["facts"]}
    fragments = {item["fragment_id"]: item for item in closure["fragments"]}
    sources = {item["source_version_id"]: item for item in closure["sources"]}
    if (
        len(facts) != len(closure["facts"])
        or len(fragments) != len(closure["fragments"])
        or len(sources) != len(closure["sources"])
    ):
        raise PortalConsumerRegistrationError("来源闭包存在重复版本标识")
    rows = {row.row_id: row for row in report.safety}
    if len(rows) != len(report.safety):
        raise PortalConsumerRegistrationError("A 安全行标识不唯一")
    for row_ref in row_versions:
        collection, separator, row_id = row_ref.partition(":")
        if separator != ":" or collection != "safety" or row_id not in rows:
            raise PortalConsumerRegistrationError("B 来源视图只接受已有安全数值行")
    if not set(row_versions.values()) <= set(snapshot["fact_version_ids"]):
        raise PortalConsumerRegistrationError("B 来源事实版本不在锁定快照")

    result_views: list[dict[str, Any]] = []
    database_path = project_root / "state/project.sqlite"
    try:
        with sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True) as database:
            for row in report.safety:
                version_id = row_versions.get(f"safety:{row.row_id}")
                if version_id is None:
                    continue
                if row.trial_id is None or row.group_assignment_state == "unassessed":
                    raise PortalConsumerRegistrationError("来源行缺少研究或明确的组别关系状态")
                source = database.execute(
                    "SELECT v.raw_value,v.scientific_context_json,v.primary_fragment_id,"
                    "f.source_version_id,f.locator,f.content_text FROM fact_versions v "
                    "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                    "WHERE v.fact_version_id=?",
                    (version_id,),
                ).fetchone()
                if source is None or version_id not in facts:
                    raise PortalConsumerRegistrationError("来源数值原子缺失")
                raw_value, context_json, fragment_id, source_id, locator_json, quote = source
                fragment = fragments.get(fragment_id)
                captured = sources.get(source_id)
                if fragment is None or captured is None:
                    raise PortalConsumerRegistrationError("来源原子缺少锁定的片段或来源版本")
                try:
                    context = json.loads(str(context_json))
                    locator = json.loads(str(locator_json))
                    numeric = float(str(raw_value))
                    observation = context["result_context"]
                    capture_url = captured["capture"]["url"]
                except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
                    raise PortalConsumerRegistrationError("来源数值或科学语境不可核验") from error
                exact_locator = clean_evidence_locator(locator)
                if exact_locator is None or precise_locator_anchor(exact_locator) is None:
                    raise PortalConsumerRegistrationError("来源原子缺少精确非本机定位")
                checks = {
                    "snapshot_fact": (
                        facts[version_id]["primary_fragment_id"] == fragment_id
                        and facts[version_id]["scientific_context_json"] == context_json
                    ),
                    "snapshot_fragment": (
                        fragment["source_version_id"] == source_id
                        and fragment["locator"] == locator
                        and fragment["original_text"] == quote
                    ),
                    "source_identity": (
                        row.source_version_id == source_id and locator.get("url") == capture_url
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
                    "safety_domain": (
                        observation.get("domain") == "adverse_events"
                        and observation.get("value_role") != "denominator"
                    ),
                    "trial_and_group": (
                        str(observation.get("trial_id", "")).casefold() == row.trial_id.casefold()
                        and observation.get("group_id") == row.group_id
                        and observation.get("group_title") == row.arm
                    ),
                    "measure_context": (_safety_source_context_matches(observation, row, numeric)),
                }
                invalid = [scope for scope, valid in checks.items() if not valid]
                if invalid:
                    raise PortalConsumerRegistrationError(
                        f"安全结果 {row.row_id} 与锁定来源不一致：{','.join(invalid)}"
                    )
                result_views.append(
                    {
                        **row.model_dump(mode="json"),
                        "arm_id": row.group_id,
                        "arm_label": row.arm,
                        "source_locator": exact_locator.model_dump(mode="json"),
                        "source_text": quote,
                    }
                )
    except sqlite3.Error as error:
        raise PortalConsumerRegistrationError("只读来源库不可用") from error
    if len(result_views) != len(row_versions):
        raise PortalConsumerRegistrationError("B 来源视图未覆盖指定的全部数值行")
    return tuple(result_views)


def register_a_source_consumers(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    report: ReportAPortalData,
    row_versions: Mapping[str, str],
    *,
    registered_at: datetime,
    source_row_contexts: Mapping[str, SourceRowContext] | None = None,
) -> tuple[ActiveFactBinding, ...]:
    """Bind only direct, exact A observations with declared arm-product identity.

    ``row_versions`` is an explicit ``efficacy:<row>`` / ``safety:<row>`` to
    source fact version mapping. No fuzzy title/value search or row-order join is
    allowed here. Rates derived from n/N need their own declared calculation
    binding and are deliberately not admitted by this direct-atom function.
    """
    if registered_at.tzinfo is None or registered_at.utcoffset() is None:
        raise PortalConsumerRegistrationError("消费者登记时间缺少时区")
    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise PortalConsumerRegistrationError("消费者只能引用证据快照")
    if not row_versions:
        raise PortalConsumerRegistrationError("消费者登记缺少明确报告行")
    if len(set(row_versions.values())) != len(row_versions):
        raise PortalConsumerRegistrationError("同一来源原子不得复制为多个 A 报告行")
    if source_row_contexts is not None and set(source_row_contexts) - set(row_versions):
        raise PortalConsumerRegistrationError("原文对照含本次未登记的报告行")
    snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    contract = verify_project_workspace(project_root).contract
    if (
        snapshot["project_id"] != contract.project_id
        or snapshot["contract_version"] != contract.contract_version
        or report.indication != contract.indication
    ):
        raise PortalConsumerRegistrationError("候选来源、报告与项目合同不一致")
    snapshot_versions = set(snapshot["fact_version_ids"])
    if report.data_cutoff != datetime.fromisoformat(snapshot["data_cutoff"]):
        raise PortalConsumerRegistrationError("报告截止时间与来源快照不一致")
    candidates: list[tuple[str, ActiveFactBinding]] = []
    rows: dict[tuple[str, str], EfficacyRow | SafetyRow] = {
        (collection, row.row_id): row
        for collection, group in (("efficacy", report.efficacy), ("safety", report.safety))
        for row in group
    }
    if len(rows) != len(report.efficacy) + len(report.safety):
        raise PortalConsumerRegistrationError("报告行跨类别标识重复")
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        for row_ref, version_id in sorted(row_versions.items()):
            collection, separator, row_id = row_ref.partition(":")
            if separator != ":" or collection not in {"efficacy", "safety"}:
                raise PortalConsumerRegistrationError("A 来源行引用不是疗效/安全行")
            key = (collection, row_id)
            row = rows.get(key)
            if row is None or version_id not in snapshot_versions:
                raise PortalConsumerRegistrationError("来源事实版本或报告行不在本次闭包")
            if row.group_assignment_state != "declared" or not row.group_id:
                raise PortalConsumerRegistrationError("组别—产品归属未明确，不得生成可编辑消费者")
            if row.trial_id is None:
                raise PortalConsumerRegistrationError("报告结果行缺少试验身份")
            trial = next((item for item in report.trials if item.id == row.trial_id), None)
            if trial is None:
                raise PortalConsumerRegistrationError("报告试验身份不在当前候选中")
            source = database.execute(
                "SELECT v.raw_value,v.scientific_context_json,f.source_version_id,"
                "f.locator,f.content_text FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?",
                (version_id,),
            ).fetchone()
            if source is None:
                raise PortalConsumerRegistrationError("来源事实版本未持久化")
            raw_value, context_json, source_version, locator_json, quote = source
            try:
                context = json.loads(str(context_json))
                result = context["result_context"]
                numeric = float(str(raw_value))
            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
                raise PortalConsumerRegistrationError("来源原子不是可直接核验的数值结果") from error
            source_group_title = result.get("group_title")
            if not isinstance(source_group_title, str) or not (
                any(
                    link.product_id == row.product_id
                    and source_group_title.strip().casefold()
                    in {label.strip().casefold() for label in link.arm_labels}
                    for link in trial.product_links
                )
                or (not trial.product_links and trial.product_id == row.product_id)
            ):
                raise PortalConsumerRegistrationError("来源组别不在试验—产品干预关系中")
            if (
                not math.isfinite(numeric)
                or row.value is None
                or not math.isclose(row.value, numeric, rel_tol=0, abs_tol=1e-9)
                or row.source_version_id != source_version
                or row.source_field_path != _source_pointer(str(locator_json))
                or row.source_text != quote
                or str(result.get("trial_id", "")).casefold() != row.trial_id.casefold()
                or result.get("group_id") != row.group_id
                or result.get("value_role") == "denominator"
                or result.get("domain")
                != ("efficacy" if collection == "efficacy" else "adverse_events")
            ):
                raise PortalConsumerRegistrationError("报告行与来源原子数值、组别或精确定位不一致")
            if collection == "efficacy":
                if not isinstance(row, EfficacyRow):
                    raise PortalConsumerRegistrationError("疗效集合的报告行类型不一致")
                original = (source_row_contexts or {}).get(row_ref)
                source_endpoint = result.get("endpoint")
                source_timepoint = result.get("timepoint")
                source_observation = result.get("observation_timepoint")
                if original is not None:
                    if (
                        original.endpoint != source_endpoint
                        or original.timepoint not in {source_timepoint, source_observation}
                        or original.group_title != source_group_title
                        or original.value_path != row.source_field_path
                    ):
                        raise PortalConsumerRegistrationError("中文呈现行的原文对照与来源原子冲突")
                elif row.endpoint != source_endpoint or row.timepoint not in {
                    source_timepoint,
                    source_observation,
                }:
                    raise PortalConsumerRegistrationError("翻译后的终点/时间窗缺少精确原文对照")
                if result.get("value_role") == "participant_count" and row.unit in {"%", "％"}:
                    raise PortalConsumerRegistrationError("疗效终点或观察时间与来源原子不一致")
                if result.get("value_role") == "participant_count":
                    denominator_candidates = result.get("denominator_candidates")
                    values = {
                        item.get("parsed_value")
                        for item in denominator_candidates or ()
                        if isinstance(item, dict) and item.get("group_id") == row.group_id
                    }
                    if (
                        row.numerator != int(numeric)
                        or int(numeric) != numeric
                        or len(values) != 1
                        or row.denominator not in values
                    ):
                        raise PortalConsumerRegistrationError("登记人数与独立同组分母不一致")
                binding = active_fact_binding_for_a(report, "efficacy", row_id)
            else:
                if not isinstance(row, SafetyRow) or not _safety_source_context_matches(
                    result,
                    row,
                    numeric,
                ):
                    raise PortalConsumerRegistrationError("安全性统计对象、观察窗或来源原子不一致")
                binding = active_fact_binding_for_a(report, "safety", row_id)
            candidates.append((version_id, binding))

        # Preflight the entire requested set before writing any append-only row.
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            existing = database.execute(
                "SELECT collection,row_id,binding_json,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='A'",
                (version_id,),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                binding.collection,
                binding.row_id,
                encoded,
                evidence_snapshot.snapshot_id,
            ):
                raise PortalConsumerRegistrationError("已登记消费者身份与当前候选冲突")
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            database.execute(
                "INSERT OR IGNORE INTO source_portal_consumer_bindings "
                "(binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    stable_id(
                        "source-portal-binding", version_id, "A", binding.collection, binding.row_id
                    ),
                    version_id,
                    evidence_snapshot.snapshot_id,
                    "A",
                    binding.collection,
                    binding.row_id,
                    encoded,
                    hashlib.sha256(encoded.encode()).hexdigest(),
                    registered_at.isoformat(),
                ),
            )
    return tuple(binding for _version_id, binding in candidates)


def register_b_shared_source_consumers(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    report: ReportBPortalData,
    row_versions: Mapping[str, str],
    *,
    registered_at: datetime,
) -> tuple[ActiveFactBinding, ...]:
    """Attach B to a previously verified A direct observation, with no science rewrite.

    This narrow bridge admits only the same source atom and scientific identity
    already verified for A. It is not a general B-source ingestion or a claim
    that B's full related-study pool has been sourced.
    """
    if registered_at.tzinfo is None or registered_at.utcoffset() is None:
        raise PortalConsumerRegistrationError("消费者登记时间缺少时区")
    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise PortalConsumerRegistrationError("消费者只能引用证据快照")
    if not row_versions or len(set(row_versions.values())) != len(row_versions):
        raise PortalConsumerRegistrationError("B 消费者缺少唯一来源原子")
    snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    contract = verify_project_workspace(project_root).contract
    if (
        snapshot["project_id"] != contract.project_id
        or snapshot["contract_version"] != contract.contract_version
        or report.indication != contract.indication
        or report.data_cutoff != datetime.fromisoformat(snapshot["data_cutoff"])
    ):
        raise PortalConsumerRegistrationError("B 候选、来源快照与项目合同不一致")
    snapshot_versions = set(snapshot["fact_version_ids"])
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    candidates: list[tuple[str, ActiveFactBinding]] = []
    with open_database(database_path) as database:
        for row_ref, version_id in sorted(row_versions.items()):
            collection, separator, row_id = row_ref.partition(":")
            if separator != ":" or collection not in {"efficacy", "safety"}:
                raise PortalConsumerRegistrationError("共享 B 来源登记只支持直接疗效/安全观察")
            collection_name: Literal["efficacy", "safety"] = (
                "efficacy" if collection == "efficacy" else "safety"
            )
            if version_id not in snapshot_versions:
                raise PortalConsumerRegistrationError("B 来源事实版本不在本次证据快照")
            source = database.execute(
                "SELECT v.raw_value,v.scientific_context_json,f.source_version_id,"
                "f.locator,f.content_text FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?",
                (version_id,),
            ).fetchone()
            declared_a = database.execute(
                "SELECT binding_json,binding_sha256,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='A'",
                (version_id,),
            ).fetchone()
            if source is None or declared_a is None:
                raise PortalConsumerRegistrationError("共享 B 消费者缺少已核验 A 来源身份")
            if hashlib.sha256(str(declared_a[0]).encode()).hexdigest() != declared_a[1]:
                raise PortalConsumerRegistrationError("A 来源消费者登记摘要不一致")
            if declared_a[2] != evidence_snapshot.snapshot_id:
                raise PortalConsumerRegistrationError("A/B 来源消费者引用不同证据快照")
            a_binding = ActiveFactBinding.model_validate_json(str(declared_a[0]))
            try:
                b_binding = active_fact_binding_for_b(report, collection_name, row_id)
                view = _b_source_view_row(report, collection, row_id)
                context = json.loads(str(source[1]))["result_context"]
                numeric = float(str(source[0]))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
                raise PortalConsumerRegistrationError("B 来源行缺少可核验数值或来源view") from error
            rows = [row for row in getattr(report, collection) if row.row_id == row_id]
            if len(rows) != 1:
                raise PortalConsumerRegistrationError("B 来源行身份不唯一")
            row = rows[0]
            source_denominators = {
                item.get("parsed_value")
                for item in context.get("denominator_candidates") or ()
                if isinstance(item, dict)
                and item.get("group_id") == row.group_id
                and type(item.get("parsed_value")) in {int, float}
            }
            value_role = context.get("value_role")
            reported_count = value_role == "participant_count"
            reported_measure = value_role == "reported_measure"
            count_matches = (
                (
                    numeric.is_integer()
                    and row.numerator == int(numeric)
                    and b_binding.statistical_form == "count"
                )
                if reported_count and math.isfinite(numeric)
                else False
            )
            measure_matches = (
                (
                    row.numerator is None
                    and b_binding.measure_object == "estimate"
                    and b_binding.statistical_form == "estimate"
                )
                if reported_measure
                else False
            )
            shared_fields = (
                "product_id",
                "drug_name",
                "trial_id",
                "registry_id",
                "group_id",
                "arm",
                "cohort_id",
                "period",
                "endpoint_definition",
                "event_definition",
                "statistical_form",
                "measure_object",
                "unit",
                "normalized_unit",
                "source_version_id",
            )
            efficacy_matches = (
                (
                    context.get("domain") == "efficacy"
                    and (count_matches or measure_matches)
                    and len(source_denominators) <= 1
                    and (len(source_denominators) != 1 or row.denominator in source_denominators)
                    and (source_denominators or row.denominator is None)
                    and (not reported_count or bool(source_denominators))
                    and view.get("numerator") == row.numerator
                    and view.get("denominator") == row.denominator
                )
                if collection == "efficacy"
                else False
            )
            source_category = context.get("category")
            safety_identity = (
                {
                    "sae": ("any_sae", "serious"),
                    "death": ("death", "deaths"),
                }.get(source_category)
                if isinstance(source_category, str)
                else None
            )
            safety_matches = (
                (
                    isinstance(row, SafetyRow)
                    and _safety_source_context_matches(context, row, numeric)
                    and (
                        bool(context.get("endpoint"))
                        or (
                            safety_identity is not None
                            and (row.term_key, row.at_risk_stat) == safety_identity
                        )
                    )
                    and all(
                        view.get(field) == expected
                        for field, expected in (
                            ("product_id", row.product_id),
                            ("trial_id", row.trial_id),
                            ("arm_id", row.group_id),
                            ("arm_label", row.arm),
                            ("term", row.term),
                            ("term_key", row.term_key),
                            ("measure_object", row.measure_object),
                            ("count_basis", row.count_basis),
                            ("source_class_title", row.source_class_title),
                            ("source_category_title", row.source_category_title),
                            ("time_window", row.time_window),
                            ("value", row.value),
                            ("unit", row.unit),
                            ("numerator", row.numerator),
                            ("denominator", row.denominator),
                        )
                    )
                )
                if collection == "safety"
                else False
            )
            if (
                not math.isfinite(numeric)
                or not (efficacy_matches or safety_matches)
                or row.value is None
                or not math.isclose(row.value, numeric, rel_tol=0, abs_tol=1e-9)
                or row.group_assignment_state != "declared"
                or row.group_id != context.get("group_id")
                or str(context.get("trial_id", "")).casefold() != row.trial_id.casefold()
                or canonical_source_pointer(view.get("source_locator")) != str(source[3])
                or view.get("source_text") != source[4]
                or any(
                    getattr(a_binding, field) != getattr(b_binding, field)
                    for field in shared_fields
                )
            ):
                raise PortalConsumerRegistrationError("B 来源行与 A 科学身份、原子或原文不一致")
            candidates.append((version_id, b_binding))

        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            existing = database.execute(
                "SELECT collection,row_id,binding_json,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='B'",
                (version_id,),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                binding.collection,
                binding.row_id,
                encoded,
                evidence_snapshot.snapshot_id,
            ):
                raise PortalConsumerRegistrationError("已登记 B 消费者与当前候选冲突")
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            database.execute(
                "INSERT OR IGNORE INTO source_portal_consumer_bindings "
                "(binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    stable_id(
                        "source-portal-binding", version_id, "B", binding.collection, binding.row_id
                    ),
                    version_id,
                    evidence_snapshot.snapshot_id,
                    "B",
                    binding.collection,
                    binding.row_id,
                    encoded,
                    hashlib.sha256(encoded.encode()).hexdigest(),
                    registered_at.isoformat(),
                ),
            )
    return tuple(binding for _version_id, binding in candidates)
