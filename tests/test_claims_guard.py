"""Claims guard for the public site and the procurement kit (PRODUCTION-READINESS G3).

Every claim the website or the kit makes must map to evidence. This test fails
when a known-stale or never-allowed phrase comes back into the sources the site
and the kit PDFs are built from:

- stale signing claims (SignPath was rejected on 2026-06-10; macOS has been
  notarized since v0.1.5; "signed installers arrive with the first full
  release" was retired);
- certification / regulatory-approval claims we have no basis for (no HIPAA
  "certified/compliant", no FDA/HSA/COFEPRIS approval or registration, no
  ISO/SOC certificate);
- the es-MX wording that INSTITUTIONS-LAUNCH-READINESS R5 forbids until an
  abogado sanitario confirms it.

Editor notes are skipped because they list the forbidden phrases on purpose:
keys starting with "_" in the JSON data files, and the `note:` line in a
Markdown file's front matter. If a phrase here becomes true
(e.g. a real certification), remove its pattern in the same PR that adds the
evidence.
"""

from __future__ import annotations

import glob
import json
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORBIDDEN = [
    # Stale signing claims.
    (r"first full release", "retired homepage note; see R6"),
    (r"final approval", "Windows signing is not in an approval stage"),
    (r"approval pending", "no signing approval is pending"),
    (r"\bsignpath\b", "SignPath rejected the project on 2026-06-10"),
    (r"notari[sz]ation (is )?pending", "macOS is notarized since v0.1.5"),
    # Certification / regulatory claims without a basis.
    (r"hipaa[- ](certified|compliant)", "no HIPAA certification exists; say 'supports your HIPAA program'"),
    (r"\b(fda|hsa|cofepris)[- ](approved|cleared|certified|registered)\b", "no regulator approval"),
    (r"(aprobad[oa]|certificad[oa]|registrad[oa]) (por|ante) (la )?cofepris", "no COFEPRIS approval (R5)"),
    (r"exento de registro sanitario", "implies we are a device with an exemption (R5)"),
    (r"cumple (con )?(la )?nom-024", "NOM-024 does not apply to us (R5)"),
    (r"no es un dispositivo m[eé]dico", "forbidden in es-MX until counsel confirms (R5)"),
    (r"cumplimiento normativo garantizado", "use 'soporte y documentación para sus procesos de cumplimiento' (R5)"),
    (r"garantiza (la )?integridad diagn[oó]stica", "forbidden (R5)"),
    (r"\b(iso ?27001|iso ?13485|soc ?2)\b", "we hold no ISO/SOC certificate"),
]


def _strings(obj, skip_notes=True):
    """Yield every string value in a JSON tree, skipping '_'-prefixed keys."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if skip_notes and isinstance(k, str) and k.startswith("_"):
                continue
            yield from _strings(v, skip_notes)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v, skip_notes)
    elif isinstance(obj, str):
        yield obj


def _drop_front_matter_notes(text):
    """Blank the `note:` editor line inside a leading `---` front-matter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        if lines[i].startswith("note:"):
            lines[i] = ""  # keep numbering so hit line numbers stay right
    return "\n".join(lines)


def _sources():
    """(relative path, text) for every public-claim source file."""
    json_globs = ["website/i18n/*.json", "website/markets/*.json", "website/kit/manifest.json"]
    text_globs = [
        "website/content/**/*.md",
        "website/templates/*.html",
        "scripts/procurement_pdf/content/**/*.md",
    ]
    out = []
    for g in json_globs:
        for p in sorted(glob.glob(os.path.join(REPO, g), recursive=True)):
            with open(p, encoding="utf-8") as f:
                out.append((os.path.relpath(p, REPO).replace(os.sep, "/"), "\n".join(_strings(json.load(f)))))
    for g in text_globs:
        for p in sorted(glob.glob(os.path.join(REPO, g), recursive=True)):
            with open(p, encoding="utf-8") as f:
                out.append((os.path.relpath(p, REPO).replace(os.sep, "/"), _drop_front_matter_notes(f.read())))
    return out


SOURCES = _sources()


def test_sources_found():
    # Guard against the globs silently matching nothing after a refactor.
    paths = {p for p, _ in SOURCES}
    assert any(p.startswith("website/i18n/") for p in paths)
    assert any(p.startswith("website/content/") for p in paths)
    assert any(p.startswith("scripts/procurement_pdf/content/") for p in paths)


@pytest.mark.parametrize("pattern,why", FORBIDDEN, ids=[p for p, _ in FORBIDDEN])
def test_no_stale_or_unbacked_claims(pattern, why):
    rx = re.compile(pattern, re.IGNORECASE)
    hits = []
    for path, text in SOURCES:
        for n, line in enumerate(text.splitlines(), 1):
            m = rx.search(line)
            if m:
                hits.append(f"{path}:{n}: …{line[max(0, m.start() - 40):m.end() + 40]}…")
    assert not hits, f"{why}:\n" + "\n".join(hits)
