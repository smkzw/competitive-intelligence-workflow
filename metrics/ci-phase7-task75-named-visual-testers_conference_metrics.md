# Conference Metrics: ci-phase7-task75-named-visual-testers

Date: 2026-08-31

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `minimax-review` | `cms-router` | `minimax-m3` | completed | 192.1 s | runner未单列 | 72,129 | current-digest defect discovery |
| `hy3x-review` | `codebuddy-cli` | `hy3-x` | completed | 504.7 s | runner未单列 | adapter未提供 | stale-evidence claims filtered |

## Timeout And Retry Evidence

Both explicit named routes completed without fallback. They were separate
supplemental test runs, not participants in the formal Cursor/Grok conference.

## Quality Decision

Useful for defect discovery; insufficient for final acceptance because the final
freeze was created later and the Hy3-x report relied partly on stale screenshots.
