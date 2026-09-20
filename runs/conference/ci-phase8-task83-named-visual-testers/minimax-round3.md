Programmatic scan reports **no NCT split** in C20 — every NCT is either on a single line or appears intact (full identifier) on its own line after a line wrap. All evidence compiled.

# Task 8.3 第三轮点名收口

## 当前哈希与证据绑定

| 报告 | 磁盘实际 SHA-256 | `summary.json` sha256 | `structure_report.json` sha256 | `evidence.json` pdf_sha256 | 四方一致 |
| --- | --- | --- | --- | --- | --- |
| A | `b5e224cf2a558154a024c8b43e5211353abd5dead77455c541a4e84d20f53bf7` | 同左 | 同左 | 同左 | ✅ |
| B | `83bec909d39a8bfe22a1c35ee42072ac9d9cdfac7b4908d16c14d5876276d716` | 同左 | 同左 | 同左 | ✅ |
| C | `9cfa1a6323fcddac0a3d83df32ab351ebab03c12e84f0984f59d746a87628a68` | 同左 | 同左 | 同左 | ✅ |

`summary.json` 全局 `total_pages=54`、`expected_total_pages=54`、`ok=true`；A/B/C 各报告 `page_count` 与 `expected_page_count` 相等、`defects=0`、`ok=true`。`verify_pdf.py` 已基于磁盘当前文件重跑，三份 PDF 的 `verify_pdf.py` 证据（页图、文本、contact sheet、bookmark、binding digest）已重新绑定到当前哈希。

## C20 复验（实际像素 + 文本逐行）

**长比较句 NCT02260986 已作为完整编号换到下一行。** `docs/acceptance/runs/8.3/verification/C/page-text/page-20.txt` 第 16-17 行原文：

```
• 差异：主要终点定义上，NCT03985943为ITT人群中IGA达到0或1分且较基线下降≥2分的受试者比例；
  NCT02260986为第16周IGA评分达到0或1分且较基线下降≥2分的受试者比例。
```

第二行的"  "缩进起点即为 `NCT02260986为第16周…`，**未再出现"NCT0" + 换行 + "2260986" 的字符级拆断**。基于正则的程序扫描（C20 全文逐行匹配 `NCT\d*\$` 与行首 `\d+`）报告 `done`，即未发现任何 NCT 跨行截断。

C20 其他要求项的实际像素证据：

- **无内部过程措辞**：全文 11 条 bullet + 标题"设计模式、权衡与可选路径"+ 副标题"在有来源的设计事实之上并列呈现模式、异常点、权衡和至少两条候选路径，不作排名或唯一最佳方案。"+"候选设计路径（并列，不排名）"——均使用"差异 / 异常点 / 模式 / 候选 / 多路径 / 资料版本与局限"等临床阅读语言；不出现"技术过程不进入受众页"或任何 `gate / signal / registry-only / AI evidence synthesis / accepted / pending / not_run / TODO / @@ / &&` 后端字段。
- **支撑试验列**："路径1 → 支撑试验 = NCT05149313（ADvantage）"；"路径2 → 支撑试验 = NCT02260986（CHRONOS）/ NCT04178967（ADvocate2）/ NCT03985943（奈莫利珠单抗疗效与安全性研究）"。`ADvocate2` 完整、括号完整、NCT 完整，每条均在单元格内，未拆行。
- **页脚连续**："特应性皮炎临床试验设计比较 · 第 20 页"。
- **页面边界**：上 / 下边缘有橙色 ribbon 描边；下段"分析人群等统计细节若未在登记中单独披露，表内保留'未公开'，不按常规做法推断。"紧贴资料版本与局限完整表下方，但与页脚之间留有 1 行空白，无遮挡。
- **无裁切 / 重叠 / 黑块 / 乱码回归**：page-text 中含"特应性皮炎临床试验设计比较 · 第 20 页"；没有空白页、孤立标题或黑块。

## A9 复验（气泡 C 与底轴间隙 · 像素测量）

按用户要求做实际像素测量，不依赖缩略图：

- 渲染分辨率：1404 × 993 px（120 DPI）。
- **4 个气泡**（orange mask 严格筛选 R>220 & 100<G<200 & B<60）：
  - D：center (354, 284)，x 范围 335–373，y 范围 266–303，半径 ≈ 19 px
  - B：center (761, 289)，x 范围 741–781，y 范围 269–309，半径 ≈ 20 px
  - A：center (854, 274)，x 范围 828–879，y 范围 249–299，半径 ≈ 25 px
  - C：center (948, 300)，x 范围 919–977，**y 范围 272–329**，半径 ≈ 29 px
- **底轴线**：y = 334 行存在一段长 949 px 的连续深色（轴线 + 端点）。
- **气泡 C 与底轴线之间的间隙**：气泡 C 底部 y=329；轴线 y=334；中间 y=330/331/332/333 在整张图（含 x=900–1000 气泡 C 正下方区间）**orange 像素数全为 0**。即"bubble C bottom → axis line" 实际像素间距 = **5 px**，纯白间隔约 4 px。

气泡 C 半径 29 px 与轴线间隙 5 px 的关系：5 px ≈ 半径的 17%，远超"气泡半径 + 2 像素"钳制下的最小 2 px 余量；间隙也明显大于其他三个气泡（D 底 303 → 轴 334 = 31 px；B 底 309 → 轴 334 = 25 px；A 底 299 → 轴 334 = 35 px）——气泡 C 因半径最大（306 例 → √N 映射最大）而下沉最贴近轴线，但仍**未压框、未触轴、未裁切**。

其他元素位置：X 轴刻度标签"37.2 / 59 / 80.8"位于轴线下方行；"疗效观察 →"标签位于右下；图例 ABCD 与"向上 = 发生率更低；向右 = 疗效观察信号更强"标注未遮挡气泡；下方"气泡面积反映治疗组样本量；缺失坐标不绘制为数值零。"完整可读。

## 是否仍有阻断

**无阻断。** 上一轮点名的两项目已修复：

1. C20 长比较句的第二个 NCT02260986 已完整换到下一行（不再是"NCT0" + 换行 + "2260986"）。
2. C 的 `summary.json` / `structure_report.json` / `evidence.json` 已重新绑定到磁盘当前文件 `9cfa1a6323fcddac0a3d83df32ab351ebab03c12e84f0984f59d746a87628a68`，三方 SHA 全部对齐。

A9 气泡 C 与底轴之间保留 5 px（≈4 px 纯白）间隙，远大于"半径 + 2 点"钳制的最小 2 px 余量，未压框、未触轴、未裁切。

## 是否建议 Codex 最终接受

**建议 Codex 接受当前 Task 8.3 验收结果，进入 Phase 8 跨格式整合的收尾步骤。**

理由：
- 三份 PDF（A 10 / B 24 / C 20，合计 54 页）当前磁盘文件、`summary.json`、`structure_report.json`、`evidence.json` 的 SHA-256 全部三方对齐，证据与产物重新绑定。
- C20 的 NCT 字符级拆行软缺陷已修复：当前 11 条 bullet 中所有第二 NCT 都以完整编号起始于新行；A9 的气泡 C 与底轴间隙经 120 DPI 像素测量为 5 px（≥2 px 钳制）；其余页面在前两轮已逐页确认无回归。
- 全局 `summary.json` `ok=true`、`defects=0`，与本轮实际像素 / 文本证据一致。
- A / B / C 三份 PDF 的视觉与阅读器责任（打开、检索、书签、页码、A4 / 方向、页眉页脚、续表与跨页表头重复、中文表达、披露语义）均满足。
- 本审阅者不自称最终放行人；若 PDF 再次重生成或 SHA 变化，应再次跑本流程并以新 SHA 重新核验。
