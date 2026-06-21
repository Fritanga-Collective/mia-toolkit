"""User-initiated update check — the app's only network call, ever.

Fetches one static, first-party file (no query params, no identifiers, a
generic User-Agent without version) ONLY when the user explicitly clicks
"Check for Updates…". Compares against the running version and reports; the
app never downloads or installs anything — that stays a human act in the
browser. See the website privacy policy, which discloses exactly this.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Tuple

from .. import __version__

try:
    import certifi  # bundled CA store — see _ssl_context()
except ImportError:  # source installs can rely on the interpreter's defaults
    certifi = None

VERSION_URL = "https://miatools.tech/version.json"
DOWNLOAD_PAGE = "https://miatools.tech/"
TIMEOUT_SECONDS = 5.0
# version.json is a tiny static file; cap the read so a hostile/compromised
# endpoint can't stream gigabytes into memory.
MAX_RESPONSE_BYTES = 64 * 1024
# A well-formed version string we're willing to act on (digits-and-dots).
# Capped at 3 components to match what parse_version() actually compares — a
# 4th component would be silently ignored and could mask a real update.
_VERSION_RE = re.compile(r"^\d{1,9}(\.\d{1,9}){0,2}$")


class _NoHTTPDowngrade(urllib.request.HTTPRedirectHandler):
    """Allow redirects only when they stay on HTTPS. A compromised endpoint
    could otherwise 30x-redirect to plaintext http:// (or another scheme),
    dropping TLS on the follow-up fetch. (urllib already blocks file:/data:.)"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith("https://"):
            raise urllib.error.HTTPError(
                newurl, code, "refusing non-HTTPS redirect", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass
class UpdateResult:
    current: str
    latest: str
    newer: bool


def parse_version(text: str) -> Tuple[int, ...]:
    """'0.1.5' -> (0, 1, 5); tolerant of stray prefixes/suffixes."""
    parts = re.findall(r"\d+", text or "")
    return tuple(int(p) for p in parts[:3]) or (0,)


def _ssl_context() -> ssl.SSLContext:
    """CA-verified TLS context that also works in frozen (PyInstaller) apps.

    The bundled OpenSSL's compiled-in certificate path points at the *build*
    machine's Python install, which doesn't exist on user machines — so the
    default context fails every HTTPS request with CERTIFICATE_VERIFY_FAILED.
    certifi ships its own CA file inside the bundle; prefer it, fall back to
    the interpreter's defaults when running from source without certifi.
    """
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def check(url: str = VERSION_URL,
          timeout: float = TIMEOUT_SECONDS) -> UpdateResult:
    """Fetch the published version file and compare. Raises on any network or
    parse failure — callers report 'couldn't check' and move on."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "MIA-Toolkit"})  # deliberately versionless
    opener = urllib.request.build_opener(
        _NoHTTPDowngrade, urllib.request.HTTPSHandler(context=_ssl_context()))
    with opener.open(request, timeout=timeout) as response:
        # Read one byte past the cap to detect (and reject) oversized bodies.
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("version file is implausibly large — refusing")
    data = json.loads(raw.decode("utf-8"))
    latest = data.get("version") if isinstance(data, dict) else None
    if not isinstance(latest, str) or not _VERSION_RE.match(latest):
        raise ValueError(f"unexpected version value: {latest!r}")
    return UpdateResult(
        current=__version__,
        latest=latest,
        newer=parse_version(latest) > parse_version(__version__),
    )
