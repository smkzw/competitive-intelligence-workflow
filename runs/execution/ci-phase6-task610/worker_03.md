# Execution Output: ci-phase6-task610 - worker_03

## Boundary And Context Check

- 已读取：
  - `context/ci-phase6-task610_execution_context.md`
  - `plans/codex_execution_ci-phase6-task610.md`
  - Task 6.10 `prd.md`、`design.md`、`implement.md`
- 仅执行测试、CLI 运行、临时目录渲染和只读数据审计。
- 未修改生产源码、fixture、catalog 或文档；未执行 Phase 6 发布或最终接受。

## Work Performed

1. 运行 Phase 6 B 类确定性测试集合。
2. 运行 A 类接受基线回归。
3. 运行运行清单、快照、产物路径及阻断边界合同。
4. 串行执行三个 D70 CLI 案例和 fresh PNH CLI 案例。
5. 对 PNH/D70 输入包进行：
   - 产品/试验数量检查；
   - 引用闭合检查；
   - 事实行唯一性检查；
   - 深层 B 事实模型校验；
   - 基线缺失差异检查；
   - 处置未公开语义检查；
   - 快照标识、报告版本和输入摘要检查。
6. 将四个 B 输入包分别渲染到临时目录，并在 Chromium/WebKit 下执行全路由和三档宽度程序化 smoke check。

## Artifacts And Evidence

### 测试通过

- B 类确定性集合：

  ```text
  uv run pytest -q \
    tests/reports/b \
    tests/integration/reports/test_b_report_portal.py \
    tests/browser/test_b_portal.py \
    tests/integration/test_fixture_case_contracts.py
  ```

  结果：`265 passed in 73.34s`

- A 类回归：

  ```text
  uv run pytest -q \
    tests/acceptance/test_report_a.py \
    tests/browser/test_a_portal.py \
    tests/integration/test_atopic_dermatitis_package_rebuild.py \
    tests/reports/a
  ```

  结果：`218 passed in 76.35s`

- 运行绑定、清单、快照和产物路径合同：

  ```text
  uv run pytest -q \
    tests/contract/test_design_acceptance_contracts.py \
    tests/contract/test_artifact_manifest.py \
    tests/integration/test_fixture_artifact_paths.py \
    tests/integration/test_project_run_cli.py \
    tests/integration/test_snapshot_identity.py
  ```

  结果：`33 passed in 10.48s`

- 阻断、零宇宙和 B/C 空场景边界：

  ```text
  uv run pytest -q tests/integration/test_no_draft_when_blocked.py
  ```

  结果：`74 passed in 3.12s`

- Fixture runner 和产物路径回归：

  ```text
  uv run pytest -q \
    tests/integration/test_fixture_run_cli.py \
    tests/integration/test_fixture_artifact_paths.py
  ```

  结果：`7 passed in 8.50s`

- 共用门户、图表—表格同步和全页面运行时回归：

  ```text
  uv run pytest -q \
    tests/browser/test_chart_table_sync.py \
    tests/browser/test_filter_state.py \
    tests/browser/test_portal_shell.py \
    tests/browser/test_evidence_drawer.py \
    tests/acceptance/test_portal_runtime.py
  ```

  结果：`285 passed in 324.38s`

- D70 注册摘要测试：

  ```text
  uv run pytest -q \
    tests/integration/test_fixture_case_contracts.py::test_all_three_b_d70_cases_are_registered_hashed_and_have_distinct_expected_states
  ```

  结果：`1 passed`

### 输入包审计

四个 B 输入包均可被 `ReportBPortalData.model_validate` 接受，所有 view facts 通过对应深层模型校验：

| 案例 | 产品 | 试验 | 疗效 | 安全 | 基线 | 处置 |
|---|---:|---:|---:|---:|---:|---:|
| `b-pnh` | 1 | 2 | 3 | 12 | 12 | 54 |
| `b-d70-baseline-blocked` | 1 | 2 | 3 | 12 | 11 | 54 |
| `b-d70-baseline-recovered` | 1 | 2 | 3 | 12 | 12 | 54 |
| `b-d70-disposition-missing-pass` | 1 | 2 | 3 | 12 | 12 | 54 |

- 所有产品、试验、事实引用均闭合，无未知产品或未知试验。
- 所有事实行标识唯一。
- PNH 的疗效、安全、基线、处置 view facts 均保留 `source_row_id`、`source_version_id`、`source_locator`。
- PNH 关键疗效哨兵事实存在：
  - APPLY-PNH 治疗组：`82.3%`；
  - APPLY-PNH 对照组：明确零值 `0.0%`；
  - APPOINT-PNH 治疗组：`92.2%`。
- D70 基线阻断案例唯一缺口：

  ```text
  (nct04558918, apply-treatment, age)
  ```

- `b-d70-baseline-recovered` 相比阻断案例只补齐上述年龄事实。
- `b-d70-disposition-missing-pass` 的 19 个预定义处置字段全部存在，均为 `not_publicly_disclosed`；值、分子、分母均为空，原始文本不含数字。
- 四个输入包的 `report_snapshot_id` 和 `report_version` 均互不重复。
- 实际输入 SHA-256：

  ```text
  b-pnh:
  7625c379429ea3d907d27f22015857a692bbcc15ce7e8c0f0b766e925551ef49

  b-d70-baseline-blocked:
  84d7fb369bd4aa508ef6ea4b0fdb4647d728c44f0a9eeac90db4cdd4441f66e0

  b-d70-baseline-recovered:
  13ca4d57178420eced06c3da0afa84cf2e8cd4de39b5101c33809168c4b54c01

  b-d70-disposition-missing-pass:
  078b520bf72f36ff85003c222b97ceca555f36436b960bb6d9a410a83eda75da
  ```

### 临时站点 smoke check

目标：确认问题不在 B 门户渲染器本身；不构成最终视觉接受。

- 四个 B 输入包均可由 `render_report_b_site` 生成：
  - 每个站点：24 个 HTML 路由；
  - 21 个静态页、1 个产品档案页、2 个试验档案页。
- Chromium 与 WebKit：
  - 全部 24 路由均有唯一 `main h1`、页脚和 `lang="zh-CN"`；
  - 无页面错误；
  - 无 console error；
  - 无远程 HTTP/HTTPS 请求。
- 768、1024、1440 三档宽度的核心页面：
  - 无整页横向溢出；
  - 图表矩形均在视口内；
  - 无宽度或高度为零的图表。
- `subgroups-supporting-evidence.html` 在四个输入包中均显示“暂无公开支持证据”，无图表和表格；这是当前输入没有专属支持证据时的显式空态，不是零竞品或零试验。

### A 类 CLI 回归

```text
uv run ci-workflow fixture run \
  --case a-complete \
  --reports A \
  --outputs html \
  --project /tmp/ci-phase6-task610-a-complete
```

结果：成功，运行标识：

```text
run_df682f8d8ce579879a6b9121
```

- A 输入：4 个产品、4 个试验、8 条疗效、16 条安全事实。
- 生成 16 个 HTML 文件。
- `validate_run_manifest` 成功重新校验当前运行清单。
- artifact manifest 的 `producer_run_id` 与当前运行一致。

## Commands And Observations

### D70 三案例 CLI 运行

命令形式：

```text
uv run ci-workflow fixture run \
  --case <case-id> \
  --reports B \
  --outputs html \
  --project /tmp/ci-phase6-task610-<case-id>
```

三个 D70 案例均以退出码 2 失败：

```text
RUN_FAILED 当前报告数据包只允许生成 A 类报告
```

失败发生在 `src/ci_workflow/application/run_service.py` 的当前 `report_data_path` 分支：

- 只接受 `contract.reports == ("A",)`；
- 只加载 `load_report_a_data`；
- 只调用 `_render_html_a`。

根因链：

- `src/ci_workflow/application/fixture_runner.py` 会将所有 `role: report_data` 输入复制到项目 `evidence/library/report-data.json`；
- 随后调用统一 `run_project`；
- B 输入因此进入当前 A-only 报告数据路径；
- 当前 `_RENDERER_REGISTRY` 也只注册 `_render_html_a`。

失败后的临时项目根并非完全为空，观察到每个 D70 临时目录均留下：

```text
project.yaml
evidence/library/report-data.json
events/events.jsonl
manifests/artifact_manifest.json
reports/A/
reports/B/
reports/C/
state/project.sqlite
```

但没有：

```text
manifests/current_run.json
B HTML 产物
B 报告快照
```

事件流只包含两个共享节点完成事件，未形成可验收的 B 当前运行清单。

### Fresh PNH CLI 运行

```text
uv run ci-workflow fixture run \
  --case b-pnh \
  --reports B \
  --outputs html \
  --project /tmp/ci-phase6-task610-b-pnh
```

结果：退出码 2：

```text
CONTRACT_ERROR 未知案例：b-pnh
（可用案例：a-complete, b-d70-baseline-blocked,
 b-d70-baseline-recovered, b-d70-disposition-missing-pass,
 no-draft-a-empty）
```

`fixtures/positive/b-pnh/inputs/report-data.json` 实际存在且模型校验通过，但当前 `fixtures/catalog.yaml` 未注册 `b-pnh`。

### 必需 Report B acceptance module

```text
uv run pytest -q tests/acceptance/test_report_b.py
```

结果：

```text
ERROR: file or directory not found: tests/acceptance/test_report_b.py
```

当前 Task 6.10 `task.json` 将该文件列为相关文件，但仓库中不存在该测试模块。当前 B 测试集合覆盖已有 B 视图和门户，但没有 fresh PNH/四项目当前运行的专用 acceptance 测试。

## Blockers Or Missing Environment

1. **P0：B fixture runner 尚未接入统一运行路径。**  
   三个 D70 案例均被 `run_service.py` 的 A-only 检查阻断，无法验证 `evidence_blocked`、`snapshot_locked`、HTML、快照或 manifest 绑定。

2. **P0：`b-pnh` 未进入唯一 catalog。**  
   输入文件存在，但 CLI 报未知案例，无法执行 fresh PNH 项目。

3. **P1：缺少 `tests/acceptance/test_report_b.py`。**  
   无法完成任务文件声明的 fresh PNH、四项目运行绑定、基线阻断恢复和处置非阻断专用验收。

4. **P1：失败运行会留下部分项目根。**  
   当前异常发生在 `run_project` 已创建工作区之后，导致 `project.yaml`、输入文件、SQLite 和共享事件残留，但没有当前运行清单。需由后续实现决定失败前校验或明确失败清理语义。

5. **潜在身份风险（推断）。**  
   三个 D70 项目的 `project_id` 因合同字段相同而相同；项目目录物理隔离且运行 ID 不同，但最终实现应确认 `case_digest` 是否足以作为项目级身份隔离依据。

## Rerun Requests Or Next Step

1. 注册 `b-pnh` 到 `fixtures/catalog.yaml`，使用上述实际输入 SHA，并由实现方计算最终 `case_digest`。
2. 在统一 `run_service` 中接入 B `report_data` 分支和 B HTML renderer，至少绑定：
   - 当前 `run_id`；
   - 当前 `snapshot_id`；
   - 当前输入和 manifest SHA；
   - case digest；
   - 当前运行起点后的文件 mtime。
3. 增加或恢复 `tests/acceptance/test_report_b.py`，覆盖：
   - PNH 关键事实和研究角色；
   - D70 三案例预期状态；
   - 基线精确阻断与恢复；
   - 处置未公开非阻断；
   - 旧文件、旧摘要、缺项目和早于运行起点产物拒绝。
4. 修复后重新串行执行四个 CLI 案例，再重跑：
   - 265 项 B 确定性集合；
   - 运行绑定/产物合同；
   - A 类 218 项回归；
   - shared portal 285 项回归。
5. 本报告中的浏览器结果仅是临时站点程序化 smoke evidence；Codex 仍需对最终当前运行产物完成真实 Chromium/WebKit、科学和视觉接受。
