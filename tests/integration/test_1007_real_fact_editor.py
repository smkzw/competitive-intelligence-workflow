"""Real current-fact editor: arbitrary selection, semantic controls, wire payloads.

Development-scope proof only. It exercises the actual production page, script, and
W04 loopback service in a pytest tmp workspace; it is not clinical, installed
journey, browser, or scientific acceptance.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.user_fact_edit import UserFactEditService, UserFactSaveError
from ci_workflow.application.user_fact_edit_server import LoopbackEditServer, _editor_page
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_w04_user_fact_edit import (
    NOW,
    PROJECT_ID,
    _project,
    _projection,
    _request_http,
)

_FACTS_SCRIPT = re.compile(rb'<script id="facts" type="application/json">(.*?)</script>', re.S)
_EDITOR_SCRIPT = re.compile(rb'<script id="editor">(.*?)</script>', re.S)
_NODE = shutil.which("node")

_HOSTILE = "</script><script>globalThis.__INJECTED=1</script><img src=x onerror=alert(1)>"
_HOSTILE_LOCATOR = "$.lsmean</script><script>globalThis.__LOCATOR=1</script>"


def _get_editor(server: LoopbackEditServer) -> tuple[str, str, str, bytes]:
    host = f"127.0.0.1:{server.port}"
    status, headers, page = _request_http(server, "GET", "/", headers={"Host": host})
    assert status == 200
    return host, headers["set-cookie"].split(";", 1)[0], headers["x-csrf-token"], page


def _post_editor(
    server: LoopbackEditServer,
    host: str,
    cookie: str,
    csrf: str,
    payload: dict[str, Any],
    *,
    with_csrf: bool = True,
    content_type: str = "application/json",
) -> tuple[int, dict[str, str], bytes]:
    headers = {
        "Host": host,
        "Origin": f"http://{host}",
        "Cookie": cookie,
        "Content-Type": content_type,
    }
    if with_csrf:
        headers["X-CSRF-Token"] = csrf
    body = json.dumps(payload, ensure_ascii=False).encode()
    return _request_http(server, "POST", "/api/save", body=body, headers=headers)


def _wire_payload(
    fact: dict[str, Any],
    edits: dict[str, Any],
    *,
    revision: int,
    request_id: str,
    operation: str = "save",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "project_id": PROJECT_ID,
        "expected_revision": revision,
        "operation": operation,
        "target": {
            key: fact[key]
            for key in ("fact_id", "fact_version_id", "entity_id", "field_id")
        },
        "edits": edits,
        "user_basis": "编辑器线载荷验收，依据已核对来源。",
        "saved_by": "browser-user",
        "saved_at": NOW.isoformat(),
    }


def _envelope(page: bytes) -> dict[str, Any]:
    match = _FACTS_SCRIPT.search(page)
    assert match is not None, "facts envelope script is missing"
    return json.loads(match.group(1).decode("utf-8"))


def _scripts(page: bytes) -> tuple[str, str]:
    facts = _FACTS_SCRIPT.search(page)
    editor = _EDITOR_SCRIPT.search(page)
    assert facts is not None and editor is not None, "page scripts are missing"
    assert b"</script" not in facts.group(1) and b"</script" not in editor.group(1)
    return facts.group(1).decode("utf-8"), editor.group(1).decode("utf-8")


def _run_node_harness(
    tmp_path: Path, *, facts_script: str, editor_script: str, case: str
) -> str:
    if _NODE is None:
        pytest.fail("Node.js is required for the real fact editor script checks")
    source = (
        "const PAGE_FACTS_JSON = " + json.dumps(facts_script) + ";\n"
        "const PAGE_SCRIPT = " + json.dumps(editor_script) + ";\n"
        "const CASE = " + json.dumps(case) + ";\n"
        + _NODE_HARNESS_BODY
    )
    path = tmp_path / f"real_fact_editor_{case}.js"
    path.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        [_NODE, str(path)], capture_output=True, text=True, timeout=120, check=False
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout


def test_real_editor_lists_every_current_fact_without_fixed_demo_forms(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        _host, _cookie, _csrf, page = _get_editor(server)
        envelope = _envelope(page)
        assert envelope["project_id"] == PROJECT_ID
        assert envelope["revision"] == 0
        assert set(envelope["facts"]) == set(service.current_facts())
        for fact_id in (
            "fact-crude-rate",
            "fact-a-safety",
            "fact-c-threshold",
            "fact-adjusted-rate",
            "fact-lsmean",
            "fact-unrelated-20",
        ):
            assert fact_id in envelope["facts"]
        # The two fixed demo forms are replaced by searchable current facts.
        assert b'id="save-rate"' not in page
        assert b'id="save-threshold"' not in page
        assert b"innerHTML" not in page
        assert b"document.write" not in page
        assert "不继承独立科学接受".encode() in page
        assert "未公开".encode() not in page
        facts_script, editor_script = _scripts(page)
        assert "fact-crude-rate" in facts_script and "fact-c-threshold" in facts_script
        assert "input-numerator" in editor_script


@pytest.mark.parametrize("case", ["base", "estimate", "sample"])
def test_real_editor_script_selects_semantic_controls_in_node(
    tmp_path: Path, case: str
) -> None:
    root, _ = _project(
        tmp_path,
        include_b_efficacy=case == "estimate",
        c_sample_size=case == "sample",
    )
    with LoopbackEditServer(UserFactEditService(root)) as server:
        _host, _cookie, _csrf, page = _get_editor(server)
    facts_script, editor_script = _scripts(page)
    stdout = _run_node_harness(
        tmp_path, facts_script=facts_script, editor_script=editor_script, case=case
    )
    assert f"NODE-OK {case}" in stdout


def test_real_editor_wire_saves_clear_restore_and_undo(tmp_path: Path) -> None:
    root, fragments = _project(tmp_path)
    service = UserFactEditService(root)
    pointer = root / "reports/current.json"
    with LoopbackEditServer(service) as server:
        host, cookie, csrf, page = _get_editor(server)
        envelope = _envelope(page)
        rate = envelope["facts"]["fact-crude-rate"]
        before_pointer = pointer.read_bytes()

        # Blank numeric text is not zero and must not touch current or revision.
        status, _headers, _body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                rate,
                {"raw_value": "", "normalized_value": 0},
                revision=0,
                request_id="wire-blank",
            ),
        )
        assert status == 400
        assert pointer.read_bytes() == before_pointer

        # Zero is a real count.
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                rate,
                {"numerator": 0, "denominator": 80},
                revision=0,
                request_id="wire-zero",
            ),
        )
        assert status == 200
        saved = json.loads(body)
        assert saved["revision"] == 1
        assert saved["result"]["derived_crude_rate"] == 0.0
        assert saved["result"]["independent_scientific_acceptance"] == "not_inherited"
        saved_rate = saved["facts"]["fact-crude-rate"]
        assert saved_rate["fact_version_id"] == saved["result"]["fact_version_id"]
        assert saved_rate["normalized_value"] == "0.0"
        # Nothing else on the fact is silently changed.
        owned = {
            "fact_version_id",
            "raw_value",
            "normalized_value",
            "numerator",
            "denominator",
            "disclosure_state",
            "review_state",
            "user_edit",
        }
        for field, value in rate.items():
            if field in owned:
                continue
            assert saved_rate[field] == value
        assert set(saved_rate) - set(rate) <= {"user_edit"}
        assert saved_rate["source_quote"] == "34/62例受试者发生任何TEAE（54.8%）。"
        row = next(
            item for item in _projection(root, "B")["safety"]
            if item["row_id"] == "safe-apply-t-1"
        )
        assert (row["value"], row["numerator"], row["denominator"]) == (0.0, 0, 80)
        with open_database(root / "state/project.sqlite") as database:
            quote = database.execute(
                "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
                (fragments["count"],),
            ).fetchone()
        assert quote is not None and quote[0] == "34/62例受试者发生任何TEAE（54.8%）。"

        # Explicit clear sends null to the effective numeric value.
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                saved_rate, {"numerator": None}, revision=1, request_id="wire-clear"
            ),
        )
        assert status == 200
        cleared = json.loads(body)
        assert cleared["revision"] == 2
        cleared_rate = cleared["facts"]["fact-crude-rate"]
        assert cleared_rate["disclosure_state"] == "user_cleared"
        assert cleared_rate["raw_value"] is None
        assert cleared_rate["normalized_value"] is None
        assert cleared_rate["numerator"] is None and cleared_rate["denominator"] is None
        assert cleared_rate["source_quote"] == "34/62例受试者发生任何TEAE（54.8%）。"
        b_projection = _projection(root, "B")
        cleared_row = next(
            item for item in b_projection["safety"] if item["row_id"] == "safe-apply-t-1"
        )
        assert cleared_row["value"] is None
        assert "用户清除，待重新核实" in json.dumps(cleared_row, ensure_ascii=False)
        edit = b_projection["user_edits"]["safe-apply-t-1"]
        assert edit["status_label_zh"] == "用户清除，待重新核实"
        assert edit["original_value"].startswith("54.8%")

        # Restore after clear keeps the source denominator rule of the service.
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                cleared_rate,
                {"numerator": 24, "denominator": 62},
                revision=2,
                request_id="wire-restore",
            ),
        )
        assert status == 200
        restored = json.loads(body)
        assert restored["revision"] == 3
        assert restored["result"]["derived_crude_rate"] == round(24 / 62 * 100, 10)

        # Undo appends a version restoring the previous effective state.
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                restored["facts"]["fact-crude-rate"],
                {},
                revision=3,
                request_id="wire-undo",
                operation="undo",
            ),
        )
        assert status == 200
        undone = json.loads(body)
        assert undone["revision"] == 4
        assert undone["result"]["review_state"] == "user_modified"
        assert undone["facts"]["fact-crude-rate"]["disclosure_state"] == "user_cleared"

        # A fresh page reads the same current revision and cleared state.
        _host2, _cookie2, _csrf2, refreshed = _get_editor(server)
        refreshed_envelope = _envelope(refreshed)
        assert refreshed_envelope["revision"] == 4
        assert refreshed_envelope["facts"]["fact-crude-rate"]["disclosure_state"] == (
            "user_cleared"
        )
        assert service.read_current_delivery().revision == 4


def test_real_editor_wire_updates_arbitrary_a_and_c_facts(tmp_path: Path) -> None:
    root, _fragments = _project(tmp_path)
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        host, cookie, csrf, page = _get_editor(server)
        envelope = _envelope(page)
        deliveries = {item.report: item for item in service.read_current_delivery().reports}

        threshold = envelope["facts"]["fact-c-threshold"]
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                threshold,
                {
                    "threshold_operator": "<=",
                    "threshold_value": 18.0,
                    "threshold_unit": "分",
                },
                revision=0,
                request_id="wire-threshold",
            ),
        )
        assert status == 200
        saved = json.loads(body)
        assert saved["revision"] == 1
        assert saved["result"]["rebuilt_reports"] == ["C"]
        saved_threshold = saved["facts"]["fact-c-threshold"]
        assert float(saved_threshold["threshold_value"]) == 18.0
        assert float(saved_threshold["normalized_value"]) == 18.0
        assert saved_threshold["unit"] == "分"
        row = next(
            item for item in _projection(root, "C")["observations"]
            if item["row_id"] == "c-nct04178967-inclusion"
        )
        assert float(row["threshold_value"]) == 18.0
        entries = {item.report: item for item in service.read_current_delivery().reports}
        assert entries["A"] == deliveries["A"] and entries["B"] == deliveries["B"]

        safety = saved["facts"]["fact-a-safety"]
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                safety,
                {"numerator": 20, "denominator": 50},
                revision=1,
                request_id="wire-a-rate",
            ),
        )
        assert status == 200
        saved_a = json.loads(body)
        assert saved_a["revision"] == 2
        assert saved_a["result"]["rebuilt_reports"] == ["A"]
        assert saved_a["result"]["derived_crude_rate"] == 40.0
        a_row = next(
            item for item in _projection(root, "A")["safety"]
            if item["row_id"] == "safe-fixture-teae"
        )
        assert (a_row["value"], a_row["numerator"], a_row["denominator"]) == (40.0, 20, 50)
        entries = {item.report: item for item in service.read_current_delivery().reports}
        assert entries["C"].revision == 1 and entries["B"] == deliveries["B"]


def test_real_editor_failure_paths_keep_current_and_revision(tmp_path: Path) -> None:
    root, _fragments = _project(tmp_path)
    service = UserFactEditService(root)
    pointer = root / "reports/current.json"
    with LoopbackEditServer(service) as server:
        host, cookie, csrf, page = _get_editor(server)
        envelope = _envelope(page)
        before_pointer = pointer.read_bytes()
        before_delivery = service.read_current_delivery()

        # A fact without declared portal consumers cannot be saved.
        unconsumed = envelope["facts"]["fact-lsmean"]
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                unconsumed,
                {"raw_value": "20.5", "normalized_value": 20.5},
                revision=0,
                request_id="wire-unconsumed",
            ),
        )
        assert status == 400
        assert "消费者" in json.loads(body)["error"]

        # A stale expected revision is a conflict, not a silent overwrite.
        rate = envelope["facts"]["fact-crude-rate"]
        status, _headers, body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                rate,
                {"numerator": 24, "denominator": 80},
                revision=7,
                request_id="wire-stale",
            ),
        )
        assert status == 409
        assert "版本冲突" in json.loads(body)["error"]

        # Missing CSRF and a non-JSON media type stay blocked.
        status, _headers, _body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                rate,
                {"numerator": 24, "denominator": 80},
                revision=0,
                request_id="wire-no-csrf",
            ),
            with_csrf=False,
        )
        assert status == 403
        status, blocked_headers, _body = _post_editor(
            server,
            host,
            cookie,
            csrf,
            _wire_payload(
                rate,
                {"numerator": 24, "denominator": 80},
                revision=0,
                request_id="wire-media",
            ),
            content_type="text/plain",
        )
        assert status == 415
        assert "access-control-allow-origin" not in blocked_headers

        assert pointer.read_bytes() == before_pointer
        assert service.read_current_delivery() == before_delivery
        assert _envelope(_get_editor(server)[3])["revision"] == 0


def test_editor_save_keeps_original_api_result_fields(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        host, cookie, csrf, page = _get_editor(server)
        fact = _envelope(page)["facts"]["fact-crude-rate"]
        status, _, body = _post_editor(server, host, cookie, csrf, _wire_payload(
            fact, {"numerator": 24, "denominator": 62}, revision=0,
            request_id="owner-compatible-save",
        ))
        data = json.loads(body)
        assert status == 200
        assert data["fact_version_id"] == data["result"]["fact_version_id"]
        assert data["rebuilt_reports"] == data["result"]["rebuilt_reports"]
        assert data["current_revision"] == 1
        assert data["refresh_required"] is False


def test_committed_save_is_not_reported_failed_when_refresh_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        host, cookie, csrf, page = _get_editor(server)
        fact = _envelope(page)["facts"]["fact-crude-rate"]

        def unavailable() -> dict[str, dict[str, Any]]:
            raise UserFactSaveError("owner injected post-commit refresh failure")

        monkeypatch.setattr(service, "current_facts", unavailable)
        status, _, body = _post_editor(server, host, cookie, csrf, _wire_payload(
            fact, {"numerator": 24, "denominator": 62}, revision=0,
            request_id="owner-refresh-failure",
        ))
        data = json.loads(body)
        assert status == 200
        assert data["revision"] == 1
        assert data["refresh_required"] is True and data["facts"] is None
        assert "已保存" in data["message"] and "不要重复保存" in data["message"]
        assert service.read_current_delivery().revision == 1


def test_editor_fact_choices_are_native_buttons(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    page = _editor_page(facts=UserFactEditService(root).current_facts(), revision=0,
                        project_id=PROJECT_ID)
    facts, script = _scripts(page)
    assert "NODE-OK native_choices" in _run_node_harness(
        tmp_path, facts_script=facts, editor_script=script, case="native_choices",
    )


_HOSTILE_FACT: dict[str, Any] = {
    "fact_id": "fact-hostile",
    "fact_version_id": "fact-hostile-v1",
    "entity_id": "entity-arm",
    "field_id": "safety.crude_rate",
    "drug_name": _HOSTILE,
    "product_id": _HOSTILE,
    "trial_id": _HOSTILE,
    "registry_id": _HOSTILE,
    "arm": _HOSTILE,
    "group_id": _HOSTILE,
    "cohort_id": _HOSTILE,
    "endpoint_definition": _HOSTILE,
    "event_definition": _HOSTILE,
    "timepoint": _HOSTILE,
    "period": _HOSTILE,
    "unit": _HOSTILE,
    "normalized_unit": _HOSTILE,
    "statistical_form": "crude_rate",
    "measure_object": "participants",
    "numerator": 34,
    "denominator": 62,
    "raw_value": _HOSTILE,
    "normalized_value": "54.8",
    "disclosure_state": "reported_value",
    "review_state": "accepted",
    "source_quote": _HOSTILE,
    "source_locator": _HOSTILE_LOCATOR,
    "source_version_id": "source-v1",
    "primary_fragment_id": "fragment-count",
    "threshold_unit": _HOSTILE,
    "consumer_bindings": [],
}


def test_real_editor_embeds_hostile_source_text_without_injection(tmp_path: Path) -> None:
    root, _fragments = _project(tmp_path, b_binding_override=("drug_name", _HOSTILE))
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        _host, _cookie, _csrf, page = _get_editor(server)
        assert b"</script><script>" not in page
        assert b"<img" not in page
        assert b"\\u003cscript" in page
        assert b"onerror" in page
        envelope = _envelope(page)
        assert envelope["facts"]["fact-crude-rate"]["drug_name"] == _HOSTILE
        assert service.current_facts()["fact-crude-rate"]["drug_name"] == _HOSTILE
        facts_script, editor_script = _scripts(page)
        stdout = _run_node_harness(
            tmp_path, facts_script=facts_script, editor_script=editor_script, case="hostile"
        )
        assert "NODE-OK hostile" in stdout

    # The embedding function itself never lets hostile data or a hostile project
    # identity close the data script or inject markup.
    direct = _editor_page(
        facts={"fact-hostile": dict(_HOSTILE_FACT)}, revision=0, project_id=_HOSTILE
    )
    assert direct.count(b"</script>") == 2
    assert b"</script><script>" not in direct
    assert b"<img" not in direct
    direct_envelope = _envelope(direct)
    assert direct_envelope["project_id"] == _HOSTILE
    direct_fact = direct_envelope["facts"]["fact-hostile"]
    for field, value in _HOSTILE_FACT.items():
        assert direct_fact[field] == value
    direct_facts_script, direct_editor_script = _scripts(direct)
    direct_stdout = _run_node_harness(
        tmp_path,
        facts_script=direct_facts_script,
        editor_script=direct_editor_script,
        case="hostile",
    )
    assert "NODE-OK hostile" in direct_stdout


_NODE_HARNESS_BODY = r"""
'use strict';
const envelope = JSON.parse(PAGE_FACTS_JSON);
const META_CSRF = 'mock-csrf-token';
let failures = 0;
async function flow(name, body) {
  try {
    await body();
    console.log('flow-ok ' + name);
  } catch (error) {
    failures += 1;
    console.error('NODE-FAIL ' + name + ': ' + (error && error.message));
  }
}
function ok(condition, message) {
  if (!condition) throw new Error(message);
}
function makeEl(tag) {
  const el = {
    tagName: tag, id: '', className: '', children: [], textContent: '', value: '',
    hidden: false, disabled: false, placeholder: '', type: '', inputMode: '', rows: 0,
    _handlers: {},
  };
  el.appendChild = function (child) { el.children.push(child); return child; };
  el.replaceChildren = function () { el.children = Array.prototype.slice.call(arguments); };
  el.addEventListener = function (type, handler) {
    (el._handlers[type] = el._handlers[type] || []).push(handler);
  };
  el.setAttribute = function (name, value) { el[name] = value; };
  el.focus = function () { globalThis.__focused = el; };
  return el;
}
const registry = {};
['facts', 'status', 'search', 'fact-list', 'detail', 'detail-fields', 'controls',
 'basis', 'result', 'save', 'clear', 'undo'].forEach(function (id) {
  registry[id] = makeEl('div');
  registry[id].id = id;
});
registry['facts'].textContent = PAGE_FACTS_JSON;
const mockRoot = makeEl('body');
Object.keys(registry).forEach(function (id) { mockRoot.appendChild(registry[id]); });
globalThis.document = {
  getElementById: function (id) { return registry[id] || null; },
  createElement: makeEl,
  querySelector: function (selector) {
    return selector === 'meta[name=csrf]' ? { content: META_CSRF } : null;
  },
};
function walk(node, out) {
  out = out || [];
  for (const child of node.children) { out.push(child); walk(child, out); }
  return out;
}
function byId(id) {
  return walk(mockRoot).find(function (el) { return el.id === id; });
}
function textOf(node) {
  let text = node.textContent || '';
  for (const child of node.children) text += textOf(child);
  return text;
}
function listItems() {
  return walk(byId('fact-list')).filter(function (el) { return el.tagName === 'li'; });
}
async function fire(el, type) {
  let last;
  for (const handler of el._handlers[type] || []) last = await handler({});
  return last;
}
function setValue(id, value) { byId(id).value = value; }
function click(id) { return fire(byId(id), 'click'); }
async function selectFact(factId) {
  const item = listItems().find(function (el) {
    return textOf(el).indexOf(factId) >= 0;
  });
  ok(item, 'fact list item missing: ' + factId);
  await fire(item, 'click');
}
const fetchLog = [];
let responder = function () {
  return { ok: false, status: 500, body: { error: 'no responder installed' } };
};
globalThis.fetch = async function (url, options) {
  fetchLog.push({ url: url, options: options });
  const reply = responder(url, options, fetchLog.length);
  return { ok: reply.ok, status: reply.status, json: async function () { return reply.body; } };
};
let serverRevision = envelope.revision;
const serverFacts = JSON.parse(JSON.stringify(envelope.facts));
function commit(factId, mutate) {
  serverRevision += 1;
  const fact = serverFacts[factId];
  fact.fact_version_id = factId + '-r' + serverRevision;
  // Mirror the service: a committed save stores the user basis with the fact.
  fact.user_edit = {
    request_id: 'browser-mock-' + serverRevision,
    revision: serverRevision,
    basis: String(registry['basis'].value || ''),
    operation: 'save',
    cleared: false,
    independent_scientific_acceptance: 'not_inherited',
  };
  if (mutate) mutate(fact);
  return {
    ok: true,
    status: 200,
    body: {
      revision: serverRevision,
      result: { revision: serverRevision },
      facts: JSON.parse(JSON.stringify(serverFacts)),
    },
  };
}
function lastCall() { return fetchLog[fetchLog.length - 1]; }
function lastPayload() { return JSON.parse(lastCall().options.body); }
function statusText() { return textOf(byId('status')); }
function detailText() { return textOf(byId('detail-fields')); }
function fieldValue(label) {
  const nodes = walk(byId('detail-fields'));
  const index = nodes.findIndex(function (el) {
    return el.tagName === 'dt' && el.textContent === label;
  });
  ok(index >= 0 && nodes[index + 1] && nodes[index + 1].tagName === 'dd',
    'detail row missing: ' + label);
  return nodes[index + 1].textContent;
}
async function actAndCommit(action, factId, mutate) {
  const revisionBefore = serverRevision;
  const versionBefore = serverFacts[factId].fact_version_id;
  responder = function () { return commit(factId, mutate); };
  await click(action);
  const payload = lastPayload();
  ok(payload.expected_revision === revisionBefore,
    action + ': expected_revision must equal the refreshed revision');
  ok(payload.target.fact_version_id === versionBefore,
    action + ': target version must equal the refreshed version');
  return payload;
}

async function flowListAndSelection() {
  const ids = Object.keys(envelope.facts);
  ok(byId('detail').hidden === true, 'detail starts hidden');
  for (const id of ids) {
    ok(textOf(byId('fact-list')).indexOf(id) >= 0, 'list must include ' + id);
  }
  setValue('search', 'lsm');
  await fire(byId('search'), 'input');
  let items = listItems();
  ok(items.length === 1, 'search must narrow the list, got ' + items.length);
  ok(textOf(items[0]).indexOf('fact-lsmean') >= 0, 'search result must be fact-lsmean');
  setValue('search', '');
  await fire(byId('search'), 'input');
  items = listItems();
  ok(items.length === ids.length, 'clearing the search restores the full list');
}

async function flowHumanAndStateFields() {
  await selectFact('fact-crude-rate');
  ok(byId('detail').hidden === false, 'detail appears after selection');
  const text = detailText();
  for (const expected of ['治疗组', 'NCT04558918', '任何TEAE', '治疗期间',
    '54.8% (34/62)', '34/62例受试者发生任何TEAE']) {
    ok(text.indexOf(expected) >= 0, 'detail missing "' + expected + '"');
  }
  ok(text.indexOf('fact-crude-rate') >= 0, 'wiring fact id must be shown');
  ok(text.indexOf('fact-crude-rate-v1') >= 0, 'wiring fact version must be shown');
}

async function flowRatePayloadsRefreshed() {
  await selectFact('fact-crude-rate');
  ok(byId('input-numerator') && byId('input-denominator'), 'rate controls expose n and N');
  ok(!byId('input-threshold-operator') && !byId('input-value'),
    'rate controls must not mix other kinds');
  setValue('basis', '根据核对后的病例汇总表修订。');
  // A blank denominator is not zero.
  setValue('input-numerator', '24');
  setValue('input-denominator', '   ');
  let before = fetchLog.length;
  await click('save');
  ok(fetchLog.length === before, 'blank denominator must not be posted');
  ok(statusText().indexOf('不能为空') >= 0, 'blank denominator must be reported');
  // Zero is a real count.
  setValue('input-numerator', '0');
  setValue('input-denominator', '80');
  let payload = await actAndCommit('save', 'fact-crude-rate', function (fact) {
    fact.normalized_value = '0.0';
    fact.raw_value = '0% (0/80)';
    fact.numerator = 0;
    fact.denominator = 80;
  });
  ok(payload.edits.numerator === 0 && payload.edits.denominator === 80,
    'zero must be sent as 0');
  ok(Object.keys(payload.edits).length === 2, 'rate payload carries exactly n and N');
  ok(payload.operation === 'save' && payload.schema_version === '1.0', 'operation and schema');
  ok(payload.project_id === envelope.project_id, 'project identity is reused from the page');
  ok(String(payload.request_id).indexOf('browser-') === 0, 'request id prefix');
  ok(lastCall().options.headers['X-CSRF-Token'] === META_CSRF,
    'csrf header must come from the page meta');
  ok(String(payload.saved_at).length > 0, 'saved_at present');
  ok(detailText().indexOf(serverFacts['fact-crude-rate'].fact_version_id) >= 0,
    'selection must stay on the refreshed fact version');
  ok(statusText().indexOf('revision ' + serverRevision) >= 0,
    'status must show the refreshed revision');
  ok(fetchLog.length === before + 1, 'exactly one request for the zero save');
  // The next save uses the refreshed revision and version.
  setValue('input-numerator', '24');
  setValue('input-denominator', '80');
  await actAndCommit('save', 'fact-crude-rate', function (fact) {
    fact.normalized_value = '30.0';
    fact.raw_value = '30% (24/80)';
    fact.numerator = 24;
    fact.denominator = 80;
  });
  ok(detailText().indexOf('30% (24/80)') >= 0, 'refreshed current value must render');
}

async function flowThreshold() {
  await selectFact('fact-c-threshold');
  ok(byId('input-threshold-operator') && byId('input-threshold-value')
    && byId('input-threshold-unit'), 'threshold controls must be present');
  ok(!byId('input-value') && !byId('input-numerator'), 'threshold must not mix other kinds');
  ok(byId('input-threshold-operator').value === '>=',
    'operator must start from the current operator');
  ok(byId('input-threshold-value').value === '16',
    'threshold must start from the current value');
  setValue('input-threshold-operator', '<=');
  setValue('input-threshold-value', '18');
  setValue('input-threshold-unit', '分');
  setValue('basis', '方案修订版将同一入组量表阈值由16分修正为18分。');
  const payload = await actAndCommit('save', 'fact-c-threshold', function (fact) {
    fact.threshold_operator = '<=';
    fact.threshold_value = 18;
    fact.raw_value = '<=18 分';
  });
  ok(payload.edits.threshold_operator === '<=' && payload.edits.threshold_value === 18
    && payload.edits.threshold_unit === '分',
    'threshold payload must carry the current operator/value/unit');
  ok(Object.keys(payload.edits).length === 3, 'threshold payload carries exactly three fields');
  const before = fetchLog.length;
  setValue('input-threshold-value', '');
  await click('save');
  ok(fetchLog.length === before, 'blank threshold must not be posted');
  ok(statusText().indexOf('不能为空') >= 0, 'blank threshold must be reported');
}

async function flowCount() {
  await selectFact('fact-unrelated-20');
  ok(byId('input-value'), 'participants count must expose a paired value input');
  ok(!byId('input-numerator') && !byId('input-denominator'),
    'participants count must not expose n/N or a rewriteable denominator');
  setValue('input-value', '25');
  setValue('basis', '核对基线人数。');
  const payload = await actAndCommit('save', 'fact-unrelated-20', function (fact) {
    fact.raw_value = '25';
    fact.normalized_value = '25';
  });
  ok(payload.edits.raw_value === '25' && payload.edits.normalized_value === 25
    && Object.keys(payload.edits).length === 2,
    'count payload must be a paired raw+normalized integer');
  const before = fetchLog.length;
  setValue('input-value', '20.5');
  await click('save');
  ok(fetchLog.length === before, 'non-integer count must not be posted');
  ok(statusText().indexOf('整数') >= 0, 'non-integer count must be reported');
  setValue('input-value', '');
  await click('save');
  ok(fetchLog.length === before, 'blank count must not be posted');
}

async function flowClearRestoreUndo() {
  await selectFact('fact-crude-rate');
  setValue('basis', '当前数值待重新核实。');
  let payload = await actAndCommit('clear', 'fact-crude-rate', function (fact) {
    fact.disclosure_state = 'user_cleared';
    fact.raw_value = null;
    fact.normalized_value = null;
    fact.numerator = null;
    fact.denominator = null;
  });
  ok(payload.operation === 'save' && payload.edits.numerator === null
    && Object.keys(payload.edits).length === 1,
    'clear must send exactly a null effective count through the service');
  const cleared = detailText();
  ok(fieldValue('当前状态') === '用户清除，待重新核实',
    'cleared state label must read 用户清除，待重新核实');
  ok(fieldValue('当前值') === '用户清除，待重新核实',
    'cleared current value must read 用户清除，待重新核实');
  ok(cleared.indexOf('未公开') < 0 && cleared.indexOf('None') < 0,
    'cleared fact must not read 未公开 or None');
  ok(cleared.indexOf('34/62例受试者发生任何TEAE') >= 0,
    'original source quote must stay visible after clear');
  ok(cleared.indexOf('fact-crude-rate') >= 0, 'selection retained after clear');
  // Restore through the same n/N control.
  setValue('input-numerator', '24');
  setValue('input-denominator', '62');
  payload = await actAndCommit('save', 'fact-crude-rate', function (fact) {
    fact.disclosure_state = 'reported_value';
    fact.raw_value = '38.7096774194% (24/62)';
    fact.normalized_value = '38.7096774194';
    fact.numerator = 24;
    fact.denominator = 62;
  });
  ok(payload.edits.numerator === 24 && payload.edits.denominator === 62, 'restore payload');
  payload = await actAndCommit('undo', 'fact-crude-rate', function (fact) {
    fact.disclosure_state = 'user_cleared';
    fact.raw_value = null;
    fact.normalized_value = null;
    fact.numerator = null;
    fact.denominator = null;
  });
  ok(payload.operation === 'undo', 'undo operation must be sent');
  ok(Object.keys(payload.edits).length === 0, 'undo must send empty edits');
  ok(fieldValue('当前值') === '用户清除，待重新核实',
    'undo must refresh to the previous effective state');
}

async function flowFailureKeepsState() {
  await selectFact('fact-crude-rate');
  setValue('input-numerator', '12');
  setValue('input-denominator', '80');
  setValue('basis', '失败写入不得改变当前状态。');
  const revisionBefore = serverRevision;
  const versionBefore = serverFacts['fact-crude-rate'].fact_version_id;
  responder = function () {
    return { ok: false, status: 409, body: { error: '版本冲突：当前事实已被另一标签页更新' } };
  };
  await click('save');
  ok(statusText().indexOf('版本冲突') >= 0, 'conflict must be shown');
  responder = function () {
    return commit('fact-crude-rate', function (fact) {
      fact.raw_value = '15% (12/80)';
      fact.normalized_value = '15.0';
      fact.numerator = 12;
      fact.denominator = 80;
    });
  };
  await click('save');
  const payload = lastPayload();
  ok(payload.expected_revision === revisionBefore,
    'a failed write must not advance the expected revision');
  ok(payload.target.fact_version_id === versionBefore,
    'a failed write must not change the target version');
}

async function flowEstimate() {
  await selectFact('fact-b-estimated-efficacy');
  ok(byId('input-value') && byId('input-normalized'),
    'estimate must expose paired raw+normalized controls');
  ok(!byId('input-numerator') && !byId('input-denominator'),
    'estimate must never be edited as n/N even though counts exist');
  ok(detailText().indexOf('82.3%') >= 0, 'estimate current value must render');
  setValue('input-value', '80.1%');
  setValue('input-normalized', '80.1');
  setValue('basis', '依据原始报告复核模型估计结果。');
  const payload = await actAndCommit('save', 'fact-b-estimated-efficacy', function (fact) {
    fact.raw_value = '80.1%';
    fact.normalized_value = '80.1';
  });
  ok(payload.edits.raw_value === '80.1%' && payload.edits.normalized_value === 80.1
    && Object.keys(payload.edits).length === 2,
    'estimate payload must pair text and normalized number');
  let before = fetchLog.length;
  setValue('input-normalized', '');
  await click('save');
  ok(fetchLog.length === before, 'blank normalized value must not be posted as zero');
  ok(statusText().indexOf('不能为空') >= 0, 'blank normalized value must be reported');
  setValue('input-normalized', '0');
  const zero = await actAndCommit('save', 'fact-b-estimated-efficacy', function (fact) {
    fact.raw_value = '0%';
    fact.normalized_value = '0';
  });
  ok(zero.edits.normalized_value === 0, 'zero must be a real value');
  const cleared = await actAndCommit('clear', 'fact-b-estimated-efficacy', function (fact) {
    fact.disclosure_state = 'user_cleared';
    fact.raw_value = null;
    fact.normalized_value = null;
  });
  ok(cleared.edits.normalized_value === null && Object.keys(cleared.edits).length === 1,
    'estimate clear must null the effective numeric value');
  ok(detailText().indexOf('用户清除，待重新核实') >= 0, 'cleared estimate label');
}

async function flowSample() {
  await selectFact('fact-c-threshold');
  ok(byId('input-value'), 'sample must expose the paired integer value input');
  ok(!byId('input-threshold-operator') && !byId('input-denominator'),
    'sample must not be edited as threshold or n/N just because the axis carries one');
  ok(byId('input-value').value === '740', 'sample must start from the current number');
  setValue('input-value', '0');
  setValue('basis', '样本量按当前登记复核。');
  const zero = await actAndCommit('save', 'fact-c-threshold', function (fact) {
    fact.raw_value = '0';
    fact.normalized_value = '0';
    fact.threshold_value = 0;
  });
  ok(zero.edits.raw_value === '0' && zero.edits.normalized_value === 0,
    'zero sample must be sent as 0');
  const before = fetchLog.length;
  setValue('input-value', '');
  await click('save');
  ok(fetchLog.length === before, 'blank sample must not be posted');
  ok(statusText().indexOf('不能为空') >= 0, 'blank sample must be reported');
  setValue('input-value', '9007199254740993');
  await click('save');
  ok(fetchLog.length === before, 'unsafe integer sample must not be posted');
  ok(statusText().indexOf('整数') >= 0, 'unsafe integer sample must be reported');
  setValue('input-value', '500');
  const payload = await actAndCommit('save', 'fact-c-threshold', function (fact) {
    fact.raw_value = '500';
    fact.normalized_value = '500';
    fact.threshold_value = 500;
  });
  ok(payload.edits.raw_value === '500' && payload.edits.normalized_value === 500,
    'sample payload must pair text and integer');
  const cleared = await actAndCommit('clear', 'fact-c-threshold', function (fact) {
    fact.disclosure_state = 'user_cleared';
    fact.raw_value = null;
    fact.normalized_value = null;
    fact.threshold_value = null;
  });
  ok(cleared.edits.normalized_value === null,
    'sample clear must null the effective numeric value');
}

async function flowHostile() {
  const ids = Object.keys(envelope.facts);
  const factId = ids.find(function (id) {
    return String(envelope.facts[id].drug_name).indexOf('</script>') >= 0;
  }) || ids[0];
  const fact = envelope.facts[factId];
  for (const field of ['drug_name', 'source_quote', 'source_locator']) {
    ok(typeof fact[field] === 'string' && fact[field].length > 0,
      'hostile fixture must carry ' + field);
  }
  await selectFact(factId);
  const text = detailText();
  for (const field of ['drug_name', 'source_quote', 'source_locator']) {
    ok(text.indexOf(fact[field]) >= 0, field + ' must render as text');
  }
  ok(textOf(byId('fact-list')).indexOf(fact.drug_name) >= 0,
    'hostile name must render as list text');
  ok(globalThis.__INJECTED === undefined, 'hostile content must not execute');
  ok(globalThis.__LOCATOR === undefined, 'hostile locator must not execute');
  ok(!byId('pwned'), 'hostile content must not create elements');
}

async function flowNativeChoices() {
  const items = listItems();
  ok(items.length === Object.keys(envelope.facts).length, 'all facts reachable');
  for (const item of items) {
    const button = walk(item).find(el => el.tagName === 'button');
    ok(button && button.type === 'button', 'fact choice must be a native keyboard button');
  }
  ok(fieldValue('接线标识').indexOf('fact-crude-rate') >= 0,
    'URL fact selection must open the actual fact without guessing a fixture default');
  await selectFact('fact-crude-rate');
  ok(byId('detail').hidden === false, 'choice opens real detail');
  ok(globalThis.__focused && globalThis.__focused.tagName === 'button'
    && textOf(globalThis.__focused).indexOf('fact-crude-rate') >= 0,
    'selection redraw must return focus to the real fact choice, not the body');
  globalThis.__focused = byId('search');
  setValue('search', 'fact-crude-rate');
  await fire(byId('search'), 'input');
  ok(globalThis.__focused === byId('search'),
    'search input event must not be confused with explicit choice focus restoration');
}

const FLOWS = {
  native_choices: [flowNativeChoices],
  base: [
    flowListAndSelection,
    flowHumanAndStateFields,
    flowRatePayloadsRefreshed,
    flowThreshold,
    flowCount,
    flowClearRestoreUndo,
    flowFailureKeepsState,
  ],
  estimate: [flowListAndSelection, flowEstimate],
  sample: [flowSample],
  hostile: [flowHostile],
};

if (CASE === 'native_choices') globalThis.location = { search: '?fact=fact-crude-rate' };
new Function(PAGE_SCRIPT)();

(async function () {
  const flows = FLOWS[CASE];
  ok(flows, 'unknown case ' + CASE);
  for (const item of flows) await flow(item.name, item);
  if (failures > 0) {
    console.error('NODE-SUMMARY ' + CASE + ' failed=' + failures);
    process.exit(1);
  }
  console.log('NODE-OK ' + CASE);
})();
"""
