# Codex Execution Review: ci-r2-r3-html-browser-repair-20260905

## Verdict

accept — 接受本次受限修复，不代表 R2/R3、真实报告矩阵或发布验收完成。

## Worker Outputs

- `worker_01`：A 门户 11 页合同、默认折叠完整表与相邻验收迁移；选择性采纳。
- `worker_02`：B 气泡图数值标签、`not_applicable` 热图、基线排序与真实跨试验标志；选择性采纳，并由 Codex 修正一个遗漏的折叠表展开测试。
- `worker_03`：C 11 页/八类图合同、首屏图表、真实设计值、DOM 锚点与共享抽屉词表；选择性采纳。
- 三个 worker 均使用 `zcode / GLM-5.3-Flash / max`，无 fallback。执行发生在三个隔离副本，worker 自报不作为验收依据。

## Manager Assessment

本路由未声明独立 execution manager；计划明确由 Codex 逐文件处置。Codex 未复制隔离树或整包应用，而是审阅差异后通过 `apply_patch` 合并，解决 worker 02 与 worker 03 对共享资产清单的并发覆盖，并修正 worker 02 漏迁移的证据抽屉点击用例。路由治理结果以 `audit-execution` 输出为准。

## Boundary

本次只接受 A/B/C 门户与共享 HTML 浏览器层的合同迁移和缺陷修复。未触碰旧工程、外部真实项目、PDF/HTML-PPT/PPTX 产品代码、RC 状态或 sealed checkpoints。隔离副本中的 `.venv` 指向主仓源码这一环境风险由 Codex 在主仓独立重跑消解。

## Hermes

执行遵循 guard 生成的 ZCode 路由与单次长等待合同。Hermes 未作为传输或替代路由；未发生模型替换、重派、固定间隔轮询或 fallback。

## Codex Independent Verification

- Ruff：变更 Python/测试文件通过。
- strict mypy：A/B/C 渲染器与共享图表规范通过。
- Node 语法：`charts.js`、`report-c.js`、`evidence-drawer.js` 通过；共享资产两份副本字节一致。
- 合同/验收聚焦集：113 passed。
- A 浏览器与集成：62 passed。
- B 浏览器/报告/集成：完整运行 308 passed、2 failed；遗漏展开修复后两项失败用例 2 passed，故障集合闭合。
- C 浏览器与验收：81 passed。
- 共享图表、证据抽屉、筛选和门户壳层：217 passed。
- 全仓质量 Gate：Ruff 全仓通过；strict mypy 196 个源文件通过；unit/contract 861 passed；旧路径运行时依赖扫描通过。
- Codex 重新生成三报告 fixture，并实际打开 A 矩阵、B 疗效安全矩阵、C 设计模式页的 1440×1000 全页截图。三页无横向溢出、空图、DOM 崩溃或工程字段泄漏；B 标签显示临床数值，C 图表位于完整表之前并显示真实设计事实。

尚未验证且不属于本次接受范围：八适应症 24 个真实门户、四视口全物理页独立视觉会商、三宿主 fresh-install、当前包摘要下的外部真实项目重建。旧外部产物摘要不匹配继续 fail-close。

## Cleanup Decision

在 `review-gate` 与 `audit-execution` 通过后归档本任务过程文件；删除三个精确定位的 `/tmp/ci-r2-browser-w*` 隔离副本、本次临时视觉 fixture 和可再生项目缓存。保留 worker 报告、审阅、指标、路由清单及必要运行证据。
