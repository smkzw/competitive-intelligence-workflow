# Metrics: ci_phase1_task12_project_workspace

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `cms-smk` |
| Selected model | `cms-model` |
| Selected effort | `high` |
| Duration | 健康检查 90.017s；真实审查会话 160.986s |
| Session | `019ff028-b597-7000-8d5c-237357c59c2e` |
| Tool calls | 83 |
| Tokens | 50,748 total；46,208 cache read；1,127 input；3,413 output |
| Artifact size | 最终报告约 8 KB；可替代原始 stdout 约 2.5 MB |
| Result | PASS；no fallback |

## Verification Burden

Task 1.2 由 Codex 先跑确定性测试，再由新上下文参与者复现。最终接受依据是两方都获得 29 项任务测试、102 项全库回归与静态检查全绿。

## Routing Decision

Initial route reason: default route for task type.

诊断性 provider/model 健康检查超时，但返回 `model_catalog_valid=true`。按合同仍对 `cms-smk/cms-model:high` 做一次真实路由尝试；该尝试建立会话并正常完成，因此未启用 fallback。
