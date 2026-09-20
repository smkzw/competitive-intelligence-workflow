# Task 10.5 精准切换工具验收说明

## 边界

本阶段只实现并验证切换工具与发布回执合同。所有 `inventory`、`validate`、`apply`、`absence-check` 的写入性验证均发生在 pytest 一次性临时根；没有对真实旧工程、旧全局 Skill、归档、缓存、备份或消费者入口执行命令。真实 inventory/dry-run 属于 Task 10.7，真实 apply/absence-check 属于 Task 10.8。

## 精准切换链

1. registry 必须显式给出批准绝对根和每个登记项；工具没有默认旧根。
2. inventory 只对登记项使用 `lstat`，记录 path、realpath、device、inode、类型、摘要、动作与批准根；目录摘要不跟随符号链接。
3. Task 10.7 的 validate 要求当前观察与 inventory 完全一致、恢复包回执为 `passed`，并生成预授权 validation 摘要；用户 authorization 必须绑定该摘要、inventory、registry、recovery receipt 与精确动作。
4. Task 10.8 的 apply 按既定 `--manifest --authorization --receipt` 接口核验该已验证授权链并再次观察当前状态；可选 `--validation-receipt` 只是额外复核，不是绕开授权链的替代品。文件/链接用 `unlink`，目录只能在登记子项逐项处置后用 `rmdir`，不递归扩大删除范围。逐项处置不是伪事务：任一项失败统一返回 `LEGACY_CUTOVER_FAIL`，修复后以同一授权重放，已完成项得到 `already_absent`。
5. absence-check 对任何仍存在的登记项失败，包括 action 为 `retain` 的旧运行时或引用；不会把“保留”误报为“无残留”。

`--legacy-root` 是 Task 10.7 已批准命令形态的单根快捷入口：它递归登记该根但对所有文件只计算 metadata 哨兵摘要，避免读取未知凭据/会话内容。最终清单若还包括根外旧全局 Skill、归档副本、启动器或消费者引用，必须使用经过审阅的多根 `--registry` 明确逐项加入；单根快捷清单不能冒充全域切换授权。

validate 成功信号只报告可证明的 `escapes=0`、`recovery=passed` 与 `content_mode=metadata_only|explicit_content`；它不输出无法由工具证明的“凭据数量”。`--scan-root` 只是确认所有登记路径都落在调用方声明的扫描根内，absence-check 仍只核验精确 registry，不进行通用磁盘或秘密扫描。

路径逃逸、批准根或路径祖先为符号链接、device/inode/type/摘要漂移、未知字段、全空 inventory、恢复包未通过或字段无效、授权摘要不匹配、删除父项同时保留子项、未登记目录内容阻止 `rmdir`，均失败关闭。登记叶符号链接允许指向批准根外，但工具只摘要其目标文本并删除链接自身，从不跟随或修改目标。

## required-v12 release receipt

`schemas/release-case-receipt.schema.json` 固定 case/release scope/owner、catalog/package/RC 摘要、run/session、input/artifact/verdict 摘要、项目合同、时间和回执自身摘要。它是 acceptance root 下 `case-receipts/<case_id>.json` 的最终 owner-stage 聚合信封，不覆盖 catalog 中指向 `host-receipt.schema.json` 的 pre-RC 运行回执。聚合器显式核验这两层合同，重新验证 catalog schema 与 case digest，并逐项绑定实际 catalog/package/project-contract 文件；`input_sha256` 从 catalog 的排序输入声明重算。

`artifact_sha256` 与 `verdict_sha256` 绑定上游 owner 已接受证据的摘要；本聚合器不替代对应的科学、视觉、包或恢复验证器，也不凭摘要字段自行宣布产物真实存在。

- 所有适用 required-v12 case 只有 `accepted` 才闭合；`pending_future_owner` 保持未闭合。
- 只有 catalog 同时声明 `execution_scope: conditional-extension` 和 `not_applicable` 的可选适配器允许 `not_applicable`，且必须绑定当前项目合同摘要。
- receipt 及其证据根不得经符号链接逃逸。

catalog 的 `receipt.owner_status` 是冻结时的责任基线，不在 RC 后改写，否则会使 case/catalog 摘要和全部既有回执漂移。聚合器要求其属于允许的责任状态，并以精确 `owner_task`、冻结摘要和 owner-stage release receipt 推进最终闭合；闭合权来自受治理的 acceptance root 与冻结记录，不来自动态改写 catalog。

本阶段新增的两个 Python 工具是仓库内治理工具，不属于可安装运行时 bundle，因此不进入 `package-manifest.json` 的运行时组件白名单；发布回执 schema 属于可移植合同，已纳入 package manifest。Task 10.6 必须按本工具已冻结的消费者合同生产 `recovery-package-v1` 回执（含 `kind/status/passed/sha256/issued_at` 且拒绝未知字段），否则 Task 10.7 的预授权验证不得通过。

## 本阶段机械验证

```bash
uv run pytest tests/migration/test_legacy_cutover.py tests/acceptance/test_required_receipt_closure.py tests/contract/test_package_manifest.py -q
uv run ruff check tools/legacy_cutover.py tools/verify_release_receipts.py tests/migration/test_legacy_cutover.py tests/acceptance/test_required_receipt_closure.py
uv run mypy tools/legacy_cutover.py tools/verify_release_receipts.py tests/migration/test_legacy_cutover.py tests/acceptance/test_required_receipt_closure.py
uv run python tools/check_no_legacy_refs.py --root .
```

真实切换命令在 Task 10.7/10.8 获得最终 RC、恢复包和用户授权之前不得运行；本文不提供真实路径示例，避免把开发验收误用为处置授权。

清单与授权摘要提供的是漂移可见性，不是数字签名。真正的权限锚来自冻结 RC、恢复演练、Task 10.7 向用户展示的完整多根清单及用户对该清单摘要的明确授权。
