# Task 4.6 worker_03 同会话修订

继续原 `worker_03` 会话，只处理 Codex 验收发现的一个 P1 假绿与一处重复语句。不要扩展范围，不要新建会话，不要修改本提示之外的文件。

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Create or modify only the four implementation/test files listed under “允许修改”.
- Runner-managed output path: `runs/execution/ci_phase4_task46_execution/worker_03_followup.md`. Return the report in the final response and never write that file with tools.
- Do not modify generated sites, snapshots, manifests, unrelated code, or global files.

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task46_execution_execution_context.md`
- `plans/codex_execution_ci_phase4_task46_execution.md`
- `src/ci_workflow/qc/browser.py`
- `src/ci_workflow/qc/__init__.py`
- `tools/verify_portal.py`
- `tests/acceptance/test_portal_runtime.py`
- `src/ci_workflow/storage/manifest_store.py`
- `src/ci_workflow/storage/snapshot_store.py`
- `src/ci_workflow/domain/ids.py`

## 必修问题

当前 `tools/verify_portal.py` 通过可重复的 `--product` / `--trial` 参数构造期望站点地图。调用者可少填实体并让缺失详情页假通过，且与实施计划的精确命令不一致。必须改为从当前报告版本的 `reports/<报告>/<版本>/html.manifest.json` 读取 `ArtifactManifest.product_ids` / `trial_ids`，并验证该清单确实绑定项目内不可变报告快照后再构造站点地图。

## 允许修改

- `src/ci_workflow/qc/browser.py`
- `src/ci_workflow/qc/__init__.py`
- `tools/verify_portal.py`
- `tests/acceptance/test_portal_runtime.py`

## 精确合同

1. 删除 CLI 的 `--product` / `--trial`；计划中的原始命令（不含这两个参数）必须成功。
2. 在生产模块实现只读、失败关闭的“锁定站点地图来源”加载器，使用现有 `ArtifactManifest`、`ReportSnapshotManifest`、`stable_id` 语义；不要复制一套较弱模型。
3. 必须验证：
   - `html.manifest.json` 存在、可解析，报告类型和版本匹配；状态不是 `failed` / `superseded`；产物相对路径正是 `reports/<报告>/<版本>/html`。
   - 清单引用的 `snapshots/reports/<报告>/<report_snapshot_id>.json` 存在、符合 `ReportSnapshotManifest`；其报告、版本、项目、合同版本、数据截止时间、证据/声明/覆盖集绑定与产物清单一致。
   - 按 `SnapshotStore` 的同一规范 JSON（排序、紧凑、中文不转义、末尾换行）重算摘要及 `stable_id("report-snapshot", report, digest)`，必须与清单、文件名一致。
   - HTML 目录当前确定性摘要与清单 `artifact.sha256` 一致，汇总字节数与 `artifact.byte_size` 一致；不一致时在启动浏览器前失败关闭，避免旧清单或被改写站点假通过。
4. 合成夹具必须真实写入锁定报告快照和完整 `html.manifest.json`；不得用 mock 绕过。
5. 新增精确黑盒测试：无 `--product/--trial` 的计划命令成功；缺清单、缺快照、快照绑定不一致、站点摘要过期均退出 2 并给出中文可操作说明；清单漏掉已有实体时站点地图应拒绝额外路由。
6. 移除 `_run_browser_acceptance` 内重复的 `page.screenshot(...)`。
7. 用户可见文案必须是中文临床业务原生表达，禁止出现“门/信号/后端/日志”等程序员式标签；内部类名可使用英文。
8. 验收器保持只读，不修改被验收项目、站点、清单或快照。

## 验证

先运行 `tests/acceptance/test_portal_runtime.py`，再运行 Task 4.6 相邻验收测试、Ruff 与 strict mypy。记录失败原因与修复，不得只报告“流程跑通”。最终按原执行输出结构返回紧凑修订报告，由 runner 持久化。
