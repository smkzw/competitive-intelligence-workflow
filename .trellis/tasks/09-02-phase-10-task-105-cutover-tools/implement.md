# Task 10.5 实施步骤

- [x] F01：读取 required-v12 catalog、现有 receipt/schema/恢复包合同和 Task 10.4 检查点。
- [x] F02：先写精准 inventory/dry-run、validate、apply/idempotence、absence-check 负向测试。
- [x] F03：实现 `tools/legacy_cutover.py`，仅支持显式 registry 与批准 fixture 根。
- [x] F04：写 release-case receipt schema 和 owner-stage closure 测试。
- [x] F05：实现 `tools/verify_release_receipts.py` 并运行定向/相邻回归与静态检查。
- [x] F06：独立审查、治理审计、真实旧根未触碰证明与无损检查点收口。

## 回滚点

若任何命令默认指向真实旧根、跟随符号链接、允许授权摘要漂移、把 pending 当 accepted、或测试在 `tmp_path` 外写入，则撤销 Task 10.5 未接受改动并恢复至 Task 10.4 检查点。
