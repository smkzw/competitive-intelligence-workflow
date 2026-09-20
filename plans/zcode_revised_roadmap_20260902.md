# 竞品调研工作流 · 修订路线图 v2

- 日期：2026-09-02
- 编制：ZCode 工程审计（依据 `reviews/zcode_ci_engineering_audit_20260902.md` + 用户 2026-09-02 两轮八项裁决）
- 效力：取代原实施计划 §15"阶段执行顺序"中自暂停点（Task 10.6A）起的剩余部分；Phase 0-9 已完成部分的历史与验收记录不受影响
- 配套文档：设计升版 `docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md`、执行计划 `plans/zcode_execution_plan_v2_20260902.md`

---

## 0. 当前基线（截至暂停点，均已核实）

| 项 | 状态 |
|---|---|
| Git | HEAD `bb27ec9`（2026-08-27，Task 5.5）；其后 6 天工作（Phase 6→10.6A）全部在 847 项脏树中未提交 |
| 质量门 | `mypy --strict src/ci_workflow` = 77 错/19 文件；ruff 3 错；`pytest tests/unit` = 536 通过/47s |
| 治理链 | Task 10.5 完成封存；Task 10.6A 进行中（worker_01 被用户暂停中断，报告 PENDING；worker_02/03 完成） |
| 未决合同 | handoff §7 Q1-Q6 未裁决 |
| 真实产物 | AD-A 门户（38 产品档案+12 静态页，多轮视觉打磨）；PNH-B 门户（10.2 真实源）；C fixture 门户（blocked→恢复链验证过） |
| 旧根 | 应只读但已被污染（`verification/` 9/2 写入）；无机械强制 |

## 1. 修订原则

1. **双轨制**：投产轨（真实报告+QC loop）与验收轨（10.6B-D→RC 冻结）并行，第 3 周在 RC commit 处交汇——投产的真实反馈进入 RC，合成 fixture 的信心权重大幅下降。
2. **代码保留、验收摘除**：PDF/HTML-PPT/PPTX 三条格式轨已建成代码不删，仅从首版验收合同移除（formats=4→1）。
3. **gate 先行**：任何续接工作不得在红灯门禁与不可回滚树上进行；P0 修复是一切的前置。
4. **机械防线优先**：git 白名单钩子、旧根 chmod、catalog 的 release_scope 字段，用机器可判定的手段固化裁决，不依赖"严禁事项"清单。
5. **治理不阻塞主线**：治理瘦身由 Codex 按审计 §4.4 材料另行判断，与工程主线并行。

## 2. 里程碑总览

| 里程碑 | 进入条件 | 退出信号（可机器判定） | 预计 |
|---|---|---|---|
| M1 工程恢复 | 无 | gate 全绿（ruff+mypy strict 全仓+unit/contract 测试）；6 天积压分组提交完毕（`git status` 仅剩白名单路径）；Q1-Q6 裁决写入 10.6 design.md；release-scope-v1 落档；旧根 chmod 完成 | 第 1 周 |
| M2 范围收缩落地 | M1 | required-v12 catalog 再生成（formats=1，deferred 案例合法）；full-matrix runner PPTX 分支摘除；12→3 artifact 断言更新；投产轨第一个真实项目 HTML 门户通过 QC loop | 第 2 周 |
| M3 RC 冻结 | M2 + 10.6A 收尾（worker_01 审计+负向测试+A01-A03） | 唯一 RC commit/tag；`RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1` | 第 3 周 |
| M4 分发与切换准备 | M3 + SKILL.md 文案/安装文档/preflight 指引达标 | 首批同事宿主 fresh-install + 关键词触发成功；`CUTOVER_INVENTORY_OK mutated=0` + 用户授权 | 第 4 周 |
| M5 删除与终验收 | M4 + burn-in（≥2 个真实报告项目或 ≥2 周真实使用） | `LEGACY_ABSENT targets=all references=0 shadows=0`；`FINAL_ACCEPTANCE_OK reports=3 formats=1 hosts=3 scenarios=<n> recovery=passed legacy_absent=passed` | 第 5-6 周 |

## 3. 周计划（任务编号对应执行计划 v2）

### 第 1 周 —— P0 修复与投产启动（M1）

| 任务 | 内容 | 关键产物 |
|---|---|---|
| R0.1-R0.2 | 建 gate 命令；修 77 个 mypy 错（pdf_native 系优先）+3 个 ruff 错 | `tools/gate.sh`（或等价）；gate 全绿输出 |
| R0.3-R0.4 | .gitignore 补全；6 天积压按逻辑分组提交；git 白名单检查进 workflow enforcement + task.py finish 钩子 | 干净工作树；钩子生效 |
| R1.1-R1.3 | Q1-Q6 裁决写入 Task 10.6 design.md/checkpoint；写 release-scope-v1；ADR 正名 research-package 检索架构 | 三份合同文档 |
| R1.4 | D71-D78 决策记录（八项裁决入台账） | docs/decisions/ |
| R0.5 | 旧根 `chmod -R a-w`；盘点旧根未迁移资产（`_ref/share_all_msgs.json` 等）在迁移清单中的闭合状态 | 只读旧根；盘点记录 |
| R3.1 | **投产轨启动：第一个真实报告项目**（新适应症，A 或 B 类，HTML only） | 真实项目根 + 首版门户 |

### 第 2 周 —— 范围收缩与 QC loop（M2）

| 任务 | 内容 | 关键产物 |
|---|---|---|
| R1.5 | required-v12 catalog 再生成（release_scope 字段：formats=1、监测 deferred、PPTX 确认 fixture 移除）；acceptance_runner 摘除 PPTX prepare/interrupt/G1-G3 分支；test_full_matrix 12→3 artifact 断言 | catalog v2 + runner v2 全绿 |
| R2.1-R2.3 | worker_01 四文件逐字节审计 → 负向测试补齐 → 10.6A checklist A01-A03 勾选 | 10.6A accepted checkpoint |
| R4.1-R4.3 | F1 research scaffold；F3 表格 CSV/XLSX 导出；F7 安全热图补强（色标图例/对照与分母列/字号） | 三个功能 + 测试 |
| R3.2 | QC loop 固化并在真实项目 #1 上跑通：verify_portal 双浏览器全路由 + 科学 QC 门 + 视觉会商（≤2 轮）+ 用户抽读 | QC loop SOP + 通过记录 |

### 第 3 周 —— RC 收口（M3）

| 任务 | 内容 | 关键产物 |
|---|---|---|
| R5.1 | 10.6B：显式 release source set、Phase 0-10 确定性回归、隔离 clean worktree、唯一 RC commit/tag（投产轨反馈并入） | RC commit/tag |
| R5.2 | 10.6C：`--from-clean-commit` 构建最终 bundle → fresh install → 全新 release root 重跑 fresh A/B/C + full-matrix（formats=1，无 PPT Master 作业） | 当次全部 receipts 绑 RC digest |
| R5.3 | 10.6D：恢复包构建 + 隔离根演练 + owner-stage receipts + 科学/视觉/包/恢复独立验收 → `RC_FROZEN`（formats=1） | 冻结记录 |
| R4.4-R4.6（视投产反馈） | F4 雷达图；F5 证据成熟度矩阵；F8 刷新变化亮点页 | 按反馈裁剪 |

### 第 4 周起 —— 分发、拉取器与切换（M4）

| 任务 | 内容 | 关键产物 |
|---|---|---|
| R6.1-R6.2 | SKILL.md 触发关键词（建议"竞品调研"）+ 最小输入引导 + 安装文档按"产品说明书"标准重写；preflight 失败提示非技术友好化 | 分发就绪的 skill 包 |
| R6.3 | 首批同事宿主分发（fresh-install + 关键词触发验收，三宿主各至少 1 真实入口） | 分发回执 |
| R7.1-R7.2 | CT.gov 拉取器；药智网 connector（joincare 账户本地联调；凭据仅存本地安全配置，不入库/包/日志） | 两个拉取器 + 回执合同 |
| R6.4 | 10.7 切换干运行 + 用户按清单 SHA-256 授权 | `CUTOVER_VALIDATE_OK` |

### 第 5-6 周 —— 删除与终验收（M5，需 burn-in 达标）

| 任务 | 内容 | 关键产物 |
|---|---|---|
| R6.5 | 10.8 精确删除旧根 + absence-check（burn-in 未达标则顺延，不阻塞其他工作） | `LEGACY_ABSENT` |
| R6.6 | 10.9 聚合全量回执封存最终发布 | `FINAL_ACCEPTANCE_OK ... formats=1` |

### 治理轨（R8，Codex 并行，不阻塞主线）

基于审计 §4.4 材料输出治理瘦身方案（证据分层保留、视觉会商上限、worker 拆分条件、metrics 模板必填字段），先方案后执行。

## 4. 双轨交汇点

- 投产轨每个真实项目 = 10.6C"fresh-source"的天然预演；其 research-package、门槛、门户、QC 记录可直接增强 RC 信心。
- 交汇规则：M3 前投产轨发现的缺陷按正常修复流进入工作树（每修复必须过 gate + 提交）；M3 后发现的缺陷进入下一 RC 候选（v1.1），不回退已冻结 RC。
- 投产轨输出物（真实报告）不受验收轨状态约束——用户已确认当前系统即可投产。

## 5. 风险与停止条件

| 风险 | 触发信号 | 处置 |
|---|---|---|
| mypy 修复引入行为回归 | unit/contract 或浏览器测试失败 | 回到该文件修复，不绕过 |
| catalog 再生成破坏旧断言 | test_full_matrix RED 与 formats=1 无关 | 区分"范围变更断言"与"真实回归"，前者更新合同，后者修代码 |
| 真实项目暴露研究包合同缺口 | research-package 校验频繁拒绝合法数据 | 修订 schema（加严不放松），出 ADR |
| 药智网页面/接口变更 | connector 回执 parser_or_schema_failure | 按技术恢复合同降级为"待修复来源"，不阻断其他来源 |
| RC 冻结后仍发现 P0 级缺陷 | — | 不解冻；走 v1.1 候选流程 |
| 治理瘦身与主线冲突 | — | 主线优先；治理动作可整体推迟到 M3 后 |

## 6. 与原实施计划的处置映射

| 原任务 | 处置 |
|---|---|
| Task 8.1-8.6（PDF/HTML-PPT） | 代码保留；验收摘除（release-scope-v1 deferred） |
| Task 8.7-8.9（PPT Master/PPTX） | 代码保留；验收摘除；full-matrix 相关分支删除 |
| Task 8.10 跨格式覆盖 | 降级为 HTML 单格式 coverage 自洽校验 |
| Task 9.3 监测 | 移出范围（catalog 标 deferred；代码保留） |
| Task 10.6A | R2 收尾（worker_01 审计+负向测试） |
| Task 10.6B/C/D | R5，信号改为 formats=1 |
| Task 10.7/10.8/10.9 | R6.4/R6.5/R6.6，10.8 增加 burn-in 前置 |
| Extension E1（LangGraph） | indefinite defer，维持不动 |
