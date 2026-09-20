# Execution Output: ci-phase10-task103-html-host-full-matrix - worker_02_ego_correction

## Boundary And Context Check

- 续接同一会话的执行模式修正。本轮仅写入原先授权的三个文件（`src/ci_workflow/application/acceptance_runner.py`、`tools/run_acceptance.py`、`tests/acceptance/test_full_matrix.py`，均为未跟踪状态，与前一轮一致）；git status 中其余 `M` 条目（.trellis/docs/fixtures 等）是本会话之前已存在的改动，原样未动。
- 已从实现与测试中**完全移除** Playwright/Chromium/WebKit/`tools/verify_portal.py` 链路：无启动、无调用、无结论读取、无安装建议。全部测试零浏览器执行。未读取其他执行者报告，未启动代理，未宣称最终验收。
- 对 ego-browser（ego-lite）SKILL.md 仅做只读查看以确认其输出形态（Node 运行时经 `cliLog` 输出，无固定回执 schema），因此回执合同由本 runner 定义、Codex 集成时按合同产出；本轮未调用 ego(lite)。

## Work Performed

**1. 删除浏览器命令链路（runner + tests）**：删除 `BROWSER_VERIFY_TOOL_PATH`、`AcceptanceCommandRunner`、`default_acceptance_command_runner`、`_REQUIRED_BROWSERS`、`_verify_browser_report`/`_bind_browser_verdict`/`verify_current_html_verdicts`/`run_html_browser_stage`，以及测试中的 `_fabricate_portal_verdict`、`_recording_runner`、`subprocess.CompletedProcess` 命令桩、PNG/trace 伪造器。`subprocess`/`sys` 导入从 runner 移除。保留 `real_source_acceptance._artifact_output`/`_parse_datetime`（运行清单产物发现与时间解析，与浏览器无关）。

**2. 阶段 3 重写为“接收并严格绑定 Codex 在 ego(lite) 中生成的浏览器回执"**（`run_ego_receipt_stage` + `_load_and_bind_ego_receipt`）：
- 约定路径：`<项目根>/verification/<报告>/<版本>/ego-receipt.json`（A/B/C 各一份）。
- 回执合同（`schema_version="1.0"`）：`tool` 必须逐字等于 `ego-lite`（`EGO_LITE_TOOL_IDENTITY`）；`ok: true`；绑定**当前 run id 与 pre_rc_run_id**（与当前运行清单逐字比对）、**当前 HTML artifact manifest id**、**report snapshot id**、**site digest**（SHA-256 格式且等于当前产物摘要）、**实际路由集合**（无重复、与当前站点地图合同集合完全一致、逐页结论一一对应）、**规定视口**（`PRESCRIBED_VIEWPORTS = [[1280,800],[1440,900],[1920,1080]]` 逐项声明）、**验收时间**（`verified_at` 带时区且不早于运行开始时间，回执文件 mtime 同样不得早于运行开始）。
- 失败关闭矩阵：回执缺失 → `EgoReceiptPendingError`（`AcceptanceRunnerError` 子类，携带 `missing_paths` 与明确指引）；旧回执、缺页、页面失败、摘要不符、非 ego 工具、身份不符、视口不符 → `AcceptanceRunnerError`。绑定原子化：三份全部校验通过才产出阶段摘要。
- 阶段名保持 `html-artifacts-browser-verdicts`（与 design.md“浏览器 verdict 绑定”语言一致，回执即其载体）；runner 自身不启动任何浏览器。

**3. 编排调整**：`run_html_pipeline`（新项目：阶段 1-2 真实执行 → 阶段 3 回执缺失时抛 pending）、新增 `bind_ego_receipts_pipeline`（已运行项目的回执绑定入口：重新核验 catalog/案例摘要、当前运行清单完整性、案例与 pre-RC 绑定后执行严格绑定，不重跑项目）；`run_pre_rc_rehearsal` 移除 `command_runner` 参数，第三阶段即回执绑定。阶段顺序常量 `PRE_RC_STAGE_ORDER` 不变。

**4. CLI（`tools/run_acceptance.py`，131→216 行）**：`--pipeline html` 在回执缺失时**退出码 3**，stderr 明确提示“真实浏览器验收必须由 Codex 使用 ego(lite) 完成，本入口不会回退到任何其他浏览器”，并逐路径列出三份回执应写入的位置与全部必绑字段；新增 `--bind-ego-receipts`（仅限与 `--pipeline html` 同用，否则用法错误退出码 2），绑定成功输出 `EGO_RECEIPTS_OK`；退出码表更新为 0/1/2/3。`PRE_RC_REHEARSAL_OK` 仍不由任何入口输出。

**5. 测试重写（`tests/acceptance/test_full_matrix.py`，699→796 行，F02 段原样保留）**：模块级 fixture 真实执行一次阶段 1-2（约 2s），故障用例复制项目树（保留 run id 与产物绑定），仅验证回执合同。实现三个精确节点（名称与 implement.md 一致）：`test_runner_orders_project_render_browser_hosts_and_project_verify`（六阶段顺序 + A→B→C 回执顺序 + 绑定不关闭未来责任）、`test_current_run_manifest_binds_three_html_artifacts_and_browser_verdicts`（三产物三回执逐项绑定 + 旧回执/伪摘要/篡改站点负向）、`test_runner_fails_closed_on_...`（10 个参数化故障：缺失回执、非 ego 工具、缺页、页面失败、站点摘要不符、run id 不符、清单标识不符、视口不符、旧回执文件、缺失产物）。另有 pending 流程测试（阶段 1-2 确已执行、指引含精确回执路径）、`run_pre_rc_rehearsal` 预检失败关闭测试、4 个 CLI 测试（html 流水线退出码 3 + ego 指引；绑定入口缺回执退出码 3；提供回执后 `EGO_RECEIPTS_OK`；`--bind-ego-receipts` 单独使用被拒）。说明：节点 4 名称中的"nonzero command"分支随浏览器命令执行一并移除（runner 不再运行任何命令），已在测试 docstring 注明。

**6. 清理**：已删除本会话生成的 `.artifacts/task103_cli_probe/`、`.artifacts/task103_probe/`、`.artifacts/task103_cli_stdout.txt`、`.artifacts/task103_cli_stderr.log`，以及首轮探针残留 `.artifacts/task103_cli_probe_stdout.json`、`.artifacts/task103_cli_probe_stderr.log`；`.artifacts/` 下无 task103 残留。其他工件未动。

## Artifacts And Evidence

- 修改文件（未提交，待 Codex 集成审阅）：`acceptance_runner.py`（1478 行）、`run_acceptance.py`（216 行）、`test_full_matrix.py`（796 行）。
- 验证结果：`uv run pytest tests/acceptance/test_full_matrix.py -q` → **37 passed in 8.88s**（20 F02 无回归 + 17 F03；全程零浏览器进程）；回归 `tests/acceptance/test_fixture_catalog.py tests/hosts/` → **54 passed, 1 skipped**；`uv run ruff check <三文件>` → All checks passed；`uv run mypy src/ci_workflow/application/acceptance_runner.py tools/run_acceptance.py` → no issues（测试文件单独跑 mypy 的报错模式与既有已验收测试一致，属项目 tests/ 基线）。
- 浏览器残留扫描：三文件中唯一 "playwright" 字样是负向用例注入的 `tool="playwright"` 字符串，用于断言非 ego 工具被拒绝（不启动、不安装、不读取任何 Playwright 组件）。

## Blockers Or Missing Environment

- **需 Codex 知悉（未授权清理项）**：前一轮为验证真实浏览器链路安装的 `~/Library/Caches/ms-playwright`（约 829MB，安装前该目录仅含 `.links`/4KB）仍在本机。本轮无权删除用户缓存目录，且删除不在指定的清理清单内；如需回收请 Codex 决定（`rm -rf ~/Library/Caches/ms-playwright` 即可完全回滚）。修正后的实现与测试不再引用它。
- **C 类真实渲染发现的存档说明**：前一轮真实浏览器探针发现 C 类 10/16 路由 `content_occlusion`（`kz-c-design-matrix__th`/`field-cell`、`kz-chart-table__th` 粘性元素，跨引擎跨视口逐字一致，截图显示无实际遮挡，指向 `qc/browser.py` 检测器对横向滚动容器的边界盒误判）。该探针原始产物已按清理指令删除，结论文字保留于前一份 worker 报告；若 Codex 仍需该证据，可在 ego(lite) 验收时复核同一路由集合。

## Rerun Requests Or Next Step

- 剩余验收全部属于 Codex 的集成责任，我未执行也未宣称：(1) 使用 ego(lite) 对 full-matrix-v1 的 A/B/C 站点（`reports/<R>/v-fixture-001/html`）完成真实浏览器验收；(2) 按 `<项目根>/verification/<R>/v-fixture-001/ego-receipt.json` 提供三份回执，字段合同见 `acceptance_runner.py` 的 `EGO_LITE_TOOL_IDENTITY`/`PRESCRIBED_VIEWPORTS`/`_load_and_bind_ego_receipt`（tool="ego-lite"、run_id、pre_rc_run_id、manifest_id、report_snapshot_id、site_digest、routes、viewports、pages 逐页 ok、verified_at）；(3) 以 `tools/run_acceptance.py --pipeline html --bind-ego-receipts` 完成绑定（缺回执时该入口会以退出码 3 给出逐路径指引）；(4) ego(lite) 回执合同如需调整字段名或身份串（当前 `ego-lite`），改动点集中在 runner 常量与绑定函数一处。
- 我的修正工作项已完成并全部验证；无需重跑。
