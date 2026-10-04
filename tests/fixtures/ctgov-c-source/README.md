# Fixed public registry source for C regression tests

This small normative fixture retains one original ClinicalTrials.gov API v2 JSON
page, byte-for-byte, in the project's existing content-addressed layout. It is not
a current acquisition, a complete competitor universe, or an accepted clinical
conclusion. Tests deliberately retain the fixed historical replay date.

- Historical capture/evidence: `packets/2026-09-22-sol-delivery/evidence/0924V1-r24/`
  R24-50 source expansion receipt and original `.artifacts` project remain intact.
- SHA-256: `5d35c3ce835ebea73cc28e53cc6216773247fb77e0b1053b45eb83036ce6b3be`.
- Size: 2,251,577 bytes. Media type: `application/json`.
- Public study records used by these tests:
  <https://clinicaltrials.gov/study/NCT02264639> and
  <https://clinicaltrials.gov/study/NCT03829449>.
- No paper full text, commercial database contents, credentials, browser session,
  private patient records, or development logs are included.

The whole page is retained rather than reserializing two selected studies, so the
original raw-page hash, record selector, locator and extraction proofs continue to
refer to the same bytes. The `tests/` tree is outside the Skill bundle's explicit
runtime allowlist. Do not add this fixture to the installation payload.
