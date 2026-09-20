Round 4 is a targeted C-only recheck. I’ll verify the new hash first, then inspect C5, C8, C12, and C13 for the two repaired wrap issues and any new clipping.Hash, 19 pages, and newer renders match. Next I’ll extract layout text and inspect C5, C8, C12, and C13.Timepoint cells look closed; C5/C12 content may have a new mid-number wrap from the column-width change. I’ll confirm that on the page images before writing the report.# Conference Participant Output: ci-phase8-task82-final-visual-review - visual_single_object round 4

## Boundary Check

- **Role:** `visual_single_object`；同会话 round 4 定向复审。Codex 保留最终视觉/医学放行权。
- **Fallback:** `pi` / `cursor` / `cursor-grok-4.6`（effort high）。未改任何源文件、PDF、fixture、测试或合同；未写 `visual_single_object_round4.md`；未上网；未用旧审阅稿代替当前页图。
- **范围:** 只复核 round 3 两条非阻断项的修复，以及加宽是否引入裁切/重叠/断框/新拆词。只开 C5、C8、C12、C13。未重审 A/B，未重开 C 全部 19 页。
- **未宣称:** 机器 `summary.json` 的 `ok: true` / `defect_count: 0` 不是视觉通过。本角色不授予 Codex 终验。

## Current Artifact Verification

实测 C 哈希、页数、渲染数与任务包一致；PNG 晚于当前 PDF。A/B 哈希未改，本轮未作为审阅对象。

| 报告 | 约定 SHA-256 | 实测 | 页数 | 渲染 PNG | PDF mtime | 相关渲染 mtime |
|---|---|---|---|---|---|---|
| C `.artifacts/pdf-complete/report-c.pdf` | `7156ffa0…579db2` | **一致** | 19 | 19 | 04:12:49 | C5/C8 04:15:36；C12/C13 04:15:37 |

- `summary.json` 生成于 `2026-08-30T20:15:38Z`；C `coverage_ok=true`、`defect_count=0`。只证明结构闸门绿。
- 本轮目视：C5、C8、C12、C13 当前 144 dpi PNG；并用 `pdftotext -layout` 复核排除原文、时间点列、内容列折行。

## Targeted Adjudication

### 1. C8 `曲罗芦单抗` 不再词内拆开

**关闭。**

排除原文可见两行：

```text
既往接受过度普利尤单抗或曲罗芦单抗
治疗
```

`曲罗芦单抗` 整词在第一行末；换行发生在药名之后的「治疗」。同页 `度普利尤单抗`、`Lebrikizumab`、`EASI` 仍整词。无裁切、无叠字、无断框。

### 2. 时间点列：`第N周` 数字与「周」同行

**关闭。** 指定页时间点列不再出现 `第52` / `周` 或 `第16` / `周`。完整形式保持在同一行；短语之间换行仍存在。

| 页 | 时间点列原文（含换行） | 数字与「周」 |
|---|---|---|
| C5 | `第1周至第51周`；`第16周`；`诱导期第16周；维` / `持期第52周`；`基线至第52周` | 51 / 16 / 52 均与「周」同行 |
| C8 | `筛选期` / `知情同意时`；入排条件无周数折行 | 不适用 |
| C12 | `第16周；长期安全` / `性随访`；`第16周`；`第1周至第51周`；`诱导期第16周；维` / `持期第52周` | 16 / 51 / 52 均与「周」同行 |
| C13 | `基线至第52周`；`诱导期第16周；维` / `持期第52周`；`第16周`；`基线至第16周` | 16 / 52 均与「周」同行 |

C5 / C13 续表标题仍在：`续表 · 设计图谱完整表`、`续表 · 访视、疗程与随访完整表`。C12 时间线 A–H 无互压；A/D/G 仍 `…` 截尾。

### 3. 加宽是否引入裁切、重叠、断框或新拆词

**裁切 / 重叠 / 断框：未引入。** 四页表框连续，页脚完整，无字压框。

**新拆词：引入了。** 时间点列加宽后，相邻「内容」列把完整周数从数字中间断开——与 round 2 阻断同类，只是换列。

**C5 · 访视与随访 · 内容（Lebrikizumab / ADvocate2）**

```text
随机、双盲、安慰剂对照、平行分组；诱导期1
6周，维持期36周，总疗程52周
```

**C12 · 访视与随访 · 内容（同一行）** 同样是 `诱导期1` / `6周`。

**C12 · 访视与随访 · 内容（度普利尤单抗 / CHRONOS）**

```text
度普利尤单抗联合外用糖皮质激素治疗至第16
周，并进行长期安全性随访
```

扫读会把「诱导期16周」读成第1周，或把「至第16周」读成「至第16」后另起「周」。静态 PDF 无法靠悬停纠正。这不是 round 3 已接受的「完整 `第16周` 之后再折行」。

## Remaining Blockers

Round-3 点名的两条非阻断项（C8 `曲罗芦单抗`、时间点列数字与「周」拆开）**已关闭**。

当前 C 哈希上仍有一条**新的视觉阻断**，由加宽时间点列挤窄「内容」列造成：

1. **C5 / C12 — 「内容」列把周数从数字中间折断**
   - C5、C12：`诱导期1` / `6周`（实为诱导期16周）
   - C12：`治疗至第16` / `周`

不写「no new visual blocker was introduced on the current C hash」。也不写「本轮独立视觉复审接受当前三份 PDF」。

## Non-blocking Improvements

- C5 / C12 / C13 时间点 `诱导期第16周；维` / `持期第52周`：数字完整，但「维持期」被拆音节。允许短语间换行，优先保持「维持期」整词。
- C12 时间点 `第16周；长期安全` / `性随访`：「安全性」被拆开。
- C8 入选原文 `筛选访视前特应性皮炎病程至少3` / `年`：数字与「年」分行；临床误读风险低于周数中位折行。
- C12 终点列仍 `主要终点（IGA` / `）`；时间线 A/D/G 仍 `…`。
- C8 / C13 试验名 `奈莫利珠单抗` / `疗效与安全性` / `研究` 仍折行（round 3 已降级，本轮未恶化为数字折断）。

## Recommended Next Step

请 Codex 只修 C 内容列的周数保护后重渲 C，旧 C PNG 作废；A/B 不必因本轮重开。

1. 禁止把 `16周` / `第16周` / `第51周` / `第52周` 从数字或「周」处断开，**内容列与时间点列同样适用**。
2. 可在完整周语之后换行（例如 `诱导期第16周；` 再 `维持期第52周`），不要写成 `诱导期1` / `6周`。
3. 顺手（非本条放行条件）：`维持期`、`安全性` 整词；C8 `3年` 同行。

本角色就 round-3 点名项可以放行；就准则 3，当前 C `7156ffa0…579db2` **不能**视为无新阻断。
