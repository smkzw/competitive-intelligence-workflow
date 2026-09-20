"""Task 3.6 FX05–FX06：唯一 fixture catalog 校验与 no-draft-a-empty 当前运行绑定。

- FX05：`fixtures/catalog.yaml` 是唯一案例注册表；validate_catalog 对未知名、
  重名案例、路径逃逸、输入缺失、未声明输入文件、输入摘要不符与非法 case_digest
  一律以 FixtureCaseError 失败关闭。
- FX06：`no-draft-a-empty` 真实运行绑定 case_digest、当前 run_id、当前 manifest
  摘要与真实输入哈希；只产生 blockers/A/v1/{audit.json,audit.md} 与运行/事件记录，
  不创建报告快照、coverage projection、格式任务、产物记录或 HTML 占位。
- Task 8.2：three-report-complete 同一适应症 A/B/C 输入、实体计数、GateSpec 预期
  与 run-binding 合同锁定；当次 html+pdf 运行写入 current_run 并绑定 PDF 产物摘要。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from ci_workflow.application.fixture_runner import (
    FixtureCaseError,
    run_fixture_case,
    validate_catalog,
)
from ci_workflow.application.run_service import (
    MANIFEST_RECORDED_EVENT,
    MANIFEST_RELATIVE_PATH,
    compute_event_stream_digest,
    compute_input_hashes_digest,
)
from ci_workflow.gates.blocker_audit import BlockerAudit
from ci_workflow.storage.event_store import EventStore

ROOT = Path(__file__).resolve().parents[2]

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_UNIVERSE_TEXT = '{"products": []}\n'


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ─── FX05 临时 catalog/案例构建 ─────────────────────────────────────────────


def _write_case(case_root: Path) -> None:
    inputs_dir = case_root / "inputs"
    inputs_dir.mkdir(parents=True)
    (inputs_dir / "universe.json").write_text(_UNIVERSE_TEXT, encoding="utf-8")


def _case_entry(
    case_id: str,
    *,
    input_path: str = "inputs/universe.json",
    sha256: str | None = None,
    case_digest: str | None = None,
) -> dict[str, Any]:
    desc = f"{case_id} 测试案例"
    input_sha = sha256 or _sha256_bytes(_UNIVERSE_TEXT.encode("utf-8"))
    fields = {
        "id": case_id,
        "description_zh": desc,
        "indication": "非小细胞肺癌",
        "timezone": "Asia/Shanghai",
        "data_cutoff": "2026-07-31",
        "created_at": "2026-08-12T10:00:00+08:00",
        "reports": ["A"],
        "outputs": ["html"],
        "inputs": [{"path": input_path, "role": "universe_closure", "sha256": input_sha}],
        "expected": {"report": "A", "report_version": "v1", "outcome": "evidence_blocked"},
    }
    digest = case_digest or _sha256_bytes(
        json.dumps(
            fields,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return {**fields, "case_digest": digest}


def _write_catalog(path: Path, entries: list[dict[str, Any]]) -> None:
    path.write_text(
        yaml.safe_dump(
            {"schema_version": "1.0", "cases": entries},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def test_fixture_registry_rejects_unknown_duplicate_or_tampered_case(
    tmp_path: Path,
) -> None:
    """FX05：catalog 是唯一注册表，未知名/重名/逃逸/缺失/多余/摘要不符全部拒绝。"""
    cases_root = tmp_path / "cases"
    catalog_path = tmp_path / "catalog.yaml"

    def expect_rejection(label: str, entries: list[dict[str, Any]]) -> None:
        _write_catalog(catalog_path, entries)
        with pytest.raises(FixtureCaseError):
            validate_catalog(catalog_path, case_root_base=cases_root)

    # 1. 未知名：catalog 声明了案例目录不存在的案例
    expect_rejection("unknown case name", [_case_entry("ghost-case")])

    # 2. 重名：同一案例 ID 出现两次
    _write_case(cases_root / "dup-case")
    expect_rejection(
        "duplicate case id",
        [_case_entry("dup-case"), _case_entry("dup-case")],
    )

    # 3. 输入路径逃逸案例目录（.. 跳转）
    _write_case(cases_root / "escape-case")
    expect_rejection(
        "input path escape",
        [_case_entry("escape-case", input_path="inputs/../../escape.json")],
    )

    # 4. 输入文件缺失：目录存在但声明的输入文件不存在
    _write_case(cases_root / "missing-input-case")
    (cases_root / "missing-input-case" / "inputs" / "universe.json").unlink()
    expect_rejection("missing input file", [_case_entry("missing-input-case")])

    # 5. inputs/ 目录存在未声明文件
    _write_case(cases_root / "extra-file-case")
    (cases_root / "extra-file-case" / "inputs" / "extra.json").write_text(
        "{}",
        encoding="utf-8",
    )
    expect_rejection("undeclared input file", [_case_entry("extra-file-case")])

    # 6. 输入 SHA-256 与真实文件内容不符
    _write_case(cases_root / "hash-mismatch-case")
    expect_rejection(
        "input sha256 mismatch",
        [_case_entry("hash-mismatch-case", sha256="0" * 64)],
    )

    # 7. case_digest 非法（内容绑定摘要被替换）
    _write_case(cases_root / "digest-case")
    expect_rejection(
        "invalid case digest",
        [_case_entry("digest-case", case_digest="1" * 64)],
    )

    # 8. schema 非法：created_at 缺少明确时区偏移
    _write_case(cases_root / "schema-invalid-case")
    expect_rejection(
        "schema invalid naive created_at",
        [
            {
                **_case_entry("schema-invalid-case"),
                "created_at": "2026-08-12T10:00:00",
            }
        ],
    )


# ─── FX06 阻断包重验证（与既有 no-draft 测试一致的位置感知剥离）────────────


# 各模型的计算摘要键（按所在模型判定）：BlockerAudit 顶层只有 audit_digest；
# empty_evidence 顶层 evidence_digest；其 exhaustion 及其嵌套缺口/复核/诊断为
# 计算键；per_gap_audits.gap_digest 是真实存储字段，不得剥离。
_COMPUTED_BY_PARENT: dict[tuple[str, ...], frozenset[str]] = {
    (): frozenset({"audit_digest"}),
    ("empty_evidence",): frozenset({"evidence_digest", "universe_closure_digest"}),
    ("empty_evidence", "exhaustion"): frozenset({"record_digest"}),
    ("empty_evidence", "exhaustion", "gaps", "<item>"): frozenset(
        {"gap_digest", "reviewer_inputs_digest"}
    ),
    ("empty_evidence", "exhaustion", "gaps", "<item>", "omission_review"): frozenset(
        {"conclusion_digest"}
    ),
    (
        "empty_evidence",
        "exhaustion",
        "gaps",
        "<item>",
        "technical_diagnosis",
    ): frozenset({"diagnosis_digest"}),
    (
        "empty_evidence",
        "exhaustion",
        "gaps",
        "<item>",
        "same_path_retry_audit",
    ): frozenset(),
    (
        "empty_evidence",
        "exhaustion",
        "gaps",
        "<item>",
        "alternative_path_audit",
    ): frozenset(),
}


def _strip_computed(node: object, path: tuple[str, ...] = ()) -> object:
    """按模型位置剔除计算字段后供 Pydantic 重读（写出的 JSON 含计算摘要）。"""
    if isinstance(node, dict):
        computed = _COMPUTED_BY_PARENT.get(path, frozenset())
        return {
            key: _strip_computed(value, (*path, key))
            for key, value in node.items()
            if key not in computed
        }
    if isinstance(node, list):
        return [_strip_computed(item, (*path, "<item>")) for item in node]
    return node


def _load_audit_json(path: Path) -> BlockerAudit:
    payload = _strip_computed(json.loads(path.read_text(encoding="utf-8")))
    return BlockerAudit.model_validate(payload)


def test_no_draft_a_empty_case_records_case_digest_and_current_run_id(
    tmp_path: Path,
) -> None:
    """FX06：no-draft-a-empty 真实运行绑定 case digest/run_id/输入哈希，只产阻断包。"""
    project_root = tmp_path / "项目"
    result = run_fixture_case(
        "no-draft-a-empty",
        project_root=project_root,
        reports=["A"],
        outputs=["html"],
    )
    run_result = result.run_result
    assert run_result.outcome == "evidence_blocked"
    assert run_result.exit_code == 4

    manifest_path = project_root / "manifests" / "current_run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # 当前 run_id 唯一且与事件流一致
    assert run_result.run_id.strip()
    assert manifest["run_id"] == run_result.run_id
    events = EventStore(project_root).read_all()
    assert events
    assert {event.run_id for event in events} == {run_result.run_id}

    # case digest 绑定：清单记录值与 runner 返回值一致
    assert manifest["case_digest"] == result.case_digest

    # 真实输入哈希：与唯一 catalog 案例输入文件内容一致
    input_hashes = manifest["input_hashes"]
    assert _SHA256_RE.fullmatch(input_hashes["inputs/universe.json"])
    assert _SHA256_RE.fullmatch(run_result.input_hashes["inputs/universe.json"])
    real_input = ROOT / "fixtures" / "synthetic" / "no-draft-a-empty" / "inputs" / "universe.json"
    assert input_hashes["inputs/universe.json"] == _sha256_bytes(real_input.read_bytes())

    # 当前 manifest 摘要必须由同 run_id 的 run.manifest.recorded 事件精确绑定
    recorded_events = [
        event
        for event in events
        if event.event_type == MANIFEST_RECORDED_EVENT and event.run_id == run_result.run_id
    ]
    assert len(recorded_events) == 1
    recorded = recorded_events[0].payload
    assert recorded["manifest_relative_path"] == MANIFEST_RELATIVE_PATH
    assert recorded["manifest_digest"] == manifest["manifest_digest"]
    assert recorded["case_id"] == "no-draft-a-empty"
    assert recorded["case_digest"] == result.case_digest
    assert recorded["input_hashes_digest"] == compute_input_hashes_digest(manifest["input_hashes"])
    assert recorded["pre_record_event_stream_digest"] == manifest["event_stream_digest"]
    assert recorded["pre_record_event_count"] == manifest["event_count"]
    pre_record = tuple(
        event
        for event in events
        if event.run_id == run_result.run_id and event.event_type != MANIFEST_RECORDED_EVENT
    )
    assert recorded["pre_record_event_count"] == len(pre_record)
    assert recorded["pre_record_event_stream_digest"] == compute_event_stream_digest(pre_record)

    # 阻断包：audit.json 可经 BlockerAudit 重验证；audit.md 为原生中文
    audit_json = project_root / "blockers" / "A" / "v1" / "audit.json"
    audit_md = project_root / "blockers" / "A" / "v1" / "audit.md"
    assert audit_json.is_file()
    audit = _load_audit_json(audit_json)
    assert audit.report_kind.value == "A"
    assert audit.source_links == ()
    assert "NCT01234567" not in audit_json.read_text(encoding="utf-8")
    markdown = audit_md.read_text(encoding="utf-8")
    assert _CJK_RE.search(markdown)
    assert "证据不足" in markdown

    # 无报告版本目录/占位文件；产物清单无 artifact 条目
    report_root = project_root / "reports" / "A"
    assert not (report_root / "v1").exists()
    assert list(report_root.rglob("*")) == []
    artifact_manifest = json.loads(
        (project_root / "manifests" / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert artifact_manifest["artifacts"] == []

    # 节点完成事件：intake/preflight/universe/gate:A/recovery:A
    completed = {
        (event.payload["node_id"], event.payload.get("report_kind"))
        for event in events
        if event.event_type == "graph.node.completed"
    }
    assert ("intake", None) in completed
    assert ("preflight", None) in completed
    assert ("universe", None) in completed
    assert ("gate", "A") in completed
    assert ("recovery", "A") in completed

    # 报告证据迁移：report_A queued→collecting→evidence_blocked
    report_transitions = {
        (event.payload["from_state"], event.payload["to_state"])
        for event in events
        if event.event_type == "graph.transition.accepted"
        and event.payload["family"] == "report_evidence"
    }
    assert ("queued", "collecting") in report_transitions
    assert ("collecting", "evidence_blocked") in report_transitions

    # 项目进入阻断终态（blocked）
    project_blocked = [
        event
        for event in events
        if event.event_type == "graph.transition.accepted"
        and event.payload["family"] == "project"
        and event.payload["to_state"] == "blocked"
    ]
    assert project_blocked

    # 无报告快照/格式任务/HTML 占位：不存在 snapshot/format/acceptance 等完成事件，
    # 无 artifact 发布/移动事件，无 coverage-projection 文件
    forbidden_nodes = {"snapshot", "format", "acceptance", "scientific_qc", "analyze"}
    completed_nodes = {
        event.payload["node_id"] for event in events if event.event_type == "graph.node.completed"
    }
    assert not (forbidden_nodes & completed_nodes)
    assert not any(event.event_type in {"artifact.publish", "artifact.move"} for event in events)
    assert not any(
        path.name.endswith(".coverage-projection.json")
        for path in (project_root / "reports").rglob("*")
        if path.is_file()
    )


def test_a_complete_case_is_registered_hashed_and_bound_to_current_run(
    tmp_path: Path,
) -> None:
    """Task 5.4：a-complete 的输入、案例、当前运行、11+P 站点与清单闭合。"""
    project_root = tmp_path / "完整门户"
    result = run_fixture_case(
        "a-complete",
        project_root=project_root,
        reports=["A"],
        outputs=["html"],
    )
    assert result.run_result.outcome == "completed"
    run_manifest = json.loads((project_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    artifact_manifest = json.loads(
        (project_root / "reports/A/v-fixture-001/html.manifest.json").read_text(encoding="utf-8")
    )
    assert run_manifest["run_id"] == result.run_result.run_id
    assert run_manifest["case_id"] == "a-complete"
    assert run_manifest["case_digest"] == result.case_digest
    assert run_manifest["input_hashes"] == result.run_result.input_hashes
    assert artifact_manifest["producer_run_id"] == result.run_result.run_id
    assert artifact_manifest["status"] == "generated"
    assert artifact_manifest["accepted_by"] is None
    assert len(artifact_manifest["product_ids"]) == 4
    assert len(artifact_manifest["pages_or_sections"]) == 11
    site = project_root / "reports/A/v-fixture-001/html"
    assert len(list(site.glob("*.html"))) == 11
    assert len(list((site / "products").glob("*.html"))) == 4
    assert all(_SHA256_RE.fullmatch(value) for value in run_manifest["input_hashes"].values())


def test_three_report_complete_case_is_registered_hashed_and_bound_to_current_run() -> None:
    """Task 8.2：three-report-complete 注册、逐文件摘要、实体计数与 GateSpec 预期锁定。"""
    catalog = validate_catalog(ROOT / "fixtures/catalog.yaml")
    cases = {case["id"]: case for case in catalog["cases"]}
    assert "three-report-complete" in cases

    case = cases["three-report-complete"]
    case_dir = ROOT / "fixtures/synthetic/three-report-complete"
    assert case["indication"] == "特应性皮炎"
    assert case["reports"] == ["A", "B", "C"]
    assert sorted(case["outputs"]) == ["html"]
    assert case["expected"]["report_version"] == "v-fixture-001"
    assert case["expected"]["outcome"] == "rendered"
    assert case["expected"]["state"] == "rendered_unreviewed"

    declared_paths = {item["path"] for item in case["inputs"]}
    required_paths = {
        "inputs/report-a-data.json",
        "inputs/report-b-data.json",
        "inputs/report-c-data.json",
        "inputs/entity-counts.json",
        "inputs/gate-spec-expected.json",
        "inputs/coverage-set-expected.json",
        "inputs/run-binding-contract.json",
    }
    assert required_paths <= declared_paths

    actual_files = {
        str(path.relative_to(case_dir).as_posix()) for path in case_dir.rglob("*") if path.is_file()
    }
    assert actual_files == declared_paths

    input_hashes: dict[str, str] = {}
    for declaration in case["inputs"]:
        path = case_dir / declaration["path"]
        digest = _sha256_bytes(path.read_bytes())
        assert digest == declaration["sha256"]
        assert _SHA256_RE.fullmatch(digest)
        input_hashes[declaration["path"]] = digest

    report_payloads = {
        "A": json.loads((case_dir / "inputs/report-a-data.json").read_text(encoding="utf-8")),
        "B": json.loads((case_dir / "inputs/report-b-data.json").read_text(encoding="utf-8")),
        "C": json.loads((case_dir / "inputs/report-c-data.json").read_text(encoding="utf-8")),
    }
    assert {payload["indication"] for payload in report_payloads.values()} == {"特应性皮炎"}
    assert {payload["report_version"] for payload in report_payloads.values()} == {"v-fixture-001"}
    assert report_payloads["B"]["report_snapshot_id"] == "snapshot-three-report-complete-001"
    assert report_payloads["C"]["report_snapshot_id"] == "snapshot-three-report-complete-001"

    entity_counts = json.loads((case_dir / "inputs/entity-counts.json").read_text(encoding="utf-8"))
    assert entity_counts["indication"] == "特应性皮炎"
    assert entity_counts["report_snapshot_id"] == "snapshot-three-report-complete-001"
    assert entity_counts["A"]["products"] == len(report_payloads["A"]["products"])
    assert entity_counts["A"]["trials"] == len(report_payloads["A"]["trials"])
    assert entity_counts["A"]["efficacy_rows"] == len(report_payloads["A"]["efficacy"])
    assert entity_counts["A"]["safety_rows"] == len(report_payloads["A"]["safety"])
    assert entity_counts["B"]["products"] == len(report_payloads["B"]["products"])
    assert entity_counts["B"]["baseline_facts"] == len(
        report_payloads["B"]["baseline_views"]["facts"]
    )
    assert entity_counts["B"]["disposition_facts"] == len(
        report_payloads["B"]["disposition_views"]["facts"]
    )
    assert entity_counts["C"]["products"] == len(report_payloads["C"]["products"])
    assert entity_counts["C"]["observations"] == len(report_payloads["C"]["observations"])

    gate_expected = json.loads(
        (case_dir / "inputs/gate-spec-expected.json").read_text(encoding="utf-8")
    )
    assert gate_expected["specs"]["A"]["spec_id"] == "gate-spec-a-v1"
    assert gate_expected["specs"]["B"]["spec_id"] == "gate-spec-b-v1"
    assert gate_expected["specs"]["C"]["spec_id"] == "gate-spec-c-v1"
    assert all(
        gate_expected["specs"][kind]["expected_result"] == "passed" for kind in ("A", "B", "C")
    )
    assert gate_expected["specs"]["B"]["baseline_gate_failures"] == []

    coverage_expected = json.loads(
        (case_dir / "inputs/coverage-set-expected.json").read_text(encoding="utf-8")
    )
    assert coverage_expected["reports"]["A"]["page_responsibility_count"] == 11
    assert coverage_expected["reports"]["B"]["page_responsibility_count"] == 20
    assert coverage_expected["reports"]["C"]["page_responsibility_count"] == 11

    binding = json.loads(
        (case_dir / "inputs/run-binding-contract.json").read_text(encoding="utf-8")
    )
    assert binding["case_id"] == "three-report-complete"
    assert binding["reports"] == ["A", "B", "C"]
    assert sorted(binding["outputs"]) == ["html"]
    assert binding["input_hashes"] == {
        path: digest
        for path, digest in input_hashes.items()
        if path != "inputs/run-binding-contract.json"
    }
    assert binding["case_digest"] is None
    assert case["case_digest"] == (
        "66ca7a36cc38701ae54ad2c84d2c898e4fca0abeb97d9c015b4b349b620d55aa"
    )
    assert _SHA256_RE.fullmatch(case["case_digest"])

    from ci_workflow.renderers.portal.report_a import load_report_a_data
    from ci_workflow.renderers.portal.report_b import (
        load_report_b_data,
        report_b_baseline_gate_failures,
    )
    from ci_workflow.renderers.portal.report_c import load_report_c_data

    load_report_a_data(case_dir / "inputs/report-a-data.json")
    report_b = load_report_b_data(case_dir / "inputs/report-b-data.json")
    load_report_c_data(case_dir / "inputs/report-c-data.json")
    assert report_b_baseline_gate_failures(report_b) == ()

    project_root = ROOT / "tmp/pdfs/three-report-complete-bound-run"
    if project_root.exists():
        import shutil

        shutil.rmtree(project_root)

    result = run_fixture_case(
        "three-report-complete",
        project_root=project_root,
        reports=["A", "B", "C"],
        outputs=["html"],
    )
    assert result.run_result.outcome == "completed"
    assert result.case_id == "three-report-complete"
    assert result.case_digest == case["case_digest"]
    assert result.run_result.case_digest == case["case_digest"]
    assert result.run_result.input_hashes == input_hashes

    run_manifest = json.loads((project_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert run_manifest["run_id"] == result.run_result.run_id
    assert run_manifest["case_id"] == "three-report-complete"
    assert run_manifest["case_digest"] == case["case_digest"]
    assert run_manifest["input_hashes"] == input_hashes
    assert run_manifest["outcome"] == "completed"
    assert all(_SHA256_RE.fullmatch(value) for value in run_manifest["input_hashes"].values())

    # 锁定合同文件继续约束实体计数 / GateSpec / 覆盖责任
    assert entity_counts["A"]["page_responsibilities"] == 11
    assert entity_counts["B"]["page_responsibilities"] == 20
    assert entity_counts["C"]["page_responsibilities"] == 11
    assert gate_expected["specs"]["A"]["expected_result"] == "passed"
    assert coverage_expected["reports"]["B"]["page_responsibility_count"] == 20

    html_outputs = {
        item["relative_path"]: item
        for item in run_manifest["outputs"]
        if item["relative_path"].endswith("/html.manifest.json")
    }
    expected_html_manifests = {
        "reports/A/v-fixture-001/html.manifest.json",
        "reports/B/v-fixture-001/html.manifest.json",
        "reports/C/v-fixture-001/html.manifest.json",
    }
    assert set(html_outputs) == expected_html_manifests
    for rel, item in html_outputs.items():
        absolute = project_root / rel
        assert absolute.is_file()
        assert item["sha256"] == _sha256_bytes(absolute.read_bytes())
        assert item["media_type"] == "application/json"
        assert _SHA256_RE.fullmatch(item["sha256"])
        assert (absolute.parent / "html").is_dir()


def test_host_smoke_v1_is_registered_hashed_and_binds_current_run_receipts(
    tmp_path: Path,
) -> None:
    """Task 9.4 HA10：host-smoke-v1 唯一 catalog 登记、逐文件摘要、case digest
    与三宿主 current receipt 绑定。

    本节点为**源码级合同验证**（source-contract）：三宿主回执经真实安装入口
    的外部子进程产生，但宿主可执行文件是显式测试替身，``real_host_pass``
    必须为假；fresh-install 下的真实三宿主实跑验收属 Task 9.5，用同一合同
    复验，本节点不主张真实宿主通过。
    """
    import stat

    from ci_workflow.application.host_smoke import (
        HOSTS,
        run_host_smoke,
        verify_host_smoke_batch,
        verify_host_smoke_receipt,
    )
    from ci_workflow.hosts.receipt import HostReceipt

    # 唯一 catalog：登记、逐文件摘要与 case digest 由 validate_catalog 整体锁定
    catalog = validate_catalog(ROOT / "fixtures" / "catalog.yaml")
    cases = {case["id"]: case for case in catalog["cases"]}
    assert sum(1 for case_id in cases if case_id == "host-smoke-v1") == 1
    case = cases["host-smoke-v1"]
    assert case["expected"]["outcome"] == "evidence_blocked"
    case_dir = ROOT / "fixtures" / "synthetic" / "host-smoke-v1"
    for declared in case["inputs"]:
        actual = _sha256_bytes((case_dir / declared["path"]).read_bytes())
        assert actual == declared["sha256"]

    doubles = tmp_path / "bin"
    doubles.mkdir()
    receipts: dict[str, HostReceipt] = {}
    roots: dict[str, Path] = {}
    for host in HOSTS:
        double = doubles / host
        double.write_text(
            f'#!/bin/sh\necho "{host}-fixture-contract-double 1.0.0"\n', encoding="utf-8"
        )
        double.chmod(double.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        root = tmp_path / f"项目-{host}"
        receipts[host] = run_host_smoke(host, project_root=root, host_executable=double)
        roots[host] = root

    for host in HOSTS:
        receipt = receipts[host]
        verify_host_smoke_receipt(receipt, project_root=roots[host])
        # 回执 fixture 绑定 == 唯一 catalog 声明
        assert receipt.fixture.case_id == "host-smoke-v1"
        assert receipt.fixture.case_digest == case["case_digest"]
        assert dict(receipt.fixture.inputs) == {
            declared["path"]: declared["sha256"] for declared in case["inputs"]
        }
        # 回执运行绑定 == 项目当前 manifest / 事件链
        current_manifest = json.loads(
            (roots[host] / "manifests" / "current_run.json").read_text(encoding="utf-8")
        )
        assert receipt.run.run_id == current_manifest["run_id"]
        assert current_manifest["case_digest"] == case["case_digest"]
        assert receipt.manifest.sha256 == _sha256_bytes(
            (roots[host] / "manifests" / "current_run.json").read_bytes()
        )
        # 阻断语义：零草稿、零产物
        assert receipt.run.state == "blocked"
        assert receipt.run.no_draft is True
        assert receipt.run.artifacts == ()

    run_ids = {receipts[host].run.run_id for host in HOSTS}
    assert len(run_ids) == len(HOSTS)

    verdict = verify_host_smoke_batch(receipts, project_roots=roots)
    assert all(verdict.statuses[host] == "verified" for host in HOSTS)
    assert verdict.real_host_pass is False
