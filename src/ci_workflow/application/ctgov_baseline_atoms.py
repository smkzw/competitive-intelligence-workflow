"""Exact baseline scalars into existing source facts, without guessed arm/product or rates.

No result snapshot, historical source or current pointer is changed here. Population,
measure/group wording and source paths are retained before any semantic comparison.
Invalid scalars stay as original facts with scoped issues, never fabricated zeroes.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from ci_workflow.application.source_research_service import (
    ClinicalTrialsResultCoverageIssue,
    ClinicalTrialsResultIssueStatus,
    RegistryDenominatorCandidate,
    ResearchFact,
    ResearchPackageError,
    ResearchResultContext,
    SourceCapture,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.source_clause_context import SourceClauseContext, SourceClauseReference
from ci_workflow.storage.source_derivation import extract_locator_quote, source_json_decoder

_BASE = "$.resultsSection.baselineCharacteristicsModule"
_Role = Literal["reported_measure", "participant_count", "denominator", "dispersion"]


@dataclass(frozen=True)
class CtgovBaselineAtoms:
    trial_id: str
    source_id: str
    facts: tuple[ResearchFact, ...]
    issues: tuple[ClinicalTrialsResultCoverageIssue, ...]


def extract_ctgov_baseline_atoms(source: SourceCapture) -> CtgovBaselineAtoms:
    """Extract module, measure and group scalars; isolate malformed measurement scope.

    Ns are unselected candidates, including duplicates and explicit zero. Missing or
    contradictory Ns never suppress a healthy measurement or produce a proportion.
    Raw source group identity is NOT a treatment association; all arms stay unknown.
    """
    if source.source_type != "clinical_trial_registry" or source.media_type != "application/json":
        raise ResearchPackageError("基线原子提取需要JSON登记来源")
    try:
        record = source_json_decoder().decode(source.content_text)
        trial_id = record["protocolSection"]["identificationModule"]["nctId"]
        if not isinstance(trial_id, str) or trial_id.casefold() != (
            source.query_or_identifier.casefold()
        ):
            raise ValueError("试验身份不一致")
    except (KeyError, TypeError, ValueError) as error:
        raise ResearchPackageError("基线来源不能证明试验身份") from error
    facts: list[ResearchFact] = []
    issues: list[ClinicalTrialsResultCoverageIssue] = []

    def issue(path: str, status: ClinicalTrialsResultIssueStatus, reason: str) -> None:
        issues.append(ClinicalTrialsResultCoverageIssue(
            category="baseline", status=status, trial_id=trial_id, source_id=source.source_id,
            source_path=path, result_key=stable_id("baseline-scope", trial_id, path),
            reason_zh=reason,
        ))

    def items(value: object, path: str) -> list[Any]:
        if isinstance(value, list):
            return value
        issue(path, "missing" if value is None else "parse_failure", "基线列表缺失或格式不正确")
        return []

    def obj(value: object, path: str) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        issue(path, "parse_failure", "基线对象格式不正确")
        return {}

    def locator(path: str) -> EvidenceLocator:
        return EvidenceLocator(document_role="clinical_trial_registry", field_path=path,
                               url=source.url)

    def quote(value: object, path: str) -> str:
        text = extract_locator_quote(source.content_text, media_type=source.media_type,
                                     locator=locator(path))
        expected = value if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        if text != expected:
            raise ResearchPackageError(f"{path}基线原子不能按来源精确重提取")
        return text

    def raw_fact(path: str, value: object, *, context: ResearchResultContext | None = None,
                 references: tuple[SourceClauseReference, ...] = ()) -> ResearchFact:
        text = quote(value, path)
        normalized = None
        zero = False
        if context is not None:
            try:
                if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                    raise ValueError("数值标量类型不正确")
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError("不是有限数值")
                if context.value_role in {"participant_count", "denominator"}:
                    if number < 0 or not number.is_integer():
                        raise ValueError("人数必须是非负整数")
                    normalized = str(int(number))
                else:
                    if context.value_role == "dispersion" and number < 0:
                        raise ValueError("离散度不能为负数")
                    normalized = str(number)
                zero = number == 0
            except (TypeError, ValueError) as error:
                issue(path, "parse_failure", f"原始标量保留；不能作为数值使用：{error}")
        fact = ResearchFact(
            fact_id=stable_id("ctgov-baseline-fact", source.source_id, path),
            row_ref=f"registry:{trial_id.casefold()}:baseline:{path}",
            entity_id=stable_id("clinical-trial", trial_id), entity_type="clinical_trial",
            canonical_name=trial_id, field_id=(
                f"ctgov.baseline.{context.value_role}" if context else "ctgov.baseline.context"
            ),
            raw_value=text, normalized_value=normalized,
            disclosure_state="reported_zero" if zero else "reported_value",
            source_id=source.source_id, locator=locator(path), original_text=text,
            result_context=context,
            source_clause_context=(SourceClauseContext(
                label_zh="基线原始统计上下文",
                scope_note_zh="登记来源层；组别尚未绑定产品，不派生比例。",
                scientific_scope={"module": "baselineCharacteristicsModule",
                                  "group_id": context.group_id},
                continuations=references,
            ) if context else None),
        )
        facts.append(fact)
        return fact

    def refs(mapping: dict[str, Any], path: str, keys: tuple[str, ...]) -> tuple[
        SourceClauseReference, ...
    ]:
        result = []
        for key in keys:
            value = mapping.get(key)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                issue(f"{path}.{key}", "parse_failure", "基线上下文文本格式不正确")
                if not isinstance(value, str) or value.strip():
                    raw_fact(f"{path}.{key}", value)
                continue
            fact = raw_fact(f"{path}.{key}", value)
            result.append(SourceClauseReference(
                reference_id=fact.fact_id, source_id=source.source_id, label_zh=f"原始字段 {key}",
                locator=fact.locator, original_text=fact.original_text,
            ))
        return tuple(result)

    results = record.get("resultsSection")
    module = results.get("baselineCharacteristicsModule") if isinstance(results, dict) else None
    if module is None:
        issue(_BASE, "missing", "来源未提供基线模块；不补零，也不等同网络或解析失败")
        return CtgovBaselineAtoms(trial_id, source.source_id, (), tuple(issues))
    module = obj(module, _BASE)
    population = module.get("populationDescription")
    population_refs = refs(module, _BASE, ("populationDescription",))
    if not population_refs:
        issue(f"{_BASE}.populationDescription", "missing", "基线分析人群未明确，保持未知")
    groups: dict[str, list[tuple[dict[str, Any], tuple[SourceClauseReference, ...]]]] = (
        defaultdict(list)
    )
    for index, raw in enumerate(items(module.get("groups"), f"{_BASE}.groups")):
        path = f"{_BASE}.groups[{index}]"
        group = obj(raw, path)
        group_refs = refs(group, path, ("id", "title", "description"))
        group_id = group.get("id")
        if not isinstance(group_id, str) or not group_id.strip():
            issue(f"{path}.id", "missing", "组别缺少明确ID，不按数组顺序补身份")
            continue
        groups[group_id].append((group, group_refs))
        if len(groups[group_id]) > 1:
            issue(path, "conflicting", "重复组别ID，禁止first-wins归属")

    candidates: dict[str, list[RegistryDenominatorCandidate]] = defaultdict(list)

    def text(mapping: dict[str, Any], key: str) -> str:
        value = mapping.get(key)
        return value if isinstance(value, str) else ""

    def context_for(group_id: str, *, role: _Role, path: str, title: str, unit: str,
                    measure_path: str, param: str | None = None, dispersion: str | None = None,
                    class_title: str | None = None, category_title: str | None = None,
                    value: object = None,
                    n_candidates: list[RegistryDenominatorCandidate] | None = None,
                    ) -> tuple[ResearchResultContext, tuple[SourceClauseReference, ...]]:
        entries = groups.get(group_id, [])
        group, group_refs = entries[0] if len(entries) == 1 else ({}, ())
        return ResearchResultContext(
            result_key=stable_id("baseline-instance", source.source_id, path), category="baseline",
            trial_id=trial_id, group_id=group_id, group_title=text(group, "title"),
            group_description=text(group, "description") or None,
            arm="unknown", term=title, endpoint=title,
            timepoint="baseline registry module; visit not specified", value_role=role,
            source_unit=unit, domain="baseline", metric="baseline_source_scalar",
            source_measure_path=measure_path, source_param_type=param,
            source_dispersion_type=dispersion, raw_value_type=type(value).__name__,
            analysis_population=population if isinstance(population, str) else None,
            class_title=class_title, category_title=category_title,
            denominator_candidates=tuple(
                candidates[group_id] if n_candidates is None else n_candidates
            ),
        ), population_refs + group_refs

    def collect_denoms(
        container: dict[str, Any], base: str,
        extra_refs: tuple[SourceClauseReference, ...] = (),
    ) -> dict[str, list[RegistryDenominatorCandidate]]:
        scoped: dict[str, list[RegistryDenominatorCandidate]] = defaultdict(list)
        for di, raw in enumerate(items(container.get("denoms"), f"{base}.denoms")):
            path = f"{base}.denoms[{di}]"
            denom = obj(raw, path)
            denom_refs = refs(denom, path, ("units",))
            for ci, raw_count in enumerate(items(denom.get("counts"), f"{path}.counts")):
                count_path = f"{path}.counts[{ci}]"
                count = obj(raw_count, count_path)
                group_id = count.get("groupId")
                if not isinstance(group_id, str) or not group_id.strip():
                    issue(f"{count_path}.groupId", "missing", "分母没有组别ID")
                    continue
                id_refs = refs(count, count_path, ("groupId",))
                if count.get("value") is None:
                    issue(f"{count_path}.value", "missing", "该组原始N缺失，不影响其他测量")
                    continue
                unit = text(denom, "units")
                context, scope_refs = context_for(
                    group_id, role="denominator", path=count_path, title="Baseline group N",
                    unit=unit, measure_path=base, value=count["value"], n_candidates=[],
                )
                fact = raw_fact(f"{count_path}.value", count["value"], context=context,
                                references=scope_refs + extra_refs + denom_refs + id_refs)
                if fact.normalized_value is not None and unit.casefold() in {
                    "participants", "participant", "subjects", "subject",
                }:
                    scoped[group_id].append(RegistryDenominatorCandidate(
                        group_id=group_id, raw_value=fact.raw_value or "", raw_value_type=type(
                            count["value"]).__name__, parsed_value=int(fact.normalized_value),
                        unit=unit, value_path=f"{count_path}.value",
                    ))
                elif fact.normalized_value is not None:
                    issue(path, "conflicting", "N单位未确认是参与者人数，不作人数分母")
        for group_id, values in scoped.items():
            if len({candidate.parsed_value for candidate in values}) > 1:
                issue(f"{base}.denoms", "conflicting", f"{group_id}存在不同N，不选择第一项")
        return scoped

    candidates.update(collect_denoms(module, _BASE))

    for mi, raw in enumerate(items(module.get("measures"), f"{_BASE}.measures")):
        path = f"{_BASE}.measures[{mi}]"
        measure = obj(raw, path)
        measure_refs = refs(measure, path, (
            "title", "description", "paramType", "dispersionType", "unitOfMeasure",
        ))
        measure_ns = (collect_denoms(measure, path, measure_refs)
                      if "denoms" in measure else candidates)
        for cli, raw_class in enumerate(items(measure.get("classes"), f"{path}.classes")):
            class_path = f"{path}.classes[{cli}]"
            clazz = obj(raw_class, class_path)
            class_refs = refs(clazz, class_path, ("title",))
            class_ns = (collect_denoms(clazz, class_path, measure_refs + class_refs)
                        if "denoms" in clazz else measure_ns)
            for cai, raw_category in enumerate(items(
                clazz.get("categories"), f"{class_path}.categories"
            )):
                category_path = f"{class_path}.categories[{cai}]"
                category = obj(raw_category, category_path)
                category_refs = refs(category, category_path, ("title",))
                category_ns = (collect_denoms(category, category_path,
                                             measure_refs + class_refs + category_refs)
                               if "denoms" in category else class_ns)
                for vi, raw_value in enumerate(items(category.get("measurements"),
                                                      f"{category_path}.measurements")):
                    value_path = f"{category_path}.measurements[{vi}]"
                    measurement = obj(raw_value, value_path)
                    group_id = measurement.get("groupId")
                    if not isinstance(group_id, str) or not group_id.strip():
                        issue(f"{value_path}.groupId", "missing", "测量缺少组别ID，不猜关系")
                        continue
                    if group_id not in groups:
                        issue(f"{value_path}.groupId", "missing",
                              "测量引用未知组别，保留原子但不猜身份")
                    value_refs = refs(measurement, value_path, ("groupId", "comment"))
                    for key in ("value", "spread", "lowerLimit", "upperLimit"):
                        if measurement.get(key) is None:
                            if key in measurement or key == "value":
                                issue(f"{value_path}.{key}", "missing",
                                      "原始测量字段缺失，不用0补齐")
                            continue
                        if isinstance(measurement[key], str) and not measurement[key].strip():
                            issue(f"{value_path}.{key}", "parse_failure",
                                  "空白数值保留在原始来源，不生成空原文事实或零值")
                            continue
                        role: _Role = (
                            "dispersion" if key == "spread" else "participant_count"
                            if key == "value" and (
                                measure.get("paramType") == "COUNT_OF_PARTICIPANTS"
                            )
                            else "reported_measure"
                        )
                        context, scope_refs = context_for(
                            group_id, role=role, path=f"{value_path}.{key}",
                            title=text(measure, "title"), unit=text(measure, "unitOfMeasure"),
                            measure_path=path, param=text(measure, "paramType") or None,
                            dispersion=text(measure, "dispersionType") or None,
                            class_title=text(clazz, "title") or None,
                            category_title=text(category, "title") or None, value=measurement[key],
                            n_candidates=category_ns.get(group_id, []),
                        )
                        fact = raw_fact(
                            f"{value_path}.{key}", measurement[key], context=context,
                            references=scope_refs + measure_refs + class_refs + category_refs
                            + value_refs,
                        )
                        group_ns = {c.parsed_value for c in context.denominator_candidates}
                        if (role == "participant_count" and fact.normalized_value is not None
                            and len(group_ns) == 1
                            and int(fact.normalized_value) > next(iter(group_ns))):
                            issue(f"{value_path}.{key}", "conflicting",
                                  "原始人数大于该作用域N，保留矛盾，不产生合法比例")
    return CtgovBaselineAtoms(trial_id, source.source_id, tuple(facts), tuple(issues))
