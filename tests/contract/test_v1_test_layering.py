"""HTML-only v1 活跃 pytest 分层合同（v1.3 §1.3/§13.1）。

v1 发布面是 HTML-only：PDF/HTML-PPT/PPTX 的源码与测试作为保留回归轨存在
（marker ``retained_legacy_format``），但不得冒充 v1 release gate。本合同
失败关闭地保证：

- 声明的每一条保留轨文件都存在且带模块级 marker；
- tests/pdf、tests/html_ppt 两个 legacy 根下的文件必须全部被声明；
- 保留轨之外的活跃测试不得直接 import 非 HTML 格式运行时；
- marker 必须在 pyproject 中注册（配合 --strict-markers 失败关闭）；
- marker 文件集合与声明集合双向精确相等，防止活跃测试被静默移出门禁；
- gate 的保留轨步骤只能自称 ``retained-compat-smoke``：它是 tests/unit 与
  tests/contract 内声明保留轨文件的有界兼容性 smoke，不是全量保留轨，
  也不是 v1 release gate（CodeBuddy 裁决：修口径，不重启排除格式产品轨）。

分层后的可复现命令（债清单见 reviews/）：
  活跃层：uv run python -m pytest -q -m "not retained_legacy_format" <路径...>
  保留轨：uv run python -m pytest -q -m "retained_legacy_format" <路径...>
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = ROOT / "tests"

MARKER = "retained_legacy_format"
MARKER_LINE = f"pytestmark = [pytest.mark.{MARKER}]"

# 非 HTML 格式运行时的 import 签名：只允许出现在已声明保留轨中。
LEGACY_RUNTIME_IMPORTS = (
    "ci_workflow.renderers.pdf_native",
    "ci_workflow.renderers.html_ppt",
    "ci_workflow.renderers.pptx_master",
    "ci_workflow.application.ppt_master_job",
)

# legacy 测试根：根下所有测试文件都必须进入 RETAINED_FILES。
LEGACY_TEST_ROOTS = (
    "tests/pdf",
    "tests/html_ppt",
)

# 已声明保留轨（相对仓库根；与各文件中的模块级 marker 一一对应）。
RETAINED_FILES: tuple[str, ...] = (
    "tests/acceptance/test_html_ppt_runtime_smoke.py",
    "tests/acceptance/test_native_pdf_slice.py",
    "tests/acceptance/test_pdf_outputs.py",
    "tests/contract/test_ppt_master_job.py",
    "tests/contract/test_ppt_master_job_contract_vectors.py",
    "tests/graph/test_pptx_confirmation_interrupt.py",
    "tests/html_ppt/test_html_ppt_browser_contract.py",
    "tests/html_ppt/test_projection_contract.py",
    "tests/html_ppt/test_report_a_html_ppt.py",
    "tests/html_ppt/test_report_bc_html_ppt.py",
    "tests/pdf/test_pdf09_shared_coverage.py",
    "tests/pdf/test_report_a_pdf.py",
    "tests/pdf/test_report_b_pdf.py",
    "tests/pdf/test_report_c_pdf.py",
    "tests/pdf/test_table_identity_wrap.py",
    "tests/renderers/test_pdf_vertical_slice.py",
    "tests/renderers/test_ppt_master_confirmation.py",
    "tests/renderers/test_ppt_master_source_pack.py",
)


def _iter_test_files() -> list[Path]:
    return sorted(TESTS_ROOT.rglob("test_*.py"))


def test_marker_is_registered_in_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert MARKER in text, "marker 必须在 pyproject [tool.pytest.ini_options] 注册"


def test_declared_retained_files_exist_and_carry_the_marker() -> None:
    missing: list[str] = []
    unmarked: list[str] = []
    for relative in RETAINED_FILES:
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        if MARKER_LINE not in path.read_text(encoding="utf-8"):
            unmarked.append(relative)
    assert not missing, f"声明的保留轨文件不存在：{missing}"
    assert not unmarked, f"保留轨文件缺少模块级 marker：{unmarked}"


def test_every_test_file_under_legacy_roots_is_declared() -> None:
    for root in LEGACY_TEST_ROOTS:
        for path in sorted((ROOT / root).rglob("test_*.py")):
            relative = path.relative_to(ROOT).as_posix()
            assert relative in RETAINED_FILES, (
                f"legacy 根下出现未声明文件：{relative}；"
                "必须加入保留轨声明并携带 marker"
            )


def test_active_tests_do_not_import_legacy_format_runtimes() -> None:
    retained = set(RETAINED_FILES)
    offenders: list[str] = []
    for path in _iter_test_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative in retained:
            continue
        text = path.read_text(encoding="utf-8")
        if MARKER_LINE in text:
            continue
        for signature in LEGACY_RUNTIME_IMPORTS:
            if re.search(rf"^\s*(from|import)\s+{re.escape(signature)}\b", text, re.M):
                offenders.append(f"{relative} -> {signature}")
    assert not offenders, (
        "活跃层测试不得直接依赖非 HTML 格式运行时"
        f"（请声明加入保留轨或改为负面断言）：{offenders}"
    )


def test_marker_carrying_files_exactly_equal_declared_retained_files() -> None:
    """双向精确相等：带 marker 的文件必须全部声明，声明文件必须真实带 marker。"""

    marked = {
        path.relative_to(ROOT).as_posix()
        for path in _iter_test_files()
        if MARKER_LINE in path.read_text(encoding="utf-8")
    }
    declared = set(RETAINED_FILES)
    undeclared = sorted(marked - declared)
    phantom = sorted(declared - marked)
    assert not undeclared, (
        "带 marker 但未声明进保留轨的文件会被活跃层集合排除在守护之外，"
        f"必须补声明或移除 marker：{undeclared}"
    )
    assert not phantom, f"声明进保留轨但实际不带 marker 的文件：{phantom}"


# gate 的保留轨兼容性 smoke 只运行 tests/unit 与 tests/contract 下的声明保留轨
# 文件；它是子集冒烟，不是全量保留轨（18 个声明文件），更不算 v1 release gate。
RETAINED_COMPAT_SMOKE_ROOTS = ("tests/unit", "tests/contract")

# 当前有界 smoke 的精确文件集合；变化必须在此显式改合同，不允许静默漂移。
EXPECTED_RETAINED_COMPAT_SMOKE_FILES: tuple[str, ...] = (
    "tests/contract/test_ppt_master_job.py",
    "tests/contract/test_ppt_master_job_contract_vectors.py",
)

GATE_SCRIPT = ROOT / "tools" / "gate.sh"


def retained_compat_smoke_files() -> tuple[str, ...]:
    return tuple(
        relative
        for relative in RETAINED_FILES
        if relative.startswith(RETAINED_COMPAT_SMOKE_ROOTS)
    )


def test_gate_retained_smoke_scope_is_exact_declared_subset() -> None:
    expected = retained_compat_smoke_files()
    assert expected == EXPECTED_RETAINED_COMPAT_SMOKE_FILES, (
        "gate 兼容性 smoke 的声明子集发生变化；必须同步更新精确口径："
        f"实际={expected} 合同={EXPECTED_RETAINED_COMPAT_SMOKE_FILES}"
    )


def test_gate_labels_retained_step_as_bounded_compat_smoke_not_release_gate() -> None:
    text = GATE_SCRIPT.read_text(encoding="utf-8")
    # 步骤只运行 unit/contract 两个目录并带保留轨 marker 过滤；不得悄悄扩大
    # 到 tests/pdf、tests/html_ppt 等产品轨，也不得保留旧的全量暗示名称。
    assert (
        'run_step retained-compat-smoke uv run python -m pytest tests/unit tests/contract '
        '-q -m "retained_legacy_format"'
    ) in text, "gate 保留轨步骤必须是有界兼容性 smoke：仅 tests/unit+tests/contract"
    assert "retained-legacy-fast-tests" not in text, (
        "旧步骤名 retained-legacy-fast-tests 暗示保留轨基础回归，已废弃"
    )
    scope = next(line for line in text.splitlines() if "GATE_SCOPE" in line)
    assert 'retained_compat_smoke=tests/unit,tests/contract,-m+"retained_legacy_format"' in scope
    assert "full-retained-track-not-run-here" in scope, (
        "scope 必须声明全量保留轨未随 gate 运行"
    )
    assert "retained-steps-are-not-v1-release-gate" in scope
    usage_start = text.index("usage()")
    usage_end = text.index("while (($# > 0))")
    usage = text[usage_start:usage_end]
    assert "兼容性 smoke" in usage
    assert "不是全量保留轨" in usage, "用法说明必须写明 smoke 不是全量保留轨"
    assert "不算 v1 release gate" in usage
