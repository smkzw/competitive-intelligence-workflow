"""Bounded public PMC objects; preserve failed v1 and every actual response receipt."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-pmc-object-witness-v2"
HOST = "pmc-oa-opendata.s3.amazonaws.com"
BUCKET = "pmc-oa-opendata"
IDENTITIES = {"PMC10202800": "10.1038/s41591-023-02320-9",
              "PMC13308661": "10.1111/jdv.70266"}
V1_METADATA = ROOT / ".artifacts/1007-pmc-object-witness-v1/PMC10202800.1.json"


def allowed_https(url: str) -> None:
    parsed = urlsplit(url)
    assert parsed.scheme == "https" and parsed.netloc == HOST, "Unapproved object host"
    assert parsed.username is None and parsed.password is None


class SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def write_json(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=1)


def fetch(url: str, file: str, limit: int) -> tuple[bytes, dict[str, object]]:
    allowed_https(url)
    started = datetime.now(UTC)
    request = Request(url, headers={"User-Agent": "competitive-intelligence-workflow/1007V1"})
    with build_opener(SameHostRedirect()).open(request, timeout=45) as response:
        allowed_https(response.url)
        raw = response.read(limit + 1)
        assert len(raw) <= limit and raw, "Empty or oversized object"
        ended = datetime.now(UTC)
        headers = {key: response.headers.get(key) for key in
                   ("Content-Type", "ETag", "Last-Modified", "Content-Length", "Date")}
        result = {"url": url, "response_url": response.url, "status": response.status,
                  "request_started_at": started.isoformat(),
                  "response_completed_at": ended.isoformat(), "headers": headers,
                  "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                  "relative_path": file}
    with (OUT / file).open("xb") as stream:
        stream.write(raw)
    write_json(file + ".receipt.json", result)
    return raw, result


def object_url(source: str, pmcid: str) -> tuple[str, str]:
    parsed = urlsplit(source)
    assert parsed.scheme == "s3" and parsed.netloc == BUCKET, "Unapproved S3 bucket"
    assert parsed.path == f"/{pmcid}.1/{pmcid}.1.xml" and not parsed.fragment
    query = parse_qs(parsed.query)
    assert set(query) == {"md5"} and len(query["md5"]) == 1
    md5 = query["md5"][0]
    assert len(md5) == 32 and all(c in "0123456789abcdef" for c in md5)
    return urlunsplit(("https", HOST, parsed.path, parsed.query, "")), md5


def main() -> None:
    assert hashlib.sha256(V1_METADATA.read_bytes()).hexdigest() == (
        "d541870dd80996e26a034c2676bae9fcca2c2f6b723728d1cfdbcf3d197ea002"
    )
    assert not OUT.exists(), "Never overwrite clocks, failures or source bytes"
    OUT.mkdir()
    write_json("recovery.json", {
        "previous_state": "FAILED_NOT_ACCEPTED_S3_URL_INSTRUMENT_ASSERTION",
        "previous_metadata_sha256": hashlib.sha256(V1_METADATA.read_bytes()).hexdigest(),
        "reason_for_new_capture": "v1 retained metadata bytes but lost its HTTP receipt; "
        "v2 captures new clocks/headers and never reconstructs old retrieval timestamps",
        "conversion": "Only fixed public PMC bucket and exact article XML path",
    })
    records = []
    try:
        for pmcid, doi in IDENTITIES.items():
            metadata, record = fetch(f"https://{HOST}/metadata/{pmcid}.1.json",
                                     f"{pmcid}.1.json", 1024 * 1024)
            parsed = json.loads(metadata)
            assert parsed["pmcid"] == pmcid and str(parsed["version"]) == "1"
            assert parsed["doi"] == doi
            xml_url, md5 = object_url(parsed["xml_url"], pmcid)
            original, xml_record = fetch(xml_url, f"{pmcid}.1.xml", 8 * 1024 * 1024)
            assert hashlib.md5(original, usedforsecurity=False).hexdigest() == md5
            records.append({"pmcid": pmcid, "doi": doi, "metadata": record,
                            "xml": xml_record, "metadata_xml_md5": md5,
                            "license_code": parsed["license_code"],
                            "is_manuscript": parsed["is_manuscript"],
                            "is_retracted": parsed["is_retracted"]})
        receipt = {"state": "PUBLIC_OBJECT_WITNESSES_NOT_FACT_ACCEPTANCE",
                   "documentation": "https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/",
                   "technical_documentation": f"https://{HOST}/README.txt",
                   "records": records, "source_current_fact_writes": 0}
        write_json("actual.json", receipt)
        print(json.dumps({"state": receipt["state"], "records": [
            {"pmcid": item["pmcid"], "metadata_headers": item["metadata"]["headers"],
             "xml_headers": item["xml"]["headers"], "xml_sha256": item["xml"]["sha256"]}
            for item in records]}))
    except Exception as error:
        write_json("failure.json", {"state": "FAILED_NOT_ACCEPTED",
                                    "error_type": type(error).__name__, "error": str(error),
                                    "completed_records": records, "current_writes": 0})
        raise


if __name__ == "__main__":
    main()
