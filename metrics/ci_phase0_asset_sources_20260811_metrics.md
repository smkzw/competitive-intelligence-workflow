# Metrics: ci_phase0_asset_sources_20260811

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `code_open_audit` |
| Risk | `medium` |
| Selected provider | `codex` |
| Selected model | `codex-main` |
| Selected effort | `high` |
| Duration | 约 12 分钟主动核验；上游 S1 运行不计入本任务时长 |
| API calls | 未由 guard 报告；不以终端请求次数伪造 |
| Artifact size | 决策/对账/上下文/复核文本；未复制二进制资产 |
| Result | `PASS WITH DEFERRED ACTIVATION` |

## Verification Burden

- 3 类外部/本机来源；Logo 两次获取与两份本机字节对比。
- ECharts 官方 GitHub + npm 双来源、tarball integrity、7 个发行文件摘要比较、classic bundle 运行依赖扫描。
- html-ppt 官方 commit + 5 个文件摘要；960 行 runtime 完整读取并按康哲合同逐项裁剪。
- 当前 design_specs 12 文件集合摘要与 6 项结构测试；仓库 Ruff、mypy、pytest、旧依赖扫描、uv lock/sync 与 JSONL 解析回归。

## Routing Decision

`code_open_audit` 由 Codex 直接执行，未调用 Hermes、Reasonix、Grok Build 或子 Agent。原因是任务边界清楚、需要直接核对本机文件和官方发行物，且最终决定与用户授权边界均由 Codex 持有。
