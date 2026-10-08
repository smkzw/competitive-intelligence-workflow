Corrections acknowledged (accounting fix, INN rule, c31af306 raw-bytes rule, attribution withdrawn). Proceeding with the bounded v3 repair verification — reading the changed-manifest and all four changed-pairs files completely, then verifying against sources.

changed-pairs-1 verified (8 keys: enrollment-phrasing, TB carve-outs, malignancy restoration, superpotent ceiling, 0–10 range, loading-dose restoration — all source-supported). Reading changed-pairs-2 completely.

changed-pairs-2 verified (8 keys). Noting a potential residual: `5615251a` (unchanged) previously read "分析窗口被延长至第16周" — I will verify its v3 state as a necessary unchanged-control read. Reading changed-pairs-3 and -4 completely now.

changed-pairs-3 verified (8 keys — including the c31af306 truncation disclosure and the "无应答" repair). Reading changed-pairs-4 completely (final changed file).

All 31 changed keys read completely across the four changed-pairs files — all source-supported so far. Now the necessary unchanged-control checks: locating `5615251a` (window wording, unchanged set) and reading the v3 receipt head.

v3 receipt metadata verified (parent = v2 receipt SHA, 31/95 split, flags false/NOT_RUN, source SHA preserved for 3e0db333). Now checking `5615251a`'s v3 window wording plus residue greps restricted to the v3 review-pairs files.

`5615251a` confirmed still carrying the exact rejected construction "分析窗口被延长至第16周" — a candidate remaining key. Disambiguating the residue hits and reading the v3 review-manifest.

Single residual `延长至` confirmed (only `5615251a`). Now reading the v3 review-manifest, locating the control clauses, and checking the frozen TERMS authority.

v3 review-manifest cross-checked: file SHAs of `review-pairs-2` and `review-pairs-4` are byte-identical to v2 (both contain **zero** of the 31 changed keys), while files 1/3/5/6 have new SHAs — the changed-key distribution (3+0+6+0+8+14=31) matches exactly. Now reading the control clauses and running receipt-integrity greps.

Controls verified so far (dose/load/interval rows correct; INN replacement confirmed; contraception-phrase variance noted). Reading the remaining necessary controls (immunogenicity/ADA, arm label) and the frozen TERMS authority.

TERMS literal verified (Nemolizumab Latin INN, loading/total, rescue=补救治疗, exceptions/negation preservation, adequate-treatment-not-cure). Final integrity greps: v3 receipt counts, preserved source SHAs, truncation disclosure, and the last control location.

All verification steps are complete. Final report follows (returned for the runner; no files written).

# Conference Output: ci-1007-c-translation-v2-fidelity - evidence_single_object

## Output

### 0. Carry-over corrections and evidence-layer statement

- **Accounting correction accepted:** my earlier "147 key slots / 21 reused assignments" wording was wrong. The manifest set is exactly **126 unique keys** (6 files × 21); `reused`/`retranslated` is a per-clause `Treatment` attribute (63/63). Re-verified in both v2 and v3 manifests; the 31 changed keys map onto the file-key lists without duplication (distribution 3+0+6+0+8+14 = 31, see §2).
- **INN rule applied:** Nemolizumab must retain the Latin INN; untranslated `dupilumab` is not a defect; no Hanzi/approval dictionary is imposed. My earlier acceptance of 奈莫利珠单抗 rows as clean is withdrawn. The frozen TERMS literal (`.artifacts/1007-c-translations-v2/repair.py` lines 20–35) was read read-only and independently corroborates: "Preserve Nemolizumab as Latin INN… do not invent a Chinese drug name"; "loading dose = 负荷剂量; no loading dose = 无负荷剂量; total = 总量"; "rescue therapy = 补救治疗"; "adequately treated = 已得到妥善治疗, not necessarily cured"; "Retain parent/child AND/OR, negation, exceptions, arm and weight branches, loading/total quantities, scale ranges and event intervals."
- **c31af306 boundary accepted:** raw CT.gov capture itself ends `non-responde` (NCT04501666 `secondaryOutcomes[4].description`); no local cap hypothesis. The v3 text preserves the raw bytes, removes the unsupported completion, and discloses the truncation; the missing tail remains an unresolved upstream source limitation — not approved, not completed.
- **Evidence layer (shell denied in this session):** I cannot recompute SHA-256. All hash statements below are **declared-value consistency checks**: owner-declared v3 values and manifest values compared against each other and against v2 values I recorded earlier. Content verification (reading) is my primary layer. Owner-recomputed hashes are the byte-integrity layer.

### 1. Coverage (bounded repair verification)

**Changed set — 31/31 keys read completely (no caps):** all four `changed-pairs-*.md` files were read in full (493 + 245 + 273 + 165 lines); each key's `source_text`, full v2 (`before`), and full v3 (`after`) were read and compared.

Per-key dispositions (all ACCEPT — source-supported, minimal, no new defects introduced):

- **changed-pairs-1 (8/8):** `3e0db333` (enrollment-phrasing + 3-month anchor + 0–10 range + TB carve-out + adverse wording + malignancy wording) · `d3877a66` (enrollment + range) · `ec972b01` (TB carve-out + malignancy) · `056321b9` (untoward) · `974030ad` (superpotent + neuropathy + adverse + TB + AND-window + malignancy + enrollment) · `d9939694` (superpotent + range + enrollment) · `e4439284` (**active malignancy restored** + TB + malignancy) · `fad1412a` (**负荷剂量 restored**).
- **changed-pairs-2 (8/8):** `2003b08f` (**每周→每2周1次**, contradiction removed) · `1dd06208` (untoward) · `76b84054` (例如但不限于 ×2 + as-per-standard-of-care + contraception phrasing) · `19536677` (例如但不限于 ×2) · `c28dfa5a` (Nemolizumab) · `0a847343` (**<90 kg loading restored** + Nemolizumab; ≥90 kg "无负荷剂量" correctly retained) · `877d2048` (Nemolizumab) · `93c5cbdf` (统计分析计划 + 补救治疗 ×2 + 最差可能值 + "当天及之后").
- **changed-pairs-3 (8/8):** `f2652105` (untoward) · `57be442f` (统计分析计划 + 补救治疗 + 之时及之后 + 10-anchor causal clause "因结节性痒疹症状而完全无法入睡") · `c31af306` (**truncation disclosure; unsupported completion removed**) · `6ace0211` (例如但不限于 ×2 + SoC + contraception) · `eee88f06` (例如但不限于 ×2) · `590552e7` (**loading restored** + Nemolizumab) · `b009e9ee` (Nemolizumab) · `144fc0e9` (两个时间点 restored + 无应答).
- **changed-pairs-4 (7/7):** `886f13e3` (补救治疗 + 之时及之后) · `f2cede23` (无应答) · `41632611` (**"对第16周的分析窗口进行了延长处理"** + 无应答) · `ad7d1170` (无应答 ×2) · `4dafe82f` (截至治疗开始时刻（含该时刻） + 无应答 + 10-anchor causal clause) · `acf04fd9` (无应答, parenthetical removed) · `ba190782` (untoward).

**Necessary unchanged controls read in v3 review-pairs:** `5615251a` (window; **residual defect found — §3**), `87228b88`, `9e9174af`, `2a17bd77`, `50b19a29`, `e68c614d`, `972c6db6` (dose/arm controls), `86a8e145`, `2c03caeb` (contraception phrasing variance), `3228c81d`, `280d2083`, `8d4b8179` (immunogenicity).

**Whole-set verification (not per-clause reads of the remaining 83):** defect-class residue greps over all v3 `review-pairs-*.md` — zero hits for `急救治疗 | 研究实施方案 | 无效数据 | 非预期 | 奈莫利珠单抗 | 肺结核 | 完全治愈 | 周围神经病变 | 经证实有效 | 视为无效 | 延长到 | 抢救`; `无负荷剂量` occurs only in the two correct ≥90 kg branches; `延长至` occurs exactly once (see §3). Additionally, the v3 `review-manifest.json` file SHAs for `review-pairs-2` and `review-pairs-4` are byte-identical to v2 — and those two files contain **zero** of the 31 changed keys — while files 1/3/5/6 carry new SHAs; this is consistent with the declared 31-changed/95-unchanged partition. v3 receipt checks: 126 clauses, 174 `row_id` entries, 126 `source_text_sha256`, all 126 statuses `candidate_not_medically_accepted` (126/126), `parent_receipt_sha256` = v2 receipt `d33776f5…`, `input_sha256` unchanged `184b788c…`, sampled v2 source SHA values (`b8c71698…`, `b33abcbf…`, `49e5a345…`, `deb5ef1d…`, `24b01e02…`) all preserved once each, `repair_method` = "bounded source-literal owner corrections; no retranslation or source modifications", `duration_seconds` unchanged from v2 (no MT rerun signal).

**Unreviewed:** 0 of 31 changed keys. Of the 95 unchanged clauses, 12 were read at clause level and the rest were covered by string-level greps + declared-hash partition, not by full individual re-reads; unchanged clauses were fully reviewed in the original v2 pass and are declared untouched.

### 2. Category dispositions

- **Dose / weight / interval — ACCEPT.** `fad1412a` now "（负荷剂量）" (source "(loading dose)"); `0a847343`/`590552e7` now "<90 kg …（60毫克负荷剂量）" and correctly keep "（总量为60毫克，即无负荷剂量）" for ≥90 kg (source "(60 mg total) at baseline (no loading dose)"); counts preserved (1×30 mg Q4W vs 2×30 mg Q4W, 16-week period); `2003b08f` now "每2周1次接受300毫克dupilumab治疗" (source "300 mg q2w for 24 weeks"), contradictory "（即每2周1次）" removed, Latin `dupilumab` retained per rule. Controls intact: `87228b88` (负荷剂量600 mg → 300 mg q2w ×24w), `9e9174af` ("作为负荷剂量"), `2a17bd77`, `50b19a29` (weight branches, no loading claims).
- **Eligibility exceptions / negations — ACCEPT.** TB carve-out "（除非已有记录证明已接受充分治疗）" added in `3e0db333`, `ec972b01`, `974030ad`, `e4439284` (source "unless documented adequately treated"; no cure implication). Active malignancy restored in `e4439284` ("患有活动性恶性肿瘤，或在基线访视前5年内有恶性肿瘤病史"); "completely treated" now "已完全治疗"/"已完全治疗且已消退" in all four malignancy clauses (cure wording removed). "例如但不限于" restored (8 list intros, 4 keys). "尚未按标准治疗得到妥善治疗" restored in `76b84054`/`6ace0211`. Enrollment-vs-diagnosis fixed in `3e0db333`/`d3877a66`/`974030ad`/`d9939694` ("受试者须具有符合以下所有条件的结节性痒疹临床诊断" ← "With a clinical diagnosis of PN defined by all of the following"). `974030ad` infection window now "以及" for source "and". "would adversely affect" → "会对…产生不利影响" in `3e0db333`/`974030ad`.
- **Statistical missingness — ACCEPT.** "considered as non-responders" now "无应答"/"视为无应答者" in `144fc0e9`, `f2cede23`, `41632611`, `ad7d1170`, `4dafe82f`, `886f13e3`; `acf04fd9` normalized to plain "无应答"; zero residual "无效数据/视为无效". "at/after receipt" now includes the receipt time ("之时及之后"/"之时起"/"当天及之后"). Composite-variable mechanics (worst possible value) retained.
- **Dates / windows — ACCEPT, ONE REMAINING KEY (§3).** `41632611` fixed to "对第16周的分析窗口进行了延长处理" (source "applied to week 16"); `144fc0e9` restored "两个时间点"; `4dafe82f` corrected to "截至治疗开始时刻（含该时刻）的7天内" (source "up to the treatment start (including until treatment start time)"). All other window clauses contain no rejected "延长至" construction — **except `5615251a`**.
- **Immunogenicity — ACCEPT (unchanged).** `3228c81d`, `280d2083`, `8d4b8179`: treatment-emergent vs treatment-boosted definitions, ≥4-fold titer rise, titer bands (<1,000 / 1,000 ≤ titer ≤ 10,000 / >10,000), and TE window (first IMP → last IMP + 14 weeks) all preserved; no defect-class residues. (Cosmetic order swap in `3228c81d` remains; non-blocking.)
- **Source limitations — correctly handled.** `c31af306` disclosure: "（来源末句在“non-responde”处截断；该断句未补写，完整内容待核。）" — raw truncation preserved, no invented suffix; unresolved upstream tail stays disclosed, explicitly not a translation approval. All 126 source quotes and 174 row locators retained per receipt counts and sampled SHAs.

### 3. Remaining minimal correction (exact key)

**`5615251a12a877d6966966bec181048d050feb142b830940796de4bff5ea9b3b`** — row `c-nct04501666-sec2-description` (v3 `review-pairs-6.md` line 29), currently:

> "正如统计分析计划中所描述的那样，**分析窗口被延长至第16周**。"

Source: "Analysis window extension was applied to **week 16**, as described in the SAP." This is the exact construction the owner ruled out ("applied TO week16 is not extended UNTIL week16") and which v3 corrected in its sibling `41632611` ("对第16周的分析窗口进行了延长处理") but missed here. The key was not among the 31 changed clauses; it is the only `延长至` instance remaining in the v3 set (whole-set grep, 1 hit). **Minimal fix:** replace with "对第16周的分析窗口进行了延长处理。" (mirror `41632611`; one line, no other text changes).

**Optional, non-blocking micro notes (not required for acceptance):** `86a8e145`/`2c03caeb` keep "有效且经批准" while the corrected siblings use "适当且经批准" for the same source phrase ("adequate and approved") — harmonization optional; the TB carve-out uses "已接受充分治疗" vs the TERMS surface "已得到妥善治疗" — semantically aligned, harmonization optional; `3228c81d` antibody-list order swap and the IGA anchor term variants (`6cbaab68`/`58523892`/`538260f6`) are unchanged cosmetic variances.

### 4. Disposition and boundaries

- **31/31 corrected clauses: ACCEPT_BOUNDED** (all literal, minimal, source-supported; no overcorrection or new defect found; each maps 1:1 to an original D1–D13 root cause or to the owner's five INN clauses, with `acf04fd9` and `c31af306` as the two additional bounded items — total 26+3+2 = 31, reconciling exactly).
- **Artifact-level: REVISE with one exact remaining key** (`5615251a`), per the owner's own window principle. After the one-line fix, no other required correction remains in the reviewed scope.
- **Boundaries retained:** source-to-Chinese fidelity only; no assertion of upstream label intent, drug approval, new formal Chinese name, scientific adoption/current state, or clinical equivalence; `scientific_acceptance=false`, `current_switched=false`, `browser=NOT_RUN` stand; the `non-responde` missing tail remains a disclosed unresolved source limitation; frozen `repair.py` and sealed evidence were not modified (read-only session; no writes, Git, network, browser, or recursive dispatch).
- **Bounded question (optional):** should the `5615251a` one-liner be applied in the owner's same repair mechanism (v3 receipt extension) with a single-clause re-check, rather than opening any new review pass? Provisional path: yes — apply `对第16周的分析窗口进行了延长处理` and re-verify only that clause against its source; nothing else needs re-review.
