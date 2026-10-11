"""Freeze only terminal proposed identities, not worker reasoning or acceptance."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ci_workflow.domain.entities import EntityIdentity, EntityType

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / "runs/execution/ci-1007-publication-identity-proof-v1/worker_01.md"
OUT = ROOT / ".artifacts/1007-publication-identity-proof-v1"


def main() -> None:
    assert not OUT.exists(), "Do not replace an existing frozen proposal"
    text = REPORT.read_text(encoding="utf-8")
    report_sha = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    assert report_sha == "da211ef1fec4369b46545dcb54997416fda9d473fb0f9b6261109cf8f0505954"
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) == 1
    proposal = json.loads(blocks[0])
    assert proposal["proposal_status"] == "proposed_not_persisted"
    assert len(proposal["primary_cells"]) == 4
    assert proposal["registry_mapping"]["assignment"] is None
    for raw in proposal["entities"]:
        identity = EntityIdentity.create(EntityType(raw["entity_type"]), raw["canonical_name"],
            raw["identity_basis"], aliases=tuple(raw.get("aliases", ())))
        assert identity.entity_id == raw["entity_id"]
    encoded = json.dumps(proposal, ensure_ascii=False, sort_keys=True, indent=1).encode()
    OUT.mkdir()
    (OUT / "proposal.json").write_bytes(encoded)
    (OUT / "manifest.json").write_text(json.dumps({
        "state": "FROZEN_PROPOSED_RELATIONS_NOT_ACCEPTED",
        "report_sha256": report_sha,
        "proposal_sha256": hashlib.sha256(encoded).hexdigest(),
        "scope": "Only returned proposal; original source/version/hash must be independently checked",
        "source_current_writes": 0,
    }, sort_keys=True), encoding="utf-8")
    print(json.dumps({"state": "FROZEN_PROPOSED_RELATIONS_NOT_ACCEPTED",
                      "entities": len(proposal["entities"])}))


if __name__ == "__main__":
    main()
