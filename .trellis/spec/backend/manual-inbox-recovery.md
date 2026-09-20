# Manual Inbox Recovery

> Durable conventions for user-assisted source recovery under the approved v1.3 contract.

## User Contract

- Create one Markdown download request per blocked snapshot only when a canonical A/B/C GateSpec still has a critical unresolved unit and the named required publication is expected to close at least one missing unit.
- Require a DOI, PMID, or registry identifier that can be checked deterministically. Blank identifiers produce a typed business rejection before any ledger row, directory, or user task is created.
- The user only downloads the named attachment, keeps the publisher's filename, and places it in the request-specific inbox. Validation and canonical naming are system responsibilities.
- Before any accepted-file rename, persist the original filename, SHA-256, DOI/PMID/registry identity, target filename, request/snapshot identity, and collision result. Then perform an atomic rename inside the same request-specific inbox. Do not copy the accepted file to another directory, move it out of the inbox, delete it, or modify its bytes.
- A user's one-time “cannot obtain” response is durable for the same snapshot. Do not ask again in that snapshot: continue with an explicit limitation only when official registry/regulatory evidence still answers the core question; otherwise produce the concise evidence-insufficiency page and retain the detailed blocker audit internally.
- User-visible Chinese copy states what is missing, why it is needed, where to download it, and where to place it. It must not expose state enums, hashes, GateSpec names, or media-type jargon.

## Matching And Isolation

- File extensions are case-insensitive. Validate the extension, derived media type, and content together; `publication_pdf` requires a real parseable PDF.
- Match normalized DOI, PMID, and NCT identifiers from file content. A DOI can establish unique identity; registry-only or PMID-only documents additionally require a meaningful title match. English titles must match distinctive words, not only generic words such as `study` or `results`.
- Ambiguity checks are scoped to the same project and immutable snapshot. A stale request from an earlier snapshot must not block the current snapshot's dedicated inbox.
- Keep rejected or ambiguous files in the request-specific inbox under their original names. Record a typed rejection and one Chinese processing-note line per concrete file; do not silently move, rename, overwrite, or delete them.
- If the canonical target name already exists, fail closed unless the persisted mapping proves it is the same accepted file and digest. Never overwrite an unrelated target.

## Replay Invariants

- Replaying from `file_detected`, `matched`, or `accepted` must converge without duplicate events, source versions, rename mappings, or re-extraction jobs.
- A replay from `matched` may continue directly to acceptance only when the content digest is unchanged.
- Persist the pre-rename mapping before touching the directory entry. If a crash occurs before rename, replay verifies the original file digest and completes the same rename. If a crash occurs after rename, replay verifies the target digest and mapping and records no second rename.
- Accepted-state replay must leave exactly one canonical file in the same inbox. A missing source and target, both names present, a changed digest, or an unbound target name fails closed; replay never deletes a “leftover” file to guess the intended state.
- Source-version and extraction records reference the canonical in-place file and its content digest. A content-addressed digest may be recorded, but creating a second archival copy is not part of v1 acceptance.

## Required Regression Coverage

- Uppercase `.PDF`, `.HTML`, and `.TXT` names work without user renaming.
- A crash immediately before and immediately after the atomic rename resumes through the filesystem scanner.
- Accepted-state replay preserves one in-place canonical file with zero new events, mappings, renames, or jobs.
- Original and canonical paths have the same parent directory; pre/post SHA-256 and file bytes are identical.
- Existing-target collision, both-names-present ambiguity, changed bytes, wrong attachment, scanned/unreadable PDF, and DOI/registry mismatch all fail closed without overwriting or deleting either file.
- Same-run ambiguity remains blocked while cross-run requests remain independent.
- Empty and whitespace-only identifiers create no side effects and return the typed business rejection.
- Multi-round rejection notes retain all concrete filenames without duplicate or generic lines.
- One-time “cannot obtain” is not re-prompted within the same snapshot and does not suppress a new request for a later snapshot when the blocking evidence edge genuinely changes.
