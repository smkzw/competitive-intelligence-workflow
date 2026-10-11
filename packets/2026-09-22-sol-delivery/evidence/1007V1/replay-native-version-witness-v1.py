"""Read-only exact native metadata replay; never qualify or adopt a fact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.sources.connectors.linked_jats import _article_element, _paragraph_text
from ci_workflow.storage.source_derivation import SourceDerivationError, extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
PACKET = ROOT / ".artifacts/1007-publication-native-package-v1/source-package.json"
PACKET_HASH = "6909f03ab9f1c7b08b264ba31078a0dab62849937f5da059f99a72c6ab880e8e"
OUT = ROOT / ".artifacts/1007-native-version-replay-v1"
META = "/article/front[1]/article-meta[1]"


def main() -> None:
    raw = PACKET.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PACKET_HASH
    assert not OUT.exists(), "Do not overwrite previous evidence"
    results = []
    for source in json.loads(raw)["sources"]:
        xml = source["content_text"]
        meta = _article_element(ET.fromstring(xml)).find("front/article-meta")
        assert meta is not None
        paths: list[tuple[str, ET.Element]] = []
        rejected = []
        for index, node in enumerate(meta.findall("article-id"), 1):
            path = f"{META}/article-id[{index}]"
            if node.get("pub-id-type") in {"doi", "pmcid", "pmcid-ver", "pmid"}:
                paths.append((path, node))
            else:
                rejected.append(path)
        for index, node in enumerate(meta.findall("article-version"), 1):
            if node.get("article-version-type") == "pmc-version":
                paths.append((f"{META}/article-version[{index}]", node))
        for index, node in enumerate(meta.findall("permissions/copyright-statement"), 1):
            paths.append((f"{META}/permissions[1]/copyright-statement[{index}]", node))
        for index, event in enumerate(meta.findall("pub-history/event"), 1):
            if event.get("event-type") in {"pmc-release", "pmc-live", "pmc-last-change"}:
                node = event.find("date")
                assert node is not None
                paths.append((f"{META}/pub-history[1]/event[{index}]/date[1]", node))
        observed = []
        for path, node in paths:
            value = extract_locator_quote(xml, media_type=source["media_type"],
                                          locator=EvidenceLocator(
                                              document_role="original_linked_publication",
                                              field_path=path))
            assert value == _paragraph_text(node)
            observed.append({"locator": path, "text": value})
        for path in rejected:
            try:
                extract_locator_quote(xml, media_type=source["media_type"],
                                      locator=EvidenceLocator(
                                          document_role="original_linked_publication",
                                          field_path=path))
            except SourceDerivationError:
                pass
            else:
                raise AssertionError("Undeclared native identity accepted")
        results.append({"source_id": source["source_id"],
                        "source_sha256": hashlib.sha256(xml.encode()).hexdigest(),
                        "exact_witnesses": observed, "rejected_identity_paths": rejected})
    assert hashlib.sha256(PACKET.read_bytes()).hexdigest() == PACKET_HASH
    receipt = {"state": "EXACT_NATIVE_REPLAY_NOT_HISTORICAL_FACT_ACCEPTANCE",
               "packet_sha256": PACKET_HASH, "sources": results,
               "source_current_fact_writes": 0}
    OUT.mkdir()
    with (OUT / "actual.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=1)
    print(json.dumps({"sources": len(results),
                      "witnesses": sum(len(item["exact_witnesses"]) for item in results),
                      "state": receipt["state"]}))


if __name__ == "__main__":
    main()
