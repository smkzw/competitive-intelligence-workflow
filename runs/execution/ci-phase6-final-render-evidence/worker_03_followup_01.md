# Visual Evidence Follow-up: worker_03

## Refreshed Bindings

- Fallback: `openai-codex / gpt-5.6-luna`.
- Scope limitation: evidence packaging and validator execution only; no independent visual-verification verdict, clinical/regulatory acceptance, delivery transition, or graph-state change.
- Current candidate:
  - Report: `B`
  - Version: `v-fixture-b-pnh-001`
  - Candidate artifact digest: `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`
  - Artifact size: `5,241,779` bytes
- Locked report snapshot SHA-256: `b6ea52732bf2cd7469065f59088e2f29c9ca07c9526610bee3ae581e0431619a`
- Design-contract digest: `b6c075c75f3b54d9afbfaeb732a6b51419a20e9136aafc17a8481288de300daf`
- Refreshed browser metrics:
  - SHA-256: `cfe8dc516ff399d888d9d8c1879a63d3b38c2f6fef6f94f95dd7c2a8173ed168`
  - `36` default render records.
  - Engines: Chromium `149.0.7827.55`, WebKit `26.5`.
  - Viewports: `768×900`, `1024×900`, `1440×900`.
  - Pages: `overview`, `efficacy`, `safety`, `baseline-overview`, `disposition-overview`, `efficacy-safety-matrix`.
- Narrow search alternatives preserved:
  - `全局搜索` remains listed in `unavailable_required_fields` for all 24 narrow-width targets.
  - All 24 corresponding `responsive_alternatives` are `verified: true`.
  - The alternative records retain actual menu interaction, query `疗效`, 10 results, keyboard focus, Escape behavior, screenshot paths, and screenshot hashes.
  - Responsive-search screenshot hashes:
    - Chromium 768: `7b7783beb2b33023c5321a210cb6c5f31c4891cbc7f3b410c3ea3c467eb1e728`
    - Chromium 1024: `18d8796a63ad06dfaa155713ecfea68c0ae2ec4cc4e9ec2cf9a785d3a6223495`
    - WebKit 768: `6c5db8f925a7d33980463e597d591d59318c08a5f1c295da0561ce1b8aa80e04`
    - WebKit 1024: `55e84186dd746d4dd13131290d9b1458b0beb2f0ca26be349e5512354336ecc0`

## Validation

- Snapshot digest recomputation: matched `b6ea5273...`.
- Candidate directory digest recomputation: matched `f094848b...`.
- Candidate byte-size recomputation: matched `5,241,779`.
- Design-contract digest: matched candidate manifest binding `b6c075c7...`.
- Visual-plan JSON Schema: **PASS**, `0` errors.
- Render-evidence JSON Schema: **PASS**, `0` errors.
- `validate_visual_finalization_plan` with authoritative snapshot and design-contract digests: **PASS**.
- `validate_visual_render_evidence` with authoritative candidate and current plan digests: **PASS**.
- Canonical plan digest: `29d32a55edfd673ba5123dd4fa8a5d35764fd2815132f6b2b4377be87c107e7d`
- Canonical render-evidence digest: `ea91e7f9e0c0a0afa304d2044d8897a98c1f5747b376f10d6696f6429ba85b22`
- Render targets: `36`, complete Chromium/WebKit × 768/1024/1440 matrix.
- Screenshot presence/hash checks: `36/36` matched.
- Interaction checks: all six triggers `36/36` passed:
  - `page_load`
  - `filter_change`
  - `drill_down`
  - `search`
  - `keyboard`
  - `reduced_motion`
- Defects: `0`.
- Overflow, clipping, overlap, unreadable labels, page errors, console errors, and runtime interaction errors: all `0`.

## Artifacts

- `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reviews/visual-finalization/visual-plan.json`
  - File SHA-256: `4a9bc1668ed0279b07c602d62f377e55409ae48e6a26dedbf5907fb6988457a2`
- `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reviews/visual-finalization/render-evidence.json`
  - File SHA-256: `5f58e405f7162853fe3ae4f2481514bed6064733548ccf52b906761910b45872`
- Only the two authorized JSON artifacts were regenerated.
- No `visual-verification-reference.json` was created.

## Remaining Boundary

- The prior missing-768 and narrow-search defects were removed only after refreshed metrics supplied the complete 768/1024/1440 matrix and verified menu-based search alternatives. No failed result was coerced.
- Codex retains final visual, clinical, regulatory, candidate-promotion, and delivery authority.
