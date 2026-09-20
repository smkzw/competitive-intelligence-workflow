---
name: visual-design-director
description: 由竞品调研控制图调用的 HTML 视觉策划能力；为锁定的 A/B/C 报告快照形成绑定康哲设计合同的站点式 HTML 策划书。不得由用户直接调用。
---

# 定稿前视觉策划

## 输入合同

接收已锁定的报告快照摘要、HTML 页面覆盖集合、康哲项目设计合同和受众阅读任务。只读取快照与合同，不接收未经锁定的事实、临床结论或自由主题。

## 输出合同

输出 `visual-finalization-plan` 策划书，并绑定当前报告快照摘要、项目设计合同摘要、HTML 门户路线、资深临床试验医学人员的阅读任务、页面责任、视觉变量、图表/表格语法、交互状态和逐域验收矩阵。策划书由项目内验证器校验后，才能交给 `render-deliver` 生成候选。

## 策划边界

- 只决定信息层级、页面结构、表现形式、文字层级、间距和交互状态；不得改写科学快照、事实、单位、分母、时间点、比较口径、证据等级或科学结论。
- 所有视觉变量必须来自康哲设计合同的有限令牌集合；不得引入任意主题、冷蓝/navy 默认抬头、霓虹色或整页品牌色。
- 唯一路线为 `html / portal`：独立多页面首页与详情责任、全局导航/搜索、筛选与 URL 状态、图表—完整表格同步、证据下钻、Chromium/WebKit 多视口。
- 图表必须声明读者问题和维度—视觉通道映射；热图、气泡图不得只依赖色相。完整折叠表责任必须在表格语法中显式记录。
- HTML 必须显式规划页面加载、筛选、下钻、搜索、键盘和减少动效六类真实使用状态。动效不得承载唯一信息。
- 每个验收域必须写成能在具体页面、组件、截图和交互状态上观察的标准；“符合规范”“视觉良好”“检查通过”等笼统语句无效。

## 输出字段

策划书必须包含：`plan_id`、`report_kind`、`report_version`、`format`、`route_id`、`report_snapshot_sha256`、`report_snapshot`、`design_contract_sha256`、`design_contract`、`scientific_snapshot_immutable`、`audience`、`page_responsibilities`、`visual_variables`、`chart_syntax`、`table_syntax`、`interaction_states`、`acceptance_matrix`、`planner_identity`、`planner_role` 和 `created_at`。其中摘要与合同摘要只能描述绑定身份，不能成为事实副本或新的科学真源。

## HTML 门户最低策划责任

- `html / portal`：多页面首页与详情责任、全局导航/搜索、筛选与 URL 状态、图表—完整折叠表同步、证据下钻、键盘焦点回返、减少动效和 Chromium/WebKit 多视口。

## 禁止行为

不得从未锁定快照猜数、补数或复制兄弟报告数字；不得在策划阶段生成候选产物、写入 `accepted`、修改快照或替代 `render-deliver`/`visual-package-qc` 的职责；不得把“文件存在”“退出码为 0”或“没有横向溢出”当作视觉完成。

## 失败与恢复

策划书校验失败时拒绝进入格式生成节点并保留确定性错误；任何事实或口径漂移都退回快照流程。候选阶段最多三轮定向美化复测；策划书只记录计划，不伪造真实渲染、旧截图或独立审阅结论。
