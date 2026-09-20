#!/usr/bin/env python3
"""Task 10.3 pre-RC 全矩阵验收入口（catalog/输入核验 + 项目运行 + ego(lite) 回执绑定）。

业务合同位于 ``src/ci_workflow/application/acceptance_runner.py``；本脚本只做
参数收口与退出码翻译。适应症、时区、数据截止、报告集合、输出格式与逐文件
摘要只从验收 catalog 解析；本命令行不提供、也不接受任何覆盖科学真值的开关。
本入口自身不启动任何浏览器，也不回退到任何其他浏览器：真实浏览器验收由
Codex 使用 ego(lite) 完成，本入口只接收并严格绑定其回执。

用法示例::

    # 阶段 1：catalog 真值与输入摘要核验（默认）
    uv run python tools/run_acceptance.py --project-root <隔离验收项目根>

    # 阶段 1-3：catalog 核验 → 空项目 HTML-only 运行 → 请求 ego(lite) 回执
    uv run python tools/run_acceptance.py --pipeline html --project-root <隔离验收项目根>

    # Codex 完成 ego(lite) 验收后，对已运行项目绑定三份回执
    uv run python tools/run_acceptance.py --pipeline html --bind-ego-receipts \\
        --project-root <已运行验收项目根>

    # 完整六阶段（首次）：构建时即核验候选安装根；项目运行后暂停在 ego(lite)
    # 回执阶段（退出码 3），宿主冒烟不会在回执绑定前执行
    uv run python tools/run_acceptance.py --pipeline full \\
        --project-root <隔离验收项目根> --acceptance-root <隔离验收证据根>

    # 完整六阶段（续跑）：对已绑定回执的项目继续三宿主真实冒烟 → 最终项目
    # 核验 → 场景回执聚合；全部通过后输出 PRE_RC_REHEARSAL_OK
    uv run python tools/run_acceptance.py --pipeline full --bind-ego-receipts \\
        --project-root <已绑定回执项目根> --acceptance-root <隔离验收证据根>

    # --suite full：独立场景 rehearsal——对 catalog 中全部
    # execution_scope=full-matrix 的首版 case/子 case 逐条执行 catalog 声明的
    # verifier 并生成 pre_rc_rehearsal 回执；恢复、切换与未来格式保持
    # pending_future_owner，release_cases_closed 恒为 0。
    uv run python tools/run_acceptance.py --suite full

流程（失败关闭）：

1. 拒绝任何试图覆盖适应症/时区/截止/报告/格式的参数（退出码 2）。
2. 加载验收 catalog：schema、release_scope、允许格式与摘要算法逐项核验。
3. 解析案例科学真值并重算案例摘要；逐文件 SHA-256 对案例目录实际字节核验。
4. 检查项目根：必须不存在或为空；预存 manifest、snapshot、站点或宿主回执
   一律失败关闭（退出码 1）。
5. ``--pipeline html`` 追加执行：同源输入空项目运行（清单绑定 case/case
   digest/pre-RC 运行身份/逐文件输入摘要）→ A/B/C 三个 HTML 当前产物发现
   （任何 PDF/PPTX/HTML-PPT 产物即失败关闭）→ 等待并严格绑定 Codex 在
   ego(lite) 中生成的浏览器回执。回执缺失时退出码 3 并给出明确指引；
   回执存在但与当前运行/产物任一绑定不符（旧回执、缺页、摘要不符、
   非 ego(lite) 工具、页面失败）时退出码 1。
6. ``--bind-ego-receipts``（html）对已运行项目重新核验 catalog 真值、当前
   运行清单与产物后绑定回执；不重跑项目。
7. ``--suite full`` 独立执行场景 rehearsal 回执聚合：套件成员只由 catalog
   决定；任一 verifier 未通过、子场景漂移、执行范围未登记或未来责任被
   关闭即失败关闭（退出码 1）。本模式不运行项目、不启动浏览器、不执行
   宿主冒烟，输出 ``SUITE_REHEARSAL_RECEIPTS_OK``。
8. ``--pipeline full`` 接入完整六阶段：候选安装根在构建时即核验（无效根
   在任何阶段执行前失败关闭）；首次运行在 ego(lite) 回执阶段暂停（退出码
   3）；``--bind-ego-receipts`` 续跑时从候选安装根执行 Codex/Hermes/OMP
   三宿主真实冒烟（回执与项目落在 --acceptance-root 下，不复用旧回执，
   三宿主进程/会话/运行互异且绑定同一候选包摘要），随后最终项目核验重新
   打开当前运行并证明产物与回执未被改动，最后聚合 full-matrix 场景回执。
   全部通过后输出 ``PRE_RC_REHEARSAL_OK``；任何阶段失败都不输出通过信号。

退出码：0 = 所选流水线阶段全部通过；1 = 验收失败关闭；2 = 用法错误；
3 = 等待 Codex 使用 ego(lite) 生成并提供浏览器回执。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Never

from ci_workflow.application.acceptance_runner import (
    DEFAULT_CANDIDATE_INSTALL_ROOT,
    AcceptanceRunnerError,
    EgoReceiptPendingError,
    bind_ego_receipts_pipeline,
    build_host_smoke_stage,
    build_pre_rc_receipts_stage,
    build_project_verify_stage,
    complete_pre_rc_rehearsal,
    format_pre_rc_rehearsal_ok,
    run_catalog_input_stage,
    run_full_matrix_suite_rehearsal,
    run_html_pipeline,
    run_pre_rc_rehearsal,
)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_PENDING_EGO_RECEIPTS = 3

# 科学真值只来自验收 catalog；以下开关永不加入解析器，出现即拒绝。
_FORBIDDEN_TRUTH_FLAGS = (
    "--indication",
    "--timezone",
    "--data-cutoff",
    "--cutoff",
    "--reports",
    "--report",
    "--formats",
    "--outputs",
    "--output-formats",
)


class _ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 的固定交互文案收口为中文。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "命令"
        self._optionals.title = "选项"
        self.add_argument("-h", "--help", action="help", help="显示帮助并退出")

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "用法:", 1)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法:", 1)


def _reject_truth_overrides(argv: list[str]) -> None:
    for flag in argv:
        name = flag.partition("=")[0]
        if name in _FORBIDDEN_TRUTH_FLAGS:
            print(
                f"拒绝执行：{name} 不得覆盖验收 catalog 的科学真值；"
                "适应症、时区、数据截止、报告与格式只能来自 "
                "fixtures/acceptance/catalog.yaml。",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_USAGE)


def _build_parser() -> _ChineseArgumentParser:
    parser = _ChineseArgumentParser(description="Task 10.3 pre-RC 全矩阵验收入口")
    parser.add_argument(
        "--pipeline",
        choices=("catalog", "html", "full"),
        default="catalog",
        help="流水线深度：catalog=仅阶段 1（默认）；html=阶段 1-3（含 ego(lite) 回执"
        "请求/绑定）；full=完整六阶段（追加三宿主真实冒烟、最终项目核验与场景回执聚合）",
    )
    parser.add_argument(
        "--suite",
        choices=("full",),
        default=None,
        help="场景套件：full=对 catalog 中全部 execution_scope=full-matrix 的首版 "
        "case/子 case 独立执行场景 rehearsal 并生成 pre_rc_rehearsal 回执"
        "（不运行项目、不启动浏览器、不执行宿主冒烟；与其他模式互斥）",
    )
    parser.add_argument(
        "--bind-ego-receipts",
        action="store_true",
        help="html=对已运行项目重新核验后绑定 Codex 提供的 ego(lite) 回执（不重跑项目；"
        "缺失回执时退出码 3）；full=在已绑定回执的项目上继续三宿主真实冒烟、"
        "最终项目核验与场景回执聚合",
    )
    parser.add_argument(
        "--install-root",
        type=Path,
        default=DEFAULT_CANDIDATE_INSTALL_ROOT,
        help="候选安装根（Task 9.5 fresh-install 隔离根；默认 "
        f"{DEFAULT_CANDIDATE_INSTALL_ROOT}；仅 --pipeline full 使用）",
    )
    parser.add_argument(
        "--acceptance-root",
        type=Path,
        default=None,
        help="隔离验收证据根（--pipeline full 必填，要求不存在或为空；宿主冒烟回执与"
        "项目全部落在该根下，不复用既有宿主回执；与 --suite 互斥）",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="验收 catalog 路径（默认仓库内 fixtures/acceptance/catalog.yaml）",
    )
    parser.add_argument(
        "--case",
        default=None,
        help="验收案例 id（默认 full-matrix-v1；必须是 catalog 已登记案例；"
        "与 --suite 互斥）",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="隔离验收项目根（流水线模式必填且要求不存在或为空；绑定回执要求已运行；"
        "与 --suite 互斥）",
    )
    return parser


def main(argv: list[str] | None = None) -> Never:
    arguments = list(sys.argv[1:] if argv is None else argv)
    _reject_truth_overrides(arguments)
    options = _build_parser().parse_args(arguments)
    if options.suite is not None:
        conflicts = []
        if options.bind_ego_receipts:
            conflicts.append("--bind-ego-receipts")
        if options.pipeline != "catalog":
            conflicts.append("--pipeline")
        if options.case is not None:
            conflicts.append("--case")
        if options.project_root is not None:
            conflicts.append("--project-root")
        if options.acceptance_root is not None:
            conflicts.append("--acceptance-root")
        if conflicts:
            print(
                "拒绝执行：--suite full 是独立的场景 rehearsal 模式，"
                f"不能与 {'、'.join(conflicts)} 同时使用。",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_USAGE)
    elif options.project_root is None:
        print(
            "拒绝执行：流水线模式必须提供 --project-root（隔离验收项目根）；"
            "独立场景 rehearsal 请使用 --suite full。",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_USAGE)
    if options.pipeline == "full" and options.acceptance_root is None:
        print(
            "拒绝执行：--pipeline full 必须提供 --acceptance-root（隔离验收证据根，"
            "要求不存在或为空）；三宿主冒烟回执与项目全部落在该根下，不复用既有宿主回执。",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_USAGE)
    if options.bind_ego_receipts and options.pipeline not in ("html", "full"):
        print(
            "拒绝执行：--bind-ego-receipts 只能与 --pipeline html 或 --pipeline full "
            "同时使用；回执绑定属于 HTML 首版第三阶段。",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_USAGE)
    try:
        if options.suite is not None:
            summary = run_full_matrix_suite_rehearsal(catalog_path=options.catalog)
        elif options.pipeline == "full":
            case = options.case or "full-matrix-v1"
            host_smoke_stage = build_host_smoke_stage(
                install_root=options.install_root,
                acceptance_root=options.acceptance_root,
            )
            project_verify_stage = build_project_verify_stage(
                catalog_path=options.catalog, case_id=case
            )
            receipts_stage = build_pre_rc_receipts_stage(
                catalog_path=options.catalog, case_id=case
            )
            if options.bind_ego_receipts:
                summary = complete_pre_rc_rehearsal(
                    catalog_path=options.catalog,
                    case_id=case,
                    project_root=options.project_root,
                    host_smoke_stage=host_smoke_stage,
                    project_verify_stage=project_verify_stage,
                    receipts_stage=receipts_stage,
                )
            else:
                summary = run_pre_rc_rehearsal(
                    catalog_path=options.catalog,
                    case_id=case,
                    project_root=options.project_root,
                    host_smoke_stage=host_smoke_stage,
                    project_verify_stage=project_verify_stage,
                    receipts_stage=receipts_stage,
                )
        elif options.bind_ego_receipts:
            summary = bind_ego_receipts_pipeline(
                catalog_path=options.catalog,
                case_id=options.case or "full-matrix-v1",
                project_root=options.project_root,
            )
        elif options.pipeline == "html":
            summary = run_html_pipeline(
                catalog_path=options.catalog,
                case_id=options.case or "full-matrix-v1",
                project_root=options.project_root,
            )
        else:
            summary = run_catalog_input_stage(
                catalog_path=options.catalog,
                case_id=options.case or "full-matrix-v1",
                project_root=options.project_root,
            )
    except EgoReceiptPendingError as pending:
        print(
            "HTML 流水线暂停在 ego(lite) 回执阶段：真实浏览器验收必须由 Codex "
            "使用 ego(lite) 完成，本入口不会回退到任何其他浏览器。",
            file=sys.stderr,
        )
        print(f"指引：{pending}", file=sys.stderr)
        raise SystemExit(EXIT_PENDING_EGO_RECEIPTS) from pending
    except AcceptanceRunnerError as error:
        print(f"验收失败关闭：{error}", file=sys.stderr)
        raise SystemExit(EXIT_FAIL) from error
    if options.suite is not None:
        counts = summary["counts"]
        print(
            f"SUITE_REHEARSAL_RECEIPTS_OK cases={counts['catalog_cases_total']} "
            f"rehearsed={counts['rehearsed']} "
            f"future_owner={counts['pending_future_owner']} "
            f"not_applicable={counts['not_applicable']} "
            f"outside_suite={counts['outside_suite']} "
            f"formats={len(summary['formats'])} "
            f"release_cases_closed={summary['release_cases_closed']} "
            f"pre_rc_run_id={summary['pre_rc_run_id']}"
        )
    elif options.pipeline == "full":
        print(format_pre_rc_rehearsal_ok(summary))
    elif options.bind_ego_receipts:
        receipt_stage = summary["stages"][-1]
        print(
            f"EGO_RECEIPTS_OK case={summary['case_id']} "
            f"reports={len(summary['reports'])} formats={len(summary['formats'])} "
            f"artifacts={len(receipt_stage['artifacts'])} "
            f"receipts={len(receipt_stage['receipts'])} "
            f"pre_rc_stages={len(summary['stages'])}/{len(summary['stage_order'])} "
            f"pre_rc_run_id={summary['pre_rc_run_id']}"
        )
    elif options.pipeline == "html":
        receipt_stage = summary["stages"][-1]
        print(
            f"HTML_PIPELINE_OK case={summary['case_id']} "
            f"reports={len(summary['reports'])} formats={len(summary['formats'])} "
            f"artifacts={len(receipt_stage['artifacts'])} "
            f"receipts={len(receipt_stage['receipts'])} "
            f"pre_rc_stages={len(summary['stages'])}/{len(summary['stage_order'])} "
            f"pre_rc_run_id={summary['pre_rc_run_id']}"
        )
    else:
        print(
            f"CATALOG_INPUTS_OK case={summary['case_id']} "
            f"reports={len(summary['reports'])} formats={len(summary['formats'])} "
            f"inputs={len(summary['inputs'])}"
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(EXIT_OK)


if __name__ == "__main__":
    main()
