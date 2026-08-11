from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker

JsonObject = dict[str, Any]
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")


class DesignContractError(ValueError):
    """设计来源包或当前运行验收合同不成立。"""


def _load_schema(path: Path) -> JsonObject:
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise DesignContractError(f"设计合同不是 JSON 对象：{path}")
    return cast(JsonObject, schema)


def canonical_json_sha256(value: JsonObject) -> str:
    """返回跨运行稳定的 UTF-8 JSON 规范化摘要。"""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_schema(instance: JsonObject, schema_path: Path) -> None:
    validator = Draft202012Validator(
        _load_schema(schema_path),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise DesignContractError(details)


def _require_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise DesignContractError(f"{label}存在重复稳定标识")


def validate_source_pack(source_pack: JsonObject, schema_path: Path) -> None:
    """验证设计来源包内的事实分类及跨载体声明一致性。"""

    _validate_schema(source_pack, schema_path)

    tokens = cast(list[JsonObject], source_pack["tokens"])
    claims = cast(list[JsonObject], source_pack["claims"])
    occurrences = cast(list[JsonObject], source_pack["occurrences"])
    notes = cast(list[JsonObject], source_pack["notes"])

    token_ids = [cast(str, token["token_id"]) for token in tokens]
    claim_ids = [cast(str, claim["claim_id"]) for claim in claims]
    _require_unique(token_ids, "数字 token")
    _require_unique(claim_ids, "定量声明")

    token_id_set = set(token_ids)
    token_by_id = {cast(str, token["token_id"]): token for token in tokens}
    claim_by_id = {cast(str, claim["claim_id"]): claim for claim in claims}
    for claim in claims:
        source_token_ids = cast(list[str], claim["source_token_ids"])
        unknown_tokens = set(source_token_ids) - token_id_set
        if unknown_tokens:
            raise DesignContractError(
                f"定量声明 {claim['claim_id']} 引用了不存在的 token：{sorted(unknown_tokens)}"
            )
        referenced_tokens = [token_by_id[token_id] for token_id in source_token_ids]
        if any(token["category"] != "audience_fact" for token in referenced_tokens):
            raise DesignContractError(f"定量声明 {claim['claim_id']} 只能引用 audience_fact token")
        if not any(
            token["original_value"] == claim["value"]
            and token["unit"] == claim["unit"]
            and token["denominator"] == claim["denominator"]
            for token in referenced_tokens
        ):
            raise DesignContractError(
                f"定量声明 {claim['claim_id']} 的值、单位或分母与来源事实不一致"
            )

    for occurrence in occurrences:
        claim_id = cast(str, occurrence["claim_id"])
        if claim_id not in claim_by_id:
            raise DesignContractError(f"载体位置引用了不存在的声明：{claim_id}")
        if occurrence["normalized_value"] != claim_by_id[claim_id]["normalized_value"]:
            raise DesignContractError(f"声明 {claim_id} 在不同载体上的归一化值不一致")

    for note in notes:
        slide_id = cast(str, note["slide_id"])
        note_claim_ids = cast(list[str], note["claim_ids"])
        claim_spans = cast(list[JsonObject], note["claim_spans"])
        span_claim_ids = [cast(str, span["claim_id"]) for span in claim_spans]
        if set(span_claim_ids) != set(note_claim_ids):
            raise DesignContractError(f"讲者稿 {slide_id} 的 claim_spans 与 claim_ids 不一致")
        text = cast(str, note["text"])
        covered_ranges: list[tuple[int, int]] = []
        for span in claim_spans:
            claim_id = cast(str, span["claim_id"])
            if claim_id not in claim_by_id:
                raise DesignContractError(f"讲者稿引用了不存在的声明：{claim_id}")
            if span["normalized_value"] != claim_by_id[claim_id]["normalized_value"]:
                raise DesignContractError(f"讲者稿 {slide_id} 的声明 {claim_id} 归一化值不一致")
            text_span = cast(str, span["text_span"])
            start = text.find(text_span)
            if start < 0:
                raise DesignContractError(f"讲者稿 {slide_id} 的声明 {claim_id} 没有对应原文片段")
            covered_ranges.append((start, start + len(text_span)))
        for match in NUMBER_PATTERN.finditer(text):
            if not any(
                start <= match.start() and match.end() <= end for start, end in covered_ranges
            ):
                raise DesignContractError(
                    f"讲者稿 {slide_id} 出现未绑定声明的数字：{match.group()}"
                )
        for claim_id in note_claim_ids:
            if claim_id not in claim_by_id:
                raise DesignContractError(f"讲者稿引用了不存在的声明：{claim_id}")
            has_note_occurrence = any(
                occurrence["claim_id"] == claim_id
                and occurrence["surface"] == "speaker_notes"
                and occurrence["location_id"] == slide_id
                for occurrence in occurrences
            )
            if not has_note_occurrence:
                raise DesignContractError(
                    f"讲者稿 {slide_id} 的声明 {claim_id} 缺少对应的 speaker_notes 位置"
                )
            has_audience_occurrence = any(
                occurrence["claim_id"] == claim_id and occurrence["surface"] != "speaker_notes"
                for occurrence in occurrences
            )
            if not has_audience_occurrence:
                raise DesignContractError(
                    f"讲者稿 {slide_id} 的声明 {claim_id} 没有任何受众可见载体依据"
                )


def _parse_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise DesignContractError(f"{label}不是日期时间字符串")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignContractError(f"{label}不是有效日期时间") from exc
    if parsed.tzinfo is None:
        raise DesignContractError(f"{label}必须包含时区")
    return parsed


def _validate_current_file(
    file_state: JsonObject,
    *,
    label: str,
    run_id: str,
    run_started_at: datetime,
    verdict_issued_at: datetime,
) -> None:
    if file_state["created_by_run_id"] != run_id:
        raise DesignContractError(f"{label}不是由当前运行生成")

    observed_at = _parse_datetime(file_state["observed_at"], f"{label}.observed_at")
    if not run_started_at <= observed_at <= verdict_issued_at:
        raise DesignContractError(f"{label}的观察时间不在当前运行窗口内")

    mtime_ns = cast(int, file_state["mtime_ns"])
    if mtime_ns < int(run_started_at.timestamp() * 1_000_000_000):
        raise DesignContractError(f"{label}的文件修改时间早于当前运行")

    pre_run_state = cast(JsonObject, file_state["pre_run_state"])
    if pre_run_state["exists"] is True and pre_run_state["sha256"] == file_state["sha256"]:
        raise DesignContractError(f"{label}与运行前文件内容相同，不能作为当前产物")


def validate_current_run_acceptance(
    manifest: JsonObject,
    verdict: JsonObject,
    *,
    manifest_schema_path: Path,
    verdict_schema_path: Path,
) -> None:
    """验证验收结论确实绑定当前运行的新产物和独立验证者。"""

    _validate_schema(manifest, manifest_schema_path)
    _validate_schema(verdict, verdict_schema_path)

    run_id = cast(str, manifest["run_id"])
    run_nonce = cast(str, manifest["run_nonce"])
    if verdict["run_id"] != run_id or verdict["run_nonce"] != run_nonce:
        raise DesignContractError("验收结论没有绑定当前运行标识")
    if verdict["manifest_sha256"] != canonical_json_sha256(manifest):
        raise DesignContractError("验收结论没有绑定当前运行清单摘要")
    if verdict["producer_identity"] != manifest["producer_identity"]:
        raise DesignContractError("验收结论中的生成者与运行清单不一致")
    if verdict["verifier_identity"] == manifest["producer_identity"]:
        raise DesignContractError("生成者不能验收自己的产物")
    if verdict["verdict"] != "accepted":
        raise DesignContractError("当前运行没有获得独立接受结论")

    checks = cast(JsonObject, verdict["checks"])
    if not all(value is True for value in checks.values()):
        raise DesignContractError("接受结论仍包含未通过的验收项")

    artifact = cast(JsonObject, manifest["artifact"])
    render = cast(JsonObject, manifest["render"])
    if verdict["artifact_sha256"] != artifact["sha256"]:
        raise DesignContractError("验收结论没有绑定当前产物摘要")
    if verdict["render_sha256"] != render["sha256"]:
        raise DesignContractError("验收结论没有绑定当前渲染摘要")

    run_started_at = _parse_datetime(manifest["run_started_at"], "run_started_at")
    verdict_issued_at = _parse_datetime(verdict["issued_at"], "verdict.issued_at")
    if verdict_issued_at < run_started_at:
        raise DesignContractError("验收结论早于当前运行开始时间")

    _validate_current_file(
        artifact,
        label="产物",
        run_id=run_id,
        run_started_at=run_started_at,
        verdict_issued_at=verdict_issued_at,
    )
    _validate_current_file(
        render,
        label="渲染",
        run_id=run_id,
        run_started_at=run_started_at,
        verdict_issued_at=verdict_issued_at,
    )

    for receipt in cast(list[JsonObject], manifest["receipts"]):
        expected = {
            "run_id": run_id,
            "run_nonce": run_nonce,
            "design_contract_sha256": manifest["design_contract_sha256"],
            "source_pack_sha256": manifest["source_pack_sha256"],
        }
        if any(receipt[key] != value for key, value in expected.items()):
            raise DesignContractError(f"收据 {receipt['receipt_id']} 没有绑定当前运行")
        issued_at = _parse_datetime(receipt["issued_at"], "receipt.issued_at")
        if not run_started_at <= issued_at <= verdict_issued_at:
            raise DesignContractError(f"收据 {receipt['receipt_id']} 不在当前运行窗口内")
