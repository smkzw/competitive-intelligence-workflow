Round 2 already finished. I’ll only re-check the three PDF hashes so we don’t rest on a stale lock.Round 2 still stands. The three PDFs are the same lock, so there is nothing new to re-audit.

**Verdict: do not accept** these three PDFs as a medical-manager manuscript. Machine `summary.json` remaining green does not change that.

Remaining blockers:

1. **B11** — disease-context continuation has no `续表` title.
2. **C5/C6/C9/C10/C12/C13** — timepoint column wraps mid-number (`基线至第5` / `2周` = week 52; `诱导期第1` / `6周` = week 16).
3. **C8** — eligibility wraps product/scale names (`度普利尤单` / `抗`, `Lebrikizuma` / `b`, `E` / `ASI`).

The old scientific blockers (EASI-75 contradiction, `突破性溶血`, sample-size axis copy, truncated NCT, backend field names) remain closed on this lock.

I am not creating a Trellis task for this turn. If you want one for the next Codex repair/re-render pass, say so.
