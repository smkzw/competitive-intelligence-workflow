# Execution Metrics: ci-phase9-task95-candidate-bundle

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `openai-codex` | `gpt-5.6-luna` | 完成 | 1376.327s | 399 | PK01–PK02 构建、逐文件摘要、校验器与反例完成 |
| `worker_02` | `openai-codex` | `gpt-5.6-luna` | 完成 | 1625.592s | 559 | PK03–PK04 内容寻址安装与真实宿主 runner 完成 |
| `worker_03` | `openai-codex` | `gpt-5.6-luna` | 完成 | 1718.077s | 619 | PK05–PK06 测试、中文说明与归档合同完成 |

## Codex 复验

- 候选包：`BUNDLE_OK`，374 文件，SHA-256 `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`。
- 规范安装：`PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`。
- 三宿主：Codex、Hermes、OMP 均为 `path_resolved`，完整阻断—恢复—HTML 路径通过，`real_host_pass=true`。
- 聚焦测试：63 passed，1 skipped；Ruff 和目标 mypy 通过。
