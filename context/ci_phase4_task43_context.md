# Task Context: ci_phase4_task43

Created: 2026-08-14 01:58:07
Objective: 实现页面级与模块级多选筛选、互不污染的重置和可复现网址状态
Task type: `html_ppt_visual_browser`
Risk: `high`
Selected agent route: `alibaba` / `qwen3.8-max` / `xhigh`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- 批准实施计划 Phase 4 Task 4.3 与设计 v1.2 §15.4、§15.7。
- Task 4.1 的 `ReportViewModel` / 稳定 row ID 与 Task 4.2 已接受门户壳层 `b2288f1`。
- 页面目录和适用筛选维度来自冻结 A/B/C 页面责任；不能由前端自由补造。

- 康哲项目内化设计合同：`contracts/kangzhe/design.md` 与 `contracts/kangzhe/design_specs/`。

## Scope

- In scope：页面级适应症/产品/靶点或机制/试验多选；模块级终点/时间点/效应形式/分析人群/AE/设计要素/量表及 B 基线与完成情况扩展维度。
- In scope：页面与模块重置互不污染；筛选、排序、锚定试验、选中证据和当前页的版本化 URL；刷新、复制、前进/后退恢复；空结果不自动扩围。
- In scope：中文原生、面向不熟悉软件的医学经理的紧凑筛选交互；`file://` 和静态服务器、Chromium/WebKit、桌面与 1024 折叠。
- Out of scope：Task 4.4 图表/完整表渲染、Task 4.5 证据抽屉内容、真实临床数据、PDF/PPT、安全测试。


## Success Criteria

- 页面级和每个模块级状态拥有独立键空间；重置一层不改写另一层，URL 可确定性往返。
- URL 使用稳定 ID，不靠中文标签作为身份；状态有版本，未知/重复/无效字段失败关闭或给出明确中文提示，不能静默截断。
- 大状态不塞爆网址：达到合同上限时转为本地命名视图建议，不丢选项；本任务只实现机器边界，不要求复杂视图管理器。
- 空结果只显示“当前选择下暂无可比较数据”、当前限制和两个明确重置动作；不得自动清空或扩大筛选。
- 适用维度才出现；不适用维度隐藏或禁用并说明，不误写成“数据缺失”。
- 浏览器实测复制网址、刷新、前进/后退、页面重置、模块重置、键盘与 reduced-motion；生成者无验收权。


## Risk Boundaries

- 不改变已接受 Task 4.2 的 Logo、导航、搜索、中文禁词和多物理页合同。
- 不把控件堆成程序员式查询构建器；默认只显示当前选择摘要和常用维度，高级维度分组展开。
- 不为让空结果消失而修改事实集、自动改选项或跨模块串改状态。

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 01:58:07: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 01:59: Task 4.2 已接受且工作树干净；Task 4.3 开始。Qwen 周配额失败状态已在 Task 4.2 真实记录，runner 仍按声明链先判断主路线，再只允许 Cursor/CodeBuddy 声明 fallback。
- 2026-08-14 02:00-03:20: 声明执行路线未产出可接受结果；保留失败回执，未采信其生成候选。Codex 逐项构造反例，沿同一 Cursor 会话完成两轮修复：网址未知/重复字段失败关闭、稳定标识编码、UTF-8 字节上限、模块行隔离、页面目录权威、全局网址状态与错误网址不覆盖现状。
- 2026-08-14 03:26-05:20: 以真实医学经理角色开展视觉试用。首次发现测试文案、产品命名不一致、疗效/安全条件混放和清除范围不清；修订为“整份报告条件 / 疗效数据 / 安全性数据”三级中文语义，各自独立清除，并隐藏仅用于边界测试的超长选项。
- 2026-08-14 05:20: CodeBuddy kimi-k2.6、Pi minimax-m3、Grok Build grok-4.6 均在同一会话完成最终复核；三者结论均为 PASS，P0=0、P1=0。Minimax 与 Grok 均完成 1280/1024 真实浏览器点选、空结果、分层清除、前进/后退/刷新；Kimi 完成同等 Playwright 复核。
- 2026-08-14 05:30: Codex 在最终树重跑 203 项聚焦测试、697 项全量测试、Ruff、strict mypy、包校验和 diff check，全部通过；原分辨率截图复核通过。Task 4.3 接受。

## 恢复锚点

- 状态：Task 4.3 `accepted`；下一步 Task 4.4。
- 实现：`filters.py`、`url_state.py`、`page_shell.py`、双份门户 CSS/JS、单元/合同/浏览器测试。
- 最终页面证据：`.artifacts/task43-portal/current/screenshots/filter-1280.png`、`filter-1024.png`。
- 已知后续边界：真实业务数据绑定时，为适应症和靶点/机制补齐 `ReportRow` 投影；当前纯筛选器与网址合同已闭合，但不能用未投影字段静默筛选。
