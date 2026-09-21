# 独立会商任务：竞品调研工作流 round-2 测试发现审阅与根因分析

你是独立会商者，与生产会话无共享上下文。你的产出将作为修复排期依据，必须基于仓库真实文件检查，不得臆测。

## 工作目录
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`（竞品调研工作流仓库）

## 背景
两个独立测试者对工作流做了 IgAN 与 UC 适应症的端到端泛化测试，产出发现：
- `runs/test-igan/findings.json`（grok-4.6/high 测试）
- `runs/test-uc/findings.json`（cursor/composer 测试）
生产侧已对部分发现做了修复（如终点 80 字截断、UC 族规则、report-a.js 交互），但以下交叉项仍待裁决：
1. 分类器跨适应症误匹配：`policies/endpoint-families/registry-v7.yaml`（现版本 v7.4）中 complement/裸 remission/`\biga\b` 规则的排序与门闩问题
2. TEAE 行混入疗效表（IgAN 44 行 / UC 16 行）——A 构建器 SAFETY_DOMAIN 前置问题
3. 矩阵气泡图空态（疗效应答率 + 安全发生率 + 样本量三轴依赖）
4. B/C 构建器不可跨适应症移植（PNH 硬编码）
5. A 渲染器 `_native_endpoint_zh` 肾脏/消化科标签（2026-09-21 已补，见 git log d964b7c 之后的提交）

## 任务
1. 逐条核验上述 5 项在**当前代码**下是否仍然成立（读 policy yaml、`tools/build_a_payload.py`、`src/ci_workflow/renderers/portal/report_a.py`、`packets/2026-09-20-test-round-2/` 相关 payload）；给出"已修复/部分修复/未修复"裁决与证据（文件:行号）
2. 深挖根因：每项归因到架构层（政策/构建器/渲染器/合同）而非表面症状
3. 举一反三：每项推演"若换第 4 个适应症（如特发性肺纤维化）会发生什么"，给出泛化风险清单
4. 产出修复排期建议：按"阻断复核收敛 > 事实正确性 > 泛化能力 > 呈现质量"排序，每项给工作量估计（S/M/L）

## 产出（必须）
写文件 `packets/2026-09-21-conference-round2/conference-memo.md`，中文，结构：
- 裁决表（每项：状态/证据/根因层）
- 根因分析（每项 3-8 句）
- 泛化风险清单（第 4 适应症推演）
- 修复排期建议

## 执行纪律（最高优先级）
- 读到此提示词后立即开始执行，不要创建 Trellis 任务，不要进入规划模式，不要提出任何确认问题或等待回复
- 所有歧义自行决策并记入 memo 的"假设"节
- 完成后正常退出（退出码 0）
