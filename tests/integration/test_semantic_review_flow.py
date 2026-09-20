"""P3.7 流程接线：semantic-review 工作项的 CLI 发射/提交与渲染前消费。

链路：CLI 从 B 载荷按渲染端同款分桶发射复核工作项 → 宿主提交经
validate_semantic_review_submission 四重绑定验证 → 按项目/报告/载荷
摘要绑定写入项目 state → run_service 渲染 B 前注入（载荷自带裁决时
拒绝双源）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _make_project(tmp_path: Path) -> Path:
    from ci_workflow.application.project_service import (
        create_project_workspace,
        verify_project_workspace,
    )
    from ci_workflow.domain.contracts import create_project_contract
    from ci_workflow.domain.enums import OutputFormat, ReportKind

    root = tmp_path / "proj"
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=[ReportKind.B.value],
        outputs=[OutputFormat.HTML.value],
        timezone="Asia/Shanghai",
        cutoff="2026-07-31",
    )
    create_project_workspace(root, contract)
    verify_project_workspace(root)
    return root


def _write_b_payload(root: Path, tmp_path: Path) -> Path:
    from tests.browser.test_b_semantic_proposals import proposal_data

    payload = proposal_data().model_dump(mode="json")
    target = root / "evidence/library/b-portal-payload.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return target


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ci_workflow", *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def test_semantic_review_emit_and_submit_round_trip(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    payload_path = _write_b_payload(root, tmp_path)

    emit = _cli(
        "research", "semantic-review", "--root", str(root),
        "--emit", "--report-data", str(payload_path),
    )
    assert emit.returncode == 0, emit.stderr
    work_item_path = root / "state/work-items/semantic-review.json"
    assert work_item_path.is_file()
    task = json.loads(work_item_path.read_text(encoding="utf-8"))
    assert task["state"] == "awaiting_host_review"
    pair_ids = {frozenset(pair["row_ids"]) for pair in task["pairs"]}
    assert frozenset(("proposal-observation-0", "proposal-observation-1")) in pair_ids

    # 幂等：同载荷重发不报错且内容一致。
    again = _cli(
        "research", "semantic-review", "--root", str(root),
        "--emit", "--report-data", str(payload_path),
    )
    assert again.returncode == 0, again.stderr
    assert json.loads(work_item_path.read_text(encoding="utf-8")) == task

    # 宿主提交：合法裁决落 state；伪造提交失败关闭。
    import ci_workflow.renderers.portal.report_b as rb
    from tests.browser.test_b_semantic_proposals import (
        _display_trial_name,
        _efficacy_records,
    )
    from tests.reports.b.test_semantic_grouping_proposals import _approved

    data = rb.ReportBPortalData.model_validate(
        json.loads(payload_path.read_text(encoding="utf-8"))
    )
    names = {product.id: product.name for product in data.products}
    trials = {t.id: _display_trial_name(t, names[t.product_id]) for t in data.trials}
    records = _efficacy_records(data, names, trials)
    submission = root / "submission.json"
    submission.write_text(json.dumps(
        [_approved(records[0][0], records[1][0]).model_dump(mode="json")],
        ensure_ascii=False,
    ), encoding="utf-8")

    ok = _cli(
        "research", "semantic-review", "--root", str(root),
        "--submit", "--report-data", str(payload_path),
        "--submission", str(submission),
    )
    assert ok.returncode == 0, ok.stderr
    state_path = root / "state/semantic-adjudications.json"
    bound = json.loads(state_path.read_text(encoding="utf-8"))
    assert bound["report"] == "B"
    assert bound["task_id"] == task["task_id"]
    assert len(bound["adjudications"]) == 1

    forged = root / "forged.json"
    payload_bad = _approved(records[0][0], records[1][0]).model_dump(mode="json")
    payload_bad["receipt"]["decision"] = "incompatible"
    forged.write_text(json.dumps([payload_bad], ensure_ascii=False), encoding="utf-8")
    bad = _cli(
        "research", "semantic-review", "--root", str(root),
        "--submit", "--report-data", str(payload_path),
        "--submission", str(forged),
    )
    assert bad.returncode != 0
    assert "Traceback" not in bad.stderr


def test_render_loader_rejects_binding_mismatch(tmp_path: Path) -> None:
    from ci_workflow.application.semantic_review_task import (
        load_semantic_adjudications_for_render,
        store_semantic_adjudications,
    )

    root = _make_project(tmp_path)
    payload_path = _write_b_payload(root, tmp_path)
    digest = _sha256_of(payload_path)
    store_semantic_adjudications(
        root,
        report="B",
        payload_digest=digest,
        project_id=_project_id_of(root),
        task_id="semantic-review-1-x",
        adjudications=(),
    )
    assert load_semantic_adjudications_for_render(
        root, report="B", data_path=payload_path,
        project_id=_project_id_of(root),
    ) == ()

    payload_path.write_text(
        payload_path.read_text(encoding="utf-8").replace("60", "61", 1),
        encoding="utf-8",
    )
    import pytest

    with pytest.raises(ValueError, match="载荷摘要"):
        load_semantic_adjudications_for_render(
            root, report="B", data_path=payload_path,
            project_id=_project_id_of(root),
        )


def _sha256_of(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_id_of(root: Path) -> str:
    import json

    state = json.loads((root / "project.yaml").read_text(encoding="utf-8"))
    return state["project_contract_versions"][0]["project_id"]
