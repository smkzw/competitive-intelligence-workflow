审计完成，探针临时文件已清理。以下为完整报告。

# Execution Output: ci-phase10-task105-cutover-tools - worker_03

## Boundary And Context Check

- 已读初始指定文件：`context/ci-phase10-task105-cutover-tools_execution_context.md`、`plans/codex_execution_ci-phase10-task105-cutover-tools.md`。本 pass 仅执行工作项 3：审计 Task 10.5 测试设计、tmp_path 隔离、恢复包门、授权摘要、幂等性风险，识别遗漏与相邻回归；只读。
- 额外读取（理由：审计对象即这些文件本身及其相邻回归面，均为仓库内只读）：`.trellis/tasks/09-02-phase-10-task-105-cutover-tools/{prd,design,implement,task.json}`、Task 10.4 checkpoint、`tools/legacy_cutover.py`、`tools/verify_release_receipts.py`、`schemas/release-case-receipt.schema.json`、`tests/migration/test_legacy_cutover.py`、`tests/acceptance/test_required_receipt_closure.py`、`tests/migration/{test_manifest_closure,test_legacy_manifest_contract,test_no_legacy_runtime_dependency}.py`、`tests/acceptance/test_legacy_negative_regressions.py`、`migration/legacy_manifest.{jsonl,schema.json}`（仅头部样例行）、`fixtures/acceptance/catalog.yaml`（字段 grep）、规格 v1.2 §19–20、`pyproject.toml`、`tests/graph/test_graph_node_contracts.py`（局部）。
- 只读边界保持：未写入仓库任何文件；行为探针与 mypy 缓存全部位于 `/tmp` 且已清理；pytest 以 `-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE=1` 运行；ruff 用 `--no-cache`。未触碰真实旧根（其路径仅出现在已授权仓库文件 `migration/legacy_manifest.jsonl` 的记录文本中）。无网络访问。
- 重要前提：**审计期间实现 worker 仍在持续写入**。五个目标文件从“部分缺失（我首轮检查时 schema 与两测试尚不存在）”到 10:48:02 全部就位，`legacy_cutover.py` 在审计中至少更新两次（10:41:50 → 10:44:44）。以下发现全部锚定时间戳，冻结前需按第 7 节复核。

## Work Performed

1. 对照 PRD/design/implement 与规格 v1.2 §20.3/§20.4（切换门槛、删除旧工程合同）逐条审计五个文件的当前版本。
2. 对 `tools/legacy_cutover.py`（@10:44:44）在 `/tmp` 临时 fixture 根上执行了 8 组最小行为探针：幂等重放、retain+absence 组合、非空目录删除、部分 apply、空洞通过（不存在根）、恢复包门负例、叶符号链接越根、授权动作序/附加动作。
3. 以无缓存方式运行两个新测试文件与静态检查（pytest/ruff/mypy strict），核对相邻回归面（Task 10.4 清单测试、旧依赖扫描、acceptance catalog、graph recovery 节点命名）。
4. 汇总测试设计遗漏、相邻回归与需 Codex 裁决的语义分歧。

## Artifacts And Evidence

被审计文件（报告时点版本）：

| 文件 | mtime | 状态 |
|---|---|---|
| `tools/legacy_cutover.py` | 10:44:44 | 573 行，inventory/validate/apply/absence-check 四命令 + 授权摘要链 + 恢复包门 |
| `tools/verify_release_receipts.py` | 10:47:45 | required-v12 回执聚合验证器，绑定 catalog/package/RC/合同摘要 |
| `schemas/release-case-receipt.schema.json` | 10:39:09 | 严格 schema（additionalProperties=false，status 条件分支） |
| `tests/migration/test_legacy_cutover.py` | 10:43:47 | 4 个测试（含 10:43 新增的 retain-absence 钉死测试） |
| `tests/acceptance/test_required_receipt_closure.py` | 10:48:02 | 8 个测试（schema 严格性、owner 闭合、pending 负例、漂移负例） |

关键行为探针结果（全部在 `/tmp` fixture 根，证据已随探针清理，结论如下）：

- **O1（最重要，语义分歧）**：`absence_check`（@10:44:44）对**所有**登记项检查存在性，无 `action=="delete"` 过滤（grep 证实）。含 `retain` 条目的 registry 在 apply 成功后 absence-check 必然失败（探针：retain 的 `keep.txt` 被报为残留 `['keep']`）。worker 已在 10:43:47 加入 `test_absence_check_does_not_treat_retain_as_absent`（tests/migration/test_legacy_cutover.py:207）把该语义**有意钉死**。但 design.md 写的是“所有登记为**必须消失**的项均不存在才通过”（即 delete 项），PRD §5 写的是“任何**已登记**旧运行时或消费者引用残留”——两份规格在此点措辞分歧，代码+测试选择了 PRD 字面严格读。后果：同一 registry 上 apply(retain)→absence-check 链条永假，真实切换 runbook 必须以“全 delete 终态 registry”或“retain 项外部移除后”运行最终 absence 门。需 Codex 裁决并把裁决写回 design.md 或测试。
- **O2（错误合同不一致 + 非原子）**：已登记删除的目录内含未登记内容时，`path.rmdir()` 抛裸 `OSError(Errno 66)`，**不是** `CutoverError`；`main()` 只捕获 `CutoverError`，CLI 会打印 traceback 而非 `LEGACY_CUTOVER_FAIL`。且 apply 非原子：同深度条目按序处理，`a.txt` 已删、目录失败时无回执、无回滚（探针证实部分状态残留）。行为上仍失败关闭（absence 门会红），但错误出口与可恢复性未定义。
- **O3**：delete 父目录 + retain 子项是结构性不可能完成的组合（子项 retain 后父目录永不为空 → O2 的 OSError）。无测试覆盖此组合。
- **O4（空洞通过）**：approved_root 从未存在时，inventory/validate/apply/absence-check 全链绿灯（`already_absent`/`absent`）。授权摘要链能防漂移但防不了“registry 写错根导致全程空转”。真实切换属受控任务且有人工审查缓冲；建议钉死语义或加“至少一项存在”要求。
- **O5**：恢复包门负例正确拒绝：`status="failed"` → “恢复包回执尚未通过”；摘要不匹配 → “恢复包回执摘要与授权不匹配”。但**测试文件没有恢复包门负例**（见 T1）。
- **O6**：授权摘要链正确：actions 重排、附加动作、自摘要篡改（repo 测试覆盖 `authorization_sha256` 路径）均被拒。
- **O7（幂等）**：重放 apply 终态一致、outcomes 变为 `already_absent`、receipt 摘要必然不同——与 design“重复执行返回相同终态”一致；repo 测试断言的是终态+outcome 语义，正确。
- **O8**：指向根外的**叶**符号链接被接受（unlink 不跟随、摘要为链接目标哈希，删除安全；realpath 已记录但从不比对）。是否要按“路径逃逸”拒绝/标记，属设计问题非缺陷。
- **O9**：pytest（两新文件）12 passed；`ruff check` 4 文件全过；`mypy --strict` 两工具文件 0 issue。
- **O10**：闭环侧测试覆盖良好：`pending_future_owner` 不得 accepted、owner 漂移、非可选适配器 `not_applicable` 拒绝、not_applicable 未绑定项目合同拒绝、package/receipt 摘要漂移拒绝，全部存在且通过。

## Commands And Observations

- `.venv/bin/python -B /tmp/cutover_probe*.py`（4 轮，stdlib-only 直连 `tools.legacy_cutover`）→ O1–O8 证据。
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -p no:cacheprovider -q tests/migration/test_legacy_cutover.py tests/acceptance/test_required_receipt_closure.py` → `12 passed in 0.68s`（对 tool@10:44:44 + 测试@10:43:47/10:41:50；10:47/10:48 的更新未复跑）。
- `.venv/bin/ruff check --no-cache <4 文件>` → All checks passed；`.venv/bin/mypy --cache-dir=/tmp/mypy-audit-cache tools/{legacy_cutover,verify_release_receipts}.py` → Success（strict）。
- `git status --short`（限定五文件）→ 全部为新增未跟踪（`??`），Task 10.5 足迹恰为五个指定文件，未改动既有文件——与 PRD“完成证据”一致。
- 环境：系统 `python3` 为 3.9.6，`from typing import Any, Never` 在其下必然 ImportError；项目 `requires-python >=3.12`，`.venv` 为 3.12.13——一切运行必须走 `.venv`/`uv run`。

### 测试设计遗漏清单（对照 PRD F02“先写负向测试”）

- **T1（P2）**：`tests/migration/test_legacy_cutover.py` 无恢复包门负例（status≠passed、recovery 摘要不匹配、recovery 未知字段）。代码已正确（O5 探针），但缺回归保护，PRD 明确要求。
- **T2（P1）**：无 OSError 包装/部分 apply/断点续跑语义测试（O2/O3）。
- **T3（P2）**：无空洞通过语义钉死测试（O4）。
- **T4（P3）**：registry/authorization/recovery 的未知字段拒绝（`_require_keys`）无 cutover 侧测试。
- **T5（P3）**：CLI 层（`main` 退出码 0/1、`--output`、失败消息格式 `LEGACY_CUTOVER_FAIL`）完全未测，负向测试全在 Python API 层。
- **T6（P3）**：registry `kind` 与观测 `node_type` 从不交叉校验（首清点即可把 symlink 误标为 file，仅靠后续摘要漂移兜底）——建议钉死或校验。
- **T7（P3）**：恢复包回执的 `issued_at`/`recovery_package_sha256` 无格式校验（无 schema、无 hex/时间格式约束）。

### 相邻回归面结论

- 新测试完全基于 `tmp_path` 构造 fixture，未引用 `migration/legacy_manifest.jsonl` 真实旧根路径——隔离保持；真实 registry 派生一致性留待 Task 10.8 受控任务，符合边界。
- `verify_release_receipts` 只读真实 `fixtures/acceptance/catalog.yaml`（18 个 required-v12 案例，字段齐备）、回执写 `tmp_path`；对 `ci_workflow.application.acceptance_catalog.compute_case_digest` 的依赖方向为 tools→package，合规。
- 小缺口：回执 `not_applicable_reason_zh` 未要求等于 catalog `not_applicable` 文本（任何非空中文串可通过）；`receipts_root` 内符号链接文件会被读取跟随（路径无 `..`/绝对，风险低）。仅记录。
- graph `recovery` 节点的 `recovery_receipt`（tests/graph/test_graph_node_contracts.py:67）是字符串 id，与 `recovery-package-v1` 回执仅命名相近，无耦合。
- `check_no_legacy_refs.py` 扫描面不受新文件影响（新文件无真实旧根路径字符串）。

## Blockers Or Missing Environment

- 无阻断。两点记录：(1) 系统 python3 3.9.6 不可运行本工具，需 `.venv`/`uv run`（venv 已就绪）；(2) 审计对象为移动目标，10:47:45/10:48:02 的最后两次更新未纳入 pytest 复跑，O 系列结论以 10:44:44 版工具为锚，冻结前须复验。

## Rerun Requests Or Next Step

给 Codex 的裁决与建议（按优先级）：

1. **裁决 O1 语义**：absence 门按 PRD 字面“所有已登记项”还是 design.md“必须消失（delete）项”。若维持现实现+钉死测试，请同步修订 design.md 措辞，并在真实切换 runbook 中规定最终 absence 门使用全 delete 终态 registry；若采纳 design.md，则恢复 action 过滤并删除/改写 `test_absence_check_does_not_treat_retain_as_absent`。
2. **要求实现 worker 修复 O2**：在 apply 处置循环把 `OSError` 包装为 `CutoverError`（保持 `LEGACY_CUTOVER_FAIL` 单一失败出口），并在文档/检查点写明 apply 非原子、断点续跑依赖重放 `already_absent`；补 T2 测试（含 delete 父 + retain 子的结构性拒绝案例）。
3. **补 T1**（恢复包门负例）、**T3**（空洞根语义钉死）、T4–T7。
4. 冻结前复跑：两测试文件 + 相邻回归（`tests/migration/`、`tests/acceptance/test_legacy_negative_regressions.py`）+ ruff/mypy，并以最终版本复核 O1–O4 是否仍成立。
5. O8（叶符号链接越根仅记录不拒绝）请 Codex 确认是否接受为设计意图。

本 worker 未修改任何仓库文件；未对真实旧根执行 inventory/apply；未做同行评审与会商。
