#!/usr/bin/env python3
"""将已保存的论文或官方披露结果合并进 A 类研究内容候选。

输入清单只描述结构化事实并引用本地原始来源文件；本工具读取原文、生成
``SourceCapture``/``ResearchFact``/``ResearchClaim``，再以完整 A 类合同验真。
它不创建科学复核结论，也不生成报告。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, cast

from ci_workflow.application.source_research_service import (
    FreshAResearchContent,
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    compute_research_content_digest,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id

_ResearchFactDisclosureState = Literal[
    "reported_value",
    "reported_zero",
    "not_reported",
    "below_reporting_threshold",
    "not_publicly_disclosed",
    "not_applicable",
    "conflicting",
    "unresolved_due_to_route",
]


class MergeError(ValueError):
    """非登记结果证据无法安全合并。"""


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MergeError(f"无法读取 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise MergeError(f"JSON 顶层必须是对象：{path}")
    return cast(dict[str, Any], value)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _load_source(item: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    source = dict(item)
    content_file = source.pop("content_file", None)
    if not isinstance(content_file, str) or not content_file.strip():
        raise MergeError("每个来源必须引用 content_file")
    source_path = (manifest_path.parent / content_file).resolve()
    try:
        content = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MergeError(f"无法读取原始来源：{source_path}") from exc
    expected = source.pop("content_sha256", None)
    actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if expected is not None and expected != actual:
        raise MergeError(f"原始来源摘要不一致：{source_path}")
    source["content_text"] = content
    return SourceCapture.model_validate(source).model_dump(mode="json")


def _fact(
    *,
    row_ref: str,
    entity_id: str,
    entity_type: str,
    canonical_name: str,
    field_id: str,
    value: object,
    disclosure_state: _ResearchFactDisclosureState,
    source_id: str,
    locator: dict[str, Any],
    original_text: str,
) -> dict[str, Any]:
    normalized = None if value is None else str(value)
    return ResearchFact(
        fact_id=stable_id("curated-result-fact", source_id, row_ref, field_id),
        row_ref=row_ref,
        entity_id=entity_id,
        entity_type=entity_type,
        canonical_name=canonical_name,
        field_id=field_id,
        raw_value=normalized,
        normalized_value=normalized,
        disclosure_state=disclosure_state,
        source_id=source_id,
        locator=EvidenceLocator.model_validate(locator),
        original_text=original_text,
    ).model_dump(mode="json")


def merge(base_path: Path, manifest_path: Path, output_path: Path) -> str:
    base = _read_object(base_path)
    manifest = _read_object(manifest_path)
    base.pop("scientific_review", None)
    report = cast(dict[str, Any], base["report_data"])

    remove_result_row_ids = {
        str(value)
        for value in cast(list[str], manifest.get("remove_result_row_ids", []))
    }
    # 允许对已清理过的正式基线重复执行；实际移除与不存在均为同一终态。
    for section in ("efficacy", "safety"):
        report[section] = [
            row
            for row in cast(list[dict[str, Any]], report[section])
            if str(row["row_id"]) not in remove_result_row_ids
        ]
    removed_row_refs = {
        f"{section}:{row_id}"
        for section in ("efficacy", "safety")
        for row_id in remove_result_row_ids
    }

    remove_source_ids = {
        str(value) for value in cast(list[str], manifest.get("remove_source_ids", []))
    }
    sources = [
        item
        for item in cast(list[dict[str, Any]], base["sources"])
        if str(item["source_id"]) not in remove_source_ids
    ]
    base["sources"] = sources
    facts = [
        item
        for item in cast(list[dict[str, Any]], base["facts"])
        if str(item["source_id"]) not in remove_source_ids
        and str(item["row_ref"]) not in removed_row_refs
    ]
    base["facts"] = facts
    retained_fact_ids = {str(item["fact_id"]) for item in facts}
    claims: list[dict[str, Any]] = []
    for item in cast(list[dict[str, Any]], base["claims"]):
        fact_ids = [str(value) for value in item["fact_ids"] if str(value) in retained_fact_ids]
        if fact_ids:
            claims.append({**item, "fact_ids": fact_ids})
    base["claims"] = claims
    source_by_id = {str(item["source_id"]): item for item in sources}
    for raw in cast(list[dict[str, Any]], manifest.get("sources", [])):
        source = _load_source(raw, manifest_path)
        source_id = str(source["source_id"])
        if source_id in source_by_id:
            if source_by_id[source_id] != source:
                raise MergeError(f"来源标识重复且内容不一致：{source_id}")
            continue
        sources.append(source)
        source_by_id[source_id] = source

    fact_by_id = {str(item["fact_id"]): item for item in facts}
    claim_by_id = {str(item["claim_id"]): item for item in claims}

    def add_fact(item: dict[str, Any]) -> None:
        fact_id = str(item["fact_id"])
        existing = fact_by_id.get(fact_id)
        if existing is not None:
            if existing != item:
                raise MergeError(f"事实标识重复且内容不一致：{fact_id}")
            return
        facts.append(item)
        fact_by_id[fact_id] = item

    def add_claim(item: dict[str, Any]) -> None:
        claim_id = str(item["claim_id"])
        existing = claim_by_id.get(claim_id)
        if existing is not None:
            if existing != item:
                raise MergeError(f"声明标识重复且内容不一致：{claim_id}")
            return
        claims.append(item)
        claim_by_id[claim_id] = item

    trials = cast(list[dict[str, Any]], report["trials"])
    for replacement in cast(list[dict[str, Any]], manifest.get("trial_replacements", [])):
        item = dict(replacement)
        old_id = str(item.pop("old_id"))
        source_id = str(item.pop("source_id"))
        locator = cast(dict[str, Any], item.pop("locator"))
        original_text = str(item.pop("original_text"))
        positions = [index for index, trial in enumerate(trials) if str(trial["id"]) == old_id]
        replacement_positions = [
            index for index, trial in enumerate(trials) if str(trial["id"]) == str(item["id"])
        ]
        if len(positions) == 1:
            trials[positions[0]] = item
        elif not positions and len(replacement_positions) == 1:
            if trials[replacement_positions[0]] != item:
                raise MergeError(f"替换后试验内容不一致：{item['id']}")
        else:
            raise MergeError(f"待替换试验必须唯一存在：{old_id}")
        add_fact(_fact(
            row_ref=f"trial:{item['id']}", entity_id=str(item["id"]),
            entity_type="trial", canonical_name=str(item["name"]),
            field_id="trial.identity", value=item["id"], disclosure_state="reported_value",
            source_id=source_id, locator=locator, original_text=original_text,
        ))

    trial_ids = {str(item["id"]) for item in trials}
    for item in cast(list[dict[str, Any]], manifest.get("trials", [])):
        trial = dict(item)
        source_id = str(trial.pop("source_id"))
        locator = cast(dict[str, Any], trial.pop("locator"))
        original_text = str(trial.pop("original_text"))
        trial_id = str(trial["id"])
        if trial_id in trial_ids:
            existing = next(item for item in trials if str(item["id"]) == trial_id)
            if existing != trial:
                raise MergeError(f"试验标识重复且内容不一致：{trial_id}")
        else:
            trials.append(trial)
            trial_ids.add(trial_id)
        add_fact(_fact(
            row_ref=f"trial:{trial_id}", entity_id=trial_id, entity_type="trial",
            canonical_name=str(trial["name"]), field_id="trial.identity", value=trial_id,
            disclosure_state="reported_value", source_id=source_id, locator=locator,
            original_text=original_text,
        ))

    products = {str(item["id"]): item for item in cast(list[dict[str, Any]], report["products"])}
    for patch in cast(list[dict[str, Any]], manifest.get("product_updates", [])):
        item = dict(patch)
        product_id = str(item.pop("product_id"))
        source_id = str(item.pop("source_id"))
        locator = cast(dict[str, Any], item.pop("locator"))
        original_text = str(item.pop("original_text"))
        if product_id not in products:
            raise MergeError(f"产品不存在：{product_id}")
        products[product_id].update(item)
        for field_name, value in item.items():
            add_fact(_fact(
                row_ref=f"product:{product_id}", entity_id=product_id,
                entity_type="product", canonical_name=str(products[product_id]["name"]),
                field_id=f"product.{field_name}", value=value,
                disclosure_state="reported_value", source_id=source_id,
                locator=locator, original_text=original_text,
            ))

    for section, field_id in (("efficacy", "result.efficacy"), ("safety", "result.safety")):
        rows = cast(list[dict[str, Any]], report[section])
        row_ids = {str(row["row_id"]) for row in rows}
        for raw in cast(list[dict[str, Any]], manifest.get(section, [])):
            row = dict(raw)
            source_id = str(row.pop("source_id"))
            locator = cast(dict[str, Any], row.pop("locator"))
            original_text = str(row.pop("original_text"))
            row_id = str(row["row_id"])
            if row_id in row_ids:
                existing = next(item for item in rows if str(item["row_id"]) == row_id)
                if existing != row:
                    raise MergeError(f"结果行标识重复且内容不一致：{row_id}")
            else:
                rows.append(row)
                row_ids.add(row_id)
            value = row.get("value")
            state: _ResearchFactDisclosureState = (
                "not_publicly_disclosed"
                if value is None
                else "reported_zero" if value == 0
                else "reported_value"
            )
            fact = _fact(
                row_ref=f"{section}:{row_id}", entity_id=str(row["trial_id"]),
                entity_type="trial", canonical_name=str(row.get("endpoint") or row.get("term")),
                field_id=field_id, value=value, disclosure_state=state, source_id=source_id,
                locator=locator, original_text=original_text,
            )
            add_fact(fact)
            claim = ResearchClaim(
                claim_id=stable_id("curated-result-claim", source_id, row_id),
                claim_text=original_text,
                claim_kind="direct_evidence",
                fact_ids=(fact["fact_id"],),
            )
            add_claim(claim.model_dump(mode="json"))

    candidate = FreshAResearchContent.model_validate(base)
    payload = candidate.model_dump(mode="json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return compute_research_content_digest(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    digest = merge(args.base, args.manifest, args.output)
    print(json.dumps({"output": str(args.output), "content_digest": digest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
