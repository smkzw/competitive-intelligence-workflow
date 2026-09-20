# Codex Execution Plan: ci-phase8-task82-complete-native-pdf

Objective: 完成 Task 8.2：锁定唯一 three-report-complete A/B/C 基准快照，复用已验证的 ReportLab 原生 PDF 引擎，按 PDF01–PDF09 生成三份完整、高信息密度、可检索、带书签和续表的 A/B/C PDF，并完成覆盖与逐页视觉验收。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 建立并锁定 three-report-complete 基准 fixture、逐文件摘要、实体计数、GateSpec 预期和当次 run/manifest 绑定；先完成精确 RED/GREEN。 | `runs/execution/ci-phase8-task82-complete-native-pdf/worker_01.md` |
| `worker_02` | 实现 A/B 原生 PDF 投影：A 类完整 profile、疗效、安全性和矩阵；B 类疗效、纵向、安全性、矩阵、基线、完成处置与试验档案。 | `runs/execution/ci-phase8-task82-complete-native-pdf/worker_02.md` |
| `worker_03` | 实现 C 原生 PDF 投影：设计图谱、人群、入排、干预、终点/时间/访视/统计、逐试验详情、模式与多路径。 | `runs/execution/ci-phase8-task82-complete-native-pdf/worker_03.md` |
| `worker_04` | 实现共享原生图表、表格、书签与 coverage projection，对三份当前 PDF 运行 pypdf/pdftotext/pdftoppm 全页验证并只报告缺陷。 | `runs/execution/ci-phase8-task82-complete-native-pdf/worker_04.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
