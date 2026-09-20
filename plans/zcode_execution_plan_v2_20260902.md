# 竞品调研工作流 · 剩余工程执行计划 v2

- 日期：2026-09-02
- 编制：ZCode（依据工程审计 `reviews/zcode_ci_engineering_audit_20260902.md`、设计升版 `docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md`、路线图 `plans/zcode_revised_roadmap_20260902.md`）
- 效力：取代原实施计划（2026-08-10）中自 Task 10.6 起的剩余任务分解；原计划 Phase 0-9 的任务定义、验收记录与已完成检查点保持历史效力。Task 10.6 的 PRD/design/implement 四阶段框架继续有效，本计划在其中注入范围与合同修订。
- 每个代码任务维持原 TDD 纪律（先 RED 后 GREEN、精确测试集合、真实锚点、独立验收）；每任务收尾过 gate 并显式提交（见 §1.1）。

---

## 0. 计划合同更新

1. 权威依据顺序：用户 2026-09-02 两轮裁决 → 设计 v1.3（升版增量）→ 本计划 → v1.2 规格未被 v1.3 修订的部分 → 原实施计划历史部分 → 康哲合同 → 审计报告（作为证据与裁决依据，非规范）。
2. 原 §3.3 用户会商点追加：release-scope 的任何再变更（恢复格式/恢复监测）为用户会商点。
3. 原 §0.5 完成定义修订：首版切换门槛为 `FINAL_ACCEPTANCE_OK reports=3 formats=1 hosts=3 scenarios=<n> recovery=passed legacy_absent=passed`；四格式表述全部按 formats=1 理解。

## 1. 全局纪律修订（立即生效）

### 1.1 gate 命令（唯一绿灯口径）

```bash
uv run ruff check src tools tests \
  && uv run mypy --strict src/ci_workflow \
  && uv run pytest tests/unit tests/contract -q \
  && uv run python tools/check_no_legacy_refs.py
```

- 实现为 `tools/gate.sh`（或 Makefile 等价物），退出码聚合。
- 任何 worker 报告/任务验收声称"质量门通过"必须附 gate 全量输出（或其 digest）；execution metrics 模板增加必填字段"声明的检查范围"。
- mypy/ruff 范围即上述命令全集，禁止缩小口径后声称通过。

### 1.2 git 纪律

- 任务收尾时 `git status --porcelain` 仅剩白名单路径（`runs/`、`logs/`、`tmp/`、`Products/`、`.artifacts/`、`dist/` 及运行期生成物，均应已被 .gitignore 覆盖后不出现）。
- `.gitignore` 追加：`runs/`、`logs/`、`tmp/`、`Products/`、`spikes/`（保留 `docs/acceptance/` 下被验收引用的截图）。
- workflow.md 的 workflow-state enforcement 块与 `task.py finish` 钩子加入上述检查（fail-visible，不自动提交）。

### 1.3 证据分层保留（约束 C3）

- 全量运行产物/日志只落 `runs/`、`logs/`（gitignore，按任务归档压缩）；`reviews/` 只存 digest+指针+抽样截图；同门户迭代禁止全量复制目录（增量或内容寻址）。
- 视觉会商每任务上限 2 轮；第 3 轮起改为主 Agent 直修 + 单验证者复核，并在 metrics 记录升级原因。

## 2. R0 工程修复（P0，第 1 周，一切续接工作的前置）

### R0.1 建立 gate
**Files:** `tools/gate.sh`、`pyproject.toml`（如需 pytest marker）
**Steps:** 实现命令聚合；先在当前树运行记录 RED 基线（77 mypy 错等）；写入 docs/decisions。
**验收:** gate 在修复前可运行并正确非零退出；脚本本身 ruff/mypy 干净。

### R0.2 修复全仓类型与 lint 错误
**Files:** `src/ci_workflow/renderers/pdf_native/**`（~35 错）、`renderers/portal/report_b.py`（8）、`renderers/pdf_native/flowables.py`（8）、`renderers/html_ppt/projections/a_pages.py`（7）、`application/run_service.py`（4）等 19 文件；`tests/acceptance/test_r13_visual_contract_static.py`（import 排序）
**Steps:** 按文件逐个修复，禁止 `# type: ignore` 掩盖（确需 ignore 的逐条注释理由并计数 ≤5）；每修完一组跑 `pytest tests/unit tests/contract -q` 防回归；pdf_native 系修复后运行其聚焦测试。
**验收:** gate 全绿（mypy 0 错、ruff 0 错、unit+contract 全过、`LEGACY_REF_OK`）。

### R0.3 分组快照提交 6 天积压
**Steps（建议提交序列，全部 `git add <显式路径>`，禁止 `git add .`）：**
1. `fix: restore strict typing across renderers`（R0.2 的修改）
2. `feat: report B portal complete`（Phase 6：reports/b、renderers/portal/report_b、templates/b、tests）
3. `feat: report C portal complete`（Phase 7 同理）
4. `feat: native pdf html-ppt pptx renderers`（Phase 8：pdf_native、html_ppt、pptx_master、tests/pdf、tests/office）
5. `feat: correction refresh host adapters bundle`（Phase 9：application/{correction,refresh}_service、hosts、tools/build_bundle 等）
6. `feat: acceptance matrix cutover tools r13 outputs`（Phase 10：acceptance_runner、legacy_cutover、run_acceptance、fixtures/acceptance）
7. `chore: schemas policies fixtures updates`
8. `chore: governance records phase 6-10`（metrics/reviews/plans/context 中需入库部分）
9. `docs: v1.3 design addendum release scope roadmap`
**验收:** 提交后 `git status --porcelain` 仅剩白名单；`git log` 时间线与 .trellis 任务序列一致；无用户文件被重置/覆盖（对比提交前后文件数）。

### R0.4 git 白名单钩子
**Files:** `.trellis/workflow.md`（enforcement 行）、`.trellis/config.yaml`（after_finish hook）、`tools/check_clean_tree.py`（新增）
**验收:** 构造脏树调用 hook 得到可见告警；干净树静默通过。

### R0.5 旧根只读强制
**Steps:** 对 `/Users/smkzw/Documents/AI Products/竞品调研工作流` 执行 `chmod -R a-w`（保留恢复说明写入 10.7 任务目录）；核对迁移清单对 `_ref/share_all_msgs.json`（D-12~D-16 证据链）与七份旧报告脱敏样本的闭合状态，缺项补录 `migration/legacy_manifest.jsonl`；旧根 `verification/` 空目录留存待 10.7 一并 inventory。
**验收:** 尝试写入旧根被拒绝；迁移清单无 unverified 项。

## 3. R1 合同与范围落档（第 1-2 周）

### R1.1 Q1-Q6 裁决落档
**Files:** `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/design.md`、`checkpoint_*.md`
**内容:** 按审计 §P0-3 六项裁决原文写入（Q1 复合摘要、Q2 双层信封、Q3 pending_future=1+修 verify_release_receipts、Q4 cutover 工具不进 bundle+修订计划条款、Q5 双入口绑定、Q6 formats 由 manifest 计算=1）。Q4 同时在 `tools/bundle_contract.py` 审计中执行（worker_01 改动的 required-content 处置：若含 cutover 工具则回退该行）。
**验收:** design.md 含六项裁决与理由；worker_01 四文件字节审计结论与之逐条对齐。

### R1.2 release-scope-v1 文档
**Files:** `docs/acceptance/release-scope-v1.md`、`docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md`（引用）
**内容:** formats=1、监测 deferred、刷新手动、三格式代码保留清单、catalog 再生成规则、deferred≠not_applicable 的合法性声明。用户裁决时间与范围摘要固定。
**验收:** 文档存在且被 catalog v2（R1.5）逐条引用。

### R1.3 ADR：检索架构正名
**Files:** `docs/decisions/0003-research-package-architecture.md`（编号顺延现有 decisions）
**内容:** 设计 v1.3 §2 全文要点；connectors 双层定位；引擎出网白名单（CT.gov/药智网）与测试固化方式。

### R1.4 D71-D78 决策记录
**Files:** `docs/decisions/0004-decisions-d71-d78.md`（或并入 0003）；v1.3 §9 为规范来源。

### R1.5 catalog 再生成与 runner 修改（第 2 周，R5 的前置）
**Files:** `fixtures/acceptance/catalog.yaml`、`src/ci_workflow/application/acceptance_runner.py`、`tests/acceptance/test_full_matrix.py`、`tests/acceptance/test_fixture_catalog.py`、`tests/acceptance/test_required_receipt_closure.py`、`tools/verify_cross_format.py`
**Steps:**
1. RED：新增测试断言 catalog 含 `release_scope` 字段；四格式 case 标 `deferred` 且引用 release-scope-v1 摘要；monitoring case 族 deferred；`full-matrix-v1` 无 PPTX 八项 fixture 要求。
2. catalog v2：逐 case 加 `release_scope: {version: v1, status: in_scope|deferred, basis: release-scope-v1}`；12-artifact 断言改 3-artifact（A/B/C × HTML）。
3. acceptance_runner：摘除 PPTX 确认中断、`ppt-master-worklist.json` 生成、G1-G3 校验分支；`--prepare/--resume` 顺序合同相应缩短；`verify_cross_format` 默认 `--formats html`。
4. test_full_matrix 同步改写（保留 fail-closed 语义：缺 3 artifact、旧摘要、顺序错误仍拒绝）。
**验收:** `uv run pytest tests/acceptance/test_fixture_catalog.py tests/acceptance/test_full_matrix.py -q` 全绿；gate 全绿。

## 4. R2 Task 10.6A 收尾（第 2 周）

### R2.1 worker_01 字节审计
按 handoff §9 逐条：重算 8 文件 SHA-256 → 审计 `build_bundle.py/verify_bundle.py/bundle_contract.py/test_fresh_install.py` 当前字节（Git root/dirty 语义、输出前 fail-closed、manifest 兼容、required content 对 Q4 的符合性、fresh-install 测试只写 tmp）。
### R2.2 负向测试补齐
dirty tree 拒绝、source commit 不匹配拒绝、required content 缺失拒绝、manifest 未知字段拒绝。
### R2.3 勾选 A01-A03
gate 全绿 + 聚焦测试 + 相邻回归后勾选；写 checkpoint。worker_01 的 PENDING 报告处置为 superseded-by-audit，不删除。

## 5. R3 投产轨与 QC loop（第 1-3 周并行）

### R3.1 真实项目 #1
**Steps:** 选一个未做过的适应症（建议肿瘤外中小适应症，如慢性自发性荨麻疹复跑或中重度哮喘）；`project create → preflight → 宿主 Agent 检索（research-package）→ project run → 门户产出`。检索用现有手工模式；R7 拉取器完成后切换。
### R3.2 QC loop 固化
**Files:** `docs/acceptance/qc-loop-sop.md`
**内容:** 每个真实报告的固定质量环：`verify_portal --all-routes --browser chromium --browser webkit` → 科学 QC 门（隔离 verdict）→ 视觉会商 ≤2 轮（checklist=六标准逐报告类型版）→ 用户抽读 30 分钟 → 缺陷入清单回修。真实项目产物落 `runs/`，不进 acceptance root。
### R3.3 回流机制
投产缺陷 → gate 修复 → 提交 → 若在 M3 后则记入 v1.1 候选清单。

## 6. R4 功能增量（第 2-3 周，各任务 1-2 天）

### R4.1 F1 research scaffold
**Files:** `src/ci_workflow/application/research_scaffold.py`、`cli.py`（`research scaffold` 子命令）、`tests/integration/test_research_scaffold.py`
**合同:** 输入适应症 → 输出待填 research-package 骨架（含 A/B/C 三类模板、必填字段注释、schema 校验入口）+ 来源清单模板（CT.gov 查询 URL、CDE/chinadrugtrials 链接、五公众号检索式、PubMed 检索式、药智网 API 提示）；`--validate` 子命令对填写中的包即时校验并报精确缺失。
**验收:** RED/GREEN `test_research_scaffold.py`；骨架通过 schema 校验器空跑；CLI catalog 更新。

### R4.2 F3 表格导出
**Files:** `src/ci_workflow/reports/common/table_export.py`、`assets/portal/portal.js`（导出按钮）、`tests/browser/test_table_export.py`
**合同:** 每图下完整表加"导出 CSV/XLSX"按钮；导出=当前筛选视图投影，文件头含筛选状态/快照 ID/数据截止；CSV 用 UTF-8 BOM（Excel 中文兼容）；不产生 artifact 状态。
**验收:** 浏览器测试验证导出内容与表格逐单元格一致；XLSX 用 openpyxl 校验（仅 dev 依赖）。

### R4.3 F7 热图补强
**Files:** `src/ci_workflow/reports/b/safety.py`、`renderers/portal/report_b.py`、`assets/portal/charts.js`、`tests/browser/test_b_safety_heatmap.py` 扩展
**合同:** 色标图例常驻；对照列/分母列默认可见；率值/绝对数切换；缺失状态图例说明。真实项目 #1 的门户作为视觉锚点。
### R4.4 F4 雷达图（视反馈）
**合同:** 设计 v1.3 §6.1；归一化可逆+原始值表；维度组合入视图清单。
### R4.5 F5 证据成熟度矩阵（视反馈）
**合同:** 设计 v1.3 §6.2；双轴信号并列不合成分数。
### R4.6 F8 刷新变化亮点（视反馈）
**合同:** 设计 v1.3 §6.5；diff 数据来自 refresh 前后快照。

## 7. R5 RC 收口（第 3 周）

### R5.1 10.6B source closure
按原 Task 10.6 四阶段之 B：显式 release source set、Phase 0-10 确定性回归（gate+全量 pytest 分层跑）、隔离 clean worktree、唯一 RC commit/tag。投产轨至该日所有修复必须已提交（R0.3 纪律保证）。
### R5.2 10.6C 最终包与重跑
`build_bundle --from-clean-commit <rc>` → `verify_bundle`（`BUNDLE_OK source_commit=... catalog=required-v12-v2`）→ fresh install → 全新 release root 重跑 fresh A/B/C + full-matrix（formats=1；无 PPT Master 作业）；全部 receipts 绑 RC digest。
### R5.3 10.6D 恢复演练与冻结
recovery package 隔离根演练 → owner-stage receipts（deferred 计数、legacy-absence 唯一 future owner）→ 科学/视觉/包/恢复独立验收 → `RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1`。

## 8. R6 分发与切换（第 4 周起）

### R6.1 SKILL.md 与安装文档
**Files:** `skills/competitive-intelligence-workflow/SKILL.md`、`docs/user-guide/install.md`
**合同:** 设计 v1.3 §7（触发词定稿、最小输入示例、无内部术语、三宿主安装步骤）；按"产品说明书"标准独立验收（非技术同事 10 分钟内完成安装+触发为通过线）。
### R6.2 preflight 友好指引
**Files:** `src/ci_workflow/application/capability_preflight.py`、`tests/integration/test_capability_preflight.py` 扩展
**合同:** 每类失败输出中文修复指引；进 conformance 测试。
### R6.3 首批分发
三宿主各至少 1 真实入口 fresh-install + 关键词触发 + 最小输入跑通 host-smoke-v1；回执存 acceptance root。
### R6.4 10.7 切换干运行
按原计划不变（`legacy_cutover inventory/validate` → 用户按清单 SHA-256 授权）。
### R6.5 10.8 删除（burn-in 后）
前置：≥2 个真实报告项目或 ≥2 周真实使用（R3 记录为证据）。其余按原计划。
### R6.6 10.9 终验收
`FINAL_ACCEPTANCE_OK reports=3 formats=1 hosts=3 scenarios=<n> recovery=passed legacy_absent=passed`；deferred 案例计数输出，不冒充 accepted。

## 9. R7 来源拉取器双件套（第 3-4 周）

### R7.1 CT.gov 拉取器
**Files:** `src/ci_workflow/sources/fetchers/clinicaltrials_gov.py`（新增，纯 HTTP+分页+限速+类型化回执）、`sources/connectors/clinicaltrials_gov.py`（解析器复用）、`tests/integration/sources/test_ctgov_fetcher.py`（录制回放+限速断言）
**边界:** 仅白名单域；失败按 §10.4 分类；拉取结果写 content_store；research-package 可引用拉取产物。
### R7.2 药智网 connector + 拉取器
**Files:** `policies/sources/source-policy-v1.yaml`（药智网条目）、`sources/fetchers/yaozh.py`、`sources/connectors/yaozh.py`、`tests/integration/sources/test_yaozh.py`
**边界:** 设计 v1.3 §3 全文；凭据读环境变量 `CI_YAOZH_USERNAME/CI_YAOZH_PASSWORD`（缺省时该来源回执 `access_or_permission_blocked`，不阻断其他来源）；联调用 Edge Lite joincare 账户，凭据不写入任何文件/日志/回执；声明域限制与冲突规则按政策执行。

## 10. R8 治理判断轨（Codex 并行，不阻塞主线）

输入=审计 §4.4 材料 + §1 纪律已生效部分；输出=治理瘦身方案（先方案后执行）：证据分层保留细则、会商轮次上限、worker 拆分条件、metrics 模板修订、磁盘归档批处理（.artifacts 四份 final 副本→保留 v5+清单；logs/conference 按任务压缩）。执行窗口默认 M3 后，若涉及主线文件（plans/context 模板）则在 M3 前只改模板不动存量。

## 11. 阶段信号汇总

```text
M1: GATE_OK（首次全绿）+ TREE_CLEAN + Q1_Q6_DECIDED + RELEASE_SCOPE_V1 + OLDROOT_READONLY
M2: CATALOG_V2_OK + TASK106A_ACCEPTED + REAL_REPORT_1_QC_PASSED
M3: RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1
M4: DIST_OK hosts=3 + CUTOVER_VALIDATE_OK（用户授权后）
M5: LEGACY_ABSENT + FINAL_ACCEPTANCE_OK reports=3 formats=1 hosts=3 scenarios=<n> recovery=passed legacy_absent=passed
```
