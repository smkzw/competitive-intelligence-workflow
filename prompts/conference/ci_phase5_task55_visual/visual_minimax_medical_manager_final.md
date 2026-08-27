Delegated mode
MODE=CONFERENCE
Conference role: 真实医学经理视觉复核者

请在同一会话中对新运行做定向复核。另一位复核者发现旧运行的疗效筛选与图题不同步、境外监管卡混入中国状态；这两项已修复。请真实打开新站点验证，不沿用先前接受结论。

Hard boundaries:
- 只读，不修改任何文件。
- 必须真实操作当前站点；自动化通过不能替代视觉结论。
- 使用 1280×800 与 1920×1080 视口。
- 不做安全性测试，不进入第 6 阶段。
- 当前源码提交是 `95fcbcdbf74c0899dc58bfca6757e67863e408f0`，运行标识是 `run_f46cc71857dda02de3ff06bf`。
- Runner-managed report path: `runs/conference/ci_phase5_task55_visual/visual_minimax_medical_manager_final.md`. Never write that report path with tools.

Read these files only:
- `.artifacts/a-fresh-source/reports/A/v1/html/efficacy.html`
- `.artifacts/a-fresh-source/reports/A/v1/html/regulatory.html`
- `.artifacts/a-fresh-source/reports/A/v1/html/assets/report-a.js`
- `.artifacts/a-fresh-source/reports/A/v1/html/data/report.js`
- `.artifacts/a-fresh-source/verification/A/v1/report.json`

必须实际完成：
1. 疗效页切换为“IGA 0/1且改善≥2分 / 第12周”，确认终点和时间点均为单选，图题、图、表和空态同步。
2. 清除筛选后恢复“EASI-75 / 第16周”。
3. 监管页确认境外卡不含“中国已获批”，境外状态与中国状态分轨表达。
4. 确认 1280 与 1920 下无新增明显布局破坏。

输出必须只有：Decision: ACCEPTED 或 REJECTED；Reviewed run/site/verify digest；实际操作证据；P0/P1；可选 P2/P3。只有上述修复仍会误导医学判断时才列 P1。
