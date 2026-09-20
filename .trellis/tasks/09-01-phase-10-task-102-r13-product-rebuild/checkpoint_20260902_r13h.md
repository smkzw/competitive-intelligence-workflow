# R13h 无损检查点

## 当前候选

- 路径：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260902-043000-r13h`
- 范围：站点式 HTML；PDF/PPT 暂不集成。
- 浏览器验收：仅 ego(lite)。

## 已完成

- A：产品级图表下钻、详情抽屉、产品档案入口及全空 AESI 隐藏。
- B：临床概念模糊归组、治疗/对照并列比较、产品/试验/组别身份保留及数值下钻。
- C：20 项研究全字段矩阵；从官方登记原始文件恢复完整入排标准；入选 148 条、排除 276 条；条目数量图、完整表及单研究详情联动。
- C 用户语言：单研究详情不再显示内部字段名，来源位置使用中文设计要素。

## 决定性证据

- 确定性测试：67 项通过；JavaScript 语法检查通过。
- ego(lite) 排除标准页：276 行、276 个唯一条目身份、页面无横向溢出；真实点击图中首项后打开 NCT02260986 排除标准依据。
- ego(lite) 单研究页：NCT02260986 展开 2 条入选、12 条排除标准；来源位置显示中文设计要素，内部字段名不可见。
- ego(lite) 全站：114 条路由 × 4 档宽度，共 456 次页面运行，0 个页面级缺陷。
- 截图：`runs/tests/r13-ego/r13h-c-exclusion-final-ego.png`、`r13h-c-exclusion-drawer-ego.png`、`r13h-c-trial-detail-final-ego.png`。

## 尚未完成

- 三位指定独立测试者尚未对 R13h 完成同会话 ego(lite) 复审。
- 执行包审计与视觉会商校验尚未闭环。
- R13h 为视觉/产品候选；在复审稳定前不标记最终产品验收。

## 下一安全动作

续接 MiniMax、ZCode、Gemini 原会话，进行只读、ego(lite) 限定的真实医学经理复审；任何新问题进入 R13i，不覆盖 R13h。
