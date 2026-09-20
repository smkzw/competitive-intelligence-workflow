# 竞品调研工作流——执行计划 v6（ZCode 接管版）

日期：2026-09-11。取代 `plans/gpt6-execution-plan-v5-20260905.md` 成为当前操作计划；v5 保留为历史输入。P0–P7 阶段骨架、产品边界、验收矩阵不变（原生 Goal 文本仍具最高产品效力），本文更新：恢复后验证结论、工程 review 处置、执行机制、以及各阶段的最小接线顺序。

配套：`reviews/zcode-takeover-engineering-review-20260911.md`（本轮 review 全文与证据）、`packets/2026-09-11-takeover-review/`（两份独立审阅派发记录）。

## 0. 执行机制（用户 2026-09-11 授权更新）

- 主线程（GLM-5.3）持有：任务分解、共享合同、run_service/科学接受边界、最终验收、用户交付。
- 独立复核/会商：按 `/Users/smkzw/.zcode/zcode-route-manifest.json` 治理派发；GLM 产物由非 GLM 家族挑战（验证者隔离）。派发 prompt 带 `Delegated mode` 前缀与硬边界；packet 落 `packets/<日期-主题>/{prompts,runs,reviews}`。
- 每 LOOP：读合同/消费者 → RED 反例 → 最小完整修复 → 定向+相邻回归 → 源/产物摘要绑定 → 检查点更新。会商裁决改变方向的，回到本计划修订而非口头记忆。
- 用户原裁决全部保留：HTML-only、24 门户、三宿主、药智边界、新鲜度/历史截止、无 PDF/PPT/导出/雷达/定时、不为过测向真实 fixture 补造临床参数。
- 旧中文工程零接触不变；禁止 reset/checkout/clean/git add .；**不做中间里程碑提交**（Review-B 论证：科学链未接线前提交会把未验证身份固化为 provenance 锚点）；恢复成本改用内容寻址脏树清单（路径+sha256+字节数，不落 git）。

## 1. 恢复后已完成（2026-09-11 本轮）

- 被中断验证全部完整重跑：B 领域+浏览器 278 绿；两轮反例 29/30（1 失败已由 Reviewer-A 终审为"反例机制过时而非页面回归"）；gate 六步中 Ruff/mypy/986 单元合同/兼容/分层全绿，legacy 引用失败已修（交接文档补 historical 标记）；integration 初跑 817/1，失败为夹具身份违约已修（matrix row_id 唯一化+级联哈希）。
- Reviewer-A（gpt-5.6-luna）终审：第二轮语义修复在真实渲染路径成立；4 项 P2 护栏缺口（§P3.0）。
- Reviewer-B（deepseek-v4-flash）架构评审 + 主线程核验：F1 科学视图层生产死代码（P0）等 10 项发现。

## 2. 阶段计划

### P3.0 语义护栏收口（当前，第一批实施）

Reviewer-A 四项 P2，每项先 RED 后 GREEN：
1. 全池裁决入口显式化：`_groups_for_page` 的裁决用途与页面投影用途分离，拒绝详情子集进入裁决入口；第一轮反例不变量以真实渲染路径固化为正式测试（tmp/ 原证据不动）。
2. 全池孤立提案拒绝：全池入口要求提案 row_ids 全部存在；局部投影保留显式 partial 模式。
3. 域白名单 fail-closed：未知域记录拒绝；已有域与页面域不一致时拒绝而非重写。
4. 纵向页 uncovered 隔离：真实记录走 uncovered 回退直接失败；仅显式合成标记记录允许。
完成后：完整 gate + integration + B browser 重跑绿 → P3 暂停点正式关闭。

### P3.5 科学视图层接线（F1 主线，四步不可换序）

1. 红灯合同先行：断言 B 渲染在缺 `efficacy_views`/`safety_views` 时失败关闭（当前 `Any|None` 静默容忍）——此测试先红。
2. `ReportBPortalData` 视图字段类型化（F2）+ 补 `reports/b/__init__.py`（F3）。
3. `_groups_for_page` 消费 `EfficacyViewSet`/`SafetyViewSet`，删除渲染器本地 `_semantic_group_key` 初分桶与 `_time_band` 自算（改读 `TimepointCompatibilityPolicy`）；投影组来源改科学层，消除循环校验。
4. 按域拆文件归 `reports/b`（renderer 只剩投影/模板职责）。
每步绑定真实 HTML 消费回归（tests/browser）；不为拆而拆，出现合同变化即停并会商。

### P2 扩展：真实路线与闭包门（与 P3.5 可并行、独立写集）

1. PubMed 可执行获取路线（复用 pubmed.py:104 URL 构造 + :125 XML 解析，仿 ctgov handler 模式 + 合成 transport 测试）——证明"路线机制真会执行"。
2. `not_applicable` 路线结果必须附适用性依据（F4，research_package.py:1019-1031）。
3. 其余照 v5 P2 合同（动态新鲜度消费、历史版本、Publication 端到端、OCR 门、药智真实浏览器观察）按竖向样例需求逐项补。

### P3.7 语义提案链闭环（P3.5 完成后）

1. `SemanticGroupingProposal` 显式状态迁移 + `review_receipt_id`（复用 `SemanticAdjudicationReceipt` 字段形状，不造第二种回执）。
2. `capabilities/semantic_review.py` 生产者接图 `semantic-review` 节点；`compare_clinical_constructs` 保留为确定性否决。
3. 签发复用 review_issuer 身份/上下文绑定；渲染器只消费已批准提案。
4. P3.1 完整临床单元（clinical_unit）在此之后，不在之前（数据模型大改不阻塞 1-3）。

### P4 门户（v5 合同不变，增补）

- A 矩阵/产品档案旧单对逻辑清除、行级来源；B/C 全页覆盖。
- 工程卫生项并入：charts.js 等全部共享资产双副本字节相等测试（F8，已完成）；README 改 HTML-only + 权威索引机器可检合同（F6，已完成）。
- 四视口×双引擎全物理页矩阵不变。
- **kangzhe-design-3d v5.2.6 视觉同步**（2026-09-12 升级：六形态卡片/图上编辑/铺开入场/生图管线；html_interact v5.2 G-INT-01…09 含须线 v2.2 几何合同；track_site v5.2.3 容器分级：图表区 max-width min(1560px,94vw) 禁止统一 1100px 封顶）。同步工作流：① 以 skill v5.2.6 为源刷新仓库合同副本（保留 project_profile.md 专属规则与 HTML-only 范围）；② kz-charts.js v5.2/kz-interact v5.2 执行层与现有 charts.js 关系评估；③ G-INT v5.2 逐条映射；④ 浅色 ONLY+面积红线全门户核查；⑤ 多模态视觉验收。**呈现形式借鉴（CMS-D017 PPT 第 9/10/11 页，2026-09-12 审视）**：(a) A 新增"靶点×阶段甘特进度图"（◆中国/●国外、自有资产橙虚线）；(b) B 疗效按临床问题分组+初治/经治分簇+组间差列+单臂不画假对照+每图窗口/文献行；(c) B 安全性加"试验vs对照分组柱+机制特异性事件 breakout"；(d) 行级五级证据口径（已核实/多源二手/据公告/据报道/推测）进 A/B 事实行；(e) 关键数值双模型核对仲裁表（数值粒度独立复核）。调研范围查漏：MY008211A 等别名入映射表；达尼可泮 CFD 加用关系语义（G11-1 医学实例）；商业维度列（销售/给药间隔/中国状态）作 P2 来源接入目标。

### P5 安装/宿主/恢复（v5 合同不变）

- B/C 提交后恢复窗口、完整 restore/resume/refresh/rebuild、三真实宿主、fresh-install 最终包。

### P6 八适应症矩阵（不变）

顺序：**PNH 竖向端到端首验**（fixture 基础已存在 fixtures/positive/b-pnh）→ 按其暴露的缺口修齐 → 8×3 铺开。合成测试与单查询取数不计入。

### P7 唯一候选与冻结（不变）

- 收敛前置条件见 §0（不做中间提交）；最终受控 source-set 逐文件纳入 + 唯一候选 commit + 绑定验收。
- 期间持续维护脏树内容寻址清单使恢复成本可测量。

## 3. 验收追踪

沿用 v5 §4 矩阵，追加：

| 需求 | 任务 | 决定性证据 |
|---|---|---|
| 渲染器不裁决 | P3.0/P3.5 | 缺视图集失败关闭红灯 + 投影组来自科学层的非循环证据 |
| 路线真会执行 | P2 扩展 | PubMed 真实获取回执 + not_applicable 适用性依据负例 |
| 提案链闭环 | P3.7 | 已批准提案消费 + 空回执/自填 reviewer 拒绝 |
| 资产零漂移 | P4 卫生 | 全部共享资产双副本字节相等测试 |
| 权威唯一 | P4 卫生 | README formats == package-manifest formats 合同测试 |
