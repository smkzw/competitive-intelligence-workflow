# Task Context: ci_phase4_task45

Created: 2026-08-14 07:33:57
Objective: 实现同页数据依据面板、固定对照、网址恢复和焦点返回
Task type: `html_ppt_visual_browser`
Risk: `high`
Selected agent route: `opencode-go` / `deepseek-v4-pro` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §15.4–15.6。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.5。
- `.trellis/tasks/08-13-phase-4-common-report-portal/{prd.md,task.json}`。
- Task 4.1–4.4 已验收的 `view_state.py`、`filters.py`、`url_state.py`、`charts.js`、`portal.js`、`portal.css` 与 Task 4.4 浏览器夹具。
- 项目内冻结康哲设计合同与现有门户视觉语言；本任务不回写通用版设计文件。

## Scope

- In scope：规范数据依据视图；图形标记、热图单元和表格单元打开同一条数据依据；右侧同页面板；多条固定对照；筛选/滚动保持；Esc 关闭；焦点回到原触发点；网址刷新、复制、前进/后退恢复；基线与完成情况扩展字段；中文原生可用性。
- Allowed output paths：`src/ci_workflow/reports/common/evidence_view.py`、`src/ci_workflow/renderers/portal/evidence_drawer.py`、现有门户资源的必要小改、Task 4.4/4.5 测试夹具、`tests/browser/test_evidence_drawer.py`、本任务 context/prompts/runs/reviews/metrics 与 `.trellis` 当前 Phase 4 条目。
- Out of scope：A/B/C 完整业务页面、真实医学结论、PDF/HTML-PPT/PPTX、外部发布、生产路径、安全专项测试。

## Success Criteria

- 每个可交互图点、热图/状态矩阵单元、完整表格数据单元都绑定同一稳定 `row_id`，打开内容不得串行或跨快照。
- 面板至少显示产品、试验、组别、终点/事件/设计要素、量表、时间点、值/阈值/单位、分子/分母、来源版本、精确定位；不适用、尚未公开、来源未列示分别呈现，不得空白或补造。
- 基线/试验完成情况行额外显示规范字段族、来源原名与定义、统计形式/计量对象、量表版本方向、分母角色、时间窗/基线定义、原始/规范原因、互斥穷尽、兼容规则/差异、披露状态。
- 用户可固定多条并列核对；筛选变化移除已不在当前事实行集的打开项/固定项，不得自行放宽筛选。
- 打开/关闭不改变滚动；Esc 关闭后焦点回到准确触发点；键盘可操作；减少动态效果有效。
- 当前打开行和固定行进入版本化 URL；刷新、复制、前进/后退恢复；未知/过期行失败关闭并规范化网址。
- Chromium 与 WebKit 的真实交互测试、全库回归、静态检查、包校验通过；Codex 重开真实页面并由指定视觉审评路线独立试用后才可接受。

## Risk Boundaries

- 仅写上述项目内路径，不读写生产路径；不新增远程依赖或远程请求。
- 用户可见文本必须是中国临床试验语境的自然中文；禁止出现 prompt、日志、后端枚举、`row_id`、`gate`、`signal` 等工程词。
- 未公开不是 0；不适用不是缺失；来源定位未知时不生成伪链接或伪定位。
- 本任务不做安全测试，测试投入聚焦真实用户功能、交互和视觉可读性。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 07:33:57: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 07:35: 重新读取最新全局 `AGENTS.md`、设计 §15.5、计划 Task 4.5 与 Phase 4 Trellis 检查点；确认不新增依赖，沿用现有不可变行、筛选、URL 和图表联动合同。
- 2026-08-14 10:53: 首线实现完成；证据视图、同页面板、固定比较、图/表 row_id、URL、Esc/焦点和双浏览器夹具落盘。
- 2026-08-14 13:10: 三路真实医学经理初审均否决；确认并修复 EASI/Age 串值、特应性皮炎页 HbA1c/mg/dL、热图表空值、状态矩阵语义复用和异常大空白。
- 2026-08-14 14:05: 第二轮复核发现筛选后图表仍保留越界数据、单个固定项与当前项无口径提示、移除提示随面板关闭消失；补机械断言后修复。
- 2026-08-14 15:00: 第三轮 CodeBuddy/kimi-k2.6、Grok Build/grok-4.6、Pi/minimax-m3 原会话真实复核均 PASS，无 P0/P1；Codex 独立查看关键截图。
- 2026-08-14 15:20: Task 4.2–4.5 联合回归 419 passed；全库 956 passed；Ruff、strict mypy、资源镜像/manifest 通过。Task 4.5 接受，下一步 Task 4.6。
