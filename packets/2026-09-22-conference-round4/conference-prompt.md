# 独立会商任务：round-4 收包裁决与根因分析

你是独立会商者，与生产会话（GLM/ZCode 主线程）和五路测试者均无共享上下文。你的产出是裁决备忘录：逐项审阅测试发现，复验真伪，深挖根因，举一反三，给出修复排期。不臆测——每项裁决必须带文件:行号或探针复验证据。

## 工作目录
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

## 输入证据（全部真实存在，先读再裁）
- 三路科学复核 verdict：`runs/pnh-vertical/abc-v97/state/scientific_review/{A,B,C}/verdict.json`（A r43 六项 / B r57 三项 / C r41 七项，均 veto）
- 对抗测试：`runs/test-round4-grok/findings.json`（grok-4.7，73 探针 62 过，findings F01–F09）
- 用户旅程：`runs/test-round4-cursor/findings.json`（cursor，overall=fail，5 项交互缺陷 + chinese_native_violations）
- 被测提交：f3ba4d3（R01–R13 修复），v97 产物 `runs/pnh-vertical/abc-v97/reports/`
- 上游纠偏背景：`/tmp/ci_v96_review/CI_workflow_v96_review/REVIEW.md`（如存在；不存在则跳过）

## 会商要求
1. **裁决表**：每条发现给状态（成立/不成立/部分成立/已修复）+ 复验证据（可运行探针或文件:行号）。特别复核 grok F01（crosswalk 期别借用路径）、F02（any_sae 规则先于停药/治疗相关命中）——生产者需知是否为真缺陷。
2. **根因分层**：区分 渲染器显示层 / 构建器投影 / 合同模型 / 政策数据 四层；同族问题合并（如"A/B/C 三报告各有一套组名/类别显示转换"是否同根）。
3. **举一反三**：对每类根因，推演下一适应症（IPF/糖尿病）是否会复现，给出结构性修法而非逐页补丁。
4. **修复排期**：按"阻断科学复核收敛 > 数据事实正确性 > 中文原生 > 交互观感"排序，每项给规模（S/M/L）与验证方式；明确哪些项属于已定的 R10 产品闭环主线（不重复排期）。
5. 产出写入 `packets/2026-09-22-conference-round4/conference-memo.md`（结构参照 `packets/2026-09-21-conference-round2/conference-memo.md`：假设、裁决表、根因分析、泛化风险、排期、一句话结论）。

## 执行纪律
读到本提示词立即开始执行；不提问、不等待、不创建任务；所有歧义自行决策并记录在备忘录"假设"节；完成后正常退出（退出码 0）。
