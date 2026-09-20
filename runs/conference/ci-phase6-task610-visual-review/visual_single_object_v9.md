# Conference Participant Output: ci-phase6-task610-visual-review - visual_single_object（v9 增量复核轮）

## Boundary Check

- 只读复核唯一候选 `output/acceptance/task-6.10/b-pnh-current-v9/reports/B/v-fixture-b-pnh-001/html/`，仅另读 `fixtures/positive/b-pnh/inputs/report-data.json` 作真源比对；未修改任何文件，未读其他审阅者输出，不做最终验收。
- 引擎：真实 Chromium（xd://browser）+ 真实 WebKit 26.4（Playwright webkit-2287），均 1024 宽度；本地服务用后已停止。
- 本轮为增量复核，仅覆盖指定的三项修订与两项回归抽查，未重新开展宽泛审查。

## Independent Work Product

### 修订 1：占位提示字号 ≥16px —— 关闭，双内核实测

| 页面 | Chromium title/hint | WebKit title/hint | 全页 <16px 计数 | 横向溢出 |
|---|---|---|---|---|
| `product-trial-profiles.html` | 16px / 16px | 16px / 16px | 0 | 0 |
| `trials/nct04820530.html` | 16px / 16px | 16px / 16px | 0 | 0 |
| `evidence-limitations.html` | 16px / 16px | 16px / 16px | 0 | 0 |

均为运行时计算字号（非样式表声明），上轮 P1-V2r 残留彻底关闭。

### 修订 2：APPLY-PNH 处置真源纠正 —— 关闭，图—表—fixture 三向一致

- fixture 实测：`randomized/received_treatment/completed_treatment/completed_study` = 治疗组 62/62/61/62、对照组 35/35/35/35，全部 `reported_value`。
- `disposition-overview.html` APPLY-PNH 图（1024 截图目检）：柱值 已随机 62/35、已接受治疗 62/35、完成治疗 61/35、完成研究 62/35，橙色=治疗组、蓝色=对照组，类别—组别双行轴标签与柱一一对应，身份同步正确。
- 同页数据表逐行匹配 fixture（8 行 APPLY + 4 行 APPOINT 抽查全中，含 APPOINT 完成治疗 38、完成研究 37）。
- 缺失未画零：图中无"筛选失败"柱（fixture `screen_failure = not_publicly_disclosed`），SVG 内 "0" 文本仅位于 y 轴原点；上轮 62/62 的假对称已消除。

### 修订 3：回归抽查 —— 无回归

- 基线同单位小多图（WebKit）：4 张标题仍为"基线样本量（人）/年龄（岁）/性别（%）/基线血红蛋白（g/dL）"，未回退为混单位单图。
- 按试验拆分完成情况图（WebKit）：`participant-flow.html` 仍为"APPLY-PNH ·"与"APPOINT-PNH ·"双图，横向溢出 = 0。

### 总结论

**本轮未发现新的 P0/P1。** 三项修订全部关闭，两项回归抽查无退化。本角色对 v9 的复核证据链闭合，最终验收权属 Codex。

## Evidence And Assumptions

- 实测证据：fixture `disposition_views.facts` 逐行打印；Chromium 图表 SVG 文本抽取 + 截图目检（已嵌入会话）；表格 12 行逐行比对；占位组件双内核运行时字号；WebKit 基线/流转页标题与溢出。
- 假设：APPOINT-PNH 第二张图未截图目检（数值经 SVG 文本抽取验证为 38/37）[INFERENCE：渲染形式与 APPLY 图同组件]。
- 局限：本轮为增量复核，未重跑 24 页全量扫描（上一轮 v9 全量已通过，本轮 diff 范围外页面未复验）。

## Risks, Gaps, And Verification Needs

- 无新增风险。遗留程序性建议（不阻断）：v9 晋升尚未记入会议 Loop Log；机器门禁建议（<16px 计数、数值标签碰撞阈值、零值冒顶检测）仍待 Codex 采纳。
- 处置数据纠正后，"完成治疗 61 vs 完成研究 62"出现治疗组 1 例"完成研究但未完成治疗"的合理临床路径，图表如实呈现，无需处理。

## Recommended Next Step

1. Codex 可将本角色三轮复核（v7 全量 → v8 定向 → v9 全量+增量）标记为证据闭合，进入 B 类 PNH 候选最终验收。
2. 若 Codex 接受门禁建议，将三条机器检查脚本化并入 `tests/browser/test_b_portal.py` 类回归入口，防止后续纵切复发。
3. 本角色无进一步工作；如同会话需要补验特定页面，可直接指派。
