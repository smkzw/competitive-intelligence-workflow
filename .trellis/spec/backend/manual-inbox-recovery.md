# Manual Inbox Recovery

> Durable conventions for user-assisted source recovery in Task 3.3 and later orchestration.

## User Contract

- Create a download request only when a canonical A/B/C GateSpec still has a critical unresolved unit and the named document is expected to close at least one missing unit.
- Require a DOI, PMID, or registry identifier that can be checked deterministically. Blank identifiers produce a typed business rejection before any ledger row, directory, or user task is created.
- The user only downloads the named attachment, keeps the publisher's filename, and places it in the request-specific inbox. Renaming, classification, and archive naming are system responsibilities.
- User-visible Chinese copy states what is missing, why it is needed, where to download it, and where to place it. It must not expose state enums, hashes, GateSpec names, or media-type jargon.

## Matching And Isolation

- File extensions are case-insensitive. Validate the extension, derived media type, and content together; `publication_pdf` requires a real parseable PDF.
- Match normalized DOI, PMID, and NCT identifiers from file content. A DOI can establish unique identity; registry-only or PMID-only documents additionally require a meaningful title match. English titles must match distinctive words, not only generic words such as `study` or `results`.
- Ambiguity checks are scoped to the same project and run. A stale request from an earlier run must not block the current run's dedicated inbox.
- Preserve every rejected file under a digest-qualified quarantine path. The Chinese processing note retains one line per concrete file and must not add a generic placeholder when the filename is known.

## Replay Invariants

- Replaying from `file_detected`, `matched`, or `accepted` must converge without duplicate events, source versions, archive files, or re-extraction jobs.
- A replay from `matched` may continue directly to acceptance only when the content digest is unchanged.
- If acceptance was persisted before the inbox copy was deleted, both scanner replay and direct `accept()` replay verify the digest and remove the leftover copy.
- Reusing an existing canonical archive requires byte-digest equality; drift fails closed.

## Required Regression Coverage

- Uppercase `.PDF`, `.HTML`, and `.TXT` names work without user renaming.
- A crash between match and acceptance resumes through the filesystem scanner.
- Accepted-state replays clean leftover inbox copies with zero new events or jobs.
- Same-run ambiguity remains blocked while cross-run requests remain independent.
- Empty and whitespace-only identifiers create no side effects and return the typed business rejection.
- Multi-round quarantine notes retain all concrete filenames without duplicate or generic lines.
