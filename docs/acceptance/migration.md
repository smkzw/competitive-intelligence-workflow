# 旧工程迁移清单验收说明

## 结论边界

Task 10.4 只完成“保留什么、拒绝迁移什么、如何验证”的清单闭环。它没有执行真实旧根盘点、切换、删除或最终发布接受：精准 cutover 工具及临时根验证属于 Task 10.5，真实旧工程无残留验证属于 Task 10.8。

## 已批准保留

清单的 `migrated` 集合是封闭白名单：

- 批准的竞品调研工作流 v1.2 规格；
- D01–D70 原始决策台账，逐字节归档到非运行目录；
- 项目内化后的康哲核心设计合同和首版站点合同；
- 经官网来源与摘要核验的康哲 Logo；
- 四个从旧失败产物裁剪、脱敏的最小负向 fixture；
- 基于这些失败证据重写的六类确定性回归断言。

康哲 `design_share_v2.md` 与 `design_v2.md` 已退化为相同兼容入口，不是两份完整权威正文；二者明确登记为 `not_migrated`。当前权威只来自项目自有 `contracts/kangzhe/`，运行时不读取上游模板目录。

## 明确不迁移

以下类别都必须存在 `not_migrated` 记录，且没有新路径：旧可运行代码、旧 schema、旧模板、旧 QC 与运行截图、旧 PRD/设计/交接等顶层文档、旧全局事实库与任务输出、旧全局 Skill、浏览器会话、过程导出、测试缓存、明文凭据或认证状态、本机绝对路径绑定和兼容包装器。

旧根的《提问与决策记录》和《数据采集策略审计与重构计划》有意只由 `legacy-top-level-documents` 集合项覆盖，不作为单独批准来源迁移。

敏感类别不读取内容，也不保存逐文件摘要。其 SHA-256 是固定排除声明的哨兵摘要，只证明本清单的处置语义，不代表凭据内容摘要。旧根的浏览器状态、会话令牌目录、认证状态文件，以及一份含明文认证信息的旧交接文档均已按载体类别登记；本文和清单不再现任何凭据值。旧事实库同样不进入新事实层；新系统的事实必须重新经过来源版本、定位、证据片段和科学门。

敏感哨兵按 UTF-8 标记原文直接计算 SHA-256，测试固定原文与结果：会话/缓存使用 `legacy-sensitive-session-and-cache-content-not-read-v1`，明文凭据载体使用 `legacy-sensitive-config-content-not-read-v1`。这些标记不包含任何凭据内容；把真实文件摘要标成哨兵会因精确值不匹配而失败。

其余四个非敏感 `redacted_sentinel` 集合项只是 Task 10.4 的一次性处置声明，不是来源内容摘要，也不提供可复算的来源完整性证明；Task 10.5 必须重新盘点，不能把这些值当作 apply 授权依据。

## 摘要与转换如何解释

- `file_bytes`：来源单文件的字节摘要。
- `collection_manifest`：按相对路径和逐文件摘要排序后形成的集合摘要。
- `source_set`：多个已批准来源摘要组成的集合摘要。
- `redacted_sentinel`：不读取敏感内容时，对固定排除声明计算的摘要。

`verbatim_copy` 要求来源与目标摘要一致；`project_internalization` 允许有记录的项目化修订，并分别保存来源和目标摘要；`deidentified_excerpt` 只保留复现旧缺陷所需的最小字段；`rewritten_assertion` 表示从失败证据重写确定性测试，而非复用旧测试实现。

康哲核心合同的 `source_sha256` 绑定 Task 10.4 对 `old_path` 的当前只读观察，并由 ADR 0002 的候选摘要记录交叉核对；`target_sha256` 绑定项目内化后的当前文件。`contracts/kangzhe/manifest.json` 是内化时冻结的项目来源映射，不用于宣称上游目录会继续同步。

## 机械验收

运行：

```bash
uv run pytest tests/migration/test_manifest_closure.py tests/migration/test_legacy_manifest_contract.py tests/migration/test_no_legacy_runtime_dependency.py -q
uv run python tools/check_no_legacy_refs.py --root .
```

Task 10.4 收口时的 59 项组合回归命令为：

```bash
uv run pytest tests/migration/test_manifest_closure.py tests/migration/test_legacy_manifest_contract.py tests/migration/test_no_legacy_runtime_dependency.py tests/contract/test_approved_spec_hash.py tests/contract/test_design_contract_hashes.py tests/acceptance/test_legacy_negative_regressions.py tests/acceptance/test_fixture_catalog.py -q
```

测试会拒绝未知字段、重复 ID、白名单扩张、缺少必需排除类别、目标越界或符号链接、目标摘要漂移、排除项出现新路径、敏感类别使用文件摘要，以及任何旧根运行依赖。

## 尚未发生

- 没有运行 Task 10.5 的真实旧根 inventory 或 apply。
- 没有删除、移动或修改旧根、旧全局 Skill、缓存或凭据文件。
- 没有冻结 RC，也没有关闭 `legacy-absence` release case。
- 后续执行真实切换前，仍须匹配授权清单摘要、恢复演练和独立验收；发现范围漂移必须停止，而不是扩大处置路径。
