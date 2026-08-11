All my temp files removed; the working tree contains only the implementation's own uncommitted changes. I have everything needed. Compiling the final report.

**SOUL.md read status:** I read the file across three reads covering lines 1–268 (the 200–268 read confirms EOF at line 268). I read the complete file to the end.

---

# Task 1.6 独立验收

## 结论

**PASS**

Task 1.6 通过独立验收。能力预检按用户选择驱动、选择性阻断与恢复重排均符合批准规格与计划 CP01–CP08；11 项精确测试与全库 132 项回归通过；Ruff、strict mypy、包校验、`git diff --check` 全绿；实机 `local` 全矩阵 12 项能力全部真实可用并有可解释证据锚点；选择性阻断/恢复均有非模型锚点（确定性探针测试 + 真实 CLI 执行）。未发现 P0/P1 缺陷。

## 已执行锚点

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/contract/test_capability_matrix.py tests/integration/test_capability_preflight.py tests/integration/test_selective_capability_blocking.py -q` | **11 passed** (0.64s) |
| `uv run pytest -q` | **132 passed** (5.84s) |
| `uv run ruff check src tests` | All checks passed (exit 0) |
| `uv run mypy --strict src` | Success, 20 source files (exit 0) |
| `uv run ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` (exit 0) |
| `git diff --check` | exit 0 |
| `uv run ci-workflow capability preflight --host local --reports A,B,C --outputs html,pdf,html-ppt,pptx --json .artifacts/reviewer-preflight.json` | `PREFLIGHT_COMPLETE`，overall_state=`ready`，`PREFLIGHT_EXIT=0` |

实机预检摘要（`local`、A/B/C × html/pdf/html-ppt/pptx）：12/12 能力 `ready`，无 `blocked`/`not_applicable` 之外的意外状态；`ppt_master`=`ready`（发现 `~/.cc-switch/skills/ppt-master/SKILL.md`）、`office_renderer`=`ready`（发现 `/Applications/Microsoft PowerPoint.app`）、`native_pdf`=`ready`（reportlab+poppler）、`html_ppt_runtime`=`ready`（`assets/html-ppt/manifest.json`）、`browser_validation`=`ready`（真实 Chromium 渲染）、`http_network`=`ready`（ClinicalTrials.gov 返回 200）。`login_browser`/`ocr`=`not_applicable`（未选择对应来源/无 OCR 需求）。该 JSON 通过 `schemas/capability-matrix.schema.json`（Draft 2020-12）校验。

## P0/P1 缺陷

无

## P2/P3 观察

范围内、可复现、真实，均不阻断：

1. **`http_network` 实机探针依赖外网且偶发超时**（`capability_preflight.py:218-225`，`_check_real` 中 `urlopen(..., timeout=5)`）。本机一次运行中 CT.gov 连接超时导致 `http_network` 被记为 `blocked`、`research:A=blocked`、`overall_state=blocked`。这是真实网络抖动而非实现缺陷——探针正确走中文失败路径（detail「无法连接 ClinicalTrials.gov」、action「请确认网络可用；Agent 会在恢复后只重试尚未完成的来源」），且随后重跑恢复正常。属预期行为，不影响验收。
2. `office_renderer` 探针把 LibreOffice/soffice 也视为可用 Office（`capability_preflight.py:283-288`），与 PPTX 的「PPT Master 串行生成」契约存在轻微语义跨度——预检只验证「有可做验收的 Office」，不验证所生成 PPTX 的编辑性。属 P3 语义观察，不是实现缺陷（规格 §6.2 只要求预检能力可用性）。

## 假通过攻击结果

对照 8 项逐条：

**1. 未选择来源/OCR/PDF/HTML-PPT/PPTX 不检查不阻断；HTML 始终包含。**
通过。`_applicable_capabilities`（`capability_preflight.py:369-395`）仅把来源/OCR/格式加入 `applicable`；未加入的能力在 `run_capability_preflight` 中置 `state="not_applicable"`（`capability_preflight.py:525-533`）。实测：`--source-routes public-http` 时 `search_browser`/`login_browser`=`not_applicable`；仅选 pdf 时 `html_ppt_runtime`/`ppt_master`=`not_applicable`。HTML 默认包含：内联路径把 `outputs` 强制规整为 `["html", ...]`（`cli.py:349-351`）；实测仅 `--outputs pdf` 输出 `selection.outputs=["html","pdf"]`。测试覆盖：`test_preflight_checks_http_and_browser_only_for_selected_source_routes`、`test_preflight_checks_pdf_document_and_ocr_only_when_required`、`test_preflight_checks_native_pdf_for_selected_pdf_output`。

**2. 缺 PPT Master/Office 只阻断 PPTX；缺网络/OCR 影响正确报告及其下游，不误判已通过格式失败。**
通过。`_delivery_dependencies`（`capability_preflight.py:409-416`）使 pptx 只依赖 `ppt_master`+`office_renderer`；实测 `overrides={"ppt_master":False,"office_renderer":True}` 时 html/pdf=`ready` 而 pptx=`blocked`。缺 `http_network` 阻断全部 research 及所有 delivery（通过 `_research_dependencies` 传播），`research:A=blocked`、`overall_state=blocked`——正确，因为研究是共同前提。缺 OCR（`--require-ocr`）类似传播到 research→delivery。测试：`test_preflight_checks_ppt_master_and_powerpoint_for_selected_pptx_output`、`test_missing_pptx_capability_blocks_only_pptx_and_gives_plain_chinese_guidance`。

**3. 项目合同与内联入口给出相同 selection/capabilities/research/deliveries/overall_state；双入口或双缺中文失败关闭。**
通过。`test_cli_project_and_inline_selection_produce_the_same_capability_summary` 断言 5 个字段全等；`selection_from_project` 与内联路径都经 `CapabilitySelection` 归一。实测双入口（`--project`+`--reports`）与双缺均输出 `CONTRACT_ERROR 请在项目目录和内联报告选择中任选一种，不要同时填写`、exit 2；缺 `--json` 输出中文参数错误、exit 2。测试覆盖：`test_selective_capability_blocking.py` 第一项 + `test_cli_command_catalog.py`。

**4. 能力矩阵 12 个唯一能力、A/B/C × 所选格式笛卡尔积；重复/缺失/伪造总状态或引用未阻断能力双合同失败。**
通过。schema 强制 `capabilities` minItems/maxItems/uniqueItems=12、`deliveries` 唯一；`CapabilityMatrix._matrix_is_complete_and_internally_consistent`（`capability_preflight.py:301-367`）强制清单完整唯一、deliveries 精确等于所选报告×格式笛卡尔积、`overall_state` 与 research/deliveries 状态一致、`blocked_by` 只引用已阻断能力。`test_capability_matrix_schema_matches_the_typed_runtime_contract` 构造重复能力同时触发 JSON Schema 与 Pydantic 校验失败。

**5. 环境修复只重排已修复能力及已解除全部阻断的下游；仍有另一能力阻断时不提前重排；研究恢复含分析、快照、渲染、验收下游。**
通过。`plan_environment_recovery`（`capability_preflight.py:598-640`）：`repaired` 仅取前 blocked→现 ready 的能力；对每个 `required_by` 下游，只有在当前 research/delivery 已是 `ready`（即全部阻断已解除）才加入 `requeue_node_ids`。实测：fix ppt 而 office 仍 blocked → `repaired=('ppt_master',)` 但 `requeue=()`（不提前重排）；fix 两者 → requeue `render:A:pptx,verify:A:pptx`。研究修复（http 恢复）→ requeue `research/analyze/snapshot:A` + 各格式 `render/verify:A:*`。测试覆盖：`test_environment_recovery_requeues_only_failed_capability_and_downstream_nodes`。

**6. `CI_WORKFLOW_CAPABILITY_OVERRIDES` 仅显式测试模式生效。**
通过。`RuntimeCapabilityProbe.__init__`（`capability_preflight.py:190-198`）仅在 `CI_WORKFLOW_TEST_MODE == "1"` 时读取 override，否则置空。实测：不带测试模式设 `CI_WORKFLOW_CAPABILITY_OVERRIDES='{"ppt_master":true,...}'` → `ppt_master` 仍走实机探针（本机 ready 是真实发现，非 override 假绿）；同命令 `http_network` 因真实网络超时被记为 blocked，证明 override 未生效。测试：`test_selective_capability_blocking._run` 显式设置 `CI_WORKFLOW_TEST_MODE="1"`。

**7. 真实探针失败中文说明「哪项不可用、影响什么、用户下一步」，非异常类/后端标签/gate/signal/纯英文；PPT Master+Office 同时缺失合并为一条。**
通过。`_failure_detail` 给出中文 detail，`CAPABILITY_ACTIONS` 给中文下一步；`_user_messages` 对 ppt_master+office 生成单条「可编辑 PPTX 暂时无法生成：…；HTML 不受影响。」实测合并输出恰好 1 条该类消息。测试断言 `"gate" not in stdout.lower()` 且 `"signal" not in stdout.lower()`。实测 OCR 失败 detail「扫描件文字识别暂时不可用」+action「请恢复扫描件文字识别能力；可正常读取的文本资料不受影响。」——中文、含影响与下一步。

**8. 实机矩阵非全可用时区分真实环境缺失与实现缺陷。**
通过。本机全矩阵 12/12 `ready`，无技术阻断；预检 JSON 与 schema 一致，无静默忽略。偶发 `http_network` 超时（见 P2/P3 #1）被正确判定为真实环境网络抖动而非实现缺陷，且恢复路径已验证。未以「命令退出 0」单独作为通过依据——上述 8 项均以确定性测试 + 真实 CLI 输出锚定。

## 接受建议

**接受 Task 1.6。** 无 P0/P1，11 项精确测试与全库 132 项回归通过，Ruff/strict mypy/包校验/diff-check 全绿，实机矩阵 12/12 可用且有真实探针证据，选择性阻断/恢复均有确定性测试 + 实机 CLI 锚点。

Codex 接受前复核下列事项（均非阻断）：
- 确认 `http_network` 实机探针依赖外网是预期（离线/内网环境会把研究标记 blocked，属保守正确而非假失败）。
- 复核 `office_renderer` 把 LibreOffice 视为可用 Office 的语义口径（P3），确认它只承诺「有可做验收的 Office」而非「可编辑 PPTX 编辑性」。
- 确认 `.artifacts/reviewer-preflight.json`（我按必执行命令生成的临时产物）已删除、不进入提交；工作树仅含实现本体的未提交改动。

**SOUL.md 读取说明：** 已完整读到文件末尾（共 268 行，末次读取覆盖 200–268 行并确认 EOF）。
