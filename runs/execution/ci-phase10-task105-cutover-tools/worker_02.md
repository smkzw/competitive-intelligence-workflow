# Execution Output: ci-phase10-task105-cutover-tools - worker_02

## Boundary And Context Check

- CWD 为 runner 绑定的工作区 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`，本次为纯只读审计（work item 2），未创建、修改或删除任何文件；未运行 pytest（测试设计审计属 worker_03 范围）。
- 已读初始 read set 两文件；为覆盖审计对象，额外只读以下来源并在此申报：Task 10.5 PRD/设计/实施/task.json、Task 10.4 完成检查点、`fixtures/acceptance/catalog.yaml` 与 `fixtures/acceptance/required-v12/catalog-fragment.yaml`、`docs/acceptance/matrix.md`、`schemas/release-case-receipt.schema.json`、`schemas/host-receipt.schema.json`、`schemas/acceptance-catalog.schema.json`、`migration/legacy_manifest.schema.json`（键级摘要）、`tools/verify_release_receipts.py`、`tools/legacy_cutover.py`（仅恢复包门与 validate 段）、`src/ci_workflow/application/acceptance_catalog.py`、`src/ci_workflow/hosts/receipt.py`（头部合同说明）、`src/ci_workflow/sources/receipts.py`（头部）、`tests/acceptance/test_required_receipt_closure.py`、`tests/acceptance/test_fixture_catalog.py`（required-v12 相关段）、`pyproject.toml`（依赖键）。
- 未读取生产路径、真实旧根、`/Users/smkzw/.codex/AGENTS.md`、`/Users/smkzw/.hermes/SOUL.md`；未联网。

## Work Performed

审计三条线：(1) required-v12 catalog 现状；(2) 现有 pre-RC receipt 语义全景；(3) 新 release-case receipt schema/owner-stage closure 的最小字段与负例覆盖。核心结论先行：

**总体判断（推断）**：Task 10.5 的 release 侧实现（schema + verifier + 正向/漂移负例测试）已存在且未提交（全部 `??` untracked），其字段集与 PRD 第 6/7 条逐项对得上，catalog 侧 18 案例双向闭合且摘要零漂移（已实测验证）。存在 1 个 P1 合同指针缺口（catalog `receipt.schema` 指向 host-receipt schema 而 verifier 既不使用也不校验它）和若干 P2/P3 收口建议，均可在当前未提交状态下低成本修复。

### A. required-v12 catalog 审计（观察 + 实测证据）

- 唯一机器目录为共享 `fixtures/acceptance/catalog.yaml`（23 案例：1 full-matrix + 4 historical-cutoff + 18 required-v12），`fixtures/acceptance/required-v12/catalog-fragment.yaml` 为 18 案例批准片段；两者顶层结构不同（共享目录有 `release_scope: site_html_v1`/`catalog_id`/`requirements`/`digest_algorithm`，片段仅 `schema_version`+`cases`）。verifier 必须以**共享目录**为 `--catalog` 入参；若误传片段会以 `catalog release_scope/cases 合同无效` 失败（失败关闭，无风险，但对未来调用方是个坑，建议在工具 docstring 注明）。
- 实测（只读内存计算）：shared 18 例与 fragment 18 例 id 集合相等；逐案例 `compute_case_digest` 重算与声明 `case_digest` **零漂移**（两文件均 NONE）；shared 与 fragment 同 id 案例内容摘要完全一致。
- `compute_case_digest`（`acceptance_catalog.py`）覆盖除 `case_digest` 自身外**全部**案例字段，含 `receipt.owner_status`、`inputs[].sha256`、verifiers、invariants——即 catalog 侧防篡改是完备的，且 input 摘要经 case_digest 传递性绑定。
- owner 路由现状：18 例中 17 例 `owner_status: pending_future_owner`，仅 `optional-adapter-recovery` 为 `not_applicable`（带顶层 `not_applicable:` 中文理由 + `execution_scope: conditional-extension` + owner `extension-e1-optional-adapter-recovery`）。三个 owner task：`phase-10-task-106-rc-freese`（16 例）、`phase-10-task-108-legacy-absence`（legacy-absence）、`extension-e1-optional-adapter-recovery`。与 matrix.md 责任阶段列语义一致（推断：106 即“最终 RC 冻结”阶段，须在冻结时实际执行 recovery-rehearsal 才能闭合，属预期失败关闭行为）。
- catalog 案例级 `receipt` 块（schema 合同）：`relative_path` + `schema` + `owner_status`（枚举含 current_owner/pending_future_owner/verified/host_unavailable/not_applicable）。

### B. 现有 pre-RC receipt 语义全景（观察）

| 回执族 | kind / 载体 | 绑定语义 | 与新 receipt 的关系 |
|---|---|---|---|
| 宿主回执 | `host-smoke-v1`（`schemas/host-receipt.schema.json` + `hosts/receipt.py`） | 包名/版本/摘要、fixture 案例与逐文件输入摘要、真实入口、可执行文件 provenance、进程/会话（PID/argv/退出码）、事件链、no-draft 断言、最终 manifest；状态敏感条件（blocked→零产物+no_draft，complete→≥1 HTML 产物）；`receipt_digest`=除自身外规范 JSON SHA-256，构造即校验 | 自摘要算法与新 release-case receipt 完全同族（排序键、紧凑分隔符）；pre-RC 运行级证据，不承担 RC 冻结语义 |
| 来源回执 | `SourceReceipt`（`sources/receipts.py` + `domain/evidence`） | 逐 gap 采集尝试、13 类 result_class 区分技术故障 vs 未找到 vs 已取得；gap_id 强绑定、回执 id 去重 | 运行时语义，非发布闭环 |
| 恢复包回执 | `recovery-package-v1` | 仅存在**消费端**：`tools/legacy_cutover.py:361` 要求 kind+`status=="passed"`+`recovery_package_sha256`+`issued_at`，摘要进 authorization | **无 schema、无生产者**（测试中伪造）。Task 10.6 必须补合同，且须含上述四个字段，否则 10.5 的 validate 门无法在真实链路闭合 |
| 迁移清单 | `migration/legacy_manifest.schema.json`（JSONL 项） | 28 项，migrated/not_migrated、old_path/realpath/inode 类字段、hash_basis、redaction、final_disposition、runtime_dependency | Task 10.4 已冻结；为 10.5 inventory/apply 的授权来源 |
| 切换回执 | `legacy-cutover-validation-v1` / `apply` / `absence-check-v1` | 绑定 inventory_sha256+authorization_sha256+recovery_receipt_sha256，canonical 自摘要 | worker_01 范围，此处仅作语义相邻确认 |

### C. 新 release-case receipt 最小字段与负例审计

**schema（`schemas/release-case-receipt.schema.json`，`receipt_kind: release-case-v1`）字段集与 PRD 第 6 条逐项对照**：catalog 摘要✓（verifier 重算文件字节比对）、package 摘要✓（同）、RC 摘要✓（CLI 入参，格式强制小写 hex64）、owner task✓（与 catalog 案例精确比对）、run/session✓（仅存在性+minLength）、input/artifact/verdict 摘要✓（字段在，见 Gap-2）、时间✓（`issued_at` format date-time + 必须显式时区后缀）、身份✓（case_id/release_scope/case_digest 全部回绑 catalog）、自完整性✓（`receipt_digest` 重算）。条件约束：`accepted`→artifact 必为 sha256 且理由为 null；`not_applicable`→artifact 必 null + 理由必填 + `project_contract_sha256` 必为 sha256（verifier 再绑真实合同文件摘要）。`pending_future_owner`/`rejected` 在聚合层一律失败关闭（“未在 owner 阶段 accepted”），`not_applicable` 仅放行 `execution_scope==conditional-extension` 且案例带非空 `not_applicable` 理由者——与 PRD 第 7 条精确一致。

**已有负例测试（`test_required_receipt_closure.py`，5 个测试）**：schema 严格性（未知字段拒绝、accepted+null artifact 拒绝）；全量正闭合（18 例，`not_applicable_case_ids==["optional-adapter-recovery"]`）；pending 不计 accepted；owner_task 漂移、非可选 not_applicable、not_applicable 合同摘要错配；package 摘要漂移、receipt 自摘要不匹配。

**缺口与建议（按优先级）**：

- **P1｜Gap-1 合同指针未失败关闭**：18 个案例的 `receipt.schema` 均指向 `schemas/host-receipt.schema.json`，而 verifier 按 `DEFAULT_SCHEMA` 用 release-case-receipt schema 校验，且完全不读取 `receipt_contract["schema"]`。当前靠 `receipt_kind: release-case-v1` const 隐式拒绝错 kind 回执，但 catalog 指针与实际校验合同脱钩，属未绑定指针。建议二选一并合做：(a) 将 18 案例 `receipt.schema` 改指 `schemas/release-case-receipt.schema.json`——注意这会改变全部 18 个 `case_digest`，需同步重算 shared+fragment 两份（`test_fixture_catalog` 的闭合/漂移负例会强制一致性，属机械改动）；(b) verifier 增加一行检查：`receipt_contract["schema"]` 必须等于声明常量（或以 `release-case-receipt.schema.json` 结尾），否则失败关闭。
- **P2｜Gap-2 `input_sha256` 无验证绑定**：schema 要求该字段、自摘要覆盖它，但 verifier 不重算。测试里语义是 `sha256(canonical_json(case["inputs"]))`，verifier 完全可用同一规范化从 catalog 重算比对（复用 `canonical_case_payload` 思路）。若不打算验证，它只是装饰性字段，与 PRD“绑定 input digest”的语义不符。建议：verifier 增加 `input_sha256 == sha256(canonical_json(案例 inputs 列表))` 比对，或降级文档说明为 owner 自声明字段。同理 `artifact_sha256`/`verdict_sha256` 聚合层只能存在性校验（receipts_root 无产物文件），属可接受的声明一致性证明，但应在工具 docstring 明示“闭合≠产物存在性验证”，避免误读。
- **P2｜Gap-3 缺失负例（代码路径已实现、无测试钉住）**：缺回执文件；catalog `case_digest` 漂移（需临时 catalog 副本）；receipt `relative_path` 越界（`..`/绝对路径）；required-v12 case id 重复；目录无 required-v12 案例；RC 摘要格式非法；`catalog_sha256`/`release_scope` 回绑漂移；`issued_at` 无时区（FormatChecker 路径）；`status=="rejected"` 拒绝；摘要格式错误（schema pattern 路径）。建议按现有 `_mutate_receipt`/临时 catalog 模式补 6–8 个参数化负例。
- **P3｜Gap-4 schema 纪律**：`pending_future_owner` 与 `rejected` 无条件约束（如 pending 可带非 null artifact、rejected 可带 not_applicable 理由）。聚合层已失败关闭，属纵深防御，可加一条 if/then（pending→artifact 与理由均 null）。另：多案例共享同一 `relative_path` 未显式查重（第二案例会因 case_id 回绑失败，仍是失败关闭，仅报错不够直观）。
- **P3｜Gap-5 运维语义**：verifier 首错即抛（只报第一个未闭合案例）且全有全无；Task 10.6 冻结时 legacy-absence 必然仍 pending→工具必然失败直到 10.8 完成。这与 PRD 语义一致（YAGNI，不建议加 partial 模式），但 Codex 需知道 10.6 阶段该工具“红”是预期态。`catalog_sha256` 为整文件字节摘要——冻结后对**任何**案例（含 historical）的编辑都会作废全部 18 张回执，属最强防篡改但要求“先冻 catalog、后发回执”的顺序纪律。
- **P3｜编辑性**：recovery-rehearsal 不变量含“Task 10.3 不得提前关闭”、legacy-absence 含“不得在 Task 10.6 recovery 或 Task 10.3 rehearsal 阶段…”——两处任务编号疑似互换/过时（10.3=html-host-full-matrix，恢复演练责任在 10.6/后续恢复阶段）。文本被 case_digest 覆盖、不影响机器闭合，但建议 RC 冻结前人工订正一次，避免 owner 阶段误读。（不确定性：不排除编号另有所指，仅标记待确认。）

## Artifacts And Evidence

- 本任务为只读审计，未产出代码/文档工件；交付物即本报告。
- 关键证据文件与行号：`tools/verify_release_receipts.py:85-95`（release_scope/cases/重复 id 失败关闭）、`:106-112`（case_digest 漂移、receipt 缺失、路径越界）、`:120-131`（七项回绑）、`:133-146`（optional/not_applicable 门与 pending 拒绝）；`schemas/release-case-receipt.schema.json:47-66`（状态敏感 allOf）；`src/ci_workflow/application/acceptance_catalog.py:35-55`（case 覆盖面）；`tools/legacy_cutover.py:344-364`（recovery-package-v1 消费合同）；`schemas/acceptance-catalog.schema.json`（case required 含 owner_task/receipt/case_digest；`receipt.owner_status` 枚举；`release_scope` const site_html_v1）；`tests/acceptance/test_fixture_catalog.py:752-814`（18 例双向闭合、批准 id 黄金集、owner 状态断言）。
- Task 10.5 五文件 git 状态：全部 untracked（`tools/legacy_cutover.py`、`tools/verify_release_receipts.py`、`schemas/release-case-receipt.schema.json`、`tests/migration/test_legacy_cutover.py`、`tests/acceptance/test_required_receipt_closure.py`，另有依赖 `src/ci_workflow/application/acceptance_catalog.py`）；catalog/schema/matrix 相关（`fixtures/acceptance/`、`schemas/acceptance-catalog.schema.json`、`docs/acceptance/matrix.md`）亦全部 untracked——整个 Phase 10 验收层尚未入版本库。

## Commands And Observations

- `find`/`ls`/`git status --porcelain`（限定相关路径）：定位 Task 10.5 文件与未提交状态。
- `grep -rn "receipt_kind|receipt-kind"`（src/schemas/tools/migration）：确认 receipt kind 全景为 host-smoke-v1、recovery-package-v1、legacy-cutover-validation/apply/absence-check-v1、release-case-v1。
- `python3 -c`（只读，`sys.path.insert` 加载仓库内 `acceptance_catalog` 重算摘要）：shared required-v12=18、fragment=18、id 集合相等；两文件 `compute_case_digest` 漂移均为 NONE；shared↔fragment 内容漂移 NONE；owner_status 仅 {pending_future_owner, not_applicable}（后者仅 optional-adapter-recovery）；owner task 共 3 个。
- `python3 -c` 解析 `schemas/acceptance-catalog.schema.json` 与 `migration/legacy_manifest.schema.json`：取 required/properties/枚举。
- 未运行 pytest、未运行任一 Task 10.5 工具（遵守“只读”边界）；测试 GREEN/RED 状态留给 Codex/worker_03 验证。

## Blockers Or Missing Environment

- 无环境缺失；jsonschema/pyyaml 均为已声明项目依赖（`pyproject.toml`），工具可运行。
- 非 blocker 的跨任务缺口（申报给 Codex 决策）：`recovery-package-v1` 回执目前无 schema、无生产者，仅 `tools/legacy_cutover.py:344-364` 的消费合同（kind+passed+`recovery_package_sha256`+`issued_at`，canonical 自摘要）。Task 10.6 定义该合同时必须至少包含这四个字段，否则 10.5 validate 门在真实链路无法闭合。
- 未验证项：测试套件实际运行结果、`tools/legacy_cutover.py` 全量实现质量（worker_01/03 范围）。

## Rerun Requests Or Next Step

- 给 Codex 的三个待决断（均小改动，可在未提交状态下直接并入 Task 10.5）：
  1. Gap-1：是否将 18 案例 `receipt.schema` 改指 release-case-receipt schema（需同步重算两份 catalog 的 18 个 case_digest），并让 verifier 校验该指针（推荐 (a)+(b) 同做）。
  2. Gap-2：`input_sha256` 改为 verifier 可重算绑定，或在 schema description 中明示为 owner 自声明字段。
  3. Gap-3/4：补 6–8 个缺失负例 + schema 对 pending/rejected 的纵深约束。
- 若 Codex 批准上述任一项，可派回本会话继续（我已持有全部上下文）；编辑性编号订正（Gap-5 recovery-rehearsal/legacy-absence 文案）建议随 RC 冻结前人工审阅一并处理。
