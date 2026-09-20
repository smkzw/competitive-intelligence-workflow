所有验证已完成。最终状态：88 个测试通过，lint 已清理，实际运行证明了端到端的 fail-closed 行为。我现在正在撰写最终报告。

````
# 执行输出: ci-phase10-task103-html-host-full-matrix - worker_03

## 边界与上下文检查

- 只读初始读集两份文件（execution context、execution plan），随后为完成分配项按 context 的 Source Of Truth 追加只读：`.trellis/tasks/09-01-phase-10-task-103-html-host-full-matrix/{prd,design,implement}.md`、`docs/decisions/0013-site-first-v1-delivery-scope.md`、`docs/acceptance/matrix.md`、`fixtures/acceptance/catalog.yaml` 与 `required-v12/*/inputs/scenario.json`、`src/ci_workflow/application/{acceptance_catalog,host_smoke_runner,host_smoke}.py`、`src/ci_workflow/hosts/receipt.py`、`tests/acceptance/test_fixture_catalog.py`、`tests/hosts/test_real_host_smoke.py`（仅头部，确认其自带测试替身、可在本环境通过）。
- 写入严格限定在授权三文件：`src/ci_workflow/application/acceptance_runner.py`、`tools/run_acceptance.py`、`tests/acceptance/test_full_matrix.py`（三者在会话开始时即为未提交的新文件，已含 worker_01/02 的阶段 1-3 实现；我在其上追加 F04 层，未改动既有阶段行为，仅更新了两文件的模块 docstring/用法说明）。
- 未写任何验收项目、pre-RC 回执文件、Trellis 完成态、评审/指标文件或视觉结论；未生成 PDF、HTML-PPT、PPTX；未启动浏览器；未联网；未安装任何包。恢复/切换/未来格式责任未关闭：运行期间与回执载荷中 `recovery-rehearsal`、`legacy-absence`、未来格式均保持 `pending_future_owner`，`release_cases_closed=0`。

## 已执行工作

Work item 3（F04）：实现 required-v12 full-matrix 场景 rehearsal 回执，并保护 recovery、legacy 与未来格式责任不被误关闭。

1. **套件解析**（`resolve_full_matrix_suite`）：套件成员完全由 catalog 的 `execution_scope=full-matrix` 决定（当前 16 例：`full-matrix-v1` + 15 个 required-v12 案例）；每个成员经完整 HTML-only、案例摘要与逐文件 SHA-256 核验。未登记的执行范围、空套件、缺少 A/B/C 基准案例均失败关闭。
2. **场景 rehearsal 回执**（`build_full_matrix_suite_receipts`）：对每个套件案例逐条执行其 catalog 声明的 verifier（真实 pytest 命令；字符串声明合成 `uv run pytest <target> -q`，结构声明要求 `kind: pytest`、命令以 `uv run pytest` 开头且包含其 target，防 catalog 夹带任意命令），结果以精简摘要（target、command、exit code、耗时、输出 SHA-256，不落原始日志）绑定进回执；子 case 从案例目录 `scenario.json` 逐项枚举并重新核验字节（case_id/release_scope/formats/子场景结构任一漂移失败关闭）。任一 verifier 未通过即失败关闭、不产出回执。
3. **责任保护**（同函数内分类层）：
   - 套件案例 → `pre_rc_rehearsal`（`release_case_closed: false`，仅表示"已预演"）；
   - `recovery-rehearsal`、`legacy-absence` → `pending_future_owner`（按 catalog 回执所有权映射，附 Task 10.6/10.8 中文原因；**不执行**其 verifier，因其责任未到时点）；
   - `optional-adapter-recovery` → `not_applicable`（按项目合同，runner 不猜测）；
   - 4 个 `historical-cutoff-*`（Task 10.1 已持有 `current_owner`）→ `outside_suite`，不改写其归属（判断：按 PRD"恢复、切换及未来格式保持 pending_future_owner"指的是恢复/切换责任，将其已接受案例标为 pending_future_owner 会失实；其 catalog 所有权逐字记录在 `catalog_receipt_owner_status` 供 Codex 复核）；
   - 未来格式（pdf/html-ppt/pptx）单独记录为 `pending_future_owner`/`release_case_closed: false`（依据 ADR 0013），不进入任何回执格式集合；
   - `release_cases_closed` 由载荷重算（出现任何关闭状态/`release_case_closed=true` 即异常），恒为 0；catalog 回执出现 runner 不可识别的关闭语义（如 schema 允许的 `verified`）时失败关闭。
4. **流水线阶段处理器**（`build_pre_rc_receipts_stage`）：供 `run_pre_rc_rehearsal` 注入的 `pre-rc-receipts` 处理器；要求上下文提供 pre-RC 运行身份、案例/摘要绑定、未漂移 catalog、A/B/C 三报告 + 三份浏览器回执的前置流水线摘要，以及恰好绑定 codex/hermes/omp 三宿主且 `ok=true` 的宿主冒烟阶段摘要（宿主摘要若携带 `pre_rc_run_id` 必须与本次一致，防复用旧宿主回执）。
5. **固定成功信号**（`format_pre_rc_rehearsal_ok`）：仅当六阶段全部通过、格式严格 `["html"]`、三宿主已绑定、`release_cases_closed=0`、回执状态与计数完整时渲染 `PRE_RC_REHEARSAL_OK reports=3 formats=1 hosts=3 cases=… rehearsed=… future_owner=… not_applicable=… outside_suite=… release_cases_closed=0 pre_rc_run_id=…`；其余一律 `成功信号被拒绝` 异常。独立套件模式（无宿主）组装的摘要无法渲染该信号。
6. **CLI**（`tools/run_acceptance.py`）：新增 `--suite full` 独立场景 rehearsal 模式（与 `--pipeline`/`--bind-ego-receipts`/`--case`/`--project-root` 互斥，冲突退出码 2），输出 `SUITE_REHEARSAL_RECEIPTS_OK … release_cases_closed=0 …`；失败关闭退出码 1。`PRE_RC_REHEARSAL_OK` 仍只留给完整六阶段流水线，当前任何入口都不会打印。流水线模式现要求显式 `--project-root`（缺省给出指向 `--suite full` 的指引）。

## 产出物与证据

- `src/ci_workflow/application/acceptance_runner.py`：新增约 700 行 F04 层（常量、`ScenarioVerifierOutcome`、`subprocess_verifier_runner`、`resolve_full_matrix_suite`、`_load_case_subscenarios`、`_declared_verifier_commands`、`_bind_host_smoke_summary`、`build_full_matrix_suite_receipts`、`build_pre_rc_receipts_stage`、`run_full_matrix_suite_rehearsal`、`format_pre_rc_rehearsal_ok`，均已加入 `__all__`）。
- `tools/run_acceptance.py`：`--suite` 接线、互斥校验、`SUITE_REHEARSAL_RECEIPTS_OK` 输出、docstring 更新。
- `tests/acceptance/test_full_matrix.py`：新增 21 个 F04 测试，含精确节点 `test_suite_full_rehearses_current_scope_without_closing_future_owner_receipts`（真实 catalog + 注入 stub verifier：16 例 rehearsed、2 pending_future_owner、1 not_applicable、4 outside_suite、子场景逐项绑定、release_cases_closed=0、固定信号渲染与 13 种拒绝路径）。
- 验证证据：
  - `uv run pytest tests/acceptance/test_full_matrix.py tests/acceptance/test_fixture_catalog.py -q` → **88 passed**；
  - `uv run ruff check`（三文件）→ All checks passed；
  - 真实 `--suite full` 全量试跑（38 条声明 verifier）：**37 条通过**（含 `host-smoke-v1` 的三宿主替身 smoke 与 fresh-install preflight），第 38 条 `tests/acceptance/test_legacy_negative_regressions.py::test_all_six_negative_subclasses_are_rejected` 因**该测试文件在重建工程中尚不存在**（pytest 退出码 4）而失败关闭：CLI 输出 `验收失败关闭：案例 legacy-negative-regressions 场景预演存在未通过的 verifier…（退出码 4）`、退出码 1、stdout 无任何 OK 信号——失败关闭行为符合预期；
  - 组合演练：`build_pre_rc_receipts_stage` 处理器注入六阶段上下文后，`format_pre_rc_rehearsal_ok` 输出 `PRE_RC_REHEARSAL_OK reports=3 formats=1 hosts=3 cases=23 rehearsed=16 future_owner=2 not_applicable=1 outside_suite=4 release_cases_closed=0 pre_rc_run_id=pre-rc-run_compose`。

## 命令与观察

- `uv run pytest …`、`uv run ruff check …`、`uv run python tools/run_acceptance.py --suite full [×冲突组合]`、`uv run python - <<EOF` 冒烟脚本（套件解析/回执分类/组合信号）。观察：套件 16/23 分类与 counts（16/2/1/4）稳定；38 条声明 verifier 全部被枚举且仅 1 条目标文件缺失；CLI 五种冲突/缺参组合均退出码 2 并给出中文用法指引；真实全量试跑失败关闭路径干净（无 JSON、无信号、退出码 1）。
- 观察到并保留的既有行为：`run_pre_rc_rehearsal` 要求空项目根且第三阶段 ego(lite) 回执在编排内部即时核验——同一进程单次调用内回执无法先于项目运行存在，因此六阶段在单次调用内尚无法完整走通（详见下一步）。

## 阻碍或缺失环境

1. **缺失声明 verifier 文件（阻塞 standalone `--suite full` 输出 OK）**：`tests/acceptance/test_legacy_negative_regressions.py::test_all_six_negative_subclasses_are_rejected`（catalog 中 `legacy-negative-regressions` 案例声明，`owner_task: phase-10-task-106-rc-freeze`）。最小补救建议：由 Codex 裁决归属——在 Task 10.6 前补齐该六类负向回归测试，或将其从该案例 verifier 中调整；本 worker 未越权代写（属 Task 10.6 范围内容）。
2. **worker_04 接口契约（需对齐，非阻塞本工件）**：我的回执聚合阶段要求宿主冒烟阶段摘要形如 `{"ok": true, "hosts": {"codex": {"ok": true, …}, "hermes": {…}, "omp": {…}}, "pre_rc_run_id": …(可选但出现即须一致)}`；进程/会话/运行互异的深核验由 worker_04 的阶段自身负责。
3. **需 Codex 决策（非阻塞本工件）**：六阶段编排跨 ego 回执暂停的驱动方式（如 `run_pre_rc_rehearsal` 增加 resume 语义，或由集成入口以 `bind_ego_receipts_pipeline` 产物构造上下文调用剩余阶段）。我的阶段处理器只消费上下文契约，两种方案均兼容。

## 重跑请求或下一步

- 建议 Codex 复核：① 历史截止案例按 `outside_suite`（而非 pending_future_owner）分类的裁决；② 回执仅以内存摘要返回、未持久化到 `docs/acceptance/pre-rc-runs/<pre_rc_run_id>/`（持久化属 Codex 集成后的授权写入）；③ 上述宿主摘要契约与六阶段驱动方式。
- 可继续项：worker_04 完成宿主/项目核验处理器后，将 `build_pre_rc_receipts_stage(verifier_runner=…)` 注入 `run_pre_rc_rehearsal` 即可产出可渲染 `PRE_RC_REHEARSAL_OK` 的完整摘要；standalone `--suite full` 在补齐缺失的 `test_legacy_negative_regressions.py` 后即可全绿。
- 复现命令：`uv run pytest tests/acceptance/test_full_matrix.py tests/acceptance/test_fixture_catalog.py -q`；`uv run python tools/run_acceptance.py --suite full`。
````
