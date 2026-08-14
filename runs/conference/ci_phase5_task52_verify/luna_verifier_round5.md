PASS

P0=0，P1=0，P2=0。

实际复核：

- `SourceVersionRecord` 的 source_id、摘要/路径、获取时间、媒体类型、日期状态、locator、重开文本篡改：8 个 build + 8 个 authoritative 入口全部拒绝；摘要确定性及重排稳定性通过。
- 999/2099 自洽伪造上下文，保留原外部合同存储：16 个入口全部拒绝；外部参数 16 个入口均为必填、无默认绕过。
- 跨产品/试验、伪造 locator、source role、review/disclosure、事实实体篡改：全部拒绝。
- 重复 binding_id、复制 binding 重用事实、疗效/安全跨域复用事实：全部拒绝；正向结果唯一。
- blocked 分析状态下 8 个 build 与 8 个 authoritative 入口全部拒绝；无工程词泄露。

机械检查：

- round4：38 passed
- round5：15 passed
- A 类单元：219 passed
- A 类联合：310 passed
- Ruff：通过
- strict mypy：89 个源文件通过
- `compute_locked_snapshot`、`SnapshotStore.lock/read` 正向身份完全一致。