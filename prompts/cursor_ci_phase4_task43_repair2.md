继续原 Task 4.3 Cursor 会话的第二次定向修复。Codex 独立验收发现以下残余假绿；先补真实 RED，再修复，不提交。

Hard boundaries:

- 只在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 工作；保持 Task 4.3，不扩至 4.4/4.5、真实临床数据、PDF/PPT 或安全测试。
- 只返回 runner 交接，由 runner 写 `runs/cursor_ci_phase4_task43_repair2.md`；不要用工具写此文件。
- 用户可见内容保持中文原生，不出现程序员/日志标签。

Read these files only:

- `prompts/cursor_ci_phase4_task43_repair2.md`
- `context/ci_phase4_task43_context.md`
- `.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/architecture/page-catalogs/`
- `src/ci_workflow/reports/common/page_registry.py`
- `src/ci_workflow/renderers/portal/`
- `assets/portal/`
- `tests/unit/test_portal_filter_contracts.py`
- `tests/browser/test_filter_state.py`
- `tests/browser/test_portal_shell.py`
- `tests/unit/reports/test_view_model.py`
- `package-manifest.json`
- `pyproject.toml`

Write exactly one output file: `runs/cursor_ci_phase4_task43_repair2.md` (runner-owned).

必须修复并机械验收：

1. Python 目前仍接受 `v1~pid=%2Fnot-in-catalog` 和 `m=made-up`。页面必须匹配冻结 A/B/C 静态路由或其动态产品/试验详情路由；模块必须来自冻结目录 `filter_profiles`。`PageFilterScope`、`ModuleFilterState`、`decode_filter_state` 均不能只校验格式。目录外页面/模块中文失败关闭；静态和合法动态路由正例要覆盖。
2. 浏览器 `parseHash` 当前接受任意 `v*`、单个不匹配当前页的 `pid`，并对 `s/a/e/pg` 直接 continue。必须：仅接受 v1；pid 必须等于页面 DOM 的 `data-page-id`；全局段分别解析、拒绝重复/畸形/非法方向/非正页码/重复证据，并原样规范化保存在内存；任一筛选选择/移除/重置后 `buildHash` 仍保留 sort、anchor、evidence、page。增加“载入带全局状态网址→操作筛选→复制/刷新/后退前进后全部仍在”的真实浏览器测试。
3. 当前 UTF-8 上限浏览器测试只是测试脚本自行计算并写提示，没有调用产品 `writeFilterToHash`，是假绿。改为通过真实筛选点击触发产品路径（可在 synthetic fixture 增加一个超长稳定 ID 选项或等效真实 DOM 事件），断言 hash 完全保持、选项不丢、提示出现。不要在测试里手工设置提示文字冒充产品行为。
4. 坏网址恢复后保持当前页面原有状态；需测试在已有合法筛选状态下导航到坏 hash，已有 UI 不被部分清空或污染。未知/重复全局字段同样显示“无法恢复此筛选网址”。

运行聚焦单测、完整 filter browser、Task 4.2 回归、Task 4.1 视图测试、ruff、mypy strict、package verify、全量 pytest。报告区分此次实际修改、RED 失败数量、最终 exact 计数和残余不确定性，结尾 `NO_COMMIT`。
