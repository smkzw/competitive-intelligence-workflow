# R0 受控重基线、恢复与质量门记录

## 1. 结论与适用范围

本记录只覆盖当前新工程的 R0 受控重基线。它不批准产品发布，也不把历史脏树、旧格式代码或一次测试结果解释为 `RC_FROZEN`。

R0 的有效结论是：

- 用户现有脏树未被 reset、checkout、clean、批量暂存或推测性提交；
- 当前工程具备可复验的完整恢复快照机制；
- Ruff、`src + tools` strict-mypy、unit/contract 和旧路径依赖扫描由一个如实声明范围的命令执行；
- 历史上名为 “release source set” 的 422 文件清单已降格为脏树基线证据，不能证明 HTML-only 发布闭包；
- 真正的发布来源集只能在 R2–R4 完成后，从干净 commit 按新的 HTML-only 包边界生成。

当前工程仍是保全现场，不是发布工作树。

## 2. 原始现场证据及其局限

worker_01 在修改前生成了：

- `context/ci-rebaseline-rebuild-20260904_prechange_inventory.json`
- 采集时间：`2026-09-04T06:40:42.800215+00:00`
- HEAD：`bb27ec9d750cf02fb64da5dfe665b2f4b262922d`
- 分支：`main`
- Git status 条目：6,599（66 个 modified、6,533 个 untracked）
- status SHA-256：`6ae1d16633e2e67dd900e907134a5ef1154399b8e7d0f6cce59bb9490c81d60c`
- tracked index 条目：1,824
- tracked index SHA-256：`a48d8045e9742260397c6bc048250f3f9c4f0a968596b9b64972c8783c0c8854`
- inventory SHA-256：`5c7a5973dee9dbba7cea7e30daba283803d8bdd57b15451da85749f3c0c0550b`

该文件是路径/状态台账，不是逐文件哈希清单，也没有在 worker 修改前生成可恢复的字节备份。因此不得把它描述为完整的“不可变文件清单”或 pre-worker 恢复点。R0 后续恢复快照只证明 Codex 修订后的当前状态，不倒推不存在的历史备份。

## 3. 两份 422 文件历史基线

以下两个文件保持原始证据字节，不重写、不追认：

1. `docs/governance/rebaseline-release-source-set-v1.json`
   - source-set SHA-256：`9e935dfe9b84cae6d3f223a9269fbddf281128d3d1564254438f9468c3c4ad4f`
2. `docs/governance/rebaseline-release-source-set-v1-postquality.json`
   - source-set SHA-256：`7c0639045a0b0a8c87369a5308ba25432e3ca4cb9f7720f6c972aef09aa27a01`

二者均绑定当时的 `tools/bundle_contract.py:DEFAULT_ALLOWLIST`，包含 PDF、HTML-PPT、PPTX、监测及 v1.2 文档等首版明确不交付的内容。其 `dirty-baseline` provenance 也不是 clean-commit provenance。

`tools/verify_rebaseline_source_set.py` 现在仅提供两种能力：

- 校验历史 JSON 自身的结构和摘要；
- 在需要诊断时，将当前字节与历史脏树基线比较。

它永远返回 `historical_baseline_only`，并拒绝用 `--require-clean` 将历史清单包装成发布证明。`tools/gate.sh` 同样拒绝 `--require-clean` 与该历史清单组合。

## 4. 当前可恢复快照合同

`tools/rebaseline_snapshot.py` 与 `tests/contract/test_rebaseline_snapshot.py` 建立以下合同：

- 先在源树上冻结 Git 状态与逐节点哈希；
- 再复制完整仓库，包括 `.git`、tracked、untracked、ignored、原始运行证据和缓存；
- 从备份侧复算每个普通文件和软链接的 SHA-256、字节数、权限模式和节点类型；
- 逐节点比较源与备份，任何缺失、额外文件、摘要、模式、Git 状态或分类差异均失败；
- 外置 manifest 使用自身 canonical SHA-256 防篡改；
- 每条记录分别携带 `git_state` 和 `content_class`，明确区分 tracked modification、untracked source、normative evidence、raw run artifact、cache、Git metadata 与其他内容。

本快照的外置路径、文件数、字节数、manifest SHA-256 与只读状态在复制完成后写入独立 receipt。该 receipt 是 R0 恢复入口，不将 5.6GB 原始现场纳入发布包。

已验证快照：

- receipt：`context/ci-rebaseline-rebuild-20260904_recovery_snapshot_receipt.json`
- 外置备份：`/Users/smkzw/Documents/AI Products/.ci-rebaseline-backups/ci-workflow-r0-20260904T074503Z`
- 文件/软链接：19,498；总字节：5,910,548,662；
- 源 manifest canonical SHA-256：`74971303c2b0c7179948647ad8e98d021657c9c54c7b0a81e6d7371aeaf5c65e`；
- 备份 manifest canonical SHA-256：`ace8cad651eacdfc934ba580e5026a7642043fd40c1d1b9b13e0e06db78d03c3`；
- 源/备份逐节点比较：passed；备份内可写节点：0。

manifest 将 Git 状态与内容类型拆成两个维度；其中 tracked modified 71、untracked 6,565、ignored 7,666，原始运行产物 7,290、缓存 4,923、规范/治理证据 2,881、源码与测试 687。备份和两个外置 manifest 均已撤销写权限。

## 5. 如实声明范围的统一质量门

唯一开发质量入口为：

```text
bash tools/gate.sh
```

实际固定范围为：

- `uv run ruff check src tests tools`
- `uv run mypy --no-incremental --strict src tools --show-error-codes`
- `uv run pytest tests/unit tests/contract -q`
- `uv run python tools/check_no_legacy_refs.py`

2026-09-04 的最终观察：

- Ruff：通过；
- strict-mypy：191 个源文件通过；
- unit/contract：860 passed in 61.21s；
- 旧路径运行时依赖扫描：`LEGACY_REF_OK`；
- 总结果：`GATE_OK status=quality-only steps=4`。

`--require-clean` 只增加“工作树完全干净”的检查，成功状态为 `clean-quality-only`，不会自称 release candidate。当前脏树预期不能通过该选项。

## 6. ReportLab 类型边界

当前运行时使用 ReportLab 5.0.0；可获得的 `types-reportlab` 类型包面向 ReportLab 4.5.1。曾在锁定环境中临时验证该类型包，但它把 31 个 import 错误转化为 57 个 API 不匹配，故已完整移除，`pyproject.toml` 与 `uv.lock` 不保留该依赖。类型包版本依据可见 [PyPI types-reportlab](https://pypi.org/project/types-reportlab/) 与 [Typeshed](https://github.com/python/typeshed)。

保留的 PDF-native 代码采用 31 条逐导入、逐错误码的 `# type: ignore[import-untyped]`，仅分布于 10 个已延期 PDF 渲染文件；另有 2 条 ReportLab `Flowable` 继承边界的 `# type: ignore[misc]`。没有全局 `--ignore-missing-imports`。除此以外，`src + tools` 在 strict-mypy 下全绿。该豁免是开发仓库兼容边界，不会把 PDF 代码纳入 HTML-only 安装包。

## 7. HTML-PPT 合同与首版范围

worker_01 修正了旧 HTML-PPT 缩放断言，使保留代码的基础合同回归通过。该结果只说明延期代码没有破坏当前基础回归：HTML-PPT、PDF 和 PPTX 均不进入首版真实渲染门、安装包或 RC 格式计数。

R2–R4 必须建立新的 HTML-only allowlist 和 fresh-install 合同；不得沿用历史 `DEFAULT_ALLOWLIST` 作为最终包定义。

## 8. 旧目录零接触边界的审计更正

worker_01 的报告声称其旧路径检查“没有接触旧根”，但当时 `tools/check_no_legacy_refs.py` 对禁用路径标记调用了 `Path.resolve()`。该实现可能触发文件系统元数据解析，因此原声明无法由现有证据证明，不能接受。

Codex 已将该逻辑改为纯词法 `abspath/expanduser`，并增加软链接负向测试，证明扫描器不会解析或访问标记目标。修复后不再用任何命令检查旧目录是否存在，也不通过读取旧目录来反证。历史潜在元数据接触如实保留为 R0 事件，不夸大为读写或内容遍历。

## 9. 原始证据与后续发布来源集

当前树内的大体积 `runs`、`logs`、`archives`、浏览器产物和缓存首先作为恢复现场保全，并在全量 manifest 中分类、内容寻址。它们不是产品源文件。

R2–R4 构建干净发布工作树时：

- 规范性文档、精简回执、测试合同和校验指针可以进入版本控制；
- 原始运行证据继续留在外置内容寻址存储；
- HTML-only 发布来源集只纳入经验证的产品代码、公共入口、内部 Skills、宿主适配器、必要资产与运行合同；
- 任何凭据、缓存、原始运行证据、PDF/PPT 运行代码或依赖都不得进入安装包。

因此，R0 的 422 文件历史基线和当前全量恢复快照都不是最终 release source-set；后者解决恢复，前者保留历史，真正发布闭包由 R4 另行生成并绑定 clean commit。

## 10. 里程碑磁盘卫生（R0.4）

每个里程碑 checkpoint 前后必须盘点本轮新增空间，并将候选目标分成 retained 与 removable。删除只能同时满足：由当前任务生成、路径精确、可再生、已经由摘要或哈希替代、且不再被测试、恢复或后续验收引用。执行前记录目标与字节数，执行后记录实际释放量；禁止 broad glob、仓库级清理和 `git clean`。

以下内容默认保留，不得按“定期清理”自动删除：规范文档、checkpoint、manifest、receipt、原始科学证据、未验收门户、仍被测试引用的 fixture，以及当前和上一可恢复点。大体积历史证据只有在外置内容寻址副本验证通过后，才允许仓库侧只保留摘要指针。

真实旧根不属于空间盘点对象。任何 inventory、存在性检查、解析、chmod 或清理都必须等未来独立退役任务和用户再次明确批准；磁盘卫生授权不改变这条零接触边界。
