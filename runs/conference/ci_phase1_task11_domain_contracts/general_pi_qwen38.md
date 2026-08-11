所有证据已收集完毕。让我来编写完整的会议输出。

---

# 会议参与者输出：ci_phase1_task11_domain_contracts - general_pi_qwen38

## 边界检查

- **会议角色**：`general_pi_qwen38`，提供商/模型分配为 `pi` / `cms-smk` / `cms-model`（日间 CMS 路由替代了北京窗口外的 Qwen Max 节点）。已接受该有效路由；未尝试切换提供商。
- **范围**：只读代码与合同验收。未修改任何项目文件。未读取其他参与者输出。未写入运行程序管理的报告路径。
- **已读取初始读取集**：`AGENTS.md`、会议上下文、源数据包、主会场计划。外加完整的源数据包：`ids.py`、`enums.py`、`contracts.py`、`project-contract.schema.json`、三个测试文件、`package-manifest.json`、ADR 0004，以及设计规范 §3.1/§8.4/§10.2。
- **已执行锚点**：3 个 Task 1.1 测试文件通过（4 个通过）；完整套件 73 个通过；`ruff` 清洁；`mypy` 严格清洁（3 个领域模块）；`package verify --root .` → `PACKAGE_OK`。所有锚点均已独立复现。
- **无生产路径**被读取或修改。Codex 保留最终验收权。

## 独立工作成果

我独立运行了 57 个对抗性边界探针，覆盖了所有六项审查目标。**54 个通过，3 个失败**。调查后，1 个失败是真正的代码发现，2 个是探针脚本比较错误（将 `OutputFormat` 枚举成员与字符串字面量进行比较——Python `Enum` 与其值不相等；实际实现是正确的）。

### 目标 1 — 稳定 ID (`ids.py`)

**已验证不变量**（通过探针）：
- 确定性：相同输入 → 相同 ID；不同种类或不同身份部分 → 不同 ID。
- NFKC 折叠：全角 `ＡＢＣ` == ASCII `ABC`。内部空白折叠；前导/尾随空白被去除。
- 种类通过 `casefold()` 进行大小写折叠（`Product` == `PRODUCT` 命名空间）。连字符种类有效；拒绝以数字开头的种类；拒绝空种类。
- `\x1f` 单元分隔符防止了邻接碰撞：`("ab","c")` ≠ `("a","bc")`。部分顺序很重要（无静默排序）。
- 空字符串和仅包含空白字符的部分被拒绝；拒绝无部分的情况。

**发现 VETO-1（P1，潜在合并缺陷）**：
- **文件/函数**：`src/ci_workflow/domain/ids.py`，`stable_id` / `_normalize_identity_part`。
- **可复现输入**：`stable_id("product", None)` → 返回 `product_9a0752ce9163e6c3ff5de65a` 而不是引发异常。此外 `stable_id("product", 0)` 和 `stable_id("product", False)` 也会产生 ID。
- **后果**：签名声明为 `*identity_parts: object`。`_normalize_identity_part` 在任何类型检查之前调用 `str(value)`，因此 `None`→`"None"`、`0`→`"0"`、`False`→`"False"`。空值防护 (`if any(not part ...)`) 仅捕获空字符串；这些非空的 `str()` 结果绕过了它。**冲突是真实的**：`stable_id("product", None) == stable_id("product", "None")` → `True`。如果未来的调用者错误地传递了缺失的字段值（`None`），它将静默生成一个与字面身份字符串 `"None"` 无法区分的稳定 ID，而不是快速失败 —— 这正是 ADR 所说的必须防止的“将不同临床对象合并”的类别。目前未触发（唯一调用者 `create_project_contract` 总是传递字符串），因此这是潜在缺陷，而非当前数据损坏。
- **最小修复**：在 `_normalize_identity_part` 中，在进行 `str()` 转换之前拒绝非字符串、非日期/日期时间输入，或者在 `stable_id` 中添加显式防护：`if not isinstance(part, (str, date, datetime)): raise ValueError(...)`。另外，缩小类型提示：`*identity_parts: str | date | datetime`。

### 目标 2 — 九个状态族 (`enums.py`)

**已验证**：所有九个族均存在，且成员与规范 §8.4 + §10.2 完全匹配：
- `RouteAttemptResult` (12), `RouteCompletion` (3), `FactDisclosureState` (8), `FactReviewState` (4), `ProjectRunState` (6), `ReportEvidenceState` (8), `FormatArtifactState` (7), `DownloadRequestState` (6), `RevisionApprovalState` (6)。
- 跨族不相等：`ProjectRunState.AWAITING_USER != ReportEvidenceState.AWAITING_USER` (不同的类，通过身份永远不相等)。
- `""`、`0`、`None` 无法构造 `FactDisclosureState` (引发 `ValueError`)。
- **路由失败值不泄漏到披露中**：共享值 `"not_publicly_disclosed"` 同时存在于 `RouteAttemptResult` 和 `FactDisclosureState` 中 —— 这符合规范（两者都列出它），并且基于值的查找正确解析为各自族内的成员，没有交叉污染。路由失败值（`transient_network_failure`、`rate_limited`、`access_or_permission_blocked`）与披露值不相交。未发现缺陷。

### 目标 3 — 合同强制执行 (`contracts.py`)

**已验证**：
- A/B/C 多选强制执行；拒绝重复；拒绝空报告；拒绝无效报告种类 `D`。
- HTML 默认值：`outputs=[]` → `(HTML,)`；`outputs=["pdf"]` → `(HTML, PDF)`；`outputs=["pdf","html"]` → `(HTML, PDF)` (HTML 移至前面，无重复)。拒绝重复输出。
- IANA 时区强制执行（`ZoneInfo("Shanghai")` → `ValueError`）。
- 带有偏移量的日期时间：`_datetimes_have_offsets` 拒绝单纯/无偏移量的日期时间。
- 空白指示被拒绝；指示被内部折叠规范化。
- `frozen=True` + `extra="forbid"`：变异和额外字段均被拒绝。

### 目标 4 — 截止日期固化、恢复、刷新 (`contracts.py`)

**已验证**：
- 默认截止日期 = 声明时区中创建日期的 `time.max` (23:59:59.999999)，带有正确的 UTC 偏移量。`cutoff_was_user_supplied=False`。
- 显式日期截止日期在声明时区中物化为当日结束时间（已验证 `America/New_York` 2024-02-29 → `-05:00` EST；已验证 2026-03-08 春令时过渡 → `-04:00` EDT；已验证 `Asia/Shanghai` 冬季 → `+08:00` 无夏令时）。
- 单纯日期时间截止日期 → 本地化为声明时区，提取日期。
- 带偏移量日期时间截止日期 → 转换为声明时区，提取日期（`2026-08-10T23:00 UTC` → 上海日期 08-11 → 物化为 08-11 结束）。语义一致：截止日期是声明时区中的日期级边界。
- 未来截止日期（日期 > 创建日期）被拒绝。
- **恢复无漂移**：`resume_project_contract` 返回相同的对象 (`is contract`)；版本和截止日期未变。拒绝单纯 `resumed_at`；接受 `None` `resumed_at`。跨天恢复（在 08-12 恢复 08-11 合同）使 08-11 截止日期保持不变。✓
- **刷新创建新版本**：`contract_version + 1`，相同的 `project_id`，新的截止日期，原始合同未更改（版本和截止日期均已验证未变）。`cutoff_was_user_supplied=True`。拒绝 `cutoff ≤ current`；拒绝 `cutoff > created_at.date()`；拒绝单纯 `created_at`。✓

### 目标 5 — Schema 同构

**已验证**：`project-contract.schema.json` 在 `package-manifest.json` 中注册。Schema 是有效的 Draft 2020-12。Pydantic 转储（默认和刷新）针对 Schema 进行验证。Schema 拒绝缺少 HTML 的输出。`project_id` 模式 `^project_[0-9a-f]{24}$` 与 `stable_id` 输出匹配。

**发现 OBSERVATION-1（P2，Schema 弱于 Pydantic，测试不足）**：
- **文件**：`schemas/project-contract.schema.json` + `tests/contract/test_project_contract.py:48-49`。
- **可复现输入**：`{"timezone": "Not/A/Real/Zone", "data_cutoff": "2026-08-11T23:59:59", "created_at": "2026-08-11T09:30:00", ...}` 针对 Schema 验证 → **0 错误**。
- **后果**：Schema 比 Pydantic 合同弱。Schema 仅检查 `timezone: {minLength: 1}`（无 IANA 验证），且 `data_cutoff`/`created_at` 仅使用 `format: "date-time"` —— 但测试从不附加 `FormatChecker`（`Draft202012Validator(schema)` 默认为 `format_checker=None`），因此格式注释是无效的。无偏移量的日期时间通过 Schema，而 Pydantic 拒绝它们。这意味着 Schema 和 Pydantic 合同**不同构**：外部消费者（非 Python）仅依赖 Schema 将接受 Pydantic 会拒绝的无效合同。“Schema 同构”成功标准仅通过测试有效输入进行了微弱验证。
- **最小修复**：(a) 在测试中添加 `format_checker=draft202012.Draft202012Validator.FORMAT_CHECKER` 并断言无偏移量的日期时间和无效时区**失败**；(b) 可选地加强 Schema —— 为 `timezone` 添加 `pattern`，或使用 `{"type": "string"}` 加自定义格式校验器 —— 尽管 JSON Schema 无法完全验证 IANA，但测试应证明不对称性。这不是否决，因为 Pydantic 合同是运行时执行路径，且 Schema 仅用于外部可发现性；但它必须被记录为同构性缺口。

### 目标 6 — 测试充分性

现有的 4 个测试是真实的契约测试（不是占位符）。覆盖的缺口：
- `test_ids.py`：确定性、命名空间、非空、正则表达式格式。**未覆盖**：`None`/`0`/`False` 输入拒绝（VETO-1 缺口），NFKC 折叠，邻接分隔符，部分顺序。
- `test_state_enums.py`：所有九个族，跨族不相等，`FactDisclosureState` 上拒绝 `""`/`0`/`None`。**覆盖良好**。
- `test_project_contract.py`：版本、时区、历史截止日期、默认截止日期固化、恢复不漂移、刷新新版本、刷新不晚于防护。**未覆盖**：Schema 拒绝无效输入（OBSERVATION-1），DST 偏移量正确性，带偏移量日期时间截止日期转换，冻结变异，额外字段拒绝。

## 证据与假设

**证据（直接观察）**：
- 测试执行：`.venv/bin/python` (Python 3.13.13, pydantic 2.13.4), pytest 9.1.1 → 4 个通过 (Task 1.1), 73 个通过 (完整套件)。
- 探针执行：57 个断言，54 个通过 / 3 个失败 → 1 个真实发现 (VETO-1)，2 个探针错误。
- `ruff check` → 清洁；`mypy` (严格) → 3 个文件无问题；`package verify --root .` → `PACKAGE_OK`。
- `stable_id("product", None)` 返回 `product_9a0752ce9163e6c3ff5de65a`；`== stable_id("product", "None")` → `True` (通过实时执行确认)。
- Schema 在无效 IANA 时区和无偏移量日期时间上 → `iter_errors` 产生 0 个错误 (通过实时执行确认)。

**假设**：
- [推理] ADR/规范未明确要求 `stable_id` 拒绝非字符串类型；ADR 称“规范化身份材料”，源数据包 Q1 询问关于“合并不同临床对象”的问题。我将 `None`→`"None"` 冲突归类为 P1（潜在缺陷），而非 P0，因为唯一调用者仅传递字符串。如果 Codex 认为该函数是一个必须拒绝所有非身份输入的公共稳定 ID API，请将其升级为 VETO。
- [推理] Schema 同构缺口 (OBSERVATION-1) 不是否决，因为 Pydantic 合同是科学状态的运行时强制执行者，且 Schema 是外部发现的补充。如果 Codex 的“Schema 同构”标准要求对对抗性输入进行 1:1 对等，则这是一个否决条件的测试充分性缺口。

## 风险、缺口与验证需求

1. **VETO-1 (P1, `stable_id` `None`/`0`/`False` 合并)** — 潜在身份合并缺陷。目前未触发，但函数签名 `object` 静默接受非身份类型并生成与字面字符串无法区分的 ID。**建议修复**：添加 `isinstance` 防护，缩小类型提示。**否决阈值判断**：这是“将不同临床对象合并”吗？仅当未来的调用者传递 `None` 时才是 —— 可能但非当前。我倾向于**有条件通过**：在合并前要求修复，但由于它不在当前的执行路径上，不属于阻塞发布的问题。

2. **OBSERVATION-1 (P2, Schema 弱于 Pydantic)** — JSON Schema 接受 Pydantic 拒绝的无效时区和无偏移量日期时间；测试未证明对称拒绝。**建议修复**：添加带有 `FormatChecker` 的对抗性 Schema 测试，断言无效输入失败。

3. **测试充分性缺口** — 现有测试未覆盖：NFKC 折叠，邻接分隔符不变量，DST 偏移量正确性 (EDT vs EST)，带偏移量日期时间截止日期跨时区转换，冻结变异拒绝，额外字段拒绝。全部已通过探针验证为正确 —— 它们只是缺乏回归覆盖。

4. **无 P0 科学状态混合或历史快照漂移缺陷发现**。核心不变量 —— 恢复返回相同对象，刷新创建新版本且原始版本未变，截止日期在创建时固化且从不重算 —— 均已通过对抗性执行验证。

## 推荐下一步

**结论：通过（附带条件）**

Task 1.1 实现满足所有六项审查目标中的核心科学状态不变量。九个状态族与规范完全匹配且无跨族污染。合同强制执行 A/B/C 多选、HTML 默认值、IANA 时区、带偏移量日期时间，以及创建时固化截止日期。恢复零漂移；刷新仅创建新版本。Schema 已注册且 Pydantic 转储有效。

**通过前/合并前的条件**（非阻塞验收，但必须在 Task 1.2 之前解决）：
1. **修复 VETO-1**：在 `stable_id` / `_normalize_identity_part` 中添加类型防护，拒绝 `None`/`0`/`False`/非字符串输入。缩小 `*identity_parts` 类型提示。添加回归测试。预计 5 行代码。
2. **修复 OBSERVATION-1**：在 `test_project_contract.py` 中添加对抗性 Schema 测试，对无效时区和无偏移量日期时间断言 `iter_errors` 非空（需要 `FormatChecker`）。预计 10 行代码。

**给 Codex 的有限问题**：`stable_id` 是否旨在作为一个必须拒绝所有非身份输入的公共稳定 ID API，还是一个仅由 `create_project_contract` 使用的内部辅助函数？如果前者 → VETO-1 升级为阻塞否决；如果后者 → 通过后的条件。安全临时路径：接受为通过后的条件，因为唯一调用者仅传递字符串，且该缺陷是潜在的而非当前的。

我没有否决核心科学状态不变量 —— 实现)))
