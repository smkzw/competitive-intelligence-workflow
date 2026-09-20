# Conference Metrics: ci-phase10-task101-acceptance-matrix-review

Date: 2026-09-01

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_single_object` | `cursor` | `default` | 完成 | 190.680s + 同会话复核 512.396s | 146 + 66 | 43885 | 接受，附非阻断未来说明 |

## Timeout And Retry Evidence

会话 `01a05b24-0174-7000-895d-98490c923c70` 连通成功并在第二轮复用；无 fallback、无新会话、无超时终止。

## Quality Decision

Pass。首轮异议已通过直接计划对照、future-owner 语义说明和 bundle allowlist 修复闭合；延后格式轨道的相邻失败不计入 Task 10.1。
