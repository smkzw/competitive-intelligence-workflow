# Execution Metrics: ci-phase9-task94-host-adapters

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3` | 完成 | 741.450s | 49 | 统一回执、双份 Schema、边界反例与集成修订完成 |
| `worker_02` | `zcode` | `GLM-5.3` | 完成 | 280.168s | 29 | 三宿主薄适配器、HA02–HA08 与恢复一致性完成 |
| `worker_03` | `zcode` | `GLM-5.3` | 完成 | 1247.137s | 79 | 真实入口 runner、HA09–HA10、回执验证与夹具完成 |

## Codex 复验

- 聚焦验收：115 passed in 55.55s。
- 完整集成：347 passed in 122.30s。
- Ruff：目标文件全部通过。
- strict mypy：7 个相关源码文件无错误。
- 根/包内 `host-receipt` Schema：逐字节一致。
- 包完整性：`PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`。
- 三宿主源码级真实调用：均为 `evidence_blocked`、11 个事件、零报告文件；不冒充 Task 9.5 fresh-install 验收。
