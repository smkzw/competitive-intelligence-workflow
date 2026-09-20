# Task 8.6 视觉调研与采用决定

日期：2026-08-31

## 调研结论

1. McKinsey Global Publishing 的年度图表集合强调用图表解释一个明确问题，并在同一图中把核心数字、变化方向和数据来源组织为可直接阅读的叙事。本项目只采用“主旨先行、直接标注、克制层级、来源就近”的编辑原则，不复制其品牌、配色或版式。
2. Apache ECharts 官方手册把清晰且无歧义的标签视为图表核心，并提供标签避让、截断与换行等能力。当前项目继续使用已有离线 SVG 生成器，但把“标签不重叠、不越界、无需反复对照图例”作为等价验收目标。
3. web.dev 建议高性能动效优先使用 `transform` 与 `opacity`，避免触发布局和重绘的几何属性；本项目已有 FX 合同与此一致，不新增动效框架。
4. MDN 说明 `prefers-reduced-motion` 应移除、减少或替换非必要动态效果；本项目继续要求减少动态效果、导出态和质检态均完整显示静态真值。

## 本轮采用

- 先修直接影响读数的标签间距、引线和数字邻近，再处理阴影、动效等次要美化。
- 柱状图、折线图、热图、气泡图优先直接标注关键数值和系列身份；图例只保留仍有必要的编码说明。
- 单页信息过密时拆图或拆页，不缩小到合同下限以下，不用裁切掩盖问题。
- 不新增第三方库；继续复用项目内已有 SVG、CSS、JavaScript 和康哲 FX 资产。

## 外部依据

- [McKinsey Publishing’s year in charts](https://www.mckinsey.com/featured-insights/year-in-review/year-in-charts)
- [McKinsey Chart of the Week](https://www.mckinsey.com/featured-insights/charts)
- [Apache ECharts 5 visual and label design](https://echarts.apache.org/handbook/en/basics/release-note/v5-feature/)
- [web.dev: Animations and performance](https://web.dev/articles/animations-and-performance)
- [MDN: prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion)
