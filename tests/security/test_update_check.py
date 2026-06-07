"""Adversarial regression tests for the update check (mia.gui.updates).

Covers the audit's A6 (response size cap), A7 (no HTTPS->HTTP downgrade on
redirect), and A8 (version must be a sane string). See docs/SECURITY-AUDIT.md.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading

import pytest

from mia.gui import updates


def _serve_file(tmp_path, payload_bytes) -> str:
    f = tmp_path / "version.json"
    f.write_bytes(payload_bytes)
    return f.as_uri()


# ---- A6: response size cap --------------------------------------------------

def test_oversized_response_refused(tmp_path):
    blob = b'{"version":"1.0.0"' + b" " * (200 * 1024) + b"}"
    url = _serve_file(tmp_path, blob)
    with pytest.raises(Exception):
        updates.check(url=url)


# ---- A8: hostile version types/shapes --------------------------------------

@pytest.mark.parametrize("payload", [
    {"version": [1, 2, 3]},
    {"version": {"a": 1}},
    {"version": 1.5},
    {"version": True},
    {"version": "; rm -rf /"},
    {"version": "9" * 5000},
    {"notversion": "1.0.0"},
    [1, 2, 3],
])
def test_bad_version_payloads_raise(tmp_path, payload):
    url = _serve_file(tmp_path, json.dumps(payload).encode())
    with pytest.raises(Exception):
        updates.check(url=url)


def test_good_version_accepted(tmp_path):
    url = _serve_file(tmp_path, json.dumps({"version": "99.0.0"}).encode())
    assert updates.check(url=url).newer


# ---- A7: HTTPS->HTTP downgrade on redirect is refused ----------------------

def test_redirect_to_http_refused():
    class Redirector(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/x.json")
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), Redirector)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        with pytest.raises(Exception):
            updates.check(url=f"http://127.0.0.1:{port}/v.json")
    finally:
        srv.shutdown()
        srv.server_close()


# ---- parse_version stays total + monotonic (no TypeError/inversion) --------

def test_parse_version_never_raises_and_is_monotonic():
    for s in ["", "x", "beta-9", "999999999999999999.0.0", "0.1.2.99", None]:
        updates.parse_version(s)  # must not raise
    assert updates.parse_version("0.0.1") < updates.parse_version("0.1.2")
