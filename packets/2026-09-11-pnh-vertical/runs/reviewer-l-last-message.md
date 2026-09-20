## 结论：rejected

## K 五项复查（逐项）

1. **背景药同义词清理：未完全闭合。** 六个原始问题词已不再形成产品实体，但 `rabbit atg`、`lapine t-lymphocyte immune globulin`、`muromonab` 等变体仍进入宇宙。
2. **SB12 生物类似药误伤：已闭合。** `sb12` 已恢复，NCT04058158 及其结果均归入 `sb12`。
3. **剂量/频次变体：已闭合。** `NTQ5082 100mg qd`、`200mg qd`、`200 mg` 均归入 `ntq5082`。
4. **`soliris/ultomiris` 复合名：名称层面已闭合。** 未见复合字符串独立成产品；NCT07413250 在 sidecar 中归入代表性规范名 `eculizumab`。
5. **`Part1/Part2: TUL321` 前缀：已闭合。** 当前产品为干净的 `tul321`。

## 新可修复错误

1. **背景/移植预处理变体残留：** `rabbit atg`（NCT06412497）、`lapine t-lymphocyte immune globulin`（NCT04965597）和 `muromonab`（NCT00566696）仍被建成产品。
2. **结果错归属：** NCT00566696 的 EFS、OS、DFS 及严重不良事件（`eff-175`–`eff-177`、`safe-60`）归入 `muromonab`，但原登记描述的是多药移植预处理/移植物处理方案，不能形成 muromonab 的药物特异性结果。
3. **别名未归并：** `ach-0144471` 与 `danicopan` 未合并；NCT03053102 将 ACH-0144471 列为 Danicopan 别名，且 NCT03181633 的安全性结果术语直接为 Danicopan。
4. **规范身份未归一：** `humanized anti-factor bb monoclonal antibody` 未归入同一记录标题及别名明确的 `SAR443809`；`OMS906` 与同记录别名 `zaltenibart` 也未按 alias-map 的规范名规则统一。
5. **黑名单误伤风险仍在：** NCT03866681 的 `sirolimus`、NCT01642979/NCT01760096 的 Levamisole 联合方案因粗粒度字符串规则整体排除；这些明确涉及 PNH 治疗的再定位/边界方案至少应有独立纳排审查，不能静默丢弃。

## 裁决理由（按 K 框架）

当前载荷数量和结构核对通过：46 产品、134 试验、234 疗效、80 安全、55 申办关系；sidecar 为 5 条样本量缺失、50 条无独立药物、139 组联合组合。

但上述问题属于可由当前官方登记材料和载荷确定修复的实体分类、别名归并、误伤及结果关联错误，不是 G11-1 联合关系限制、中国路线 `access_blocked`、CT.gov 当前快照无历史宇宙或 G12-1 黑名单分类器演进可以豁免的已披露限制。

应先补充结构化干预角色/创新边界分类，扩展别名映射，移除 NCT00566696 的错误产品级结果关联，重新生成载荷、sidecar 和审计包，再进行独立终审。

## 观察意见（原样进入 scientific_review.observations，中文，≤5 条）

1. R17 已闭合 SB12 恢复、NTQ5082 剂量归并及 TUL321 前缀清理；当前载荷结构计数核对通过。
2. `rabbit atg`、`lapine t-lymphocyte immune globulin` 和 `muromonab` 仍属于移植预处理或背景干预污染。
3. NCT00566696 的移植结果仍被错误投影为 muromonab 产品结果。
4. `ach-0144471`、`SAR443809` 泛称及 `OMS906/zaltenibart` 的身份规范化仍未完成。
5. G11-1、G7-2、中国路线访问受阻及当前快照限制可以披露，但不能豁免本轮已确认的实体分类、别名和结果关联错误。

