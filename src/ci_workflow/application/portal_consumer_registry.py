"""Append-only bridge from verified source atoms to portal row consumers.

Registration is a development/candidate action. It does not accept evidence,
publish a report, or change the source fact's scientific content/version.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
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


def _source_pointer(locator_text: str) -> str | None:
    try:
        locator = json.loads(locator_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(locator, dict):
        return None
    path = locator.get("field_path")
    return path if isinstance(path, str) else None


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
                "WHERE v.fact_version_id=?", (version_id,),
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
                    and source_group_title.strip().casefold() in {
                        label.strip().casefold() for label in link.arm_labels
                    }
                    for link in trial.product_links
                )
                or (not trial.product_links and trial.product_id == row.product_id)
            ):
                raise PortalConsumerRegistrationError("来源组别不在试验—产品干预关系中")
            if (
                not math.isfinite(numeric) or row.value is None
                or not math.isclose(row.value, numeric, rel_tol=0, abs_tol=1e-9)
                or row.source_version_id != source_version
                or row.source_field_path != _source_pointer(str(locator_json))
                or row.source_text != quote
                or str(result.get("trial_id", "")).casefold() != row.trial_id.casefold()
                or result.get("group_id") != row.group_id
                or result.get("value_role") == "denominator"
                or result.get("domain") != (
                    "efficacy" if collection == "efficacy" else "adverse_events"
                )
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
                elif (
                    row.endpoint != source_endpoint
                    or row.timepoint not in {source_timepoint, source_observation}
                ):
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
                        row.numerator != int(numeric) or int(numeric) != numeric
                        or len(values) != 1 or row.denominator not in values
                    ):
                        raise PortalConsumerRegistrationError("登记人数与独立同组分母不一致")
                binding = active_fact_binding_for_a(report, "efficacy", row_id)
            else:
                if not isinstance(row, SafetyRow) or (
                    result.get("timepoint") != row.time_window
                    or result.get("value_role") != "affected_count"
                    or row.measure_object not in {"participant_count", "event_count"}
                ):
                    raise PortalConsumerRegistrationError("安全性观察窗与来源原子不一致")
                binding = active_fact_binding_for_a(report, "safety", row_id)
            candidates.append((version_id, binding))

        # Preflight the entire requested set before writing any append-only row.
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            existing = database.execute(
                "SELECT collection,row_id,binding_json,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='A'", (version_id,),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                binding.collection, binding.row_id, encoded,
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
                    stable_id("source-portal-binding", version_id, "A",
                              binding.collection, binding.row_id),
                    version_id, evidence_snapshot.snapshot_id, "A",
                    binding.collection, binding.row_id, encoded,
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
            if separator != ":" or collection != "efficacy":
                raise PortalConsumerRegistrationError("共享 B 来源登记当前只支持直接疗效观察")
            if version_id not in snapshot_versions:
                raise PortalConsumerRegistrationError("B 来源事实版本不在本次证据快照")
            source = database.execute(
                "SELECT v.raw_value,v.scientific_context_json,f.source_version_id,"
                "f.locator,f.content_text FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?", (version_id,),
            ).fetchone()
            declared_a = database.execute(
                "SELECT binding_json,binding_sha256,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='A'", (version_id,),
            ).fetchone()
            if source is None or declared_a is None:
                raise PortalConsumerRegistrationError("共享 B 消费者缺少已核验 A 来源身份")
            if hashlib.sha256(str(declared_a[0]).encode()).hexdigest() != declared_a[1]:
                raise PortalConsumerRegistrationError("A 来源消费者登记摘要不一致")
            if declared_a[2] != evidence_snapshot.snapshot_id:
                raise PortalConsumerRegistrationError("A/B 来源消费者引用不同证据快照")
            a_binding = ActiveFactBinding.model_validate_json(str(declared_a[0]))
            try:
                b_binding = active_fact_binding_for_b(report, "efficacy", row_id)
                view = _b_source_view_row(report, "efficacy", row_id)
                context = json.loads(str(source[1]))["result_context"]
                numeric = float(str(source[0]))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
                raise PortalConsumerRegistrationError("B 来源行缺少可核验数值或来源view") from error
            rows = [row for row in report.efficacy if row.row_id == row_id]
            if len(rows) != 1:
                raise PortalConsumerRegistrationError("B 来源行身份不唯一")
            row = rows[0]
            source_denominators = {
                item.get("parsed_value")
                for item in context.get("denominator_candidates") or ()
                if isinstance(item, dict) and item.get("group_id") == row.group_id
                and type(item.get("parsed_value")) in {int, float}
            }
            value_role = context.get("value_role")
            reported_count = value_role == "participant_count"
            reported_measure = value_role == "reported_measure"
            count_matches = (
                numeric.is_integer()
                and row.numerator == int(numeric)
                and b_binding.statistical_form == "count"
            ) if reported_count and math.isfinite(numeric) else False
            measure_matches = (
                row.numerator is None
                and b_binding.measure_object == "estimate"
                and b_binding.statistical_form == "estimate"
            ) if reported_measure else False
            shared_fields = (
                "product_id", "drug_name", "trial_id", "registry_id", "group_id",
                "arm", "cohort_id", "period", "endpoint_definition", "event_definition",
                "statistical_form", "measure_object", "unit", "normalized_unit",
                "source_version_id",
            )
            if (
                not math.isfinite(numeric)
                or context.get("domain") != "efficacy"
                or not (count_matches or measure_matches)
                or row.value is None
                or not math.isclose(row.value, numeric, rel_tol=0, abs_tol=1e-9)
                or len(source_denominators) > 1
                or (
                    len(source_denominators) == 1
                    and row.denominator not in source_denominators
                )
                or (not source_denominators and row.denominator is not None)
                or (reported_count and not source_denominators)
                or view.get("numerator") != row.numerator
                or view.get("denominator") != row.denominator
                or row.group_assignment_state != "declared"
                or row.group_id != context.get("group_id")
                or str(context.get("trial_id", "")).casefold() != row.trial_id.casefold()
                or canonical_source_pointer(view.get("source_locator")) != str(source[3])
                or view.get("source_text") != source[4]
                or any(getattr(a_binding, field) != getattr(b_binding, field)
                       for field in shared_fields)
            ):
                raise PortalConsumerRegistrationError("B 来源行与 A 科学身份、原子或原文不一致")
            candidates.append((version_id, b_binding))

        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            existing = database.execute(
                "SELECT collection,row_id,binding_json,evidence_snapshot_id FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='B'", (version_id,),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                binding.collection, binding.row_id, encoded, evidence_snapshot.snapshot_id,
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
                    stable_id("source-portal-binding", version_id, "B",
                              binding.collection, binding.row_id),
                    version_id, evidence_snapshot.snapshot_id, "B",
                    binding.collection, binding.row_id, encoded,
                    hashlib.sha256(encoded.encode()).hexdigest(),
                    registered_at.isoformat(),
                ),
            )
    return tuple(binding for _version_id, binding in candidates)
