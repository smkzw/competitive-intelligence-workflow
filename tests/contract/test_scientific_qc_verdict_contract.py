"""Task 3.7 生产质控结论验证器合同：打包 Draft 2020-12 Schema 在边界内运行。

与运行时代码共用同一个生产验证器（``validate_scientific_qc_verdict_payload``），
保证“Schema 校验与签发同一边界”可被合同测试直接验证；负例是 Pydantic/
语义单独通过而 Schema 拒绝的载荷（``locator.page=true`` 宽松强转），证明
Schema 层在签发路径上真实生效，而不是摆设。
"""

from __future__ import annotations

import json as jsonlib
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from ci_workflow.capabilities.scientific_qc import (
    ScientificQcBoundaryError,
    _scientific_qc_verdict_schema,
    validate_scientific_qc_verdict_payload,
)
from ci_workflow.domain.enums import ReportKind

ROOT = Path(__file__).resolve().parents[2]
PACKAGED_SCHEMA = (
    ROOT / "src" / "ci_workflow" / "schemas" / "scientific-qc-verdict.schema.json"
)


def _valid_verdict_payload() -> dict[str, Any]:
    from tests.integration.test_scientific_qc_gate import (
        _accepted_trio,
        _passed_gate_result,
        snapshot_for,
    )

    report_kind = ReportKind.A
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    _ctx, _bundle, verdict = _accepted_trio(report_kind, gate_result, snapshot)
    return cast(dict[str, Any], verdict)


def test_packaged_schema_copy_matches_directory_contract() -> None:
    """目录包与 wheel 内运行时 Schema 必须逐字一致，避免安装后口径漂移。"""
    assert PACKAGED_SCHEMA.read_bytes() == (
        ROOT / "schemas" / "scientific-qc-verdict.schema.json"
    ).read_bytes()


def test_production_validator_passes_valid_payload() -> None:
    verdict = validate_scientific_qc_verdict_payload(_valid_verdict_payload())
    assert verdict.verdict == "accepted"


def test_production_validator_runs_schema_before_pydantic_and_semantics() -> None:
    """负例：``page=true`` 让 Pydantic/语义单独通过但 Schema 拒绝 → 生产
    验证器拒绝，且错误文本确定（同一载荷两次调用错误完全一致）。"""
    payload = _valid_verdict_payload()
    payload["locators"][0]["locator"]["page"] = True

    from ci_workflow.capabilities.scientific_qc import _strip_computed
    from ci_workflow.qc.scientific import (
        ScientificQcVerdict,
        check_scientific_qc_verdict_semantics,
    )

    stripped = _strip_computed(payload)
    # 对照 1：Pydantic 单独通过（宽松强转 True -> 1）
    assert ScientificQcVerdict.model_validate(stripped) is not None
    # 对照 2：语义单独通过
    assert check_scientific_qc_verdict_semantics(dict(stripped)) == []
    # 对照 3：Draft 2020-12 Schema 拒绝
    schema = jsonlib.loads(
        (ROOT / "schemas/scientific-qc-verdict.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(stripped))

    # 生产验证器拒绝且错误确定
    with pytest.raises(ScientificQcBoundaryError, match="打包 Schema") as first:
        validate_scientific_qc_verdict_payload(payload)
    with pytest.raises(ScientificQcBoundaryError, match="打包 Schema") as second:
        validate_scientific_qc_verdict_payload(payload)
    assert str(first.value) == str(second.value)
    assert str(first.value).startswith("质控结论不符合打包 Schema")


def test_schema_resolves_from_source_tree_and_packaged_layout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Schema 路径解析同时支持源码树与打包安装布局，且不接受调用方选择的
    路径（解析函数没有路径参数，也不读取任何调用方来源）。"""
    import ci_workflow.capabilities.scientific_qc as sqc_module

    repo_schema = jsonlib.loads(
        (ROOT / "schemas/scientific-qc-verdict.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert repo_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    # 源码树布局：仓库根 schemas/（本仓库的目录安装包布局）
    source_tree_schema = _scientific_qc_verdict_schema()
    assert source_tree_schema == repo_schema

    # 打包安装布局：模块位于 site-packages/ci_workflow/capabilities/，
    # Schema 随包数据装入 site-packages/ci_workflow/schemas/。
    site_packages = tmp_path / "site-packages"
    packaged_schemas = site_packages / "ci_workflow" / "schemas"
    packaged_schemas.mkdir(parents=True)
    (packaged_schemas / "scientific-qc-verdict.schema.json").write_text(
        (ROOT / "schemas/scientific-qc-verdict.schema.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sqc_module,
        "__file__",
        str(site_packages / "ci_workflow" / "capabilities" / "scientific_qc.py"),
    )
    packaged_schema = _scientific_qc_verdict_schema()
    assert packaged_schema == repo_schema
    # 打包布局下生产验证器同样完整运行
    verdict = validate_scientific_qc_verdict_payload(_valid_verdict_payload())
    assert verdict.verdict == "accepted"


def test_schema_resolver_fails_closed_with_deterministic_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """两种布局都缺失时以确定性的 ScientificQcBoundaryError 失败关闭。"""
    import ci_workflow.capabilities.scientific_qc as sqc_module

    monkeypatch.setattr(
        sqc_module,
        "__file__",
        str(tmp_path / "site-packages" / "ci_workflow" / "capabilities" / "scientific_qc.py"),
    )
    with pytest.raises(ScientificQcBoundaryError, match="无法定位"):
        _scientific_qc_verdict_schema()
