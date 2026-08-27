Delegated mode
MODE=CONFERENCE
Conference role: 真实医学经理视觉复核者

本轮是同一会话的定向复核。上一轮你拒绝了疗效筛选与图题不同步、境外监管卡混入中国状态。请只核对这两项是否在新运行中真实修复，并确认修复未破坏默认疗效视图、清除筛选和监管双轨。

Hard boundaries:
- 只读，不修改任何文件。
- 必须真实打开当前站点并操作，不能沿用旧截图或仅信自动化结果。
- 使用 1280×800 与 1920×1080 视口。
- 不做安全性测试，不扩展到第 6 阶段。
- 当前源码提交是 `95fcbcdbf74c0899dc58bfca6757e67863e408f0`，运行标识是 `run_f46cc71857dda02de3ff06bf`。
- Runner-managed report path: `runs/conference/ci_phase5_task55_visual/visual_grok_medical_manager_final.md`. Never write that report path with tools.

Read these files only:
- `.artifacts/a-fresh-source/reports/A/v1/html/efficacy.html`
- `.artifacts/a-fresh-source/reports/A/v1/html/regulatory.html`
- `.artifacts/a-fresh-source/reports/A/v1/html/assets/report-a.js`
- `.artifacts/a-fresh-source/reports/A/v1/html/data/report.js`
- `.artifacts/a-fresh-source/verification/A/v1/report.json`

必须实际完成：
1. 疗效页只选“IGA 0/1且改善≥2分”与“第12周”，确认终点和时间点各只有一个选中项，图题、图的无障碍名、表格与空态都与当前选择一致，不残留旧 EASI-75 图。
2. 点击“清除筛选”，确认恢复“EASI-75 / 第16周”及对应图题。
3. 监管页检查度普利尤单抗、阿布昔替尼等境外卡，不得再出现“中国已获批”；有境外证据时只保留美国/欧盟状态，无境外证据时明确“境外状态未核实”。
4. 检查中国卡仍保留中国状态，双轨未被合并。

输出必须只有：Decision: ACCEPTED 或 REJECTED；Reviewed run/site/verify digest；实际操作证据；P0/P1；可选 P2/P3。只有上述两项仍会误导医学判断时才列 P1。
