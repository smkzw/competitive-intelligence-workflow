# ADR 0012：定稿前视觉策划与独立放行闭环

- 状态：已实施
- 日期：2026-08-29
- 范围：站点式 HTML、原生 PDF、HTML-PPT、可编辑 PPTX

## 决定

四种格式均不得从锁定快照直接进入正式交付。每个格式先形成绑定当前快照和项目设计合同的视觉策划书，再生成候选、真实渲染、诊断并定向美化；最多三轮后由隔离的视觉审阅者裁定。通过后才建立正式清单并放行。

视觉层不得改写科学真源。若美化需要改变事实、单位、分母、时间点、比较口径或证据状态，必须退回快照流程，而不是在页面中“优化”。

## 研究依据与项目转译

1. GOV.UK 设计系统以有限字号刻度和 5 px 倍数的行高、间距刻度建立一致垂直节奏；项目据此要求字号、行高与间距来自项目令牌，不允许卡片逐个自由取值。来源：https://design-system.service.gov.uk/styles/type-scale/ 与 https://design-system.service.gov.uk/styles/spacing/
2. W3C WCAG 2.2 要求普通文字至少 4.5:1 对比度、200% 缩放不丢内容、重排、非文字对比和焦点不被遮挡；项目把这些作为最低机器检查，而非附加美化项。来源：https://www.w3.org/TR/WCAG22/
3. Apache ECharts 将数据映射到颜色、大小、透明度等视觉通道，并提供 ARIA 描述和纹理作为颜色之外的辅助编码；项目要求每个图表声明维度—视觉通道映射，热图/气泡图不能只靠色相。来源：https://echarts.apache.org/handbook/en/concepts/visual-map/ 与 https://echarts.apache.org/handbook/en/best-practices/aria/
4. Material motion 强调短而自然、按移动距离调整时长；View Transition API 的价值是帮助用户在状态变化中保持上下文。项目只对弹层、筛选、下钻和页面状态变化使用短动效，并提供减少动态效果。来源：https://m1.material.io/motion/duration-easing.html 与 https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API
5. McKinsey 的年度图表集合展示以图表回答单一问题、突出关键数据和邻近呈现来源的编辑方式。项目只吸收“主旨先行、直接标注、克制配色、减少无效装饰”的原则，不复制品牌视觉。来源：https://www.mckinsey.com/featured-insights/year-in-review/year-in-charts
6. WCAG 2.2 的最小指针目标为 24×24 CSS px，且颜色不能作为唯一信息通道；项目据此把筛选按钮、下钻入口和图中数值命中区纳入真实浏览器验收。来源：https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html 与 https://www.w3.org/TR/WCAG22/#use-of-color
7. W3C 对交互动效建议支持用户的减少动态效果偏好；项目禁止不可关闭的非必要位移动画，并在视觉验收中单独检查 `prefers-reduced-motion`。来源：https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions
8. Apache ECharts 的 `visualMap` 明确将数据维度映射到颜色、大小等视觉通道；项目要求热图数值直接标注、气泡大小绑定治疗组样本量，并用文字或边框补充颜色编码。来源：https://echarts.apache.org/handbook/en/concepts/visual-map/

## 不采用的方案

- 不增加一套任意主题或“酷炫模式”；动效和阴影必须服务状态与层级。
- 不把全部规则堆入一个生成提示词；策划、生成和独立验收各自有类型化输入输出。
- 不用 Lighthouse、截图存在或无横向滚动作为单一完成信号。
- 不让生成者写入 `accepted`，不让旧截图或旧清单为新产物背书。

## 恢复边界

单一格式三轮后仍不合格时只阻断该格式，并保存当前候选、缺陷和最短恢复动作；已独立通过的其他格式不撤销。正式 Phase 8 产物生成前必须先通过本合同。

## 实施结果

- 视觉策划书、真实呈现证据和独立视觉结论均已形成项目内 JSON Schema，并提供源码树与安装包副本。
- HTML 放行要求 Chromium/WebKit × 768/1024/1440 完整组合；每个呈现目标分别完成页面加载、筛选、下钻、搜索、键盘和减少动效检查。
- 响应式布局中暂不直接显示的必需字段必须有已实际验证的用户可见替代入口；遮挡、裁切、不可读标签、工程化文字和开放阻断缺陷均失败关闭。
- 状态图直接验证嵌套呈现证据和七域独立结论，并以规范摘要绑定当前候选、策划书、格式及生成/审阅身份；纯布尔标志不能放行。
