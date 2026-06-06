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
import urllib.request
from dataclasses import dataclass
from typing import Tuple

from .. import __version__

try:
    import certifi  # bundled CA store — see _ssl_context()
except ImportError:  # source installs can rely on the interpreter's defaults
    certifi = None

VERSION_URL = "https://mia-toolkit.fritanga.co/version.json"
DOWNLOAD_PAGE = "https://mia-toolkit.fritanga.co/"
TIMEOUT_SECONDS = 5.0


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
    with urllib.request.urlopen(request, timeout=timeout,
                                context=_ssl_context()) as response:
        data = json.loads(response.read().decode("utf-8"))
    latest = str(data["version"])
    return UpdateResult(
        current=__version__,
        latest=latest,
        newer=parse_version(latest) > parse_version(__version__),
    )
