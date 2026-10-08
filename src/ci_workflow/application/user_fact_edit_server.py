"""Strict, on-demand loopback editor for :mod:`user_fact_edit`.

The server has no wildcard CORS, file URL, shell, filesystem-path, or multipart upload
surface. Every write requires an exact loopback Host/Origin pair, a SameSite session,
and a per-session CSRF token.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import secrets
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from ci_workflow.application.delivered_artifacts import _ordinary
from ci_workflow.application.latest_delivery import CurrentDeliveryBundle, current_bundle_sha256
from ci_workflow.application.user_fact_edit import (
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveConflictError,
    UserFactSaveError,
    current_delivery_lock,
)
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.renderers.portal.report_b import ReportBPortalData, _b_source_view_row

_MAX_BODY = 64 * 1024
_WEB_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}


def _report_links(current: CurrentDeliveryBundle) -> list[dict[str, str]]:
    generation = current_bundle_sha256(current)
    return [
        {"report": item.report, "href": f"/reports/{generation}/{item.report}/overview.html"}
        for item in current.reports
        if "overview.html" in item.file_hashes
    ]


def _edit_context(
    service: UserFactEditService,
    current: CurrentDeliveryBundle,
    report: str,
) -> dict[str, Any]:
    item = next(item for item in current.reports if item.report == report)
    data_b = None
    if report == "B":
        if item.builder_input_relative_path is None:
            raise ValueError("B编辑导航缺少已绑定输入")
        source = service.project_root / item.builder_input_relative_path
        _ordinary(service.project_root, source)
        data_b = ReportBPortalData.model_validate_json(source.read_bytes())
    bindings = []
    for fact_id, fact in service.current_facts().items():
        declarations = fact.get("consumer_bindings", ())
        if not isinstance(declarations, (list, tuple)):
            raise ValueError("事实消费者绑定无法核验")
        for declaration in declarations:
            binding = ActiveFactBinding.model_validate(declaration)
            if binding.report != report:
                continue
            row_id = binding.row_id
            if data_b is not None:
                row_id = _b_source_view_row(data_b, binding.collection, row_id)["row_id"]
            bindings.append(
                {"collection": binding.collection, "row_id": row_id, "fact_id": fact_id}
            )
    return {
        "revision": current.revision,
        "generation": current_bundle_sha256(current),
        "report": report,
        "bindings": bindings,
    }


def _safe_json(payload: object) -> str:
    """JSON for an inline data script: no hostile byte can close a tag or entity."""
    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


_EDITOR_TEMPLATE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>事实修订</title><style>
*{box-sizing:border-box}
body{font:18px/1.4 "Microsoft YaHei","PingFang SC",Arial,sans-serif;
margin:24px;color:#0F1115;background:#FBFCFD}
h1{font-size:32px;margin:0 0 .6rem}
h2{font-size:24px;margin:.2rem 0 .6rem}
#report-links{display:flex;flex-wrap:wrap;gap:16px;margin:0 0 16px}
a{color:#404040;text-decoration:underline;text-underline-offset:3px}
a:focus-visible,button:focus-visible{outline:2px solid #C00000;outline-offset:3px}
#status{padding:.6rem .75rem;background:#f3f6f8;border-radius:8px;margin:0 0 1rem}
main{display:grid;grid-template-columns:minmax(17rem,23rem) 1fr;gap:1rem;align-items:start}
section{min-width:0;border:1px solid rgba(190,178,161,.45);border-radius:18px;padding:16px;
background:linear-gradient(135deg,rgba(255,253,251,.62),
rgba(255,251,242,.55) 48%,rgba(255,245,228,.5));
box-shadow:0 5px 18px rgba(15,17,21,.07)}
input,select,textarea{font:inherit;padding:.35rem .5rem;border:1px solid #aab6c0;
border-radius:6px;width:100%}
#fact-list{list-style:none;margin:.6rem 0 0;padding:0;max-height:62vh;overflow:auto}
#fact-list li{padding:.45rem .5rem;border-bottom:1px solid #eef2f5;cursor:pointer}
#fact-list li span{display:block}
#fact-list button{width:100%;text-align:left;background:transparent;color:inherit;margin:0}
#fact-list button:focus-visible{outline:2px solid #C00000;outline-offset:2px}
.wiring{color:#64676B;font-size:16px;overflow-wrap:anywhere}
label{display:block;margin:.5rem 0}
button{font:inherit;padding:.45rem .9rem;margin-right:.5rem;background:#FF9900;color:#0F1115;
border:0;border-radius:8px}
dl{display:grid;grid-template-columns:auto 1fr;gap:.25rem .8rem;margin:.5rem 0}
dt{color:#5c6b7a}dd{margin:0;overflow-wrap:anywhere}
#controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(20rem,1fr));gap:0 16px}
#result{white-space:pre-wrap;overflow-wrap:anywhere;font-size:16px;color:#404040}
</style></head><body>
<h1>当前事实修订</h1>
<p id="status" role="status">正在读取当前 revision…</p>
<nav id="report-links" aria-label="返回当前报告"></nav>
<main>
<section id="selector"><label for="search">搜索事实（药物/研究/终点/标识）</label>
<input id="search" type="search" autocomplete="off" placeholder="输入关键词筛选">
<ul id="fact-list"></ul></section>
<section id="detail" hidden><h2>事实详情</h2>
<dl id="detail-fields"></dl>
<div id="controls"></div>
<label>用户依据<textarea id="basis" rows="2"
placeholder="写明本次修订的用户依据"></textarea></label>
<p><button id="save" type="button">保存当前修订</button>
<button id="clear" type="button">清除当前数值</button>
<button id="undo" type="button">撤销上一版</button></p>
<pre id="result"></pre></section>
</main>
<script id="facts" type="application/json">__FACTS_JSON__</script>
<script id="editor">
(function () {
  'use strict';
  const CLEARED_LABEL = '用户清除，待重新核实';
  const envelope = JSON.parse(document.getElementById('facts').textContent);
  const csrf = document.querySelector('meta[name=csrf]').content;
  const statusEl = document.getElementById('status');
  const searchEl = document.getElementById('search');
  const listEl = document.getElementById('fact-list');
  const detailEl = document.getElementById('detail');
  const fieldsEl = document.getElementById('detail-fields');
  const controlsEl = document.getElementById('controls');
  const basisEl = document.getElementById('basis');
  const resultEl = document.getElementById('result');
  const state = {
    project_id: envelope.project_id,
    revision: envelope.revision,
    facts: envelope.facts,
    selected: null,
  };
  function renderReportLinks(links) {
    const nav = document.getElementById('report-links');
    if (!nav) return;
    nav.replaceChildren();
    const labels = { A: '竞品全景台', B: '临床结果证据室', C: '试验设计图谱' };
    (links || []).forEach(function (item) {
      const link = document.createElement('a');
      link.href = item.href;
      link.textContent = '返回' + labels[item.report];
      nav.appendChild(link);
    });
  }
  renderReportLinks(envelope.report_links);
  let editor = null;
  const requestedFact = new URLSearchParams(
    typeof location === 'undefined' ? '' : location.search
  ).get('fact');
  if (requestedFact && Object.prototype.hasOwnProperty.call(state.facts, requestedFact)) {
    state.selected = requestedFact;
  }

  function cleared(fact) {
    return fact.disclosure_state === 'user_cleared'
      || Boolean(fact.user_edit && fact.user_edit.cleared === true);
  }
  function show(value) {
    return value === null || value === undefined || value === '' ? '—' : String(value);
  }
  function stateLabel(fact) {
    if (cleared(fact)) return CLEARED_LABEL;
    if (fact.review_state === 'user_modified') return '用户修订，未独立复核';
    return '来源登记值（尚未修订）';
  }
  function currentValue(fact) {
    if (cleared(fact)) return CLEARED_LABEL;
    if (fact.raw_value !== null && fact.raw_value !== undefined && fact.raw_value !== '') {
      return String(fact.raw_value);
    }
    if (fact.normalized_value !== null && fact.normalized_value !== undefined
        && fact.normalized_value !== '') {
      return String(fact.normalized_value);
    }
    return '暂无当前数值';
  }
  function human(fact) {
    return {
      drug: show(fact.drug_name || fact.product_id),
      study: show(fact.trial_id)
        + (fact.registry_id ? '（' + String(fact.registry_id) + '）' : ''),
      arm: show(fact.arm || fact.group_id || fact.cohort_id),
      endpoint: show(fact.endpoint_definition || fact.event_definition),
      time: show(fact.timepoint || fact.period),
      unit: show(fact.unit || fact.normalized_unit),
    };
  }
  function declarations(fact) {
    return Array.isArray(fact.consumer_bindings) ? fact.consumer_bindings : [];
  }
  function kindOf(fact) {
    const sample = declarations(fact).some(function (binding) {
      return Boolean(binding) && binding.report === 'C'
        && binding.collection === 'observations'
        && binding.endpoint_definition === 'planned_or_actual_sample_size';
    });
    if (sample) return 'sample';
    const form = String(fact.statistical_form || '');
    const measure = String(fact.measure_object || '');
    if (form === 'threshold') return 'threshold';
    if (form === 'crude_rate' && measure === 'participants') return 'rate';
    if (form === 'count' && measure === 'participants') return 'count';
    return 'scalar';
  }
  function searchText(fact) {
    const parts = [
      fact.fact_id, fact.field_id, fact.drug_name, fact.product_id, fact.trial_id,
      fact.registry_id, fact.arm, fact.group_id, fact.cohort_id, fact.endpoint_definition,
      fact.event_definition, fact.unit, fact.normalized_unit, fact.source_quote,
    ];
    return parts.filter(Boolean).join(' ').toLowerCase();
  }
  function summary(fact) {
    const parts = human(fact);
    return parts.drug + ' · ' + parts.study + ' · ' + parts.endpoint;
  }
  function clearNode(node) {
    node.replaceChildren();
    node.textContent = '';
  }
  function addRow(label, value) {
    const term = document.createElement('dt');
    term.textContent = label;
    const detail = document.createElement('dd');
    detail.textContent = value;
    fieldsEl.appendChild(term);
    fieldsEl.appendChild(detail);
  }
  function addInput(id, labelText, value, integer) {
    const label = document.createElement('label');
    label.textContent = labelText + ' ';
    const input = document.createElement('input');
    input.id = id;
    input.value = value;
    if (integer) input.inputMode = 'numeric';
    label.appendChild(input);
    controlsEl.appendChild(label);
    return input;
  }
  function readText(input, label) {
    const text = String(input.value).trim();
    if (text === '') throw new Error(label + '不能为空');
    return text;
  }
  function readNumber(input, label) {
    const text = String(input.value).trim();
    if (text === '') throw new Error(label + '不能为空');
    const value = Number(text);
    if (!Number.isFinite(value)) throw new Error(label + '必须是有限数值');
    return value;
  }
  function readInteger(input, label, minimum) {
    const text = String(input.value).trim();
    if (text === '') throw new Error(label + '不能为空');
    const value = Number(text);
    if (!Number.isSafeInteger(value) || String(value) !== text) {
      throw new Error(label + '必须是不带单位的整数');
    }
    if (value < minimum) throw new Error(label + '不得小于' + minimum);
    return value;
  }
  function numericText(value) {
    return value === null || value === undefined ? '' : String(value);
  }
  function buildEditor(fact) {
    const kind = kindOf(fact);
    clearNode(controlsEl);
    if (kind === 'rate') {
      const numerator = addInput('input-numerator', '事件人数 n',
        numericText(fact.numerator), true);
      const denominator = addInput('input-denominator', '分母 N（当前人数比例的独立输入）',
        numericText(fact.denominator), true);
      return {
        clear: function () { return { numerator: null }; },
        edits: function () {
          return {
            numerator: readInteger(numerator, '事件人数 n', 0),
            denominator: readInteger(denominator, '分母 N', 1),
          };
        },
      };
    }
    if (kind === 'threshold') {
      const operator = document.createElement('select');
      operator.id = 'input-threshold-operator';
      [['<', '<'], ['<=', '≤'], ['>', '>'], ['>=', '≥'], ['=', '=']].forEach(
        function (pair) {
          const option = document.createElement('option');
          option.value = pair[0];
          option.textContent = pair[1];
          operator.appendChild(option);
        });
      const current = String(fact.threshold_operator || '<');
      const allowed = ['<', '<=', '>', '>=', '='];
      operator.value = allowed.indexOf(current) >= 0 ? current : '<';
      const operatorLabel = document.createElement('label');
      operatorLabel.textContent = '运算符 ';
      operatorLabel.appendChild(operator);
      controlsEl.appendChild(operatorLabel);
      const value = addInput('input-threshold-value', '阈值',
        numericText(fact.threshold_value), false);
      const unit = addInput('input-threshold-unit', '单位',
        numericText(fact.threshold_unit || fact.unit), false);
      return {
        clear: function () { return { threshold_value: null }; },
        edits: function () {
          return {
            threshold_operator: operator.value,
            threshold_value: readNumber(value, '阈值'),
            threshold_unit: readText(unit, '单位'),
          };
        },
      };
    }
    if (kind === 'count' || kind === 'sample') {
      const label = kind === 'sample' ? '当前样本量（整数）' : '当前人数（整数）';
      const field = addInput('input-value', label, numericText(fact.normalized_value), true);
      return {
        clear: function () { return { normalized_value: null }; },
        edits: function () {
          const number = readInteger(field, label.replace('（整数）', ''), 0);
          return { raw_value: String(number), normalized_value: number };
        },
      };
    }
    const raw = addInput('input-value', '当前值文本', numericText(fact.raw_value), false);
    const normalized = addInput('input-normalized', '规范数值',
      numericText(fact.normalized_value), false);
    return {
      clear: function () { return { normalized_value: null }; },
      edits: function () {
        return {
          raw_value: readText(raw, '当前值文本'),
          normalized_value: readNumber(normalized, '规范数值'),
        };
      },
    };
  }
  function renderFields(fact) {
    clearNode(fieldsEl);
    const parts = human(fact);
    addRow('药物/产品', parts.drug);
    addRow('研究', parts.study);
    addRow('组别', parts.arm);
    addRow('终点/事件', parts.endpoint);
    addRow('时点', parts.time);
    addRow('单位', parts.unit);
    addRow('当前状态', stateLabel(fact));
    addRow('当前值', currentValue(fact));
    addRow('原始来源引文', show(fact.source_quote));
    addRow('来源定位', show(fact.source_locator));
    addRow('接线标识', String(fact.fact_id) + ' · ' + String(fact.fact_version_id));
  }
  function renderList(restoreFocus) {
    const query = String(searchEl.value || '').trim().toLowerCase();
    clearNode(listEl);
    let selectedChoice = null;
    Object.keys(state.facts).forEach(function (factId) {
      const fact = state.facts[factId];
      if (!fact || (query !== '' && searchText(fact).indexOf(query) < 0)) return;
      const item = document.createElement('li');
      const choice = document.createElement('button');
      choice.type = 'button';
      if (state.selected === factId) selectedChoice = choice;
      const head = document.createElement('span');
      head.textContent = (state.selected === factId ? '▶ ' : '') + summary(fact);
      const wiring = document.createElement('span');
      wiring.className = 'wiring';
      wiring.textContent = String(fact.fact_id) + ' · ' + String(fact.fact_version_id);
      choice.appendChild(head);
      choice.appendChild(wiring);
      item.appendChild(choice);
      item.addEventListener('click', function () {
        state.selected = factId;
        renderList(true);
        renderDetail();
      });
      listEl.appendChild(item);
    });
    if (restoreFocus === true && selectedChoice) selectedChoice.focus();
  }
  function renderDetail() {
    const fact = state.selected === null ? null : state.facts[state.selected];
    clearNode(resultEl);
    if (!fact) {
      detailEl.hidden = true;
      editor = null;
      return;
    }
    detailEl.hidden = false;
    renderFields(fact);
    editor = buildEditor(fact);
    const basis = fact.user_edit && fact.user_edit.basis;
    basisEl.value = basis === null || basis === undefined ? '' : String(basis);
  }
  async function submit(operation, editsFactory) {
    try {
      const fact = state.selected === null ? null : state.facts[state.selected];
      if (!fact) throw new Error('请先选择事实');
      const basis = String(basisEl.value || '').trim();
      if (basis === '') throw new Error('请填写用户依据');
      const payload = {
        schema_version: '1.0',
        request_id: 'browser-' + crypto.randomUUID(),
        project_id: state.project_id,
        expected_revision: state.revision,
        operation: operation,
        target: {
          fact_id: fact.fact_id,
          fact_version_id: fact.fact_version_id,
          entity_id: fact.entity_id,
          field_id: fact.field_id,
        },
        edits: editsFactory(),
        user_basis: basis,
        saved_by: 'browser-user',
        saved_at: new Date().toISOString(),
      };
      const response = await fetch('/api/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || '保存失败');
      if (data.refresh_required) {
        statusEl.textContent = data.message;
        resultEl.textContent = JSON.stringify(data.result, null, 2);
        ['save', 'clear', 'undo'].forEach(function (id) {
          document.getElementById(id).disabled = true;
        });
        return;
      }
      state.revision = data.current_revision === undefined ? data.revision : data.current_revision;
      state.facts = data.facts;
      renderReportLinks(data.report_links);
      renderList();
      renderDetail();
      resultEl.textContent = JSON.stringify(data.result, null, 2);
      statusEl.textContent = '当前 revision ' + state.revision + '；用户修订，未独立复核。';
    } catch (error) {
      statusEl.textContent = '操作未完成：'
        + String(error && error.message ? error.message : error);
    }
  }
  searchEl.addEventListener('input', renderList);
  document.getElementById('save').addEventListener('click', function () {
    return submit('save', function () { return editor.edits(); });
  });
  document.getElementById('clear').addEventListener('click', function () {
    return submit('save', function () { return editor.clear(); });
  });
  document.getElementById('undo').addEventListener('click', function () {
    return submit('undo', function () { return {}; });
  });
  statusEl.textContent = '当前 revision ' + state.revision
    + '；用户保存后不继承独立科学接受。';
  renderList();
  renderDetail();
})();
</script></body></html>"""


def _editor_page(
    *,
    facts: dict[str, dict[str, Any]],
    revision: int,
    project_id: str,
    report_links: list[dict[str, str]] | None = None,
) -> bytes:
    """Render the compact editor over the current facts.

    All fact and identity data is embedded through one escaped JSON envelope and
    later written to the DOM with ``textContent`` only; project identity takes
    the same path as every other fact field.
    """
    envelope = _safe_json(
        {
            "project_id": project_id,
            "revision": revision,
            "facts": facts,
            "report_links": report_links or [],
        }
    )
    return _EDITOR_TEMPLATE.replace("__FACTS_JSON__", envelope, 1).encode("utf-8")


class LoopbackEditServer:
    def __init__(self, service: UserFactEditService, *, port: int = 0) -> None:
        self.service = service
        self._sessions: dict[str, str] = {}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "CIWorkflowLoopback/1.0"

            def log_message(self, _format: str, *args: object) -> None:
                return

            def _host(self) -> str | None:
                expected = f"127.0.0.1:{owner.port}"
                return expected if self.headers.get("Host") == expected else None

            def _send(
                self,
                status: int,
                body: bytes,
                *,
                content_type: str,
                headers: dict[str, str] | None = None,
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                content_security_policy = (
                    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                )
                self.send_header("Content-Security-Policy", content_security_policy)
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                self.send_header("Referrer-Policy", "no-referrer")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                self._send(
                    status,
                    (json.dumps(payload, ensure_ascii=False) + "\n").encode(),
                    content_type="application/json; charset=utf-8",
                )

            def _session(self) -> tuple[str, str] | None:
                cookie = SimpleCookie()
                try:
                    cookie.load(self.headers.get("Cookie", ""))
                except Exception:
                    return None
                morsel = cookie.get("session")
                if morsel is None:
                    return None
                token = owner._sessions.get(morsel.value)
                return (morsel.value, token) if token is not None else None

            def _authorize_write(self) -> bool:
                host = self._host()
                if host is None:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Host不受信任"})
                    return False
                if self.headers.get("Origin") != f"http://{host}":
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Origin不受信任"})
                    return False
                session = self._session()
                csrf = self.headers.get("X-CSRF-Token", "")
                if (
                    session is None
                    or not csrf.isascii()
                    or not secrets.compare_digest(session[1], csrf)
                ):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "会话或CSRF校验失败"})
                    return False
                return True

            def do_GET(self) -> None:  # noqa: N802
                if self._host() is None:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Host不受信任"})
                    return
                path = urlsplit(self.path).path
                if path.startswith("/reports/"):
                    self._report(path)
                    return
                if path == "/favicon.ico":
                    self._send(HTTPStatus.NO_CONTENT, b"", content_type="image/x-icon")
                    return
                if path != "/":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                    return
                try:
                    with current_delivery_lock(owner.service.project_root):
                        current = owner.service.read_current_delivery()
                        expected_generation = parse_qs(
                            urlsplit(self.path).query,
                            keep_blank_values=True,
                        ).get("generation")
                        if expected_generation is not None and expected_generation != [
                            current_bundle_sha256(current)
                        ]:
                            self._json(
                                HTTPStatus.CONFLICT, {"error": "报告版本已变化，请重新打开当前报告"}
                            )
                            return
                        page = _editor_page(
                            facts=owner.service.current_facts(),
                            revision=current.revision,
                            project_id=current.project_id,
                            report_links=_report_links(current),
                        )
                except (UserFactSaveError, OSError, ValueError):
                    self._json(HTTPStatus.CONFLICT, {"error": "当前交付未能完整核验"})
                    return
                session_id = secrets.token_urlsafe(32)
                csrf = secrets.token_urlsafe(32)
                owner._sessions[session_id] = csrf
                marker = b"<head>"
                page = page.replace(
                    marker,
                    marker + f'<meta name="csrf" content="{html.escape(csrf)}">'.encode(),
                    1,
                )
                self._send(
                    HTTPStatus.OK,
                    page,
                    content_type="text/html; charset=utf-8",
                    headers={
                        "Set-Cookie": f"session={session_id}; HttpOnly; SameSite=Strict; Path=/",
                        "X-CSRF-Token": csrf,
                    },
                )

            def _report(self, path: str) -> None:
                if self._session() is None:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "请先打开事实编辑页建立会话"})
                    return
                match = re.fullmatch(r"/reports/([0-9a-f]{64})/([ABC])/(.+)", unquote(path))
                if match is None:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                    return
                generation, report, relative = match.groups()
                parts = relative.split("/")
                if (
                    any(part in {"", ".", ".."} for part in parts)
                    or any(char in relative for char in ("%", "\\", "\x00"))
                    or Path(relative).suffix not in _WEB_TYPES
                ):
                    self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                    return
                try:
                    # ponytail: whole-current validation under the existing lock;
                    # profile before adding a validated-generation cache.
                    with current_delivery_lock(owner.service.project_root):
                        current = owner.service.read_current_delivery()
                        if current_bundle_sha256(current) != generation:
                            self._json(
                                HTTPStatus.CONFLICT,
                                {"error": "报告版本已变化，请从编辑页打开当前报告"},
                            )
                            return
                        item = next(
                            (item for item in current.reports if item.report == report), None
                        )
                        if item is None or relative not in item.file_hashes:
                            self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                            return
                        target = owner.service.project_root / item.site_relative_path / relative
                        _ordinary(owner.service.project_root, target)
                        body = target.read_bytes()
                        if hashlib.sha256(body).hexdigest() != item.file_hashes[relative]:
                            raise ValueError("报告文件摘要已变化")
                        if relative.endswith(".html"):
                            if b"<head>" not in body:
                                raise ValueError("报告缺少导航注入位置")
                            context = _safe_json(_edit_context(owner.service, current, report))
                            marker = '<script id="ci-current-edit" type="application/json">'
                            body = body.replace(
                                b"<head>",
                                b"<head>" + (marker + context + "</script>").encode("utf-8"),
                                1,
                            )
                    self._send(HTTPStatus.OK, body, content_type=_WEB_TYPES[Path(relative).suffix])
                except (UserFactSaveError, OSError, ValueError):
                    self._json(HTTPStatus.CONFLICT, {"error": "当前交付未能完整核验"})

            def do_POST(self) -> None:  # noqa: N802
                path = urlsplit(self.path).path
                if path != "/api/save":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                    return
                if not self._authorize_write():
                    return
                if self.headers.get_content_type() != "application/json":
                    self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "仅接受JSON"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    length = -1
                if length < 0 or length > _MAX_BODY:
                    self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "请求过大"})
                    return
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw)
                    if not isinstance(payload, dict):
                        raise ValueError("top level")
                    command = UserFactSaveCommand.model_validate(payload)
                    result = owner.service.save(command)
                except UserFactSaveConflictError as error:
                    self._json(HTTPStatus.CONFLICT, {"error": str(error)})
                    return
                except (json.JSONDecodeError, ValueError, UserFactSaveError) as error:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                    return
                # The committed save is answered with the same fresh facts and
                # revision a reload would read, so the editor can refresh in
                # place while retaining its selected fact.
                saved = result.model_dump(mode="json")
                response: dict[str, Any] = {**saved, "result": saved}
                try:
                    with current_delivery_lock(owner.service.project_root):
                        facts = owner.service.current_facts()
                        current = owner.service.read_current_delivery()
                        response.update(
                            current_revision=current.revision,
                            facts=facts,
                            report_links=_report_links(current),
                            refresh_required=False,
                        )
                except (UserFactSaveError, OSError, ValueError):
                    # The transaction already committed. A read failure must
                    # not invite a second save with a new request identity.
                    response.update(
                        current_revision=None,
                        facts=None,
                        refresh_required=True,
                        message="已保存，但当前数据未能重新载入。请重开编辑页核对，不要重复保存。",
                    )
                self._json(HTTPStatus.OK, response)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None

    def start(self) -> LoopbackEditServer:
        if self._thread is None:
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        return self

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> LoopbackEditServer:
        return self.start()

    def __exit__(self, *_args: object) -> None:
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="启动严格loopback事实编辑界面")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    server = LoopbackEditServer(UserFactEditService(args.project), port=args.port)
    print(f"http://127.0.0.1:{server.port}", flush=True)
    try:
        server._httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server._httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
