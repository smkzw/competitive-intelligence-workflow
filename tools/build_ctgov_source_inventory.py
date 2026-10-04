#!/usr/bin/env python3
"""Build a compact, source-faithful CT.gov trial/intervention inventory.

Pinned capture receipts select exact raw pages. This helper does not accept
science, invent aliases, close a competitive universe, or emit portals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DRUG_TYPES = frozenset({"DRUG", "BIOLOGICAL"})
_STANDARD_THERAPY_MARKERS = (
    "standard of care",
    "standard therapy",
    "best supportive care",
    "placebo",
    "saline",
    "normal saline",
    "sham",
    "vehicle",
    "sugar pill",
)


class InventoryError(ValueError):
    """Pinned receipt or raw page identity is invalid."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o644)
    except FileExistsError as error:
        raise InventoryError(f"输出已存在；请选择新的版本化输出路径: {path}") from error
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InventoryError(f"{label}必须是对象")
    return value


def _parse_acquired_at(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise InventoryError("分页缺少 acquired_at")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InventoryError("acquired_at 缺少时区")
    return parsed


def _looks_standard_therapy(name: str) -> bool:
    lowered = name.casefold()
    return any(marker in lowered for marker in _STANDARD_THERAPY_MARKERS)


def _pinned_file(cas_root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else cas_root / path
    if not candidate.is_relative_to(cas_root) or ".." in candidate.parts:
        raise InventoryError("获取材料必须是当前CAS内的普通文件")
    current = cas_root
    for part in candidate.relative_to(cas_root).parts:
        current = current / part
        if current.is_symlink():
            raise InventoryError("获取材料或父目录为链接，不是钉定普通文件")
    if not candidate.is_file():
        raise InventoryError("获取材料不存在或不是普通文件")
    return candidate


def _load_pinned_bundle(
    cas_dir: Path,
    capture_receipt: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    cas_root = cas_dir.resolve()
    receipt_path = _pinned_file(cas_root, capture_receipt)
    receipt_raw = receipt_path.read_bytes()
    receipt_sha256 = _sha256_bytes(receipt_raw)
    receipt_parts = receipt_path.relative_to(cas_root).parts
    if receipt_parts[:3] == ("evidence", "raw", "sha256") and receipt_parts != (
        "evidence", "raw", "sha256", receipt_sha256[:2], receipt_sha256 + ".bin",
    ):
        raise InventoryError("获取回执摘要与内容寻址路径不一致")
    try:
        receipt = json.loads(receipt_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InventoryError("获取回执不是有效JSON") from error
    receipt = _require_mapping(receipt, "获取回执")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise InventoryError("获取回执格式无效")
    if receipt.get("projection_status") != "complete":
        raise InventoryError("逐研究派生未完成，不能建立来源清单")
    acquisition = _require_mapping(receipt.get("acquisition"), "acquisition")
    if (
        acquisition.get("status") != "complete"
        or acquisition.get("pagination_complete") is not True
    ):
        raise InventoryError("分页未完成，不能建立来源清单")
    pages = acquisition.get("pages")
    records = receipt.get("records")
    total = acquisition.get("total_count")
    if (
        not isinstance(pages, list)
        or not pages
        or not isinstance(records, list)
        or type(total) is not int
        or len(records) != total
    ):
        raise InventoryError("获取回执缺少完整分页或逐研究集合")

    page_metas: list[dict[str, Any]] = []
    study_rows: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    for number, page in enumerate(pages, 1):
        page_obj = _require_mapping(page, f"pages[{number - 1}]")
        if page_obj.get("page_number") != number:
            raise InventoryError("获取回执分页顺序不连续")
        acquired_at = _parse_acquired_at(page_obj.get("acquired_at"))
        ids = page_obj.get("study_ids")
        asset = _require_mapping(page_obj.get("raw_asset"), f"pages[{number - 1}].raw_asset")
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            raise InventoryError("获取回执研究ID无效")
        digest = asset.get("sha256")
        relative = asset.get("relative_path")
        byte_size = asset.get("byte_size")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise InventoryError("获取回执分页摘要无效")
        if not isinstance(relative, str) or not isinstance(byte_size, int):
            raise InventoryError("获取回执分页路径或大小无效")
        parts = PurePosixPath(relative).parts
        if parts != ("evidence", "raw", "sha256", digest[:2], digest + ".bin"):
            raise InventoryError("获取回执分页不在预期内容寻址路径")
        path = _pinned_file(cas_root, Path(relative))
        blob = path.read_bytes()
        if len(blob) != byte_size or _sha256_bytes(blob) != digest:
            raise InventoryError("获取回执与原始分页字节不一致")
        if all_ids.intersection(ids) or len(set(ids)) != len(ids):
            raise InventoryError("获取回执包含重复研究ID")
        all_ids.update(ids)
        try:
            payload = json.loads(blob.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InventoryError(f"原始分页不是有效JSON: {relative}") from error
        payload_obj = _require_mapping(payload, relative)
        studies = payload_obj.get("studies")
        if not isinstance(studies, list):
            raise InventoryError("CAS混有非原始分页；仅处理回执锁定分页")
        actual_ids = tuple(
            str(
                ((study.get("protocolSection") or {}).get("identificationModule") or {}).get(
                    "nctId"
                )
                or ""
            )
            if isinstance(study, dict)
            else ""
            for study in studies
        )
        if actual_ids != tuple(ids):
            raise InventoryError("获取回执研究ID与原始分页不一致")
        page_metas.append(
            {
                "page_number": number,
                "sha256": digest,
                "byte_size": byte_size,
                "relative_path": relative,
                "acquired_at": acquired_at.isoformat().replace("+00:00", "Z"),
                "study_ids": list(ids),
                "study_id_count": len(ids),
            }
        )
        for study_index, study in enumerate(studies):
            if not isinstance(study, dict):
                raise InventoryError("原始分页研究记录无效")
            study_rows.append(
                {
                    "page_number": number,
                    "study_index": study_index,
                    "page_sha256": digest,
                    "page_relative_path": relative,
                    "study": study,
                }
            )
    if len(all_ids) != total:
        raise InventoryError("获取回执唯一研究数与来源总量不一致")
    record_ids = [
        record.get("nct_id") if isinstance(record, dict) else None for record in records
    ]
    if (
        not all(isinstance(item, str) for item in record_ids)
        or len(set(record_ids)) != total
        or set(record_ids) != all_ids
    ):
        raise InventoryError("逐研究派生集合与原始分页研究ID不一致")
    receipt_meta = {
        "relative_path": PurePosixPath(*receipt_path.relative_to(cas_root).parts).as_posix(),
        "sha256": receipt_sha256,
        "byte_size": len(receipt_raw),
    }
    return receipt, receipt_meta, page_metas, study_rows


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _study_inventory_row(
    row: Mapping[str, Any], *, include_eligibility: bool = False,
) -> dict[str, Any]:
    study = row["study"]
    assert isinstance(study, dict)
    page_number = int(row["page_number"])
    study_index = int(row["study_index"])
    page_sha256 = str(row["page_sha256"])
    page_relative_path = str(row["page_relative_path"])
    proto = study.get("protocolSection")
    proto_obj = proto if isinstance(proto, dict) else {}
    ident = proto_obj.get("identificationModule")
    ident_obj = ident if isinstance(ident, dict) else {}
    nct = str(ident_obj.get("nctId") or "")
    title = str(ident_obj.get("briefTitle") or "")
    conditions_mod = proto_obj.get("conditionsModule")
    conditions_obj = conditions_mod if isinstance(conditions_mod, dict) else {}
    design = proto_obj.get("designModule")
    design_obj = design if isinstance(design, dict) else {}
    status_mod = proto_obj.get("statusModule")
    status_obj = status_mod if isinstance(status_mod, dict) else {}
    arms_mod = proto_obj.get("armsInterventionsModule")
    arms_obj = arms_mod if isinstance(arms_mod, dict) else {}
    outcomes_mod = proto_obj.get("outcomesModule")
    outcomes_obj = outcomes_mod if isinstance(outcomes_mod, dict) else {}
    refs_mod = proto_obj.get("referencesModule")
    refs_obj = refs_mod if isinstance(refs_mod, dict) else {}
    results = study.get("resultsSection")
    results_obj = results if isinstance(results, dict) else None
    enrollment = design_obj.get("enrollmentInfo")
    enrollment_obj = enrollment if isinstance(enrollment, dict) else {}
    enrollment_missing = "count" not in enrollment_obj
    enrollment_count = enrollment_obj.get("count")
    if enrollment_count is not None and type(enrollment_count) is not int:
        enrollment_count = None
        enrollment_missing = True

    arm_groups = arms_obj.get("armGroups")
    arm_group_list = arm_groups if isinstance(arm_groups, list) else []
    interventions = arms_obj.get("interventions")
    intervention_list = interventions if isinstance(interventions, list) else []

    arms_out: list[dict[str, Any]] = []
    arm_labels: dict[str, list[int]] = {}
    for arm_index, arm in enumerate(arm_group_list):
        if not isinstance(arm, dict):
            continue
        label = str(arm.get("label") or "")
        path = (
            f"$.studies[{study_index}].protocolSection.armsInterventionsModule"
            f".armGroups[{arm_index}]"
        )
        intervention_names = _string_list(arm.get("interventionNames"))
        arms_out.append(
            {
                "index": arm_index,
                "label": label,
                "type": str(arm.get("type") or ""),
                "intervention_names": intervention_names,
                "path": path,
                "intervention_names_path": f"{path}.interventionNames",
            }
        )
        if label.strip():
            arm_labels.setdefault(label, []).append(arm_index)

    interventions_out: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    raw_drug_names: list[str] = []
    drug_candidate = False
    for intervention_index, intervention in enumerate(intervention_list):
        if not isinstance(intervention, dict):
            continue
        itype = str(intervention.get("type") or "")
        name = str(intervention.get("name") or "")
        other_names = _string_list(intervention.get("otherNames"))
        labels = _string_list(intervention.get("armGroupLabels"))
        base_path = (
            f"$.studies[{study_index}].protocolSection.armsInterventionsModule"
            f".interventions[{intervention_index}]"
        )
        interventions_out.append(
            {
                "index": intervention_index,
                "type": itype,
                "name": name,
                "other_names": other_names,
                "arm_group_labels": labels,
                "path": base_path,
                "other_names_path": f"{base_path}.otherNames",
                "arm_group_labels_path": f"{base_path}.armGroupLabels",
            }
        )
        if itype.upper() in _DRUG_TYPES and name.strip():
            drug_candidate = True
            raw_drug_names.append(name)
        if not labels:
            edges.append(
                {
                    "basis": "intervention.armGroupLabels",
                    "intervention_index": intervention_index,
                    "intervention_name": name,
                    "intervention_type": itype,
                    "arm_label": "",
                    "arm_index": None,
                    "relationship_status": "missing_arm_labels",
                    "path": f"{base_path}.armGroupLabels",
                }
            )
        else:
            for label_index, label in enumerate(labels):
                candidate_indices = arm_labels.get(label, [])
                matched_arm_index = candidate_indices[0] if len(candidate_indices) == 1 else None
                edges.append(
                    {
                        "basis": "intervention.armGroupLabels",
                        "intervention_index": intervention_index,
                        "intervention_name": name,
                        "intervention_type": itype,
                        "arm_label": label,
                        "arm_index": matched_arm_index,
                        "candidate_arm_indices": candidate_indices,
                        "relationship_status": (
                            "bound" if matched_arm_index is not None
                            else "ambiguous_arm_label" if candidate_indices
                            else "unknown_arm_label"
                        ),
                        "path": f"{base_path}.armGroupLabels[{label_index}]",
                    }
                )

    for arm in arms_out:
        for name_index, declared in enumerate(arm["intervention_names"]):
            edges.append(
                {
                    "basis": "armGroup.interventionNames",
                    "intervention_index": None,
                    "intervention_name": declared,
                    "intervention_type": "",
                    "arm_label": arm["label"],
                    "arm_index": arm["index"],
                    "relationship_status": "arm_declared_intervention_name",
                    "path": f"{arm['intervention_names_path']}[{name_index}]",
                }
            )

    primary = outcomes_obj.get("primaryOutcomes")
    secondary = outcomes_obj.get("secondaryOutcomes")
    other = outcomes_obj.get("otherOutcomes")
    references = refs_obj.get("references")
    reference_list = references if isinstance(references, list) else []
    reference_counts: dict[str, int] = {}
    for ref in reference_list:
        if not isinstance(ref, dict):
            continue
        ref_type = str(ref.get("type") or "UNKNOWN")
        reference_counts[ref_type] = reference_counts.get(ref_type, 0) + 1
    results_om = []
    if results_obj is not None:
        om_mod = results_obj.get("outcomeMeasuresModule")
        if isinstance(om_mod, dict):
            measures = om_mod.get("outcomeMeasures")
            if isinstance(measures, list):
                results_om = measures

    proposal = _innovation_proposal(
        nct_id=nct,
        interventions=interventions_out,
        drug_candidate=drug_candidate,
        raw_drug_names=raw_drug_names,
    )
    projection = {
        "nct_id": nct,
        "title": title,
        "conditions": _string_list(conditions_obj.get("conditions")),
        "keywords": _string_list(conditions_obj.get("keywords")),
        "study_type": str(design_obj.get("studyType") or ""),
        "phases": _string_list(design_obj.get("phases")),
        "overall_status": str(status_obj.get("overallStatus") or ""),
        "enrollment": {
            "count": enrollment_count,
            "type": (
                str(enrollment_obj["type"])
                if isinstance(enrollment_obj.get("type"), str)
                else None
            ),
            "missing_count": enrollment_missing,
            "path": (
                f"$.studies[{study_index}].protocolSection.designModule.enrollmentInfo"
            ),
        },
        "arms": [
            {
                "index": arm["index"],
                "label": arm["label"],
                "type": arm["type"],
                "intervention_names": arm["intervention_names"],
                "path": arm["path"],
            }
            for arm in arms_out
        ],
        "interventions": interventions_out,
        "arm_intervention_edges": edges,
        "raw_drug_names": sorted(set(raw_drug_names)),
        "drug_candidate_flag": drug_candidate,
        "innovation_proposal": proposal,
        "outcome_availability": {
            "primary_outcome_count": len(primary) if isinstance(primary, list) else 0,
            "secondary_outcome_count": len(secondary) if isinstance(secondary, list) else 0,
            "other_outcome_count": len(other) if isinstance(other, list) else 0,
            "has_results_flag": bool(study.get("hasResults")),
            "has_results_section": results_obj is not None,
            "results_outcome_measure_count": len(results_om),
            "reference_total": len(reference_list),
            "reference_counts_by_type": dict(sorted(reference_counts.items())),
            "locators": {
                "outcomes_module": (
                    f"$.studies[{study_index}].protocolSection.outcomesModule"
                ),
                "references_module": (
                    f"$.studies[{study_index}].protocolSection.referencesModule"
                ),
                "results_section": (
                    f"$.studies[{study_index}].resultsSection"
                    if results_obj is not None
                    else None
                ),
            },
        },
        "source_locator": {
            "page_number": page_number,
            "study_index": study_index,
            "page_sha256": page_sha256,
            "page_relative_path": page_relative_path,
            "study_path": f"$.studies[{study_index}]",
        },
    }
    if include_eligibility:
        module = proto_obj.get("eligibilityModule", {})
        criteria = module.get("eligibilityCriteria") if isinstance(module, dict) else module
        if not isinstance(module, dict):
            status = "parse_error"
        elif "eligibilityCriteria" not in module:
            status = "source_field_missing"
        elif criteria is None:
            status = "source_value_null"
        elif not isinstance(criteria, str):
            status = "parse_error"
        else:
            status = "reported_value" if criteria.strip() else "source_text_empty"
        projection["eligibility_criteria"] = {
            "status": status, "value": criteria,
            "path": (
                f"$.studies[{study_index}].protocolSection.eligibilityModule.eligibilityCriteria"
            ),
        }
    return projection


def _innovation_proposal(
    *,
    nct_id: str,
    interventions: Sequence[Mapping[str, Any]],
    drug_candidate: bool,
    raw_drug_names: Sequence[str],
) -> dict[str, Any]:
    """Source-local proposal only; never marks innovative eligibility accepted."""
    if not interventions:
        return {
            "status": "unresolved_innovation",
            "reasons": ["no_interventions_reported"],
            "accepted": False,
            "nct_id": nct_id,
        }
    types = {str(item.get("type") or "").upper() for item in interventions}
    names = [str(item.get("name") or "") for item in interventions]
    if drug_candidate:
        non_standard = [name for name in raw_drug_names if not _looks_standard_therapy(name)]
        only_standard = bool(raw_drug_names) and not non_standard
        if only_standard:
            return {
                "status": "proposed_standard_therapy_or_control",
                "reasons": ["drug_or_biological_names_match_standard_therapy_markers"],
                "raw_drug_names": list(raw_drug_names),
                "accepted": False,
                "nct_id": nct_id,
            }
        reasons = ["source_drug_or_biological_intervention_present"]
        if any(_looks_standard_therapy(name) for name in names):
            reasons.append("also_contains_standard_therapy_or_control_labels")
        return {
            "status": "proposed_innovative_inclusion_candidate",
            "reasons": reasons,
            "raw_drug_names": sorted(set(non_standard)),
            "accepted": False,
            "nct_id": nct_id,
        }
    if types and types.isdisjoint(_DRUG_TYPES):
        return {
            "status": "proposed_non_drug",
            "reasons": ["no_drug_or_biological_intervention_type"],
            "intervention_types": sorted(types),
            "accepted": False,
            "nct_id": nct_id,
        }
    return {
        "status": "unresolved_innovation",
        "reasons": ["intervention_types_present_but_drug_candidate_not_established"],
        "accepted": False,
        "nct_id": nct_id,
    }


def _alias_collections(
    studies: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build otherNames→name suggestions; conflicting aliases stay unresolved."""
    grouped: dict[str, dict[str, Any]] = {}
    for study in studies:
        nct = str(study["nct_id"])
        page_number = int(study["source_locator"]["page_number"])
        study_index = int(study["source_locator"]["study_index"])
        for intervention in study["interventions"]:
            name = str(intervention.get("name") or "").strip()
            if not name:
                continue
            other_names = intervention.get("other_names")
            if not isinstance(other_names, list):
                continue
            for other_index, alias in enumerate(other_names):
                if not isinstance(alias, str) or not alias.strip():
                    continue
                alias_key = alias.casefold()
                source = {
                    "nct_id": nct,
                    "alias": alias,
                    "name": name,
                    "page_number": page_number,
                    "study_index": study_index,
                    "intervention_index": intervention["index"],
                    "path": (
                        f"$.studies[{study_index}].protocolSection.armsInterventionsModule"
                        f".interventions[{intervention['index']}].otherNames[{other_index}]"
                    ),
                    "name_path": (
                        f"$.studies[{study_index}].protocolSection.armsInterventionsModule"
                        f".interventions[{intervention['index']}].name"
                    ),
                }
                bucket = grouped.setdefault(
                    alias_key,
                    {
                        "alias_key": alias_key,
                        "alias_spellings": [],
                        "targets": {},
                    },
                )
                spellings: list[str] = bucket["alias_spellings"]
                if alias not in spellings:
                    spellings.append(alias)
                target_key = name.casefold()
                target = bucket["targets"].setdefault(
                    target_key,
                    {"name": name, "name_spellings": [], "sources": []},
                )
                if name not in target["name_spellings"]:
                    target["name_spellings"].append(name)
                target["sources"].append(source)

    canonical: dict[str, Any] = {}
    unresolved: list[dict[str, Any]] = []
    for alias_key in sorted(grouped):
        bucket = grouped[alias_key]
        targets = bucket["targets"]
        alias_spelling = sorted(bucket["alias_spellings"])[0]
        if len(targets) == 1:
            target = next(iter(targets.values()))
            canonical[alias_spelling] = {
                "name": target["name"],
                "alias_spellings": bucket["alias_spellings"],
                "sources": target["sources"],
            }
            continue
        unresolved.append(
            {
                "alias": alias_spelling,
                "alias_key": alias_key,
                "alias_spellings": bucket["alias_spellings"],
                "candidates": [
                    {
                        "name": target["name"],
                        "name_spellings": target["name_spellings"],
                        "sources": target["sources"],
                    }
                    for target_key, target in sorted(targets.items())
                ],
                "reason": "conflicting_otherNames_to_name_mappings",
            }
        )
    return canonical, unresolved


def build_inventory(
    *,
    cas_dir: Path,
    capture_receipt: Path,
    output: Path | None = None,
    replay_command: str | None = None,
) -> dict[str, Any]:
    receipt, receipt_meta, page_metas, study_rows = _load_pinned_bundle(cas_dir, capture_receipt)
    acquisition = _require_mapping(receipt.get("acquisition"), "acquisition")
    studies = [_study_inventory_row(row) for row in study_rows]
    studies.sort(key=lambda item: item["nct_id"])
    canonical_by_alias, unresolved_aliases = _alias_collections(studies)

    proposed_inclusion = [
        {
            "nct_id": study["nct_id"],
            "raw_drug_names": study["raw_drug_names"],
            "reasons": study["innovation_proposal"]["reasons"],
        }
        for study in studies
        if study["innovation_proposal"]["status"] == "proposed_innovative_inclusion_candidate"
    ]
    proposed_non_drug = [
        {
            "nct_id": study["nct_id"],
            "intervention_types": study["innovation_proposal"].get("intervention_types", []),
            "reasons": study["innovation_proposal"]["reasons"],
        }
        for study in studies
        if study["innovation_proposal"]["status"] == "proposed_non_drug"
    ]
    proposed_standard = [
        {
            "nct_id": study["nct_id"],
            "raw_drug_names": study["raw_drug_names"],
            "reasons": study["innovation_proposal"]["reasons"],
        }
        for study in studies
        if study["innovation_proposal"]["status"] == "proposed_standard_therapy_or_control"
    ]
    unresolved_innovation = [
        {
            "nct_id": study["nct_id"],
            "reasons": study["innovation_proposal"]["reasons"],
        }
        for study in studies
        if study["innovation_proposal"]["status"] == "unresolved_innovation"
    ]

    acquired_values = [str(page["acquired_at"]) for page in page_metas]
    source_set_sha256 = _sha256_bytes(
        _canonical_json(
            {
                "receipt_sha256": receipt_meta["sha256"],
                "pages": [
                    {
                        "page_number": page["page_number"],
                        "sha256": page["sha256"],
                        "byte_size": page["byte_size"],
                        "study_ids": page["study_ids"],
                    }
                    for page in page_metas
                ],
            }
        )
    )
    gaps = [
        "universe_not_closed_public_registry_query_only",
        "scientific_acceptance_not_performed",
        "innovative_eligibility_not_accepted",
        "alias_suggestions_are_source_otherNames_only",
        "china_registry_and_literature_closure_not_in_this_inventory",
    ]
    if unresolved_aliases:
        gaps.append("conflicting_aliases_unresolved")
    if unresolved_innovation:
        gaps.append("innovation_status_unresolved_for_some_studies")
    if any(study["enrollment"]["missing_count"] for study in studies):
        gaps.append("enrollment_count_missing_for_some_studies")

    if replay_command is None:
        replay_command = (
            "python tools/build_ctgov_source_inventory.py"
            f" --cas-dir {cas_dir}"
            f" --capture-receipt {capture_receipt}"
            f" --output {output if output is not None else 'INVENTORY.json'}"
        )

    inventory: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "inventory_id": "r24-93-ctgov-source-inventory",
        "scientific_acceptance": "not_accepted",
        "universe_closed": False,
        "accepted": False,
        "released": False,
        "source": {
            "cas_dir": str(cas_dir),
            "capture_receipt": receipt_meta,
            "condition": acquisition.get("condition"),
            "diagnostic": acquisition.get("diagnostic"),
            "limitation": receipt.get("limitation"),
            "temporal_scope": acquisition.get("temporal_scope"),
            "total_count": acquisition.get("total_count"),
            "pagination_complete": True,
            "universe_closed": bool(acquisition.get("universe_closed"))
            if isinstance(acquisition.get("universe_closed"), bool)
            else False,
            "pages": [
                {
                    "page_number": page["page_number"],
                    "sha256": page["sha256"],
                    "byte_size": page["byte_size"],
                    "relative_path": page["relative_path"],
                    "acquired_at": page["acquired_at"],
                    "study_id_count": page["study_id_count"],
                }
                for page in page_metas
            ],
            "source_set_sha256": source_set_sha256,
            "fetched_at": {
                "earliest": min(acquired_values),
                "latest": max(acquired_values),
            },
        },
        "replay_command": replay_command,
        "counts": {
            "studies": len(studies),
            "drug_candidate_studies": sum(1 for study in studies if study["drug_candidate_flag"]),
            "proposed_innovative_inclusion_candidates": len(proposed_inclusion),
            "proposed_non_drug": len(proposed_non_drug),
            "proposed_standard_therapy_or_control": len(proposed_standard),
            "unresolved_innovation": len(unresolved_innovation),
            "canonical_aliases": len(canonical_by_alias),
            "unresolved_aliases": len(unresolved_aliases),
            "studies_with_results_section": sum(
                1 for study in studies if study["outcome_availability"]["has_results_section"]
            ),
            "missing_enrollment_count": sum(
                1 for study in studies if study["enrollment"]["missing_count"]
            ),
        },
        "canonical_by_alias": canonical_by_alias,
        "unresolved_aliases": unresolved_aliases,
        "proposals": {
            "innovative_inclusion_candidates": proposed_inclusion,
            "non_drug": proposed_non_drug,
            "standard_therapy_or_control": proposed_standard,
            "unresolved_innovation": unresolved_innovation,
            "note": (
                "drug_candidate_flag and proposals are source-local suggestions only; "
                "innovative eligibility is not accepted"
            ),
        },
        "studies": studies,
        "gaps": gaps,
    }
    if output is not None:
        _write_exclusive(output, inventory)
    return inventory


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a compact CT.gov source inventory from a pinned capture receipt",
    )
    parser.add_argument("--cas-dir", required=True, type=Path, help="CAS root directory")
    parser.add_argument(
        "--capture-receipt",
        required=True,
        type=Path,
        help="Capture receipt path (absolute or relative to cas-dir)",
    )
    parser.add_argument("--output", required=True, type=Path, help="Exclusive JSON output path")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        inventory = build_inventory(
            cas_dir=args.cas_dir,
            capture_receipt=args.capture_receipt,
            output=args.output,
            replay_command=(
                "python tools/build_ctgov_source_inventory.py"
                f" --cas-dir {args.cas_dir}"
                f" --capture-receipt {args.capture_receipt}"
                f" --output {args.output}"
            ),
        )
    except InventoryError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "output": str(args.output),
                "studies": inventory["counts"]["studies"],
                "source_set_sha256": inventory["source"]["source_set_sha256"],
                "scientific_acceptance": inventory["scientific_acceptance"],
                "universe_closed": inventory["universe_closed"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
