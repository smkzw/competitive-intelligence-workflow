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

# Current Product Scope — rebaseline-v2

- The user authorized the rebaseline-v2 subsystem on 2026-10-23. Develop only `rebaseline-v2/`; v1 code, paused projects and dirty files remain read-only references. Do not resume the old 1007V1 repair/review loops.
- Current product requirements, architecture, milestones and state live in `rebaseline-v2/docs/01_PRD.md`, `02_ARCHITECTURE.md`, `03_PLAN.md` and `STATUS.md`. Read `04_AGENT_RULES.md` as local v2 rules; it cannot override global governance or grant destructive authority.
- Active Trellis task: `.trellis/tasks/10-23-rebaseline-v2-m1/`. Old root HANDOFF/pause records describe v1 historical state, not a pause of the newly authorized v2 work.
- v2 is a single-user Web service with its own minimal Skill Harness. Do not carry v1 host packages, report editing/undo/configuration/sharing or 24-portal gates into its acceptance. Preserve their history without deleting it.
- Keep sources, CAS, databases, credentials and runtime receipts local and out of commits. No history rewriting, force push, global routing changes or cleanup is authorized by the review ZIP.
- Never touch the retired Chinese workspace. Preserve unknown files and all v1 user changes; explicit English-root working directories are mandatory.
- Retain native Chinese expert presentation, ECharts with matching tables, genuine source context, missing-not-zero and desktop screen use. Avoid defensive disclaimer walls and project-specific renderer dictionaries.

# Historical v1 Project Rules (v1 only)

- The latest audience-presentation contract is the 2026-10-11 expert-reading section of `packets/2026-09-22-sol-delivery/PRD.md`, with matching DESIGN/PLAN/ACCEPTANCE and task records. It supersedes older defensive-copy requirements: no expert-facing disclaimer walls; real comparison is ECharts plus the corresponding table, and longitudinal data uses annotated lines. Keep source data and internal scientific checks. Do not reintroduce the removed prose during later repairs.

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` is the approved product contract. The v1.2 design, ZCode review material, historical catalogs, and existing `competitive-intelligence-workflow` Skill are inputs to verify, not authority; where they conflict with v1.3 or the user's later decisions, v1.3 and the later decisions win.
- Preserve the current dirty tree and unrelated user work. Do not use `git reset`, `git checkout`, `git clean`, or `git add .`, and do not rewrite sealed Task 10.3-10.5 evidence.
- The v1 product surface is HTML-only: one public Skill, three independent A/B/C multi-page portals, and lightweight Codex/Hermes/OMP adapters. PDF, HTML-PPT, PPTX, scheduled monitoring, CSV/XLSX export, radar charts, and evidence-maturity views must not appear in the install bundle or v1 acceptance surface.
- Runtime code, Skills, assets, tests, and generated artifacts must not depend on the legacy workspace. Before the separately authorized retirement stage, do not read, inventory, probe, chmod, modify, absence-check, or delete the legacy Chinese workspace.
- User-facing copy must be native Chinese for senior clinical-trial medical professionals. Do not expose prompt text, log labels, backend state names, internal paths/locators, or unnecessary English system terminology in reports.
- Missing evidence follows the v1.3 tiered contract: run two materially different recovery strategies and independent review for critical gaps; deliver with explicit limits only when the core question remains answerable; otherwise render a concise evidence-insufficiency page while retaining the detailed blocker audit internally. Never use empty charts, fixed zero walls, placeholders, or dropped competitors to simulate completeness.
- Every first report must close the global/China competitor universe through required source routes and alias, target, company, and trial reverse expansion. No Top-N or default ranking may substitute for closure.
- Required publication handling, optional authenticated-browser access, and manual inbox processing must preserve the credential and byte-integrity boundaries in v1.3. Credentials, session tokens, and unredacted authentication material must not enter prompts, files, logs, receipts, snapshots, or bundles.
- Generated A/B/C HTML is not accepted by file existence alone. Reopen every physical page in Chromium and WebKit at the four v1.3 viewport classes, bind acceptance to the current run and immutable report snapshot, and keep Codex responsible for final scientific, browser, visual, packaging, recovery, and release acceptance.
- Release states are only `DEVELOPMENT_CANDIDATE`, `RC_FROZEN`, and `RELEASED`. Do not emit an RC or release signal until its actual gates pass; deferred or not-applicable cases never count as accepted.
