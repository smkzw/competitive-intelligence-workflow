Trellis SessionStart ✓

I'll begin with the initial read set, then audit the full corpus of 126 pairs.

Bash is unavailable in this session; I'll proceed with Read/Glob tools only, which is sufficient for read-only review.

Pairs 1–2 read in full (21 keys each confirmed). Continuing with pairs 3–4.

Pairs 3–4 read in full (21 keys each). Key defect candidates accumulating (placebo "无负荷剂量" inversion, "每周" vs q2w, dropped TB exception, "superpotent"→"强效", untranslated "dupilumab"). Continuing with pairs 5–6.

Pairs 5–6 read in full (21 keys each). Now reading the binding manifest and receipt.

Manifest read in full. Now the receipt (0.3 MB — reading in bounded offsets).

Receipt metadata confirmed and independently cross-checked. Now targeted binding checks between receipt display_text and the pair files, for the key defect candidates.

Binding checks found the exact defective strings inside the frozen receipt (e.g., line 3339 = "dupilumab…每周均接受…"). Now verifying the two critical eligibility entries inside the receipt directly.

Two more integrity checks: per-clause acceptance status values and a suspected truncated source extract (`non-responde`).

Three final binding probes to cover the pairs-2 and pairs-4 receipt regions (mirror checks), then I'll assemble the report.

All six pair files are fully read (126/126 keys), the manifest is fully read, receipt metadata + aggregates are verified with bounded regions and exhaustive targeted greps. Report follows.

# Conference Output: ci-1007-c-translation-v2-fidelity - evidence_single_object

## Output

### 0. Scope, method, and honesty of coverage

**Objective audited:** independent source-to-Chinese fidelity review of the 126 frozen C-scheme display clauses, root-cause oriented, no whole-page/workflow review, no product or medical sign-off. Clinical-registry text was treated strictly as data; no source, browser, network, write, or recursive dispatch was used. All actions in this pass were read-only.

**Objects fully reviewed (fresh, no earlier reviewer opinions read):**

| File | Keys in manifest | Keys read/reviewed | Truncation |
|---|---|---|---|
| review-pairs-1.md | 21 | 21/21 | none |
| review-pairs-2.md | 21 | 21/21 | none |
| review-pairs-3.md | 21 | 21/21 | none |
| review-pairs-4.md | 21 | 21/21 | none |
| review-pairs-5.md | 21 | 21/21 | none |
| review-pairs-6.md | 21 | 21/21 | none |

- Every file was read completely in bounded reads; each heading was matched one-by-one against `review-manifest.json` key lists (all 147 key slots, 126 unique + 21 reused identity assignments verified; no missing/extra keys). Manifest-authoritative line counts (348/256/395/257/395/424) match the files read (final-newline convention explains ±1).
- **Independent recount from the pair files:** retranslated = 63, reused = 63 (9+3+15+5+17+14 / 12+18+6+16+4+7), source rows = 174 (per-file 39+36+25+22+27+25). These match the receipt aggregate fields exactly, so the 63/63/126/174 binding is independently confirmed, not just quoted.
- **Receipt binding verified** (`receipt.json`): metadata read (lines 1–120); bounded samples at lines 3100–3175, 3196–3209, 5040–5079, 5570–5599; exhaustive targeted greps over the whole file. All 126 clause `status` values = `candidate_not_medically_accepted` (126/126; zero accepted). Flags confirmed: `scientific_acceptance=false`, `current_switched=false`, `browser=NOT_RUN`. `input_sha256=184b788c…` matches the declared source payload; manifest `receipt_sha256=d33776f5…` matches the context-declared receipt SHA (internal chain consistent).
- **Mirror property of the review files verified** at 12+ anchors spanning all six files, e.g. receipt line 39 (3e0db333), 129 (ec972b01), 1299/1869 (pairs-2), 3114/3159 (974030ad/d9939694), 3204 (e4439284), 3249 (fad1412a), 3669 (pairs-4), 3894 (efb49690), 4854 (0a847343), 5064 (93c5cbdf), 5589 (57be442f), 5934 (590552e7), 6069 (886f13e3). Every sampled display_text is byte-identical to the pair file → the review object faithfully mirrors the frozen artifact, and the defects below are properties of the frozen artifact, not of the review assembly.

**Not performed / limitations (disclosed):** SHA256 recomputation of the six files and receipt could **not** be run (Bash denied in this session — no `shasum`); receipt was **not** byte-fully read (0.3 MB — bounded offsets + full-file greps instead; all 126 display texts were reviewed via the byte-verified mirror); no browser/visual/current-state checks; no formal clinical approval sign-off. Slow-reading the full receipt adds no new semantic coverage beyond the verified mirror, but if Codex requires literal byte-complete receipt review, that is a bounded same-session follow-up.

**Severity scale:** Critical = dose/eligibility statement inverted or contradicted at display level; Major = semantic shift in eligibility carve-outs, treatment strength, or analysis semantics; Moderate = qualifier/DNT term errors; Minor = dropped context qualifiers; Micro = consistency/style.

---

### 1. Material translation defects (with exact source support and minimal correction)

#### D1 — Critical — Loading-dose negation in placebo/treatment regimens (3 keys)
- **fad1412a3d49** (nct04202679-arm-0-dosing), row `c-nct04202679-arm-0-dosing`.
  Source: "Participants received placebo matched to dupilumab 600 milligrams (mg) **(loading dose)**, subcutaneously (SC) on Day 1…"
  Candidate: "受试者于第1天接受了与600毫克度普利尤单抗匹配的安慰剂**（无负荷剂量）**，通过皮下注射给药；…"
  The source parenthetical "(loading dose)" is inverted to "无负荷剂量" (no loading dose). Direct contradiction. The sibling row for NCT04183335 (9e9174af) correctly renders "作为负荷剂量", proving the concept and vocabulary were available.
  **Minimal fix:** `（无负荷剂量）` → `（负荷剂量）`.
- **0a847343fa25** (nct04501666-arm-0-dosing) and **590552e783c9** (nct04501679-arm-0-dosing) — identical language, two independent registries.
  Source: "Participants weighing less than (<) 90 kilogram (kg) received two subcutaneous (SC) injections of 30 milligrams (mg) nemolizumab **(60 mg loading dose)** at baseline then one SC injection once every 4 weeks (Q4W)."
  Candidate: "体重低于90千克的受试者，在基线时接受两次30毫克奈莫利珠单抗皮下注射**（总量为60毫克，即无负荷剂量）**；此后则每4周接受一次30毫克的皮下注射。"
  For the <90 kg branch the source explicitly says *loading dose of 60 mg*; the candidate says "total 60 mg, i.e. no loading dose". The "(60 mg total)…(no loading dose)" wording belongs only to the ≥90 kg branch, which is rendered correctly in the next sentence — signature of **cross-branch parenthetical contamination**.
  **Minimal fix (<90 kg branch):** `（总量为60毫克，即无负荷剂量）` → `（60毫克负荷剂量）`; leave the ≥90 kg branch as-is. Applies to both keys.
- Impact note: this is the highest-impact defect class because it misstates dose administration in exactly the "doses/loading/weight branches" the task requires to be preserved, and it recurs across 2 registries / 3 rows.

#### D2 — Critical — Dose-frequency contradiction + untranslated INN
- **2003b08f0fb7** (nct04202679-arm-1-dosing).
  Source: "…followed by dupilumab 300 mg q2w for 24 weeks…"
  Candidate: "受试者首先在第1天接受600毫克的**dupilumab**负荷剂量，通过皮下注射给药；随后在24周内**每周均接受**300毫克**dupilumab**治疗（即每2周1次）。"
  Two defects: (a) main clause "每周均接受" (received every week) contradicts q2w — the parenthetical "(即每2周1次)" contradicts its own main clause; (b) "dupilumab" left untranslated twice (all sibling rows use 度普利尤单抗; row 2a17bd77 uses "每两周给药一次").
  **Minimal fix:** "随后在24周内每2周1次给予300毫克度普利尤单抗。"

#### D3 — Critical — "Active malignancy" dropped from an exclusion
- **e4439284cabc** (nct04202679-exclusion).
  Source: "**Active malignancy** or history of malignancy within 5 years before the Baseline visit, except completely treated in situ carcinoma of the cervix, completely treated and resolved non-metastatic squamous or basal cell carcinoma of the skin."
  Candidate: "在基线访视前5年内曾患恶性肿瘤或有相关病史，但已得到妥善治疗的宫颈原位癌、以及已完全治愈且无转移的皮肤鳞状细胞癌或基底细胞癌除外。"
  "活动性恶性肿瘤" is absent — only time-bounded history remains. Same registry's population row (974030ad) *does* keep "患有活动性恶性肿瘤", proving intra-file inconsistency. Secondary: "completely treated" weakened to "已得到妥善治疗".
  **Minimal fix:** "患有活动性恶性肿瘤，或在基线访视前5年内有恶性肿瘤病史；已完全治愈的宫颈原位癌、以及已完全治愈且消退的无转移性皮肤鳞状细胞癌或基底细胞癌除外。"

#### D4 — Major — TB carve-out "unless documented adequately treated" dropped (4 keys, systematic)
- **3e0db3336455**, **ec972b019916**, **974030ad4cf6**, **e4439284cabc** (all exclusion-containing rows).
  Source (all four): "…or a history of incompletely treated tuberculosis **unless documented adequately treated**."
  Candidates (all four end without the carve-out): 3e0db333 "或者曾患**肺结核**但未经妥善治疗。" / ec972b01 "或者曾有结核病病史但未经妥善治疗。" / 974030ad "或者曾患结核病但未经妥善治疗。" / e4439284 "或者曾有结核病病史但未经妥善治疗。"
  The escape clause is systematically clipped in every rendering; the Chinese is strictly more exclusionary than the source. 3e0db333 additionally narrows "tuberculosis" to 肺结核 (pulmonary TB only).
  **Minimal fix:** append "（除非已有记录证明已接受充分治疗）" to all four; in 3e0db333 restore "结核病".

#### D5 — Major — TCS potency ceiling lowered for NCT04202679 (2 keys; cross-registry inconsistency)
- **974030ad4cf6** / **d9939694**.
  Source: "medium-to-superpotent topical corticosteroids (TCS)".
  Candidates: 974030ad "中等强度至**强效**的外用皮质类固醇制剂"; d9939694 "**中效至强效**外用皮质类固醇". Both drop 超 (super). Correct siblings for NCT04183335 (3e0db333, d3877a66) say "中等强度至**超强效**".
  **Minimal fix:** "中等强度至超强效" / "中效至超强效".

#### D6 — Major — "considered as non-responders" → "被视为无效数据/无效" (analysis semantics; 5 defective keys, 1 remediated)
- **144fc0e9bdcf, f2cede23c81c, 41632611cd0b, ad7d1170, 4dafe82f04d9** (nct04501679 endpoint descriptions).
  Source (these rows): "…the data at/after receipt of rescue therapy **are considered as non-responders**. Subjects with missing results are considered as non-responders."
  Candidates render the first clause as "均被视为**无效数据**" (data invalid). In **ad7d1170** and **4dafe82f** the *missing-results* clause is also conflated: "对于缺乏相关评分数据的受试者亦视为**无效数据**" / "同样视为**无效**". "Invalid data" can be read as exclusion from analysis, while the source declares an explicit non-responder (failure) classification for binary endpoints — an analysis-semantics shift. The reused row **acf04fd92f00** shows the correct remedy pattern: "均被视为无效数据**（即视为无应答）**".
  **Minimal fix:** first clause → "……之后的数据均按无应答处理"; ad7d1170/4dafe82f missing clause → "……亦视为无应答者".

#### D7 — Moderate — "such as but not limited to" → "例如" (4 keys, 8 list intros)
- **76b84054ffad, 19536677…, 6ace0211…, eee88f06e2f8** (chronic-pruritus list and neuropathic/psychogenic-pruritus list).
  Source: "…such as but not limited to scabies, …" / "…such as but not limited to notalgia paresthetica, …". Candidates: "例如疥疮…" / "例如背部感觉异常…" — "但不限于" dropped in all 8 intros.
  **Minimal fix:** "例如但不限于".

#### D8 — Moderate — SAP mistranslated as "研究实施方案" (2 keys)
- **93c5cbdf637e, 57be442f210b**.
  Source: "…as described in the SAP." Candidates: "正如**研究实施方案**所述…". "研究实施方案" maps to study protocol, not Statistical Analysis Plan. Correct siblings: 5615251a, 38081caa, c31af306 all use "统计分析计划".
  **Minimal fix:** → "统计分析计划".

#### D9 — Moderate — "rescue therapy" → "急救治疗" (3 keys)
- **93c5cbdf637e, 57be442f210b, 886f13e3d2e0**.
  Source: "If a participant received any rescue therapy…". Candidates: "急救治疗" (emergency care register). Majority usage in the same corpus is "补救治疗" (e.g., c31af306, f2cede23, 4dafe82f).
  **Minimal fix:** → "补救治疗".

#### D10 — Minor — WI-NRS 0–10 range dropped (3 keys)
- **3e0db3336455, d3877a66bead, d9939694689d**.
  Source: "…(WI-NRS) ranged/ranging from 0 to 10…". Candidate for these three omits the range (sibling 974030ad keeps "（评分范围0至10分）").
  **Minimal fix:** add "（评分范围0至10分）".

#### D11 — Minor — 3e0db333 cluster (secondary items)
- "Diagnosed by a dermatologist for at least 3 months **before the screening visit**" → "由皮肤科医生确诊患病且**病程至少已达3个月**" — loses the screening-visit anchor and shifts "time since diagnosis" to "disease duration" (sibling d3877a66: "确诊时间距筛选访视时至少已有3个月" is correct). Fix: align with d3877a66 wording.
- "would adversely affect" → "**可能**影响受试者参与研究" (drops "adversely", weakens "would"); same weakening in 974030ad. Fix: "会对受试者参与研究产生不利影响".
- "肺结核" narrowing (covered in D4).

#### D12 — Minor — "as per standard of care" dropped (2 of 4 rows)
- **76b84054ffad, 6ace0211…**: "尚未按照标准治疗…" absent — "以及未得到妥善治疗的糖尿病或甲状腺疾病". Preserved correctly in 19536677 and eee88f06 ("尚未按照标准治疗方案得到妥善治疗的…").
  **Minimal fix:** add "按标准治疗（规范）" to the two rows.

#### D13 — Minor/systematic — "untoward" → "非预期" (4 AE-definition keys)
- **056321b915d9, 1dd06208acdf, f265210531ea, ba190782e57f**: "any untoward medical occurrence" → "任何…**非预期**医学情况". "非预期" conventionally maps to "unexpected" in PV usage; standard alternative is "不良医学事件/不利医学情况". Flag-level only; the surrounding AE/SAE logic (all SAE categories, +14-week TE window, safety population) is intact.
  **Minimal fix (optional batch):** "任何不利的医学情况".

#### D14 — Micro/consistency set (affects ~12 keys + a few defect keys; no standalone blockers)
- IGA anchors vary across rows: clear = 完全消退/完全清除; almost clear = 几乎消退 (6cbaab68, 58523892, 631a0e58) / 几乎无可见皮损 (538260f6, 3a424974, 0d83a72c) / 几乎痊愈 (4f975b67, c7370128). Same source anchor, 3–4 renderings.
- "5级评分制/5级评分法", "占比/比例/百分比", "各组的最小二乘均值" additions (efb49690, 8544ae32), "总评分范围**同样**为0至42分" oddity (8544ae32), "计算结果即为最小二乘均值" phrasing (631a0e58).
- d5637eb78de8 keeps "PN分期总体评分" (Latin PN) inside a Chinese name where siblings expand 结节性痒疹.
- 3228c81d order swap ("治疗增强型" before "治疗期间出现") — content complete.
- 974030ad: "在基线时距既往确诊的恶性肿瘤病史未满5年" is grammatically strained; "（如周围神经病变…）" narrows "neuropathy" to peripheral (d9939694 does not).
- 76b84054/6ace0211 "经证实有效" vs 86a8e145/2c03caeb "有效且经批准" for "adequate and approved".
- 144fc0e9 drops "both timepoints" ("分析窗口的时间范围亦相应予以延长").

#### Artifact-level finding (not a translation defect)
- **A1 — Truncated source extract:** `c31af306ee4e` (`c-nct04501666-sec4-description`) — the frozen `source_text` ends mid-word: "…are considered as non-**responde**" (receipt line 5675 area; mirror-consistent). The Chinese display is complete and correct, but the frozen source excerpt is clipped (likely an extraction length cap; it is the only mid-word clip found). Recommendation: re-extract this one row's source in any repair receipt so the pair is fully auditable.

---

### 2. Unchanged positive controls (verified faithful; no change requested)

- **Age/numeric one-liners:** 2ff8b1e8 (18 Years→18岁), 158f9d6f (80 Years→80岁); all week enumerations intact (4dcd443a: 第1–24周 complete).
- **Arm/intervention one-liners:** 972c6db6, 3ce4ed36, 10aad988, 414f03f6, 85cdf6b3, e68c614d (Placebo→安慰剂), 6e1fdb97, 988476d5, 1d0721f8, b386e85b, 2a17bd77, c28dfa5a (Nemolizumab→奈莫利珠单抗), 877d2048, b009e9ee.
- **Dosing controls:** 87228b88 (dupilumab 600 mg loading → 300 mg q2w × 24 w; "负荷剂量" correct), **9e9174af** (placebo loading dose → "作为负荷剂量" — the correct sibling of D1), **50b19a29** (nemolizumab placebo weight branches: <90 kg two SC at baseline then one SC Q4W; ≥90 kg two then two Q4W × 16 w — all numbers/branches preserved).
- **Definitions/analysis:** 280d2083/8d4b8179 (ADA: emergent vs boosted, ≥4-fold, titer bands <1,000 / 1,000–10,000 / >10,000), 056321b9/1dd06208/f2652105/ba190782 (AE/SAE category lists complete, IMP+14w window, safety population — D13 term caveat only), 74beaa08/e4494a2d/8f8b7149 (TEAE/TESAE/AESI counts), 93c5cbdf composite-variable strategy mechanics (worst possible value; missing→non-responder), 329b696f/4b32d039/d504c08d/4e24e3ee/08577552/d210f64b/3feb9c8b (≥4-point / <2 endpoint definitions with correct weeks), 2b9e0850/886f13e3 (IGA success = 0/1 + ≥2-point reduction, scale 0–4), 9005f810/b0f3bba2/beb44711/7baba592 (composite WI-NRS ≥4 + IGA 0/1), 1b368d93/849ed3a3 (primary ≥4 at Week 24 with 0–10 anchors and direction).
- **Scales/directions:** 6cbaab68/538260f6/fc108c30/0d83a72c/631a0e58/3a424974 (IGA PN-S 0–4 anchors, higher=worse), 4f975b67/c7370128 (IGA PN-A excoriation bands 0% / ≤10% / 11–25% / 26–75% / 76–100%), b921ef71/8544ae32 (HADS 14 items, 0–21 subscales, 0–42 total, direction), 41533478 (DLQI 10 questions, 0–3 Likert, total 0–30), efb49690 (Sleep-NRS 0=worst/10=best, higher=better sleep), 5615251a/ad7d1170/c31af306 (SD NRS baseline window incl. treatment-start time, ≥4 of 7 days, rounding prohibition), 57be442f (SD NRS anchors — D9 term caveat only).
- **Eligibility structures:** 76b84054/86a8e145 (NCT04501666: 6-month history, ≥20 nodules bilateral, IGA ≥3, PP NRS ≥7.0 both windows, 12-week contraception, serology list), 6ace0211/2c03caeb/eee88f06 (NCT04501679 same set), 974030ad/2ff8b1e8 etc. (age/lesion/emollient rules; "or when TCS not medically advisable" preserved everywhere).
- **Source-ambiguity handling (positive):** the garbled "Within 6 months before the screening visit, or documented diagnosis of…AD…" bullet is rendered with a consistent, defensible interpretation in all four occurrences rather than silently "fixed"; source typos (`\>=`, "abled") were not propagated.

---

### 3. Root-cause analysis (as requested — targeted, not page-by-page)

1. **The material defects concentrate in the 63 `retranslated` clauses.** All of D1–D7, D10–D12 occur in rows marked `retranslated`. The two `reused`-row defects are term-level only (D8/D9, with acf04fd9 showing a remediated pattern). So the failure surface is the *retranslation pass*, not the whole corpus.
2. **Two mechanical failure signatures in the retranslated family:**
   - *Negation/parenthetical contamination across sibling branches in one paragraph* (D1: the ≥90 kg "(no loading dose)" wording bleeding into the <90 kg "loading dose" branch, twice; D2: "每周" next to its own "(即每2周1次)" correction).
   - *Tail-clause elision*: exception/qualifier clauses at sentence end dropped — "unless documented adequately treated" (×4), "Active malignancy" (×1), "but not limited to" (×8), "as per standard of care" (×2), "both timepoints" (×1).
3. **The correct target language exists inside the same corpus** for every defect class (超强效 in NCT04183335 siblings; 作为负荷剂量 in 9e9174af; 统计分析计划 in 5615251a/38081caa; 补救治疗 in c31af306 et al.; 无应答者 in acf04fd9/886f13e3; 每2周1次 in 87228b88/2a17bd77). This bounds the repair to literal, low-risk replacements and means a "gold" glossary can be extracted from existing correct siblings rather than authored from scratch.
4. **Suggested gate for any future MT pass (or for the repair):** a clause-equivalence checklist — negations (无/不/未), exception clauses (除非/除…外; unless/except), parentheticals (loading/total/none), numeric ranges and thresholds, hedge words (但不限于/按标准治疗), analysis taxonomy (non-responder vs invalid), and a term glossary (补救治疗, 统计分析计划, 无应答者, 不利医学事件, 超强效). Note: the `terminology_sha256` recorded in the receipt should be checked against D9/D8 before authoring the fix (see Q2).

---

### 4. Coverage ledger — reviewed/unreviewed keys (126/126 reviewed; 0 unreviewed)

Tags: `OK` clean; `PC` clean positive control; `m` micro-consistency only; `D#` defect codes above. (12-char key prefixes; full keys are in the manifest.)

- **Pairs-1:** 3e0db3336455 (D4,D10,D11), d3877a66bead (D10), ec972b019916 (D4,m), 2ff8b1e822f5 OK·PC, 158f9d6f49bb OK·PC, 972c6db667d9 OK, 87228b881aca OK·PC, 3ce4ed362f9b OK, 10aad988f5c3 OK, 414f03f6827b OK, 85cdf6b329a5 OK, e68c614d36a1 OK, 9e9174afc818 OK·PC, 6e1fdb9712ff OK, 988476d58ed5 OK, 1d0721f8f450 OK, b386e85bbdf4 OK, 1b368d93e030 OK·PC, 849ed3a39321 OK·PC, 6cbaab680359 m, 58523892c61b m.
- **Pairs-2:** all 21 OK (9005f8106d93, b0f3bba23aaf, 96fbb391add6, 285b18cb610b, 7e699f3e7b90, 4153347809a4·PC, 52ae1ccd4d26, f27c97b3bc1d, 71075aa9cb78, b921ef71c58a·PC, a15933837991, a838c19583bc, 50ad70f908f6, ad0756037bd0, 54c1b17b9332, 4dcd443a9188·PC, b00c9c8e3b55, 2e933f7548b3, c62f803beccc, b076f41c896f, 6cf585fbe557).
- **Pairs-3:** d429e25ac6c9 OK, a9e5a8bf813f OK, 3763997ee459 OK, b07c1f99d6cc m, 538260f6b4b8 m, 6390c5aeb3bc OK, fc108c30f5f2 m, 2a3ec29a2f8b m, 4f975b67f42c OK·PC, afc5f3ec3e3c m, 74beaa0856cc OK·PC, 056321b915d9 D13, 3228c81d84da m, 280d2083300c OK·PC, 974030ad4cf6 D4,D5,m, d9939694689d D5,D10, e4439284cabc D3,D4, fad1412a3d49 D1, 2a17bd772a2b OK, 2003b08f0fb7 D2, d7b0356638a0 OK.
- **Pairs-4:** 6e0c0893f185 OK, 3f884295b6e7 OK, 817641585300 OK, 3a42497457ec OK·PC, beb447116520 OK·PC, 7baba5921290 OK, 2253c008d049 OK, d62d847dcbe4 OK, 226314f44a16 OK, fb786afd4b41 OK, efb49690459f OK·m, 8544ae32ecef OK·m, c5d333685a71 OK, 6ae0ae9a832a OK, 82b2be5b223c OK, 91eaae50095e OK, e90c7618af74 OK, 06891afae67f OK, a4ebf0d138f4 OK, d5637eb78de8 m, 0d83a72cbac8 OK·PC.
- **Pairs-5:** 631a0e58e6f2 m, da8f0f018d2e OK, c7370128531f m, 09ce6eb7d054 OK, 1dd06208acdf D13, 8d4b8179b844 OK·PC, 76b84054ffad D7,D12,m, 86a8e1458dcb OK, 19536677112e D7, c28dfa5ab89d OK, 0a847343fa25 D1, 877d2048e81d OK, 50b19a29a027 OK·PC, 329b696f6166 OK·PC, 93c5cbdf637e D8,D9, 4b32d039a348 OK·PC, 2b9e0850110a OK·PC, 8f8b714952f2 OK·PC, f265210531ea D13, d504c08ddabd OK·PC, 38081caa0ff7 OK·PC.
- **Pairs-6:** d210f64b9f93 OK, 5615251a12a8 OK·PC, 4e24e3ee14cb OK·PC, 57be442f210b D8,D9, 085775521515 OK·PC, c31af306ee4e OK (A1 note), 3feb9c8b5742 OK, 6ace02119e3e D7,D12,m, 2c03caebe364 OK, eee88f06e2f8 D7, 590552e783c9 D1, b009e9eea223 OK, 144fc0e9bdcf D6,m, 886f13e3d2e0 D9, f2cede23c81c D6, 41632611cd0b D6, ad7d1170276e D6, 4dafe82f04d9 D6, acf04fd92f00 OK·PC (remedied pattern), e4494a2df7c1 OK·PC, ba190782e57f D13.

**Totals:** 126 reviewed / 0 unreviewed; 26 keys with ≥1 listed defect; 12 micro-only keys; 88 clean keys.

---

### 5. Objections, proposed solutions, decision points, and bounded questions for Codex

**Objections (highest first):**
1. **A single batch verdict would be wrong.** The artifact is two populations: 63 retranslated (carries every material defect) and 63 reused (carries only term-level issues, one already remediated in-row). Recommendation: split disposition — bounded repair list for the retranslated family; term-normalization set for the reused family; no re-run of the pipeline.
2. **D1/D2 are release-blocking for the affected keys if `display_text` renders as-is.** "无负荷剂量" (×3 rows, incl. both registries' nemolizumab weight-branch row) and "每周均接受…（即每2周1次）" are dose-instruction inversions/contradictions, i.e., the most hazardous defects found, and they sit exactly in the "doses/loading/weight branches" preservation scope. D3/D4 block the affected eligibility rows; D6 blocks analysis-semantics rows.
3. **Whole-window re-review is unnecessary and risky.** All fixable text is expressible as literal replacements on the frozen display_text; a per-key before/after diff keyed by the existing hashes is auditable and preserves the rest of the frozen artifact.

**Proposed remediation (bounded):** a single "C v3 repair" receipt covering the defect keys (~10 material: fad1412a, 0a847343, 590552e7, 2003b08f, e4439284, 3e0db333, ec972b01, 974030ad + ~16 minor/term keys listed in the ledger), with (a) literal replacement patches, (b) one-line re-check of each patched clause against its source, (c) re-extraction of the clipped source for c31af306, (d) glossary rows: 补救治疗 / 统计分析计划 / 无应答者 / 不利医学事件 / 超强效 / 例如但不限于 / 除非已有记录证明…. No re-translation, no other keys touched.

**Decision points for Codex:**
- D1: approve the repair target "（60毫克负荷剂量）" for the <90 kg nemolizumab branch — confirm against the upstream label intent (OLYMPIA-style: 60 mg loading then 30 mg Q4W for <90 kg; 60 mg Q4W, no loading, for ≥90 kg). My fix follows the frozen source literally; flag only if the source itself is the error (in which case, do NOT silent-fix — classify as source-defect).
- D6: approve "按无应答处理/视为无应答者" as the canonical rendering (matches acf04fd9's in-row remedy).
- Whether reused-row term fixes (D8/D9) are in scope now or deferred; provisional recommendation: include (term-only, zero re-translation).

**Bounded questions (answerable in a same-session follow-up):**
- **Q1 (attribution):** The receipt records `parent_receipt_sha256=70ff0e34…` and per-clause `repair_parent_receipt_sha256`. May I be granted that parent receipt (read-only) to attribute whether D1–D7 were introduced by the v2 retranslation or inherited from v1? Why it matters: the prevention gate differs (retranslation QA vs legacy corruption). Provisional path: fix regardless; attribution is optional and not required for the repair.
- **Q2 (glossary authority):** Is there an authoritative terminology file behind `terminology_sha256=0850942c…`? If it contains "急救治疗"/"研究实施方案" for rescue therapy/SAP, the D8/D9 fix must update the glossary, not just the text. Provisional: fix text to majority usage (补救治疗/统计分析计划) and align the glossary if it disagrees.
- **Q3 (render path):** Does portal C render `display_text` verbatim (no downstream normalization)? This determines whether D8/D13-type term drifts are user-visible. Provisional safe assumption: verbatim → all D-items are user-visible.

**Boundary confirmations:** no file was written; the runner-managed report path was not touched; no browser/network/recursive dispatch; earlier model opinions not read; the translator model (HyMT2-30B-A3B-oQ8-MLX) differs from this reviewer model; scientific acceptance/current/browser remain false/NOT_RUN and nothing in this output should be read as medical approval.
