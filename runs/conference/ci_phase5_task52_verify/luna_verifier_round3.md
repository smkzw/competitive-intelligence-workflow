Verdict: REVISE

P0：0

P1：

1. 注册表内容未真正绑定锁定快照

- 符号：[pages.py:496](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:496>)、[pages.py:313](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:313>)。
- 构造：同时篡改 `fact-org-origin.raw_value="原研 伪造企业"` 与主片段 `original_text`，重算 `content_sha256`，保留全部 ID/locator。
- 实际：`build_company_deal_view` 接受 `CompanyDealView`；AV04、AV05、AV07、AV08 同样可接受同步伪造值。
- 预期：必须因注册表内容不属于锁定快照而拒绝。
- 未捕获原因：现有校验只比较 ID 和片段摘要；重验证结果未替换后续使用的 `evidence.registry`，且 manifest 不含注册表内容摘要。
- 修复：从权威仓储按快照重载注册表，或把注册表内容摘要纳入锁定快照并逐项比对；后续统一使用重验证后的注册表。

2. 合同版本/截止日可在同一边界内自洽伪造

- 符号：[AEvidenceContext](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:244>)、[pages.py:263](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:263>)。
- 构造：将 manifest 和 `project_contract` 同时改为 `contract_version=999`、`data_cutoff=2099-01-01`，用新的 `SnapshotStore._lock()` 写入匹配载荷，并把 snapshot ID 更新为新值。
- 实际：`build_product_overview_view` 接受 `ProductOverviewView`。
- 预期：必须拒绝未来/伪造的当前合同。
- 未捕获原因：调用边界没有独立的当前权威 `ProjectContract`；校验只是 manifest、contract、store 之间的内部一致性。
- 修复：builder 接收独立的当前合同或不可伪造的权威上下文，并绑定版本、截止日及存储身份。该问题不宜延后。

3. 疗效/安全分母未绑定原子事实

- 符号：[pages.py:1809](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1809>)、`_dossier_efficacy_record`、`_dossier_safety_record`。
- 构造：将原子事实分母设为 `224`，同时 `b-eff`、`b-saf` 的 `denominator` 改为 `999`。
- 实际：档案接受，输出分母均为 `999`。
- 预期：必须拒绝数值、单位、分子/分母与事实不一致的摘要。
- 未捕获原因：当前仅比较 `numeric_value + unit`，输出直接消费绑定对象的分母；现有测试只覆盖数值和单位。
- 修复：比较并绑定 numerator、denominator、unit、normalized_unit 等全部结果字段，或只从权威事实推导摘要。

4. 扩展记录未重新验证，`model_copy` 可绕过 AV04 字段边界

- 符号：[pages.py:451](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:451>)、`_assert_trial_region_records_closed`、`build_clinical_portfolio_view`。
- 构造：用真实一致的 `clinical_trial_region` 事实“III期 已完成 美国”，再对合法记录执行 `model_copy(update={"region": "美国"})`。
- 实际：临床组合接受并输出“美国”。
- 另一个构造：将 `phase` 的 `EvidenceField` 用 `model_copy` 改成同时含 value 和 `NOT_YET_DISCLOSED` state；实际仍输出原 value。
- 预期：必须拒绝非法地域及互斥状态同时存在的 DTO。
- 未捕获原因：builder 只重新验证项目、快照、绑定和结果标记，不重新验证 AV04–AV08 扩展记录及嵌套 `EvidenceField`；输出行只检查用户文本。
- 修复：所有扩展记录先 `model_validate(model_dump(...))`，并使用返回对象；临床组合再次强制地域闭合集合。

P2：

5. NFKC 等价日期被误拒绝

- 符号：[pages.py:2478](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:2478>)。
- 构造：将 `2020-06-19` 改为全角等价形式 `２０２０-０６-１９`。
- 实际：因与合同日期字符串不完全相等而拒绝。
- 预期：日期比较前应规范化为同一标准日期。
- 未捕获原因：现有测试未覆盖 Unicode 等价日期。
- 修复：日期模型边界统一 NFKC/ISO 解析后比较。

6. 中文标点被 NFKC 改成不自然的 ASCII 标点

- 符号：[_user_facing_text](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:206>)。
- 构造：输入 `靶点与目标适应症机制相关，适应症关系未确立，独立观察`。
- 实际：展示值变为 `靶点与目标适应症机制相关,适应症关系未确立,独立观察`。
- 预期：保留自然中文标点；NFKC 应只用于安全比较，不应直接改写展示文本。
- 未捕获原因：现有测试使用 ASCII 逗号，未检查中文展示保真。
- 修复：分离“比较规范化”和“展示规范化”，保留中文标点。

验证结果：

- `tests/unit/reports/a`：166 passed
- `tests/reports/a tests/unit/reports/a`：257 passed
- Ruff：通过
- strict mypy：通过
- `report_ready=False`：8 个 builder、8 个 authoritative 入口均拒绝
- 监管事件重复 ID、事实复用、类型/地域冲突：均拒绝
- 四类历史状态均保留；空企业/专利/历史模块合法生成
- `RegistryResultsPostedEvidence` 的 `model_copy/model_construct` 伪造：均拒绝
- 快照正向一致性：`compute_locked_snapshot == _lock == store.read` 均为 `True`
- 工程词变体均拒绝，医学英文和 `aggregate` 均通过

上述 P1/P2 仍存在，因此不能 PASS。