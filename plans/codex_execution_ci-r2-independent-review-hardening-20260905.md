# Codex Execution Plan: ci-r2-independent-review-hardening-20260905

Objective: 按 Codex 对 CodeBuddy 与 gpt-6-astra 阶段审阅的裁决，最小化修复 R2 独立科学复核信任根、post-format 不可变晋级、A/B/C 状态一致性、bundle 与测试门口径；TDD、失败关闭，不扩展 v1 产品范围。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现最小、可重复的 scientific-review-v1 签发入口：绑定现有 review request、真实 reviewer/producer 分离、runner/host 执行证据与正式 verdict 字节；补未来/过期时间拒绝和无真实签发记录负向测试。 | `runs/execution/ci-r2-independent-review-hardening-20260905/worker_01.md` |
| `worker_02` | 重排 B/C 运行时为 format 完成后才允许科学晋级，并将首次门户 manifest/站点字节摘要绑定进 review request；恢复时重验字节，支持等待回执的受控多次 resume 与晋级后幂等，不接受跨候选/跨项目/无关历史。 | `runs/execution/ci-r2-independent-review-hardening-20260905/worker_02.md` |
| `worker_03` | 把 fresh A 接入与 B/C 同等级的 rendered_unreviewed→独立回执→不可变晋级状态机，移除 research-package 内自审作为最终授权，补当前 A 真实来源可达性与负向测试。 | `runs/execution/ci-r2-independent-review-hardening-20260905/worker_03.md` |
| `worker_04` | 补齐 HTML-only bundle 的 scientific review Python 模块/required-content，校准 retained non-HTML 门为明确的兼容性 smoke（不重启排除格式产品轨），并补精确分层/隔离安装导入测试与信任根文档。 | `runs/execution/ci-r2-independent-review-hardening-20260905/worker_04.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
