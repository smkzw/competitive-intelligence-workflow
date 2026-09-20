这是同一会话的定向复审，不要重启任务、不要新开会话。Codex 已接受你上一轮的主要反对意见并完成修复，请重新读取磁盘当前状态，不要沿用旧摘要作结论。

Hard boundaries:
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`, plus the one explicitly listed canonical install root in read-only mode.
- Read these files only: the paths listed below and the already authorized Task 9.5 context and plan.
- Write exactly one output file: `runs/conference/ci-phase9-task95-candidate-bundle-review/general_single_object.md`; runner-owned, return it and do not write it with tools.
- Read-only; no source, artifact, installation, or external-state changes.

只读复核以下当前证据；不得修改文件：

- `src/ci_workflow/application/host_smoke.py`
- `src/ci_workflow/application/host_smoke_scenario.py`
- `src/ci_workflow/application/host_smoke_runner.py`
- `src/ci_workflow/application/fresh_install.py`
- `tools/install_bundle.py`
- `skills/competitive-intelligence-workflow/SKILL.md`
- `docs/user-guide/install.md`
- `docs/acceptance/host-smoke/{archive.json,batch.json,codex.json,hermes.json,omp.json}`
- `tests/hosts/test_fresh_install.py`
- `fixtures/catalog.yaml`
- 当前候选包 `dist/competitive-intelligence-workflow.tar.zst` 及 sidecar
- 规范候选安装根 `/Users/smkzw/.cc-switch/skills/clinical-research/competitive-intelligence-workflow`（只读）

重点逐项核实上一轮缺陷是否已闭合：

1. 真实宿主路径是否现在完整证明初始证据阻断且零草稿、固定补件、显式重开与重新绑定、最终站点式 HTML、项目验证和摘要绑定。
2. 宿主提示是否已删除精确 fixture argv 的 spoon-feeding，改由已安装公共 Skill 自行发现入口与步骤。
3. `tools/install_bundle.py`、中文安装说明和验收说明是否已进入候选包内容闭包。
4. `archive.json` 是否绑定当前 dist 摘要、包清单摘要、当前 case digest，并且测试失败关闭旧归档。
5. 是否已安装到规范 `.cc-switch` 根，三宿主是否为真实 PATH 入口、不同进程/会话/运行，且 `batch.real_host_pass=true`。
6. Hermes 首次因默认提供方端点 404 技术失败后，是否沿用同一会话 `20260901_094921_a92463` 切换到可用模型完成，而非新建会话或把技术故障误写成无资料。
7. 首版是否固定站点式 HTML，不再向用户询问 PDF/PPT。

当前候选包 SHA-256 应为 `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`；聚焦测试当前结果为 `63 passed, 1 skipped`，ruff 与目标 mypy 均通过。请自行核实关键事实，不得仅采信这些声明。

返回完整更新后的既定 Markdown schema，并给出明确的复审结论：可接受、仍需修复，或因哪一项证据不足无法判断。Codex 仍是最终验收者。
