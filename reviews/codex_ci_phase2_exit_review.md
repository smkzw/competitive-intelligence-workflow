# Codex Review: ci_phase2_exit

Date: 2026-08-12
Delegated-agent outputs:

- `runs/codex-subagent_ci_phase2_exit.md`
- `runs/codex-subagent_ci_phase2_exit_followup.md`
- `runs/codex-subagent_ci_phase2_exit_followup2.md`
- `runs/codex-subagent_ci_phase2_exit_followup3.md`

## Verdict

**PASS：Phase 2 accepted。P0=0、P1=0、P2=0。**

该结论只接受创新药宇宙、来源路由、证据恢复、精确定位及版本化事实—声明链，不提前接受 Phase 3、真实全量竞品调研或报告质量。

## Boundary Check

- 验收者在 Luna/max 只读环境运行；产品工作树未被验收者修改，四份报告由 runner 写入既定 `runs/` 路径。
- 最终窄复核只读指定实现、测试和上轮报告，未扩展到 Phase 3，未进行安全测试。
- 原生 Luna 能力探测明确拒绝该模型后，按全局约定使用 CLI 兼容路线；全部四轮复用会话 `019ff1d8-8ee4-79e1-b5fe-2aebb063e0be`，未因延迟重派或更换模型。

## Codex Verification

- 正式 Phase 2 套件：61 passed。
- 全库：188 passed；Ruff 通过；strict mypy 45 个源文件通过；包校验输出 `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`；`git diff --check` 通过。
- ClinicalTrials.gov 官方 API 录制锚点为 NCT02912468；样本量 276，两组背景治疗、主要终点 -0.45/-1.34、分母 133/143、首次结果 2019-07-25、PMID 31543428 均经来源链重建。
- 最终报告摘要：`48cf68a2d350ff51d07a2c1175a61f9799ac51127b4f92b3d8bf76f4ff75af9a`；录制 fixture 摘要：`f497d57cb1d4dacf9f52ce015d12ff33d7c9dc43b0b788d3792d03e4ca38b1b1`。

## Delegated-Agent Output Review

独立验收没有用正向 fixture 代替反例验证。前三轮发现的 23 个 P1（每轮为当时剩余数，不作简单累加）均由同一会话复核；最终逐项重放六类残余反例，确认路线尝试与回执逐字段一致、技术失败不能伪装科学穷尽、公众号必须定位完整段落、中国自然日必须为 `+08:00`、声明不能接受调用方伪造事实上下文、科学证据必须从 SQLite 与内容寻址正文真实重开。

只读隔离环境无法创建临时目录，导致八项 `tmp_path` 测试在 setup 阶段报错；验收者将其与科学断言失败分离，并在不依赖临时目录的子集重放 22 项。父 Codex 在可写项目环境完整执行 61/188 项，因此该环境限制不构成产品缺陷。

## Residual Risk

- Phase 2 录制 fixture 证明单个真实来源跨层链路，不等同于真实适应症全量竞品调研。
- Phase 3 必须继续对关键证据不足时不生成草稿、下载补件与自动归档、科学质量否决和恢复机制进行独立验收。
- 报告门户、动态筛选、中文原生表达及四格式视觉质量均尚未进入接受范围。
