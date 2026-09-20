给 Codex 的交接提示词（2026-09-02，由 ZCode 工程审计产出，用户授权转交）

一、角色与背景
你是本项目的继续构建者。项目是竞品调研多 Skill 工作流，位于 /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow。你此前按 2026-08-10 实施计划构建到 Task 10.6A，被用户于 2026-09-02 11:46 无损暂停（见 PAUSE_HANDOFF_20260902_114643.md）。暂停期间用户委托 ZCode 做了完整工程审计，并做出两轮共八项裁决。你现在的任务是基于审计发现和八项裁决继续构建，不要从原计划原地续跑——剩余工作已被重新分解。

二、开工前按此顺序通读（都在新工程根目录下）
1. .trellis/tasks/09-02-phase-10-task-106-rc-freeze/PAUSE_HANDOFF_20260902_114643.md（暂停现场与安全状态）
2. reviews/zcode_ci_engineering_audit_20260902.md（工程审计：问题清单、六标准评估、证据索引）
3. docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md（设计升版：v1.3 增量条款，取代 v1.2 被修订部分）
4. plans/zcode_revised_roadmap_20260902.md（修订路线图：里程碑 M1-M5、周计划、原任务处置映射）
5. plans/zcode_execution_plan_v2_20260902.md（执行计划 v2：R0-R8 任务分解，这是你的工作清单）
6. .trellis/tasks/09-02-phase-10-task-106-rc-freeze/ 下的 prd.md / design.md / implement.md（10.6 四阶段框架仍有效，注入 v2 修订）

三、已裁决事项（用户 2026-09-02 明确拍板，不得重开、不得再会商）
1. 多宿主分发是正式需求：Codex/Hermes/OMP 三宿主一致性测试、bundle/fresh-install 合同、真实宿主 smoke 全部保留。LangGraph 适配器 E1 继续 indefinite defer。
2. 旧工程目录（竞品调研工作流）确认不用后可删除：10.7/10.8 删除链保留，但删除前需 burn-in（至少 2 个真实报告项目或 2 周真实使用）。
3. 当前系统可立即投产出真实报告并跑 QC loop：投产轨与验收轨并行，见路线图第 4 节。
4. 治理密度瘦身由你判断后执行：判断材料在审计第 4.4 节，先出方案再动手，不阻塞工程主线。
5. 药智网企业版纳入来源政策：声明域与凭据边界见设计 v1.3 第 3 节；实施联调可用用户 Edge Lite 浏览器中的 joincare 账户；凭据只存本地环境变量，不入库不入包不入日志。
6. 分发形态是 skill 安装包：同事在各自 Agent 中用关键词触发；SKILL.md 文案和 preflight 失败指引按产品说明书标准验收（设计 v1.3 第 7 节）。
7. 全部人工手动触发，不做自动增量刷新：监测 Skill 移出范围，catalog 标 deferred。
8. 首版输出只要 HTML 门户：PDF、HTML-PPT、PPTX 全部不需要；三条格式轨代码保留但验收摘除，formats=4 全部改 formats=1，合法性依据是 release-scope-v1 文档（R1.2 产出）。
另外 handoff 的 Q1-Q6 六项合同冲突也已裁决，结论在执行计划 v2 的 R1.1，直接落档即可。

四、执行顺序（严格按依赖，细节看执行计划 v2）
第一步 R0：建 gate 命令；修复全仓 77 个 mypy 错误和 3 个 ruff 错误；补 .gitignore 后把 8/27 以来 6 天的积压按 v2 第 2 节 R0.3 的提交序列分组提交；加 git 白名单钩子；旧根 chmod -R a-w。
第二步 R1：Q1-Q6 裁决写入 Task 10.6 design.md；写 release-scope-v1 文档；写检索架构 ADR；记录 D71-D78；再生成 required-v12 catalog（formats=1、deferred 状态字段）并修改 acceptance_runner 与 test_full_matrix。
第三步 R2：审计 worker_01 留下的四个文件字节，补负向测试，勾选 A01-A03，收尾 10.6A。
第四步 R3 与 R4 并行：投产轨选一个新适应症跑真实报告并固化 QC loop；同时做 research scaffold、表格导出、热图补强三个小功能。
第五步 R5：10.6B source closure 到唯一 RC commit，10.6C 最终包重跑（formats=1，无 PPT Master 作业），10.6D 恢复演练后输出 RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1。
第六步 R6 起：skill 包分发文案、三宿主真实分发、10.7 干运行、burn-in 达标后 10.8 删除、10.9 终验收。
R7 拉取器双件套（CT.gov 加药智网）在第 3-4 周窗口实施。R8 治理瘦身你自行排期，主线优先。

五、硬边界（违反任何一条立即停止并报告）
1. 旧根 /Users/smkzw/Documents/AI Products/竞品调研工作流 只读：不读、不写、不 inventory、不删除；10.7 之前任何命令不得指向它。chmod 后任何写入都会失败，这是刻意的。
2. 不 reset、不 checkout、不 clean 当前 847 项脏树：积压用分组提交保全，用户改动必须完整保留。
3. worker_01 的 PENDING 报告不得当作 accepted；续接先审计字节再决定采纳或重派。
4. 不修改已封存的 Task 10.5 及更早检查点与验收记录。
5. RC_FROZEN、FINAL_ACCEPTANCE_OK 等信号只能在实际全部门通过后输出；deferred 案例计数输出，不得冒充 accepted，也不得用 not_applicable 绕过。
6. RC commit 创建之后不得再改产品代码、测试、catalog、runner、切换工具；发现问题走 v1.1 候选。
7. 凭据红线：joincare 用户名密码、任何会话 token 只存本地环境变量，禁止进入任何文件、日志、回执、事件、快照、bundle。
8. 每个代码任务维持 TDD（先 RED 后 GREEN）、真实锚点、独立验收；每任务收尾必须 gate 全绿并显式提交（禁止 git add .）。

六、汇报与检查点要求
1. 每完成路线图一个里程碑（M1 到 M5）写一份 checkpoint 到对应 trellis 任务目录，格式沿用现有 checkpoint 文档。
2. 新工作按执行计划 v2 的 R0.x 到 R8.x 编号创建 trellis 任务；R1.1 与 R1.2 完成前不进入任何 10.6 续接工作。
3. 遇到本提示词和四份文档都没覆盖的新决策点：涉及科学规则、来源权威、用户可见行为变化的，暂停并列举选项请用户裁决；纯实施细节自行决定并在 checkpoint 记录理由。
4. 第一条动作是只读的：重算 handoff 第 5 节 8 个文件的 SHA-256 确认现场未被外部改动，然后从 R0.1 开始。

七、关键提醒
1. 审计发现你的检查点曾声称 mypy 通过而实际全仓有 77 错（按文件局部通过被当成全局通过）：这就是 gate 命令和"声明的检查范围"必填字段要堵的洞，先堵洞再做别的。
2. Phase 6 之后提交纪律失效是最大的工程风险，R0.3 的分组提交是整个续接工作的地基。
3. 治理材料（metrics/reviews/plans/context）只增不改存量，R8 方案批准前不要清理。
4. 路线图预估：M1 第 1 周、M2 第 2 周、M3 第 3 周、M4 第 4 周、M5 第 5-6 周；进度落后时砍 R4.4-R4.6（视反馈排入的功能），不砍 R0-R2 和 R5。
