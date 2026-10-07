"""Joint replay of two pinned, already source-checked identity source-sets.

Bounded replay glue only. It verifies both pinned source-sets and the listed
history bytes, copies only the declared exact bytes into a new source root,
prefixes the source/entity reference keys with the input label, and calls the
existing ``materialize_identity_sources.materialize`` exactly once on the merged
spec. It never rewrites scientific names, aliases, dates, predicates,
jurisdictions, scopes, quotes, URLs or product ids, never adds sources, and
never claims scientific, current, China or clinical acceptance.

After the joint candidate exists, each input is independently materialized from
its original pinned spec/root and every declared product header is compared
(semantic fields only, because reference-key-scoped ids legitimately differ).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from ci_workflow.domain.entities import EntityIdentity, EntityType
from ci_workflow.reports.common.identity_projection import load_identity_context
from ci_workflow.sources.connectors.public_pdf_availability import PublicPdfAvailabilityWitness
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import source_json_decoder
from tools.materialize_identity_sources import materialize

_LABEL = re.compile(r"[a-z0-9][a-z0-9-]*")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SOURCE_FIELDS = frozenset({
    "key", "filename", "sha256", "page", "paragraph", "url", "public_pdf_availability",
})
_ENTITY_FIELDS = frozenset({
    "key", "entity_type", "canonical_name", "identity_basis", "aliases",
    "official_chinese_name", "name_source_key",
})
_RELATION_FIELDS = frozenset({
    "subject", "object", "predicate", "source_key", "jurisdiction",
    "authorization_scope", "effective_from", "effective_until", "observed_at",
})
_MERGE_NOTE = (
    "联合重放：仅对两组已复核来源集取并集，并对来源/实体引用键加命名空间前缀；"
    "科学名称、别名、日期、判断、辖区、范围、原文、URL 与产品编号保持原样。"
)
_MERGE_LIMITATION = (
    "联合候选仅覆盖两组已复核来源集的并集，不构成当前性、中国监管状态、科学或临床接受；"
    "获取时间仅为离线重放导入时点，不是首次公开或生效日期。"
)
_COMPARISON_FIELDS = {
    "sources": ("source_sha256", "raw_sha256", "url", "page", "original_text",
                "observed_publicly_available_at"),
    "companies": ("legal_entity_id", "legal_entity_name", "group_entity_id",
                  "group_chain_entity_ids", "role", "jurisdiction", "authorization_scope",
                  "effective_from", "effective_until", "observed_at", "label"),
    "relations": ("subject_entity_id", "predicate", "object_entity_id", "jurisdiction",
                  "authorization_scope", "effective_from", "effective_until", "observed_at"),
}


@dataclass(frozen=True)
class IdentitySourceInput:
    """One pinned input: source root, source-set file and the expected digest."""

    label: str
    source_root: Path
    source_set: Path
    expected_sha256: str


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _digest_json(value: Any) -> str:
    return _sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _text(item: dict[str, Any], field: str, where: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} 缺少有效文本字段：{field}")
    return value


def _fields(item: Any, allowed: frozenset[str], where: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"{where} 必须是对象")
    unknown = set(item) - allowed
    if unknown:
        raise ValueError(f"{where} 含未定义字段，拒绝静默丢弃：{sorted(unknown)}")
    return item


def _logical_path(path: Path) -> str:
    """Receipt-facing path that never leaks an absolute user directory."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return f"<external>/{resolved.name}"


def _write_exclusive(path: Path, content: bytes) -> None:
    if path.is_symlink() or path.exists():
        raise ValueError(f"拒绝覆盖已存在文件：{path.name}")
    with path.open("xb") as stream:
        stream.write(content)


def _prepare(source: IdentitySourceInput) -> dict[str, Any]:
    """Verify one pinned input and return its prefix-remapped declaration."""
    if not _LABEL.fullmatch(source.label):
        raise ValueError(f"来源集标签不合法：{source.label!r}")
    raw = source.source_set.read_bytes()
    actual = _sha256(raw)
    if actual != source.expected_sha256:
        raise ValueError(f"来源集摘要与固定值不一致：{source.label}")
    spec = source_json_decoder().decode(raw.decode("utf-8"))
    if not isinstance(spec, dict) or spec.get("candidate_only") is not True:
        raise ValueError(f"来源集必须是 candidate_only 对象：{source.label}")
    raw_sources = spec.get("sources")
    raw_entities = spec.get("entities")
    raw_relations = spec.get("relations")
    raw_products = spec.get("product_entity_ids")
    if (not isinstance(raw_sources, list) or not isinstance(raw_entities, list)
            or not isinstance(raw_relations, list) or not isinstance(raw_products, dict)):
        raise ValueError(f"来源集结构不完整：{source.label}")
    prefix = f"{source.label}:"
    declarations: list[tuple[str, str, bool]] = []
    sources: list[dict[str, Any]] = []
    source_keys: set[str] = set()
    for entry in raw_sources:
        item = _fields(entry, _SOURCE_FIELDS, f"{source.label} sources")
        key = _text(item, "key", f"{source.label} sources")
        digest = _text(item, "sha256", f"{source.label} sources")
        if not _DIGEST.fullmatch(digest):
            raise ValueError(f"来源摘要不合法：{source.label}:{key}")
        if key in source_keys:
            raise ValueError(f"来源键重复：{source.label}:{key}")
        source_keys.add(key)
        declarations.append((_text(item, "filename", f"{source.label} sources"), digest, True))
        witness_raw = item.get("public_pdf_availability")
        if witness_raw is not None:
            witness = PublicPdfAvailabilityWitness.model_validate(witness_raw)
            if witness.receipt_asset is None:
                raise ValueError(f"公开可用性见证缺少可重开回执：{source.label}:{key}")
            declarations.append((witness.expected_raw_asset.relative_path,
                                 witness.expected_raw_asset.sha256, False))
            declarations.append((witness.receipt_asset.relative_path,
                                 witness.receipt_asset.sha256, False))
        sources.append({**item, "key": prefix + key})
    entities: list[dict[str, Any]] = []
    entity_keys: set[str] = set()
    for entry in raw_entities:
        item = _fields(entry, _ENTITY_FIELDS, f"{source.label} entities")
        key = _text(item, "key", f"{source.label} entities")
        if key in entity_keys:
            raise ValueError(f"实体键重复：{source.label}:{key}")
        entity_keys.add(key)
        _text(item, "entity_type", f"{source.label} entities")
        _text(item, "canonical_name", f"{source.label} entities")
        _text(item, "identity_basis", f"{source.label} entities")
        aliases = item.get("aliases", [])
        if (not isinstance(aliases, list)
                or any(not isinstance(alias, str) or not alias.strip() for alias in aliases)):
            raise ValueError(f"实体别名必须是文本列表：{source.label}:{key}")
        remapped = {**item, "key": prefix + key}
        if "name_source_key" in item:
            name_key = _text(item, "name_source_key", f"{source.label} entities")
            if name_key not in source_keys:
                raise ValueError(f"名称来源键未定义：{source.label}:{key}")
            remapped["name_source_key"] = prefix + name_key
        entities.append(remapped)
    relations: list[dict[str, Any]] = []
    for entry in raw_relations:
        item = _fields(entry, _RELATION_FIELDS, f"{source.label} relations")
        for field in ("subject", "object", "predicate", "source_key"):
            _text(item, field, f"{source.label} relations")
        if item["subject"] not in entity_keys or item["object"] not in entity_keys:
            raise ValueError(f"关系端点未定义：{source.label}")
        if item["source_key"] not in source_keys:
            raise ValueError(f"关系来源未定义：{source.label}")
        relations.append({**item, "subject": prefix + item["subject"],
                          "object": prefix + item["object"],
                          "source_key": prefix + item["source_key"]})
    product_ids: dict[str, str] = {}
    for product_id, ref in raw_products.items():
        if (not isinstance(product_id, str) or not product_id.strip()
                or not isinstance(ref, str) or ref not in entity_keys):
            raise ValueError(f"产品映射不合法：{source.label}")
        product_ids[product_id] = prefix + ref
    file_digests: dict[str, str] = {}
    for relative, digest, _ in declarations:
        file_digests.setdefault(relative, digest)
    declared_files = [{"relative_path": relative, "sha256": digest}
                      for relative, digest in sorted(file_digests.items())]
    return {
        "label": source.label, "prefix": prefix,
        "source_root": source.source_root, "source_set": source.source_set,
        "source_set_sha256": actual,
        "source_root_logical": _logical_path(source.source_root),
        "source_set_logical": _logical_path(source.source_set),
        "declared_metadata": {key: value for key, value in spec.items() if key not in {
            "candidate_only", "sources", "entities", "relations", "product_entity_ids"}},
        "declared_files": declared_files, "declarations": declarations,
        "sources": sources, "entities": entities, "relations": relations,
        "product_entity_ids": product_ids,
    }


def _entity_identity(item: dict[str, Any]) -> tuple[EntityIdentity, dict[str, Any]]:
    name_key = item.get("name_source_key")
    identity = EntityIdentity.create(
        EntityType(item["entity_type"]), item["canonical_name"], item["identity_basis"],
        aliases=tuple(item.get("aliases", ())),
        official_chinese_name=item.get("official_chinese_name"),
        name_evidence_fragment_id=f"pending:{name_key}" if name_key else None,
    )
    payload = {field: item.get(field) for field in (
        "entity_type", "canonical_name", "identity_basis", "aliases",
        "official_chinese_name", "name_source_key")}
    return identity, payload


def _check_conflicts(prepared: Sequence[dict[str, Any]]) -> None:
    """Contradictory product mappings or scientific identities fail closed."""
    payloads: dict[str, tuple[dict[str, Any], str]] = {}
    identities: dict[str, EntityIdentity] = {}
    types_by_basis: dict[str, set[str]] = {}
    for entry in prepared:
        for item in entry["entities"]:
            identity, payload = _entity_identity(item)
            previous = payloads.get(identity.entity_id)
            if previous is not None and previous[0] != payload:
                raise ValueError(
                    f"科学身份冲突：{previous[1]} 与 {item['key']} 对同一身份给出不同内容")
            payloads[identity.entity_id] = (payload, item["key"])
            identities[item["key"]] = identity
            types_by_basis.setdefault(item["identity_basis"], set()).add(item["entity_type"])
    for basis, types in types_by_basis.items():
        if len(types) > 1:
            raise ValueError(f"科学身份冲突：同一身份依据声明了不同类型：{basis}")
    product_owner: dict[str, tuple[str, dict[str, Any]]] = {}
    for entry in prepared:
        for product_id, ref in entry["product_entity_ids"].items():
            identity = identities[ref]
            payload = payloads[identity.entity_id][0]
            owner = product_owner.get(product_id)
            if owner is not None and (owner[0] != identity.entity_id or owner[1] != payload):
                raise ValueError(f"冲突的产品映射：{product_id}")
            product_owner[product_id] = (identity.entity_id, payload)


def _plan_files(prepared: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    planned: dict[str, dict[str, Any]] = {}
    for entry in prepared:
        for relative, digest, pdf_required in entry["declarations"]:
            pure = PurePosixPath(relative)
            if (not relative.strip() or pure.is_absolute() or ".." in pure.parts
                    or "\\" in relative):
                raise ValueError(f"来源路径必须留在来源根内：{relative!r}")
            existing = planned.get(relative)
            if existing is None:
                planned[relative] = {"root": entry["source_root"], "relative": relative,
                                     "sha256": digest, "pdf": pdf_required}
            elif existing["sha256"] != digest:
                raise ValueError(f"同一来源路径固定了不同字节：{relative}")
    return list(planned.values())


def _read_verified(entry: dict[str, Any]) -> bytes:
    store = ContentAddressedStore(entry["root"])
    raw = store.resolve_relative(entry["relative"]).read_bytes()
    if _sha256(raw) != entry["sha256"]:
        raise ValueError(f"来源字节与固定摘要不一致：{entry['relative']}")
    if entry["pdf"] and not raw.startswith(b"%PDF-"):
        raise ValueError(f"固定来源不是 PDF 字节：{entry['relative']}")
    return raw


def _staged_files(planned: Sequence[dict[str, Any]], staging: Path) -> list[dict[str, Any]]:
    staging.mkdir(parents=False, exist_ok=False)
    staged: list[dict[str, Any]] = []
    for entry in planned:
        raw = _read_verified(entry)
        destination = staging / PurePosixPath(entry["relative"])
        if destination.is_symlink() or destination.exists():
            raise ValueError(f"暂存目标已存在，拒绝覆盖：{entry['relative']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.resolve().is_relative_to(staging.resolve()):
            raise ValueError(f"暂存路径越界：{entry['relative']}")
        with destination.open("xb") as stream:
            stream.write(raw)
        if _sha256(destination.read_bytes()) != entry["sha256"]:
            raise ValueError(f"暂存回读与固定摘要不一致：{entry['relative']}")
        staged.append({"relative_path": entry["relative"], "sha256": entry["sha256"],
                       "byte_size": len(raw)})
    return staged


def _merged_source_set(prepared: Sequence[dict[str, Any]]) -> dict[str, Any]:
    product_ids: dict[str, str] = {}
    for entry in prepared:
        for product_id, ref in entry["product_entity_ids"].items():
            # Duplicates passed `_check_conflicts` only as the same verified entity.
            product_ids.setdefault(product_id, ref)
    return {
        "candidate_only": True,
        "joint_merge": {
            "schema_version": "joint-identity-source-set-1",
            "inputs": [{"label": entry["label"],
                        "source_set_sha256": entry["source_set_sha256"]}
                       for entry in prepared],
            "key_prefix": {entry["label"]: entry["prefix"] for entry in prepared},
            "note": _MERGE_NOTE,
        },
        "limitation": _MERGE_LIMITATION,
        "sources": [item for entry in prepared for item in entry["sources"]],
        "entities": [item for entry in prepared for item in entry["entities"]],
        "relations": [item for entry in prepared for item in entry["relations"]],
        "product_entity_ids": product_ids,
    }


def normalize_product_header(header: dict[str, Any]) -> dict[str, Any]:
    """Drop run-local ids so two materializations of the same facts compare equal.

    Entity ids derive from the declared scientific identity basis and must stay
    equal; fragment/version/relation ids and acquisition clocks legitimately
    differ because reference keys are namespaced per input.
    """
    companies = []
    for company in header["companies"]:
        companies.append({
            **{field: company.get(field) for field in _COMPARISON_FIELDS["companies"]},
            "group_relations": sorted(
                ({field: relation.get(field) for field in _COMPARISON_FIELDS["relations"]}
                 for relation in company.get("group_relations", [])),
                key=lambda item: _digest_json(item),
            ),
        })
    return {
        "entity_id": header["entity_id"],
        "display_name": header["display_name"],
        "original_name": header["original_name"],
        "aliases": header["aliases"],
        "company_label": header["company_label"],
        "targets": sorted(
            ({"entity_id": item["entity_id"], "name": item["name"]}
             for item in header["targets"]),
            key=lambda item: (item["entity_id"], item["name"]),
        ),
        "companies": sorted(companies, key=_digest_json),
        "unresolved_relations": sorted(item["reason"] for item in header["unresolved_relations"]),
        "sources": sorted(
            ({field: item.get(field) for field in _COMPARISON_FIELDS["sources"]}
             for item in header["sources"]),
            key=_digest_json,
        ),
    }


def compare_product_headers(product_id: str, joint: dict[str, Any],
                            independent: dict[str, Any]) -> None:
    if normalize_product_header(joint) != normalize_product_header(independent):
        raise ValueError(f"联合候选与独立材料化输入不一致：{product_id}")


def merge_identity_source_sets(inputs: Sequence[IdentitySourceInput], output: Path, *,
                               cutoff: datetime | None = None) -> dict[str, Any]:
    if len(inputs) != 2:
        raise ValueError("联合重放只接受两组固定来源集")
    if len({item.label for item in inputs}) != len(inputs):
        raise ValueError("来源集标签必须唯一")
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise ValueError("输出必须是不存在的新目录，拒绝覆盖")
    prepared = [_prepare(item) for item in inputs]
    for entry in prepared:
        if output.resolve().is_relative_to(entry["source_root"].resolve()):
            raise ValueError("输出不得写入只读来源根")
    _check_conflicts(prepared)
    planned = _plan_files(prepared)
    for entry in planned:
        _read_verified(entry)  # All input bytes verified before the output tree exists.
    staging = output / "sources"
    output.mkdir(parents=True, exist_ok=False)
    staged = _staged_files(planned, staging)
    merged = _merged_source_set(prepared)
    merged_bytes = json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    merged_path = output / "joint-identity-source-set-v1.json"
    _write_exclusive(merged_path, merged_bytes)
    merged_sha = _sha256(merged_bytes)
    joint_receipt = materialize(staging, merged_path, merged_sha, output / "candidate")
    baseline_receipts: dict[str, dict[str, Any]] = {}
    for entry in prepared:
        baseline_receipts[entry["label"]] = materialize(
            entry["source_root"], entry["source_set"], entry["source_set_sha256"],
            output / "independent" / entry["label"])
    moment = cutoff if cutoff is not None else datetime.now(UTC)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("核对截止时点必须包含时区")
    joint = load_identity_context(output / "candidate", joint_receipt["graph_asset"])
    joint_product_ids = sorted(joint.product_entity_ids)
    if not joint_product_ids:
        raise ValueError("联合候选没有声明产品")
    joint_headers = joint.project(tuple(joint_product_ids), cutoff=moment)
    comparisons: list[dict[str, Any]] = []
    declared_products: set[str] = set()
    for entry in prepared:
        label = entry["label"]
        baseline = load_identity_context(
            output / "independent" / label, baseline_receipts[label]["graph_asset"])
        baseline_headers = baseline.project(tuple(sorted(baseline.product_entity_ids)),
                                            cutoff=moment)
        for product_id, baseline_header in baseline_headers.items():
            if product_id not in joint_headers:
                raise ValueError(f"联合候选缺少输入产品：{product_id}")
            if joint_headers[product_id]["entity_id"] != baseline_header["entity_id"]:
                raise ValueError(f"联合候选产品身份头与独立材料化输入不一致：{product_id}")
            compare_product_headers(product_id, joint_headers[product_id], baseline_header)
            declared_products.add(product_id)
            comparisons.append({
                "product_id": product_id, "baseline_label": label,
                "entity_id": baseline_header["entity_id"],
                "joint_normalized_sha256":
                    _digest_json(normalize_product_header(joint_headers[product_id])),
                "baseline_normalized_sha256":
                    _digest_json(normalize_product_header(baseline_header)),
                "normalized_equal": True,
            })
    if set(joint_product_ids) != declared_products:
        raise ValueError("联合候选产品集合与输入声明不一致")
    projection_path = output / "joint-identity-projection.json"
    _write_exclusive(projection_path, (
        json.dumps({"schema_version": "joint-identity-projection-1",
                    "cutoff": moment.isoformat(), "products": joint_headers},
                   ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"))
    receipt = {
        "schema_version": "joint-identity-merge-1",
        "acquisition_mode": "offline_replay_of_pinned_source_sets_not_live_access",
        "science_accepted": False,
        "current_promoted": False,
        "china_status_assessed": False,
        "cutoff": moment.isoformat(),
        "inputs": [{"label": entry["label"], "source_root": entry["source_root_logical"],
                    "source_set": entry["source_set_logical"],
                    "source_set_sha256": entry["source_set_sha256"],
                    "declared_files": entry["declared_files"],
                    "declared_metadata": entry["declared_metadata"]}
                   for entry in prepared],
        "staged_sources": {"relative_root": "sources", "files": staged},
        "merged_source_set": {"relative_path": merged_path.name, "sha256": merged_sha},
        "joint_candidate": {"relative_path": "candidate", "receipt": joint_receipt},
        "independent_baselines": {
            label: {"relative_path": f"independent/{label}", "receipt": receipt_entry}
            for label, receipt_entry in baseline_receipts.items()},
        "product_comparison": comparisons,
    }
    _write_exclusive(output / "joint-merge-receipt.json",
                     json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    return receipt


def _parse_input(value: str) -> IdentitySourceInput:
    parts = value.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("必须为 LABEL:SOURCE_ROOT:SOURCE_SET:SHA256")
    label, source_root, source_set, expected_sha256 = parts
    if not _LABEL.fullmatch(label) or not _DIGEST.fullmatch(expected_sha256):
        raise argparse.ArgumentTypeError("标签或摘要不符合合同")
    return IdentitySourceInput(label, Path(source_root), Path(source_set), expected_sha256)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, action="append", type=_parse_input,
                        metavar="LABEL:SOURCE_ROOT:SOURCE_SET:SHA256",
                        help="两组固定来源集，按并集顺序重复两次")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipt = merge_identity_source_sets(tuple(args.input), args.output)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
