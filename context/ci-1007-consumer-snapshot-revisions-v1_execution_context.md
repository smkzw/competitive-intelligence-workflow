# 1007 consumer snapshot revision root-cause execution
Status READY. Active Goal unchanged. Method: one execution node for bounded shared consumer schema/registration/recovery/current-read work while Codex owns the scientific packet, current and final integration.
Actual RED obtained:
- tests/integration/test_1007_c_source_review_entry.py::test_corrected_display_prepares_new_epoch_without_reaccepting_source_facts
- 36 adjacent tests passed; this test fails CPortalConsumerRegistrationError: 已登记 C 消费者身份与当前候选冲突.
- Real repaired six-row PN display candidate fails identically at registration, before rendering/new epoch; original current is still absent, candidate facts unchanged.
Root cause: source_portal_consumer_bindings currently has unique(source_fact_version_id,report), binding_id lacks snapshot, so a second immutable snapshot of the SAME scientific fact cannot register independently. Six changed display originals have distinct row hashes, while 252 unchanged rows still have a new evidence_snapshot_id.
Do not create new fact versions simply to change display, no UPDATE/DELETE history, no acceptance flag, no database write in actual .artifacts projects.
Read sources, migrations 0016/0017, source C registration, A/B registration/anchors, binding recovery proof and current-reading consumers before editing. Reuse existing typed ActiveFactBinding, locked snapshot and normal epoch mechanisms.
Expected smallest complete design: version source consumers by existing evidence_snapshot_id, preserving legacy rows/IDs exactly; new snapshot-qualified IDs accepted only with full exact snapshot proof; one source fact→one row per report PER snapshot; all consumers/recovery/readers must resolve explicit scope, not arbitrary first row, last timestamp, or mixed old/new.
The shared current-reading surface must choose legitimate current consumer declarations and avoid returning duplicate historical candidate rows. Fail closed on unresolved scope, retain legacy single-snapshot behavior when no current exists and no ambiguity. Do not weaken row_sha256/semantic guards.
User/source history, scientific versions, existing frozen migrations, report version and gate semantics remain unchanged.
Owner dirty changes: source-entry test appended; materializer v-prefix fix plus its regression. Five unrelated user files and unknown untracked history protected. Worker does not edit owner materializer code/test.
