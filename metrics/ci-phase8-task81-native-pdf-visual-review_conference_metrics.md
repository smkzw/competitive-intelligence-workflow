# Conference Metrics: ci-phase8-task81-native-pdf-visual-review

Date: 2026-08-31

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `visual_single_object` | `cursor` fallback | `cursor-grok-4.6` | completed | same-session rounds 1–3 | runner recorded | runner recorded | pass for Task 8.1 |

## Timeout And Retry Evidence

- Grok Build failed before a resumable session was established; the runner used
  the declared Pi/Cursor/Grok fallback rather than an undeclared substitution.
- Session `01a053b1-218c-7000-afd8-e639c64f41ae` was reused for rounds 2 and 3.
- Long hard waits completed; latency was not treated as failure.

## Quality Decision

Pass for the pinned Task 8.1 vertical sample. Final participant output found no
high/medium in-scope blocker; lower-page whitespace remains a documented fixture
residual and full-report density is deferred to Task 8.2.
