REVISE

P0=0；P1=4；P2=0。

1. P1：科学摘要遗漏 `SourceVersionRecord`

符号：[lineage_registry.py:180](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/lineage_registry.py:180>) `compute_scientific_content_digest`。

- 构造：保留片段 ID、locator、原文、事实和 manifest 不变，仅用 `model_copy` 修改 `source_version.content_sha256/content_relative_path` 或 `acquired_at`。
- 实际：`build_product_overview_view(...)` 接受并生成 5 个产品。
- 预期：当前锁定快照应拒绝来源版本内容/审计字段变化。
- 未捕获原因：现有摘要只序列化片段字段和 `source_version_id`，未序列化整个 `source_version`。
- 最小修复：摘要中纳入完整 `VerifiedEvidenceFragment`（至少完整 `fragment`、`source_version`、`reopened_original_text`）规范序列化，并新增来源版本字段篡改回归测试。

2. P1：项目合同权威存储可被整体替换

符号：[pages.py:291](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:291>) `AEvidenceContext`；[pages.py:311](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:311>) `_assert_evidence_context_bound`。

- 构造：新建临时 `SnapshotStore` 和 `ProjectContractStore`，写入自洽的合同 `version=999/data_cutoff=2099-01-01`，同步替换 manifest、locked snapshot、context contract/store，并更新 universe snapshot 的 `evidence_snapshot_id`。
- 实际：产品总览接受，输出 `contract=999`。
- 预期：攻击者提供的新合同根和持久化内容不能冒充当前权威合同。
- 未捕获原因：既有 future-context 测试保留了原始 `evidence.contract_store`，未替换权威合同存储。
- 最小修复：从可信应用边界额外注入不可由 `AEvidenceContext.model_copy` 替换的 authoritative contract handle/store；校验必须使用该独立对象，并拒绝 context store 身份不一致。此项不能延后，因为影响全部 8 个页面及 authoritative 入口。

3. P1：结果绑定未闭合产品/试验/来源血统

符号：[pages.py:540](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:540>) `_assert_result_binding_matches_fact`；[pages.py:1988](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1988>) 结果摘要循环。

- 构造 A：给 `p-clinical` 用 `model_copy` 增加锚定试验；复制 `b-eff/b-saf`，改 `object_id="p-clinical"`、`trial_id="NCT-clin-1"`，但仍引用 `project-dupilumab` 的 `fact-v-1/fact-v-2`。
- 实际：档案接受，`p-clinical.result_bearing=True`，并显示度普利尤单抗的疗效/安全结果。
- 构造 B：仅将 `b-eff.source_location` 改为伪造定位、`source_role` 改为 `COMPANY_DISCLOSURE`。
- 实际：档案仍接受。
- 预期：事实实体、主片段定位、来源角色应与绑定和当前产品/试验一致。
- 未捕获原因：当前只检查 fact ID 已注册及数值、单位、分母、人群、时间点、组别；未检查 `fact.entity_id`、fragment locator、fact/binding source role。
- 最小修复：在重验证边界按当前宇宙解析 binding scope，强制结果事实实体与产品/试验一致，并校验 binding locator/source role/review/disclosure 与事实及主片段一致。

4. P1：同一结果事实可重复渲染

符号：[pages.py:1988](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1988>)。

- 构造：复制 `b-eff`，仅改 `binding_id="b-eff-duplicate"`，保留同一 `fact_version_id="fact-v-1"`，调用 `build_product_dossier_view`。
- 实际：接受；疗效记录 ID 为 `['fact-v-1', 'fact-v-1']`。
- 预期：同一事实版本重复消费应失败关闭。
- 未捕获原因：现有测试覆盖字段错配，未覆盖重复结果绑定；`ProductDossier` 也没有结果事实唯一性校验。
- 最小修复：构建疗效/安全摘要时按产品和结果域维护 `fact_version_id` 集合，重复即拒绝；同时校验 binding ID 唯一。

已实际验证并通过的关键攻击：

- 8 个 build + 8 个 authoritative 入口在 `report_ready=False` 下全部拒绝。
- locked 的 sha/path/byte_size/snapshot_id、manifest 合同版本/截止日、context 合同版本/截止日篡改均拒绝。
- 错摘要、缺摘要、旧快照存储字节篡改均拒绝。
- AV04–AV08 同步篡改事实/片段/摘要、漏传、重复记录均拒绝。
- 结果 numeric、unit、denominator、population、timepoint/window、arm/cohort 错配均拒绝。
- AV04–AV08 全部 `model_construct` DTO 和嵌套双态 `EvidenceField` 攻击均拒绝。
- EARLY_DECISION→OTHER_ELIGIBLE、缺角色证据、事件复用事实、事件类型冲突、历史状态冲突均拒绝。
- 全角日期、非零填充日期规范化通过；非法日期拒绝；中文标点保真；指定工程词拒绝，医学英文和 `aggregate` 通过。

命令结果：

- round4 精确测试：38 passed
- `tests/unit/reports/a`：204 passed
- A 类联合测试：295 passed
- 合同存储测试：5 passed
- 快照身份测试：1 passed
- Ruff：All checks passed
- strict mypy：8 source files，无问题

全程只读；临时文件均位于系统临时目录并自动清理，未写入 runner 报告路径。