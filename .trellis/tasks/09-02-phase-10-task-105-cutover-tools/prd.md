# Task 10.5 PRD：精准切换工具与发布回执闭环

## 目标

在 RC 冻结前实现并验证一套最小、可审计、失败关闭的旧工程精准切换工具，以及 required-v12 release case 的 owner-stage 回执闭环验证器。

## 必须满足

1. `inventory` 只枚举显式注册的旧根、旧全局 Skill、归档副本、符号链接、启动器与消费者引用；记录 path、realpath、device、inode、类型、SHA-256 和拟处置。
2. `dry-run` 不改变任何目标；前后清单摘要一致。
3. `validate` 拒绝路径逃逸、跟随符号链接、inode/device/摘要漂移、授权清单摘要不匹配和未通过的恢复包。
4. `apply` 只接受匹配的授权摘要，逐项处置且可幂等重放；测试仅作用于 `tmp_path`。
5. `absence-check` 对任何已登记旧运行时或消费者引用残留失败关闭。
6. release receipt 绑定 catalog/package/RC digest、owner task、run/session、input/artifact/verdict digest 与时间。
7. `pending_future_owner` 不得计为 accepted；只有 catalog 声明为可选的适配器才能按项目合同成为 `not_applicable`。

## 非目标

- 不对真实旧根、真实旧全局 Skill、真实归档、缓存、凭据或启动器执行 inventory/apply。
- 不实现通用安全扫描器，不扩大到未注册路径。
- 不冻结 RC、不关闭 Task 10.8 `legacy-absence`、不宣称产品最终接受。

## 完成证据

- 五个指定文件实现完成。
- 定向 RED/GREEN、静态检查、相邻回执/迁移回归通过。
- 独立审查和受治理执行审计通过。
- 检查点明确真实旧根未读取执行、未修改、未删除。
