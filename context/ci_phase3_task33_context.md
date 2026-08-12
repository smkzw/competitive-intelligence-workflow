# Task Context: ci_phase3_task33

Created: 2026-08-12 20:52:22
Objective: 按批准计划实现 Task 3.3：只有确为关键阻断的 publication/supplement 才请求用户下载；用户保留原文件名放入唯一目录后，系统自动识别 NCT/DOI/标题、规范命名、隔离或原子归档、重新抽取并幂等续跑。
Task type: `finite_code_task`
Risk: `high`
Selected agent route: `cms-smk` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §10.2、§11.5、§11.7。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 3.3。
- `src/ci_workflow/domain/enums.py`：既有六态 `DownloadRequestState`。
- `src/ci_workflow/storage/event_store.py`：追加式事件与幂等键真源。
- `src/ci_workflow/storage/content_store.py`：内容寻址、原子落盘与来源版本链。
- `src/ci_workflow/ingestion/classifier.py`、`identity.py`：既有来源分类和实体标识约定。
- `src/ci_workflow/application/project_service.py`：项目内 `evidence/manual-inbox`、`evidence/quarantine`、`evidence/library` 目录合同。
- 用户已批准的产品决定：只有关键字段仍被阻断且目标附件很可能关闭该缺口时才请求补件；用户保留发布者原文件名，Agent 负责识别、规范命名、归档和重抽取；临床试验设计事实优先取登记平台，统计细节和 B 类完成情况非阻断。

## Scope

- In scope: `src/ci_workflow/ingestion/manual_inbox.py`、`schemas/download-request.schema.json` 和计划指定的三个集成测试；必要时只做最小 `__init__.py` 导出及 `package-manifest.json`/对应合同测试登记调整。
- In scope: 下载请求创建/取消判定，稳定请求身份与唯一相对收件目录，六态迁移守卫和事件，文件内容识别，规范命名元数据，隔离、原子归档、重抽取任务回执和幂等重放。
- In scope: PDF/HTML/纯文本及通用二进制的确定性完整性/错误页识别；依赖嵌入文本、请求标识符和标题完成 NCT/DOI/标题唯一匹配，不做 OCR 或联网下载。
- Out of scope: Task 3.4 通用控制图、真实论文解析器、浏览器登录、远程下载、UI/报告、数据库迁移、新外部依赖、安全性测试。

## Success Criteria

- 计划指定三份测试先因 Task 3.3 API/规则缺失而 RED，随后全部 GREEN；测试必须覆盖关键/非关键补件决策，而不是只验证 happy path。
- `awaiting_user -> file_detected -> matched -> accepted` 完整链及两条返工链、任一未接受态到 `not_required` 均保存前后状态、触发者、守卫证据、时间和幂等键；未声明迁移拒绝。
- 下载请求必须保存稳定请求 ID、阻断优先级、报告/产品/试验/登记/论文标识、文档角色、标题、来源、落地页/附件链接、所缺关键字段、中文原因和项目内唯一相对收件目录；不得保存机器绝对路径。
- 已接受证据足以关闭关键缺口时，补充材料请求必须为 `not_required`；非阻断统计细节和 B 类试验完成情况不得单独触发用户补件。
- 用户以任意原文件名放入目录后，系统按内容摘要、媒体类型、NCT/DOI/标题识别；规范文件名由试验/文档稳定标识、角色、版本/日期和摘要组成，元数据保留原文件名。
- 错附件、身份歧义、登录/错误 HTML、残缺/不可读文件进入项目隔离区并生成一句可执行的中文说明，不覆盖既有接受来源；之后可生成去重新请求并返回 `awaiting_user`。
- 接受路径必须复用内容寻址库或提供等价原子归档，生成绑定来源版本和缺口的重抽取任务；相同事件重放不重复移动、归档、事件或重抽取任务。
- 精确三测试、Task 3.1/3.2 回归、全量 pytest、Ruff、严格 mypy、schema 校验和包校验通过；独立审查 P0/P1 为零后才接受。

## Risk Boundaries

- 只能修改本项目工作树和 pytest 临时目录；不得触碰真实项目证据库或生产路径。
- 不做安全测试；路径约束、原子性和不覆盖是用户资料完整性/可恢复性功能合同，不扩大为安全工程。
- 不引入第三方依赖；本任务沿用已批准的 Pydantic、pathlib、事件库、内容寻址库。
- 任何无法提取唯一内容标识的文件必须留在隔离区，不能凭文件名或模型猜测接受。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## First-Principles Decision

- 用户的真实目标不是“上传成功”，而是无需理解目录、命名和后端状态也能把受阻报告继续跑下去。因此可见说明只回答：缺哪份资料、为什么现在需要、从哪里下载、放到哪里、下载后无需改名。
- 本任务不需要重新做外部技术选型：已批准架构已固定事件流、内容寻址和项目目录，新增依赖只会增加包可移植性成本；实现应是这些既有原语的最小组合。
- “未获取到文件”必须区分资料确未公开、自动路线技术失败、用户下载文件无效三种情况；本任务只处理第三种以及由第二种升级的精确人工补件，不把它们写成科学上的未披露。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 20:52:22: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-12: Beijing night-window route resolved to `Pi/opencode-go/deepseek-v4-flash:max`; the same session `019ff262-8ff4-7000-8709-4589a92be55c` completed the implementation and two bounded repair rounds without fallback.
- 2026-08-13: Codex reproduced independent-review findings, closed uppercase-extension and crash-replay false greens, added foreign-title and cross-run boundaries, then closed the final typed-error and cleanup P2 items.
- 2026-08-13: Exact Task 3.3 suite 3 passed, existing Phase 3 regression 241 passed, full suite 432 passed; Ruff, strict mypy, schema, package verification and diff checks passed. Two isolated reviewers accepted with P0=0 and P1=0.
