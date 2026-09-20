Delegated mode（执行模块角色：只读独立复核节点 Reviewer-F）

# 硬边界

只读评审（read-only）；不修改文件、不跑 pytest；唯一工作区 /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow；禁止访问旧中文工程；结论基于亲自读到的代码行。

# 评审对象：P3.3 时间政策统一（今日落地）

变更前：`compare_clinical_constructs` 时间维度用全局硬编码 `delta > 2.0` 周（semantic_contract.py 旧 246 行），与 policies/timepoints YAML 的窗口归类（48–56 同属 week-52 窗）是两套不一致机制（Reviewer-E P1）。

变更后：
1. contracts.py `TimepointCompatibilityRule` 新增 `comparison_tolerance_weeks`（默认 2.0，有限正数校验，别名 tolerance_weeks/near_window_weeks）。
2. policies/timepoints/compatibility-v1.yaml version 1.0→1.1，5 条规则显式 `comparison_tolerance_weeks: 2`。
3. semantic_contract.py：`compare_clinical_constructs(..., timepoint_policy=None)`；新 `_default_timepoint_policy()`（lru_cache 默认加载）与 `_resolve_timepoint_rule(observation, policy)`（同单位值比较、闭区间、命中必须唯一否则 raise）；时间判定改为：双侧命中规则且 rule_id 相同 → |Δweeks| ≤ 该规则容差才可比；任一未命中或异规则 → 不可比（理由含政策 ID/版本/规则 ID/容差）。
4. 合同测试 tests/reports/b/test_versioned_time_policy.py 7 项（13↔15、8↔10 旧放行现拒绝；48↔50 同窗容差内可比；48↔56 同窗超容差拒；政策容差调 4 时 48↔52 可比、默认下拒；12↔48 异规则拒；政策文件版本与逐规则容差声明）。

主线程已运行：政策合同 7/7、B+application 321 绿、integration+浏览器 865 绿、gate 六步绿。

# 裁决问题

Q1 语义正确性：新判定（双侧命中+同规则+规则容差内）与 v1.3 §"48/50 周等近窗口按医学语境处理，不把固定阈值套全部终点"的合同方向是否一致？收紧（窗外观察不再被 ±2 放行）是否引入了违背医学语境的过拆（例如 day/month 单位观察跨规则的正当情况）？
Q2 单位换算：Δweeks 用 timepoint_weeks（day/7、month×4.34524、year×52.1429）与规则单位匹配按枚举值——跨单位同观察（如 day-28 vs week-4）现在必然异规则/未命中 → 拒。这方向保守是否可接受、有无被错误放行的组合？
Q3 唯一命中 raise：区间重叠政策会 raise ValueError 而非拒绝比较——在 compare_clinical_constructs 的消费面（complete-link compatible() 的 except ValueError→False、semantic_review_task 无捕获）是否安全？
Q4 缓存与注入：lru_cache 默认政策 + 测试注入 timepoint_policy 的交互；渲染/审阅链路是否有路径绕过政策参数仍走旧语义。
Q5 兼容性：policy version 1.1 + schema_version 仍 1.0；旧政策文件（无容差字段）默认 2.0 加载——与研究包/回执中 policy 版本绑定是否产生漂移风险。

# 输出格式（严格）

## 结论（一句话）
## 发现清单（[P0-P3]+文件:行+影响+最小修复；无则"无"）
## Q1-Q5 逐项（结论+证据）
## 范围声明
