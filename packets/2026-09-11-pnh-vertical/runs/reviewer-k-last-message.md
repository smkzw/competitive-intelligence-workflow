## 结论：rejected

## 前四轮问题复查（逐项）

- 统计核对通过：当前载荷为 54 产品、135 试验、237 疗效、81 安全、57 申办关系；sidecar 为 5 条样本量缺失、49 条无独立药物、140 条组合记录。
- R16-a 已闭合：NCT02534909 归属 `lfg316`；其 4 条疗效和 2 条安全记录均归 `lfg316`，sidecar 保留 `iptacopan` 与 `lfg316`。
- R16-b 未闭合：显式名称虽多数被排除，但同义词/商品名仍进入宇宙。例：`anti-thymocyte globulin`、`l-phenylalanine mustard`、`rituxan™`、`thioplex®`、`treosulfan`、`sargramostim` 等。
- R16-c 未闭合：仍有 `ntq5082 100mg qd`、`ntq5082 200mg qd`、`ntq5082 200 mg` 三个剂量变体；`soliris/ultomiris` 未按已知别名归并；`Part1/Part2: TUL321` 残留为异常名称 `: tul321`。
- R16-d 仅机械闭合：所有有疗效/安全行的产品均标记“已有部分公开结果”，其余为“暂无公开关键结果”；但错误保留的背景/预处理药本身携带结果，故产品级结果状态仍然语义错误。NCT00566696 的移植相关结果被归至 `thioplex`，NCT00856388 的结果被归至 `anti-thymocyte globulin`。

## 新问题（若有）

- 黑名单存在误伤风险：NCT04058158 的真实干预 `SB12 (proposed eculizumab biosimilar)` 因名称包含 `eculizumab biosimilar` 被整体过滤；若竞品定义包含生物类似药/竞争性开发项目，该实体发生漏纳。
- 黑名单也漏过多个背景、移植预处理或支持治疗同义词，导致创新药宇宙污染。
- `soliris/ultomiris` 同时涉及两个已知别名，当前作为独立产品保留，既未归并也未拆成完整关联。

## 裁决理由（明确说明已知限制是否可接受）

G11-1 单一 `product_id` 的联合关系限制，在 sidecar 完整保存组合关系并如实披露的前提下，可以作为已知限制接受；中国路线 `access_blocked` 和 CT.gov 当前快照不含历史宇宙，也可作为明确披露的范围限制。

但 G12-1 不能作为本轮放行理由。当前问题不是单纯不可避免的模型缺口，而是可由现有来源和载荷确定修复的实体分类、别名归并和结果关联错误。必须补充结构化干预角色分类或等效的明确处置规则，修复背景/预处理药、剂量/阶段变体及复合别名后，重新生成载荷、sidecar、审计包并再次独立终审。

## 观察意见（原样进入 scientific_review.observations，中文，≤5 条）

1. NCT02534909 已正确归属 `lfg316`，相关疗效和安全记录未再错归 `iptacopan`。
2. 当前载荷仍纳入 `anti-thymocyte globulin`、`thioplex`、`l-phenylalanine mustard`、`rituxan`、`treosulfan` 等背景或移植预处理干预。
3. `ntq5082` 剂量变体、`soliris/ultomiris` 复合别名及 `: tul321` 名称残留，说明 R16-c 尚未完成实体规范化。
4. R16-d 的状态赋值规则机械通过，但错误保留的背景药已承载疗效和安全结果，产品级结果语义仍不可靠。
5. G11-1、访问受阻和历史快照限制可在明确披露下接受；G12-1 不能豁免本轮已证实的可修复数据错误。

