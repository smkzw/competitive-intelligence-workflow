"""Replay captured CT.gov sources into an isolated C dataset (component replay only).

Read-only on captured data; writes only to a new output directory. Uses the
production parser, DB/CAS and ordinary C renderer. Not a pipeline run or M1 acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from ciw2.render import design as design_module
from ciw2.render import portal as portal_module
from ciw2.render.portal import data_c, render_report
from ciw2.sources import ctgov as ctgov_module
from ciw2.sources.ctgov import _trial_attrs, design_facts, parse_study
from ciw2.store.cas import CAS
from ciw2.store.db import DB, new_id

RECEIPT = "ciw2.source-replay.receipt.v2"
KIND = "ctgov"
DRUG_TYPES = {"DRUG", "BIOLOGICAL"}
PHASES = {"PHASE2", "PHASE3"}
PLACEBO = {"placebo", "安慰剂"}
ROUTE = "replay:ctgov:captured"
MISSING = object()
HEX = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")
RULE = (
    "Latest captured version per literal NCT id (fetched_at, source_id; lower study index on an exact tie); "
    "studyType == INTERVENTIONAL; phases explicitly contain PHASE2 or PHASE3; at least one intervention typed "
    "DRUG or BIOLOGICAL with a non-empty literal name other than exact Placebo/安慰剂. No Top-N; no MAH, "
    "company, target or name translation; no arm-role inference; whole combination names preserved."
)


class ReplayError(RuntimeError):
    pass
def _now():
    return datetime.now(UTC).isoformat(timespec="seconds")
def _sha(data):
    return hashlib.sha256(data).hexdigest()
def _tokens(path):
    if not isinstance(path, str) or not path.startswith("$"):
        raise ReplayError(f"invalid JSON locator: {path!r}")
    found, position = [], 1
    while position < len(path):
        match = TOKEN.match(path, position)
        if match is None:
            raise ReplayError(f"invalid JSON locator: {path!r}")
        found.append(match.group(1) if match.group(1) is not None else int(match.group(2)))
        position = match.end()
    return found
def _resolve(document, path):
    current = document
    for token in _tokens(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return MISSING
            current = current[token]
        elif not isinstance(current, dict) or token not in current:
            return MISSING
        else:
            current = current[token]
    return current
def _abs(container, relative):
    return f"{container}.protocolSection.{relative}" if relative else container
def _read(source_dir, project_id):
    database = source_dir / "ciw2.sqlite3"
    if not database.is_file():
        raise ReplayError(f"source database not found: {database}")
    connection = None
    try:
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        project = connection.execute(
            "SELECT id, indication, focus, cutoff_date FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        rows = [dict(row) for row in connection.execute(
            "SELECT id,kind,url,title,digest,text_digest,published_date,fetched_at,meta FROM sources "
            "WHERE project_id=? ORDER BY fetched_at,id", (project_id,))]
        kinds = {row["kind"]: row["n"] for row in connection.execute(
            "SELECT kind, count(*) AS n FROM sources WHERE project_id=? GROUP BY kind", (project_id,))}
        connection.execute("ROLLBACK")
    except sqlite3.Error as exc:
        raise ReplayError(f"cannot read captured sources from {database}: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    if project is None:
        raise ReplayError(f"source project not found: {project_id}")
    sources = [row for row in rows if row["kind"] == KIND]
    if not sources:
        raise ReplayError(f"source project {project_id} has no captured {KIND} sources")
    return {"database": database, "project": dict(project), "sources": sources, "all": rows,
            "kinds": kinds, "max_fetched_at": max(row["fetched_at"] for row in sources)}
def _load(source_dir, digest):
    if not isinstance(digest, str) or not HEX.fullmatch(digest):
        return None, "invalid_digest"
    path = source_dir / "cas" / digest[:2] / digest
    if not path.is_file():
        return None, "missing_object"
    data = path.read_bytes()
    return (data, None) if _sha(data) == digest else (None, "digest_mismatch")
def _shape(document):
    if isinstance(document, dict) and isinstance(document.get("studies"), list):
        return "ctgov_studies_array", [(f"$.studies[{i}]", i, study)
                                       for i, study in enumerate(document["studies"])]
    if isinstance(document, dict) and isinstance(document.get("protocolSection"), dict):
        return "ctgov_single_study", [("$", 0, document)]
    return None, []
def _scan(snapshot, source_dir):
    latest = {}
    count = seen = no_nct = 0
    failures, unreadable = [], []
    for row in snapshot["sources"]:
        raw, error = _load(source_dir, row["digest"])
        if error:
            failures.append({"source_id": row["id"], "url": row["url"], "object": "raw", "reason": error})
            continue
        if row["text_digest"] and row["text_digest"] != row["digest"]:
            _, error = _load(source_dir, row["text_digest"])
            if error:
                failures.append({"source_id": row["id"], "url": row["url"], "object": "text", "reason": error})
                continue
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            unreadable.append({"source_id": row["id"], "url": row["url"], "reason": str(exc)})
            continue
        shape, entries = _shape(document)
        if shape is None:
            unreadable.append({"source_id": row["id"], "url": row["url"], "reason": "unsupported_container"})
            continue
        for locator, index, study in entries:
            seen += 1
            nct = _resolve(study, "$.protocolSection.identificationModule.nctId") if isinstance(study, dict) else MISSING
            if not isinstance(nct, str) or not nct.strip():
                no_nct += 1
                continue
            count += 1
            candidate = {"nct": nct, "source_id": row["id"], "fetched_at": row["fetched_at"],
                         "locator": locator, "index": index, "shape": shape}
            current = latest.get(nct)
            if current is None or _key(candidate) > _key(current):
                latest[nct] = candidate
    return {"latest": latest, "count": count, "seen": seen, "no_nct": no_nct,
            "failures": failures, "unreadable": unreadable}
def _key(candidate):
    return (candidate["fetched_at"], candidate["source_id"], -candidate["index"])
def _qualifies(item):
    if not isinstance(item, dict) or item.get("type") not in DRUG_TYPES:
        return False
    name = (item.get("name") or "").strip()
    return bool(name) and name.casefold() not in PLACEBO
def _classify(study):
    protocol = study.get("protocolSection") if isinstance(study, dict) else None
    if not isinstance(protocol, dict):
        return "missing_protocol_section", None
    design = protocol.get("designModule") if isinstance(protocol.get("designModule"), dict) else {}
    study_type = design.get("studyType")
    if study_type != "INTERVENTIONAL":
        return "study_type_not_interventional", str(study_type)
    phases = design.get("phases") if isinstance(design.get("phases"), list) else []
    if not set(phases) & PHASES:
        return "phase_not_2_or_3", "|".join(map(str, phases)) or "NONE"
    module = protocol.get("armsInterventionsModule")
    items = module.get("interventions") if isinstance(module, dict) else []
    if not any(_qualifies(item) for item in (items if isinstance(items, list) else [])):
        return "no_qualifying_drug_or_biological_intervention", None
    return None, None
def _drugs(parsed):
    names = []
    for item in parsed.get("interventions") or []:
        if _qualifies(item):
            name = (item.get("name") or "").strip()
            if name not in names:
                names.append(name)
    return names
def _exact(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact(a, b) for a, b in zip(left, right))
    return left == right
def _value_ok(fact, source):
    value, present = fact.get("value"), source is not MISSING
    if value is None:
        if not present or source is None:
            outcome, reason = "unknown", "source_value_missing" if not present else "source_value_null"
        else:
            outcome, reason = "mismatch", "fact_missing_source_present"
    elif not present:
        outcome, reason = "mismatch", "source_value_missing"
    elif source is None:
        outcome, reason = "mismatch", "source_value_null"
    elif type(source) is not type(value):
        outcome, reason = "mismatch", "type_mismatch"
    elif source != value:
        outcome, reason = "mismatch", "value_mismatch"
    else:
        outcome, reason = "match", None
    if fact.get("status") != ("unknown" if value is None else "verified"):
        outcome, reason = "mismatch", "status_mismatch"
    return outcome, reason, None if not present else source
def _endpoint_ok(fact, source):
    if source is MISSING or not isinstance(source, dict):
        return "mismatch", "source_outcome_not_object", None
    expected = {"measure": source.get("measure"), "time_frame": source.get("timeFrame"),
                "description": source.get("description")}
    value = fact.get("value")
    if not isinstance(value, dict):
        return "mismatch", "fact_not_object", expected
    if set(value) != set(expected):
        return "mismatch", "shape_mismatch", expected
    if not _exact(value, expected):
        return "mismatch", "value_or_type_mismatch", expected
    return "match", None, expected
def verify_facts(document, container_locator, nct, facts):
    """Directly traverse the original study JSON; compare identity and exact type/value."""
    study = _resolve(document, container_locator)
    identity = isinstance(study, dict)
    source_nct = _resolve(study, "$.protocolSection.identificationModule.nctId") if identity else None
    identity = bool(identity and source_nct == nct)
    fields = defaultdict(lambda: {"checked": 0, "match": 0, "mismatch": 0, "unknown": 0})
    failures = []
    checked = matches = mismatches = unknowns = 0
    for fact in facts:
        if fact.get("tier") != "critical":
            continue
        path = fact["context"]["json_path"]
        if not identity:
            outcome, reason, source_value = "mismatch", "source_identity_mismatch", None
        else:
            source = _resolve(document, path)
            if fact["field"] == "design.sample_size":
                outcome, reason, source_value = _value_ok(fact, source)
            elif fact["field"] == "design.primary_endpoint":
                outcome, reason, source_value = _endpoint_ok(fact, source)
            else:
                outcome, reason, source_value = "mismatch", "no_direct_verifier", None
        if outcome == "mismatch":
            fact["status"] = "unverified"
            failures.append({"fact_id": fact.get("id"), "field": fact["field"], "nct": nct,
                             "json_path": path, "reason": reason, "source_value": source_value})
        fields[fact["field"]]["checked"] += 1
        fields[fact["field"]][outcome] += 1
        checked += 1
        matches += outcome == "match"
        mismatches += outcome == "mismatch"
        unknowns += outcome == "unknown"
    return {"checked": checked, "match": matches, "mismatch": mismatches, "unknown": unknowns,
            "fail": mismatches, "fields": dict(fields), "failures": failures,
            "identity": {"checked": 1, "match": int(identity), "mismatch": int(not identity),
                         "source_nct": None if source_nct is MISSING else source_nct}}
def _copy(cas, data, digest):
    if _sha(data) != digest or cas.put(data) != digest or cas.get(digest) != data:
        raise ReplayError(f"CAS copy is not byte-exact: {digest}")
def _register(db, project_id, source_project_id, source, included, shape, cas, source_dir, copied):
    meta = {}
    try:
        parsed_meta = json.loads(source["meta"] or "{}")
        if isinstance(parsed_meta, dict):
            meta = parsed_meta
    except (TypeError, json.JSONDecodeError):
        pass
    locators = sorted({candidate["locator"] for candidate, _ in included})
    meta.update({"capture_kind": shape, "per_nct_fetch": shape == "ctgov_single_study",
                 "replay_of_source_id": source["id"], "replay_of_project_id": source_project_id,
                 "captured_at": source["fetched_at"], "replayed_at": _now(),
                 "replay_tool": RECEIPT, "container_locators": locators})
    sid = db.add_source(project_id, KIND, source["url"], source["digest"], title=source["title"],
                        text_digest=source["text_digest"], published_date=source["published_date"], meta=meta)
    db.execute("UPDATE sources SET fetched_at=?, published_date=? WHERE id=?",
               (source["fetched_at"], source["published_date"], sid))
    raw, error = _load(source_dir, source["digest"])
    if error:
        raise ReplayError(f"captured source {source['id']} changed during replay: {error}")
    _copy(cas, raw, source["digest"])
    text = None
    if source["text_digest"]:
        if source["text_digest"] == source["digest"]:
            text = raw
        else:
            text, error = _load(source_dir, source["text_digest"])
            if error:
                raise ReplayError(f"captured text {source['id']} changed during replay: {error}")
        _copy(cas, text, source["text_digest"])
    copied.append({"captured_source_id": source["id"], "isolated_source_id": sid, "url": source["url"],
                   "fetched_at": source["fetched_at"], "published_date": source["published_date"],
                   "raw_sha256": source["digest"], "text_sha256": source["text_digest"],
                   "raw_bytes": len(raw), "text_bytes": len(text) if text is not None else 0,
                   "capture_kind": shape, "per_nct_fetch": shape == "ctgov_single_study",
                   "container_locators": locators})
    return sid
def _limits(parsed):
    nct, out = parsed["nct"], []
    if parsed["enrollment"] is None:
        out.append(("missing_enrollment", nct, "enrollmentInfo.count absent/null"))
    if parsed["enrollment_type"] is None:
        out.append(("missing_enrollment_type", nct, "enrollmentInfo.type absent/null"))
    primary = parsed["primary_outcomes"] or []
    if not primary:
        out.append(("no_primary_outcomes", nct, "primaryOutcomes empty"))
    for index, outcome in enumerate(primary):
        if not outcome.get("measure"):
            out.append(("primary_endpoint_measure_missing", nct, f"primaryOutcomes[{index}]"))
        if outcome.get("timeFrame") is None:
            out.append(("primary_endpoint_time_frame_missing", nct, f"primaryOutcomes[{index}]"))
    if parsed["phase"] == "unknown":
        out.append(("phase_mapping_unknown", nct, "|".join(parsed["phases"] or [])))
    return out
def _ingest(db, project_id, isolated_source_id, candidate, study, document):
    parsed = parse_study(study)
    nct = parsed["nct"]
    if nct != candidate["nct"]:
        raise ReplayError(f"source identity mismatch at {candidate['locator']}")
    attrs = _trial_attrs(parsed) | {"replay_container_locator": candidate["locator"],
                                    "replay_captured_source_id": candidate["source_id"]}
    entity_id, _ = db.upsert_entity(project_id, "trial", nct, attrs=attrs, route_id=ROUTE)
    facts = design_facts(parsed)
    for fact in facts:
        fact["id"] = new_id("fct")
        relative = (fact.get("context") or {}).get("json_path") or ""
        fact["context"].update({"parser_json_path": relative, "json_path": _abs(candidate["locator"], relative),
                                "container_locator": candidate["locator"],
                                "captured_source_id": candidate["source_id"],
                                "captured_at": candidate["fetched_at"]})
        fact.update(project_id=project_id, entity_id=entity_id, source_id=isolated_source_id)
    critical = [fact for fact in facts if fact["tier"] == "critical"]
    verification = verify_facts(document, candidate["locator"], nct, critical)
    for fact in facts:
        db.add_fact(fact)
    drugs = _drugs(parsed)
    for name in drugs:
        drug_id, _ = db.upsert_entity(project_id, "drug", name, route_id=ROUTE, attrs={
            "discovery_method": "registry_intervention_replay", "evidence_urls": [attrs.get("url")]})
        db.link(project_id, drug_id, "drug-trial", entity_id)
    record = {"nct": nct, "container_locator": candidate["locator"],
              "captured_source_id": candidate["source_id"], "isolated_source_id": isolated_source_id,
              "enrollment": parsed["enrollment"], "enrollment_type": parsed["enrollment_type"],
              "phase": parsed["phase"], "phases": parsed["phases"], "study_type": parsed["study_type"],
              "drugs": drugs, "fact_ids": [fact["id"] for fact in facts]}
    return record, verification, _limits(parsed)
def _crit(verifications):
    out = {"checked": 0, "match": 0, "mismatch": 0, "unknown": 0, "fail": 0,
           "identity": {"checked": 0, "match": 0, "mismatch": 0}, "fields": {}, "failures": []}
    for verification in verifications:
        for key in ("checked", "match", "mismatch", "unknown", "fail"):
            out[key] += verification[key]
        for key in ("checked", "match", "mismatch"):
            out["identity"][key] += verification["identity"][key]
        out["failures"].extend(verification["failures"])
        for field, stats in verification["fields"].items():
            target = out["fields"].setdefault(field, {"checked": 0, "match": 0, "mismatch": 0, "unknown": 0})
            for key in target:
                target[key] += stats[key]
    return out
def _limitations(limits):
    counts, trials = Counter(kind for kind, _, _ in limits), defaultdict(list)
    for kind, nct, _ in limits:
        if nct not in trials[kind]:
            trials[kind].append(nct)
    return [{"kind": kind, "count": counts[kind], "trials": trials[kind]} for kind in sorted(counts)]
def _files():
    items = {"helper": Path(__file__), "parser": Path(ctgov_module.__file__),
             "render_portal": Path(portal_module.__file__), "render_design": Path(design_module.__file__)}
    return {name: {"path": str(path.resolve()), "sha256": _sha(path.read_bytes())}
            for name, path in items.items()}
def _materialize(source_dir, source_project_id, output_dir, command, snapshot, scan):
    data_dir = output_dir / "data"
    data_dir.mkdir()
    cas = CAS(data_dir / "cas")
    db = DB(data_dir / "ciw2.sqlite3")
    project = snapshot["project"]
    project_id = db.create_project(project["indication"], ["C"], focus=project["focus"] or "",
                                   cutoff_date=project["cutoff_date"],
                                   request_text="组件回放：仅使用已捕获的 CT.gov 容器 JSON；无实时检索、无 LLM、无流水线运行。")
    selected = defaultdict(list)
    for candidate in scan["latest"].values():
        selected[candidate["source_id"]].append(candidate)
    by_id = {row["id"]: row for row in snapshot["sources"]}
    trials, excluded, copied, verifications, limits = [], [], [], [], []
    for source_id in sorted(selected):
        source = by_id[source_id]
        raw, error = _load(source_dir, source["digest"])
        if error:
            raise ReplayError(f"captured source {source_id} changed during replay: {error}")
        document = json.loads(raw)
        included = []
        for candidate in sorted(selected[source_id], key=lambda item: item["nct"]):
            study = _resolve(document, candidate["locator"])
            source_nct = _resolve(study, "$.protocolSection.identificationModule.nctId") if isinstance(study, dict) else None
            if source_nct != candidate["nct"]:
                raise ReplayError(f"source identity mismatch at {candidate['locator']}")
            reason, detail = _classify(study)
            if reason:
                excluded.append({"nct": candidate["nct"], "reason": reason, "detail": detail,
                                 "captured_source_id": source_id, "container_locator": candidate["locator"]})
            else:
                included.append((candidate, study))
        if not included:
            continue
        isolated_source_id = _register(db, project_id, source_project_id, source, included,
                                       included[0][0]["shape"], cas, source_dir, copied)
        for candidate, study in included:
            record, verification, trial_limits = _ingest(db, project_id, isolated_source_id, candidate, study, document)
            trials.append(record)
            verifications.append(verification)
            limits.extend(trial_limits)
    return _finish(db, project_id, output_dir, command, snapshot, scan, trials, excluded, copied,
                   verifications, limits)
def _finish(db, project_id, output_dir, command, snapshot, scan, trials, excluded, copied, verifications, limits):
    html = render_report(db, project_id, "C", inline=True)
    html_bytes = html.encode("utf-8")
    (output_dir / "portal-C.html").write_bytes(html_bytes)
    rows = data_c(db, project_id)["rows"]
    critical = _crit(verifications)
    counts = {
        "latest_versions": len(scan["latest"]), "included": len(trials), "excluded": len(excluded),
        "top_n_applied": False,
        "included_with_missing_enrollment": sum(trial["enrollment"] is None for trial in trials),
        "included_with_zero_enrollment": sum(trial["enrollment"] == 0 for trial in trials),
        "included_without_primary_outcomes": sum(1 for kind, _, _ in limits if kind == "no_primary_outcomes"),
        "unique_literal_intervention_names": len({drug for trial in trials for drug in trial["drugs"]}),
    }
    if counts["latest_versions"] != counts["included"] + counts["excluded"]:
        raise ReplayError("scope accounting mismatch: latest versions != included + excluded")
    by_tier = {row["tier"]: row["n"] for row in db.query("SELECT tier, count(*) AS n FROM facts GROUP BY tier")}
    pipeline = {key: db.one(f"SELECT count(*) AS n FROM {table}")["n"] for key, table in (
        ("runs_created", "runs"), ("stages_created", "stages"),
        ("coverage_rows", "coverage"), ("agent_steps", "agent_steps"))}
    pipeline.update({"llm_calls": 0, "network_calls": 0, "browser_calls": 0,
                     "live_db_writes": 0, "live_cas_writes": 0,
                     "note": "No run/stage/coverage/agent-step rows; component replay only."})
    reasons = Counter(item["reason"] for item in excluded)
    receipt = {
        "schema": RECEIPT,
        "generated_at": _now(),
        "command": command,
        "component_only": True,
        "m1_status": "NOT_ASSESSED",
        "scope": {"inclusion_rule": RULE, "not_an_innovation_decision": True},
        "source_snapshot": {
            "source_db": str(snapshot["database"]), "project_id": snapshot["project"]["id"],
            "open_mode": "read-only URI (mode=ro, query_only=ON), single snapshot",
            "max_fetched_at": snapshot["max_fetched_at"], "sources_rows_total": len(snapshot["all"]),
            "sources_by_kind": snapshot["kinds"], "ctgov_sources": len(snapshot["sources"]),
            "studies_seen": scan["seen"], "studies_without_nct_id": scan["no_nct"],
            "candidate_bindings": scan["count"], "unique_ncts": len(scan["latest"]),
            "superseded_bindings": scan["count"] - len(scan["latest"]),
            "integrity_failures": scan["failures"], "unreadable_sources": scan["unreadable"],
            "live_db_note": "Read-only snapshot; the live process may append new sources after this read.",
        },
        "selection": {
            "strategy": "Latest (fetched_at, source_id) per literal NCT id; lower study index on an exact tie.",
            "counts": counts, "excluded_by_reason": dict(sorted(reasons.items())),
            "trials": sorted(trials, key=lambda item: item["nct"]),
            "excluded_trials": sorted(excluded, key=lambda item: item["nct"]),
        },
        "copied_sources": copied,
        "facts": {"added": sum(by_tier.values()), "by_tier": by_tier},
        "critical_verification": critical,
        "parser_limitations": _limitations(limits),
        "render": {"project_id": project_id, "rows": len(rows), "html": str(output_dir / "portal-C.html"),
                   "html_sha256": _sha(html_bytes), "html_bytes": len(html_bytes)},
        "pipeline": pipeline,
        "files": _files(),
    }
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt
def _failed(output_dir, command, source_dir, project_id, error):
    try:
        (output_dir / "FAILED.json").write_text(json.dumps({
            "status": "FAILED", "error": f"{type(error).__name__}: {error}",
            "created_at": _now(), "command": command, "source_data_dir": str(source_dir),
            "project_id": project_id, "output_dir": str(output_dir),
            "resume_hint": "Inspect this directory; it was created by this run and is never overwritten. "
                           "Retry with a new output directory.",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
def run_replay(source_data_dir, project_id, output_dir):
    source_dir = Path(source_data_dir).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not source_dir.is_dir():
        raise ReplayError(f"source data directory not found: {source_dir}")
    if output_dir.exists() or output_dir.is_symlink():
        raise ReplayError(f"output directory already exists: {output_dir}")
    if not output_dir.parent.is_dir():
        raise ReplayError(f"output parent directory does not exist: {output_dir.parent}")
    snapshot = _read(source_dir, project_id)
    scan = _scan(snapshot, source_dir)
    if not scan["latest"]:
        raise ReplayError("no readable captured CT.gov studies with an NCT id were found")
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "--source-data-dir", str(source_dir),
                          "--project-id", project_id, "--output-dir", str(output_dir)])
    output_dir.mkdir(exist_ok=False)
    try:
        return _materialize(source_dir, project_id, output_dir, command, snapshot, scan)
    except Exception as error:
        _failed(output_dir, command, source_dir, project_id, error)
        raise
def _parser():
    parser = argparse.ArgumentParser(description="Replay captured CT.gov sources into an isolated C dataset.")
    parser.add_argument("--source-data-dir", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser
def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        receipt = run_replay(args.source_data_dir, args.project_id, args.output_dir)
    except ReplayError as error:
        print(f"replay refused or failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"output_dir": str(Path(args.output_dir).expanduser().resolve()),
                      "trials": receipt["selection"]["counts"]["included"],
                      "excluded": receipt["selection"]["counts"]["excluded"],
                      "critical_checked": receipt["critical_verification"]["checked"],
                      "critical_mismatch": receipt["critical_verification"]["mismatch"],
                      "html_sha256": receipt["render"]["html_sha256"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
