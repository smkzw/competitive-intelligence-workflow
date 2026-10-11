"""Pure view adapter routing accepted publication composite cells into the B views.

One bounded bridge between immutable accepted source facts and the existing
``efficacy``/``safety`` view mappings: a fact whose source context declares
``raw_value_type=composite_count_and_percent`` in the efficacy or
adverse-events domain gets one display row per parent fact, projected with the
exact ``publication_value_components`` helper. The view value is the
independently printed percent token — never recomputed from a column header N,
never a derived ratio — and the independently printed count rides along as
``reported_count`` with no denominator. Product, arm and NCT identities stay
unknown; threshold/footnote cells stay in-domain but
``unresolved_due_to_route``; every fact outside this composite adapter is
returned verbatim under ``unhandled``. Identities come only from the supplied
exact version mappings, and the display clause copy — never the frozen source
model — carries ``source_version_id``/``source_measure_path`` for the existing
source-question binder. Consumers, shared renderer, persistence and browser
acceptance remain the Owner's surface; this module persists nothing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ci_workflow.application.source_research_service import (
    ResearchFact,
    ResearchResultContext,
)
from ci_workflow.reports.b.publication_components import publication_value_components

_PROJECTED = "projected"
_UNRESOLVED_ROUTE = "unresolved_due_to_route"

# Only these source domains may be presented under the existing efficacy and
# safety views; every other domain or context form stays unhandled verbatim.
_DOMAIN_VIEWS: Mapping[str, str] = {"efficacy": "efficacy", "adverse_events": "safety"}

def build_source_publication_views(
    facts: Sequence[ResearchFact], *,
    source_versions: Mapping[str, str],
    fact_versions: Mapping[str, str],
) -> dict[str, Any]:
    """Route source composite cells into existing views plus verbatim leftovers.

    Returns ``efficacy`` and ``safety`` view mappings (each ``{"facts": rows}``)
    plus ``unhandled`` holding the exact original facts this bounded adapter
    does not project. Duplicate fact identities fail closed — never first-wins —
    and routed rows demand a non-blank entry in both supplied version mappings.
    """
    seen: dict[str, int] = {}
    for fact in facts:
        seen[fact.fact_id] = seen.get(fact.fact_id, 0) + 1
    duplicates = sorted(fid for fid, count in seen.items() if count > 1)
    if duplicates:
        raise ValueError(
            "复合单元格视图收到重复事实身份，不能first-wins：" + "、".join(duplicates)
        )
    efficacy_rows: list[dict[str, Any]] = []
    safety_rows: list[dict[str, Any]] = []
    unhandled: list[ResearchFact] = []
    for fact in facts:
        context = fact.result_context
        view = _DOMAIN_VIEWS.get(context.domain) if context is not None else None
        if (
            context is None
            or view is None
            or context.raw_value_type != "composite_count_and_percent"
        ):
            unhandled.append(fact)
            continue
        row = _composite_row(
            fact, context,
            source_versions=source_versions, fact_versions=fact_versions,
        )
        (efficacy_rows if view == "efficacy" else safety_rows).append(row)
    efficacy_rows.sort(key=lambda row: str(row["row_id"]))
    safety_rows.sort(key=lambda row: str(row["row_id"]))
    unhandled.sort(key=lambda item: item.fact_id)
    return {
        "efficacy": {"facts": tuple(efficacy_rows)},
        "safety": {"facts": tuple(safety_rows)},
        "unhandled": tuple(unhandled),
    }


def _exact_version(mapping: Mapping[str, str], key: str, kind: str) -> str:
    value = mapping.get(key)
    if value is None or not value.strip():
        raise ValueError(
            f"复合单元格{kind}版本未闭合：{key}（视图要求精确版本身份，不接受缺失或空白）"
        )
    return value


def _composite_row(
    fact: ResearchFact,
    context: ResearchResultContext, *,
    source_versions: Mapping[str, str],
    fact_versions: Mapping[str, str],
) -> dict[str, Any]:
    source_version = _exact_version(source_versions, fact.source_id, "来源")
    fact_version = _exact_version(fact_versions, fact.fact_id, "事实")
    projection = publication_value_components(fact)["projection"]
    value: float | None = None
    count: int | None = None
    if projection["state"] == _PROJECTED:
        for component in projection["components"]:
            if component["kind"] == "percent":
                value = float(component["value"])
            elif component["kind"] == "count":
                count = int(component["value"])
    disclosure: str = fact.disclosure_state
    projection_reason = projection["reason"]
    if projection["state"] != _PROJECTED:
        disclosure = _UNRESOLVED_ROUTE
    elif disclosure == "reported_zero" and (
        (value is not None and value != 0.0) or (count is not None and count != 0)
    ):
        # A printed nonzero cell under a declared zero is inconsistent; it must
        # stay unresolved, never a false zero or a silently trusted nonzero.
        disclosure = _UNRESOLVED_ROUTE
        projection_reason = "来源披露声明为零，但单元格印刷分量非零；保持未解析，不伪称零值。"
    projected = disclosure != _UNRESOLVED_ROUTE
    return {
        "row_id": fact.fact_id,
        "source_row_id": fact.fact_id,
        "source_fact_version_id": fact_version,
        "source_version_id": source_version,
        "trial_id": fact.entity_id,
        "source_trial_label": context.trial_id,
        "product_id": None,
        "group_id": context.group_id,
        "group_label_zh": "来源组：" + (context.group_title or context.group_id),
        "source_group_title": context.group_title,
        "arm_role": "unknown",
        "group_assignment_state": "unknown",
        "source_name": context.term,
        "source_endpoint": context.endpoint,
        "endpoint": context.endpoint,
        "source_measure_path": context.source_measure_path,
        "source_measure_definition": context.endpoint,
        "source_timepoint": context.timepoint,
        "timepoint": context.timepoint,
        "observation_timepoint": context.observation_timepoint,
        "analysis_population": context.analysis_population,
        "source_analysis_population": context.analysis_population,
        "field_family": "论文结果",
        "statistic_form": "proportion" if projected else None,
        "statistic_label_zh": "报告百分比" if projected else None,
        **({"source_param_type": context.source_param_type}
           if context.source_param_type is not None else {}),
        **({"source_dispersion_type": context.source_dispersion_type}
           if context.source_dispersion_type is not None else {}),
        "source_value_role": context.value_role,
        "source_domain": context.domain,
        "source_metric": context.metric,
        "unit": "%" if projected else None,
        "value": value if projected else None,
        "reported_count": count if projected else None,
        "numerator": None,
        "denominator": None,
        "raw_value": fact.raw_value,
        "source_text": fact.original_text,
        "source_locator": fact.locator.model_dump(mode="json"),
        "source_id": fact.source_id,
        "source_result_context": context.model_dump(mode="json"),
        "source_component_projection": projection,
        "source_fact": fact.model_dump(mode="json"),
        "source_disclosure_state": fact.disclosure_state,
        "disclosure_state": disclosure,
        "projection_reason": projection_reason,
        "source_clause_context": _display_clause(
            fact, source_version=source_version,
        ),
    }


def _display_clause(fact: ResearchFact, *, source_version: str) -> dict[str, Any] | None:
    """Copy the clause context and bind display identity into its scope copy.

    The frozen source model is never touched. A predeclared scope identity that
    conflicts with the supplied version or the context's own measure path is
    rejected instead of overwritten; matching or absent keys are kept or added.
    """
    clause = fact.source_clause_context
    if clause is None:
        return None
    display = clause.model_dump(mode="json")
    scope = dict(display["scientific_scope"])
    context = fact.result_context
    measure_path = context.source_measure_path if context is not None else None
    for key, expected in (
        ("source_version_id", source_version),
        ("source_measure_path", measure_path),
    ):
        predeclared = scope.get(key)
        if key in scope and predeclared != expected:
            raise ValueError(
                f"科学范围预声明的 {key} 与供给身份冲突：{predeclared!r}≠{expected!r}；"
                "不覆盖漂移，请先核对来源"
            )
        scope.setdefault(key, expected)
    display["scientific_scope"] = scope
    return display
