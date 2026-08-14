复验同一 Task 5.1，保持只读，不修改文件。请读取当前最新 `src/ci_workflow/reports/a/*` 与 `tests/reports/a/*`，重跑你上一轮的全部 P0/P1 反例；不要依赖主代理或 worker 的“已修复”声明。

重点确认：
1. 无真实数值、无正分母、未接受事实、错误来源/作用域不能满足疗效或 TEAE/SAE 最低记录。
2. 调用方不能填写 maturity/result-bearing/basis；官方 Results posted 证据必须解析到同一 accepted ClinicalTrials registry binding，而非任意事实号。
3. 核心试验、锚定试验、疗效/安全性事实必须属于同一产品和适格试验；试验级/终点级绑定不会被产品筛选器误删。
4. 安全事件类别由封闭 `unit_id` 判定，发生率单位仍保存为 `%` 等真实单位；把 `teae` 写入 unit 不得通过。
5. 单项目直接评估也要求闭合 snapshot；重复/空/不匹配宇宙失败关闭；监管事件不跨记录拼接；不适用规则正确。
6. 生成的阻断说明不含“门槛、竞品宇宙、基础层、blocked/missing/result_bearing”等后端或提示词语言，且能告诉用户缺什么、补齐后可继续。

运行专项测试与必要的只读反例。只输出：PASS 或 REVISE；剩余 P0/P1/P2（精确证据）；通过的反例清单；仍需主代理确认的边界。
