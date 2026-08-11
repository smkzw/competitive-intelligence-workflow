# Independent review — Phase 0 Kangzhe repair contract

- Reviewer route: Codex CLI compatibility / `gpt-5.6-luna:max`
- Session: `019fee5a-0e56-7ae1-9b7a-36b19dbdedca`
- Permission: read-only
- Final verdict: `PASS`
- Initial output: `runs/conference/ci_phase0_design_repair_contract_20260811/luna_check.md`
- Final output: `runs/conference/ci_phase0_design_repair_contract_20260811/luna_followup_3.md`

## Closed findings

1. P0 — DS07/DS08 的字号例外没有精确固定 `data-density=ultra`、§13.3 条件、允许角色和负例。
2. P0 — runner-owned immutable manifest、current-run lineage、verifier 隔离、矩阵写入权和 exact-test registry 不完整，可被自签或旧产物假绿。
3. P1 — source-pack 没有 typed schema、稳定 ID、locator、单位/分母和互斥数字分类。
4. P1 — `aside.notes` 未独立提取并与页面、图、表共同重算。
5. P1 — DS01 未把两个 compat stubs 纳入实际读取与负例。
6. P1 — S2 未明确仅为设计包重验，且没有机械保留原生 PDF、HTML-PPT 固定运行时和 PPT Master 必经边界。

后续同一会话又发现并关闭了四个机械缺口：清单摘要必须由 validator 规范化重算；运行前状态必须明确存在/不存在；定量声明必须与 `audience_fact` 的值、单位和分母一致；讲者稿数字必须位于绑定同一 claim/value 的受控原文片段。

## Acceptance state

Hermes workflow guard initialized the conference shell, but the declared native Luna capability was unavailable, so the documented CLI compatibility route was used. The exact same model session performed three targeted follow-ups. The final pass reran five in-memory falsification mutations and rejected all five;专项测试为 `32 passed`，项目全量为 `38 passed`，包内测试为 `Ran 8 tests ... OK`。

Acceptance is limited to the project-owned design contract, schemas and validator. No A/B/C portal, PDF, HTML-PPT or PPTX artifact is accepted by this review.

## Verification

- Same isolated verifier session: `019fee5a-0e56-7ae1-9b7a-36b19dbdedca`.
- Final read-only result: `runs/conference/ci_phase0_design_repair_contract_20260811/luna_followup_3.md`, SHA-256 `f6601713...b913`.
- Deterministic verification: focused `32 passed`, repository `38 passed`, package `8 tests OK`.
- Falsification verification: five previously accepted mutations were rerun and all rejected.

## Boundary

This review accepts only the internalized design contract, schemas and validator. It does not accept offline presentation assets, a public Skill package, any source-research result, or any report artifact.
