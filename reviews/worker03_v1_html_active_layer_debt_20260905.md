# HTML-only v1 活跃 pytest/验收分层与全量债清单（worker_03，2026-09-05）

- 执行上下文：`ci-r2-review-runtime-fixture-rebaseline-20260905` / `worker_03`
- 源权威：`docs/specs/competitive-intelligence-workflow-design-v1.3.md` §1.3、§13.1、§5.5、§8.1；
  `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_terminal_recovery_review_boundary.md`
- 边界声明：本文是执行证据与债清单，不是 R2/RC/发布完成宣告；Codex 保留最终科学、
  视觉、包、恢复与发布验收裁决权。

## 1. 分层合同（本切片交付）

v1 发布面是 HTML-only。PDF/HTML-PPT/PPTX 的源码与测试**保留**为回归轨，
但**不构成 v1 release gate**（v1.3 §1.3 附录 A；§13.1 `formats=1`）。

- marker：`retained_legacy_format`（已在 `pyproject.toml [tool.pytest.ini_options]`
  注册，配合 `--strict-markers` 失败关闭）。
- 保留轨文件（18 个，均带模块级 `pytestmark`）：
  `tests/pdf/`（5）、`tests/html_ppt/`（4）、
  `tests/acceptance/{test_native_pdf_slice,test_pdf_outputs,test_html_ppt_runtime_smoke}.py`、
  `tests/renderers/{test_pdf_vertical_slice,test_ppt_master_confirmation,test_ppt_master_source_pack}.py`、
  `tests/contract/{test_ppt_master_job,test_ppt_master_job_contract_vectors}.py`、
  `tests/graph/test_pptx_confirmation_interrupt.py`。
- 分层守护合同：`tests/contract/test_v1_test_layering.py`（4 条测试，失败关闭）：
  声明文件必须存在且带 marker；legacy 根下不得出现未声明文件；活跃层测试不得
  直接 import 非 HTML 格式运行时（`renderers.pdf_native`、`renderers.html_ppt`、
  `renderers.pptx_master`、`application.ppt_master_job`）；marker 必须注册。
- gate 步骤（`tools/gate.sh`，全部失败关闭）：

| 步骤 | 层 | 说明 |
|---|---|---|
| ruff / mypy | 共同 | mypy 经 `python -m` 执行（见 §4 环境债 E1） |
| v1-fast-tests | 活跃层 | `-m "not retained_legacy_format"` |
| retained-legacy-fast-tests | 保留轨 | 基础回归；**不算 v1 release gate** |
| v1-layer-audit | 守护 | test_v1_test_layering.py |
| legacy-references | 共同 | check_no_legacy_refs |

### 可复现命令（本工作区副本内执行）

```bash
# 活跃层（v1 gate 口径）
uv run python -m pytest -q -m "not retained_legacy_format"
# 保留回归轨（非 v1 gate）
uv run python -m pytest -q -m "retained_legacy_format"
# 分层守护
uv run python -m pytest tests/contract/test_v1_test_layering.py -q
# 质量门（六步）
tools/gate.sh
```

分层收集数（2026-09-05，本副本）：全树 2,815 项 = 活跃层 2,694 + 保留轨 121。

注意：必须用 `uv run python -m pytest`，不要用 `uv run pytest`（原因见 §4 E1）。

## 2. 本切片修复项（RED → GREEN）

### F1（已修复）B 抽屉分子旧断言与"禁止分母回填"合同冲突

- 位置：`tests/browser/test_b_portal.py` 原 198、277 行
  `assert "分子\n51" in drawer_text`（两处）。
- 证据：`fixtures/positive/b-pnh/inputs/report-data.json` 的
  `efficacy_views.facts[eff-row-nct04558918-apply-treatment]` 中 `numerator=None`
 （来源只报告 82.3% 与分母 60，未单独报告分子；51/60=85.0% 与 82.3% 矛盾，
  属历史回填值）。渲染器对未报告分子按合同渲染互斥中文状态"来源未列示"
 （`report_b.py::_evidence_field`）。
- RED：基线全量 23 failed 中含这两条；定向复现 2 failed
 （`uv run python -m pytest tests/browser/test_b_portal.py::test_b_pnh_drawer_and_design_axes_use_the_same_native_facts tests/browser/test_b_portal.py::test_b_pnh_chart_values_groups_and_filters_are_clinically_direct`）。
- GREEN：断言改为 `"分子\n来源未列示" in drawer_text`、`"分子\n51" not in drawer_text`
 （反向防回填）且 `"分母\n60" in drawer_text`；两条测试 2 passed。
- 附带审计：`safety_views.facts`、`baseline_views.facts`、`efficacy_views.facts`
 全部 n/N 与 value 一致（脚本核验 0 处矛盾）；b-pnh 矩阵
 treatment_sample_size=62 与疗效分母 60 属"治疗人数 vs 可评估分析集"，
 为合法差异，非债。

### F2（已修复）测试夹具从百分比反推分子

- 位置：`tests/unit/reports/b/test_fresh_b_research_package.py` 原 183、208 行
  `"numerator": round(value * denominator / 100)`（疗效与安全行构造器）。
- 证据：grep 全仓唯一两处百分比→n 反推公式；与 v1.3 §5.5/§8.1
 "不得从百分比反推或回填未报告 n/N" 冲突。
- 修复：构造器改为显式报告 `numerator`（int），`value` 由 n/N 确定性复算
 （§8.1 允许方向：n/N → 比例）。调用点同步：疗效 60/96→62.5%、30/99→30.3%；
 安全 65/96→67.7%、60/99→60.6%、4/96→4.2%、3/99→3.0%；疗效差值事实
 32.4→32.2（62.5−30.3，保持夹具内部自洽）。
- GREEN：`uv run python -m pytest tests/unit/reports/b/test_fresh_b_research_package.py`
 24 passed（含 digest 绑定、门户投影一致性、独立复核负向用例）。

## 3. 全量债清单（可复现，2026-09-05）

复现命令：`uv run python -m pytest -q`（本副本，约 18 分钟）。
修复后基线：**2,770 passed、19 failed、25 errors、1 skipped**（1,070s）。
修复前基线（同一内容树，经旧解释器执行）：2,762 passed、23 failed、25 errors、1 skipped。

### A. 保留轨回归债（`retained_legacy_format`；不算 v1 release gate）

| # | 测试 | 现象 |
|---|---|---|
| A1 | tests/acceptance/test_native_pdf_slice.py::test_native_pdf_chinese_text_is_selectable_and_searchable | failed |
| A2 | tests/acceptance/test_native_pdf_slice.py::test_long_table_continuation_repeats_header_and_clinical_context | failed |
| A3 | tests/acceptance/test_native_pdf_slice.py::test_comparison_chart_page_contains_vector_drawing_not_only_raster | failed |
| A4 | tests/html_ppt/test_projection_contract.py::test_slide_counts_and_coverage_match_catalogs | failed（与当前 A/B/C page-catalog 漂移） |

处置：保留源码与测试；不进入 v1 release gate。修不修、何时修由后续版本合同
决定（恢复任一格式需新版本决策，v1.3 附录 A）。

### B. 活跃层债：preview fixture 报告快照合同（worker 01/02 范围）

根因（实测）：`run.node.failed` 事件 `reason="B 类门户引用的报告快照不存在或不可信"`，
`format:B` 失败 → 案例结果 `failed`，与期望 `completed` 不符。

| # | 测试 | 参数 |
|---|---|---|
| B1 | tests/acceptance/test_report_b.py::test_b_cases_are_bound_to_the_current_fresh_run | b-pnh |
| B2 | 同上 | b-d70-baseline-recovered |
| B3 | 同上 | b-d70-disposition-missing-pass |
| B4 | tests/integration/test_fixture_case_contracts.py::test_three_report_complete_case_is_registered_hashed_and_bound_to_current_run | three-report-complete（单报告与多报告同一根因） |

处置：等 worker 02 的 preview fixture snapshot 合同修复（开发预览确定性生成
自身 snapshot 并保持 `rendered_unreviewed`）后重跑；不是断言过期，不修改断言。

### C. 活跃层债：旧真实验收根/真实来源验收绑定（Codex 权限范围）

| # | 测试 | 现象 |
|---|---|---|
| C1 | tests/acceptance/test_full_matrix.py::test_html_pipeline_runs_project_then_requests_ego_receipts | 验收项目运行未以完成终态结束（failed；与 B 同根因后失败关闭） |
| C2 | tests/acceptance/test_full_matrix.py::test_cli_html_pipeline_prompts_for_ego_receipts | 同上 |
| C3–C22 | tests/acceptance/test_full_matrix.py 25 个 ERROR | 同一 fixture/验收根准备阶段失败关闭（AcceptanceRunnerError 前置） |
| C23–C27 | tests/acceptance/test_report_a_real.py 5 项 | "HTML 清单未绑定当前安装包摘要"——绑定旧真实验收根/旧包摘要 |
| C28 | tests/acceptance/test_report_b_real.py::test_real_b_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts | 同类 |
| C29 | tests/acceptance/test_report_c_real.py 同名绑定测试 | 同类 |

处置：真实来源验收需要隔离验收根 + 当前包摘要 + ego(lite) 回执，
由 Codex 按验收流程重建；不得以修断言方式"转绿"。

### D. 活跃层债：静态/浏览器残留（各 1 项）

| # | 测试 | 现象与证据 |
|---|---|---|
| D1 | tests/acceptance/test_r13_visual_contract_static.py::test_c_full_design_matrix_precedes_disclosure_status_chart | `template.index('id="kz-c-design-matrix"')=4700 > index('id="kz-c-chart-visuals"')=4051`；C 模板块序与旧静态合同断言漂移。属 C 类静态验收债（非 B 抽屉，不在 worker_03 修改边界内） |
| D2 | tests/browser/test_evidence_drawer.py::test_drawer_starts_below_sticky_header_and_keeps_navigation_available[webkit] | 仅 WebKit：抽屉起点与粘性页底高度断言失败；Chromium 通过。浏览器差异/环境债，需 Codex 视觉复核定位 |

## 4. 环境债（高优先，影响一切复现）

- **E1 `.venv` 控制台脚本 shebang 指向原工作区**：本副本
  `.venv/bin/{pytest,py.test,mypy,ci-workflow,playwright,jsonschema,pdf*…}`
  的包装脚本内嵌解释器路径
  `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.venv/bin/python`。
  后果：`uv run pytest` / `uv run mypy` 会静默换到原工作区解释器与 site-packages
  （实测 `ci_workflow.__file__` 解析到原树）；本次基线中的
  `test_chart_table_sync::test_packaged_echarts_contract_fail_closed`
  （`/Users/...` vs `/private/tmp/...` 断言失败）与
  `test_full_matrix::test_runner_requires_html_only_catalog_truth_and_hashed_inputs`
  即为该环境伪失败——改用本地解释器后两条自然转绿。
  已做的最小缓解：gate.sh 的 pytest/mypy 步骤改为 `uv run python -m pytest|mypy`。
  最小修复提案（需 Codex 批准后执行，本 worker 未擅自改动环境）：
  在副本内执行 `uv sync`（或重建 .venv）使 console scripts 重新绑定本副本。
- **E2 陈旧 `__pycache__`**：随树复制来的字节码缓存 co_filename 指向原工作区，
  污染 traceback 路径显示。已清理 tests/ 与 src/ 下全部 `__pycache__`（可再生物）。

## 5. 审计发现、未改动项（范围纪律）

- F3：`fixtures/positive/b-pnh/inputs/report-data.json` 顶层 `efficacy` 三行的
  n/N 与 value 矛盾（51/60=85.0% vs 82.3%；0/35=0.0% vs 1.8%；31/33=93.9% vs 92.2%）。
  抽屉/图表实际渲染走 `*_views.facts`（已验证全部一致），顶层行 n/N 未被用户可见
  表面渲染。修改会牵动 fixture 摘要/catalog，属 worker 02 fixture 元数据范围，
  建议由其决定置 None 或替换为来源一致 n/N。
- F4：`tests/unit/reports/b/test_fresh_b_research_package.py` `_baseline("sex", …)`
  对照臂 numerator=53、denominator=99 → 53.5% ≠ 报告值 55.2%（治疗组 53/96=55.2%
  一致）。低影响测试夹具不一致，建议顺带修复为按臂给 n。
- 未把任何失败"标记掉"：保留轨 4 项失败仍在 gate.sh 中失败关闭地报告；
  活跃层失败全部登记于本清单并保持原测试层可见。

## 6. 本切片改动文件清单

- `pyproject.toml`（注册 `retained_legacy_format` marker）
- `tools/gate.sh`（分层步骤 + `python -m` 调用）
- `tests/contract/test_v1_test_layering.py`（新增分层守护合同）
- `tests/browser/test_b_portal.py`（F1 断言修复）
- `tests/unit/reports/b/test_fresh_b_research_package.py`（F2 反推修复）
- 18 个保留轨测试文件的模块级 marker（见 §1 清单）
