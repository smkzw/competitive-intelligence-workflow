"""Task 3.3 下载请求生命周期：真实 GateSpec 绑定、类型化守卫、身份与列表重生成。

验收计划要求本文件只含一个顶层测试节点，最终恰好 3 passed。
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ci_workflow.domain.enums import DownloadRequestState
from ci_workflow.gates.models import GateSpec
from ci_workflow.ingestion.manual_inbox import (
    DownloadRequestError,
    ManualInboxService,
    RequestNotRequiredError,
    UndeclaredTransitionError,
)

ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime(2026, 8, 12, 10, 0, tzinfo=UTC)


def _spec_b() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "B-v1.yaml")


def _spec_c() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "C-v1.yaml")


def _create_service(tmp_path: Path) -> ManualInboxService:
    root = tmp_path / "项目"
    for rel in ("events", "receipts", "evidence/manual-inbox",
                "evidence/quarantine", "evidence/library",
                "evidence/raw", "logs", "state/checkpoints"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / "logs" / "download_requests.md").write_text(
        "# 待补充资料\n\n当前无需补充资料。\n", encoding="utf-8",
    )
    return ManualInboxService(root)


def _content(text: str) -> bytes:
    return text.encode("utf-8")


def _create_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "project_id": "p1", "run_id": "r1", "report_kind": "B", "spec": _spec_b(),
        "blocking_priority": "blocking", "product_id": "p", "trial_id": "NCT001",
        "registry_identifiers": ("NCT001",), "doi": "10.1000/test.001",
        "pmid": None, "document_role": "supplementary_material",
        "title": "终点报告", "publisher": "Elsevier",
        "landing_page_url": "https://a", "attachment_url": "https://b.pdf",
        "missing_fields": ("b_baseline_age",), "reason_zh": "需要基线年龄。",
        "gap_still_open": True,
        "expected_to_close_units": ("b_baseline_age",),
    }
    kwargs.update(overrides)
    return kwargs


def test_download_request_transitions():
    """一个顶层测试节点覆盖：真实 GateSpec 绑定、类型化守卫、身份与列表。"""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        svc = _create_service(Path(td))

        # ── 子用例 1：真实 GateSpec + 类型化守卫 ──────────────────────────
        req = svc.create_request(**_create_kwargs())
        if req.spec_id != "gate-spec-b-v1":
            failures.append("子用例1：未持久化真实 GateSpec 标识")
        if req.spec_fingerprint != _spec_b().spec_fingerprint:
            failures.append("子用例1：未持久化真实 GateSpec 指纹")
        if req.expected_to_close_units != ("b_baseline_age",):
            failures.append("子用例1：未持久化目标文档预计关闭的关键单元")

        # B spec 用于 C → 拒绝（真实指纹校验）
        try:
            svc.create_request(**_create_kwargs(spec=_spec_c()))
            failures.append("子用例1：C spec 应拒绝（报告类型/指纹不符）")
        except RequestNotRequiredError:
            pass
        # 修改后的 spec（单元被改 → 指纹不同）→ 拒绝
        altered = GateSpec.model_validate(
            {
                **json.loads(_spec_b().model_dump_json()),
                "units": [
                    {**u, "user_label_zh": u["user_label_zh"] + "改"}
                    for u in json.loads(_spec_b().model_dump_json())["units"]
                ],
            }
        )
        try:
            svc.create_request(**_create_kwargs(spec=altered))
            failures.append("子用例1：修改过的 spec 应拒绝（指纹不符）")
        except RequestNotRequiredError:
            pass
        # 非阻断优先级 → 拒绝
        try:
            svc.create_request(**_create_kwargs(blocking_priority="non_blocking"))
            failures.append("子用例1：non_blocking 应拒绝")
        except RequestNotRequiredError:
            pass
        # 扩展单元 → 拒绝
        try:
            svc.create_request(**_create_kwargs(
                missing_fields=("b_trial_disposition",),
                expected_to_close_units=("b_trial_disposition",),
            ))
            failures.append("子用例1：扩展单元应拒绝")
        except RequestNotRequiredError:
            pass
        # 未知单元 → 拒绝
        try:
            svc.create_request(**_create_kwargs(
                missing_fields=("unknown_unit",),
                expected_to_close_units=("unknown_unit",),
            ))
            failures.append("子用例1：未知单元应拒绝")
        except RequestNotRequiredError:
            pass
        # 关键缺口已关闭 → 拒绝
        try:
            svc.create_request(**_create_kwargs(gap_still_open=False))
            failures.append("子用例1：gap_still_open=False 应拒绝")
        except RequestNotRequiredError:
            pass
        # 未声明预期关闭单元 → 拒绝
        try:
            svc.create_request(**_create_kwargs(expected_to_close_units=()))
            failures.append("子用例1：空 expected_to_close_units 应拒绝")
        except RequestNotRequiredError:
            pass
        # 没有 DOI、PMID 或登记号的资料无法让用户无歧义补件，应以业务原因拒绝
        try:
            svc.create_request(**_create_kwargs(
                doi=None, pmid=None, registry_identifiers=(), trial_id=None,
            ))
            failures.append("子用例1：缺少可核对标识的资料不应发起下载请求")
        except RequestNotRequiredError:
            pass
        try:
            svc.create_request(**_create_kwargs(
                doi=None, pmid=None, registry_identifiers=("   ",), trial_id=None,
            ))
            failures.append("子用例1：仅含空白的标识不应发起下载请求")
        except RequestNotRequiredError:
            pass
        # 预期关闭单元未覆盖所缺字段 → 拒绝
        try:
            svc.create_request(**_create_kwargs(
                missing_fields=("b_baseline_age",),
                expected_to_close_units=("b_baseline_sex",),
            ))
            failures.append("子用例1：预期关闭单元未覆盖缺口应拒绝")
        except RequestNotRequiredError:
            pass
        # 拒绝路径不得写入请求/目录/列表
        if len(list((svc.project_root / "receipts").glob("download_requests.jsonl"))) and \
                len(svc.requests_path.read_text(encoding="utf-8").splitlines()) != 1:
            failures.append("子用例1：拒绝路径不应新增请求记录")

        # ── 子用例 2：六态链 + 事件 + attempt_number + 未声明拒绝 ──────────
        req2 = svc.create_request(**_create_kwargs(
            trial_id="NCT002", doi="10.1000/test.002",
            title="次要终点结果", missing_fields=("b_baseline_sex",),
            reason_zh="需要性别数据。", expected_to_close_units=("b_baseline_sex",),
            run_id="r2",
        ))
        rid2 = req2.request_id
        content = _content("NCT002 DOI: 10.1000/test.002\n基线性别构成数据。\n")
        svc.detect_file(rid2, filename="supp.html", content=content, media_type="text/html",
                        occurred_at=_NOW)
        svc.match_file(rid2, filename="supp.html", content=content, media_type="text/html",
                       occurred_at=_NOW + timedelta(seconds=1))
        inbox_file = svc.project_root / req2.inbox_directory / "supp.html"
        inbox_file.write_bytes(content)
        accepted = svc.accept(rid2, filename="supp.html", content=content,
                              media_type="text/html",
                              occurred_at=_NOW + timedelta(seconds=2))
        if accepted.state is not DownloadRequestState.ACCEPTED:
            failures.append(f"子用例2：接受迁移失败（{accepted.state}）")
        if not accepted.source_version_id or not accepted.canonical_relative_path \
                or not accepted.re_extraction_job_ids or not accepted.matched_identifiers:
            failures.append("子用例2：接受后缺少来源/归档/任务/匹配元数据")
        transitions = [e for e in svc.event_store.read_all()
                       if e.event_type == "download_request_state_changed"]
        if len(transitions) < 3:
            failures.append(f"子用例2：迁移事件不足（{len(transitions)}）")
        if any("attempt_number" not in e.payload for e in transitions):
            failures.append("子用例2：事件缺少 attempt_number")
        try:
            svc.detect_file(rid2, filename="x.pdf", content=b"x", media_type="text/plain")
            failures.append("子用例2：已接受请求不应再次检测")
        except (UndeclaredTransitionError, DownloadRequestError):
            pass

        # not_required 走声明迁移路径（写事件）
        req3 = svc.create_request(**_create_kwargs(
            trial_id="NCT003", doi="10.1000/test.003", run_id="r3",
        ))
        cancelled = svc.mark_not_required(
            req3.request_id, reason_zh="监管材料已关闭缺口。", gap_still_open=False,
            occurred_at=_NOW + timedelta(seconds=3),
        )
        if cancelled.state is not DownloadRequestState.NOT_REQUIRED:
            failures.append("子用例2：not_required 迁移失败")
        not_required_events = [
            e for e in svc.event_store.read_all()
            if e.payload.get("current_state") == "not_required"
        ]
        if not not_required_events:
            failures.append("子用例2：not_required 未写声明迁移事件")

        # re_request 写事件并递增 attempt_number
        req4 = svc.create_request(**_create_kwargs(
            trial_id="NCT004", doi="10.1000/test.004", run_id="r4",
        ))
        svc.detect_file(req4.request_id, filename="bad.html",
                        content=b"<html>Sign in</html>", media_type="text/html",
                        occurred_at=_NOW)
        svc.quarantine(req4.request_id, reason_zh="登录页。",
                       occurred_at=_NOW + timedelta(seconds=1))
        before = svc.load_request(req4.request_id)
        re_requested = svc.re_request(
            req4.request_id, reason_zh="请重新下载。",
            occurred_at=_NOW + timedelta(seconds=2),
        )
        if re_requested.state is not DownloadRequestState.AWAITING_USER:
            failures.append("子用例2：re_request 迁移失败")
        if re_requested.attempt_number != before.attempt_number + 1:
            failures.append("子用例2：re_request 未递增 attempt_number")
        re_events = [
            e for e in svc.event_store.read_all()
            if e.payload.get("trigger") == "deduplicated_re_request"
        ]
        if not re_events:
            failures.append("子用例2：re_request 未写事件")

        # ── 子用例 3：身份绑定 + 同参重建 + 漂移拒绝 ──────────────────────
        svc.create_request(**_create_kwargs(
            trial_id="NCT005", doi="10.1000/test.005",
            document_role="publication_pdf", title="完整论文",
            attachment_url="https://paper.pdf",
            missing_fields=("b_safety_minimum_record",),
            reason_zh="需要安全性数据。",
            expected_to_close_units=("b_safety_minimum_record",),
            run_id="r5",
        ))
        reqs = [
            json.loads(line)
            for line in (
                svc.project_root / "receipts" / "download_requests.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(reqs) < 2:
            failures.append(f"子用例3：同试验不同文档应有独立请求（{len(reqs)}）")
        else:
            ids = [r["request_id"] for r in reqs]
            if len(set(ids)) != len(ids):
                failures.append("子用例3：同试验不同文档请求 ID 必须不同")

        # 同参重建：返回既有记录，状态/时间戳不变，列表不重复
        original = svc.load_request(req.request_id)
        again = svc.create_request(**_create_kwargs())
        if again.request_id != original.request_id:
            failures.append("子用例3：同参重建应返回同请求")
        if again.updated_at != original.updated_at or again.state != original.state:
            failures.append("子用例3：同参重建不应重置状态/时间戳")
        list_text = (svc.project_root / "logs" / "download_requests.md").read_text("utf-8")
        if list_text.count(original.inbox_directory) != 1:
            failures.append("子用例3：列表不应重复同一请求条目")

        next_run = svc.create_request(**_create_kwargs(run_id="r-next"))
        if next_run.request_id == original.request_id:
            failures.append("子用例3：新运行不应复用旧运行的下载请求状态")
        # 旧运行仍保留同一资料请求时，新运行的专属收件目录不应被误判为歧义
        next_content = _content(
            "NCT001 DOI: 10.1000/test.001\n新运行补充的基线年龄数据。\n"
        )
        next_inbox = svc.project_root / next_run.inbox_directory
        (next_inbox / "same-paper.html").write_bytes(next_content)
        next_result = svc.scan_and_process_inbox(next_run.request_id, occurred_at=_NOW)
        if next_result is None or next_result.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例3：旧运行的同资料请求不得阻断新运行收件")

        # 强制同 ID 漂移 → 失败关闭
        drifted = again.model_copy(update={"attachment_url": "https://drift.pdf"})
        try:
            svc._persist(drifted)
            failures.append("子用例3：同 ID 身份漂移应拒绝")
        except DownloadRequestError:
            pass

    if failures:
        raise AssertionError("\n".join(failures))
