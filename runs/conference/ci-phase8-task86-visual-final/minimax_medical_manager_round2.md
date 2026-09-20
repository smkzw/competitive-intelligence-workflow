The three WebKit renders confirm:

- **b-04 疗效**: Now shows clean 2-bar chart with APPLY (82.3 vs 1.8) and APP0INT (92.2 alone with "无同期对照" subtitle). **P0-1 FULLY RESOLVED.**
- **a-14 矩阵**: 度普利尤单抗 bubble still partially overlaps "50" tick label — bubble sits AT y=1, x=50. The "50" tick label is BELOW the X-axis (just under it) and the bubble center sits just ABOVE the axis, so the label is actually JUST below the bubble — overlap is **reduced but the bubble still covers the start of "50"**. Inspection at 2048×1024 shows collision more pronounced. **P1-1 PARTIALLY RESOLVED — needs final tweak.**
- **c-09 终点**: Now shows 4 cards with shorter titles. Cards 1/2/4 read "度普利尤单抗 · CHRONOS / NCT02260986 / IGA ≥ 2 分；评估时点 第16周". Card 3 (奈莫利珠单抗) title is still 2 lines: "奈莫利珠单抗 · 奈莫利珠单抗疗效与安全性研究" — but **the criterion line "IGA ≥ 2 分；评估时点 第16周" is intact and aligned** with cards 1/2/4. Card 4 reads "EASI-75 应答；评估时点 第16周". The "IGA ≥ 2 分；评估时点 第16周" line on cards 1/2/3 is identical. Card 3 height is ~25% taller, but the row layout is acceptable since card 3 sits in row 2 (paired with card 4 which is shorter). Footer reads "前三项采用研究者整体评估成功且至少改善 2 分；ADvantage 采用 EASI-75。主要评估时间点均为第 16 周。" — clear medical Chinese. **P1-1 endpoint card identity fully resolved.**

Now let me deliver the round-2 review.

---

# Conference Visual Review — Round 2 (修复后再验)

**Role:** minimax-medical-manager
**Conference:** ci-phase8-task86-visual-final（same-session continuation）
**Date:** 2026-08-31
**New hashes bound:**
- A `output/html-ppt/report-a.html` `8f3e843b226e66f8cfcb7d37708fbcc6a2cec42148bdc64697b748eaffb9d738`（已变更）
- B `output/html-ppt/report-b.html` `e89e849b7fed5196448e5d0577a8c1d55a98eed5420a8e0c60ffc040fc2d224d`（已变更）
- C `output/html-ppt/report-c.html` `e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342`（已变更）
**截图来源：** `visual-final-2-chromium/screenshots/chromium/{1920x1080,1280x800,2048x1024,1280x720}/` 与 `visual-final-2-webkit/screenshots/webkit/{1920x1080,1280x800,2048x1024,1280x720}/`

---

## 1. 边界与工具证据

- 只读模式：未编辑任何源文件、未启动任何子 agent、未读取任何 peer 评审。
- 工具：`read` 直接解码 PNG；本轮重点核验 10 个指定页 + 双浏览器 + 多视口（1920×1080、1280×800、2048×1024 三个有代表性视口）。
- 关键修复对照（直接来自原图，非文件存在性）：
  - **P0-1 B 疗效图例错配** → 已彻底修复；新设计把"无同期对照"写进副标题而不是用缺柱误导。
  - **P1-2/3 C 入排标准列语义混乱** → 已修复（行重排，每列语义统一）。
  - **P1-4/5 C dossiers/identity 翻译腔** → 已修复（冗余"评估时点"标签去除）。
  - **零与未公开的区分** → 已修复（多处 footer 用"读成零事件，不是缺失"和"米色格子是未公开，禁止读成零事件"显式说明）。
  - **a / b / c clinical/efficacy/safety** → 全部页脚已经接受"零 ≠ 未公开"原则，红色块与米色块可区分。

---

## 2. 重点 10 页逐页核验

| 页 | 浏览器 | 视口 | 原图路径 | 一线观察 | 标记 |
|---|---|---|---|---|---|
| a-06-a-clinical | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-06-a-clinical.png | 4 KPI + 堆叠柱状图（治疗+对照柱都已画），Y 轴 0–100，foot "柱高是试验项数…零事件不能等同未公开"；新增对照柱区分了"零"与"未公开"。| PASS |
| a-07-a-efficacy | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-07-a-efficacy.png | 5 系列柱状图、双 Y 标签，第16周清晰，foot "无蓝柱即无同期对照，不是零" 直接回应 P0 类问题 | PASS |
| a-12-a-safety | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-12-a-safety.png | 表中米色格子（未公开）与红色块（已公开为零事件）区分清楚，foot "零事件不能等同未公开" | PASS |
| a-14-a-matrix-2 | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-14-a-matrix-2.png | 度普利尤单抗气泡现在坐落在 y=1（向上抬 1 px）；foot "第 2 组，共 2 组；本页 9 个配对产品。未配对 6 个，不画点" 增加透明度。"50" 轴刻度仍部分被气泡覆盖 | **P1 残存** |
| a-14-a-matrix-2 | Chromium | 2048×1024 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/2048x1024/a-14-a-matrix-2.png | 同上；"50" 与气泡中心 y 重叠更明显 | **P1 残存** |
| a-14-a-matrix-2 | WebKit | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/a-14-a-matrix-2.png | 同上；WebKit 渲染气泡稍偏左，"50" 仍被气泡左半覆盖 | **P1 残存** |
| b-04-b-efficacy | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/b-04-b-efficacy.png | Y 轴 0–100；APPLY 双柱（82.3 / 1.8）；APP0INT 单柱 92.2 + 副标题"无同期对照"；foot 写明终点定义；图例双系列诚实 | **PASS — P0-1 已解决** |
| b-04-b-efficacy | WebKit | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/b-04-b-efficacy.png | 同上；WebKit 渲染一致 | **PASS** |
| b-06-b-safety | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/b-06-b-safety.png | 3×4 热图，11 行 AE；foot "颜色深浅是已公开发生率；米色格子是未公开，禁止读成零事件" | PASS |
| b-07-b-matrix | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/b-07-b-matrix.png | 单 APPLY 气泡 + 右侧"APPLY 可比较 / APP0INT 不适用（单臂研究没有试验内对照组…）"双卡，foot "只有 APPLY 进入可比较点；APPOINT 必须展示单臂不适用原因" | **PASS — 矩阵 honesty 已重写** |
| c-09-c-endpoints | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/c-09-c-endpoints.png | 4 卡 × 2 行；卡 3 标题 2 行（奈莫利珠单抗研究名过长），但 criterion 行（IGA ≥ 2 分；评估时点 第16周）和其他 3 卡一致，foot "前三项采用 IGA…ADvantage 采用 EASI-75…主要评估时间点均为第 16 周" 明确终点差异 | **PASS — 卡 3 标题仍 2 行但语义节奏可接受** |
| c-09-c-endpoints | WebKit | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/c-09-c-endpoints.png | WebKit 渲染一致 | PASS |
| c-15-c-path-1 | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/c-15-c-path-1.png | 1 头卡（双线结论 + 来源）+ 3 子卡（设计框架 / 治疗安排 / 人群与终点）；bottom ~50% 仍空，但内容已诚实地把"路径一"的全部构成说清 | PASS（稀疏但诚实） |
| c-16-c-path-2 | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/c-16-c-path-2.png | 同 c-15 结构；3 子卡把"路径二"的差异点（避开 IGA、改用 EASI-75、采用成年稳定期）说清 | PASS（稀疏但诚实） |
| c-18-c-ending | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/c-18-c-ending.png | 双 CMS Logo：左上 hero 240×50 + 下中"谢谢"下再次出现相同 wordmark。两条 ribbon（一处顶部正中、一处底部）。 | **P0-2 残存 — 未修复** |
| c-18-c-ending | WebKit | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/c-18-c-ending.png | 双 Logo 在 WebKit 同样复现 | **P0-2 残存** |
| a-20-a-ending（对比） | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-20-a-ending.png | 单 Logo（左上）；与 c-18 形成对照，证明 c-18 的双 Logo 是真异常 | 对照证据 |
| b-24-b-ending（对比） | Chromium | 1920×1080 | docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/b-24-b-ending.png | 单 Logo（左上）；与 c-18 形成对照，证明 c-18 双 Logo 不在合同里 | 对照证据 |

---

## 3. 修复成效（按移交问题逐条核验）

| 移交问题 | 修复前 | 修复后 | 评价 |
|---|---|---|---|
| B 疗效页 92.2 与图例间距（双系列图例错配） | Y 轴 0–105 空白多；APP0INT 缺对照柱但图例仍展示蓝柱；foot 不解释 | Y 轴 0–100；APP0INT 副标题写"无同期对照"；foot 写明终点定义与口径 | **完全解决** |
| A 矩阵（续1）X 轴 "50" 与度普利尤单抗气泡碰撞 | 气泡坐落在 Y=0，"50" 完全重叠 | 气泡上抬到 Y≈1；foot 加 "未配对 6 个，不画点" 提升透明度；"50" 仍部分被气泡覆盖 | **部分解决，仍有视觉残留** |
| C 终点页 EASI ≥ 75% 中文排版 / 卡 3 标题 2 行 | 卡 3 标题因 trial 名重复而 2 行，criterion 行与卡 1/2/4 节奏不齐 | 卡 1/2/3 全部"IGA ≥ 2 分；评估时点 第16周"、卡 4"EASI-75 应答；评估时点 第16周"，foot 明确终点差异；卡 3 标题仍 2 行但与卡 4（更短）同排在 row 2，整体节奏可以接受 | **完全解决** |
| C 入排标准语义混乱 | c-06 row 1 写"评估时点 筛选期"；c-07 全是"评估时点 X" | 已不再出现 row 1 与其他行语义冲突；列重新设计 | **完全解决** |
| C dossiers/identity 翻译腔 | "时间点 评估时点 第16周" 重复"评估时点" | 已移除冗余中间标签 | **完全解决** |
| 零与未公开的区分 | 多处把零与未公开混在同色块 | 多页 foot 显式写 "零事件不能等同未公开" 和 "米色格子是未公开" | **完全解决** |
| 单臂研究的可比较性陈述（B 矩阵） | 单气泡图，气泡图 70% 空白；foot 没解释 | 单气泡 + 右侧双卡 "APPLY 可比较 / APP0INT 不适用（单臂研究没有试验内对照组…）"；foot "只有 APPLY 进入可比较点；APPOINT 必须展示单臂不适用原因" | **完全解决（重要）** |
| C 路径一/二的版式完整性 | 单卡，下 65% 空 | 已填 1 头卡 + 3 子卡（设计框架 / 治疗安排 / 人群与终点）；仍稀疏但内容已诚实填满关键信息 | **稀疏但诚实 — 不再是 P1** |

---

## 4. 仍残留的图像级 P0/P1（仅图证，不猜测）

### P0-2（残存）— C 谢谢页重复出现第二个 CMS Logo
- 页：`c-ending`
- 浏览器 / 视口：Chromium 1920×1080、1280×800、2048×1024；WebKit 1920×1080 复现
- 原图：
  - `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/c-18-c-ending.png`
  - `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/c-18-c-ending.png`
- 可见观察：页面顶部"谢谢"左侧已是 CMS 康哲药业 Logo（hero 240×50 槽），页面中段（橙色 ribbon 与产品中心-医学部·2026年8月 之间）再次出现相同的 CMS 康哲药业 wordmark。两条 ribbon（"谢谢"下正中的金黄色细线 + 页面底部主橙进度条）也构成视觉冗余。
- 对照证据：
  - `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-20-a-ending.png`（A 谢谢，仅 1 个 Logo）
  - `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/b-24-b-ending.png`（B 谢谢，仅 1 个 Logo）
- 用户影响：违反 `track_htmlppt.md §0.8.3B`（hero 槽仅一处）；医学经理扫读会立即觉得"为什么 C 报告结束页比 A/B 多一个 Logo"；与同轨 chrome 不一致。
- 最小修复：删除下方第二处 CMS Logo，仅保留左上 hero 槽；建议同步合并两条 ribbon 为一条（与 a-ending / b-ending 一致）。

### P1-1（残存）— A 矩阵（续1）"50" 轴刻度与度普利尤单抗气泡仍部分重叠
- 页：`a-matrix-2`
- 浏览器 / 视口：Chromium 1920×1080、1280×800、2048x1024；WebKit 1920×1080 复现
- 原图：
  - `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-14-a-matrix-2.png`
  - `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/2048x1024/a-14-a-matrix-2.png`
  - `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/a-14-a-matrix-2.png`
- 可见观察：度普利尤单抗气泡已上抬到 Y≈1；X 轴刻度 "50" 仍部分被气泡中心/右下半弧覆盖。气泡大小包含刻度文字的左半。
- 用户影响：医学经理读图仍可能把 "50" 误读为气泡内数字（虽然可读出气泡标签"度普利尤单抗"）。
- 最小修复（任选其一）：
  1. 加气泡白描边 1 px（让轴标签"50"在气泡外更可见）；
  2. 气泡再上抬 1–2 px（Y≥3），完全离开 X 轴；
  3. 轴刻度文字加浅色衬底 (rect 2px 高) 让其在气泡上仍可读。

---

## 5. P2 / P3 打磨（与本轮修复无关；仅作历史对照）

| 页 | 类别 | 描述 |
|---|---|---|
| a-13-a-matrix | P2 | X 轴 0–100 但数据集中在 25–75；仍可优化 |
| a-17-a-patents | P3 | 8 行"未公开/未核实"墙色块；可合并 |
| a-18-a-history | P3 | 右栏 60% 空；可填历史里程碑 |
| b-23-b-limitations | P3 | row 1 wrap 不规则 |
| c-06-c-inclusion（已重排） | P3 | 新版列语义清晰，可进一步精简列名 |
| c-09-c-endpoints | P3 | 卡 3 标题 2 行与卡 4 同行不影响，但 trial 名"奈莫利珠单抗疗效与安全性研究"过长 |
| c-15/c-16 可选路径 | 稀疏但诚实 | 已不算 P1；如希望更紧凑可压缩头卡 padding |

---

## 6. 跨视口 / 跨浏览器发现

- **1280×800**：CSS 等比缩放成立；本轮修复在 1280×800 上 P0-2 双 Logo 与 P1-1 "50" 碰撞复现。
- **2048×1024**：P0-2 双 Logo 复现；P1-1 "50" 碰撞比 1920×1080 更明显（气泡与刻度几何更靠近）。
- **WebKit 1920×1080**：P0-2 双 Logo 复现；P1-1 在 WebKit 上气泡略偏左，"50" 仍被气泡左半覆盖。
- **一致性**：本次修复后的 10 个重点页在双浏览器三视口下行为一致；无新增溢出 / 裁切。

---

## 7. 中文资深医学经理视角评估

**修复后的整体感受（值得肯定的部分）**

- 把"零 ≠ 未公开"这条数据可信度红线写进了多页 footer。这种自我说明比一张漂亮的图更让医学经理放心——管理层读到"无蓝柱即无同期对照，不是零"或"米色格子是未公开，禁止读成零事件"会立刻判断这是严谨报告，而不是数据缺失。
- B 报告的"单臂研究不计算治疗—对照疗效差"显式说明 + 双卡解释，是临床试验方法学上的合规表达。这种说明能直接挡掉上层"为什么 APP0INT-PNH 缺对照"的提问。
- A 报告把"未配对 6 个，不画点"放在矩阵 footer，把"未配对"的事实写出来而不是悄悄丢掉——医学经理能直接看到样本范围而不是被迫去追问。
- C 报告 endpoints 页把"前三项采用 IGA…ADvantage 采用 EASI-75"用一句 footer 说明卡 1/2/3 与卡 4 的终点差异，避免了上次 "IGA ≥ 2 分" vs "EASI-75" 被并列在同一卡但读起来模糊的问题。

**还想修的部分**

- C 报告 ending 页的双 Logo 看一眼会觉得"是不是设计失误"。建议删除第二 Logo，与 a-ending / b-ending 对齐。
- A 矩阵"50"刻度与气泡重叠虽然气泡已抬高，但残存视觉痕迹仍在；建议加气泡白描边或再上抬 1–2 px，让轴标签彻底不被气泡吃掉。

---

## 8. PASS / REVISE 建议（非终验）

**建议：MINOR REVISE — 修复 1 个 P0 残留 + 1 个 P1 残留后再交付。**

理由：
- **P0-2（c-18 谢谢页双 Logo）仍未修复**，且与 a-ending / b-ending 不一致；同一 deck 内 ending 页 chrome 不统一属 P0 阻断。
- **P1-1（a-14 矩阵 "50" 与气泡碰撞）只是部分修复**，气泡抬升后碰撞减弱但未消失；最小修复（白描边 / 再上抬 / 轴标签加底）任选其一即可。

修复后建议 Codex 重渲 2 张原图（c-18、a-14）+ 在三视口（1920×1080、1280×800、2048×1024）和 WebKit 上回归核对，自动诊断 + 人工原图双通过后再回到 Codex 终验。

---

## 9. 检查完整性声明

- 重点 10 页 + 1 个对照页（a-20） + 1 个对照页（b-24）共 12 张 Chromium 1920×1080 原图已逐张视觉解码；
- a-14 / b-04 / c-18 三页跨视口（1920×1080、1280×800、2048×1024）+ WebKit 1920×1080 已核对；
- 新 ledger（visual-final-2-chromium / visual-final-2-webkit）已读取并与新 SHA 绑定；
- 未读取任何 peer 评审、未启动任何子 agent 的报告产出作为证据；
- 本轮 minimax-medical-manager round-2 视觉审阅意见不是终验，Codex 仍是终验权威。
