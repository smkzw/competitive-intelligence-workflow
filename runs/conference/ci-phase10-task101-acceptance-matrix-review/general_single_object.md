I'll start by reading the conference context and Codex plan, then audit Task 10.1 acceptance-matrix materials against the required-v12 families and ADR 0013.
# Conference Participant Output: ci-phase10-task101-acceptance-matrix-review - general_single_object

## Boundary Check

- **Within scope:** Read-only audit of `fixtures/acceptance/**`, `schemas/acceptance-catalog.schema.json`, `tests/acceptance/test_fixture_catalog.py`, `docs/acceptance/matrix.md`, `docs/decisions/0013-site-first-v1-delivery-scope.md`, Trellis Task 10.1 contracts, and execution evidence under `runs/execution/ci-phase10-task101-acceptance-matrix/`.
- **Out of scope honored:** No file edits, no fresh-source A/B/C runs, no RC, no production paths, no final visual/browser acceptance.
- **Blocked external SoT:** `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` is cited as authoritative but **not readable** in this workspace. Independent closure against the approved plan’s 18 machine families cannot be fully completed.
- **Commands run:** `uv run pytest tests/acceptance/test_fixture_catalog.py -q` → **35 passed**; `uv run pytest tests/contract/test_package_manifest.py -q` → **1 passed**.

---

## Independent Work Product

### Overall verdict: **需修复（有条件通过）**

Task 10.1 的**目录骨架、ADR 0013 收窄、脱敏摘要可重算、责任阶段分层、中文矩阵说明**已基本到位，且 23-case catalog 与 18 个 `required-v12` 族在仓库内**自洽闭合**。但当前实现存在**自证循环**、**悬空 verifier**、**打包未闭合**和**任务状态未完成**四类阻断，尚不能将 `pytest` 通过等同于“验收矩阵已完整闭合”。

---

### 1. 与批准 18 族 / 23-case catalog 的闭合性

| 检查项 | 证据 | 结论 |
|---|---|---|
| 案例总数 | `catalog.yaml`：1 full-matrix + 4 historical-cutoff + 18 required-v12 = **23** | ✅ 数量闭合 |
| 18 族 ID 集合 | `tests/acceptance/test_fixture_catalog.py` `_APPROVED_REQUIRED_V12_IDS`（18 项）与 `required-v12/catalog-fragment.yaml`、共享 `catalog.yaml` 双向一致 | ✅ 仓库内闭合 |
| 子场景闭合 | `_APPROVED_SUBSCENARIO_IDS` 与每个 `required-v12/<id>/inputs/scenario.json` 的 `subscenarios` 精确匹配；含 6 个 legacy-negative 子类 | ✅ |
| 与批准计划独立对照 | 批准计划文件不可读 | ⚠️ **无法独立证明** 18 族来自计划而非实现时硬编码 |
| Trellis 任务状态 | `task.json` = `in_progress`；`implement.md` 全部 `[ ]` | ❌ 任务未收口 |

**关键异议：** `worker_03_round2.md` 明确写道 *“Independently hardcoded the approved required-v12 set of exactly 18 IDs”*。测试中的批准集合是**仓库内自引用常量**，不是从可读的外部计划派生。这构成**自证循环**：catalog 证明 catalog，测试证明测试里的列表。

---

### 2. ADR 0013（HTML-only）合规

| 检查项 | 证据 | 结论 |
|---|---|---|
| 允许格式 | `requirements.allowed_formats: [html]`；所有 case `formats: [html]` | ✅ |
| 四格式不阻断 | `full-matrix-v1` `prohibited_outcomes` 明确禁止以 PDF/HTML-PPT/PPTX 缺失阻断 HTML | ✅ |
| 收窄子场景 | `b-interaction-cross-format` / `multi-report-partial-delivery` / `kangzhe-and-large-project-runtime` 含 `adr-0013-html-only` 或 `adr-0013-no-pptx-simulation` 子场景 | ✅ |
| `scenario.json` 延后声明 | `deferred_formats: ["pdf","html-ppt","pptx","powerpoint-confirmation"]` | ✅ |
| 旧格式回流 | 无 case 将 PDF/PPT 列为必选；`legacy-negative-regressions` 仅负向引用 | ✅ |
| 命名残留 | case id 仍含 `cross-format` | ⚠️ 可接受（已文档化收窄），但验收人员可能误读为四格式门槛 |

**ADR 0013 实质性合规；未发现把 PDF/PPT 重新抬为首版阻断项。**

---

### 3. 脱敏输入摘要 / 路径可重算

| 检查项 | 证据 | 结论 |
|---|---|---|
| 逐文件 SHA-256 | `full-matrix-v1` 8 个输入 + 4 个 historical 输入 + 18 个 `scenario.json` 均有声明摘要 | ✅ |
| 文件存在且一致 | `test_fixture_catalog.py::_assert_case_files` 校验磁盘摘要 | ✅ |
| `case_digest` | `acceptance_catalog.py` + 测试重算 `sha256-canonical-json-v1` | ✅ |
| IANA / cutoff | `full-matrix-v1` = `Asia/Shanghai` + `2026-07-31T23:59:59+08:00`；历史场景 cutoff 冻结 | ✅ |
| `full-matrix-v1` 脱敏链 | `provenance.json` 声明 `deidentified: true`, `identity_verified: true` | ✅ |
| `required-v12` 输入厚度 | 每族仅 1 个 `scenario.json`（元数据合同），**无** case 级 report-data fixture | ⚠️ 摘要可重算，但**场景输入过薄** |
| Verifier 与 catalog 输入绑定 | Verifier 指向既有 unit/integration 测试，**不读取 catalog case 输入** | ❌ **验证链断裂** |

---

### 4. 责任阶段 / 回执 / 是否提前关闭未来责任

| 案例 | `expected.state` | `receipt.owner_status` | `owner_task` | 评价 |
|---|---|---|---|---|
| `optional-adapter-recovery` | `not_applicable` | `not_applicable` | `extension-e1-optional-adapter-recovery` | ✅ E1 合同摘要绑定正确 |
| `recovery-rehearsal` | `pending_future_owner` | `pending_future_owner` | `phase-10-task-106-rc-freeze` | ✅ 未提前关闭 |
| `legacy-absence` | `pending_future_owner` | `pending_future_owner` | `phase-10-task-108-legacy-absence` | ✅ 未提前关闭 |
| 其余 15 个 RC 阶段族 | 多为 `snapshot_locked` / `evidence_blocked` | **全部** `pending_future_owner` | `phase-10-task-106-rc-freeze` | ⚠️ 语义分层正确但易误读 |
| 全部 23 case | — | **23 个 receipt JSON 均不存在** | — | ⚠️ 占位路径，尚无真实回执 |

测试 `_assert_required_owner_and_state_rules` 强制：除 `optional-adapter-recovery` 外，所有 required-v12 的 `receipt.owner_status` 必须为 `pending_future_owner`。**机器层面未提前关闭未来责任**，这是优点。

**异议：** `expected.state: snapshot_locked` 与 `receipt.owner_status: pending_future_owner` 并存，若验收人员只看 catalog 不看 matrix，可能误以为场景已通过。`matrix.md` 已用“最终 RC 冻结前”缓解，但 catalog 字段本身仍偏乐观。

---

### 5. 失败关闭测试

**已通过（35/35）：**
- catalog ↔ fragment 双向闭合
- 缺失/替换/额外 case 拒绝
- `case_digest` / 输入摘要漂移拒绝
- 非 HTML 格式、绝对路径、未脱敏拒绝
- 子场景批准集合精确匹配
- owner/state 规则

**未覆盖的关键缺口：**

1. **4 个 verifier 目标文件不存在：**
   - `tests/hosts/test_optional_adapter_resume.py`
   - `tests/migration/test_recovery_rehearsal.py`
   - `tests/migration/test_legacy_cutover.py`
   - `tests/acceptance/test_legacy_negative_regressions.py`

2. **测试不校验 verifier 目标存在或可执行**——只检查 `kind`/`target` 字符串非空。

3. **没有测试执行 catalog 中声明的 verifier**——catalog 的“验证器”目前是**文档性指针**，不是可运行验收门。

---

### 6. 中文医学验收说明（`docs/acceptance/matrix.md`）

| 检查项 | 结论 |
|---|---|
| 面向医学/验收人员语言 | ✅ 全中文临床语境，无 `snapshot_locked` 等内部码泄露到用户表 |
| 结果解释表 | ✅ 区分成功交付 / 关键证据不足 / 未公开 / 技术问题 / 等待后续责任 / 条件不适用 |
| 18 族说明 | ✅ 每族有“要证明什么 / 成功 / 阻断 / 责任阶段” |
| 子场景要求 | ✅ 明确要求 `scenario.json` 逐项声明 |
| ADR 0013 边界 | ✅ “后续格式恢复边界”专节 |
| 潜在误读点 | ⚠️ “成功交付 → 进入已批准的后续责任阶段” 与 catalog 中大量 `pending_future_owner` 并存；需强调**目录登记 ≠ RC 已通过** |

---

### 7. 打包闭合（`package-manifest.json`）

- `schemas/acceptance-catalog.schema.json` **已列入** manifest schemas → `test_package_manifest.py` 通过。
- **`fixtures/acceptance/**` 未列入** manifest components**。
- 会议上下文将 manifest 列为“打包闭合”来源之一，但 acceptance catalog/fixtures **不在候选包清单中**。
- `worker_03_round2.md` 曾记录 schema 未入 manifest 的 blocker；当前 schema 已修复，**fixtures 仍未纳入**。

---

### 8. 最高影响缺陷与具体修复建议

#### 缺陷 A — 自证循环（最高优先级）
**问题：** 批准 18 族集合只存在于 `test_fixture_catalog.py` 常量；外部计划不可读；catalog 测试不执行 catalog verifier。  
**修复：**
1. 将批准 18 族清单以**只读摘录**落入仓库（例如 `fixtures/acceptance/required-v12/APPROVED_MANIFEST.json`，带来源 plan SHA）。
2. 测试从该 manifest 读取，而非硬编码 frozenset。
3. 新增 `test_catalog_verifier_targets_exist_and_are_importable`：遍历所有 `verifiers[].target`，断言文件与 pytest node 存在。

#### 缺陷 B — 悬空 verifier（阻断性）
**问题：** 4 个 case 指向不存在测试文件。  
**修复（二选一）：**
- **实现** 4 个缺失测试文件（即使先 RED stub + `pytest.skip` 也不应指向幽灵路径）；或
- **改写** catalog verifier 指向已存在测试，并在 catalog 注释中说明 Task 10.6/10.8 责任边界。

#### 缺陷 C — 验证链未绑定 catalog 输入
**问题：** `required-v12` 仅 `scenario.json`，verifier 跑的是无关 fixture 的 unit test。  
**修复（可分期）：** Task 10.2+ 增加 `fixture run --case <id>` 或 catalog-driven verifier runner；Task 10.1 至少在 matrix 与 catalog 中明确“当前 verifier 为**能力探针**，非 case 级 E2E”。

#### 缺陷 D — 打包未闭合
**修复：** 将 `fixtures/acceptance/catalog.yaml`、`fixtures/acceptance/full-matrix-v1/**`、`fixtures/acceptance/required-v12/**`、`docs/acceptance/matrix.md` 纳入 `package-manifest.json` components（或 ADR 说明为何仅源码仓保留）。

#### 缺陷 E — 任务状态不一致
**修复：** 完成上述 A/B 后，勾选 `implement.md`，将 `task.json` 置为 completed。

---

## Evidence And Assumptions

### 直接证据
- `fixtures/acceptance/catalog.yaml`：23 cases，`release_scope: site_html_v1`，`allowed_formats: [html]`
- `fixtures/acceptance/required-v12/catalog-fragment.yaml`：18 cases，与共享 catalog 内容一致
- `tests/acceptance/test_fixture_catalog.py`：35 passed；含 `_APPROVED_REQUIRED_V12_IDS`、owner/state 规则、子场景图
- `src/ci_workflow/application/acceptance_catalog.py`：确定性 `compute_case_digest`
- `docs/acceptance/matrix.md`：中文医学验收矩阵完整
- `docs/decisions/0013-site-first-v1-delivery-scope.md`：HTML-only 首版
- Python 脚本核查：4 个 verifier 文件缺失；23 个 receipt 文件缺失

### 推断
- 23 个 receipt 缺失在 Task 10.1 阶段**可能有意**（未来 owner 尚未执行），但 schema 仍要求 `receipt.relative_path` 存在，形成“路径已声明、文件未生成”的中间态。
- `expected.state=snapshot_locked` 表示**目标终态合同**，不是当前验收完成声明；与 `pending_future_owner` 并用是设计意图，但对人不透明。

### 假设
- 批准计划中的 18 族 ID 与当前仓库列表一致（**未能验证**）。
- 执行证据 `worker_02_round4.md` / `worker_03_round2.md` 仅作旁证，非权威。

---

## Risks, Gaps, And Verification Needs

| 风险 | 严重度 | 说明 |
|---|---|---|
| 自证循环 | **高** | 测试通过 ≠ 计划合规；未来改测试常量即可“通过” |
| 悬空 verifier | **高** | catalog 声明不可执行验证器，RC 冻结时可能发现无测试可跑 |
| 验证链断裂 | **中** | scenario.json 与 unit test fixture 无运行时绑定 |
| 打包缺口 | **中** | 安装包可能不含 acceptance catalog |
| 语义误读 | **中** | `snapshot_locked` + `pending_future_owner` 并存 |
| 外部 SoT 缺失 | **中** | 无法完成会议要求的“独立于测试的批准计划对照” |

### Codex 需裁定的边界问题

1. **批准计划不可读：** 是否提供 plan 摘录或 manifest 快照供仓库内独立对照？否则 18 族闭合只能信任实现者自述。
2. **Receipt 占位：** Task 10.1 是否允许 23 个 `docs/acceptance/receipts/**` 路径存在但文件缺失？若不允许，应生成 schema-valid 的 `pending` stub。
3. **Verifier 策略：** Task 10.1 是否要求 verifier **文件必须存在**？若要求是，当前 4 case 直接阻断收口。
4. **打包范围：** acceptance fixtures 是否必须进入 `package-manifest.json`？

### 建议 Codex 验收前再跑的命令

```bash
uv run pytest tests/acceptance/test_fixture_catalog.py -q
# 待修复后新增：
# uv run pytest tests/acceptance/test_catalog_verifier_targets.py -q
# 对每个 catalog verifier target 做存在性/可收集性检查
```

---

## Recommended Next Step

**结论：需修复后再由 Codex 最终验收。** 不建议以当前状态宣告 Task 10.1 完整闭合。

**最小修复包（建议 Codex 授权一轮编辑）：**

1. 落地 `APPROVED_MANIFEST`（或等价 plan 摘录）并让测试读取，打破 18 族自证循环。
2. 补齐或改正 4 个悬空 verifier 目标；新增 verifier 目标存在性测试。
3. 决定 receipt 策略：生成 `pending` stub 或 schema 放宽 + 文档说明。
4. 将 `fixtures/acceptance/**` 与 `docs/acceptance/matrix.md` 纳入 `package-manifest.json`（若首版候选包需要携带验收目录）。
5. 更新 `implement.md` / `task.json` 状态。

**可保留的优点（不必回滚）：**
- ADR 0013 HTML-only 收窄执行到位
- 23-case / 18 族仓库内双向闭合
- SHA-256 / case_digest 可重算
- `recovery-rehearsal` / `legacy-absence` 未提前关闭
- `docs/acceptance/matrix.md` 中文医学说明质量高

**安全暂定路径（若 Codex 暂不授权编辑）：** 可将 Task 10.1 记为 **“目录合同已建立，验证器与打包闭合待补”**，明确禁止任何下游任务（10.2/10.6/RC）把 `35 passed` 解释为 RC 验收已通过。
