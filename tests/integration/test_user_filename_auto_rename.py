"""Task 3.3 用户原文件名自动改名：标识符规范化、PDF 支持与类型一致性。

验收计划要求本文件只含一个顶层测试节点，最终恰好 3 passed。
"""

from __future__ import annotations

import io
import tempfile
from datetime import UTC, datetime
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


def _pdf(text: str) -> bytes:
    """用 reportlab 生成真实可解析 PDF（含文本层）。"""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setTitle("Supplementary Data")
    y = 760
    for line in text.splitlines():
        c.drawString(72, y, line[:90])
        y -= 18
    c.save()
    return buf.getvalue()


def _create(svc: ManualInboxService, **overrides: object):
    kwargs: dict[str, object] = {
        "project_id": "p1", "run_id": "r1", "report_kind": "B", "spec": _spec_b(),
        "blocking_priority": "blocking", "product_id": "p", "trial_id": "NCT001",
        "registry_identifiers": ("NCT001",), "doi": "10.1000/test.001",
        "pmid": "38570000", "document_role": "supplementary_material",
        "title": "关键试验主要终点完整结果与分析方法", "publisher": "Elsevier",
        "landing_page_url": "https://a", "attachment_url": "https://b.pdf",
        "missing_fields": ("b_baseline_age",), "reason_zh": "需要基线年龄。",
        "gap_still_open": True, "expected_to_close_units": ("b_baseline_age",),
    }
    kwargs.update(overrides)
    return svc.create_request(**kwargs)


def test_user_filename_auto_rename():
    """一个顶层测试节点覆盖标识符规范化、PDF 支持与类型一致性。"""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        svc = _create_service(tmp)

        # ── 子用例 1：标识符规范化 ────────────────────────────────────────
        req = _create(svc, trial_id="NCT001", doi="10.1000/test.001")
        rid = req.request_id
        inbox = svc.project_root / "evidence/manual-inbox" / rid
        # 小写 nct + DOI 尾部标点 → 规范化后唯一匹配
        (inbox / "任意名.html").write_bytes(_content(
            "nct01234567 10.1000/test.001,\n关键试验主要终点完整结果与分析方法。\n"
        ))
        result = svc.scan_and_process_inbox(rid, occurred_at=_NOW)
        if result is None or result.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例1：规范化标识符应唯一匹配")
        # 仅 DOI 且标题不出现 → DOI 唯一即足够
        req2 = _create(svc, trial_id="NCT002", doi="10.1000/test.002",
                       run_id="r2", title="任何标题",
                       reason_zh="需要年龄。", attachment_url="https://c.pdf")
        rid2 = req2.request_id
        inbox2 = svc.project_root / "evidence/manual-inbox" / rid2
        (inbox2 / "s.html").write_bytes(
            _content("DOI: 10.1000/test.002\nSupplementary appendix.\n")
        )
        result2 = svc.scan_and_process_inbox(rid2, occurred_at=_NOW)
        if result2 is None or result2.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例1：DOI 精确唯一应足够（标题不出现）")
        # 用户无需重命名：大写扩展名与小写扩展名等价
        upper_req = _create(
            svc, trial_id="NCT002A", doi="10.1000/test.002a", run_id="r2a",
            title="Uppercase attachment", attachment_url="https://c2.HTML",
            missing_fields=("b_baseline_sample_size",),
            expected_to_close_units=("b_baseline_sample_size",),
        )
        upper_inbox = svc.project_root / upper_req.inbox_directory
        (upper_inbox / "SUPPLEMENT.HTML").write_bytes(_content(
            "NCT002A DOI: 10.1000/test.002a\nSample size results.\n"
        ))
        upper_result = svc.scan_and_process_inbox(
            upper_req.request_id, occurred_at=_NOW,
        )
        if upper_result is None or upper_result.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例1：大写扩展名不得要求用户重命名")
        # 国外资料只有登记号时，可用英文标题核对
        english_req = _create(
            svc, trial_id="NCT00000022", doi=None, pmid=None, run_id="r2b",
            registry_identifiers=("NCT00000022",), title="Baseline Demographic Results",
            attachment_url="https://c3.html",
            missing_fields=("b_baseline_sample_size",),
            expected_to_close_units=("b_baseline_sample_size",),
        )
        english_inbox = svc.project_root / english_req.inbox_directory
        (english_inbox / "appendix.html").write_bytes(_content(
            "NCT00000022\nBaseline demographic results for the randomized population.\n"
        ))
        english_result = svc.scan_and_process_inbox(
            english_req.request_id, occurred_at=_NOW,
        )
        if english_result is None or english_result.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例1：英文标题应能核对国外试验附件")
        english_wrong = _create(
            svc, trial_id="NCT00000023", doi=None, pmid=None, run_id="r2c",
            registry_identifiers=("NCT00000023",),
            title="Baseline Demographic Results",
            attachment_url="https://c4.html",
            missing_fields=("b_baseline_sample_size",),
            expected_to_close_units=("b_baseline_sample_size",),
        )
        wrong_inbox = svc.project_root / english_wrong.inbox_directory
        (wrong_inbox / "wrong.html").write_bytes(_content(
            "NCT00000023\nStudy results for pharmacokinetic sampling.\n"
        ))
        svc.scan_and_process_inbox(english_wrong.request_id, occurred_at=_NOW)
        if not svc.load_request(english_wrong.request_id).quarantine_rejected_paths:
            failures.append("子用例1：英文标题只命中通用词时应按错附件隔离")
        # NCT 单独匹配但无标题 → 歧义隔离
        req3 = _create(svc, trial_id="NCT003", doi=None, pmid="38570001",
                       run_id="r3", registry_identifiers=("NCT003",),
                       reason_zh="需要年龄。", attachment_url="https://d.pdf",
                       missing_fields=("b_baseline_sex",),
                       expected_to_close_units=("b_baseline_sex",))
        rid3 = req3.request_id
        inbox3 = svc.project_root / "evidence/manual-inbox" / rid3
        (inbox3 / "only-nct.html").write_bytes(_content(
            "NCT003\n与目标标题完全无关的内容。\n"
        ))
        svc.scan_and_process_inbox(rid3, occurred_at=_NOW)
        req3_after = svc.load_request(rid3)
        if not req3_after.quarantine_rejected_paths:
            failures.append("子用例1：仅 NCT 无标题匹配应隔离并记录路径")

        # ── 子用例 2：PDF 支持 + 角色/类型一致性 ──────────────────────────
        pdf_req = _create(svc, trial_id="NCT004", doi="10.1000/test.004",
                          run_id="r4", document_role="publication_pdf",
                          title="安全性完整论文", attachment_url="https://e.pdf",
                          missing_fields=("b_safety_minimum_record",),
                          reason_zh="需要安全性数据。",
                          expected_to_close_units=("b_safety_minimum_record",))
        rid4 = pdf_req.request_id
        inbox4 = svc.project_root / "evidence/manual-inbox" / rid4
        pdf_bytes = _pdf("Study NCT004 DOI: 10.1000/test.004 安全性数据。")
        (inbox4 / "paper.pdf").write_bytes(pdf_bytes)
        result4 = svc.scan_and_process_inbox(rid4, occurred_at=_NOW)
        if result4 is None or result4.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例2：publication_pdf 应接受真实 PDF")
        # HTML 不能充当 publication_pdf
        pdf_req2 = _create(svc, trial_id="NCT005", doi="10.1000/test.005",
                           run_id="r5", document_role="publication_pdf",
                           title="另一篇论文", attachment_url="https://f.pdf",
                           missing_fields=("b_baseline_sample_size",),
                           reason_zh="需要样本量。",
                           expected_to_close_units=("b_baseline_sample_size",))
        rid5 = pdf_req2.request_id
        inbox5 = svc.project_root / "evidence/manual-inbox" / rid5
        (inbox5 / "paper.html").write_bytes(_content(
            "NCT005 DOI: 10.1000/test.005\n样本量数据。\n"))
        svc.scan_and_process_inbox(rid5, occurred_at=_NOW)
        if not svc.load_request(rid5).quarantine_rejected_paths:
            failures.append("子用例2：HTML 不应满足 publication_pdf（应隔离）")
        # 直接 API 伪造 PDF：text/plain 字节命名为 .pdf → 拒绝
        try:
            svc.detect_file(rid5, filename="fake.pdf",
                            content=b"plain text not pdf", media_type="text/plain")
            failures.append("子用例2：直接 API 应拒绝伪造 PDF")
        except DownloadRequestError:
            pass
        try:
            svc.match_file(rid5, filename="fake.pdf",
                           content=b"plain text not pdf", media_type="text/plain")
            failures.append("子用例2：match 应拒绝伪造 PDF")
        except DownloadRequestError:
            pass
        try:
            svc.accept(rid5, filename="fake.pdf",
                       content=b"plain text not pdf", media_type="text/plain")
            failures.append("子用例2：accept 应拒绝伪造 PDF")
        except DownloadRequestError:
            pass

        # ── 子用例 3：规范命名 + 原文件名仅元数据 + 列表重生成 ───────────
        req6 = _create(svc, trial_id="NCT006", doi="10.1000/test.006",
                       run_id="r6", title="基线汇总", attachment_url="https://g.pdf",
                       missing_fields=("b_source_role_maturity_location",),
                       reason_zh="需要来源定位。",
                       expected_to_close_units=("b_source_role_maturity_location",))
        rid6 = req6.request_id
        inbox6 = svc.project_root / "evidence/manual-inbox" / rid6
        (inbox6 / "原文件名-最终版.html").write_bytes(_content(
            "NCT006 DOI: 10.1000/test.006\n来源与成熟度定位数据。\n"))
        result6 = svc.scan_and_process_inbox(rid6, occurred_at=_NOW)
        if result6 is None or result6.state is not DownloadRequestState.ACCEPTED:
            failures.append("子用例3：合法文件应接受")
        canonical = result6.canonical_filename or ""
        if "supplement" not in canonical:
            failures.append(f"子用例3：规范文件名缺少角色段（{canonical}）")
        if not result6.content_sha256 or result6.content_sha256[:8] not in canonical:
            failures.append("子用例3：规范文件名缺少摘要后缀")
        if result6.original_filename != "原文件名-最终版.html":
            failures.append("子用例3：原文件名应保留在元数据")
        library_dir = svc.project_root / result6.canonical_relative_path
        if not (svc.project_root / result6.canonical_relative_path).exists():
            failures.append("子用例3：规范库文件未创建")
        lib_names = [f.name for f in library_dir.parent.iterdir()]
        if "原文件名-最终版.html" in lib_names:
            failures.append("子用例3：原文件名出现在库目录中")

        # 其余活跃请求全部不再需要 → 无待办
        svc.mark_not_required(rid3, reason_zh="监管材料已关闭缺口。", gap_still_open=False)
        svc.mark_not_required(rid5, reason_zh="登记结果已补充。", gap_still_open=False)
        svc.mark_not_required(
            english_wrong.request_id,
            reason_zh="已从登记结果补齐基线资料。",
            gap_still_open=False,
        )
        # 列表重生成：已接受/不再需要请求消失，无待办时显示“当前无需补充资料”
        list_text = (svc.project_root / "logs" / "download_requests.md").read_text("utf-8")
        if "当前无需补充资料" not in list_text:
            failures.append("子用例3：无待办时列表应显示当前无需补充资料")
        if "「基线汇总」" in list_text or "「安全性完整论文」" in list_text:
            failures.append("子用例3：已接受请求不应出现在待办列表")
        if "awaiting_user" in list_text or "gate-spec" in list_text or "✓" in list_text:
            failures.append("子用例3：列表不得暴露内部状态/规则/符号")

    if failures:
        raise AssertionError("\n".join(failures))
