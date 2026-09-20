Delegated mode（执行模块角色：独立宇宙遗漏审查节点 Reviewer-K，第五会话，独立于生产者与 Reviewer-G/H/I/J）

# 硬边界
只读评审（read-only 沙箱）；不修改文件；唯一工作区 /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow；禁止访问旧中文工程。

# 任务：PNH 宇宙第五轮独立终审（R16 载荷）

四轮拒绝循环后的 R16 修复（统计数字自动读取自当前物理载荷，非人工填写）：
- R16-a 主药=来源干预顺序首个（修复 NCT02534909 的 LFG316 结果错归属——现归 lfg316）；
- R16-b 背景/对照/预处理药 11 类黑名单（环孢素/吗替/马法兰/依托泊苷/G-CSF/利妥昔/细胞输注/糖皮质激素类），恢复创新竞品边界；
- R16-c 变体词剔除（infusion/monotherapy/study drug/dose N/part N）+ 双品牌复合窄归并（连字符各段均为已知别名→归首）；
- R16-d result_status 仅对确有结果行的产品设置。

当前载荷（packets/2026-09-11-pnh-vertical/pnh-a-payload.json）：
54 产品 / 135 试验 / 237 疗效 / 81 安全 / 57 申办关系；排除样本量 5 条、无独立药物 49 条、联合组合 140 组

已知边界（载荷与审计包内如实声明）：中国路线 access_blocked（G7-2 执行器未部署）；历史宇宙不在 CT.gov 当前快照；G11-1 载荷单 product_id 模型限制（联合关系在 sidecar 全记录）；G12-1 干预角色结构化分类器未建（黑名单为过渡方案）。

请独立复查（读载荷、derivation sidecar、pnh-alias-map-v1.json）：
Q1 前四轮问题是否全部闭合（抽查：背景药是否已出宇宙？NCT02534909 归属？变体残留？result_status 误标？）。
Q2 新引入错误（黑名单误伤真实创新药？顺序主药在新数据上的错归？）。
Q3 终审：在上述已声明边界内 accepted / rejected？rejected 给必补项（考虑：若剩余问题均为 G11-1/G12-1 等已记档模型层缺口而非本载荷可修数据错误，是否构成"有可证实处置的已知限制"——请明确你的裁决理由）。

# 输出格式（严格）
## 结论：accepted / rejected
## 前四轮问题复查（逐项）
## 新问题（若有）
## 裁决理由（明确说明已知限制是否可接受）
## 观察意见（原样进入 scientific_review.observations，中文，≤5 条）
