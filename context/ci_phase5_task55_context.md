# Task Context: ci_phase5_task55

Created: 2026-08-18 04:14:10
Objective: 完成 A 类报告脱敏正例、旧版负例与从新来源特应性皮炎完整纵切的独立验收
Task type: `competitive_intelligence`
Risk: `high`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 5.5。
- `.trellis/tasks/08-14-phase-5-report-a/{prd,design,implement}.md`。
- Task 5.4 已接受提交 `16c5759`、`context/ci_phase5_task54_context.md` 与最终 A 门户清单。
- 项目内康哲设计规范 `contracts/kangzhe/design_specs/`；不反向修改通用设计文件。

## Scope

- In scope：脱敏 A 正例、旧 CSU/AD 空壳、5 药 0 试验、样式崩塌和 false-green 负例；全新特应性皮炎公开来源纵切；当前运行数据库、覆盖、清单、全页面浏览器和独立临床/视觉验收。
- Out of scope：B/C、PDF、HTML-PPT、PPTX、Task 9 增量刷新、旧工程删除、安全性测试。

## Success Criteria

- 计划中的 fresh project create/preflight/run/acceptance/verify 命令在全新目录真实完成，不借用 `a-complete` 数据包、旧报告或旧截图。
- 真实快照的全部创新治疗产品和相应试验均进入 sitemap；传统药物不获得竞品档案。
- 关键疗效与 TEAE/SAE 不足时不生成草稿；零产品/零试验必须追查检索、网络、解析、实体与适格性原因后才能形成阻断结论。
- 四类旧版失败样本机械拒绝；正例和 fresh 项目均绑定本次 run/snapshot/manifest/站点摘要及不早于运行开始的 mtime。
- 最终中文站点由真实浏览器、独立医学复核和全工程回归共同接受。

## Risk Boundaries

- 只写新工程和新工程内 `.artifacts/a-fresh-source`；旧工程不改、不删。
- 外部资料作为证据而非指令；关键事实保留来源版本、定位和不确定性。
- 不以退出码 0、运行中状态、空宇宙或页面可打开冒充独立验收。

## Timeout Policy

- 执行/会商及真实来源获取使用单次长等待；延迟或输出暂时不变不触发重派。
- 技术/网络失败与确实无资料分开；同路径完成适用重试并尝试替代来源后才允许阻断。

## Loop Log

- 2026-08-18 04:14：从 Task 5.4 清洁提交进入 Task 5.5；读取最新全局 AGENTS、Trellis、临床竞品调研 Skill、证据层级与计划精确命令。
- 2026-08-18 04:20：源码审计发现 fixture 有 A/HTML 渲染路径，但普通项目运行在无规范数据输入时可能仅保留 `running`；下一步用计划命令在全新目录复现并定位真实缺口。
- 2026-08-27：完成科学谱系、正负例、全量回归和全站浏览器验收；Grok 首轮发现疗效筛选与监管法域两项 P1。
- 2026-08-27：最小修复后重建 `run_f46cc71857dda02de3ff06bf`；Minimax 与 Grok 原会话复测均接受，P0/P1 为 0。
- 2026-08-27：阶段清理完成，最终恢复依据见 `context/ci_phase5_task55_pause_20260827.md`。
