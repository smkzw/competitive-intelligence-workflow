# W03 实施结果 — 安全关系、typed 数值与 C 实例

日期：2026-09-22。工程根：本交付包声明的英文工程。分支/HEAD：
`main` / `2df24bb441e555f20b233ad2011b4ffd3610655b`。请求模型为
`gpt-5.6-sol:medium`；当前会话没有运行时可核验的 model/effort 回执，因此模型身份
记为 **UNVERIFIED**。

## 范围与写入边界

- 单一写入者完成 W03；未派发子代理，未执行 commit/push/add/reset/checkout/clean，
  未删除未跟踪资料，保留 W00–W02 和其他用户脏树。
- 首轮仅执行两个集中子批及一次受影响 A 矩阵浏览器旅程；独立审阅 FAIL 后按原范围
  补齐 A/B/C 受影响旅程。未跑全 gate、24 门户、全页模型会商，也未修改历史
  accepted/checkpoint 或接续 PNH v107。
- W01 信任合同未放宽。B/C 联合运行夹具改为真实 JSON 字节、逐事实精确
  `$.array[index].field` locator 与可重提取原文；联合 A/B/C 运行重新通过。

## 风险合同（供独立新上下文审阅）

1. 分母关系以 study/module/group/period/measure object/analysis population/window/source
   version 和显式来源边/审计映射共同定址。标题只否决错误候选，不能创建关系；同 N
   不证明身份，Drug X 不得借 Placebo。旧查找仅能经显式历史只读 adapter 调用，生产
   消费者不可达；新 PNH 生产消费者写入完整身份。JSON 整数不再先转 float。
2. 安全概念保留 polarity、grade set、seriousness、TEAE、relatedness、parent/children、
   count basis。`Non-serious TEAEs`、`without SAEs`、Grade 4、Grade 1 or 3 均保持原语义；
   composite 不自动索取 `other` 分母。B 不再把全部安全行硬编码为 SAE。
3. `numeric_projection` 将 participant proportion/count、event count、person-time rate、
   adjusted estimate、sample size 分面。只有人数比例受 `n<=N` 约束；事件次数可大于人数，
   但不会除以参与者 N 冒充发生率。A/B/C Python 门户投影和 JS/表均消费投影值；差值缺
   对照或口径不兼容即不可绘；轴域来自最终点；size basis 逐点携带。
4. C 实例按 outcome_id/role/group/cohort/period/window 验证；全 universe 每研究必须有实例
   覆盖；多 primary 逐实例合法。新包的 endpoint/timepoint 强制 outcome_id；旧 fallback 仅在
   `legacy_readonly_v0` 显式历史只读模式可达，且同角色多实例失败关闭。干预仅按 CT.gov
   `armGroupLabels` 投到对应臂，无关系保留显式阻断状态，不塞入 arm1。

## 两个 RED/GREEN 子批

### 子批 1：安全关系 + 数值链

- RED 1：`.venv/bin/python -m pytest -q tests/unit/test_w03_safety_numeric_contract.py`
  在收集期因缺少 `describe_safety_concept` 失败。
- RED 2（首轮实现后）：`2 failed, 7 passed`；暴露 `Period 1` 未归一到 TP1、
  `Grade 1 or 3` 只保存 Grade 1。两处均按合同修复。
- GREEN：W03 新测试、既有 v96 安全反例、C 既有三元投影、实际 A/B/C 联合运行、
  A/B/C 门户投影及 A 浏览器矩阵合并命令共 `68 passed in 4.41s`。
- 新增测试 SHA-256：
  `tests/unit/test_w03_safety_numeric_contract.py` =
  `b41958d6afd6b66e5b3bf0f9588c48b6c818edd31c256634943b06d4422696c0`。

### 子批 2：C 实例链

- RED：`.venv/bin/python -m pytest -q tests/reports/c/test_w03_instance_contract.py`
  在收集期因缺少 `ci_workflow.reports.c.arm_interventions` 失败。
- GREEN：首次实现后 `8 passed`；与既有 C endpoint 页面投影合并后纳入上述 68 项绿批。
- 新增测试 SHA-256：
  `tests/reports/c/test_w03_instance_contract.py` =
  `887ac5ea0d8165479bbee1960f18ddcd9531e3a8590dbe03858d6499229efbb2`。

## 实际 A/B/C 消费链

- A：PNH A builder 写入关系身份、participant/event 类型；`report_a.py` 生成 typed
  projection；`report-a.js` 只读取 `plot_value/plot_unit/facet_key`，不在 JS 除数、补对照或
  借总 N；折叠表读取同一 points。作者源和 bundle mirror 字节一致。
- B：PNH B builder 按概念映射 family/category/term_key/measure object；`report_b.py`
  将 raw 值与 projected 值分开；共享 `charts.js` 用最终 projected 点形成域并逐点显示
  size basis。
- C：PNH C builder 已全量 primary/secondary outcome_id，并按 `armGroupLabels` 逐臂生成
  regimen；Fresh C 对全 universe 调实例验证；页面投影和 portal sample-size 消费同一身份
  与 typed 数值。
- 实际联合消费者：
  `test_multi_report_submission_runs_each_report_independently_and_resumes_idempotently` 通过，
  证明可重放 B/C JSON 来源经过 W01 ingest、A/B/C 分支与门户生成，不是 helper-only 绿灯。
- bundle mirror 合同：`1 passed in 0.03s`；最终 W03 + 联合运行 + 浏览器子集复核
  `19 passed in 4.16s`；`git diff --check` 通过。新增文件的 Ruff F/I 检查通过；对所有受影响
  旧大文件做全 Ruff 会命中既有重复字典键、未用 import 与历史格式债务，因此未把该结果
  误记为 W03 失败或擅自扩大修复范围。
- 冻结后一次性复核把 mirror、两个 W03 批次、相邻既有合同、真实 A/B/C 联合运行、
  A/B/C 门户投影与受影响浏览器用例合并执行：`69 passed in 4.65s`；随后新增文件 Ruff F/I、
  作者源/mirror 字节比较与 compileall 全部通过。

## 首轮浏览器矩阵旅程（独立审阅前）

使用仓库 Playwright CLI、当前代码重新生成的 `a-complete` 站点和本地 HTTP 服务；服务与
浏览器会话均已关闭。

- 初始矩阵 4 点；治疗组 size basis 明示。成功 hover 可分离气泡；另一重叠气泡 hover 被
  邻点拦截（记录为限制，未伪称全部指针命中）。
- 抽查点属性/原生 tooltip：疗效 `68.4`、TEAE `66.2`、size basis `治疗组样本量`；tooltip
  同时显示试验、观察窗和 N。
- 刻度为投影后点生成的 `0/25/50/75/100%`；完整表初始折叠，展开后同产品行含
  `68.4` 与 `66.2%`，程序核对 `sameSource=true`；console `0 errors / 0 warnings`。
- 截图：`output/playwright/W03-matrix-journey.png`，SHA-256
  `39fb3ff6319ebe1471d8cae0a0d2d9d514ec6d596d035865440f9184d41b6f51`。
- 浏览器载荷：`output/playwright/w03-matrix-20260922/.../data/report.js`，SHA-256
  `a19abcc1791d3ea6a87881253f8b672aeb96454ff25451d9ecac8370e158d9b2`。

## 关键产物摘要

- typed 投影：`src/ci_workflow/reports/common/numeric_projection.py` =
  `5952db2fb5ff387b3b7abf94794d87f9750c39389b8a69500fb57ac46f85586a`。
- 分母关系：`safety_denominator_crosswalk.py` =
  `3534488b24468cd522be412694f1923d3bb98e51b06eef784efb116d18963b32`。
- 安全概念：`safety_concepts.py` =
  `549a5cadd28e8b732aa9185bf0a6def6897178b2e699b45d80b515c8ae4c0ab2`。
- C 实例与 arm 关系：`endpoint_instances.py` =
  `26889c84eba0b23a318298192938d58115284cb9861e6558eeb657ce87ccff25`；
  `arm_interventions.py` =
  `17c32e3a92d7b680af74e523c24ecc2274d4cbfc3a58a873e02c94a76054a7f8`。
- 门户作者源/mirror：`report-a.js` =
  `eb6bc2cf56490c22abcfd4276824077f1612ee652ee22ad4ff08b0bf06f2fd19`；
  `report-b.js` = `a50857d890207504901d664626954bf8816ed35584323a23415acf3999ba1ce2`；
  `charts.js` = `0925e6ef140af8566578e63cc3b2a9a6936e41c7bd731b9394da5aa84c53f47e`。

## 限制与未解决项

- 模型身份、effort 与任何独立新上下文审阅均 **UNVERIFIED**；按用户边界未自行派审阅者。
- 未执行全 gate、24 门户、全浏览器/viewport/恢复矩阵、真实 PNH v107 重建或正式科学接受。
- 一处重叠气泡的直接 hover 存在 pointer interception；本次用可分离点完成 tooltip 旅程，
  重叠布局的全面可达性留给 W05/视觉批次。
- 旧查找兼容仅保留在显式历史只读 adapter；生产路径执行严格关系。B family 映射、C 缺
  关系干预的阻断状态及所有审阅结论仍须由主线程安排新的独立上下文复核。

## 独立审阅返修（最终状态，晚于上文首轮记录）

### 审阅基线与执行结果

- 独立只读审阅文件 `evidence/W03-independent-review.md` 保持原样。首轮结论为 **FAIL**：
  `P0=0 / P1=6 / P2=1`，本轮将 F01–F06、R01 全部作为必须关闭项处理。
- 返修集中 RED：
  `tests/unit/test_w03_safety_numeric_contract.py`、`tests/reports/c/test_w03_instance_contract.py`、
  两个 Fresh C 反例与生产消费者闭包合并运行，结果 `8 failed, 18 passed`。失败逐项命中
  F01 关系/兼容入口、F02 语义字段、F03 A raw/B Mapping、F04 实例错配、F05 locator 与
  R01 未绑定干预。
- 中间闭包曾因更新 `b-pnh` typed fixture 后未同步 catalog 摘要出现 `4 failed, 46 passed`；
  这是 manifest 绑定失败，修复 `fixtures/catalog.yaml` 的输入 SHA 与 case digest 后不再复现。
- 最终受影响闭包命令覆盖 W03 两个测试族、生产 B/C builder→W01 ingest→manifest-only
  restore、Fresh C 多 primary/组期窗/未绑定关系反例、A/B/C 多报告生产运行、PNH B
  真实 fixture、HTML 投影合同及作者源/mirror/manifest 一致性；结果：
  **`47 passed in 4.09s`**。其后 `py_compile`、4 个 `node --check`、`git diff --check`
  均退出 0。
- 请求模型/effort 为 `gpt-5.6-sol:medium`，但无运行时可核验回执：**UNVERIFIED**。

### F01–F06 / R01 关闭矩阵

- **F01 PASS** — `safety_denominator_crosswalk.py:82-138` 以完整 rich identity 和显式
  `source_declared/audited_mapping` 关系恢复分母；`safety_denominator_crosswalk.py:263-270`
  隔离历史只读 adapter。PNH A 已删除标题+EG/OG 尾号制造边的函数与字段。测试：
  `test_w03_safety_numeric_contract.py` 的负例/正例及
  `test_pnh_a_builder_does_not_manufacture_cross_module_edges`；最终闭包通过。
- **F02 PASS** — A/B 事实合同在 `report_a.py:180-187`、`safety.py:589-596` 保留 polarity、
  grade set、seriousness、TEAE、relatedness、parent/children、count basis；PNH A 在
  `build_pnh_a_payload.py:531` 调用 `describe_safety_concept`，PNH B 将字段写入事实及 portal
  payload，A/B 筛选与表格消费同一字段。复合项不借 other N。测试：安全概念负例、固定
  SAE 消费者及 composite 反例均在最终闭包通过。
- **F03 PASS** — 共享投影位于 `numeric_projection.py:16-137`；A JS 从
  `report-a.js:783-1051` 只读 `numeric_projection`。B 的封闭输入为
  `report_b.py:1250-1291`，实际矩阵消费在 `report_b.py:2838-2866`；PNH B 生产 builder
  在 `build_pnh_b_audit.py:1228-1330` 生成 typed treatment/control/safety/size projections，
  无对照或不兼容不生成点。`charts.js:739-784` 使用显式单位与逐点 size basis，不再默认
  百分点/%；生产 builder 非百分比 `g/L` 测试通过。B 浏览器显示 projected `%` 轴、
  tooltip 文本、`治疗组安全性分析人数 62`，展开表与图同值；单臂 APPOINT 不成伪差值。
- **F04 PASS** — `fresh_c_research_package.py:195,304-360` 新包强制 `instance_v1`，仅显式
  `legacy_readonly_v0` 可走旧只读兼容且多同角色失败关闭；`endpoint_instances.py:89-132`
  校验 outcome_id/role/group/cohort/period/window。Fresh C 多 primary 缺 timepoint、group/
  period/window 错配和每终点独立 timepoint 反例全部通过。C 浏览器四研究均逐实例展示定义
  与第16周；冻结 payload 明示各自 outcome_id/group_id/period。
- **F05 PASS** — PNH A 在 `build_pnh_a_payload.py:602-722` 写精确索引 JSONPath 和来源标量；
  PNH B 事实从 `build_pnh_b_audit.py:379-493` 透传精确 path/original_text；PNH C `_row`
  在 `build_pnh_c_audit.py:64-115` 强制 field_path/source_value，实际 outcome/arm 路径见
  `:284-554`。`test_production_b_c_builder_rows_roundtrip_w01_and_manifest_only_restore`
  用生产 builder 行经过 W01 ingest 并仅凭 manifest 在空目录恢复，最终闭包通过。
- **F06 PASS** — `test_w03_production_consumer_closure.py:19-151` 直接加载生产 PNH builders，
  覆盖 A 禁造边、B/C 精确路径、A JS、B typed matrix、W01 重提取与 manifest-only restore；
  A/B/C 多报告生产运行测试通过。A/B/C 浏览器受影响旅程均完成，见下节。
- **R01 PASS** — `arm_interventions.py:31-93` 对未绑定/未知 arm label 生成显式
  `relationship_status`、`relationship_reason`、`blocking=true`，不丢弃也不回退 arm1；C
  builder 在 `build_pnh_c_audit.py:349-379` 保留该观察，Fresh C 在
  `fresh_c_research_package.py:286-297` 阻断。对应 helper 与完整包反例均通过。

### A/B/C 受影响浏览器旅程

浏览器使用当前源码生成的站点、仓库 Playwright CLI 与受控临时 HTTP 服务；所有浏览器和
服务均已关闭，控制台检查为 `0 errors / 0 warnings`。

- A：矩阵 4 个投影点，tooltip/无障碍文本含疗效、TEAE、窗口和治疗组 N；展开表的 size
  列标题随 preset 为“治疗组样本量”，逐行显示相同 size basis。截图
  `output/playwright/W03-repair-A-matrix.png`，SHA-256
  `a5adc7bc7e19fca8511243da5cf967973ed76f3463ac55c0d6665b8a779bfb6f`。
- B：PNH typed 矩阵仅绘 APPLY 的合法治疗-对照比较；轴/tooltip 使用投影单位，气泡和展开
  表同为疗效差 `80.5`、安全性 `54.83870967741935`、治疗组安全性分析人数 `62`；单臂
  APPOINT 未生成伪差值。截图 `output/playwright/W03-repair-B-typed-matrix.png`，SHA-256
  `6ac4a4720f83043609db5838f8d28fab7d4a88de7aeb847aa50b9410ee467936`。
- C：endpoint-timepoint 页面四研究逐研究显示主要终点定义与第16周，展开表逐条成对；
  treatment-arms 页面逐研究显示显式干预关系，未回退统一 arm1。截图
  `output/playwright/W03-repair-C-endpoint-instances.png`（SHA-256
  `3de7930f6569bc8c17c0071d2c0b2d885d05b37690ece6db7a360bc9a460cc2e`）与
  `output/playwright/W03-repair-C-arm-relations.png`（SHA-256
  `092b33e79f87611dc2e8e7b187a68acb84c79450d2d2fb045a92ace4a4df5186`）。对应冻结
  `data/report.js` SHA-256 为
  `46e3c647462ec0b95e0ce8b726832ac78f51e7e83a552a87338bd8dd48a8891d`。

### 返修后仍未验证

- **UNVERIFIED**：请求模型/effort 的运行时身份；新的独立上下文复审；全 gate、24 门户、
  全 viewport/全页视觉、真实 PNH v107、正式科学/产品/RC 接受。
- 本轮没有进入 W04，没有改写 `W03-independent-review.md`，没有 commit/push/add/reset/
  checkout/clean，没有删除未跟踪资料。

## 相邻合同扩大闭包（主线程 86 项复现）

主线程在上述 47 项定向闭包之外扩大受影响范围后报告 6 个失败。本实现节点按指定边界完成
一次集中修订并只重跑一次重构出的 86 项：

- C 单候选旧负向断言改为正向先例合同：一项证据完整的研究允许形成一条 C 先例路径，
  未恢复“至少两条候选方案”生产门。
- 三个 `RunContext` 夹具均把 research package 写入各自显式 `project_root/inputs`；没有放宽
  `RunContext` 的项目根路径限制。
- `fixtures/positive/b-pnh/inputs/report-data.json` 当前 SHA-256
  `020e8273de3fe3c6fb5d4016af2842c3818d07493ddb11ad0ba08fcba8b460af` 已同步到
  `fixtures/catalog.yaml` 与 HTML-PPT 锁定输入合同；B 矩阵说明同步为封闭 typed rows，单臂
  APPOINT 不生成伪差值。
- A/B 的演示专属局限责任通过 `non_portal_responsibilities` 保留在非门户基础合同中，不加入
  权威门户 page catalog，也未删除实际 slide/page。

重构命令收集并执行 **86 项**，结果为 **`3 failed, 83 passed in 5.19s`**。依照用户“若仍
失败，明确返回”的边界，本轮未继续第二次修复/重跑，W03 当前整体状态为 **FAIL / 不可进入
独立复审前接受**。剩余精确阻塞：

1. `test_run_service_persists_recovery_state_for_blocked_c_evidence`：项目根路径已修正后，夹具
   来源事实仍使用集合级 `$.observations` locator；W01 在
   `source_derivation.py:32` 正确报“事实JSON定位必须精确到字段或数组元素”。
2. `test_fresh_c_double_exhaustion_publishes_reopenable_terminal_decision`：同一集合级 locator
   问题；不是 RunContext 越界，也不得通过放宽 W01 解决。
3. `test_slide_counts_and_coverage_match_catalogs`：C 权威 catalog 要求
   `evidence-limitations`，当前 HTML-PPT 合同仍映射 `evidence-versions-limitations`，导致
   `C 未覆盖页面责任: ['evidence-limitations']`。A 的原始冲突已经关闭，但 C 相邻责任仍未
   对齐。

本节晚于上文 `47 passed` 记录并具有最终优先级。请求模型/effort 运行时回执仍
**UNVERIFIED**；未进入 W04，未修改独立审阅原文，未提交或推送。

## 相邻合同收口（最终实现状态，晚于上节 83/86）

- 第一轮独立只读审阅结论仍为 **FAIL (`P0=0 / P1=6 / P2=1`)**；
  `W03-independent-review.md` 未修改，SHA-256 仍为
  `2517c36f445b0d1155d9eebfbdd96df2277a29baf092adcc55a24dfefb3c64c3`。
- C recovery 与 double-exhaustion 两条实际 `run_service` 旅程现统一通过
  `tests/integration/test_fresh_c_research_package.py:380-406` 重建来源 JSON 字节，并把每条
  observation 绑定到 `$.observations[index].source_text`。两个消费者位于 `:1305-1372` 与
  `:1375-1420`；写入项目根内 package 后，生产 W01 ingest 会从相同持久化 JSON 字节重提取
  `original_text/source_text`，未放宽 `source_derivation.py` 的精确 locator 合同。
- C HTML-PPT `c-limitations` 保留为第 17 页，责任在
  `src/ci_workflow/renderers/html_ppt/projections/c_pages.py:265-275` 对齐权威 catalog 的
  `evidence-limitations`。锁定合同表与 coverage 分别见
  `docs/acceptance/runs/8.5/projection-contract.md:124-132,226-240`；C 不再被列作非门户责任，
  A/B 首版非 HTML 基础兼容保持不变，未删除页面或缩小 coverage 检查。
- 变更字节 SHA-256：Fresh C 集成测试
  `c1146d26e31edeeb73d90626ed2205047cd8c02a06fdf17bf47aee4b3895de06`；C HTML-PPT 投影
  `4b4eb274cfc4354f4ad10a60f8c28373e4ae355d09044e4daa7c2875f43654ca`；投影锁定合同
  `6ae775cf0fb80a8d65e52e2049245d3768523b868a07e611cce77feb28c6a96c`。

复跑命令为上一节同一 86 项 pytest 集合（W03 两个测试族、生产消费者闭包、W01 trust
snapshot、Fresh C 全文件、多报告运行、4 个 PNH B acceptance 节点、HTML-PPT 投影合同、
bundle 作者源/mirror/manifest 合同），环境固定
`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider -q --tb=short`。运行时回执：
**`86 passed in 5.43s`，exit 0**。因此上一节三个精确失败均已关闭，当前 W03
**实现侧受影响闭包 PASS，可交主线程安排新的独立只读复审**。

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q \
  tests/unit/test_w03_safety_numeric_contract.py \
  tests/reports/c/test_w03_instance_contract.py \
  tests/contract/test_w03_production_consumer_closure.py \
  tests/integration/test_w01_trust_snapshot_closure.py \
  tests/integration/test_fresh_c_research_package.py \
  tests/integration/test_multi_report_product_run.py::test_multi_report_submission_runs_each_report_independently_and_resumes_idempotently \
  tests/acceptance/test_report_b.py::test_pnh_fixture_keeps_source_backed_efficacy_safety_and_baseline_sentinels \
  tests/acceptance/test_report_b.py::test_pnh_view_facts_share_arm_identity_and_build_the_default_matrix \
  'tests/acceptance/test_report_b.py::test_b_cases_are_bound_to_the_current_fresh_run[b-pnh-completed-rendered_unreviewed]' \
  tests/acceptance/test_report_b.py::test_disposition_missing_is_visible_but_does_not_block_report \
  tests/html_ppt/test_projection_contract.py \
  tests/contract/test_bundle_scientific_closure.py::test_portal_asset_author_source_mirror_and_manifest_are_consistent \
  --tb=short
```

F01、F02、F03、F04、F05、F06、R01 的实现侧终态均为 **PASS**；逐项生产证据、测试与
A/B/C 浏览器旅程仍以“F01–F06 / R01 关闭矩阵”和“A/B/C 受影响浏览器旅程”为准。本次
相邻收口没有改变那些生产合同或浏览器载荷，只补齐 C 恢复旅程的可重放来源绑定和 C
HTML-PPT catalog 覆盖。

仍为 **UNVERIFIED**：请求模型 `gpt-5.6-sol:medium` 的运行时 model/effort 身份、新的独立
上下文复审、全 gate、24 门户、全 viewport/全页视觉、真实 PNH v107 及正式科学/产品/RC
接受。本轮未进入 W04，未 commit/push/add/reset/checkout/clean，未删除未跟踪资料。

## 第二次独立复审返修（当前最终实现状态）

### 冻结审阅与批次

- 第二次独立只读复审 `evidence/W03-independent-rereview.md` 原结论保持 **FAIL
  (`P1=4 / P2=2`)**，文件未修改，SHA-256
  `65840ad8055e2f8c2c38ed0f90f1300190954d5ebac6018452f79b8e6fa2e4fa`。第一次独立审阅也
  未修改，SHA-256
  `2517c36f445b0d1155d9eebfbdd96df2277a29baf092adcc55a24dfefb3c64c3`。
- 集中 RED：生产消费者、Fresh C、HTML-PPT 三个测试文件合批，结果
  **`7 failed, 49 passed in 1.95s`**；分别命中 B term_key 丢失、两个矩阵伪造、A builder
  `page` NameError、Fresh C 内容/运行入口 legacy 自报和 C 双路径旧门。
- 第一轮整族 GREEN 尝试暴露事件次数孤立 numerator 与两个测试断言问题：
  **`3 failed, 53 passed in 7.45s`**。修复后同批为 **`56 passed in 30.58s`**。
- 按上一轮相同“86 项”命令复跑；因本轮新增 7 个回归节点，实际收集并执行 93 项：
  **`93 passed in 35.33s`，exit 0**。
- 真实固定 CAS A→B/C 全链单独回执：**`1 passed in 28.15s`**。三个复审直接反例（B
  term_key、B 矩阵两种伪造、Fresh C 内容与 run_service legacy 自报）单独回执：
  **`5 passed in 0.48s`**。

### P1/P2 关闭证据

- **P1-01 / F02 PASS** — `report_b.py:1026-1103` 优先读取并验证 `term_key`，仅接受
  `SAFETY_CONCEPTS` 受控键，并以键本身作为 `clinical_concept`；catalog 已覆盖
  `absence_sae/non_serious_teae/grade_specific/composite_ae` 等现有 typed keys。
  `build_pnh_b_audit.py:51-88,1160` 由 `build_portal_safety_rows` 原样保留 row term_key，
  不再按 family 逆推 generic。端到端测试
  `test_w03_production_consumer_closure.py:84-114` 走 builder→ReportBPortalData→安全筛选/表，
  `absence_sae` 与 `negative_presence` 不降级。
- **P1-02 / F03 PASS** — `report_b.py:1265-1301` 要求投影携带
  `canonical_numeric_projection_v1`、raw value/unit、numerator/denominator，并用共享
  `project_numeric` 重算 plot value/unit/facet；`:1304-1344` 严格比较治疗/对照的 kind、
  unit、direction、window、estimand，安全轴强制 `%`，size 强制正整数“人”和批准的非空
  size_basis。生产 builder 在 `build_pnh_b_audit.py:1248-1264` 输出同一 canonical provenance。
  `test_w03_production_consumer_closure.py:117-137` 从 `ReportBPortalData` JSON 入口拒绝
  `g/L` 对 `%` 与 `%` size 两个复审伪造；fixture bytes SHA-256 为
  `a37d7239bfc68f50d86ff732953c68769f1e70710d9e05e36f474941ce172e3b`，catalog 与 lock 已同步。
- **P1-03 / F04 PASS** — `fresh_c_research_package.py:184-203` 的新内容 schema 只允许
  `instance_v1`；`:300-309` 无任何 package 可开启的 legacy 分支，统一执行逐 outcome 实例
  校验。普通内容和实际 `run_service` 包声明 `legacy_readonly_v0` 的反例位于
  `test_fresh_c_research_package.py:491-532`，均失败关闭。当前最小实现没有伪造一个“可信迁移”
  入口；历史只读迁移不属于新 Fresh C package schema。
- **P1-04 / F05/F06 PASS** — A builder 的真实错误在
  `build_pnh_a_payload.py:431-451` 修为 `page_no`；实际输出疗效/安全消费行在
  `:576-632,665-723` 均携带精确 `source_field_path/source_text`。完整生产测试
  `test_w03_production_consumer_closure.py:216-284` 在受控临时目录执行固定两页 CAS 的 A
  `main()`（3895 疗效、519 安全）→B `main()`/C `main()`（258 observations），再将全部 B
  facts 与全部 C derived facts 分别送入生产 W01 ingest，并仅凭 manifest 在空目录 restore；
  同时生成真实 C 站点并检查 `data/report.js`。这不是手工单行替代测试。
- **P2-01 PASS** — `projection-contract.md` 已把单条完整 C 先例设为合法，
  `C_min_design_paths=1`；固定 `c-path-2` 仅标为首版结构兼容位，不是当前 HTML 产品或真实
  渲染门。`c_pages.py` 删除“至少两条”及强制“两条并列”措辞；
  `test_projection_contract.py:205-221` 锁定该兼容边界，未删除 slide/page 或缩小 coverage。
- **P2-02 PASS** — `tools/build_w03_browser_freeze.py` 从固定 CAS 运行 A→C→真实 C portal，
  只保留 `evidence/W03-browser-freeze/site.manifest.json` 与 `data/report.js`，不保留巨大临时站点。
  manifest SHA-256 为
  `caa754ddd00e6fc2fe04e86ad8a2e9ff57dd4d60027dce59ad91e51c8a787b1f`；冻结
  `data/report.js` SHA-256 为
  `fff71397b08d24b8ed3ef21f9736298ca16b9814ee88df143e4f12af21b1882d`。manifest 同时绑定
  两份 CAS、当前四个生成源码、18 个站点文件的 sitemap 摘要及两张 C 浏览器截图；
  `test_w03_production_consumer_closure.py:287-302` 逐字节复核全部绑定。

### 保持项与边界

- **F01 PASS / R01 PASS 保持**：本轮没有修改分母 crosswalk 或 arm-intervention 关系实现；
  原负例和 93 项扩展闭包继续通过。
- 作者源/mirror/manifest 合同包含在 93 项中；最终 Python/JS 语法、独立作者源镜像节点与
  `git diff --check` 均另行复跑：5 个生产/证据 Python 文件 `py_compile` exit 0；门户
  A/B/C/charts 的 4 个作者源与 4 个发包镜像共 8 个 `node --check` 全部 exit 0；
  `test_portal_asset_author_source_mirror_and_manifest_are_consistent` 为
  **`1 passed in 0.02s`**；最终 `git diff --check` exit 0。
- 当前是 **W03 实现侧 PASS，可交新的独立只读复审**，不是对两份历史 FAIL 的改写。
  请求模型 `gpt-5.6-sol:medium` 运行时身份、新独立复审、全 gate、24 门户、全页视觉、
  PNH v107 及正式科学/产品/RC 接受仍为 **UNVERIFIED**。未进入 W04，未提交、推送、清理
  或删除资料。

## 第三次独立复审后的证据绑定返修

### 审阅结论与修复边界

- 第三次独立只读复审 `evidence/W03-independent-rereview-2.md` 原结论保持 **FAIL
  (`P0=0 / P1=0 / P2=1`)**，文件未修改，SHA-256
  `d1da3d6ee95d7da932d69e4aae490b3aead51f9dcc1adc68c8fa50e17ed372da`。其唯一失败是旧
  manifest 把 6 项真实 PNH `report.js` 与 4 项合成试验截图错误绑定；上一节在二审返修时
  对 P2-02 的实现侧 PASS 判断由此被第三次独立复审否定。
- 本轮仅修浏览器 freeze 的证据生成、绑定与机械测试，没有修改 F01–F06/R01 生产语义，
  没有进入 W04。前三份独立审阅原文全部保留。

### 真实冻结站点与浏览器旅程

- `tools/build_w03_browser_freeze.py` 现在可用 `--site-root` 把固定两页 CAS 经 A main→C main→
  `render_report_c_site` 重建到显式空目录；本次生成回执为 A `3895` 疗效/`519` 安全行，C
  `6` trials、`5` products、`258` observations、`4` paths。随后从该目录启动仅绑定
  `127.0.0.1:8765` 的受控临时 HTTP 服务，浏览器旅程结束后 Playwright 与服务均已关闭。
- `endpoint-timepoint-matrix.html` 与 `treatment-arms.html` 两页均由 Playwright CLI 在
  `1720×1100` viewport 打开。页面内现场 fetch `data/report.js` 后得到的 payload trial 集合，
  与 DOM 可见 NCT 集合均精确为：`NCT02591862`、`NCT02605993`、`NCT03181633`、
  `NCT04170023`、`NCT04469465`、`NCT05886244`；两页 `allVisible=true`，console 均为
  `0 errors / 0 warnings`。
- 结构化回执位于
  `W03-browser-freeze/journeys/endpoint-timepoint-matrix.json`（SHA-256
  `56b5f760463527e7246f6fffbfdc002118021582d64bb4619685b86e68332ade`）与
  `journeys/treatment-arms.json`（SHA-256
  `56cfbacdae3d46ea92ee4dcaf251a9f3832e79c4bc9bc10c17387f618b477db0`）。回执保存 runner、
  viewport、route、页面哈希、`report.js` 哈希、payload/DOM trial 集合、console 与截图绑定；
  机械检查不使用 OCR。
- 新截图为 `output/playwright/W03-browser-freeze-C-endpoint-timepoint.png`（SHA-256
  `9c945099649d8a6b8347a4b88e4fcfa7e81cf589056f0750c55a3e5137894188`）和
  `output/playwright/W03-browser-freeze-C-arm-relations.png`（SHA-256
  `67652ce43ba8b57ce3a411092361b4098eba2b418644a9b987d0be4b5144bd54`）；两图画面均直接展示
  上述 6 项真实 PNH NCT 身份。旧合成截图未删除，但 `site.manifest.json` 已不再引用。

### Freeze v2 与验证回执

- `W03-browser-freeze/site.manifest.json` 升级为 `w03-browser-freeze-v2`，SHA-256
  `44b994b9fee2a237132be62a437c343e6368e0eeecd8729c86d7b46becf3262a`。当前绑定两份固定
  CAS、11 个生成/模板/资产/工具源码、两页 HTML 哈希、保留的 sitemap、两份结构化旅程和
  两张新截图；不再绑定旧合成截图，也未把完整临时站点写入 evidence。
- 冻结 `data/report.js` 保持 SHA-256
  `fff71397b08d24b8ed3ef21f9736298ca16b9814ee88df143e4f12af21b1882d`；新增保留的
  `data/sitemap.json` SHA-256 为
  `001ca757ea8f827e11af64ca1ab097422a8938cc10a1443237152cba25013d01`。从当前 CAS/源码再次
  运行 freeze builder 后，C package、`report.js`、sitemap 和两页 HTML 哈希均与 manifest/
  旅程回执一致。
- 定向机械测试先对旧 manifest 得到 **`1 failed in 0.34s`**（schema v1 命中 RED）；修复后
  `test_w03_browser_freeze_rebinds_report_data_sources_and_screenshots` 为
  **`1 passed in 0.30s`**。该测试解析保留的 `report.js`，逐项比较两个旅程回执中的 payload
  与 DOM trial 集合，并校验 page/console/screenshot/manifest 哈希绑定。
- 因本轮只改 freeze 工具、证据和对应机械测试，按第三次审阅的最小影响闭包没有无谓重跑
  93 项生产合同：作者源/mirror/manifest 节点为 **`1 passed in 0.02s`**；两个 Python 文件
  `py_compile` exit 0；最终 `git diff --check` exit 0。

### 当前终态与未验证项

- 第三次独立复审唯一 P2 现为 **实现侧 PASS**；W03 可交新的独立只读复核，但不能把本轮
  自验写成独立接受。F01–F06/R01 继续沿用第三次复审的 `P1=0` 通过结论，本轮未触碰。
- 请求模型 `gpt-5.6-sol:medium` 的运行时 model/effort 身份仍无可核验回执，记
  **UNVERIFIED**。全 gate、24 门户、全 viewport/全页 Chromium/WebKit、真实 PNH v107、
  正式医学/统计/产品/RC 接受仍为 **UNVERIFIED**。
- 未 commit/push/add/reset/checkout/clean，未删除资料，未进入 W04。

## 最终独立核验（晚于上述实现侧状态）

- 新的独立只读核验见 `W03-independent-freeze-review.md`，结论为 **PASS，P0=0 / P1=0 /
  P2=0 / P3=0**。它重新验证固定 CAS/当前源码可重建完全一致的 package、`report.js`、
  sitemap 和两页 HTML；两条 journey 的 report.js 与 DOM 均为同一组 6 项真实 PNH NCT，
  console、route、page、screenshot 与 manifest 哈希全部一致，旧合成截图未被当前 manifest
  引用。定向测试 `1 passed in 0.30s`。
- 至此 W03 工程风险合同关闭。该结论不构成正式医学、统计、产品、24 门户或 RC 接受；
  请求模型 `gpt-5.6-sol:medium` 仍缺少可核验运行时 model/effort 回执，记为
  **UNVERIFIED**。
