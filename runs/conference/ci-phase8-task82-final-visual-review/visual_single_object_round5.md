Round 5 is a targeted C-only recheck of the content-column week wraps. I’ll verify the new hash first, then inspect C5, C8, C12, and C13.Hash and 19 newer renders match. Next I’ll extract layout text and inspect C5, C8, C12, and C13.The round-4 mid-number wraps are gone on these pages. I’ll quote the current cells and check that the wrapper did not add clipping or a new clinical misread.

# Conference Participant Output: ci-phase8-task82-final-visual-review - visual_single_object round 5

## Boundary Check

- **Role:** `visual_single_object`；同会话 round 5 定向复审。Codex 保留最终视觉/医学放行权。
- **Fallback:** `pi` / `cursor` / `cursor-grok-4.6`（effort high）。未改任何源文件、PDF、fixture、测试或合同；未写 `visual_single_object_round5.md`；未上网；未用旧审阅稿代替当前页图。
- **范围:** 只复核 round 4 内容列周数中位折行，以及共享表包装器是否引入裁切/重叠/断框/多余页/新的实质可读缺陷。只开 C5、C8、C12、C13。未重审 A/B，未重开 C 全部 19 页。
- **未宣称:** 机器 `summary.json` 的 `ok: true` / `defect_count: 0` 不是视觉通过。本角色不授予 Codex 终验。

## Current Artifact Verification

实测 C 哈希、页数、渲染数与任务包一致；PNG 晚于当前 PDF。A/B 哈希未改，本轮未作为审阅对象。仍为 19 页，无意外增页。

| 报告 | 约定 SHA-256 | 实测 | 页数 | 渲染 PNG | PDF mtime | 相关渲染 mtime |
|---|---|---|---|---|---|---|
| C `.artifacts/pdf-complete/report-c.pdf` | `667715ae…3938343` | **一致** | 19 | 19 | 04:21:15 | C5 04:22:03；C8/C12/C13 04:22:04 |

- `summary.json` 生成于 `2026-08-30T20:22:05Z`；C `coverage_ok=true`、`defect_count=0`。只证明结构闸门绿。
- 本轮目视：C5、C8、C12、C13 当前 144 dpi PNG；并用 `pdftotext -layout` 复核内容列与时间点列。全文 C5–C13 无 `诱导期1` / `6周`、无行末 `治疗至第16`。

## Targeted Adjudication

### 1. C5/C12 不再渲染 `诱导期1` / `6周` 或 `治疗至第16` / `周`

**关闭。**

**C5 · Lebrikizumab / ADvocate2 / 访视与随访 · 内容**

```text
随机、双盲、安慰剂对照、平行分组；
诱导期16周，维持期36周，总疗程52周
```

**C12 · 同行内容** 同样在分号后整段换行，`诱导期16周` 完整。

**C12 · 度普利尤单抗 / CHRONOS / 访视与随访 · 内容**

```text
度普利尤单抗联合外用糖皮质激素
治疗至第16周，并进行长期安全性随访
```

`治疗至第16周` 整词在第二行，不再把「周」单独打下。

同页时间点列现为短语边界换行，不再拆数字：

```text
诱导期第16周；
维持期第52周
```

### 2. 指定页所有可见 `第N周` / `N周` 数字与单位同行

**关闭。** 内容列与时间点列均未再把数字与「周」拆开。

| 页 | 内容列完整周语 | 时间点列完整周语 |
|---|---|---|
| C5 | `每2周`、`第51周`、`第16周`、`诱导期16周`、`36周`、`52周`、`基线至第16周`、`维持期至第52周` | `第1周至第51周`、`第16周`、`诱导期第16周；` / `维持期第52周`、`基线至第52周` |
| C8 | 无疗程周数；`1周` 出现在 `基线访视前1周内…`、`基线前1周` | 不适用 |
| C12 | `治疗至第16周`、`每2周`、`第51周`、`诱导期16周`、`36周`、`52周`、`基线至第16周` | `第16周`、`第1周至第51周`、`诱导期第16周；` / `维持期第52周`；时间线 A–H 的周语完整 |
| C13 | `每2周`、`第52周`、`第16周`、`至第16周` | `基线至第52周`、`诱导期第16周；` / `维持期第52周`、`基线至第16周`、`第16周` |

C5 / C13 续表标题仍在。C8 `曲罗芦单抗` 仍整词：`既往接受过度普利尤单抗或曲罗芦单抗` / `治疗`。入选原文改为 `至少` / `3年`，数字与「年」同行，优于 round 4 的 `至少3` / `年`。

### 3. 共享包装器是否引入裁切、重叠、断框、多余页或新的实质可读缺陷

**未引入阻断级缺陷。**

- 四页表框连续，页脚完整，无字压框、无叠字。
- 页数仍为 19，无意外增页。
- C13 访视内容在完整 `每2周1次者` 之后换行，第二行以 `，维持期…` 起句：标点前置，可读，不造成时点误读。
- C12 时间点仍有 `第16周；长期安全` / `性随访`（「安全性」拆开）；时间线 A/D/G 仍 `…`；终点列仍 `主要终点（IGA` / `）`。均为既有非阻断项，不是新的周数中位折行。

## Remaining Blockers

**Round-4 阻断已关闭。当前 C 哈希 `667715ae…3938343` 上，本定向闸门没有新的视觉阻断。**

不写「本轮独立视觉复审接受当前三份 PDF」为 Codex 终验；A/B 本轮未重开。就准则 1–3 而言：内容列 `诱导期1`/`6周` 与 `治疗至第16`/`周` 已消失，周语数字与单位在内容列和时间点列均同行，加宽/包装未引入裁切、重叠、断框或新的临床误读。

## Non-blocking Improvements

- C12 时间点 `第16周；长期安全` / `性随访`：「安全性」仍拆音节。
- C12 时间线 A/D/G 仍 `…` 截尾（`第16周；长期安…`、`诱导期第16周；…`）。
- C12 终点列仍 `主要终点（IGA` / `）`、`主要终点（EASI` / `）`，右括号单独换行。
- C13 内容第二行以顿号/逗号起句（`，维持期继续同剂量给药`）：标点前置，优先在「者」后留在上行或把逗号带到第一行末。
- C8 试验名 `奈莫利珠单抗` / `疗效与安全性` / `研究` 仍折行（既有降级项）。

## Recommended Next Step

Codex 可在当前 C 哈希上判断是否结束本定向修补链。A/B 不必因 round 5 重开。若继续修非阻断项，优先 C12「安全性」整词与时间线截尾；修后必须重渲 C 并作废旧 PNG。
