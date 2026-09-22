# 独立对抗复测：守卫与分类修复验证 · round-5（grok-4.7 xhigh）

你是独立对抗测试者。round-4 你的 F01–F09 已被会商确认成立并修复（提交 7d16cbb）。本轮复测：重跑你的探针集 + 针对修复新增用例。

## 工作目录
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

## 清洁纪律
产物只写 `runs/test-round5-grok/`（自行创建）；不读其他测试者目录。

## 复测内容
1. **重跑 round-4 探针集**（runs/test-round4-grok/adversarial_probes.py，复制到本轮目录后按需调整）：F01/F02/F03/F04/F05/F06/F07/E05/E06/R12 对应用例应转 pass。记录逐项结果。
2. **新增守卫用例（≥8 个）**：
   - crosswalk：TP 大小写/空格变体归一（tp 1/TP1）；请求不存在期别时 conflicts 是否记录 `requested_period_absent`；单组名称变体（rVA576 vs "rVA576 Coversin"）；"Period 1: X" 前缀剥离
   - classify_safety_concept：`"(TEAEs) of Special Interest"` 括号形态 → aesi；`Grade 3 or 4` → grade_3_plus；`Serious TEAEs` → serious_teae_subset
   - concept_catalog：`row_concept` 对旧词表（治疗期间不良事件/严重不良事件）与新词表（…（登记））双路回推
   - concept 字面扫描：`grep -rn "治疗期间不良事件" src/ --include="*.py"` 与 `assets/*.js`——确认除 catalog/legacy 别名定义处外无概念字面匹配残留（display 标签字典除外，逐一判断）
3. **渲染抽查（ego lite 真实浏览器）**：`runs/pnh-vertical/abc-v100/reports/A/v1/html/matrix.html` 任何TEAE 轴气泡数（round-4 为 0）；`clinical-portfolio.html` 无 `n=null`；B `safety.html` 无 `-declared` 行展示；B `products/eculizumab.html` 有"监管批准事实"两列
4. **写 findings**：`runs/test-round5-grok/findings.json`（overall/probes/regression/visual/findings/assumptions，结构同上轮）

## 执行纪律
读到提示词立即执行；不提问不等待；完成后退出码 0。
