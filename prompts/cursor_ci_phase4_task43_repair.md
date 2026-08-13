继续同一 Task 4.3 会话。父级 Codex 已对候选实现做独立反例测试；自带测试虽绿，但以下失败已在当前文件系统真实复现。请在原范围内执行修复，不提交，最后返回可审计的执行报告。

Hard boundaries:

- 只在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 工作；不提交、不改 Task 4.1/4.2 已接受合同，不实现 Task 4.4/4.5、真实临床数据、PDF/PPT 或安全测试。
- 仅将完整交接报告返回给 runner，由 runner 写入 `runs/cursor_ci_phase4_task43_repair.md`；不要用工具自行写该文件。
- 用户可见内容必须是中文原生临床试验语境，不显示程序员、后端或日志用语。

Read these files only:

- `prompts/cursor_ci_phase4_task43_repair.md`
- `context/ci_phase4_task43_context.md`
- `.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/architecture/page-catalogs/`
- `src/ci_workflow/reports/common/view_state.py`
- `src/ci_workflow/reports/common/page_registry.py`
- `src/ci_workflow/renderers/portal/`
- `assets/portal/`
- `tests/contract/test_filter_contracts.py`
- `tests/unit/test_portal_filter_contracts.py`
- `tests/unit/reports/test_view_model.py`
- `tests/browser/test_filter_state.py`
- `tests/browser/test_portal_shell.py`
- `package-manifest.json`
- `pyproject.toml`

Write exactly one output file: `runs/cursor_ci_phase4_task43_repair.md` (runner-owned).

必须先补 RED 测试并证明失败，再最小修复：

1. `decode_filter_state` 当前静默接受重复 `pid`、同一 `ps` 内重复维度、重复模块 ID、重复 evidence ID，以及 `ps=totally_unknown:a`。这些均须失败关闭并给简洁中文错误。页面维度只允许 `PAGE_DIMENSION_IDS`，模块维度只允许 `MODULE_DIMENSION_IDS`；网址恢复不得因 `dimensions=()` 绕过维度身份检查。
2. `FilterState` 本体须拒绝重复模块 ID；`reset_module("nonexistent")` 不得静默成功，应以中文拒绝未知模块。更新候选测试中相反的错误预期。
3. URL 的稳定 ID 可能含分隔符。采用逐组件 percent-encoding/decoding，或以严格稳定 ID 字符集在模型入口拒绝；须有包含 `/b/overview`、动态详情路由或带保留字符 ID 的往返测试，并拒绝解码后注入额外段。不要靠未经转义的 `~|,:=` 拼接。
4. `select_view_rows` 当前对 `indication`、`target_or_mechanism` 以及多数模块维度直接 `continue`，形成“用户已筛选、实际未筛选”。Task 4.1 的 `ReportRow` 没有这些身份字段时，不能猜造数据：对无法投影的已选维度明确失败关闭；对现有 product/trial/endpoint/timepoint/ae_term 映射完成 OR-within-dimension、AND-across-dimensions 测试。不得静默忽略。
5. 浏览器 JS 当前解析未知/重复字段时静默覆盖或忽略。必须以当前页面呈现明确中文“无法恢复此筛选网址”提示并保持原始 hash，不应用部分状态；未知筛选值、未知维度、重复段、重复维度/值、重复模块都测试。已知页面/模块选项从当前 DOM 构建 allowlist。不得把坏状态转成空状态或重写网址。
6. 浏览器模块筛选只应影响相应模块的行。目前 `rowMatches` 遍历所有模块并作用于所有合成行，需给每行/容器明确 module identity 并测试两个模块互不污染；页面级筛选仍影响全页。保持同维度多选为 OR、跨维度 AND。
7. URL 长度按 UTF-8 字节而非 JS 字符数判定；超限时保持原 hash、不部分写入，并显示“当前选择过多，请保存为本地视图”。Python 同样按 UTF-8 字节计数。

验收：运行聚焦单测、完整 `tests/browser/test_filter_state.py`、Task 4.2 浏览器回归、Task 4.1 视图测试、ruff、mypy src strict、package verify、全量 pytest。任何预期外零行、浏览器差异或失败要追根因。报告要区分你实际修改与前序候选已有修改，并列 exact 命令/计数/截图/残余不确定性，结尾 `NO_COMMIT`。
