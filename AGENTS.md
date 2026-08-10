<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

# Project Rules

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` is the approved product contract. Do not silently relax its evidence thresholds, report scope, interaction contract, or format-specific acceptance criteria.
- The repository is a clean rebuild. Runtime code, Skills, assets, tests, and generated artifacts must not depend on the legacy workspace.
- User-facing copy must be native Chinese for senior clinical-trial medical professionals. Do not expose prompt text, log labels, backend state names, or unnecessary English system terminology in reports.
- A missing key-evidence threshold is fail-closed: no draft, placeholder, or partially populated report may be rendered. Diagnose technical failure separately from evidence that is not public or not found after exhaustive search.
- Security-specific test expansion is outside the approved product scope. Concentrate validation on functional correctness, scientific completeness, data lineage, interaction, native rendering, and visual usability.
- Generated HTML, PDF, HTML-PPT, and PPTX are not accepted by file existence alone. Reopen the real artifact and bind acceptance to the current run and immutable report snapshot.
- Do not modify or delete the legacy workspace during implementation. Final cutover and deletion require the plan's full acceptance closure and separate user authorization.
