All verified. Final report follows.

---

# Execution Output: ci_phase4_task46_execution - worker_03 (修订)

## Boundary And Context Check

- Worked only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`; modified only the four allowed files: `src/ci_workflow/qc/browser.py`, `src/ci_workflow/qc/__init__.py`, `tools/verify_portal.py`, `tests/acceptance/test_portal_runtime.py`.
- Read list honored: `AGENTS.md`、`context/ci_phase4_task46_execution_execution_context.md`、`plans/codex_execution_ci_phase4_task46_execution.md`、四个允许修改文件、`manifest_store.py`、`snapshot_store.py`、`domain/ids.py`。未读其他文件，未触碰生成站点/快照/清单/无关代码；`qc/__init__.py` 仅保留 worker_01 的早期 docstring 修改（未动）。
- 未做安全测试、未访问外网、未修改被验收项目；验收器保持只读（加载器只读不写；只读保证测试已扩展到站点 + 清单 + 快照全部字节）。
- 未执行最终视觉/渲染验收（Codex 权威）。报告文件 `runs/execution/ci_phase4_task46_execution/worker_03_followup.md` 未用工具写入，按要求在本响应返回。

## Work Performed

**P1 假绿修复（锁定站点地图来源）：**

1. `src/ci_workflow/qc/browser.py` 新增只读、失败关闭的锁定来源加载器（末尾新章节，~200 行）：
   - `LockedSitemapSourceError`、`LockedSitemapSource`（dataclass：`ArtifactManifest` + `ReportSnapshotManifest` + `product_ids`/`trial_ids`）、`site_directory_digest(site_root) -> (sha256, byte_size)`（路径+NUL+字节整体摘要，与产物清单同一合同）、`load_locked_sitemap_source(project_root, report, version)`。
   - 核验链（全部使用现有模型与语义，未复制弱模型）：① `html.manifest.json` 存在、可解析、符合 `ArtifactManifest`，报告/版本匹配，状态非 `failed`/`superseded`，`artifact.relative_path` 正是 `reports/<报告>/<版本>/html`；② 引用快照 `snapshots/reports/<报告>/<report_snapshot_id>.json` 存在且符合 `ReportSnapshotManifest`；③ 按 SnapshotStore 同一规范 JSON（排序、紧凑、中文不转义、末尾换行）重算摘要与 `stable_id("report-snapshot", 报告, 摘要)`，与清单身份和文件名一致；④ 报告/版本/项目/合同版本/数据截止/证据快照/声明快照/覆盖集/声明集合绑定一致；⑤ 站点目录当前摘要与汇总字节数 == 清单 `artifact.sha256`/`byte_size`，不一致在启动浏览器前失败关闭。全部通过后返回清单记录的产品/试验标识。
2. `tools/verify_portal.py`：删除 `--product`/`--trial` 参数及本地 `_site_digest`；主流程改为「输入校验 → `load_locked_sitemap_source`（失败中文说明退出 2）→ `derive_sitemap_contract(source.product_ids, source.trial_ids)` → 站点地图一一对应 → 运行时验收」；`site_digest` 直接用已核验的 `manifest.artifact.sha256`；`report.json` 增加 `manifest_id`/`report_snapshot_id`；文档中「站点地图闸门」改为「站点地图一一对应」，移除程序员式标签；失败/帮助/结论文案均为中文临床业务原生表达（核对：无 门/信号/后端/日志）。
3. `tests/acceptance/test_portal_runtime.py`（+6 净节点，55 总）：合成夹具 `_build_task46_project` 现在真实写入锁定报告快照（规范 JSON 内容寻址 + `stable_id`）与**完整** `html.manifest.json`（经真实 `ArtifactManifest.model_validate` 校验后写入，含全部字段与通过态验收记录），无 mock；`_write_locked_report_artifacts` 可在篡改后重新绑定清单。新增黑盒测试：无 `--product/--trial` 的计划命令成功；缺清单、缺快照、快照绑定不一致、站点摘要过期均退出 2 且中文可操作；清单漏实体 → 站点地图拒绝额外路由；移除身份参数的拒绝测试；只读保证扩展到清单与快照。
4. 重复语句核查：`_run_browser_acceptance` 中 `page.screenshot` 现为 **1 处**（每路由×浏览器×视口恰一次，`grep -c` 确认）；疑似为评审时中间态，当前已无重复，未改动该调用。

## Artifacts And Evidence

| 文件 | 变更 | 证据 |
|---|---|---|
| `src/ci_workflow/qc/browser.py` | +锁定站点地图来源加载器（docstring 更新） | RED ImportError → 全绿；strict mypy 通过 |
| `tools/verify_portal.py` | -`--product/--trial`/-`_site_digest`；+加载器接线；+report.json 清单/快照身份 | 计划命令真实运行 exit 0；`--help` 无 product/trial |
| `tests/acceptance/test_portal_runtime.py` | 夹具真实写锁定快照+完整清单；+6 节点 | `55 passed in 108.32s` |
| `src/ci_workflow/qc/__init__.py` | 未修改（worker_01 早期 docstring 保留） | git status ` M` 原样 |

## Commands And Observations

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/acceptance/test_portal_runtime.py -q`（改测试后、实现前） | **RED**：`ImportError: cannot import name 'load_locked_sitemap_source'` |
| 确定性子集 `-k "cli_rejects or fails_closed or plan_command or extra_route or sitemap_gate"` | 28 passed（首次修复后） |
| `uv run pytest tests/acceptance/test_portal_runtime.py -q`（实现后、格式化后各一次） | **55 passed in 108.32s**（两次均 55，格式化无语义变化） |
| `uv run ruff check` + `ruff format --check`（4 文件） | 1 处 F401（测试文件未用导入）修复后 All checks passed |
| `uv run mypy src/ci_workflow/qc/browser.py tools/verify_portal.py` | `Success: no issues found in 2 source files`（strict） |
| `uv run mypy src/` | `Success: no issues found in 84 source files` |
| 相邻回归 `tests/unit/reports/test_view_model.py tests/contract/test_coverage_set.py tests/acceptance/test_html_ppt_runtime_smoke.py` | 69 passed |
| 真实 CLI（计划命令，chromium-only，scratch 夹具） | exit 0，`全站验收通过…` + `A_PORTAL_OK routes=16 browsers=1`；report.json 含 `manifest_id`/`report_snapshot_id` |
| 真实 CLI 失败路径 | 站点改写 → exit 2「报告站点摘要与清单不一致：站点产物可能已被改写，请重新生成该报告版本后重试。」；删清单 → exit 2「报告站点清单不存在：…html.manifest.json。请确认 --project 与 --version 指向已生成的门户产物…」 |
| `grep -c page.screenshot tools/verify_portal.py` | 1（唯一） |

## Blockers Or Missing Environment

None。未安装包、未访问外网、未写生产/站点/清单/快照；scratch 证据目录已清理。

## Rerun Requests Or Next Step

- Codex 验收：`uv run pytest tests/acceptance/test_portal_runtime.py -q`（55 节点）为单一总闸；随后 `uv run ruff check`（4 文件）、`uv run mypy src/` strict、相邻 69 项回归均已在本次通过。
- 待办（超出本修订范围，Codex 权威）：真实 Phase-5 管线按同一合同写入 `html.manifest.json`（站点目录摘要/字节数 = `site_directory_digest` 合同）与锁定报告快照；Phase-5 项目上以 `--browser chromium --browser webkit --all-routes` 复跑；提交与 `cleanup-execution` 归档。
