# Task 8.2 点名视觉测试上下文

日期：2026-08-31

## 目标

在正式视觉会商与 Codex 终验之外，按用户点名的三条精确路线补充三份彼此独立的“真实医学经理”视觉审评。测试者只读当前 A/B/C 原生 PDF 及其当前页图，不修改实现，不读取其他测试者结论。

## 当前唯一对象

- A：`.artifacts/pdf-complete/reports/A/v-fixture-001/report.pdf`；SHA-256 `1c5a8a47dfc78df468f5aa2b8dec486a9fdc628dde58bf1ab756ef4c91900398`；10 页。
- B：`.artifacts/pdf-complete/reports/B/v-fixture-001/report.pdf`；SHA-256 `4801c4ad5bb72ce7171790bc22035c8b3ac24e3b0305995152d0541bc8b02b4d`；24 页。
- C：`.artifacts/pdf-complete/report-c.pdf`；SHA-256 `667715ae76cde0d72149b9fb4d938541ceea71cd07c0001163bfbd9913938343`；19 页。
- 当前页图：`docs/acceptance/runs/8.2/verification/{A,B,C}/renders/page-*.png`。
- 结构摘要：`docs/acceptance/runs/8.2/verification/summary.json`。

## 验收边界

- 结构绿灯不等于视觉通过。
- 诚实的“未公开”可以接受；疑似漏抽取、错适应症、错试验或错时间点不可因流程跑通而接受。
- 测试者必须检查实际页图，并以用户能否快速读懂、比较和下钻为中心裁决。
- Codex 保留最终视觉、医学和用户交付权。
