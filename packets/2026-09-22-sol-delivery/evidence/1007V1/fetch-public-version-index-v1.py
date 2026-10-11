"""Capture two official PMC version identities, not facts or historical acceptance."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-pmc-version-index-v1"
URL = ("https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
       "?ids=PMC10202800,PMC13308661&versions=yes&showaiid=yes&format=json"
       "&tool=competitive-intelligence-workflow")


def main() -> None:
    assert not OUT.exists(), "No previous response or acquisition clock may be replaced"
    OUT.mkdir()
    started = datetime.now(UTC)
    request = Request(URL, headers={"User-Agent": "competitive-intelligence-workflow/1007V1"})
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read(1024 * 1024 + 1)
            assert len(raw) <= 1024 * 1024
            ended = datetime.now(UTC)
            status, final_url = response.status, response.url
            media_type = response.headers.get("Content-Type")
        with (OUT / "response.bin").open("xb") as stream:
            stream.write(raw)
        payload = json.loads(raw)
        assert payload.get("status") == "ok" and len(payload["records"]) == 2
        assert {r["pmcid"] for r in payload["records"]} == {"PMC10202800", "PMC13308661"}
        receipt = {"state": "OFFICIAL_VERSION_INDEX_CAPTURE_NOT_FACT_ACCEPTANCE",
                   "request_url": URL, "response_url": final_url, "status": status,
                   "media_type": media_type, "request_started_at": started.isoformat(),
                   "response_completed_at": ended.isoformat(),
                   "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                   "records": payload["records"], "source_current_fact_writes": 0}
        with (OUT / "actual.json").open("x") as stream:
            json.dump(receipt, stream, sort_keys=True, indent=1)
        print(json.dumps(receipt))
    except Exception as error:
        with (OUT / "failure.json").open("x") as stream:
            json.dump({"state": "FAILED_NOT_ACCEPTED", "error": str(error),
                       "request_started_at": started.isoformat(), "current_writes": 0}, stream)
        raise


if __name__ == "__main__":
    main()
