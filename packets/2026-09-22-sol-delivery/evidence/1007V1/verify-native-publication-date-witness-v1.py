"""Reopen only two existing native date nodes; not full-text or fact adoption."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.source_research_service import SourceCapture, _public_quote_is_exact
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / ".artifacts/1007-publication-native-package-v1/source-package.json"
EXPECTED = "6909f03ab9f1c7b08b264ba31078a0dab62849937f5da059f99a72c6ab880e8e"
OUT = ROOT / ".artifacts/1007-native-date-witness-replay-v1.json"


def main() -> None:
    raw = PACKAGE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    assert not OUT.exists(), "Never overwrite a replay result"
    sources = json.loads(raw)["sources"]
    assert len(sources) == 2
    rows = []
    for payload in sources:
        source = SourceCapture.model_validate(payload)
        assert source.text_derivation is not None
        text_sha = hashlib.sha256(source.content_text.encode()).hexdigest()
        assert text_sha == source.text_derivation.text_sha256
        evidence = source.date_evidence("published_at")
        quote = extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=evidence.locator,
        )
        assert _public_quote_is_exact(evidence, quote, source)
        rows.append({"source_id": source.source_id, "source_sha256": text_sha,
                     "locator": evidence.locator.model_dump(mode="json"),
                     "original_quote": quote, "date": evidence.value.isoformat(),
                     "precision": evidence.precision, "date_replay": "PASS",
                     "first_disclosed_at": source.first_disclosed_at})
    assert PACKAGE.read_bytes() == raw
    receipt = {"scope": "native date nodes only; no version/correction or clinical qualification",
               "source_package_sha256": EXPECTED, "rows": rows, "source_writes": 0,
               "current_writes": 0, "fact_adoptions": 0, "clinical_facts_proven": 0}
    with OUT.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, sort_keys=True, indent=2)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
