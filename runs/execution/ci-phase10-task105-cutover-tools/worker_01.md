# Execution Output: ci-phase10-task105-cutover-tools - worker_01

## Boundary And Context Check

- 只读审计任务（Work Item 1），未创建、未修改、未删除任何仓库文件；未对真实旧根 `/Users/smkzw/Documents/AI Products/竞品调研工作流` 执行 inventory/apply 或任何读取（仅将其字符串作为 `check_no_legacy_refs.py` 既有代码的阅读对象，未执行该路径扫描）。
- 运行器报告路径 `runs/execution/ci-phase10-task105-cutover-tools/worker_01.md` 未写；完整报告在本次响应中返回。
- 读到的初始上下文：`context/ci-phase10-task105-cutover-tools_execution_context.md`、`plans/codex_execution_ci-phase10-task105-cutover-tools.md`。未读 `/Users/smkzw/.codex/AGENTS.md`、`/Users/smkzw/.hermes/SOUL.md`。
- 重要时序观察：会话开始（10:34:34）时 Task 10.5 的五个目标文件均不存在；审计期间实现并行推进，10:37 出现 `tools/legacy_cutover.py`，10:39–10:44 五个文件全部落盘，且工具文件在我两次阅读之间被修订（532 行 → 578 行）。本审计以 10:44 修订版为准。**代码仍在活跃编辑中，最终以 Codex 冻结版为准复核。**

## Work Performed

对精准 inventory/validate/apply/absence-check 的最小失败关闭合同、路径与 inode/symlink 边界做了三层工作：

1. **合同溯源**：从 PRD（`.trellis/tasks/09-02-phase-10-task-105-cutover-tools/prd.md`）、设计（`design.md`）、实施步骤（`implement.md`）与批准规格 §19.2/§20.3/§20.4（`docs/specs/competitive-intelligence-workflow-design-v1.2.md:845-866`）提取权威要求；对照 Task 10.4 交付物（`migration/legacy_manifest.jsonl` 28 条、schema、`tests/migration/test_manifest_closure.py`）与既有先例（`tools/check_no_legacy_refs.py`、`tools/bundle_contract.py`、`schemas/host-receipt.schema.json`）。
2. **实现审计**：逐行审计 `tools/legacy_cutover.py`（578 行，10:44 版）的失败关闭合同、路径/包含/符号链接/inode 边界、幂等性与授权摘要链。
3. **无写入验证**：AST 解析、venv ruff 静态检查，以及 12 项纯内存守卫探针（只引用不存在的路径，`sys.dont_write_bytecode=True`，零文件系统写入）实证各失败分支确实失败。

### 结论（先说结果）

实现整体高质量地满足 PRD #1–#5 的失败关闭合同，核心边界（无默认旧根、lstat-only、逐级 symlink 拒绝、escape 拒绝、inode/device/摘要漂移拒绝、授权摘要精确匹配、逐项处置+空目录 rmdir、幂等重放）全部在位且经探针实证。发现 **1 个需要 Codex 裁决的 P1 合同分歧**和 2 个 P2 健壮性缺口（均保持失败关闭，但错误面不受控）。

### P1 — absence-check 对 `retain` 项的语义与 design.md 分歧，且对含 retain 项的 registry 构成合同死锁

- **证据（观察）**：10:44 版 `tools/legacy_cutover.py:509-513` 的 `absence_check` 对**所有**登记项检查 `exists`，不再按 action 过滤（我阅读的第一版是 `entry["action"] == "delete"`，后被改为全量）；`tests/migration/test_legacy_cutover.py:207-212`（`test_absence_check_does_not_treat_retain_as_absent`）把这一行为固化为测试预期。而 `design.md` 明文：“所有登记为**必须消失**的 runtime/reference 项均不存在才通过”；PRD #5 的措辞是“已登记旧运行时或消费者引用残留”（kind 域措辞）。三者各指向一种语义。
- **推断（为何是 P1）**：`apply` 对 `retain` 项明确不做文件系统动作（`legacy_cutover.py:470-472`，outcome=`retained`）。因此按现实现，**任何含 retain 项的 registry 永远无法通过 absence-check**——apply 拒绝删它、absence-check 又因它存在而失败，Task 10.8 `legacy-absence` 对这类 registry 不可闭合。这是死锁，不只是措辞问题；除非真实受治理 registry 全部为 delete。
- **建议（供裁决，三选一并同步文档+测试）**：
  - **方案 A（推荐）**：absence-check 只对 `action=delete` 项要求不存在（与 design.md 逐字一致）；同时补充 registry 解析期规则：`retain` 项不得位于任何 `delete` 动作目录的子树内（矛盾处置在解析期拒绝）。需修改 `test_absence_check_does_not_treat_retain_as_absent` 的预期。
  - 方案 B：保留现实现（全量必须不存在），在任务文档中修订 design.md 该句，并把 `retain` 改名为 `defer` 或直接从 `ACTIONS` 移除——否则 `retain` 是一个不可用动作。
  - 方案 C：按 PRD #5 的 kind 域解释（`legacy_root/legacy_skill/launcher/symlink/consumer_reference/cache/backup` 必须消失，`archive_copy` 可保留）——较复杂，不推荐首选。
- 该裁决须在测试冻结前做出，因为现有测试已锚定现行为。

### P2 — apply 处置与观察环节的 OSError 未包装，错误面不受控（失败关闭仍成立）

- **证据**：`tools/legacy_cutover.py:483-485` 的 `path.rmdir()`/`path.unlink()`，以及 `file_digest`（:49-54）、`_directory_digest`（:152-175）、`os.readlink`（:148,167,183）均可能抛 `OSError`（ENOTEMPTY、EACCES、TOCTOU 落空等），未被转换为 `CutoverError`，CLI 只捕获 `CutoverError`（:570）→ 原生 traceback 退出码 1。
- **评价**：失败关闭方向正确（尤其目录删除坚持 leaf-wise + `rmdir`，全仓无 `shutil.rmtree`，这是“精准”的正确姿态，必须保留）；但治理执行要求统一 `LEGACY_CUTOVER_FAIL` 审计输出。
- **建议**：在处置循环与摘要计算处 `except OSError as error: raise CutoverError(f"文件系统操作失败：{entry_id}：{error}")`。

### P2 — registry 解析期不拒绝“delete 目录包含 retain 后代”的矛盾处置

- **证据**：`_parse_registry`（:229-269）只查重复 path/entry_id；delete 祖先+retain 后代在 apply 时才暴露（retain 先“保留”，delete 父目录 `rmdir` 因非空失败 → 结合上一条成为原生 OSError）。
- **建议**：解析期按路径前缀关系检测 delete↔retain 祖先矛盾并 `CutoverError`（与 P1 方案 A 的规则同一条）。

### 值得肯定并锁进验收的关键边界（证据均经探针/测试实证）

- **无默认旧根**：全工具无任何默认路径常量（对比 `check_no_legacy_refs.py:13-15` 的 `DEFAULT_LEGACY_ROOT`）——PRD 非目标“不对真实旧根执行”在代码层成立。
- **lstat-only 观察**：`_observe_entry`/`_directory_digest` 全程 `lstat`+`scandir`，不跟随、不递归发现未注册路径；symlink 项记录 `os.readlink` 摘要且绝不进入目录递归（无环风险）。
- **根级+祖先级 symlink 拒绝**：`_reject_symlink_ancestors`（:112-128）在最新修订中新增批准根自身 lstat 拒绝（:113-117），测试 `tests/migration/test_legacy_cutover.py:140-159` 已覆盖 alias-root symlink 拒绝——这正是我第一轮审阅发现的缺口，实现者已在我复核前补上。
- **路径逃逸拒绝**：lexical `relative_to` 于未解析路径 + 最深根匹配（:99-109），探针实证 `/etc/passwd` 被拒。
- **漂移拒绝**：validate 全结构比对（含 realpath/device/inode/type/摘要，:369-371），测试用“删除后重写同路径文件”实证 inode 漂移被拒。
- **授权摘要链**：registry/inventory/authorization/validation receipt 四级自摘要 + 跨绑定（inventory_sha256、registry_sha256、逐项 actions 全等、recovery_receipt_sha256），探针 5–9 实证任一环节篡改即拒。注意这是**篡改可见性（tamper-evidence）而非防篡改（tamper-resistance）**——同一操作者可重算全部自摘要；信任锚是受治理流程，建议在 Task 10.8 受治理执行说明中明示这一边界。
- **幂等重放**：重放 exit 0、文件系统终态相等、outcome 变为 `already_absent`（探针 10、测试 ：185-189）。注意首跑与重放的 `apply_sha256` 不同（outcomes 措辞不同）——“相同终态”指文件系统；Task 10.8 若绑定 `apply_sha256` 应意识到闭环后重放会产生不同回执（建议不要在闭环后重放）。
- **dry-run 语义**：无独立命令；`inventory` 即 §20.4 的“干运行清单”（构造上只读），测试 `test_inventory_is_exact_and_dry_run_is_non_mutating` 以全 inventory 结构等价（含 device/inode）+ 目标树状态前后一致证明非变异——满足 PRD #2，可接受，无需加命令。
- **敏感内容纪律缺口（提示，非本工具缺陷）**：`hash_mode=content` 的目录项会递归读取全部文件内容。Task 10.4 对 session/cache/credentials 只用固定无内容哨兵；生成真实 registry 时这些类必须用 `metadata` 模式。建议把该纪律写进 Task 10.8 受治理 registry 的生成规则（工具层可不强制）。

### 跨任务接口记录（供 Codex 与 worker_02/03 参考）

- `recovery-package-v1` 回执目前**没有生产者**：字段集（`schema_version/receipt_kind/status/recovery_package_sha256/issued_at`）只存在于 `validate_cutover` 的 `_require_keys`（:350-364）和测试夹具。Task 10.6（恢复责任阶段，见 `src/ci_workflow/application/acceptance_runner.py:2589,2751`）生产该回执时必须逐字段对齐此隐式合同；建议 Task 10.6 前将其落为共享常量或 JSON schema。
- absence-check 状态基（仅校验登记路径本身）符合“不扩大到未注册路径”非目标；§20.4 的主动无残留扫描（安装根/启动器/缓存登记等更广面）属于 Task 10.8，勿在本工具内扩权。

## Artifacts And Evidence

- 审计对象（只读）：`tools/legacy_cutover.py`（578 行，10:44 修订版）；`tests/migration/test_legacy_cutover.py`（213 行）。
- 合同源：`prd.md`、`design.md`、`implement.md`、`task.json`（Task 10.5）；`docs/specs/competitive-intelligence-workflow-design-v1.2.md:845-866`（§20.3/§20.4）、`:814`（§19.2 恢复包演练）；Task 10.4 `checkpoint_20260902_completed.md`。
- 先例与接口：`migration/legacy_manifest.schema.json`、`migration/legacy_manifest.jsonl`（28 条）、`tests/migration/test_manifest_closure.py`、`tests/migration/test_no_legacy_runtime_dependency.py`、`tools/check_no_legacy_refs.py`、`tools/bundle_contract.py`、`schemas/host-receipt.schema.json`、`src/ci_workflow/application/acceptance_runner.py:2589,2751,2956`。
- 本审计未产出任何文件（只读边界）；全部证据在上文与下节命令输出中。

## Commands And Observations

- `ast.parse(tools/legacy_cutover.py)` → `AST_OK`（用 `.venv/bin/python3` 3.12.13）。
- `.venv/bin/ruff check --no-cache tools/legacy_cutover.py` → `All checks passed!`。
- 纯内存守卫探针（`.venv/bin/python3 -c`，`sys.dont_write_bytecode=True`，仅引用不存在的 `/tmp/cutover-audit-probe-nonexistent/...` 路径，零 fs 写入）12/12 通过：inventory 确定性（两次构建全等）、逃逸拒绝、未知字段拒绝、重复 path 拒绝、未通过 recovery 拒绝、recovery 摘要不匹配拒绝、合法链产出 validation receipt、篡改 inventory（inode）拒绝、authorization actions 不一致在 apply 拒绝、缺席项重放幂等（`already_absent`×2，两次回执摘要相等）、absence 通过、伪造 exists=True 残留拒绝。
- 时序证据：`ls -la` 显示五文件落盘时间 10:37–10:44；`tools/legacy_cutover.py` 在我两次读取间从 20100B/532 行变为 20984B/578 行（新增根级 symlink 拒绝、`_matches_directory_after_child_deletes`、absence_check 语义变更、`_require_keys` 签名修订）。
- 环境观察：`/usr/bin/python3` 为 Xcode CLT 3.9（无 `typing.Never`）；项目 `pyproject.toml` 要求 `>=3.12,<3.14`，ruff 0.16.2 仅在 `.venv`。工具经 `#!/usr/bin/env python3` 直调在本机可能落到 3.9——与兄弟工具同一约定（经 `.venv` 运行），非缺陷，记录备查。

## Blockers Or Missing Environment

- 无环境阻塞。唯一需要 Codex 决策的是 P1（absence-check retain 语义三选一），裁决须先于测试冻结；P2 两项为建议性修补。
- 不确定项：实现仍在并行推进，本审计锚定 10:44 版；`_matches_directory_after_child_deletes`（:425-443）以 device/inode 身份键放行目录摘要漂移、以 `rmdir` 仅删空目录兜底——该权衡方向正确（否则“先删子项再删父目录”必然误报漂移，工具不可用），但它不校验漂移确由已注册子项删除引起，未注册新增文件会落到 ENOTEMPTY 兜底（结合 P2-1 应包装为 CutoverError）。

## Rerun Requests Or Next Step

- 请求 Codex：(1) 裁决 P1 语义并对齐 design.md/代码/测试三方；(2) 批准 P2 两项最小修补（OSError→CutoverError 包装；registry 解析期 delete↔retain 祖先矛盾拒绝）；(3) 冻结后将本审计的探针清单（12 项）并入冻结前复核或交 worker_03 并入测试设计审计。
- 无需重跑本审计的命令；所有探针可由 Codex 用同一只读方式复现（`.venv/bin/python3` + 不存在路径 + `sys.dont_write_bytecode=True`）。
