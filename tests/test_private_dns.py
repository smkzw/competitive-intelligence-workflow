"""Synthetic addresses only: no DNS/network/service mutation during tests."""

import json
import socket
import ssl
import subprocess

import pytest

from ciw.verify.transport import _PrivateHTTPSConnection, _tailscale_address


def test_dns_fallback_keeps_original_tls_host_and_is_scoped_to_the_expected_host(monkeypatch):
    calls, transport = [], {}
    marker = object()

    def create(address, timeout, source):
        calls.append(address)
        if address[0] == "example.tail000000.ts.net":
            raise socket.gaierror(8, "synthetic DNS failure")
        return marker

    monkeypatch.setattr(socket, "create_connection", create)
    monkeypatch.setattr("ciw.verify.transport._tailscale_address", lambda host: "100.64.0.9")
    connection = _PrivateHTTPSConnection(
        "example.tail000000.ts.net",
        expected_host="example.tail000000.ts.net",
        transport=transport,
        context=ssl.create_default_context(),
    )
    assert connection._create_connection((connection.host, 443), 10, None) is marker
    assert calls == [("example.tail000000.ts.net", 443), ("100.64.0.9", 443)]
    assert connection.host == "example.tail000000.ts.net" and connection._context.check_hostname
    assert connection._context.verify_mode == ssl.CERT_REQUIRED
    assert transport == {"dns_resolution": "tailscale-cli"}


@pytest.mark.parametrize(
    "bodies,ok", [(["100.64.0.9"], True), (["203.0.113.9"], False), (["100.64.0.9", "100.64.0.10"], False)]
)
def test_only_one_matching_private_dns_answer_is_accepted(monkeypatch, bodies, ok):
    monkeypatch.setattr("shutil.which", lambda name: "/synthetic/tailscale")
    doc = {
        "ResponseCode": "RCodeSuccess",
        "Answers": [{"Type": "TypeA", "Name": "example.tail000000.ts.net.", "Body": body} for body in bodies],
    }
    monkeypatch.setattr("subprocess.run", lambda *a, **k: subprocess.CompletedProcess(a, 0, json.dumps(doc), ""))
    if ok:
        assert _tailscale_address("example.tail000000.ts.net") == bodies[0]
    else:
        with pytest.raises(OSError):
            _tailscale_address("example.tail000000.ts.net")
