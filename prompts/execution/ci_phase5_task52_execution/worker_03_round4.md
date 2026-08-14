# 第 5.2 步同会话修复第 4 轮

继续原 worker_03 会话。Luna 第 3 轮独立复核仍为 `REVISE`，完整报告在：
`runs/conference/ci_phase5_task52_verify/luna_verifier_round3.md`。

## Hard boundaries

- 仅在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 内工作，不提交 Git。
- 不进入模板、HTML、PDF、PPT、浏览器和安全测试；不改无关文件。
- Runner 管理唯一输出文件 `runs/execution/ci_phase5_task52_execution/worker_03_round4.md`，Agent 不得自行写入该文件，只在最终回复返回完整交接。
- Read these files only as the initial mandatory set: `AGENTS.md`、`runs/conference/ci_phase5_task52_verify/luna_verifier_round3.md`、当前第 5.2 源码与测试；仅在修复依赖确有需要时沿调用链读取相邻文件，并在交接中说明。

Read these files only:
- `AGENTS.md`
- `runs/conference/ci_phase5_task52_verify/luna_verifier_round3.md`
- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/reports/a/contracts.py`
- `src/ci_workflow/storage/snapshot_store.py`
- `tests/unit/reports/a/`

Exact writable files:
- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/reports/a/contracts.py`
- `src/ci_workflow/reports/a/__init__.py`
- `src/ci_workflow/storage/snapshot_store.py`
- 为当前项目合同权威只读存储所必需的相邻 `src/ci_workflow/` 文件
- `tests/unit/reports/a/`
- 与 manifest、snapshot、当前合同存储直接对应的测试文件

Runner-managed report path: `runs/execution/ci_phase5_task52_execution/worker_03_round4.md`.

请直接修复当前工作树，不提交 Git。先把报告中的每个反例转成精确回归测试并确认旧实现 RED，再做最小架构修复。不得通过修改测试期望、弱化失败关闭、扩大字符串黑名单或在测试工厂里预先规避攻击来获得绿色。

## P1-1 锁定快照必须绑定证据注册表内容

- 当前 manifest 只绑定 source/fragment/fact ID，不足以证明注册表内容属于锁定快照。为锁定清单增加稳定、确定性的科学证据内容摘要，至少覆盖每条已验证片段与每条已接受事实的规范序列化内容；排序必须稳定，摘要计算必须有一个公共实现，写入和验证共用。
- 每次公共构建入口从 `model_dump` 重新验证 registry、片段、事实，并真正使用返回的重验证对象；重算内容摘要并与锁定 manifest 比较。同步改写 `AtomicFactVersion.raw_value`、主片段 `original_text`、重算 fragment `content_sha256`、保留全部 ID/locator 的攻击必须拒绝。
- 兼容已存在的真实快照生成路径：所有 manifest 构造点与 schema/contract tests 必须同步更新；缺少内容摘要的权威视图输入失败关闭，不得静默补算为可信。
- 回归至少覆盖 AV04、AV05、AV06、AV07、AV08 各一条同步伪造，以及正向 `_lock == compute_locked_snapshot == store.read`。

## P1-2 当前项目合同必须来自独立权威边界

- `AEvidenceContext` 内部的合同、manifest、store 彼此自洽仍不足以证明它们是当前项目合同。调用边界必须携带或读取一个独立的、只读的当前合同权威来源；构建器用该来源重载当前 `ProjectContract`，再校验 project_id、contract_version、data_cutoff。
- 优先复用现有项目存储/数据库服务；若当前工程确无可复用读取器，增加一个最小、明确的只读 `ProjectContractStore/Repository`，其内容持久化、内容寻址或版本化，并由测试真实写入后重读。不能只是多传一个可随意 `model_copy` 的合同对象。
- 同时把 context 中合同、manifest、锁定快照、新 SnapshotStore 全部改成 version 999 / cutoff 2099 并自洽重锁，仍必须因权威当前合同不匹配而拒绝。正向当前合同需通过；resume/重复读取不能漂移。

## P1-3 疗效/安全摘要必须完整绑定原子事实

- 不得只比较 `numeric_value + unit`。对结果型 binding 与当前已接受 `AtomicFactVersion` 比较所有已有强类型对应字段，至少包括 normalized/raw numeric value、unit/normalized_unit、numerator、denominator、arm/cohort、population、timepoint/time window；缺少需要支撑的事实字段时失败关闭。
- 页面摘要优先从权威事实推导，或在校验完全一致后才消费 binding。
- 原子事实 denominator=224、binding denominator=999 的疗效和安全性反例必须拒绝；再补 numerator、unit、normalized_unit、population/timepoint 等逐字段错配攻击。正向夹具需真实填齐对应事实字段，不得只在测试中绕过。

## P1-4 AV04–AV08 所有扩展 DTO 重新验证

- 所有公共构建入口收到的扩展记录及其嵌套 `EvidenceField` 均先执行 `Type.model_validate(record.model_dump(mode="python"))`，后续只使用返回对象。
- 覆盖 AV04–AV08 每一种扩展记录类型的 `model_copy/model_construct` 绕过。至少确认 AV04 `region="美国"` 被拒绝；`EvidenceField` 同时含 value 和 state 被拒绝；输出临床地域再次限定为“中国/境外”。
- 任何非法扩展记录不得通过“事实原文也同步改写”绕过类型边界。

## P2 中文原生显示与日期等价

- 分离比较规范化与显示规范化。工程词检测可使用 NFKC/去零宽后的比较串，但用户可见中文必须保留自然全角标点，不得把 `，` 显示成 `,`。
- 监管日期在模型边界统一做 NFKC 后按 ISO 日期解析并规范输出；全角等价 `２０２０-０６-１９` 与 `2020-06-19` 比较一致。非法日期仍拒绝。
- 正反测试都要覆盖，不得削弱工程词变体拦截。

## 范围与验证

允许修改第 5.2 当前文件、证据快照 schema/存储、权威项目合同只读存储及其精确测试。不得进入模板、HTML、PDF、PPT、浏览器或安全测试。

依次运行并报告：

1. 本轮新增攻击测试（先 RED 后 GREEN 的精确结果）。
2. `uv run pytest tests/unit/reports/a -q`
3. `uv run pytest tests/reports/a tests/unit/reports/a -q`
4. 共享 gate/no-draft/A 回归组合。
5. 所有受影响的 snapshot/contract/project-store 测试。
6. 目标 Ruff。
7. `uv run mypy --strict src`
8. 非浏览器、非 acceptance 的全库测试。

不要自行宣告验收，不提交。交接必须逐项说明修复机制、攻击测试 RED/GREEN、变更文件、完整命令与精确结果，并明确任何残余问题。

Output file: `runs/execution/ci_phase5_task52_execution/worker_03_round4.md`
