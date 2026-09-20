## 结论（一句话）

不建议无条件通过：核心时间语义方向正确，但政策身份绑定和异常失败关闭仍有 P2 风险。

## 发现清单（[P0-P3]+文件:行+影响+最小修复）

- [P2] `src/ci_workflow/reports/b/semantic_contract.py:289-300`：不同规则理由缺政策 ID/版本，超容差理由缺规则 ID及政策身份；影响审计无法精确绑定判定来源；最小修复是统一输出 `policy_id/version/rule_id/tolerance`。
- [P2] `src/ci_workflow/reports/b/semantic_grouping.py:205-221`、`src/ci_workflow/application/semantic_review_task.py:92-117`：`try/except ValueError`未覆盖 `compare_clinical_constructs()`；重叠策略经注入后会异常冒泡并中止渲染/复核任务。正常 YAML 会在 `contracts.py:648-668` 拒绝重叠，故无误合并，但运行失败关闭不完整；最小修复是消费端捕获并返回不可比，或统一转换为可识别的策略配置错误。
- [P2] `src/ci_workflow/reports/b/semantic_grouping.py:105-110`、`src/ci_workflow/application/semantic_review_task.py:56-60,188-193`、`src/ci_workflow/cli.py:586-590`：语义摘要/复核任务绑定的是语义策略版本或首条摘要前缀，不是时间政策 ID/版本；影响政策升级后回执无法审计区分；最小修复是把时间政策 ID、版本及摘要纳入提案/回执/任务绑定，且 CLI 不再覆盖为摘要前缀。
- [P3] `src/ci_workflow/renderers/portal/report_b.py:837-881`：仍保留硬编码 `_time_band()` 时间带；当前科学分区和最终比较仍受政策守卫，未见直接误放行，但展示标签/初始分桶可能与 YAML 漂移；最小修复是从当前时间政策派生展示时间带，或明确其仅为非裁决展示逻辑。

## Q1-Q5 逐项（结论+证据）

### Q1

结论：双侧命中、同规则、闭区间内按规则容差比较，与 v1.3 一致；未见医学语境过拆。

证据：v1.3 明确允许 48/50 周在兼容构念下共框，但要求实际时间差标注，并要求单位或实质时间语境不兼容时拆分（`docs/specs/competitive-intelligence-workflow-design-v1.3.md:381-383`）。实现按同单位闭区间唯一命中（`semantic_contract.py:196-211`），再按同规则及规则容差判定（`semantic_contract.py:282-305`）。因此 day-28 与 week-4 被拒绝属于合同要求的保守拆分。

### Q2

结论：单位换算实现保守且可接受，未发现正常政策下错误放行组合。

证据：周数换算为 day÷7、month×4.34524、year×52.1429（`semantic_contract.py:104-110`）；规则匹配先要求枚举单位值相同（`semantic_contract.py:201-207`），再要求规则 ID 相同（`semantic_contract.py:289-295`）。所以跨单位观察不会因数值接近而放行；同单位边界仍受闭区间和容差约束。

### Q3

结论：配置加载层安全，但消费端异常处理不完整；会失败关闭，不会静默误合并。

证据：政策模型对同单位重叠区间直接拒绝（`contracts.py:648-668`），唯一命中异常在 `semantic_contract.py:209-210` 抛出。所谓 complete-link 的 `except ValueError` 实际只包住观察构造（`semantic_grouping.py:205-208`），比较调用位于其外（`semantic_grouping.py:214,221`）；复核任务同样在 `semantic_review_task.py:103,109,115-117` 未捕获。因此重叠策略经未重验对象注入时会中止调用方，而不是转为 `False`。

### Q4

结论：默认生产路径已走新政策，注入政策不会污染缓存；但缓存可能陈旧，且自定义政策不能传入渲染/复核链。

证据：默认政策由 `lru_cache(maxsize=1)` 加载（`semantic_contract.py:190-193`），注入政策走独立分支（`semantic_contract.py:214-220,279-282`）；complete-link 和复核任务均调用默认比较（`semantic_grouping.py:214,221`、`semantic_review_task.py:103-117`）。门户科学分区也通过无参数 `match_endpoint_compatibility()` 使用默认政策（`portal_science.py:176-179`）。未发现旧 `delta > 2` 仍在比较路径生效，但长驻进程更新政策文件后缓存不会自动刷新。

### Q5

结论：schema_version 保持 1.0 可以兼容旧文件，但时间政策版本绑定只覆盖终点兼容结果，未覆盖语义提案、复核任务和完整回执，存在漂移风险。

证据：新字段默认 2.0（`contracts.py:577-582`），政策 schema 仍限定 1.0（`contracts.py:630-640`），因此无容差字段的旧政策可继续加载；当前 `EndpointCompatibilityResult` 保存政策 ID/版本（`contracts.py:695-698`、`1002-1005`）。但 `SemanticGroupingProposal` 摘要只加入 `SEMANTIC_POLICY_VERSION`（`semantic_grouping.py:105-110`），`SemanticReviewTask.policy_version`也只是语义策略字段（`semantic_review_task.py:56-60,188-193`），CLI 还将其写成首条摘要前缀（`cli.py:586-590`）。当前 1.0→1.1 的有效容差相同，立即决策漂移有限；未来窗口、单位或容差变化时，历史回执无法可靠复现。

## 范围声明

只读完成；未修改文件、未运行 pytest、未访问旧中文工程。结论来自当前工作区实际读取的代码、政策、合同和调用方；主线程报告的绿灯结果未在本节点重复执行。

