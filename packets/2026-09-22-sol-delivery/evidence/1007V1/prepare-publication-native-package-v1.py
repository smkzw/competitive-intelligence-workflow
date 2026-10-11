"""Replay 118 publication atoms into one isolated native source package.

The frozen candidate stays a proposal. This recipe does not accept facts,
issue a publication verdict, adopt science, or move the live current project.
Journal XML does not receive the protocol/SAP current-acquisition witness.
Declared electronic publication days stay published_at only.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any

from ci_workflow.application.fresh_research_ingestion import (
    _validate_references,
    ingest_research_evidence,
)
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.source_research_service import (
    CaptureDateLocators,
    CaptureDatePrecisions,
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    _declared_electronic_publication_day,
    source_capture_from_linked_jats_xml,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.evidence import EvidenceLocator, source_version_identity
from ci_workflow.sources.connectors.linked_jats import inspect_linked_jats_xml
from ci_workflow.storage.source_derivation import (
    SourceTextDerivation,
    extract_locator_quote,
    verify_source_text_derivation,
)

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-publication-native-package-v1"
CANDIDATE = ROOT / ".artifacts/1007-publication-atoms-v1/candidate-v4.json"
DATE_CHECKPOINT = ROOT / ".artifacts/1007-publication-source-dates-v1/checkpoint.json"
SOURCE_LIBRARY = ROOT / ".artifacts/1007-publication-source-dates-v1/source-library"
CANDIDATE_SHA = "6e545087d448f04b49046327ee9628c5c574447337320e254e6a88a3947f1c82"
DATE_LIBRARY_SHA = "248976c2f7edd748230b471a396ff0081faf5f60493d3c49dfa64115e4fad563"
EVIDENCE_LIBRARY_SHA = "82371710ec1c79749b464b5b3ca63233f3837e83160b81bfe01bb3312f3d0621"
BINDINGS_SHA = "b5cde13679a965b3c8f3d001f3cb47786cbdd6f93813229fe521baff6a140b69"
CREATED = datetime.fromisoformat("2026-10-11T13:19:13+08:00")
REPORT_KIND = "B"
_NCT = re.compile(r"NCT[0-9]{8}")
_REGISTRY_IDS = (
    "NCT03181503",
    "NCT04183335",
    "NCT04202679",
    "NCT05052983",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def protected_paths() -> list[Path]:
    evidence = ROOT / ".artifacts/1007-publication-atoms-v1"
    dates = ROOT / ".artifacts/1007-publication-source-dates-v1"
    live = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
    paths = [
        CANDIDATE,
        evidence / "evidence-checkpoint.json",
        evidence / "evidence-library/state/project.sqlite",
        evidence / "evidence-library/state/project.sqlite-wal",
        evidence / "evidence-library/state/project.sqlite-shm",
        DATE_CHECKPOINT,
        dates / "source-library/state/project.sqlite",
        dates / "source-library/state/project.sqlite-wal",
        dates / "source-library/state/project.sqlite-shm",
        ROOT / ".artifacts/1007-publication-binding-candidates-v1/bindings-v2.json",
        live / "project.yaml",
        live / "reports/current.json",
        live / "state/project.sqlite",
        live / "state/project.sqlite-wal",
        live / "state/project.sqlite-shm",
        ROOT / "src/ci_workflow/renderers/portal/report_a.py",
        ROOT / "src/ci_workflow/application/source_research_service.py",
        ROOT / "src/ci_workflow/application/fresh_research_ingestion.py",
        ROOT / "src/ci_workflow/domain/publication.py",
        ROOT / "src/ci_workflow/domain/evidence.py",
        ROOT / "src/ci_workflow/storage/content_store.py",
        ROOT / "src/ci_workflow/storage/snapshot_store.py",
        ROOT / "src/ci_workflow/application/publication_manual_gate.py",
    ]
    return [path for path in paths if path.is_file()]


def hash_map(paths: list[Path]) -> dict[str, str]:
    return {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}


def locator_key(source_id: str, locator: EvidenceLocator) -> str:
    payload = {"locator": locator.model_dump(mode="json"), "source_id": source_id}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def reopen_fact(payload: dict[str, Any]) -> ResearchFact:
    """An existing instance is not authority; reconstruct it twice."""

    first = ResearchFact.model_validate(payload)
    return ResearchFact.model_validate(first.model_dump(mode="json"))


def expected_capture(
    item: dict[str, Any],
    record: dict[str, Any],
    raw: bytes,
) -> SourceCapture:
    """Replay the dated leaf from bytes already in the read-only source library."""

    version = record["source_version"]
    if version["source_version_id"] != item["source_version_id"]:
        raise SystemExit("日期检查点的来源版本与候选 source_set 不一致")
    text = raw.decode("utf-8").strip()
    receipt = SourceTextDerivation.model_validate(version["text_derivation"])
    verify_source_text_derivation(SOURCE_LIBRARY, receipt, text)
    inspection = inspect_linked_jats_xml(
        raw, expected_pmid=item["pmid"], expected_pmcid=item["pmcid"],
        expected_doi=item["doi"],
    )
    declared = _declared_electronic_publication_day(raw)
    if inspection.body_state != "body_present" or declared is None:
        raise SystemExit(f"{item['pmid']} 没有可重放的全文或完整电子出版日")
    day, ordinal = declared
    published_at = datetime.combine(day, time.min, tzinfo=UTC)
    date_locator = EvidenceLocator(
        document_role="original_linked_publication",
        field_path=f"/article/front[1]/article-meta[1]/pub-date[{ordinal}]",
        url=item["locator_url"],
    )
    capture = SourceCapture(
        source_id=item["fact_source_id"],
        route_id="primary-publication",
        source_type="journal_publication",
        title=inspection.title,
        url=item["locator_url"],
        query_or_identifier=f"{inspection.pmcid} / DOI {inspection.doi}",
        language="en",
        access_method="identity_checked_linked_jats_response",
        media_type="text/xml",
        content_text=text,
        text_derivation=receipt,
        acquired_at=datetime.fromisoformat(version["acquired_at"]),
        published_at=published_at,
        effective_at=None,
        first_disclosed_at=None,
        date_precisions=CaptureDatePrecisions(published_at="calendar_day"),
        date_locators=CaptureDateLocators(published_at=date_locator),
        locator=EvidenceLocator(
            document_role="original_linked_publication",
            url=item["locator_url"],
            paragraph=inspection.title,
        ),
    )
    return SourceCapture.model_validate(capture.model_dump(mode="json"))


def remember_quote(
    quotes: dict[str, str],
    collisions: list[dict[str, str]],
    source_id: str,
    locator: EvidenceLocator,
    text: str,
) -> None:
    key = locator_key(source_id, locator)
    previous = quotes.get(key)
    if previous is None:
        quotes[key] = text
        return
    if previous != text:
        collisions.append({"key": key, "left": previous, "right": text})


def validate_quotes(
    facts: tuple[ResearchFact, ...],
    captures: dict[str, SourceCapture],
) -> dict[str, object]:
    quotes: dict[str, str] = {}
    collisions: list[dict[str, str]] = []
    occurrences = 0
    for fact in facts:
        remember_quote(quotes, collisions, fact.source_id, fact.locator, fact.original_text)
        occurrences += 1
        context = fact.source_clause_context
        if context is None:
            continue
        references = list(context.continuations)
        references.extend(
            reference for relation in context.relations for reference in relation.references
        )
        for reference in references:
            remember_quote(
                quotes, collisions, reference.source_id,
                reference.locator, reference.original_text,
            )
            occurrences += 1
    if collisions:
        raise SystemExit(f"同一原文定位出现冲突引文：{len(collisions)}")
    mismatches = []
    for key, expected in quotes.items():
        source_id = json.loads(key)["source_id"]
        locator = EvidenceLocator.model_validate(json.loads(key)["locator"])
        capture = captures[source_id]
        extracted = extract_locator_quote(
            capture.content_text, media_type=capture.media_type, locator=locator,
        )
        if extracted != expected:
            mismatches.append(key)
    if mismatches:
        raise SystemExit(f"原文定位不能重放：{len(mismatches)}")
    return {
        "reference_occurrences": occurrences,
        "unique_fragments": len(quotes),
        "collisions": 0,
        "mismatches": 0,
    }


def study_relationships(facts: tuple[ResearchFact, ...]) -> dict[str, object]:
    issues: list[str] = []
    labels: dict[str, int] = {}
    retained: dict[str, set[str]] = {
        "binary_response_intercurrent_events": set(),
        "cohort_split": set(),
        "nct_assignment": set(),
        "numerical_frame_eligibility": set(),
        "severity_vs_seriousness": set(),
        "use_as_calculated_denominator": set(),
    }
    for fact in facts:
        if any(registry_id in fact.entity_id for registry_id in _REGISTRY_IDS):
            issues.append(f"{fact.fact_id} 把登记号写进了事实实体")
        scope = {} if fact.source_clause_context is None else (
            fact.source_clause_context.scientific_scope
        )
        for field, values in retained.items():
            if field in scope:
                values.add(json.dumps(scope[field], ensure_ascii=False, sort_keys=True))
        context = fact.result_context
        if context is None:
            continue
        labels[context.trial_id] = labels.get(context.trial_id, 0) + 1
        if _NCT.fullmatch(context.trial_id):
            issues.append(f"{fact.fact_id} 的试验身份是登记号而不是来源标签")
    if issues:
        raise SystemExit("；".join(issues[:8]))
    if set(labels) != {"OLYMPIA LTE", "PRIME", "PRIME2"}:
        raise SystemExit("来源试验标签超出已冻结的 PRIME、PRIME2 和 OLYMPIA LTE")
    if retained["nct_assignment"] != {'"unresolved"'}:
        raise SystemExit("NCT 对应关系不再是未解析")
    if retained["use_as_calculated_denominator"] != {"false"}:
        raise SystemExit("候选把分析人数当成了可计算分母")
    return {
        "result_trial_labels": labels,
        "nct_list_order_not_used": True,
        "bindings_v2_not_applied": True,
        "retained_scope_values": {key: sorted(value) for key, value in retained.items()},
    }


def date_state(capture: SourceCapture, cutoff: datetime) -> dict[str, object]:
    published = capture.date_evidence("published_at")
    effective = capture.date_evidence("effective_at")
    first = capture.date_evidence("first_disclosed_at")
    if capture.public_pdf_availability is not None:
        raise SystemExit("隔离包不得授予期刊的当前 PDF 资格")
    if first.state != "not_publicly_disclosed" or effective.state != "not_publicly_disclosed":
        raise SystemExit("首次公开日或生效日被补写")
    if published.state != "reported" or published.precision != "calendar_day":
        raise SystemExit("电子出版日不是已声明的自然日")
    receipt = capture.text_derivation
    if receipt is None:
        raise SystemExit("来源缺少原文派生回执")
    version = source_version_identity(
        capture.source_id,
        receipt.raw_asset.sha256,
        published_at=published,
        effective_at=effective,
        first_disclosed_at=first,
        text_derivation=receipt,
    )
    return {
        "source_id": capture.source_id,
        "source_version_id": version,
        "published_at": published.model_dump(mode="json"),
        "effective_at": effective.state,
        "first_disclosed_at": first.state,
        "historically_available_by_project_cutoff": capture.is_available_by(cutoff),
        "availability_reason": (
            "first_disclosed_at 为 not_publicly_disclosed；"
            "声明电子出版日不构成首次公开或当前获取资格"
        ),
        "protocol_sap_current_witness": False,
    }


def direct_claim(fact: ResearchFact) -> ResearchClaim:
    claim = ResearchClaim(
        claim_id=f"pubclaim:{fact.fact_id.removeprefix('pubfact:')}",
        claim_text=fact.original_text,
        claim_kind="direct_evidence",
        fact_ids=(fact.fact_id,),
    )
    return ResearchClaim.model_validate(claim.model_dump(mode="json"))


def isolated_counts(database: Path) -> dict[str, object]:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        def count(sql: str) -> int:
            return int(connection.execute(sql).fetchone()[0])

        dates = [
            {"role": role, "state": state, "precision": precision}
            for role, state, precision in connection.execute(
                "SELECT date_role, disclosure_state, date_precision "
                "FROM source_date_assertions ORDER BY source_version_id, date_role"
            )
        ]
        reviews = [
            {"state": state, "count": count_value}
            for state, count_value in connection.execute(
                "SELECT review_state, COUNT(*) FROM fact_versions GROUP BY review_state"
            )
        ]
        return {
            "fact_versions": count("SELECT COUNT(*) FROM fact_versions"),
            "claim_versions": count("SELECT COUNT(*) FROM claim_versions"),
            "source_versions": count("SELECT COUNT(*) FROM source_versions"),
            "conflict_sets": count("SELECT COUNT(*) FROM conflict_sets"),
            "current_delivery_state": count("SELECT COUNT(*) FROM current_delivery_state"),
            "user_fact_edit_requests": count("SELECT COUNT(*) FROM user_fact_edit_requests"),
            "fact_review_states": reviews,
            "date_assertions": dates,
        }


def main() -> None:
    if OUT.exists():
        raise SystemExit("隔离包已存在；检查原回执，不要重放摄入")
    if sha256_file(CANDIDATE) != CANDIDATE_SHA:
        raise SystemExit("candidate-v4 摘要与冻结值不一致")
    dates_db = SOURCE_LIBRARY / "state/project.sqlite"
    evidence_db = (
        ROOT / ".artifacts/1007-publication-atoms-v1/evidence-library/state/project.sqlite"
    )
    bindings = ROOT / ".artifacts/1007-publication-binding-candidates-v1/bindings-v2.json"
    if sha256_file(dates_db) != DATE_LIBRARY_SHA or sha256_file(evidence_db) != (
        EVIDENCE_LIBRARY_SHA
    ) or sha256_file(bindings) != BINDINGS_SHA:
        raise SystemExit("来源库、证据库或历史绑定提案摘要已变化")
    candidate = load_json(CANDIDATE)
    checkpoint = load_json(DATE_CHECKPOINT)
    if candidate["state"] != "proposal_not_accepted" or len(candidate["facts"]) != 118:
        raise SystemExit("候选不是未采纳的 118 条事实")
    records = {
        record["source_version"]["source_version_id"]: record
        for record in checkpoint["records"]
        if record.get("source_version")
    }
    before = hash_map(protected_paths())
    captures: dict[str, SourceCapture] = {}
    for item in candidate["source_set"]:
        raw_path = ROOT / item["native_relative_path"]
        raw = raw_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["content_sha256"] or (
            len(raw) != item["byte_size"]
        ):
            raise SystemExit(f"CAS 原件与候选记录不一致：{item['pmid']}")
        capture = expected_capture(item, records[item["source_version_id"]], raw)
        captures[capture.source_id] = capture
    facts = tuple(reopen_fact(item) for item in candidate["facts"])
    if [fact.source_id for fact in facts].count("pubmed-record-37142763") != 51:
        raise SystemExit("dupilumab 来源事实数不是 51")
    if [fact.source_id for fact in facts].count("pubmed-record-41405008") != 67:
        raise SystemExit("nemolizumab 来源事实数不是 67")
    contract = create_project_contract(
        indication="结节性痒疹",
        reports=["A", "B"],
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff="2026-10-07",
        created_at=CREATED,
    )
    quote_audit = validate_quotes(facts, captures)
    relationships = study_relationships(facts)
    states = [date_state(capture, contract.data_cutoff) for capture in captures.values()]
    if any(item["historically_available_by_project_cutoff"] for item in states):
        raise SystemExit("未知首次公开日仍被项目截止日授予历史资格")
    expected_versions = {item["source_version_id"] for item in candidate["source_set"]}
    if {item["source_version_id"] for item in states} != expected_versions:
        raise SystemExit("重建来源版本与冻结日期版本不一致")
    claims = tuple(direct_claim(fact) for fact in facts)
    _validate_references(tuple(captures.values()), facts, claims)
    missing_bodies = [
        {"pmid": record["pmid"], "state": record["state"]}
        for record in checkpoint["records"]
        if record.get("state") == "required_body_missing"
    ]
    OUT.mkdir()
    project = create_project_workspace(OUT / "project", contract)
    isolated: dict[str, SourceCapture] = {}
    for item in candidate["source_set"]:
        raw = (ROOT / item["native_relative_path"]).read_bytes()
        _inspection, bridge = source_capture_from_linked_jats_xml(
            project,
            raw,
            expected_pmid=item["pmid"],
            expected_pmcid=item["pmcid"],
            expected_doi=item["doi"],
            url=item["locator_url"],
            acquired_at=captures[item["fact_source_id"]].acquired_at,
            media_type="text/xml",
            use_declared_publication_date=True,
        )
        if bridge is None or bridge.source_id != item["native_capture_source_id"]:
            raise SystemExit(f"{item['pmid']} 在隔离项目中没有匹配的全文捕获")
        if bridge.public_pdf_availability is not None:
            raise SystemExit("期刊 XML 不得带上方案/SAP 当前获取见证")
        payload = bridge.model_dump(mode="json")
        payload["source_id"] = item["fact_source_id"]
        capture = SourceCapture.model_validate(payload)
        capture = SourceCapture.model_validate(capture.model_dump(mode="json"))
        if capture.model_dump(mode="json") != captures[capture.source_id].model_dump(mode="json"):
            raise SystemExit("隔离项目来源捕获与只读原件回放不一致")
        if capture.text_derivation is None:
            raise SystemExit("隔离来源缺少原文派生回执")
        verify_source_text_derivation(project, capture.text_derivation, capture.content_text)
        isolated[capture.source_id] = capture
    package = {
        "schema_version": "ci-1007-publication-native-package-v1",
        "state": "isolated_candidate_not_accepted",
        "scientific_adoption": False,
        "current_promoted": False,
        "candidate_sha256": CANDIDATE_SHA,
        "project_id": contract.project_id,
        "contract_version": contract.contract_version,
        "data_cutoff": contract.data_cutoff.isoformat(),
        "report_kind_slot": REPORT_KIND,
        "report_kind_meaning": (
            "ingest_research_evidence 的技术槽位；row_ref 仍是来源路径，"
            "没有生成 A/B/C 消费载荷"
        ),
        "sources": [item.model_dump(mode="json") for item in isolated.values()],
        "facts": [item.model_dump(mode="json") for item in facts],
        "claims": [item.model_dump(mode="json") for item in claims],
        "claim_role": "direct_quote_carrier_not_a_new_conclusion",
        "missing_or_conflicting_scopes": candidate["missing_or_conflicting_scopes"],
        "missing_bodies_not_acquired": missing_bodies,
        "date_states": states,
        "study_relationships": relationships,
    }
    write_json(OUT / "source-package.json", package)
    lineage = ingest_research_evidence(
        project_root=project,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        report_kind=REPORT_KIND,
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=CANDIDATE_SHA,
        created_at=CREATED,
        sources=tuple(isolated.values()),
        route_attempts=(),
        facts=facts,
        claims=claims,
        request_id="ci-1007-publication-native-package-v1",
    )
    after = hash_map(protected_paths())
    if after != before:
        changed = sorted(set(before) ^ set(after) | {
            key for key in before if before[key] != after.get(key)
        })
        write_json(OUT / "protected-hash-drift.json", {"changed": changed})
        raise SystemExit("受保护的候选、原件、现行项目或生产字典发生变化")
    counts = isolated_counts(project / "state/project.sqlite")
    if counts["fact_versions"] != 118 or counts["claim_versions"] != 118:
        raise SystemExit("隔离库事实或声明数量不是 118")
    if counts["current_delivery_state"] or counts["conflict_sets"] or (
        counts["user_fact_edit_requests"]
    ):
        raise SystemExit("隔离摄入写入了现行、冲突或用户编辑")
    if counts["fact_review_states"] != [{"count": 118, "state": "candidate"}]:
        raise SystemExit("事实复核状态不是 candidate")
    manifest = {
        "state": "ISOLATED_NATIVE_INGESTED_NOT_ACCEPTED_NOT_CURRENT",
        "technical_status": "PASS",
        "scientific_adoption": False,
        "candidate_sha256": CANDIDATE_SHA,
        "facts": 118,
        "claims": 118,
        "sources": 2,
        "quote_audit": quote_audit,
        "date_states": states,
        "study_relationships": relationships,
        "missing_or_conflicting_scope_ids": [
            {"scope_id": item["scope_id"], "status": item["status"]}
            for item in candidate["missing_or_conflicting_scopes"]
        ],
        "missing_bodies_not_acquired": missing_bodies,
        "conflicts": [],
        "database_counts": counts,
        "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "source_version_ids": list(lineage.source_version_ids),
        "protected_hashes_unchanged": True,
        "protected_hashes": before,
        "live_current_mutated": False,
        "bindings_v2_sha256": BINDINGS_SHA,
        "bindings_v2_used_for_assignment": False,
    }
    write_json(OUT / "manifest.json", manifest)
    print(json.dumps({
        "state": manifest["state"],
        "snapshot": lineage.evidence_snapshot.snapshot_id,
        "facts": 118,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
