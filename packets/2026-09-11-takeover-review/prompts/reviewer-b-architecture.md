Delegated mode（执行模块角色：只读独立复核节点 Reviewer-B）

# 硬边界

1. 只读评审（plan 权限）。不修改任何文件、不创建文件、不运行写入型命令。可以运行只读命令（wc、grep、sed、find、ls、cat 等）。
2. 唯一允许的工作区：/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow。禁止访问路径含"竞品调研工作流"的旧中文工程（不读、不写、不盘点、不确认存在性）。
3. 不重派任务、不启动代理、不声称最终接受。
4. 结论必须给出文件/行号或目录证据。

# 产品合同约束（评审建议不得突破）

- v1 交付面：HTML-only；一个公开 Skill 入口；A/B/C 三个独立中文多页门户；不建融合首页。
- 排除项（不得建议加入 v1）：PDF/PPT 输出、CSV/XLSX 导出、雷达图、证据成熟度视图、定时监测、默认排名/Meta/NMA、LangGraph 强依赖。
- 技术形态：Python 研究/证据/编排引擎（Pydantic + 应用自有类型化控制图）+ SQLite/CAS + Jinja 静态 HTML + 本地 JS/ECharts。
- 八适应症 × A/B/C = 24 门户真实矩阵是最终验收；三宿主（Codex/Hermes/OMP）fresh-install 一致性。
- 禁止 git reset/checkout/clean/add .；保留脏树；不猜历史提交。

# 你的任务：整体工程架构评审

派发方（主线程）的初步问题清单——逐条验证是否成立、严重度如何、给出你的独立判断和修正：

1. **巨型文件/科学-渲染耦合**：renderers/portal/report_b.py 4199 行、application/run_service.py 3938 行、reports/b/pages.py 3757 行、reports/b/safety.py 3333 行、efficacy.py 3316 行。v1.4 §9 要求科学裁决在 Python 科学视图层确定、渲染器只消费；当前 renderer 内仍持有 _semantic_group_key/_groups_for_page/_cross_trial_groups 等裁决逻辑（约 2771-3139 行）。评估：这是否是实现"完整医学语义"目标的阻塞点？拆分的最小安全路径是什么？
2. **双份资产手动同步**：assets/portal/ 与 src/ci_workflow/renderers/portal/assets/ 各有一份 charts.js/portal.css/portal.js/evidence-drawer.*，靠测试护栏同步；manifest.json 只有 repo 侧一份。builder.resolve_portal_asset 优先模块内。评估漂移风险与收敛方案（单一来源+构建期复制？）。
3. **大规模脏树**：~1219 条 git 状态条目、HEAD bb27ec9 之后全部工作未提交。v5 P7 要求最终收敛唯一 source-set。评估：何时收敛、如何降低恢复成本、是否需要中间里程碑提交（注意禁止推测性历史提交，但"当前验收过的切片"是否可提交需要你给出方案）。
4. **导航/元数据漂移**：README 仍描述 v1.2 四格式；v1.4 设计标题"待审定"但已是实际权威；AGENTS.md 项目版仍写 v1.3。评估统一权威索引的方案。
5. **语义提案链未闭环**：SemanticGroupingProposal 是"候选"合同，真实 LLM 提案生产者、独立复核签发（review_issuer/scientific_review_transition 已有）与分组消费之间还没接通；P3.1-P3.5（完整临床单元、版本化时间政策、unknown/N-A 分离）未实现。评估接通的最小路径与顺序。
6. **P2 来源链缺口**：真实取数只有 CT.gov 单查询（PNH 189 记录）；PubMed/CDE/中国登记/监管/企业路线、动态新鲜度消费、历史版本获取、Publication 端到端、OCR、药智真实浏览器适配均未完成。评估竖向样例（PNH 或 IgAN 端到端）优先还是横向铺开优先。
7. **测试体系**：~244 个测试文件分 12 层；gate 是 quality-only。评估：当前测试布局对"页面=科学视图投影"这类合同的覆盖是否足够；哪些关键负向合同缺失。
8. 其他你发现的架构级问题（安装/宿主/恢复/快照/latest 指针/graph 层均可）。

方法要求：先用 skim/rg 概览（src/ci_workflow 各子包的职责与规模），再深入你在清单中要裁决的点的实际代码。不要逐文件通读全仓。

# 输出格式（严格遵守）

输出 Markdown：

## 结论
三句以内：架构总体判断、最大的三个风险、优先行动顺序。

## 清单逐条裁决
1-8 每条：成立/不成立/部分成立 + 证据 + 你的修正意见。

## 新发现
你发现的清单外问题，每条带证据与严重度（P0-P3）。

## 建议的下一步
按依赖顺序列出 5-10 个最小可验收行动。
