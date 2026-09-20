# Execution Output: ci_phase5_a_values_matrix_fix - worker_01

## Boundary And Context Check

已读取初始上下文：

- `context/ci_phase5_a_values_matrix_fix_execution_context.md`
- `plans/codex_execution_ci_phase5_a_values_matrix_fix.md`

补充读取了当前任务 PRD、设计/实现说明、A 类研究包、来源审计代码、Portal A 渲染代码、相关测试及既有审计报告。

本轮仅执行来源—抽取—归一—投影—默认可见五层审计，未修改源码、数据或生成报告，也未执行最终视觉/PPT/PDF验收。未访问互联网、生产路径或外部系统。

## Work Performed

### 1. 来源取得层

当前研究包统计：

- 38 个产品、49 个试验
- 44 个试验有 ClinicalTrials.gov 来源记录
- 17 个注册库来源包含结果
- 18 个注册库结果未发布
- 14 个试验由二级来源报告结果，其中 5 个仅有二级来源

当前审计通过：

- `audit=True`
- `issues=0`
- 注册库数值路径共 16,840 条：
  - outcome：6,745
  - TEAE：36
  - SAE：3,954
  - common AE：6,105
  - AESI：0
  - parse failure：0

结论：未发现注册库来源取得或解析层造成的疗效/安全性数值缺失。二级来源虽已绑定来源，但当前缺少通用的二级来源解析覆盖审计，因此二级来源完整性仍属于未完全验证项。

### 2. 抽取层

当前报告行：

- 疗效 6,780 行，全部为数值
- 安全性 10,222 行，其中 10,132 行为数值、90 行为“未公开”
- 所有疗效和安全性行均有 fact/source 绑定
- 未公开值和注册库中的 `NA`、`0/0` 均被保留，没有被转换为零

结论：未发现当前报告数值在事实抽取或事实绑定层被丢失。

### 3. 临床语义归一层

#### 疗效

当前默认视野使用语义正则匹配 EASI-75 和第16周：

- 可匹配 21 个产品
- 当前有任意数值结果的产品共 28 个
- 其中 6 个成熟产品和 1 个部分公开产品有数值，但不属于 EASI-75/第16周默认组合：
  - 阿布昔替尼：第12周
  - 芦可替尼乳膏：第8周
  - 克立硼罗：无 EASI-75 结果
  - 他匹那罗夫：第8周
  - 罗氟司特乳膏：第4周
  - ICP-332：第4周
  - Difamilast：第52周

因此，疗效缺数最早不是来源或抽取层，而是“默认端点/时间点覆盖”层。当前默认视野没有错误地把其他时间点当作第16周，但也没有提供替代时间点状态。

发现一个语义投影风险：Amlitelimab 的原始时间点同时包含第16周和第24周描述，当前 `isWeek16()` 仅因字符串包含 Week 16 即纳入，可能在行级选择时混入第24周上下文。

#### 安全性

当前默认安全性术语为：

- `任何TEAE`
- `任何SAE`
- `Headache`
- `Nasopharyngitis`

当前精确原文匹配结果：

- `Headache`：13 个产品
- `HEADACHE`：另有 2 个产品
- 大小写归一后应覆盖 15 个产品
- `Nasopharyngitis`：13 个产品
- `NASOPHARYNGITIS`：另有 2 个产品
- 大小写归一后应覆盖 15 个产品

当前没有 `头痛` 或 `鼻咽炎` 行，但代码也尚未支持批准的中文别名。

因此，安全性 Headache/Nasopharyngitis 缺数最早发生在临床术语归一层：原始报告行及来源事实存在，但默认术语使用精确大小写匹配，导致别名行未进入同一临床术语桶。`Tension Headache` 不应并入普通 Headache。

### 4. 报告投影层

发现三个最小但重要的投影问题：

1. `efficacyPairFor()` 的配对键包含试验、端点、时间点、单位、人口，但不包含 `arm_detail`。多剂量/多活动臂场景可能按分母和 `row_id` 选择任意活动臂。

2. 当前第16周匹配依赖宽泛原始时间点字符串。Amlitelimab 的第16周/第24周共存描述会带来上下文歧义。

3. `safetyFor()` 在未指定试验时，可跨多个试验选择同一产品/术语的结果。示例：Rocatinlimab 的 `任何SAE`、`Headache`、`Nasopharyngitis` 均存在多个试验结果，当前固定按试验排序选择，并非统一锚定同一个试验/时间窗。

这不是来源缺失，而是违反“默认视野不自动跨试验合并”的投影上下文风险。

### 5. 默认可见层

当前默认视野模拟结果：

- 首页疗效：21 个产品
- 安全性热图：4 列、38 行，共 152 个产品-术语单元格
  - 当前显示数值 57 格
  - 其余 95 格显示“未公开”
  - Headache/Nasopharyngitis 完成批准别名归一后，预计增加 4 个数值格，共约 61 格
- 默认疗效/安全性矩阵：6 个点

当前矩阵 6 个点：

- Amlitelimab
- Etokimab
- 司普奇拜单抗
- 乐德奇拜单抗（Rademikibart / SIM0718）
- GR1802
- 611（SSGJ-611）

矩阵缺点主要来自默认 EASI-75/第16周与同一试验、同一活动臂的 TEAE 数值及治疗组样本量无法同时满足。当前代码选择不绘制缺失点，避免伪造数值；但应将“缺失原因”与“未公开”区分展示。

## Artifacts And Evidence

当前审计依据：

- [research-package.json](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/fixtures/positive/a-atopic-dermatitis/research-package.json>)
- [source_research_service.py](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/application/source_research_service.py>)
- [report-a.js](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/renderers/portal/assets/report-a.js:52>)
- [rebuild-manifest.json](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.artifacts/a-result-visibility-accepted-v1/verification/rebuild-manifest.json>)
- `fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json`
- `fixtures/positive/a-atopic-dermatitis/sources/`

本轮未产生代码或数据改动。未写入 runner 管理的报告文件。

建议的最小修正：

1. 在报告投影前增加规范化字段，保留原始术语，同时生成 `term_key`：
   - `Headache / HEADACHE / 头痛`
   - `Nasopharyngitis / NASOPHARYNGITIS / 鼻咽炎`
   - 不将 `Tension Headache` 合并到普通 Headache
   - 术语合并时同时约束定义、时间窗和试验上下文

2. 增加疗效 `endpoint_family`、`timepoint_key`，将第16周与第24周拆开；不能只依赖宽泛原始字符串。

3. 将 `arm_detail` 纳入疗效配对上下文，或建立明确、版本化的活动臂选择规则，禁止由分母/行号隐式决定剂量。

4. 建立单一确定性 projection snapshot，由首页、详情热图、矩阵图和矩阵表共同消费；安全性默认视野必须显式锚定试验/时间窗，禁止跨试验自动择优。

5. 默认安全性术语覆盖应基于归一化后的 `term_key` 计算，并保留 38 个产品行及“未公开”状态。

## Commands And Observations

通过命令行和 Node 静态检查完成：

- `./.venv/bin/pytest -q tests/integration/test_ctgov_result_coverage_audit.py tests/integration/test_atopic_dermatitis_package_rebuild.py`
  - `14 passed in 39.58s`

- `node --check src/ci_workflow/renderers/portal/assets/report-a.js`
  - 通过

- `git diff --check`
  - 通过

- `./.venv/bin/mypy src/ci_workflow/application/source_research_service.py`
  - `Success: no issues found in 1 source file`

- 正确范围的 Ruff 检查：
  `./.venv/bin/ruff check src/ci_workflow/application/source_research_service.py tests/integration/test_ctgov_result_coverage_audit.py tests/integration/test_atopic_dermatitis_package_rebuild.py`
  - `All checks passed!`

另一次 Ruff 命令错误地把 JavaScript 文件作为 Python 输入，产生大量语法错误；该结果属于命令用法错误，不代表 JavaScript 源文件缺陷。随后已用 `node --check` 和正确范围的 Ruff 分别验证。

未执行真实浏览器验收，因该项属于主控/视觉验收工作流。

## Blockers Or Missing Environment

- 当前任务上下文未授权本 worker 修改源码或生成产物，因此未直接实施修正。
- 二级来源缺少通用解析覆盖审计，当前只能确认报告行具有来源绑定，不能据此证明二级来源已穷尽。
- Amlitelimab 的宽泛时间点字符串、以及多剂量活动臂未纳入配对键，需要主控决定最终版本化选择策略。
- 未执行真实浏览器检查，首页/安全性详情/矩阵的最终运行态仍待主控验收。

## Rerun Requests Or Next Step

建议由主控或后续实现 worker 按以下顺序处理：

1. 实施批准术语别名归一、疗效时间点规范化和活动臂上下文修正。
2. 让首页、热图、矩阵图、矩阵表共同使用同一 projection snapshot。
3. 增加回归测试：
   - Headache/Nasopharyngitis 大小写及中文别名合并
   - Tension Headache 不合并
   - Amlitelimab 第16周与第24周隔离
   - 多剂量活动臂不发生隐式错配
   - 矩阵图与矩阵表使用完全相同的数值和缺失状态
4. 重新构建研究包和 A 类报告，再由主控执行真实浏览器验收。
