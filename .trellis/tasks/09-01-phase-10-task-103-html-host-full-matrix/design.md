# Task 10.3 设计

## 最小编排

`tools/run_acceptance.py` 只做入口；业务合同位于 `src/ci_workflow/application/acceptance_runner.py`。runner 复用既有 fixture 运行、门户核验、候选包三宿主 smoke 和项目核验能力，不实现第二套报告生成器。

```text
acceptance catalog
  → 校验 full-matrix-v1 与全部输入摘要
  → 在空项目运行同源 three-report-complete 输入
  → 校验 catalog 输入与实际运行输入逐文件同摘要
  → A/B/C HTML 全路由（仅 ego(lite)，1024/1280/1440/1920 四档桌面视口）
  → 候选安装根 Codex/Hermes/OMP host-smoke-v1
  → project verify
  → pre-RC manifest + case rehearsal receipts
```

## 运行身份

每次运行生成独立 `pre_rc_run_id`，并绑定 catalog 与 case digest、项目 run ID 与清单摘要、A/B/C 三个 HTML artifact 与浏览器 verdict、三个不同宿主的进程/会话/运行回执，以及每个适用场景的 rehearsal 回执。

目录固定在 `docs/acceptance/pre-rc-runs/<pre_rc_run_id>/`。运行时产物可放在用户指定的隔离 acceptance root；仓内只保存精简回执和内容摘要，不复制大型站点。

## 场景责任

- 本轮关闭的只是“已预演”：`pre_rc_rehearsal`。
- Task 10.6 的最终 release case、`recovery-rehearsal` 和 Task 10.8 的 `legacy-absence` 保持 `pending_future_owner`。
- `optional-adapter-recovery` 仍按项目合同条件处理，不被本 runner 猜测。
- PDF、HTML-PPT、PPTX 不进入 manifest 的首版 artifact 集合，也不能以缺失状态制造部分交付。

## 失败关闭

预存项目、catalog 漂移、输入摘要不一致、非 HTML 格式、A/B/C 任一缺失、当前运行断链、浏览器 verdict 不属于本次文件、宿主回执复用或任一命令非零时，保留诊断并停止，不写成功信号。
