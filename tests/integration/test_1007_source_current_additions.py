"""产品回归根因族：来源当前刷新的可选来源新增条目（ci-1007-source-current-additions-v1）。

根因：既有 ``source_current_refresh`` 只支持同一逻辑事实的来源替换，
``_new_active_ids`` 永远不会接纳新原子；新接受来源原子无法以“新增逻辑事实”接
入当前交付。修复必须扩展既有刷新事务（而非重置/重新初始化/publish 旁路），并
满足：

- 新增条目携带显式事实/版本/来源身份，没有伪造的旧 current 版本；至少一条替换
  或新增；集合内与集合间重复禁止；仅替换请求的请求哈希保持向后兼容。
- 新增必须是已接受、非用户层原子，具备主证据片段；消费者必须按本次请求钉固的
  普通 builder 输入快照作用域解析，不能沿用旧 current 快照或任意最新声明。
- 旧活动事实、用户修订/清除层与未受影响的 C 整体保留；只并集新接受的标识。
- 坏载荷（候选/用户层/身份占用/取值/来源漂移/快照作用域缺失/重复/过期版本）
  失败关闭且不切换 current；精确重放幂等。

所有断言读取实际持久化的字节：SQLite 行、current bundle、门户投影、消费者回执。
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from ci_workflow.application.source_current_refresh import (
    ReportCode,
    SourceCurrentRefreshCommand,
    SourceCurrentRefreshConflictError,
    SourceCurrentRefreshService,
    SourceFactAddition,
    SourceFactRefusalError,
    SourceFactReplacement,
    SourceReportBuilderInput,
)
from ci_workflow.application.user_fact_edit import FactEdit
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
    canonical_source_pointer,
)
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    active_fact_binding_for_a,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    active_fact_binding_for_b,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_source_current_refresh import (
    _delivery,
    _projection_any,
    _read_current,
    _site_hashes,
    _source_atom_count,
    _world,
)
from tests.integration.test_w04_user_fact_edit import (
    NOW,
    PROJECT_ID,
    _seed_fact,
)

ADDITION_FACT_ID = "fact-serious-teae"
ADDITION_VERSION = "fact-serious-teae-v1"
ADDITION_SOURCE_VERSION = "nct04558918-safety-report-addition-v1"
ADDITION_ROW_ID = "safe-addition-t-1"
ADDITION_TERM = "严重TEAE（SAE）"
ADDITION_VALUE = 41.9
ADDITION_RAW = "41.9% (26/62)"
ADDITION_NORMALIZED = "41.9"
ADDITION_NUMERATOR = 26
ADDITION_DENOMINATOR = 62
SNAPSHOT_DEVELOPMENT = "evidence-snapshot-development"
SNAPSHOT_STALE = "evidence-snapshot-additions-stale"
SNAPSHOT_NEW = "evidence-snapshot-additions-new"
BINDING_KIND = "source-portal-binding"
AT = NOW + timedelta(minutes=7)


def _inputs_from_paths(root: Path, paths: dict[str, str]) -> dict[str, SourceReportBuilderInput]:
    return {
        report: SourceReportBuilderInput(
            report=cast(ReportCode, report),
            input_relative_path=paths[report],
            input_sha256=hashlib.sha256((root / paths[report]).read_bytes()).hexdigest(),
        )
        for report in paths
    }


def _current_inputs(root: Path) -> dict[str, SourceReportBuilderInput]:
    """Declared builder inputs pointing at the committed current inputs (valid bytes)."""
    current = _read_current(root)
    inputs: dict[str, SourceReportBuilderInput] = {}
    for report in ("A", "B"):
        delivery = next(item for item in current.reports if item.report == report)
        assert delivery.builder_input_relative_path is not None
        assert delivery.builder_input_sha256 is not None
        inputs[report] = SourceReportBuilderInput(
            report=cast(ReportCode, report),
            input_relative_path=delivery.builder_input_relative_path,
            input_sha256=delivery.builder_input_sha256,
        )
    return inputs


def _append_addition_inputs(
    root: Path, *, snapshot: str | None, tag: str = "addition-1",
) -> dict[str, str]:
    """Ordinary new A/B builder inputs adding one consumed safety row.

    The new row reuses the shared source pointer of the existing consumer row so
    the added atom has one identical logical source across A and B, exactly like
    a newly acquired source page that carries an additional event row.
    """
    payloads: dict[str, dict[str, Any]] = {}
    for report in ("A", "B"):
        delivery = _delivery(root, report)
        assert delivery.builder_input_relative_path is not None
        payloads[report] = json.loads(
            (root / delivery.builder_input_relative_path).read_bytes()
        )
    view_source = payloads["B"]["safety_views"]["facts"]
    base_view = next(row for row in view_source if row["row_id"] == "safe-apply-t-1")
    locator = dict(base_view["source_locator"])
    locator["field_path"] = f"nct04558918/safety/{ADDITION_ROW_ID}"
    locator["row"] = ADDITION_ROW_ID
    pointer = canonical_source_pointer(locator)
    for report in ("A", "B"):
        payload = payloads[report]
        base_row = next(row for row in payload["safety"] if row["row_id"] == "safe-apply-t-1")
        row = dict(base_row)
        row.update(
            row_id=ADDITION_ROW_ID,
            term=ADDITION_TERM,
            value=ADDITION_VALUE,
            numerator=ADDITION_NUMERATOR,
            denominator=ADDITION_DENOMINATOR,
        )
        if report == "A":
            row["source_version_id"] = ADDITION_SOURCE_VERSION
            row["source_field_path"] = pointer
        payload["safety"].append(row)
        view = dict(base_view)
        view.update(
            row_id=ADDITION_ROW_ID,
            observation_id=f"observation-{ADDITION_ROW_ID}",
            source_term=ADDITION_TERM,
            term_id=ADDITION_TERM,
            raw_value=f"{ADDITION_NUMERATOR}/{ADDITION_DENOMINATOR}（{ADDITION_NORMALIZED}%）",
            value=ADDITION_VALUE,
            numerator=ADDITION_NUMERATOR,
            denominator=ADDITION_DENOMINATOR,
            source_version_id=ADDITION_SOURCE_VERSION,
            source_locator=locator,
        )
        payload["safety_views"]["facts"].append(view)
        if snapshot is not None:
            payload["source_evidence_snapshot_id"] = snapshot
    out_dir = root / "inputs" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for report, payload in payloads.items():
        path = out_dir / f"report-{report.lower()}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        paths[report] = path.relative_to(root).as_posix()
    return paths


def _addition_bindings(
    root: Path, paths: dict[str, str],
) -> tuple[ActiveFactBinding, ActiveFactBinding]:
    a_data = ReportAPortalData.model_validate_json((root / paths["A"]).read_bytes())
    b_data = ReportBPortalData.model_validate_json((root / paths["B"]).read_bytes())
    return (
        active_fact_binding_for_a(a_data, "safety", ADDITION_ROW_ID),
        active_fact_binding_for_b(b_data, "safety", ADDITION_ROW_ID),
    )


def _seed_addition_atom(
    root: Path,
    *,
    bindings: tuple[ActiveFactBinding, ...],
    snapshots: tuple[str, ...],
    review_state: str = "accepted",
    fact_id: str = ADDITION_FACT_ID,
    version_id: str = ADDITION_VERSION,
    source_version: str = ADDITION_SOURCE_VERSION,
    stale_variants: tuple[ActiveFactBinding, ...] = (),
) -> None:
    """Register one accepted addition atom with its snapshot-scoped consumers."""
    locator = bindings[0].source_pointer
    assert all(item.source_pointer == locator for item in bindings)
    fragment_id = f"fragment-{version_id}"
    quote = "26/62例受试者发生严重TEAE（41.9%）。"
    with open_database(root / "state/project.sqlite") as database:
        database.execute(
            "INSERT OR IGNORE INTO source_versions (source_version_id,source_id,content_sha256,"
            "acquired_at,created_at) VALUES (?,?,?,?,?)",
            (
                source_version,
                f"source-{hashlib.sha256(source_version.encode()).hexdigest()[:12]}",
                hashlib.sha256(source_version.encode()).hexdigest(),
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
        database.execute(
            "INSERT INTO evidence_fragments (fragment_id,source_version_id,locator,"
            "content_text,content_sha256,created_at) VALUES (?,?,?,?,?,?)",
            (
                fragment_id,
                source_version,
                locator,
                quote,
                hashlib.sha256(quote.encode()).hexdigest(),
                NOW.isoformat(),
            ),
        )
        _seed_fact(
            database,
            fact_id=fact_id,
            version_id=version_id,
            entity_id="entity-arm",
            field_id="safety.serious_teae",
            raw_value=ADDITION_RAW,
            normalized_value=ADDITION_NORMALIZED,
            fragment_id=fragment_id,
            context={
                "numerator": ADDITION_NUMERATOR,
                "denominator": ADDITION_DENOMINATOR,
                "raw_value": ADDITION_RAW,
                "normalized_value": ADDITION_NORMALIZED,
            },
            review_state=review_state,
        )
        rows: list[tuple[ActiveFactBinding, str]] = [
            (binding, snapshot) for snapshot in snapshots for binding in bindings
        ]
        rows.extend((variant, SNAPSHOT_STALE) for variant in stale_variants)
        for binding, snapshot in rows:
            binding_json = json.dumps(
                binding.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            database.execute(
                "INSERT INTO source_portal_consumer_bindings (binding_id,"
                "source_fact_version_id,evidence_snapshot_id,report,collection,row_id,"
                "binding_json,binding_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    stable_id(
                        BINDING_KIND,
                        version_id,
                        binding.report,
                        binding.collection,
                        binding.row_id,
                        snapshot,
                    ),
                    version_id,
                    snapshot,
                    binding.report,
                    binding.collection,
                    binding.row_id,
                    binding_json,
                    hashlib.sha256(binding_json.encode()).hexdigest(),
                    NOW.isoformat(),
                ),
            )


def _stale_binding(binding: ActiveFactBinding) -> ActiveFactBinding:
    return binding.model_copy(
        update={"original_row_sha256": hashlib.sha256(b"stale-declaration").hexdigest()}
    )


def _addition_command(
    world: Any,
    *,
    paths: dict[str, str] | None = None,
    inputs: dict[str, SourceReportBuilderInput] | None = None,
    additions: tuple[SourceFactAddition, ...] | None = None,
    request_id: str = "source-addition-1",
    expected_revision: int | None = None,
    declared_source: str = ADDITION_SOURCE_VERSION,
) -> SourceCurrentRefreshCommand:
    root = world.root
    if inputs is None:
        assert paths is not None
        inputs = _inputs_from_paths(root, paths)
    if additions is None:
        additions = (
            SourceFactAddition(
                fact_id=ADDITION_FACT_ID,
                fact_version_id=ADDITION_VERSION,
                source_version_id=declared_source,
                rationale_zh="来源再获取后的新增已接受原子，按既有刷新事务接入。",
            ),
        )
    revision = world.current.revision if expected_revision is None else expected_revision
    return SourceCurrentRefreshCommand(
        request_id=request_id,
        project_id=PROJECT_ID,
        expected_revision=revision,
        requested_by="source-refresh-worker",
        requested_at=AT,
        replacements=(),
        additions=additions,
        builder_inputs=tuple(inputs[report] for report in sorted(inputs)),
    )


def _receipt_consumers(root: Path, report: str) -> list[dict[str, Any]]:
    delivery = _delivery(root, report)
    receipt = json.loads(
        (root / delivery.site_relative_path / "data/consumer-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    return [item for item in receipt["consumers"] if isinstance(item, dict)]


def _user_row_snapshot(root: Path, fact_version_id: str) -> tuple[Any, ...]:
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT raw_value,normalized_value,content_sha256,scientific_context_json "
            "FROM fact_versions WHERE fact_version_id=?",
            (fact_version_id,),
        ).fetchone()
    assert row is not None
    return tuple(row)


# ── 1. 合同与向后兼容 ───────────────────────────────────────────────────────


def _replacement() -> SourceFactReplacement:
    return SourceFactReplacement(
        fact_id="fact-contract",
        current_fact_version_id="fact-contract-v1",
        replacement_fact_version_id="fact-contract-v2",
        replacement_source_version_id="source-contract-v2",
        rationale_zh="合同测试替换。",
    )


def _addition(fact_id: str, version_id: str) -> SourceFactAddition:
    return SourceFactAddition(
        fact_id=fact_id,
        fact_version_id=version_id,
        source_version_id="source-contract-v2",
        rationale_zh="合同测试新增。",
    )


def _contract_input() -> SourceReportBuilderInput:
    return SourceReportBuilderInput(
        report="A",
        input_relative_path="inputs/report-a.json",
        input_sha256="0" * 64,
    )


def _contract_command(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "request_id": "contract-request",
        "project_id": "contract-project",
        "expected_revision": 0,
        "requested_by": "contract-worker",
        "requested_at": AT,
        "replacements": (_replacement(),),
        "builder_inputs": (_contract_input(),),
    }
    base.update(overrides)
    return base


def test_addition_contract_rejects_duplicate_and_empty_sets() -> None:
    with pytest.raises(ValidationError, match="同一刷新请求"):
        SourceCurrentRefreshCommand(**_contract_command(replacements=(), additions=()))
    with pytest.raises(ValidationError, match="同一逻辑事实只能有一条新增"):
        SourceCurrentRefreshCommand(
            **_contract_command(
                replacements=(),
                additions=(
                    _addition("fact-a", "fact-a-v1"),
                    _addition("fact-a", "fact-a-v2"),
                ),
            )
        )
    with pytest.raises(ValidationError, match="同一来源事实版本只能新增一次"):
        SourceCurrentRefreshCommand(
            **_contract_command(
                replacements=(),
                additions=(
                    _addition("fact-a", "fact-a-v1"),
                    _addition("fact-b", "fact-a-v1"),
                ),
            )
        )
    with pytest.raises(ValidationError, match="不能同时作为替换与新增"):
        SourceCurrentRefreshCommand(
            **_contract_command(
                additions=(_addition("fact-contract", "fact-other-v1"),),
            )
        )
    with pytest.raises(ValidationError, match="不能同时作为替换与新增"):
        SourceCurrentRefreshCommand(
            **_contract_command(
                additions=(_addition("fact-other", "fact-contract-v2"),),
            )
        )


def test_replacement_only_request_hash_stays_backward_compatible() -> None:
    command = SourceCurrentRefreshCommand(**_contract_command())
    dumped = command.model_dump(mode="json", exclude_unset=True)
    assert "additions" not in dumped
    rebuilt = SourceCurrentRefreshCommand.model_validate(
        command.model_dump(mode="python", exclude_unset=True)
    )
    assert "additions" not in rebuilt.model_dump(mode="json", exclude_unset=True)
    replay = SourceCurrentRefreshCommand(
        **_contract_command(additions=(), replacements=(_replacement(),))
    )
    assert "additions" in replay.model_dump(mode="json", exclude_unset=True)


# ── 2. 新增成功路径：旧事实/用户层/C 保留，A+B 同代更新，重放幂等 ────────────


def test_addition_appends_accepted_atom_preserving_user_layer_and_c(tmp_path: Path) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    assert world.current.revision == 1
    old_active = world.current.active_fact_version_ids
    c_before = _delivery(root, "C")
    c_hashes = _site_hashes(root, c_before)
    user_before = _user_row_snapshot(root, user_version)

    paths = _append_addition_inputs(root, snapshot=SNAPSHOT_DEVELOPMENT)
    bindings = _addition_bindings(root, paths)
    _seed_addition_atom(root, bindings=bindings, snapshots=(SNAPSHOT_DEVELOPMENT,))
    facts_before = _source_atom_count(root)
    command = _addition_command(world, paths=paths)

    result = SourceCurrentRefreshService(root).refresh(command)

    assert result.revision == 2
    assert result.rebuilt_reports == ("A", "B")
    assert result.effective_fact_version_ids == {ADDITION_FACT_ID: ADDITION_VERSION}
    assert result.appended_fact_version_ids == (ADDITION_VERSION,)
    assert result.replacement_source_version_ids == ()
    current = _read_current(root)
    assert current.revision == 2 and current.request_id == command.request_id
    # 只并集新接受标识：旧活动/用户层标识逐一保留并保持顺序。
    assert current.active_fact_version_ids == (*old_active, ADDITION_VERSION)
    # 用户层与未受影响 C 逐字节保持；不重复版本。
    assert _user_row_snapshot(root, user_version) == user_before
    assert _delivery(root, "C") == c_before
    assert _site_hashes(root, c_before) == c_hashes
    assert _source_atom_count(root) == facts_before
    # 门户投影：用户修订仍在，新增行按真实来源值出现。
    projection_a = _projection_any(root, "A")
    user_row = next(item for item in projection_a["safety"] if item["row_id"] == "safe-apply-t-1")
    assert user_row["value"] == 30.0
    assert projection_a["user_edits"]["safe-apply-t-1"]["status_label_zh"] == (
        "用户修订，未独立复核"
    )
    added_a = next(item for item in projection_a["safety"] if item["row_id"] == ADDITION_ROW_ID)
    assert added_a["value"] == ADDITION_VALUE
    projection_b = _projection_any(root, "B")
    added_b = next(item for item in projection_b["safety"] if item["row_id"] == ADDITION_ROW_ID)
    assert added_b["value"] == ADDITION_VALUE
    row_b_user = next(item for item in projection_b["safety"] if item["row_id"] == "safe-apply-t-1")
    assert row_b_user["value"] == 30.0
    # 实际持久化回执证明 A/B 都消费了新增原子的同一逻辑身份。
    for report in ("A", "B"):
        consumers = [
            item
            for item in _receipt_consumers(root, report)
            if item["row_id"] == ADDITION_ROW_ID
        ]
        assert len(consumers) == 1
        assert consumers[0]["fact_id"] == ADDITION_FACT_ID
        assert consumers[0]["fact_version_id"] == ADDITION_VERSION
        assert _delivery(root, report).revision == 2
    # 精确重放幂等：同一命令返回同一回执，不再推进 current。
    replay = SourceCurrentRefreshService(root).refresh(command)
    assert replay == result
    assert _read_current(root) == current


# ── 3. 候选/用户层原子不允许作为新增 ────────────────────────────────────────


@pytest.mark.parametrize("review_state", ("candidate", "user_modified"))
def test_addition_requires_accepted_non_user_atom(
    tmp_path: Path, review_state: str,
) -> None:
    world = _world(tmp_path)
    root = world.root
    paths = _append_addition_inputs(root, snapshot=SNAPSHOT_DEVELOPMENT)
    bindings = _addition_bindings(root, paths)
    _seed_addition_atom(root, bindings=bindings, snapshots=(SNAPSHOT_DEVELOPMENT,),
                        review_state=review_state)

    with pytest.raises(SourceFactRefusalError, match=f"当前状态为{review_state}"):
        SourceCurrentRefreshService(root).refresh(_addition_command(world, paths=paths))

    assert _read_current(root) == world.current
    assert not tuple(root.glob("reports/*/v1-source-r*"))


# ── 4. 既有逻辑事实（含用户清除层）不能被新增身份偷渡 ───────────────────────


@pytest.mark.parametrize("user_edit", (True, False))
def test_addition_cannot_smuggle_existing_logical_fact(
    tmp_path: Path, user_edit: bool,
) -> None:
    world = _world(
        tmp_path,
        user_edit=user_edit,
        edits=FactEdit(raw_value=None) if user_edit else None,
    )
    root = world.root
    active_fact_id = "fact-crude-rate"
    smuggling_version = "fact-crude-rate-smuggle-v1"
    a_delivery = _delivery(root, "A")
    b_delivery = _delivery(root, "B")
    assert a_delivery.builder_input_relative_path is not None
    assert b_delivery.builder_input_relative_path is not None
    a_payload = ReportAPortalData.model_validate_json(
        (root / a_delivery.builder_input_relative_path).read_bytes()
    )
    b_payload = ReportBPortalData.model_validate_json(
        (root / b_delivery.builder_input_relative_path).read_bytes()
    )
    bindings = (
        active_fact_binding_for_a(a_payload, "safety", "safe-apply-t-1"),
        active_fact_binding_for_b(b_payload, "safety", "safe-apply-t-1"),
    )
    _seed_addition_atom(
        root,
        bindings=bindings,
        snapshots=(SNAPSHOT_DEVELOPMENT,),
        fact_id=active_fact_id,
        version_id=smuggling_version,
        source_version="nct04558918-safety-report-v1",
    )
    current_before = _read_current(root)
    user_rows_before = {
        version_id: _user_row_snapshot(root, version_id)
        for version_id in current_before.active_fact_version_ids
    }

    with pytest.raises(SourceFactRefusalError, match="不能作为新增条目"):
        SourceCurrentRefreshService(root).refresh(
            _addition_command(
                world,
                inputs=_current_inputs(root),
                additions=(
                    SourceFactAddition(
                        fact_id=active_fact_id,
                        fact_version_id=smuggling_version,
                        source_version_id="nct04558918-safety-report-v1",
                        rationale_zh="偷渡尝试：既有逻辑事实伪装成新增。",
                    ),
                ),
                request_id=f"source-addition-smuggle-{int(user_edit)}",
            )
        )

    assert _read_current(root) == current_before
    for version_id, row in user_rows_before.items():
        assert _user_row_snapshot(root, version_id) == row
    assert not tuple(root.glob("reports/*/v1-source-r*"))


# ── 5. 新原子消费者按本次钉固输入快照作用域解析，不沿用旧 current ───────────


def test_addition_consumers_resolve_under_new_pinned_snapshot_scope(tmp_path: Path) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    paths = _append_addition_inputs(root, snapshot=SNAPSHOT_NEW)
    fresh = _addition_bindings(root, paths)
    stale = tuple(_stale_binding(binding) for binding in fresh)
    _seed_addition_atom(
        root,
        bindings=fresh,
        snapshots=(SNAPSHOT_NEW,),
        stale_variants=stale,
    )
    command = _addition_command(world, paths=paths, request_id="source-addition-scope")

    result = SourceCurrentRefreshService(root).refresh(command)

    assert result.revision == 2
    assert result.rebuilt_reports == ("A", "B")
    fresh_digests = {binding.original_row_sha256 for binding in fresh}
    stale_digest = stale[0].original_row_sha256
    for report in ("A", "B"):
        consumers = [
            item
            for item in _receipt_consumers(root, report)
            if item["row_id"] == ADDITION_ROW_ID
        ]
        assert len(consumers) == 1
        assert consumers[0]["binding_identity"]["original_row_sha256"] in fresh_digests
        assert consumers[0]["binding_identity"]["original_row_sha256"] != stale_digest
        assert consumers[0]["binding_identity"]["report"] == report
    # 新增条目的公开投影保持旧 current 事实与用户层不受影响。
    projection = _projection_any(root, "A")
    assert any(item["row_id"] == "safe-apply-t-1" for item in projection["safety"])
    assert any(item["row_id"] == ADDITION_ROW_ID for item in projection["safety"])


def test_addition_missing_exact_scope_consumer_refuses_without_dropping_current(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    paths = _append_addition_inputs(root, snapshot=SNAPSHOT_NEW)
    bindings = _addition_bindings(root, paths)
    _seed_addition_atom(root, bindings=bindings, snapshots=(SNAPSHOT_STALE,))
    current_before = _read_current(root)

    with pytest.raises(SourceFactRefusalError, match="缺少本次钉固快照作用域内的合法消费者"):
        SourceCurrentRefreshService(root).refresh(
            _addition_command(world, paths=paths, request_id="source-addition-no-scope")
        )

    assert _read_current(root) == current_before
    assert not tuple(root.glob("reports/*/v1-source-r*"))


@pytest.mark.parametrize("missing_scope_reports", (("A", "B"), ("B",)))
def test_addition_requires_explicit_scope_for_every_consumed_report(
    tmp_path: Path, missing_scope_reports: tuple[str, ...],
) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    paths = _append_addition_inputs(root, snapshot=SNAPSHOT_NEW)
    bindings = _addition_bindings(root, paths)
    _seed_addition_atom(root, bindings=bindings, snapshots=(SNAPSHOT_NEW,))
    for report in missing_scope_reports:
        path = root / paths[report]
        payload = json.loads(path.read_bytes())
        payload.pop("source_evidence_snapshot_id", None)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    before = _read_current(root)
    user_before = _user_row_snapshot(root, world.user_version)
    facts_before = _source_atom_count(root)
    with pytest.raises(SourceFactRefusalError, match="新增.*明确.*快照作用域"):
        SourceCurrentRefreshService(root).refresh(
            _addition_command(world, paths=paths, request_id="source-addition-unscoped")
        )
    assert _read_current(root) == before
    assert _user_row_snapshot(root, world.user_version) == user_before
    assert _source_atom_count(root) == facts_before
    assert not tuple(root.glob("reports/*/v1-source-r*"))


# ── 6. 取值/来源漂移与过期 revision 失败关闭 ────────────────────────────────


@pytest.mark.parametrize(
    ("tamper", "match"),
    (
        ("value", "来源数值与builder不一致"),
        ("source", "声明来源版本与实际片段绑定不一致"),
    ),
)
def test_addition_value_or_source_drift_refuses(
    tmp_path: Path, tamper: str, match: str,
) -> None:
    world = _world(tmp_path)
    root = world.root
    paths = _append_addition_inputs(root, snapshot=SNAPSHOT_DEVELOPMENT)
    bindings = _addition_bindings(root, paths)
    _seed_addition_atom(root, bindings=bindings, snapshots=(SNAPSHOT_DEVELOPMENT,))
    facts_before = _source_atom_count(root)
    declared_source = ADDITION_SOURCE_VERSION
    if tamper == "value":
        path = root / paths["A"]
        payload = json.loads(path.read_bytes())
        row = next(item for item in payload["safety"] if item["row_id"] == ADDITION_ROW_ID)
        row["value"] = 99.0
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        declared_source = "nct04558918-safety-report-addition-vX"

    with pytest.raises(SourceFactRefusalError, match=match):
        SourceCurrentRefreshService(root).refresh(
            _addition_command(world, paths=paths, declared_source=declared_source)
        )

    assert _read_current(root) == world.current
    assert _source_atom_count(root) == facts_before
    assert not tuple(root.glob("reports/*/v1-source-r*"))


def test_addition_stale_expected_revision_refuses(tmp_path: Path) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    paths = _append_addition_inputs(root, snapshot=None)
    bindings = _addition_bindings(root, paths)
    _seed_addition_atom(root, bindings=bindings, snapshots=(SNAPSHOT_DEVELOPMENT,))

    with pytest.raises(SourceCurrentRefreshConflictError, match="版本冲突"):
        SourceCurrentRefreshService(root).refresh(
            _addition_command(world, paths=paths, expected_revision=0)
        )

    assert _read_current(root) == world.current
