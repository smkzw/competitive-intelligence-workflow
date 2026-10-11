"""One immutable source-context repair; no new numeric extraction or adoption."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.source_clause_context import SourceClauseReference
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-publication-context-v5"
INPUT = ROOT / ".artifacts/1007-publication-atoms-v1/candidate-v4.json"
BASE = Path(__file__).with_name("prepare-publication-native-package-v1.py")
SPEC = importlib.util.spec_from_file_location("native_publication_checks", BASE)
assert SPEC is not None and SPEC.loader is not None
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)
N = "pubmed-record-41405008"
D = "pubmed-record-37142763"
FACT = "pubfact:PMC13308661:/article/front[1]/article-meta[1]/abstract[1]/sec[4]/p[1]"
CONTEXT = (
    ("/article/front[1]/article-meta[1]/abstract[1]/sec[3]/p[1]",
     "摘要疗效观察病例与救援/缺失规则"),
    ("/article/body[1]/sec[2]/sec[3]/p[3]", "主要疗效分析：观察病例，不插补，无论救援"),
    ("/article/body[1]/sec[2]/sec[2]/sec[2]/p[1]", "疗效终点定义、导入期基线及100周范围"),
    ("/article/body[1]/sec[2]/sec[3]/p[4]", "敏感性NRI分析；不套用至上述OC结果"),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Read original candidate and proof; no replay/overwrite"
    assert sha(INPUT) == native.CANDIDATE_SHA
    old = json.loads(INPUT.read_bytes())
    value = copy.deepcopy(old)
    sources = {s["fact_source_id"]: s for s in value["source_set"]}
    text = {}
    for sid, source in sources.items():
        path = ROOT / source["native_relative_path"]
        assert sha(path) == source["content_sha256"]
        text[sid] = path.read_text()

    def quote(sid: str, path: str) -> str:
        return extract_locator_quote(
            text[sid], media_type="text/xml", locator=EvidenceLocator(
                document_role="original_linked_publication", field_path=path,
                url=sources[sid]["locator_url"],
            ),
        )

    fact = next(f for f in value["facts"] if f["fact_id"] == FACT)
    ctx = fact["source_clause_context"]
    existing = {r["locator"]["field_path"] for r in ctx["continuations"]}
    assert not ({p for p, _label in CONTEXT} <= existing), "Original RED no longer applies"
    for path, label in CONTEXT:
        if path not in existing:
            ctx["continuations"].append(SourceClauseReference(
                reference_id=N + ":" + path, source_id=N, label_zh=label,
                locator=EvidenceLocator(document_role="original_linked_publication",
                                        field_path=path, url=sources[N]["locator_url"]),
                original_text=quote(N, path),
            ).model_dump(mode="json"))
    ctx["label_zh"] = "摘要疗效与安全性结果原文"
    ctx["scope_note_zh"] = (
        "本段同时含疗效与安全性原文。100周疗效按可评价观察病例，不作缺失插补，"
        "无论救援用药均呈现；变化终点以导入期基线为锚点。敏感性NRI不套用于"
        "上述OC结果，终点访视分母未查明，不借总体安全N508补写，不授予数值共轴。"
    )
    ctx["scientific_scope"].update(
        narrative_domains=["efficacy", "safety"],
        efficacy_analysis="observed cases at week100, evaluable per endpoint",
        missing_efficacy_data="no imputation",
        rescue_therapy="observed data regardless of rescue therapy",
        change_endpoint_reference="lead-in baseline",
        sensitivity_nri_not_applied_to_oc=True,
        efficacy_denominator_unknown=True,
        safety_total_not_efficacy_denominator=True,
    )
    corrections = "/article/front[1]/article-meta[1]/permissions[1]/copyright-statement[1]"
    # Version metadata is not a clinical atomic locator. Do not expand the
    # production paragraph/cell parser or masquerade it as a numeric fact.
    articles = ET.fromstring(text[D]).findall("./article")
    assert len(articles) == 1  # This frozen original uses a PMC articleset wrapper.
    metadata = articles[0].findall("./front/article-meta/permissions/copyright-statement")
    assert len(metadata) == 1
    copyright_quote = " ".join("".join(metadata[0].itertext()).split())
    assert "corrected publication 2023" in copyright_quote
    value["missing_or_conflicting_scopes"].append({
        "scope_id": "dup-corrected-publication-version-scope-unresolved", "source_id": D,
        "status": "version_update_requires_source_check",
        "description_zh": ("原件标注corrected publication2023，具体更正日期/范围未闭合；"
                           "不推断所涉数字错误或把电子发表日当更正版可得日期。"),
        "paths": [corrections], "quotes": [copyright_quote],
        "evidence_method": "exact single XML metadata node; not a clinical atomic fragment",
        "raw_source_sha256": sources[D]["content_sha256"],
    })
    table = "/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[9]"
    paths = [table + f"/td[{col}]" for col in (2, 4, 5, 6)]
    values = [quote(N, path) for path in paths]
    assert values == ["44 (9)", "30 (6)", "10 (2)", "3 (1)"]
    value["missing_or_conflicting_scopes"].append({
        "scope_id": "nem-discontinuation-44-versus-timebands-43", "source_id": N,
        "status": "source_internal_reconciliation_unresolved",
        "description_zh": ("原表TEAE退出总体44，三个时间带30+10+3=43；保留原数，不补人，"
                           "不把时间带当作已证明完备互斥处置分解。"),
        "paths": paths, "quotes": values,
    })
    changed = []
    for prior, revised in zip(old["facts"], value["facts"], strict=True):
        assert {k: v for k, v in prior.items() if k != "source_clause_context"} == {
            k: v for k, v in revised.items() if k != "source_clause_context"
        }
        if prior != revised:
            changed.append(prior["fact_id"])
    assert changed == [FACT] and len(value["facts"]) == 118
    package = json.loads((native.OUT / "source-package.json").read_bytes())
    captures = {s["source_id"]: native.SourceCapture.model_validate(s)
                for s in package["sources"]}
    facts = tuple(native.reopen_fact(f) for f in value["facts"])
    audit = native.validate_quotes(facts, captures)
    assert {p for p, _label in CONTEXT} <= {
        r["locator"]["field_path"] for r in ctx["continuations"]
    }
    assert sha(INPUT) == native.CANDIDATE_SHA
    value["context_v5_closure"] = {
        "prior_candidate_sha256": native.CANDIDATE_SHA, "changed_fact_ids": changed,
        "raw_values_and_fact_ids_unchanged": True, "new_numeric_extraction": False,
        "new_scientific_acceptance": False, "current_mutated": False,
        "date_policy": "unchanged; awaiting user decision and actual version evidence",
    }
    OUT.mkdir()
    with (OUT / "candidate-v5.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
    with (OUT / "verified.json").open("x", encoding="utf-8") as stream:
        json.dump({"state": "CONTEXT_REPAIRED_HOLDING_NOT_ACCEPTED_OR_CURRENT",
                   "candidate_sha256": sha(OUT / "candidate-v5.json"), "quote_audit": audit,
                   "recipe_sha256": sha(Path(__file__)), "changed_fact_ids": changed,
                   "raw_values_and_ids_unchanged": 118, "other_facts_unchanged": 117,
                   "scopes": len(value["missing_or_conflicting_scopes"]),
                   "new_native_ingestion": False}, stream, ensure_ascii=False, indent=1)
    print(json.dumps({"state": "HOLDING_V5_NOT_ACCEPTED", "facts": 118, "audit": audit}))


if __name__ == "__main__":
    main()
