# 独立端到端测试：IPF（特发性肺纤维化）泛化验证 · round-3

你是独立测试者，在全新疾病领域（特发性肺纤维化，IPF）验证竞品调研工作流的泛化能力。既往测试覆盖 PNH/AD/IgAN/UC，本测试是第 4 个适应症。

## 材料（真实 CT.gov 数据，2026-09-21 抓取）
- CT.gov 数据: `packets/2026-09-21-test-round3/ipf-page-1.json`（20 项研究：Nintedanib/Pirfenidone/bosentan/TRK-250/PMG1015/VUM02 等，3 项有结果）
- 政策: `policies/endpoint-families/registry-v7.yaml`（当前版本）
- 分类器: `src/ci_workflow/reports/`（classify_registry_endpoint 入口自查）
- A 构建器参考: `tools/build_a_payload.py`（通用版）与 `packets/2026-09-21-test-round2 参考: packets/2026-09-20-test-round-2/`（IgAN/UC 的别名映射与载荷样例）
- 渲染器: `src/ci_workflow/renderers/portal/report_a.py`

## 五步测试（从零开始，完整清洁环境）
1. **从零建项目**：在 `runs/test-ipf/` 建立全新项目目录（不要复用任何既有 runs/ 下的旧缓存旧产物；如目录已存在先清空其中你无权保留的内容需自行判断，报告假设）
2. **构建**：从 ipf-page-1.json 出发——建 IPF 别名映射（nintedanib/pirfenidone 等标准药清单；安慰剂/基础氧疗等非竞品排除），用 tools/build_a_payload.py 构建 IPF A 载荷（或如通用构建器跑不通，记录阻塞详情并以自己的最小复制构建验证渲染层）
3. **分类器泛化**：对全部疗效行跑 classify_registry_endpoint，统计纤维化/肺科核心指标（FVC、6MWD、DLCO、急性加重、肺部HRCT/纤维化评分）的命中率；列出未命中的唯一终点全文
4. **门户渲染 + 真实视觉验证**：渲染 A 门户到 `runs/test-ipf/evidence/html-independent/`；用 **ego lite**（ego-browser skill）以真实用户身份打开门户：真实点击导航、切换筛选、展开图卡、截图关键页（1280 与 1440 视口），验证：标题为"特发性肺纤维化竞品全景"、无 PNH/AD/IgAN/UC 字样泄漏、肺科终点有中文标签（不得满屏"其他临床疗效指标"）、时间窗/单位/人群无英文残留、页面无 pageerror
5. **写 findings**：`runs/test-ipf/findings.json`（结构参照 `runs/test-uc/findings.json`）：overall（pass/partial/fail）、steps_completed、steps_failed、run_facts、classifier_coverage、findings（severity+evidence）、generalization_gaps、assumptions

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不要创建 Trellis 任务，不要进入规划模式，不要提出任何确认问题或等待回复
- 所有歧义自行决策，并在 findings.json 的 assumptions 字段记录你的假设
- 视觉验证必须真实打开页面（ego lite 或 Playwright），不允许只读 HTML 源码代替
- 本任务没有交互确认环节；完成后正常退出（退出码 0）
