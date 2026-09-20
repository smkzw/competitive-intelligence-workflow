我编写的三个文件都是新的未追踪文件；`git diff` 显示的修改是本会话之前就存在的，我没有触动它们。工作已完成并经验证 —— 这是我的报告。

# 执行输出: ci-phase10-task103-html-host-full-matrix - worker_01

## 边界与上下文检查

- 遵循委派模式；仅读取了初始读取集（execution context、Codex plan），以及被授权工作项 1 要求作为事实来源的 Trellis/仓库文件：Task 10.3 `prd/design/implement.md`、ADR 0013、`fixtures/acceptance/catalog.yaml` + `full-matrix-v1/`、`docs/acceptance/matrix.md`、`schemas/acceptance-catalog.schema.json`、`src/ci_workflow/application/{acceptance_catalog,fixture_runner,project_service,real_source_acceptance}.py`、`tests/acceptance/{test_fixture_catalog,test_report_a_real}.py`、`.trellis/spec/backend/{index,quality-guidelines}.md`、`tools/verify_portal.py`、`pyproject.toml`。未读取 `.codex/AGENTS.md` 或 `.hermes/SOUL.md`。
- 写入范围严格限制为三个授权文件，均为新增（未触碰任何现有文件；预先存在的 `working-tree` 更改保持不变）：`src/ci_workflow/application/acceptance_runner.py`、`tools/run_acceptance.py`、`tests/acceptance/test_full_matrix.py`。
- ADR 0013 合规性：仅存在 HTML；实现或测试中任何位置均无 PDF/HTML-PPT/PPTX 路径；未输出 `PRE_RC_REHEARSAL_OK`；未写入任何回执/Trellis 完成状态（Task 10.6/恢复/切换责任保持未动）。

## 已完成工作

已实现工作项 1（实现步骤 F02，精确节点 1），采用 RED→GREEN 顺序：

1. **Catalog HTML-only 真值解析** (`acceptance_runner.py`)：`load_acceptance_catalog()` 加载 `fixtures/acceptance/catalog.yaml`（默认路径；重复键拒绝），根据 `schemas/acceptance-catalog.schema.json` 进行校验，并明确强制执行 `release_scope=site_html_v1`、`digest_algorithm=sha256-canonical-json-v1`、`allowed_formats==["html"]`、`extra_case_policy=reject_unless_explicitly_registered`。`resolve_acceptance_case()` 仅从目录（schema const + 防御性 `_assert_case_html_only`）解析每个案例的科学真值——适应症、IANA `ZoneInfo` 验证的时区、偏移量日期时间 `data_cutoff`/`created_at`、报告、严格为 `("html",)` 的格式——通过重用 `compute_case_digest()` 重新推导 `case_digest`，检查案例族是否被批准，并按照 Task 10.1 布局规则（`full-matrix-v1`/`historical-cutoff-*` → `full-matrix-v1/`，其他 → `required-v12/<case_id>/`）推导案例 fixture 根目录。目录仍然是唯一的真值；代码或 CLI 中没有任何字段可以覆盖它。
2. **输入摘要核验**：解析时验证每个声明的输入（8 个文件）和 `expected/full-matrix.json`，确保其相对于案例 fixture 字节的存在性、路径安全性和逐字节 SHA-256；经核验的摘要通过 `ResolvedAcceptanceCase.input_digests` / `.expected_digests` 公开，供 worker_02 的运行输入交叉检查使用。
3. **空项目失败关闭合同**：`require_empty_project_root()` 要求验收项目根目录缺失或为空；任何预先存在的内容（manifest、reports/site、snapshots、receipts、`verification/`、`host-smoke/`、project workspace）均会通过精确的中文诊断导致失败关闭；非目录根目录也会被拒绝。
4. **入口** (`tools/run_acceptance.py`)：仅入口；阶段 1 编排 (`run_catalog_input_stage`) 位于应用程序模块中。CLI 仅暴露 `--catalog/--case/--project-root`；硬编码的 `_FORBIDDEN_TRUTH_FLAGS` 防护（`--indication/--timezone/--data-cutoff/--cutoff/--reports/--report/--formats/--outputs/--output-formats`）会以退出码 2 拒绝任何覆盖尝试。退出码 0 = 已核验 + 根目录为空（输出 `CATALOG_INPUTS_OK case=... reports=3 formats=1 inputs=8` + JSON 真值绑定，包含 `catalog_sha256`/`case_digest`），1 = 验收失败关闭，2 = 使用错误。
5. **测试** (`tests/acceptance/test_full_matrix.py`，20 个测试)：精确节点 `test_runner_requires_html_only_catalog_truth_and_hashed_inputs` 加上针对非 HTML 格式（目录层和案例层）、输入字节漂移、虚假声明摘要（即使重新计算 `case_digest`）、缺失输入、预期文件摘要漂移、`case_digest` 漂移、未注册案例 id、未经批准的族、8 种项目根布局（缺失/空通过；文件根目录、manifest、site、snapshot、receipt、host-smoke 失败关闭）以及 CLI 行为（覆盖拒绝 → 2；新鲜根目录 → 0 + 正确真值；预先存在的项目 → 1，且没有 `PRE_RC_REHEARSAL_OK`）的失败关闭测试。所有负面测试均在临时副本上操作；共享目录/fixture 为只读。

## 工件与证据

| 工件 | 内容 |
|---|---|
| `src/ci_workflow/application/acceptance_runner.py` | `AcceptanceRunnerError`, `AcceptanceCaseInput`, `AcceptanceExpectedFile`, `AcceptanceCatalog`, `ResolvedAcceptanceCase`, `load_acceptance_catalog`, `_assert_case_html_only`, `resolve_acceptance_case`, `require_empty_project_root`, `run_catalog_input_stage` |
| `tools/run_acceptance.py` | 仅入口 CLI；真值覆盖防护；退出码 0/1/2；仅从阶段 1 输出 `CATALOG_INPUTS_OK` |
| `tests/acceptance/test_full_matrix.py` | 20 个测试，包括 `implement.md` 节点 1 |

证据：`tests/acceptance/test_full_matrix.py::test_runner_requires_html_only_catalog_truth_and_hashed_inputs` 绿色；针对 `full-matrix-v1` 解析出的真值 = 特应性皮炎 / Asia/Shanghai / `2026-07-31T23:59:59+08:00` / 报告 A,B,C / 格式仅 html / 8 个输入摘要与声明的目录值逐字节匹配（例如 `inputs/report-a-data.json` → `8460ff9a…503b3`）；`case_digest=2c2698bf…0f9c7f`；`catalog_sha256=499d644e…4777ca`。

## 命令与观察结果

- RED：`uv run pytest tests/acceptance/test_full_matrix.py -q` → `ModuleNotFoundError: ci_workflow.application.acceptance_runner`。
- GREEN：相同命令 → **20 通过**。`tests/acceptance/test_fixture_catalog.py` 回归测试 → **35 通过**（目录 fixture 完好）。
- `uv run ruff check <3 files>` → 所有检查均通过；`uv run mypy <runner + cli>`（严格模式） → 无问题。
- Shell 冒烟测试：新鲜临时根目录 → 退出码 0，显示 `CATALOG_INPUTS_OK case=full-matrix-v1 reports=3 formats=1 inputs=8` + JSON 绑定；`--indication 篡改适应症` → 退出码 2，显示 "不得覆盖…科学真值"；带有 `manifests/current_run.json` 的根目录 → 退出码 1，显示 "验收项目根必须不存在或为空；发现预存内容：manifests=预存运行清单"。
- 集成安全：`tools/check_no_legacy_refs.py` → `LEGACY_REF_OK`；`tests/contract/test_package_manifest.py` + `test_bundle_packaging.py` → 5 通过（新文件未破坏清单/包契约）。
- 会话期间的更正：修复了两个起草 Bug（在编辑前发现了自身缺陷——`_copy_case` 缺少案例目录段；非 HTML 测试最初将有效案例包裹在 `pytest.raises` 中），并将摘要漂移测试细化为两个真正的场景，与 Task 10.1 的 `input_hash_drift` 语义保持一致。

## 障碍或缺失环境

无。未遇到缺失的工具或环境；未进行任何安装。

## 重跑请求或下一步

- Worker_02 的集成点（未完成，根据项目划分）：在空根检查后，运行 three-report-complete 项目，然后按照 `fixtures/acceptance/full-matrix-v1/inputs/run-binding-contract.json` 中的 `binding_rules_zh` 绑定 `run_manifest.case_id == full-matrix-v1`、`run_manifest.case_digest == catalog digest` 和 `run_manifest.input_hashes == ResolvedAcceptanceCase.input_digests`。注意：该 fixture 的 `case_digest` 字段为 `null`；运行器应在运行时提供目录摘要——不需要 fixture 更改，且由于不在我的工作范围内，我没有对其进行任何修改。
- 供 Codex 集成参考：worker_03 负责固定的 `PRE_RC_REHEARSAL_OK ... release_cases_closed=0` 信号；阶段 1 特意不输出该信号。`ResolvedAcceptanceCase` 还携带 `owner_task`/`execution_scope` 以进行回执路由。
- 此会话中无需重新运行；所有分配的工作项 1 证据均已在上述命令中捕获。
