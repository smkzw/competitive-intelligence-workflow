"""Task 3.3 人工收件恢复：真实文件系统扫描、多文件分支、隔离与重抽取任务。

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
)

ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime(2026, 8, 12, 10, 0, tzinfo=UTC)


def _spec_b() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "B-v1.yaml")


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


def _create(svc: ManualInboxService, **overrides: object):
    kwargs: dict[str, object] = {
        "project_id": "p1", "run_id": "r1", "report_kind": "B", "spec": _spec_b(),
        "blocking_priority": "blocking", "product_id": "p", "trial_id": "NCT001",
        "registry_identifiers": ("NCT001",), "doi": "10.1000/test.001",
        "pmid": None, "document_role": "supplementary_material",
        "title": "终点结果", "publisher": "Elsevier",
        "landing_page_url": "https://a", "attachment_url": "https://b.pdf",
        "missing_fields": ("b_baseline_age",), "reason_zh": "需要基线年龄。",
        "gap_still_open": True, "expected_to_close_units": ("b_baseline_age",),
    }
    kwargs.update(overrides)
    return svc.create_request(**kwargs)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_manual_inbox_recovery():
    """一个顶层测试节点覆盖三类真实文件系统子用例。"""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        svc = _create_service(tmp)

        # ── 子用例 1：多文件扫描：合法文件 + 登录页 → 无需删除即可恢复 ─────
        req = _create(svc)
        rid = req.request_id
        inbox = svc.project_root / "evidence/manual-inbox" / rid
        valid_html = _content("NCT001 DOI: 10.1000/test.001\n基线年龄结果。\n")
        login_html = b"<html><body>Sign in to view</body></html>"
        (inbox / "login.html").write_bytes(login_html)
        (inbox / "数据.html").write_bytes(valid_html)
        result = svc.scan_and_process_inbox(rid, occurred_at=_NOW)
        if result is None or result.state is not DownloadRequestState.ACCEPTED:
            failures.append(
                f"子用例1：合法+登录页应接受合法文件（{result.state if result else None}）"
            )
        updated = svc.load_request(rid)
        if not updated.quarantine_rejected_paths:
            failures.append("子用例1：登录页应按摘要隔离并记录路径")
        q_path = updated.quarantine_rejected_paths[0]
        if not q_path.startswith("evidence/quarantine/"):
            failures.append("子用例1：隔离路径必须是项目相对路径")
        quarantine_file = svc.project_root / q_path
        if not quarantine_file.exists():
            failures.append("子用例1：隔离文件实际存在")
        if len(updated.quarantine_rejected_paths) != 1:
            failures.append("子用例1：只应隔离登录页一个文件")

        # 已识别但尚未归档时中断：重新扫描应直接续跑，且不重复事件或作业
        crash_req = _create(
            svc, trial_id="NCT001A", doi="10.1000/test.001a", run_id="r1a",
            missing_fields=("b_baseline_sample_size",),
            expected_to_close_units=("b_baseline_sample_size",),
        )
        crash_content = _content(
            "NCT001A DOI: 10.1000/test.001a\n样本量数据。\n"
        )
        crash_inbox = svc.project_root / crash_req.inbox_directory
        crash_path = crash_inbox / "附件.html"
        crash_path.write_bytes(crash_content)
        svc.detect_file(
            crash_req.request_id, filename=crash_path.name, content=crash_content,
            media_type="text/html", occurred_at=_NOW,
        )
        svc.match_file(
            crash_req.request_id, filename=crash_path.name, content=crash_content,
            media_type="text/html", occurred_at=_NOW + timedelta(milliseconds=1),
        )
        before_resume_events = len(svc.event_store.read_all())
        resumed = svc.scan_and_process_inbox(
            crash_req.request_id, occurred_at=_NOW + timedelta(milliseconds=2),
        )
        if resumed is None or resumed.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例1：已识别状态中断后应自动续跑归档")
        after_resume_events = len(svc.event_store.read_all())
        jobs_before_replay = len(_read_jsonl(svc.re_extraction_path))
        # 接受后的重放不得删除用户文件；规范文件与原始文件都由用户目录保留
        crash_path.write_bytes(crash_content)
        replayed = svc.scan_and_process_inbox(
            crash_req.request_id, occurred_at=_NOW + timedelta(milliseconds=3),
        )
        if replayed is None or replayed.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例1：已接受状态重放应保持 accepted")
        if not crash_path.exists():
            failures.append("子用例1：已接受重放不应删除用户收件文件")
        if len(svc.event_store.read_all()) != after_resume_events:
            failures.append("子用例1：已接受重放不应重复写入事件")
        if len(_read_jsonl(svc.re_extraction_path)) != jobs_before_replay:
            failures.append("子用例1：已接受重放不应重复创建重抽取作业")
        if after_resume_events != before_resume_events + 1:
            failures.append("子用例1：从已识别续跑只应新增一次接受事件")
        svc.accept(
            crash_req.request_id, filename=crash_path.name, content=crash_content,
            media_type="text/html", occurred_at=_NOW + timedelta(milliseconds=4),
        )
        if not crash_path.exists():
            failures.append("子用例1：直接接受重放不应删除用户收件文件")
        if len(svc.event_store.read_all()) != after_resume_events:
            failures.append("子用例1：直接接受重放不应重复写入事件")
        if len(_read_jsonl(svc.re_extraction_path)) != jobs_before_replay:
            failures.append("子用例1：直接接受重放不应重复创建作业")

        # ── 子用例 2：多合法文件 → 全部按歧义隔离；两个请求作业保留 ─────────
        req_a = _create(svc, trial_id="NCT010", doi="10.1000/test.010",
                        run_id="r2", missing_fields=("b_baseline_sex",),
                        reason_zh="需要性别数据。",
                        expected_to_close_units=("b_baseline_sex",))
        rid_a = req_a.request_id
        inbox_a = svc.project_root / "evidence/manual-inbox" / rid_a
        (inbox_a / "one.html").write_bytes(
            _content("NCT010 DOI: 10.1000/test.010\n性别数据 A。\n"))
        (inbox_a / "two.html").write_bytes(
            _content("NCT010 DOI: 10.1000/test.010\n性别数据 B。\n"))
        svc.scan_and_process_inbox(rid_a, occurred_at=_NOW)
        req_a_after = svc.load_request(rid_a)
        if len(req_a_after.quarantine_rejected_paths) != 2:
            failures.append(
                f"子用例2：多合法文件应全部隔离（{len(req_a_after.quarantine_rejected_paths)}）")

        # 单合法请求正常接受 → 两个请求共 2 个重抽取作业
        req_b = _create(svc, trial_id="NCT011", doi="10.1000/test.011",
                        run_id="r3", missing_fields=("b_safety_minimum_record",),
                        reason_zh="需要安全性数据。",
                        expected_to_close_units=("b_safety_minimum_record",))
        rid_b = req_b.request_id
        inbox_b = svc.project_root / "evidence/manual-inbox" / rid_b
        (inbox_b / "safety.html").write_bytes(
            _content("NCT011 DOI: 10.1000/test.011\n安全性数据。\n"))
        svc.scan_and_process_inbox(rid_b, occurred_at=_NOW)
        jobs = _read_jsonl(svc.re_extraction_path)
        if len(jobs) < 2:
            failures.append(f"子用例2：重抽取作业不足 2 条（{len(jobs)}）")
        job_requests = {j["request_id"] for j in jobs}
        if rid not in job_requests or rid_b not in job_requests:
            failures.append("子用例2：重抽取作业应覆盖子用例1与2的两个请求")

        # 重放：已接受请求再扫/再接受 → 不新增作业
        svc.accept(rid_b, filename="safety.html",
                   content=_content("NCT011 DOI: 10.1000/test.011\n安全性数据。\n"),
                   media_type="text/html", occurred_at=_NOW)
        jobs_after = _read_jsonl(svc.re_extraction_path)
        if len(jobs_after) != len(jobs):
            failures.append("子用例2：重放后不应新增作业")

        # 同 job_id 不同内容 → 冲突失败
        svc._append_re_extraction_job({
            "job_id": "re-extraction_conflict", "request_id": rid_b,
            "source_version_id": "sv-x", "gap_id": "g", "state": "queued",
            "created_at": "2026-08-12T10:00:00+00:00",
        })
        svc._append_re_extraction_job({
            "job_id": "re-extraction_conflict", "request_id": rid_b,
            "source_version_id": "sv-x", "gap_id": "g", "state": "queued",
            "created_at": "2026-08-12T10:01:00+00:00",
        })
        try:
            svc._append_re_extraction_job({
                "job_id": "re-extraction_conflict", "request_id": rid_b,
                "source_version_id": "sv-different", "gap_id": "g", "state": "queued",
                "created_at": "2026-08-12T10:02:00+00:00",
            })
            failures.append("子用例2：同 job_id 不同内容应失败关闭")
        except DownloadRequestError:
            pass

        # 规范归档预存漂移 → 拒绝复用
        req_c = _create(svc, trial_id="NCT012", doi="10.1000/test.012",
                        run_id="r4", missing_fields=("b_baseline_sample_size",),
                        reason_zh="需要样本量。",
                        expected_to_close_units=("b_baseline_sample_size",))
        rid_c = req_c.request_id
        content_c = _content("NCT012 DOI: 10.1000/test.012\n样本量数据。\n")
        inbox_c = svc.project_root / "evidence/manual-inbox" / rid_c
        (inbox_c / "ok.html").write_bytes(content_c)
        # 预写漂移的规范归档文件
        library_dir = svc.project_root / "evidence/library" / rid_c
        library_dir.mkdir(parents=True, exist_ok=True)
        from ci_workflow.ingestion.manual_inbox import _canonical_filename
        canonical = _canonical_filename(
            basis="NCT012", document_role="supplementary_material",
            version_or_date=None,
            digest=__import__("hashlib").sha256(content_c).hexdigest(),
            original_extension=".html",
        )
        (library_dir / canonical).write_bytes(b"drifted-content")
        try:
            svc.scan_and_process_inbox(rid_c, occurred_at=_NOW)
            failures.append("子用例3：规范归档漂移应失败关闭")
        except DownloadRequestError:
            pass
        if svc.load_request(rid_c).state is DownloadRequestState.ACCEPTED:
            failures.append("子用例3：漂移归档不得进入 accepted")

        # ── 子用例 3：两个坏下载循环 + attempt 事件 + 有效恢复 ──────────────
        req3 = _create(svc, trial_id="NCT020", doi="10.1000/test.020",
                       run_id="r5", missing_fields=("b_treatment_control_identity",),
                       reason_zh="需要治疗对照身份。",
                       expected_to_close_units=("b_treatment_control_identity",))
        rid3 = req3.request_id
        inbox3 = svc.project_root / "evidence/manual-inbox" / rid3
        bad = b"<html><body>Sign in to view</body></html>"
        # 第一次坏文件 → needs_re_download
        (inbox3 / "bad1.html").write_bytes(bad)
        svc.scan_and_process_inbox(rid3, occurred_at=_NOW)
        if svc.load_request(rid3).state is not DownloadRequestState.NEEDS_RE_DOWNLOAD:
            failures.append("子用例3：第一次坏文件后应 needs_re_download")
        # 第二次坏文件（同字节）→ attempt 递增，事件身份不同
        svc.re_request(rid3, reason_zh="请重新下载。",
                       occurred_at=_NOW + timedelta(seconds=1))
        (inbox3 / "bad2.html").write_bytes(bad)
        svc.scan_and_process_inbox(rid3, occurred_at=_NOW + timedelta(seconds=2))
        req3_after = svc.load_request(rid3)
        if req3_after.attempt_number < 2:
            failures.append("子用例3：attempt_number 应随循环递增")
        quarantine_events = [
            e for e in svc.event_store.read_all()
            if e.payload.get("current_state") == "needs_re_download"
        ]
        if len(quarantine_events) < 2:
            failures.append(
                f"子用例3：两个坏下载应产生两个隔离事件（{len(quarantine_events)}）")
        if len({e.event_id for e in quarantine_events}) != len(quarantine_events):
            failures.append("子用例3：两次隔离事件身份必须不同")

        # 有效文件恢复 → accepted
        svc.re_request(rid3, reason_zh="请重新下载。",
                       occurred_at=_NOW + timedelta(seconds=3))
        (inbox3 / "valid.html").write_bytes(
            _content("NCT020 DOI: 10.1000/test.020\n治疗对照身份详情。\n"))
        result3 = svc.scan_and_process_inbox(rid3, occurred_at=_NOW + timedelta(seconds=4))
        if result3 is None or result3.state is not DownloadRequestState.ACCEPTED:
            failures.append(
                f"子用例3：有效文件应恢复至 accepted（{result3.state if result3 else None}）"
            )

        # 重放：已隔离文件路径按摘要保留
        if len(svc.load_request(rid3).quarantine_rejected_paths) < 2:
            failures.append("子用例3：两个坏文件路径应持久化")
        note_text = (
            svc.project_root / "evidence/quarantine" / rid3 / "处理说明.md"
        ).read_text(encoding="utf-8")
        if "bad1.html" not in note_text or "bad2.html" not in note_text:
            failures.append("子用例3：处理说明应保留每一轮坏文件记录")
        if "未能识别文件名的附件" in note_text:
            failures.append("子用例3：已有文件名时处理说明不应追加泛化占位行")

    if failures:
        raise AssertionError("\n".join(failures))
