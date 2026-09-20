## 结论

第二轮三项修复在真实渲染路径上成立；失败反例调用了会对子集重分组的私有 helper，不是实际档案页回归，但该入口仍有 P2 护栏风险。

## 发现清单

[P2] 产品/overview helper 仍允许子集重分组  
证据：`report_b.py:3119-3138` 按传入记录重新调用各域分组；而真实路径由 `report_b.py:3679-3692、3770-3782` 先建全池再投影。  
影响：未来调用者可绕过全局分组，重现 `tmp/semantic-independent-w1RHFS/test_independent.py:93-107` 的错误合并。  
最小修复：把反例改为真实渲染或 `_project_scientific_groups`；为全池裁决增加显式模式/断言，禁止详情子集进入裁决入口。

[P2] 全池中的孤立提案被静默忽略  
证据：`semantic_grouping.py:110-117` 对缺少任一 row_id 的提案直接 `continue`；全池调用见 `report_b.py:3679-3692`。  
影响：页面局部调用可合理忽略外部提案，但完整观察池中的失效提案没有审计信号。  
最小修复：仅在全池入口要求所有 row_id 存在；页面局部投影保留显式的 partial-proposal 模式。

[P2] 未支持域缺少 fail-closed 校验  
证据：`report_b.py:2586-2607` 会按页面重写已有 `_domain`；`2992-3016` 和 `3119-3136` 只处理已知域，未知域可能被重分类或丢弃。  
影响：错误域记录可能串入错误分组，或从 overview/profile 中静默消失。  
最小修复：入口校验域白名单；已有域与页面域不一致时拒绝，不自动覆盖。

[P2] uncovered 记录缺少科学分组隔离护栏  
证据：`report_b.py:3497-3502` 对 uncovered 记录重新调用 `_groups_for_page`；纵向全池构建见 `3695-3704`。  
影响：当前标准疗效输入全部进入 `trial_series`，但未来残留真实记录可能重新触发跨试验分组。  
最小修复：纵向页对真实 uncovered 记录直接失败；仅允许明确标记的合成/非比较记录走回退分组。

## Q1-Q4 逐项裁决

### Q1

结论：真实产品/试验档案页已满足“全局分组投影”；直接调用 `_groups_for_page` 子集重分组仍构成合同风险。处置应“两者都要”。

证据：

- 全池一次裁决：`report_b.py:3679-3692`。
- 档案页只从 `detail_pool` 筛选后传入全局组：`report_b.py:3770-3782、3828-3841`。
- `_render_page_context` 对 covered 记录调用 `_project_scientific_groups`：`report_b.py:3497-3502`。
- 投影保留原组对象和 `scientific_group_id`，并校验域/摘要：`report_b.py:2748-2768`。
- 失败反例直接调用产品页 helper 的子集分支：`tmp/semantic-independent-w1RHFS/test_independent.py:93-107`。
- 实际浏览器档案页路径已覆盖全局分组投影：`tests/browser/test_b_semantic_proposals.py:50-85`。

### Q2

1. 孤立提案：已有缺陷（全池语境）；页面局部忽略是代码明确允许的行为。证据：`semantic_grouping.py:110-117`。

2. 未支持域：已有输入边界缺陷。正常构建的 `detail_pool` 只打入已知域：`report_b.py:3679-3686`；但 helper 本身未拒绝未知域：`2586-2607、3119-3138`。

3. 同一观察多页投影：已被现有代码防住且属于设计允许。域/事实冲突在单次去重时拒绝：`report_b.py:2036-2052`；跨页投影保留原组：`2748-2768`。纵向页使用独立的纵向组是有意设计：`3693-3704`。

4. overview 拆域一致性：真实路径已防住；overview 直接 helper 仍共享 Q1 的子集重分组风险。真实路径的全池投影见 `report_b.py:3497-3502、3679-3692`；直接拆域分组见 `2992-3016`。

5. 纵向页 uncovered：当前标准构建已防住，因为所有 efficacy 记录都进入 `trial_series`：`report_b.py:3695-3704`；但回退分支本身没有禁止真实记录，属于护栏缺口：`3497-3502`。

6. 合成状态记录与真实记录混布：当前构造路径已防住，属于纯理论风险。产品/试验档案使用 `records or synthetic`，不会混合：`report_b.py:3770-3793、3828-3851`。但 `_synthetic_status_records` 没有显式 synthetic 标记：`2196-2264`。

7. 输入重排/产品切片：重排已防住，row_id 排序使 complete-link 稳定：`semantic_grouping.py:157-164`；产品切片直接重分组未防住，见 `report_b.py:3130-3134`，真实路径则由投影防住。

### Q3

结论：三类修复在当前真实构建路径上均成立，但不是所有私有 helper 调用都具备同等防护。

- 同 ID 跨域/跨摘要：`_project_record` 写入域和 source binding：`report_b.py:1843-1846、1967`；`_dedupe_records` 以域和摘要组成身份并拒绝冲突：`2039-2051`；全池调用发生在写站点前：`3679-3705`。
- 纵向系列：按产品、试验、组别、arm role 先分系列：`report_b.py:3695-3698`；再构造独立 `within_trial_longitudinal` 组：`3699-3704`。
- 跨域正向提案：overview/profile 在分域前检查两端域并拒绝：`report_b.py:2969-2974`；真实全池使用 profile 入口：`3690-3692`。

### Q4

结论：真实渲染路径不会发生；裸调用 `_groups_for_page("longitudinal-results", mixed_records)` 存在可构造场景，会拆开同试验纵向行。

证据：

- longitudinal helper 不包含时间轴：`report_b.py:2975-2982、2801-2804`。
- 同试验同产品、无提案时直接视为兼容：`semantic_grouping.py:125-136`。
- 跨试验仍受时间差守卫约束：`semantic_grouping.py:147-155`、`semantic_contract.py:246-255`。
- 构造 `A@50周、B@50周、A@12周`，并令 row_id 排序为 A@50、B@50、A@12：前两行可进同一跨试验组，最后一行因与 B 相差 38 周不能加入，于是同试验 A@12 与 A@50 被拆开。
- 实际路径先按试验分隔 `trial_series`，因此 B 不会进入同一 helper 调用：`report_b.py:3695-3703`。

## 范围声明

实际读过：

- `semantic_grouping.py` 全文。
- `report_b.py` 中记录投影、去重、语义补全、分组、页面上下文、全池装配及档案页区间。
- `semantic_contract.py` 的模型、unknown 判定和 `compare_clinical_constructs`。
- 两个 tmp 反例文件全文。
- 两个正式语义测试文件全文。
- v1.3 合同及 B 页面目录的相关段落。

未覆盖：

- `report_b.py` 其余未涉及函数、模板和前端 JavaScript 的完整行为。
- 未运行 pytest、浏览器或任何写入命令。
- 本报告是 Reviewer-A 独立复核，不构成最终验收。