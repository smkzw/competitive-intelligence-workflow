# Codex Review: ci_phase1_exit

Date: 2026-08-11
Delegated-agent outputs: `runs/pi_ci_phase1_exit.md`, `runs/pi_ci_phase1_exit_followup.md`

## Verdict

PASS。Phase 1 可以接受并进入 Phase 2；没有提前接受来源检索、证据门槛、科学分析或报告渲染。

## Boundary Check

- 首轮独立验收使用声明的 `Pi/cms-smk/deepseek-v4-flash:max`，session `019ff11d-e558-7000-b72d-c19ccd7c4da0`，无 fallback；评审只读，临时项目在系统临时目录并已清理，runner 仅写其管理的运行报告和原始输出。
- 22:00 后的窄幅文档复核请求恢复原 session，但全局夜间路由把 CMS-SMK 替换为 `Pi/opencode-go/deepseek-v4-flash:max`，runner 明确记录 `resume_session_reset=true` 并产生 session `019ff12d-c9d1-7000-8077-0e798377e314`。这不符合“原底层 session 继续”的理想机制，因此不把补充报告作为同 session 证据；它仅确认文档修订，首轮 PASS 仍是独立接受依据。
- 变更和验收均只发生在新架构独立仓；旧工程、通用康哲 design.md 和外部项目未修改。

## Codex Verification

- 批准的 Phase 1 确定性命令：62 passed；独立 reviewer 复跑同一清单：62 passed。
- 全库：Codex 133 passed；独立 reviewer 133 passed。SQLite 血缘专项 7 passed。
- `ruff check src tests`、`mypy --strict src`（20 个源文件）、`package verify --root .`、Trellis validate、`git diff --check` 均通过。
- 公共 CLI 创建 A/B/C 和 HTML/PDF/HTML-PPT/PPTX 项目，真实能力预检得到 10 项适用能力 ready、登录浏览器/OCR 本次不适用、12 个交付分支 ready；移动并改名后 `project verify` 通过。
- 12 个非 SQLite 持久文件不含原位置或新位置的机器绝对路径；数据库 `integrity_check=ok`、`user_version=8`。
- 三类项目级孤儿记录均被迁移 0008 拒绝；来源四类日期、完整来源回执/证据缺口、证据片段 locator、事件/检查点恢复、不可变证据/报告快照、当前上下文绑定产物清单均有真实运行锚点。
- Codex 本轮真实启动 Chromium 并完成页面渲染探针；Phase 1 不涉及正式报告页面的视觉接受。

## Delegated-Agent Output Review

首轮 Hermes reviewer 给出 PASS，P0=0、P1=0，并独立复现所有决定性检查。其 P2-1“验收记录未保存完整命令”已补齐；补充只读复核确认关闭。另一项关于临时锚点摘要不可独立重算的观察不阻断：临时项目已按清理要求移除，但同一行为由 reviewer 的独立临时项目、确定性测试和当前文件合同共同复现。Reviewer 没有把 Phase 2 功能错误纳入 Phase 1。

## Residual Risk

- 夜间路由切换时 runner 会把恢复请求重置为新底层 session；后续需要在全局执行机制层修正或明确“同逻辑任务/同底层 session”的边界，不能在项目验收中声称同 session。
- Phase 1 只证明宿主能力存在和底层科学真源可恢复；不证明任何真实适应症竞品数据齐全，也不证明正式报告内容和视觉质量。
