# Codex Conference Review: ci_phase0_task04_package_cli

Date: 2026-08-11

## Verdict

**PASS** — 仅接受 Phase 0 Task 0.4 的包根清单、一个公开 Skill、15 个内部能力边界、中文 CLI 骨架和未实现能力失败关闭。P0=0，P1=0；不接受任何 Phase 1 以后业务能力，也不把 Python wheel 冒充 Task 9.5 最终跨宿主 Skill bundle。

## Boundary Compliance

- 参与者只读检查当前新工程；临时项目和变异副本只放在 OS 临时目录，没有改动生产文件或旧工程。
- 初始 Pi 日间有效路由为 `cms-smk/cms-model`；Grok 使用原生 Grok Build，不经 Hermes。
- Grok Build 同一 session 三次均为 `stopReason=cancelled` 的进度句，未计验收；恢复耗尽后依声明顺序使用 Cursor，再因 Ask 模式拒绝 Shell 而使用第二 fallback `cms-router/minimax-m3`。
- Pi 修复后第一次续跑因时间路由把 resume 清空，实际生成新 session；Codex没有把它冒充同会话复核，随后直接使用原有效 route 恢复原 session 并完成终态确认。
- 没有提前实现 Task 1、Task 9.5、A/B/C 报告、PDF/PPT 或安全专项。

## Participant Outputs Reviewed

- Pi 初审：session `019fefba-eb43-7000-8356-de4cd0f7b6b5`，发现安装语义边界、英文 argparse、CLI 目录和提示词假绿风险；报告摘要 `52813162dc98043673654680f8567df42505e4b9441404c4b349afb01c874f8e`。
- Pi 原 session 终态复核：同一 session `019fefba-eb43-7000-8356-de4cd0f7b6b5`， focused 6 项、全量 53 项、两个变异与中文交互均通过；报告摘要 `5b69d7ee17849123510040d3ee5905998433bfbe91477443cb6dce926a2260e7`。
- Grok Build：session `c27fa169-1486-4f42-a661-72f63d328231`，初始及两次同 session 恢复均取消，仅有进度句，不计质量结论。
- Cursor 第一 fallback：session `c9f05959-dd08-49da-978b-a6e0dd7ee04c`，完成静态审查但所有 Shell 被 Ask 模式拒绝，只用于提出 CLI catalog/prompt runtime 假绿，不计独立执行 PASS。
- Minimax 第二 fallback：session `019fefc8-703d-7000-b1cb-cf7bac8962ff`，新鲜上下文真实执行 53 项全量、Ruff、mypy、项目创建/校验、deferred/alias 与两类变异，P0=0、P1=0；报告摘要 `52a063861a55ccabd0b9c1afa223af2785fe88478b0744abdd5ec3b8aa4a21d7`。

## Conference Panel Review

会商发现并关闭三类当前阶段假绿：

1. `schemas/package-manifest.schema.json` 原先只要求 CLI 目录至少 6 条，允许未经批准的第 7 条；现以有序 `prefixItems`、`minItems=maxItems=6`、`items=false` 固定唯一目录，运行时再与 `EXPECTED_CLI_CATALOG` 精确比较。
2. `tests/contract` 会检查 `$skill-id`，但真实 `package verify` 原先不会；现公开入口和 15 个内部 Skill 都在运行时复核默认提示绑定，临时去掉 `$monitoring` 会退出 2 并给出精确中文原因。
3. deferred 命令测试原先只断言非零，argparse 退出 2 也可能假绿；现明确要求四条命令均退出 3，并同时含机器代码与中文说明。

同时将 CLI 的 argparse 固定英文帮助和错误改为中文原生的 `用法/命令/选项/参数错误`。Python wheel 只承载 CLI 模块；批准计划在 Task 9.5 由 `tools/build_bundle.py` 生成、自校验并 fresh-install 完整 `.tar.zst` Skill bundle，因此 wheel 未含 Skills/合同/资产被记录为阶段边界，不作为 Task 0.4 缺陷，也不允许以后用 wheel 代替 Task 9.5 验收。

## Main-Venue Codex Review

- 首轮 RED：包清单 extra CLI 与运行时 drift 测试确实 2 failed；修复后 focused 4 passed。
- 最终主会场：Ruff `src tests` 通过；mypy strict 对 3 个源文件通过；全量 53 passed。
- `uv run ci-workflow package verify --root .` 输出 `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4`。
- `uv build --clear` 成功生成 sdist 和 wheel；主动检查 wheel 仅含 `ci_workflow` CLI 模块，与 Task 9.5 bundle 阶段边界一致。
- 根帮助、缺参数、禁止别名、项目创建/校验、deferred normal/resume 路径均由主会场或独立参与者实际执行。
- Skill Creator 初始化器在生成 16 个标准目录后其系统目录被外部刷新移除；项目用确定性合同补齐名称、描述、界面提示和内部不可隐式调用检查，没有伪称执行已不存在的 `quick_validate.py`。

## Codex Independent Verification

上述测试、构建、CLI 与包校验均由 Codex 在当前工作区亲自执行；Pi 原 session 与 Minimax 分别提供了独立、可执行的交叉证据。Cursor 的静态报告和被取消的 Grok 输出未被当作完成证据。没有执行浏览器/PDF/PPT 验收，因为 Task 0.4 不生成这些报告产物。

## Final Decision

Task 0.4 接受，允许在提交和阶段清理后进入 Task 1.1。Task 9.5 必须继续承担完整 `.tar.zst` bundle、fresh install 和 Codex/Hermes/OMP 三个真实宿主入口验收，不能以当前 Python wheel 或源树绿灯替代。
