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
import urllib.request
from dataclasses import dataclass
from typing import Tuple

from .. import __version__

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


def check(url: str = VERSION_URL,
          timeout: float = TIMEOUT_SECONDS) -> UpdateResult:
    """Fetch the published version file and compare. Raises on any network or
    parse failure — callers report 'couldn't check' and move on."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "MIA-Toolkit"})  # deliberately versionless
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    latest = str(data["version"])
    return UpdateResult(
        current=__version__,
        latest=latest,
        newer=parse_version(latest) > parse_version(__version__),
    )
