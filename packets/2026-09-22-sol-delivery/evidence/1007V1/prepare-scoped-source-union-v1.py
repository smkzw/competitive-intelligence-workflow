"""Read-only union of the new source candidates and exact accepted ancestors.

No ingestion, scientific acceptance, current/DB write or freshness claim.
The new local replay observation never replaces public/version dates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.fresh_research_ingestion import _validate_references
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.evidence import source_version_identity
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    verify_source_text_derivation,
)

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RECEIPT = PROJECT / "evidence/library/joint-ab-source-context-v1/receipt-recovered-v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(source: SourceCapture) -> str:
    return source_version_identity(
        source.source_id,
        hashlib.sha256(source.content_text.encode()).hexdigest(),
        published_at=source.date_evidence("published_at"),
        effective_at=source.date_evidence("effective_at"),
        first_disclosed_at=source.date_evidence("first_disclosed_at"),
        text_derivation=source.text_derivation,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-version", type=int, choices=(1, 2), default=1)
    revision = parser.parse_args().candidate_version
    out = ROOT / f".artifacts/1007-scoped-source-union-preparation-v{revision}"
    new = ROOT / f".artifacts/1007-scoped-source-pool-reconcile-v{revision}/candidate.json"
    expected = {
        1: "73ae5683f0de826dc125898173dac7b92a6e638316668ab259f4750b754ceb6c",
        2: "9aae15b65841b35910c51469ac0db875729d17fa47454e71e6cc281aa8f22587",
    }[revision]
    if out.exists():
        raise SystemExit("Union preparation already exists; reopen, never overwrite/retry")
    assert sha(new) == expected
    recovered = json.loads(RECEIPT.read_bytes())
    locked = LockedSnapshot.model_validate(recovered["evidence_snapshot"])
    assert locked.sha256 == "2d0521aef6132555c4ebd8cd262281a93cb5e6c4da615075036960aa4462b154"
    old = SnapshotStore(PROJECT).read(locked)
    cutoff = datetime.fromisoformat(old["data_cutoff"])
    assert cutoff.isoformat() == "2026-10-07T23:59:59.999999+08:00"
    protected = {
        p: sha(p)
        for p in (
            new,
            RECEIPT,
            PROJECT / locked.relative_path,
            PROJECT / "state/project.sqlite",
            PROJECT / "reports/current.json",
        )
    }
    local_observation = datetime.now(UTC)
    candidate = json.loads(new.read_bytes())
    sources = [SourceCapture.model_validate(x["capture"]) for x in old["closure"]["sources"]]
    fact_payloads = [
        {**x["fact"], "row_ref": x["consumer_binding"]["row_ref"]} for x in old["closure"]["facts"]
    ]
    claim_payloads = [x["claim"] for x in old["closure"]["claims"]]
    assert (len(sources), len(fact_payloads), len(claim_payloads)) == (3, 105, 91)
    new_versions = {}
    for capture in candidate["source_captures"].values():
        before = SourceCapture.model_validate(capture)
        assert before.access_method == "offline_cas_replay"
        after = SourceCapture.model_validate(
            {
                **capture,
                "acquired_at": local_observation.isoformat(),
            }
        )
        assert version(before) == version(after)
        assert after.model_dump(exclude={"acquired_at"}) == before.model_dump(
            exclude={"acquired_at"}
        )
        sources.append(after)
        new_versions[after.source_id] = version(after)
    fact_payloads.extend(candidate["facts"])
    claim_payloads.extend(candidate["claims"])
    facts = tuple(ResearchFact.model_validate(x) for x in fact_payloads)
    claims = tuple(ResearchClaim.model_validate(x) for x in claim_payloads)
    _validate_references(sources, facts, claims)
    assert len({f.row_ref for f in facts}) == len(facts)
    captures = {source.source_id: source for source in sources}
    for source in sources:
        assert source.is_available_by(cutoff), source.source_id
        assert source.text_derivation is not None
        verify_source_text_derivation(PROJECT, source.text_derivation, source.content_text)
    for fact in facts:
        source = captures[fact.source_id]
        assert (
            extract_locator_quote(
                source.content_text,
                media_type=source.media_type,
                locator=fact.locator,
            )
            == fact.original_text
        )
    old_versions = {x["fact"]["fact_id"]: x["fact_version_id"] for x in old["closure"]["facts"]}
    assert set(old_versions).isdisjoint(f["fact_id"] for f in candidate["facts"])
    package = {
        "schema_version": "1007-source-only-union-preparation-1",
        "project_id": old["project_id"],
        "contract_version": old["contract_version"],
        "data_cutoff": old["data_cutoff"],
        "sources": [s.model_dump(mode="json") for s in sources],
        "facts": [f.model_dump(mode="json") for f in facts],
        "claims": [c.model_dump(mode="json") for c in claims],
    }
    encoded = json.dumps(
        package, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    out.mkdir()
    with (out / "source-package.json").open("x") as stream:
        stream.write(encoded)
    proof = {
        "status": "VERIFIED_SOURCE_UNION_PREPARED_NOT_INGESTED_NOT_ACCEPTED_NOT_CURRENT",
        "source_package_sha256": sha(out / "source-package.json"),
        "candidate_version": revision,
        "candidate_sha256": expected,
        "local_replay_observed_at": local_observation.isoformat(),
        "counts": {"sources": len(sources), "facts": len(facts), "claims": len(claims)},
        "fact_roles": dict(Counter(f.result_context.value_role for f in facts if f.result_context)),
        "exact_old_accepted_ancestor_versions": old_versions,
        "new_source_versions": new_versions,
        "cutoff": old["data_cutoff"],
        "source_date_scope": (
            "Current record-version public calendar dates precede the fixed project cutoff; "
            "exact existing source date locators/derivation reopened. No live current source "
            "check or independent historical adjudication claimed."
        ),
        "acquisition_scope": (
            "New captures' acquired_at is this actual local CAS replay observation "
            "only, not network acquisition, first disclosure or freshness. All source "
            "versions/date proofs/content unchanged; old3 captures unchanged."
        ),
        "input_hashes": {str(p.relative_to(ROOT)): v for p, v in protected.items()},
        "limits": (
            "Old105 exact ancestors plus pinned new candidate facts; four older trials/279 "
            "still-unaccepted rows and C258 remain separate. No current user-cleared "
            "versions replaced, no source acceptance or universe/numeric-frame/RC claim."
        ),
    }
    assert all(sha(path) == digest for path, digest in protected.items())
    with (out / "proof.json").open("x") as stream:
        json.dump(proof, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "status": proof["status"],
                "counts": proof["counts"],
                "source_package_sha256": proof["source_package_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
