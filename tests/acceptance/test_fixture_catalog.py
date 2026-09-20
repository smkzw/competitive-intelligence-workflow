"""Task 10.1 M05：首版验收目录的双向闭合与失败关闭测试。

这些测试只读取仓库内脱敏/合成案例，不修改共享 catalog 或 fixture。目录的
Schema、逐文件摘要、案例摘要、责任路由和 required-v12 批准集合任一不一致，
都必须以确定性失败关闭。
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "fixtures/acceptance/catalog.yaml"
SCHEMA_PATH = ROOT / "schemas/acceptance-catalog.schema.json"
FRAGMENT_PATH = ROOT / "fixtures/acceptance/required-v12/catalog-fragment.yaml"
FULL_MATRIX_ROOT = ROOT / "fixtures/acceptance/full-matrix-v1"
REQUIRED_V12_ROOT = ROOT / "fixtures/acceptance/required-v12"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_EXECUTION_SCOPES = {
    "full-matrix",
    "recovery",
    "legacy-cutover",
    "conditional-extension",
}
_APPROVED_REQUIRED_V12_IDS = frozenset(
    {
        "landscape-global-china-maturity",
        "ontology-regimen-boundaries",
        "study-role-boundaries",
        "c-protocol-registry-paths",
        "evidence-guidance-conflicts",
        "supplement-requiredness",
        "b-baseline-d70",
        "b-disposition",
        "b-interaction-cross-format",
        "technical-and-manual-recovery",
        "multi-report-partial-delivery",
        "state-replay-and-reopen",
        "kangzhe-and-large-project-runtime",
        "host-smoke-v1",
        "optional-adapter-recovery",
        "recovery-rehearsal",
        "legacy-absence",
        "legacy-negative-regressions",
    }
)
_APPROVED_NON_REQUIRED_IDS = frozenset(
    {
        "full-matrix-v1",
        "historical-cutoff-acquired-after-disclosed-before",
        "historical-cutoff-disclosed-after-cutoff",
        "historical-cutoff-unknown-first-disclosure",
        "historical-cutoff-cross-day-resume",
    }
)
_APPROVED_IDS = _APPROVED_REQUIRED_V12_IDS | _APPROVED_NON_REQUIRED_IDS
_APPROVED_LEGACY_NEGATIVE_SUBCLASS_IDS = frozenset(
    {
        "old-csu-a",
        "pnh-b",
        "ad-a",
        "style-collapse",
        "fake-screenshot",
        "false-green-qc",
    }
)
_APPROVED_SUBSCENARIO_IDS: dict[str, frozenset[str]] = {
    "landscape-global-china-maturity": frozenset(
        {
            "global-mature-result-bearing",
            "china-mature-result-bearing",
            "local-early-no-result",
            "overseas-early-no-result",
        }
    ),
    "ontology-regimen-boundaries": frozenset(
        {
            "adc",
            "fusion-protein",
            "innovative-with-traditional-background",
            "pure-traditional",
            "reformulation-repositioning-fixed-combination-review",
        }
    ),
    "study-role-boundaries": frozenset(
        {
            "exclude-healthy-volunteer",
            "exclude-pure-pk-or-be",
            "exclude-unrelated-indication",
            "exclude-observational",
            "exclude-eap-compassionate-use",
            "supporting-layer",
            "special-early-core",
            "study-publication-role-separation",
        }
    ),
    "c-protocol-registry-paths": frozenset(
        {
            "protocol-sap-complete",
            "registry-sufficient",
            "statistical-only-missing",
            "critical-design-missing-then-recovered",
            "multiple-design-paths-no-unique-recommendation",
        }
    ),
    "evidence-guidance-conflicts": frozenset(
        {
            "paper-registry-regulatory-industry-conflict",
            "final-draft-superseded-guidance",
            "cde-fda-aligned",
            "cde-fda-divergent",
            "strict-majority",
            "most-commonly-adopted",
        }
    ),
    "supplement-requiredness": frozenset(
        {
            "supplement-unavailable-not-required",
            "supplement-required-block",
            "user-file-recovery",
        }
    ),
    "b-baseline-d70": frozenset(
        {
            "baseline-age-block-recover",
            "baseline-sex-block-recover",
            "baseline-severity-block-recover",
            "mean-median-split",
            "age-bin-demographic-category-split",
            "scale-version-direction-split",
            "baseline-time-split",
        }
    ),
    "b-disposition": frozenset(
        {
            "fully-undisclosed-nonblocking",
            "partially-undisclosed-nonblocking",
            "different-denominators",
            "completion-withdrawal",
            "pd-subject-event-counts",
            "non-mutually-exclusive-reasons",
        }
    ),
    "b-interaction-cross-format": frozenset(
        {
            "baseline-chart-table-drawer",
            "disposition-chart-table-drawer",
            "filter-round-trip",
            "url-round-trip",
            "adr-0013-html-only",
        }
    ),
    "technical-and-manual-recovery": frozenset(
        {
            "network-failure",
            "rate-limit",
            "captcha",
            "page-change",
            "parser-failure",
            "tool-capability-failure",
            "manual-original-name-match",
            "rename-archive-recover",
        }
    ),
    "multi-report-partial-delivery": frozenset(
        {
            "shared-evidence-independent-gates",
            "one-report-blocks",
            "other-html-delivers",
            "adr-0013-no-pptx-simulation",
        }
    ),
    "state-replay-and-reopen": frozenset(
        {
            "illegal-transition",
            "idempotent-replay",
            "remaining-object-terminal-block",
            "explicit-reopen",
        }
    ),
    "kangzhe-and-large-project-runtime": frozenset(
        {
            "logo-navigation-no-collision",
            "global-search",
            "full-pages",
            "filters",
            "evidence-drilldown",
            "large-project-browser",
            "adr-0013-html-only",
        }
    ),
    "host-smoke-v1": frozenset(
        {
            "codex-entry",
            "hermes-entry",
            "omp-entry",
            "semantic-conformance",
            "independent-processes",
        }
    ),
    "optional-adapter-recovery": frozenset(
        {
            "selected-adapter-cache-loss",
            "event-checkpoint-recovery",
            "unselected-not-applicable",
        }
    ),
    "recovery-rehearsal": frozenset(
        {
            "isolated-install",
            "project-rehydrate",
            "incremental-refresh",
            "representative-html-rebuild",
            "pre-rc-cannot-close",
        }
    ),
    "legacy-absence": frozenset(
        {
            "shadow-copy",
            "symbolic-link",
            "legacy-entry",
            "consumer-reference",
            "cache-backup",
            "authorized-exact-list",
        }
    ),
    "legacy-negative-regressions": _APPROVED_LEGACY_NEGATIVE_SUBCLASS_IDS,
}


class CatalogContractError(AssertionError):
    """验收目录违反结构、内容寻址或批准矩阵时的测试错误。"""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise CatalogContractError(message)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict), f"YAML 顶层必须是对象：{path}")
    return cast(dict[str, Any], payload)


def _load_catalog() -> dict[str, Any]:
    return _load_yaml(CATALOG_PATH)


def _load_fragment() -> dict[str, Any]:
    return _load_yaml(FRAGMENT_PATH)


def _index_cases(payload: dict[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    raw_cases = payload.get("cases")
    _require(isinstance(raw_cases, list) and raw_cases, f"{label}必须包含非空 cases 列表")
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_case in enumerate(cast(list[Any], raw_cases)):
        _require(isinstance(raw_case, dict), f"{label}案例 #{index} 必须是对象")
        case = cast(dict[str, Any], raw_case)
        case_id = case.get("id")
        _require(isinstance(case_id, str) and case_id, f"{label}案例 #{index} 缺少 id")
        case_id = cast(str, case_id)
        _require(case_id not in indexed, f"{label}存在重复案例：{case_id}")
        indexed[case_id] = case
    return indexed


def _case_digest(case: dict[str, Any]) -> str:
    """按 acceptance-catalog.schema 的 sha256-canonical-json-v1 重算案例摘要。"""
    payload = {key: value for key, value in case.items() if key != "case_digest"}
    reports = cast(list[str], payload["reports"])
    formats = cast(list[str], payload["formats"])
    inputs = cast(list[dict[str, Any]], payload["inputs"])
    payload["reports"] = sorted(reports)
    payload["formats"] = sorted(formats)
    payload["inputs"] = sorted(inputs, key=lambda item: str(item["path"]))
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _refresh_case_digest(case: dict[str, Any]) -> None:
    case["case_digest"] = _case_digest(case)


def _case_root(case_id: str) -> Path:
    if case_id == "full-matrix-v1" or case_id.startswith("historical-cutoff-"):
        return FULL_MATRIX_ROOT
    return REQUIRED_V12_ROOT / case_id


def _assert_relative_path(raw_path: object, *, label: str) -> str:
    _require(isinstance(raw_path, str) and raw_path, f"{label}必须是非空相对路径")
    path = cast(str, raw_path)
    _require(not Path(path).is_absolute(), f"{label}不得是绝对路径：{path}")
    _require(not PureWindowsPath(path).drive, f"{label}不得包含 Windows 盘符：{path}")
    _require("\\" not in path, f"{label}必须使用 POSIX 路径：{path}")
    _require(".." not in Path(path).parts, f"{label}不得越出所属目录：{path}")
    return path


def _assert_schema(catalog: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(catalog),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        error = errors[0]
        raise CatalogContractError(f"catalog 不符合 acceptance schema：{error.message}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_case_files(case_id: str, case: dict[str, Any]) -> None:
    case_root = _case_root(case_id)
    _require(case_root.is_dir(), f"案例目录不存在：{case_root}")
    raw_inputs = case.get("inputs")
    _require(isinstance(raw_inputs, list) and raw_inputs, f"案例 {case_id} 缺少输入文件")
    for input_index, raw_input in enumerate(cast(list[Any], raw_inputs)):
        _require(isinstance(raw_input, dict), f"案例 {case_id} 输入 #{input_index} 必须是对象")
        input_entry = cast(dict[str, Any], raw_input)
        relative_path = _assert_relative_path(
            input_entry.get("path"),
            label=f"案例 {case_id} 输入 #{input_index} 路径",
        )
        declared_sha = input_entry.get("sha256")
        _require(
            isinstance(declared_sha, str) and _SHA256_RE.fullmatch(declared_sha) is not None,
            f"案例 {case_id} 输入 {relative_path} 缺少有效 SHA-256",
        )
        input_path = case_root / relative_path
        resolved = input_path.resolve()
        _require(
            resolved.is_relative_to(case_root.resolve()),
            f"案例 {case_id} 输入路径越界：{relative_path}",
        )
        _require(input_path.is_file(), f"案例 {case_id} 输入文件不存在：{relative_path}")
        _require(
            _sha256_file(input_path) == declared_sha,
            f"案例 {case_id} 输入摘要与文件不一致：{relative_path}",
        )

    expected = cast(dict[str, Any], case["expected"])
    expected_files = expected.get("expected_files", [])
    _require(isinstance(expected_files, list), f"案例 {case_id} expected_files 必须是列表")
    for file_index, raw_file in enumerate(cast(list[Any], expected_files)):
        _require(isinstance(raw_file, dict), f"案例 {case_id} 预期文件 #{file_index} 必须是对象")
        expected_file = cast(dict[str, Any], raw_file)
        relative_path = _assert_relative_path(
            expected_file.get("path"),
            label=f"案例 {case_id} 预期文件 #{file_index} 路径",
        )
        declared_sha = expected_file.get("sha256")
        _require(
            isinstance(declared_sha, str) and _SHA256_RE.fullmatch(declared_sha) is not None,
            f"案例 {case_id} 预期文件 {relative_path} 缺少有效 SHA-256",
        )
        expected_path = case_root / relative_path
        _require(expected_path.is_file(), f"案例 {case_id} 预期文件不存在：{relative_path}")
        _require(
            _sha256_file(expected_path) == declared_sha,
            f"案例 {case_id} 预期文件摘要与文件不一致：{relative_path}",
        )


def _assert_case_routing(case_id: str, case: dict[str, Any]) -> None:
    owner_task = case.get("owner_task")
    _require(isinstance(owner_task, str) and owner_task, f"案例 {case_id} 缺少 owner_task")
    _require(
        case.get("execution_scope") in _ALLOWED_EXECUTION_SCOPES,
        f"案例 {case_id} 缺少有效 execution_scope",
    )
    formats = case.get("formats")
    _require(formats == ["html"], f"案例 {case_id} 首版格式必须严格为 [html]")
    verifiers = case.get("verifiers")

    _require(isinstance(verifiers, list) and verifiers, f"案例 {case_id} 缺少 verifiers")
    for verifier_index, verifier in enumerate(cast(list[Any], verifiers)):
        if isinstance(verifier, str):
            _require(verifier.strip(), f"案例 {case_id} verifier #{verifier_index} 不能为空")
            continue
        _require(isinstance(verifier, dict), f"案例 {case_id} verifier #{verifier_index} 无效")
        verifier_dict = cast(dict[str, Any], verifier)
        _require(
            verifier_dict.get("kind") in {"pytest", "command", "script"},
            f"案例 {case_id} verifier #{verifier_index} 缺少有效 kind",
        )
        _require(
            isinstance(verifier_dict.get("target"), str) and bool(verifier_dict["target"].strip()),
            f"案例 {case_id} verifier #{verifier_index} 缺少 target",
        )

    receipt = case.get("receipt")
    _require(isinstance(receipt, dict), f"案例 {case_id} 缺少 receipt")
    receipt_dict = cast(dict[str, Any], receipt)
    _assert_relative_path(
        receipt_dict.get("relative_path"),
        label=f"案例 {case_id} receipt.relative_path",
    )
    _assert_relative_path(receipt_dict.get("schema"), label=f"案例 {case_id} receipt.schema")
    _require(
        isinstance(receipt_dict.get("owner_status"), str) and bool(receipt_dict["owner_status"]),
        f"案例 {case_id} receipt 缺少 owner_status",
    )


def _assert_provenance(case_id: str, case: dict[str, Any]) -> None:
    provenance = case.get("provenance")
    _require(isinstance(provenance, dict), f"案例 {case_id} 缺少 provenance")
    provenance_dict = cast(dict[str, Any], provenance)
    source_fixture = _assert_relative_path(
        provenance_dict.get("source_fixture"),
        label=f"案例 {case_id} provenance.source_fixture",
    )
    _require(
        provenance_dict.get("deidentified") is True,
        f"案例 {case_id} 必须声明已脱敏",
    )
    _require(
        provenance_dict.get("identity_verified") is True,
        f"案例 {case_id} 必须声明身份核验完成",
    )
    _require(
        (ROOT / source_fixture).exists(),
        f"案例 {case_id} provenance.source_fixture 不存在：{source_fixture}",
    )


def _assert_subscenario_declarations(
    catalog_cases: dict[str, dict[str, Any]],
) -> None:
    for case_id, approved_ids in _APPROVED_SUBSCENARIO_IDS.items():
        _require(case_id in catalog_cases, f"子场景对应案例未登记：{case_id}")
        scenario_path = _case_root(case_id) / "inputs/scenario.json"
        _require(scenario_path.is_file(), f"案例 {case_id} 缺少子场景定义：{scenario_path}")
        scenario_payload = json.loads(scenario_path.read_text(encoding="utf-8"))
        _require(isinstance(scenario_payload, dict), f"案例 {case_id} 子场景顶层必须是对象")
        scenario = cast(dict[str, Any], scenario_payload)
        _require(
            scenario.get("case_id") == case_id,
            f"案例 {case_id} 子场景 case_id 不一致",
        )
        _require(
            scenario.get("release_scope") == "site_html_v1",
            f"案例 {case_id} 子场景 release_scope 必须为 site_html_v1",
        )
        _require(
            scenario.get("formats") == ["html"],
            f"案例 {case_id} 子场景格式必须严格为 [html]",
        )
        raw_subscenarios = scenario.get("subscenarios")
        _require(
            isinstance(raw_subscenarios, list) and raw_subscenarios,
            f"案例 {case_id} 缺少 subscenarios",
        )
        declared_ids: list[str] = []
        for index, raw_subscenario in enumerate(cast(list[Any], raw_subscenarios)):
            _require(
                isinstance(raw_subscenario, dict),
                f"案例 {case_id} 子场景 #{index} 必须是对象",
            )
            subscenario = cast(dict[str, Any], raw_subscenario)
            subscenario_id = subscenario.get("id")
            _require(
                isinstance(subscenario_id, str) and subscenario_id,
                f"案例 {case_id} 子场景 #{index} 缺少 id",
            )
            _require(
                isinstance(subscenario.get("description_zh"), str)
                and bool(subscenario["description_zh"].strip()),
                f"案例 {case_id} 子场景 #{index} 缺少中文说明",
            )
            declared_ids.append(cast(str, subscenario_id))
        _require(
            len(declared_ids) == len(set(declared_ids)),
            f"案例 {case_id} 子场景存在重复 id",
        )
        _require(
            frozenset(declared_ids) == approved_ids,
            f"案例 {case_id} 子场景与批准集合不一致："
            f"缺失={sorted(approved_ids - frozenset(declared_ids))}，"
            f"额外={sorted(frozenset(declared_ids) - approved_ids)}",
        )
        if case_id == "legacy-negative-regressions":
            _require(
                frozenset(declared_ids) == _APPROVED_LEGACY_NEGATIVE_SUBCLASS_IDS,
                "旧版负向回归必须声明批准的六个子案例",
            )


def _assert_required_owner_and_state_rules(
    catalog_cases: dict[str, dict[str, Any]],
) -> None:
    required_cases = {case_id: catalog_cases[case_id] for case_id in _APPROVED_REQUIRED_V12_IDS}
    conditional_ids = {
        case_id
        for case_id, case in required_cases.items()
        if case.get("execution_scope") == "conditional-extension"
    }
    _require(
        conditional_ids == {"optional-adapter-recovery"},
        "只有 optional-adapter-recovery 可以使用 conditional-extension",
    )
    not_applicable_ids = {
        case_id
        for case_id, case in required_cases.items()
        if cast(dict[str, Any], case["expected"]).get("state") == "not_applicable"
    }
    _require(
        not_applicable_ids == {"optional-adapter-recovery"},
        "只有 optional-adapter-recovery 可以为 not_applicable",
    )

    optional = required_cases["optional-adapter-recovery"]
    optional_expected = cast(dict[str, Any], optional["expected"])
    optional_receipt = cast(dict[str, Any], optional["receipt"])
    optional_reason = optional.get("not_applicable")
    _require(
        isinstance(optional_reason, str)
        and "合同摘要" in optional_reason
        and "E1" in optional_reason,
        "optional-adapter-recovery 的 not_applicable 必须绑定 E1 合同摘要",
    )
    _require(
        optional_expected.get("outcome") == "pending"
        and optional_expected.get("state") == "not_applicable",
        "optional-adapter-recovery 必须保持 pending/not_applicable",
    )
    _require(
        optional_receipt.get("owner_status") == "not_applicable",
        "optional-adapter-recovery 回执必须为 not_applicable",
    )

    pending_future_ids = {
        case_id
        for case_id, case in required_cases.items()
        if cast(dict[str, Any], case["expected"]).get("state") == "pending_future_owner"
    }
    _require(
        pending_future_ids == {"recovery-rehearsal", "legacy-absence"},
        "只有 recovery-rehearsal 和 legacy-absence 的预期终态保持 pending_future_owner",
    )
    for case_id in ("recovery-rehearsal", "legacy-absence"):
        expected = cast(dict[str, Any], required_cases[case_id]["expected"])
        receipt = cast(dict[str, Any], required_cases[case_id]["receipt"])
        _require(
            expected.get("outcome") == "pending"
            and expected.get("state") == "pending_future_owner",
            f"案例 {case_id} 必须保持 pending_future_owner",
        )
        _require(
            receipt.get("owner_status") == "pending_future_owner",
            f"案例 {case_id} 回执必须保持 pending_future_owner",
        )

    future_receipt_ids = {
        case_id
        for case_id, case in required_cases.items()
        if cast(dict[str, Any], case["receipt"]).get("owner_status") == "pending_future_owner"
    }
    _require(
        future_receipt_ids == _APPROVED_REQUIRED_V12_IDS - {"optional-adapter-recovery"},
        "Task 10.1 只能登记未来责任阶段；除 E1 条件不适用外不得提前关闭回执",
    )


def _assert_required_bidirectional_closure(
    catalog_cases: dict[str, dict[str, Any]],
    fragment: dict[str, Any],
) -> None:
    _require(
        fragment.get("schema_version") == "1.0",
        "required-v12 fragment schema_version 必须为 1.0",
    )
    required_catalog_ids = {
        case_id for case_id, case in catalog_cases.items() if case.get("family") == "required-v12"
    }
    _require(
        required_catalog_ids == _APPROVED_REQUIRED_V12_IDS,
        "required-v12 目录与批准矩阵不闭合："
        f"缺失={sorted(_APPROVED_REQUIRED_V12_IDS - required_catalog_ids)}，"
        f"额外={sorted(required_catalog_ids - _APPROVED_REQUIRED_V12_IDS)}",
    )
    fragment_cases = _index_cases(fragment, label="required-v12 fragment")
    fragment_ids = set(fragment_cases)
    _require(
        fragment_ids == _APPROVED_REQUIRED_V12_IDS,
        "required-v12 fragment 与批准矩阵不闭合："
        f"缺失={sorted(_APPROVED_REQUIRED_V12_IDS - fragment_ids)}，"
        f"额外={sorted(fragment_ids - _APPROVED_REQUIRED_V12_IDS)}",
    )
    for case_id in _APPROVED_REQUIRED_V12_IDS:
        _require(
            fragment_cases[case_id] == catalog_cases[case_id],
            f"required-v12 fragment 与共享 catalog 内容不一致：{case_id}",
        )


def _assert_catalog_closed(catalog: dict[str, Any], fragment: dict[str, Any]) -> None:
    _assert_schema(catalog)
    catalog_cases = _index_cases(catalog, label="acceptance catalog")
    requirements = cast(dict[str, Any], catalog["requirements"])
    _assert_required_bidirectional_closure(catalog_cases, fragment)
    _require(
        set(requirements["approved_case_families"])
        == {"full-matrix", "historical-cutoff", "required-v12"},
        "approved_case_families 未覆盖 full-matrix、historical-cutoff、required-v12",
    )
    _require(requirements["allowed_formats"] == ["html"], "首版允许格式必须只有 html")
    _require(
        requirements["extra_case_policy"] == "reject_unless_explicitly_registered",
        "额外案例必须采用显式登记后才允许的策略",
    )
    declared_case_ids = set(requirements.get("declared_case_ids", []))
    unknown_ids = set(catalog_cases) - _APPROVED_IDS
    _require(
        unknown_ids <= declared_case_ids,
        "发现未登记额外案例；必须先在 requirements.declared_case_ids 显式说明："
        f"{sorted(unknown_ids - declared_case_ids)}",
    )
    _require(
        set(catalog_cases) == _APPROVED_IDS | (unknown_ids & declared_case_ids),
        "catalog 案例集合与批准矩阵不闭合",
    )
    _assert_subscenario_declarations(catalog_cases)
    _assert_required_owner_and_state_rules(catalog_cases)

    for case_id, case in catalog_cases.items():
        _require(
            case.get("family") in {"full-matrix", "historical-cutoff", "required-v12"},
            f"案例 {case_id} family 未登记",
        )
        _assert_case_routing(case_id, case)
        _assert_provenance(case_id, case)
        _require(
            _case_digest(case) == case.get("case_digest"),
            f"案例 {case_id} case_digest 不匹配",
        )
        _assert_case_files(case_id, case)


def _expect_rejection(
    catalog: dict[str, Any],
    *,
    fragment: dict[str, Any] | None = None,
    message: str,
) -> None:
    with pytest.raises(CatalogContractError, match=message):
        _assert_catalog_closed(catalog, fragment or _load_fragment())


# fmt: off
def test_full_matrix_scenario_has_indication_timezone_cutoff_hashed_inputs_and_html_only_scope(
) -> None:
# fmt: on
    """验收节点 1：full-matrix-v1 的三报告首版 HTML 基线可重算。"""
    catalog = _load_catalog()
    _assert_catalog_closed(catalog, _load_fragment())
    case = _index_cases(catalog, label="acceptance catalog")["full-matrix-v1"]

    assert case["indication"] == "特应性皮炎"
    assert case["timezone"] == "Asia/Shanghai"
    assert case["formats"] == ["html"]
    assert case["execution_scope"] == "full-matrix"
    assert case["reports"] == ["A", "B", "C"]
    cutoff = datetime.fromisoformat(case["data_cutoff"])
    assert cutoff.tzinfo is not None and cutoff.utcoffset() is not None
    assert case["data_cutoff"] == "2026-07-31T23:59:59+08:00"
    assert all(_SHA256_RE.fullmatch(item["sha256"]) for item in case["inputs"])
    assert case["provenance"]["deidentified"] is True
    assert case["provenance"]["identity_verified"] is True


# fmt: off
def test_historical_cutoff_scenario_separates_disclosure_from_acquisition_and_freezes_resume_cutoff(
) -> None:
# fmt: on
    """验收节点 2：披露、获取和跨日恢复始终使用独立且冻结的 cutoff。"""
    catalog = _load_catalog()
    _assert_catalog_closed(catalog, _load_fragment())
    cases = _index_cases(catalog, label="acceptance catalog")
    historical_ids = {
        "historical-cutoff-acquired-after-disclosed-before",
        "historical-cutoff-disclosed-after-cutoff",
        "historical-cutoff-unknown-first-disclosure",
        "historical-cutoff-cross-day-resume",
    }
    assert {
        case_id for case_id in cases if case_id.startswith("historical-cutoff-")
    } == historical_ids

    for case_id in historical_ids:
        case = cases[case_id]
        history = cast(dict[str, Any], case["history"])
        input_entry = cast(dict[str, Any], case["inputs"][0])
        source = json.loads((_case_root(case_id) / input_entry["path"]).read_text(encoding="utf-8"))
        source_first_disclosed = source["first_disclosed_at"]
        expected_first_disclosed = (
            source_first_disclosed["value"]
            if source_first_disclosed["state"] == "reported"
            else None
        )
        assert history["first_disclosed_at"] == expected_first_disclosed
        assert history["acquired_at"] == source["acquired_at"]
        assert history["materialized_cutoff"] == case["data_cutoff"]
        assert history["resume_cutoff"] == history["materialized_cutoff"]
        assert history["cutoff_is_frozen"] is True

    acquired_before = cases["historical-cutoff-acquired-after-disclosed-before"]["history"]
    disclosed_after = cases["historical-cutoff-disclosed-after-cutoff"]["history"]
    unknown = cases["historical-cutoff-unknown-first-disclosure"]["history"]
    cross_day = cases["historical-cutoff-cross-day-resume"]["history"]
    cutoff = datetime.fromisoformat(acquired_before["materialized_cutoff"])
    assert datetime.fromisoformat(acquired_before["first_disclosed_at"]) <= cutoff
    assert datetime.fromisoformat(acquired_before["acquired_at"]) > cutoff
    assert acquired_before["expected_assessment"] == "snapshot_eligible"
    assert datetime.fromisoformat(disclosed_after["first_disclosed_at"]) > cutoff
    assert datetime.fromisoformat(cross_day["resumed_at"]) > datetime.fromisoformat(
        cross_day["materialized_cutoff"]
    )
    assert unknown["first_disclosed_at"] is None
    assert unknown["expected_assessment"] == "blocked_unknown_disclosure"
    assert cross_day["expected_assessment"] == "snapshot_eligible"

    expected_path = FULL_MATRIX_ROOT / "expected/history/cross-day-resume.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert expected["resume_cutoff_before_cross_day"] == expected["resume_cutoff_after_cross_day"]
    assert expected["resume_cutoff_after_cross_day"] == cross_day["materialized_cutoff"]


def test_acceptance_catalog_covers_every_required_v12_scenario_with_hashed_inputs() -> None:
    """验收节点 3：批准的 18 个 required-v12 场景与共享 catalog 双向闭合。"""
    catalog = _load_catalog()
    _assert_catalog_closed(catalog, _load_fragment())
    cases = _index_cases(catalog, label="acceptance catalog")
    required_cases = {
        case_id: case for case_id, case in cases.items() if case["family"] == "required-v12"
    }

    assert set(required_cases) == _APPROVED_REQUIRED_V12_IDS
    assert len(required_cases) == 18
    for case_id, case in required_cases.items():
        assert case["formats"] == ["html"], case_id
        assert case["owner_task"], case_id
        assert case["execution_scope"] in _ALLOWED_EXECUTION_SCOPES, case_id
        assert case["verifiers"], case_id
        assert case["receipt"]["relative_path"].startswith("docs/acceptance/"), case_id
        assert case["inputs"], case_id
        assert all(_SHA256_RE.fullmatch(item["sha256"]) for item in case["inputs"]), case_id
        assert case["provenance"]["deidentified"] is True, case_id
        assert case["provenance"]["identity_verified"] is True, case_id


def test_required_v12_subscenarios_and_owner_states_are_approved_and_declared() -> None:
    catalog = _load_catalog()
    _assert_catalog_closed(catalog, _load_fragment())
    cases = _index_cases(catalog, label="acceptance catalog")

    assert set(_APPROVED_SUBSCENARIO_IDS) == _APPROVED_REQUIRED_V12_IDS
    assert (
        _APPROVED_SUBSCENARIO_IDS["legacy-negative-regressions"]
        == _APPROVED_LEGACY_NEGATIVE_SUBCLASS_IDS
    )
    assert cases["optional-adapter-recovery"]["expected"]["state"] == "not_applicable"
    assert cases["recovery-rehearsal"]["expected"]["state"] == "pending_future_owner"
    assert cases["legacy-absence"]["expected"]["state"] == "pending_future_owner"


def test_acceptance_catalog_rejects_missing_required_case_from_shared_catalog() -> None:
    catalog = copy.deepcopy(_load_catalog())
    catalog["cases"] = [case for case in catalog["cases"] if case["id"] != "host-smoke-v1"]
    _expect_rejection(catalog, message="required-v12")


def test_acceptance_catalog_rejects_missing_required_case_from_fragment() -> None:
    catalog = _load_catalog()
    fragment = copy.deepcopy(_load_fragment())
    fragment["cases"] = [case for case in fragment["cases"] if case["id"] != "host-smoke-v1"]
    _expect_rejection(catalog, fragment=fragment, message="required-v12")


@pytest.mark.parametrize("replaced_id", tuple(sorted(_APPROVED_REQUIRED_V12_IDS)))
def test_acceptance_catalog_rejects_invented_required_v12_replacement(
    replaced_id: str,
) -> None:
    catalog = copy.deepcopy(_load_catalog())
    fragment = copy.deepcopy(_load_fragment())
    for payload in (catalog, fragment):
        for case in payload["cases"]:
            if case["id"] == replaced_id:
                case["id"] = f"invented-{replaced_id}"
                _refresh_case_digest(case)
    _expect_rejection(catalog, fragment=fragment, message="required-v12")


def test_acceptance_catalog_rejects_unregistered_extra_case_without_requirement_explanation() -> (
    None
):
    catalog = copy.deepcopy(_load_catalog())
    cases = _index_cases(catalog, label="acceptance catalog")
    extra_case = copy.deepcopy(cases["full-matrix-v1"])
    extra_case["id"] = "unregistered-extra-case"
    extra_case["name_zh"] = "未登记额外案例"
    _refresh_case_digest(extra_case)
    catalog["cases"].append(extra_case)
    _expect_rejection(catalog, message="未登记额外案例")


def test_acceptance_catalog_rejects_case_digest_drift() -> None:
    catalog = copy.deepcopy(_load_catalog())
    case = next(case for case in catalog["cases"] if case["id"] == "full-matrix-v1")
    case["description_zh"] = f"{case['description_zh']}（篡改）"
    _expect_rejection(catalog, message="case_digest")


def test_acceptance_catalog_rejects_input_hash_drift_even_when_case_digest_is_recomputed() -> None:
    catalog = copy.deepcopy(_load_catalog())
    case = next(case for case in catalog["cases"] if case["id"] == "full-matrix-v1")
    case["inputs"][0]["sha256"] = "0" * 64
    _refresh_case_digest(case)
    _expect_rejection(catalog, message="输入摘要与文件不一致")


@pytest.mark.parametrize("missing_field", ("owner_task", "execution_scope", "verifiers", "receipt"))
def test_acceptance_catalog_rejects_missing_routing_contract(missing_field: str) -> None:
    catalog = copy.deepcopy(_load_catalog())
    case = next(case for case in catalog["cases"] if case["id"] == "full-matrix-v1")
    case.pop(missing_field)
    _expect_rejection(catalog, message=missing_field)


@pytest.mark.parametrize(
    "invalid_variant", ("absolute_input", "non_html_format", "unredacted_source")
)
def test_acceptance_catalog_rejects_out_of_scope_or_unredacted_variant(
    invalid_variant: str,
) -> None:
    catalog = copy.deepcopy(_load_catalog())
    case = next(case for case in catalog["cases"] if case["id"] == "full-matrix-v1")
    if invalid_variant == "absolute_input":
        case["inputs"][0]["path"] = "/tmp/production-secret.json"
        expected_message = "不符合 acceptance schema"
    elif invalid_variant == "non_html_format":
        case["formats"] = ["html", "pdf"]
        expected_message = "不符合 acceptance schema"
    else:
        case["provenance"]["deidentified"] = False
        expected_message = "不符合 acceptance schema"
    _refresh_case_digest(case)
    _expect_rejection(catalog, message=expected_message)


def test_full_matrix_timezone_is_a_real_iana_zone() -> None:
    """补充边界：时区不能只满足字符串形状，必须能由 IANA 数据库解析。"""
    case = _index_cases(_load_catalog(), label="acceptance catalog")["full-matrix-v1"]
    try:
        zone = ZoneInfo(case["timezone"])
    except ZoneInfoNotFoundError as error:
        raise CatalogContractError(f"未知 IANA 时区：{case['timezone']}") from error
    assert zone.key == "Asia/Shanghai"
