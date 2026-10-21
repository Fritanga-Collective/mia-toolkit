#!/usr/bin/env python3
"""Build the institutional procurement-kit PDFs (EN + es-MX).

Pipeline: vault Markdown (English, read-only) -> cleaned customer-facing
Markdown -> HTML (Carbon-foundations template) -> tagged PDF (WeasyPrint).

  * English is generated from the Obsidian vault license pack every run.
    The cleaned English Markdown is written to
    scripts/procurement_pdf/content/en/<key>.md so translators can diff it.
  * Spanish (es-MX) is a careful hand translation kept in the repo at
    scripts/procurement_pdf/content/es/<key>.md. Each file records the
    sha256 of the cleaned English it was translated from; the build warns
    (or fails with --strict) when the English has changed since.

Outputs: website/kit/<lang>/<filename>.pdf and website/kit/manifest.json.

Usage:
  python scripts/build_procurement_pdfs.py [--vault PATH] [--preview DIR] [--strict]
                                           [--stamp-translations]

The vault path defaults to $MIA_VAULT_LICENSE_PACK or the path below.
Requires: weasyprint, markdown (and pymupdf for --preview). On macOS,
WeasyPrint needs Pango from Homebrew (`brew install pango`).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

import markdown

# --------------------------------------------------------------------------
# Single-point settings
# --------------------------------------------------------------------------
# Header brand line. Swap here (one variable per language) if the brand changes.
BRAND = {
    "en": "MIA Tools – Clinics & Hospitals",
    "es": "MIA Tools – Clínicas y Hospitales",
}
DOC_VERSION = "1.0"
DOC_DATE = "2026-10-20"
SUPPORT_EMAIL = "support@miatools.tech"
SITE = "miatools.tech"

DEFAULT_VAULT = ("/Users/luis/obsidian/luigisrs_remote/Projects/mia-toolkit/"
                 "legal-finance/license-pack")

ROOT = Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "scripts" / "procurement_pdf"
CONTENT_DIR = TPL_DIR / "content"
OUT_DIR = ROOT / "website" / "kit"

# key -> vault source, output filenames and titles per language
DOCS = {
    "security": {
        "src": "SECURITY-ONEPAGER.md",
        "file": {"en": "mia-security-onepager-en.pdf", "es": "mia-ficha-seguridad-es.pdf"},
        "title": {"en": "Security One-Pager", "es": "Ficha de seguridad"},
    },
    "it-guide": {
        "src": "IT-DEPLOYMENT-GUIDE.md",
        "file": {"en": "mia-it-deployment-guide-en.pdf", "es": "mia-guia-instalacion-ti-es.pdf"},
        "title": {"en": "IT Deployment Guide", "es": "Guía de instalación para TI"},
    },
    "license-terms": {
        "src": "LICENSE-TERMS.md",
        "file": {"en": "mia-license-terms-en.pdf", "es": "mia-terminos-licencia-es.pdf"},
        "title": {"en": "Institutional License Terms", "es": "Términos de la licencia institucional"},
    },
    "certificate": {
        "src": "CERTIFICATE-TEMPLATE.md",
        "file": {"en": "mia-sample-certificate-en.pdf", "es": "mia-certificado-muestra-es.pdf"},
        "title": {"en": "Sample License Certificate", "es": "Certificado de licencia (muestra)"},
    },
}

UI = {
    "en": {
        "kit": "Procurement kit",
        "eyebrow": "MIA Toolkit · Procurement kit",
        "lang_name": "English (United States, Singapore)",
        "control": ["Document", "Version", "Date", "Language", "Pages"],
        "page": "Page", "of": "of",
        "footer": f"{SUPPORT_EMAIL} · {SITE}",
        "by_market": "By market",
    },
    "es": {
        "kit": "Documentos para Compras y TI",
        "eyebrow": "MIA Toolkit · Documentos para Compras y TI",
        "lang_name": "Español (México)",
        "control": ["Documento", "Versión", "Fecha", "Idioma", "Páginas"],
        "page": "Página", "of": "de",
        "footer": f"{SUPPORT_EMAIL} · {SITE}",
        "by_market": "Por mercado",
    },
}
ES_TRANSLATION_NOTE = "Traducción; en caso de discrepancia prevalece la versión en inglés."

WARNINGS: list[str] = []


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"WARNING: {msg}", file=sys.stderr)


# --------------------------------------------------------------------------
# Cleaning vault Markdown -> customer-facing Markdown
# --------------------------------------------------------------------------
INTERNAL_RE = re.compile(r"internal|remove before sending|TODO|FIXME|\bLuis\b", re.I)
DAGGER = "<sup>†</sup>"


def strip_frontmatter(md: str) -> tuple[dict, str]:
    meta: dict = {}
    m = re.match(r"\A---\n(.*?)\n---\n", md, re.S)
    if not m:
        return meta, md
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, md[m.end():]


def wikilink(m: re.Match) -> str:
    target, _, label = m.group(1).partition("|")
    return label or target.split("#")[0].replace("-", " ").title()


def clean_common(md: str) -> str:
    """Drop frontmatter, internal blockquotes, Related/Contact lines, rules,
    and render [[wikilinks]] as plain text. Fenced code is left untouched."""
    _, md = strip_frontmatter(md)
    out: list[str] = []
    lines = md.splitlines()
    i, fence = 0, False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(line)
            i += 1
            continue
        if fence:
            out.append(line)
            i += 1
            continue
        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i])
                i += 1
            if INTERNAL_RE.search(" ".join(block)):
                continue  # internal note: drop it
            out.extend(block)
            continue
        s = line.strip()
        if (s == "---" or re.match(r"^(Related|Contact|Support):", s)
                or re.match(r"^(- )?(TODO|FIXME)\b", s)):
            i += 1
            continue
        out.append(line)
        i += 1
    text = "\n".join(out)
    for w in re.findall(r"\[\[([^\]]+)\]\]", text):
        print(f"note: wikilink [[{w}]] rendered as plain text", file=sys.stderr)
    text = re.sub(r"\[\[([^\]]+)\]\]", wikilink, text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def split_sections(md: str) -> tuple[str, str, list[list[str]]]:
    """-> (h1 title, preamble, [[heading, body], ...]) on '## ' boundaries."""
    title, pre, sections, cur = "", [], [], None
    fence = False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if not fence and line.startswith("## "):
            cur = [line[3:].strip(), ""]
            sections.append(cur)
            continue
        if cur is None:
            pre.append(line)
        else:
            cur[1] += line + "\n"
    return title, "\n".join(pre).strip(), sections


def join_sections(sections) -> str:
    return "\n\n".join(f"## {h}\n\n{b.strip()}" for h, b in sections) + "\n"


def bullets(body: str) -> list[str]:
    """Top-level '- ' list items with continuation lines joined."""
    items: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif items and line.startswith("  ") and line.strip():
            items[-1] += " " + line.strip()
    return items


def section(sections, name: str):
    for s in sections:
        if s[0].lower().startswith(name.lower()):
            return s
    warn(f"expected section '{name}' not found in vault source")
    return None


def mark_verify(md: str) -> tuple[str, bool]:
    """Internal '(verify on Windows)' markers -> a customer-safe dagger note."""
    # "The X line is *(verify on Windows)*." -> "... is not yet tested by us on Windows†."
    md = re.sub(r"\bis\s+\*?\(verify on Windows\)\*?", "is not yet tested by us on Windows" + DAGGER,
                md, flags=re.I)
    new, n = re.subn(r"\s*\*?\(verify on Windows\)\*?", DAGGER, md, flags=re.I)
    n += md.count(DAGGER)
    return new, n > 0


# Per-document English transforms -------------------------------------------

def en_security(md: str) -> dict:
    title, pre, secs = split_sections(md)
    lead = pre.split("\n\n")
    df = section(secs, "Data flow")
    if df:
        df[1] = "{{FLOW}}\n"
    priv = section(secs, "Privacy")
    market = {}
    if priv:
        keep = []
        for it in bullets(priv[1]):
            m = re.match(r"\*\*(United States|Singapore|México|Mexico):\*\*\s*(.*)", it)
            if m:
                if m.group(1) in ("United States", "Singapore"):
                    market[m.group(1)] = m.group(2)
                continue  # Mexico wording lives only in the es-MX edition
            it = it.replace("**PDPA / HIPAA-adjacent framing:**",
                            "**Local processing under your controls:**")
            keep.append(it)
        priv[0] = "Privacy and regulatory framing"
        priv[1] = "\n".join(f"- {i}" for i in keep) + "\n\n{{MARKET}}\n"
        for k in ("United States", "Singapore"):
            if k not in market:
                warn(f"security one-pager: no '{k}' regulatory line found")
    body = join_sections(secs)
    mkt = "\n\n".join(f"#### {k}\n\n{v}" for k, v in market.items())
    return {"lead": "\n\n".join(lead), "body": body, "market": mkt}


def en_it_guide(md: str) -> dict:
    md, has_dagger = mark_verify(md)
    title, pre, secs = split_sections(md)
    pc = section(secs, "Post-install check")
    if pc and "after v0.1.13" not in pc[1]:
        # From the removed internal note: the headless flags ship after v0.1.13.
        pc[1] = pc[1].replace(
            "Both builds have headless flags",
            "Releases after v0.1.13 have headless flags (v0.1.13's `--selftest` "
            "performs an import check only)", 1)
    return {"lead": pre, "body": join_sections(secs), "dagger": has_dagger}


def en_license_terms(md: str) -> dict:
    title, pre, secs = split_sections(md)
    # Drop the internal draft/status line ("*Draft for counsel review...*").
    pre = "\n\n".join(p for p in pre.split("\n\n")
                      if not re.match(r"^\*Draft", p.strip()))
    rf = section(secs, "Refunds")
    if rf:
        text = " ".join(rf[1].split())
        text = re.sub(r"Full policy, in English, Spanish, Chinese, Malay and Tamil:.*$",
                      "The full refund policy is published in English, Spanish, Chinese, "
                      "Malay and Tamil; if the versions differ, the English version applies.",
                      text)
        sents = re.split(r"(?<=\.)\s+(?=[A-Z])", text)
        rf[1] = "\n".join(f"- {s}" for s in sents) + "\n"
    body = join_sections(secs).replace("licence", "license").replace("Licence", "License")
    return {"lead": pre.replace("licence", "license"), "body": body}


def en_certificate(md: str) -> dict:
    text = clean_common(md)
    plain = re.sub(r"<[^>]+>", "", text)
    stmt = next((p.strip() for p in plain.split("\n\n")
                 if p.strip().startswith("This certificate confirms")), "")
    if not stmt:
        warn("certificate: statement paragraph not found")
    issuer = re.search(r"\*\*Issued by\*\*\s*\n\s*\*\*([^*]+)\*\*", plain)
    return {"statement": " ".join(stmt.split()),
            "issuer": issuer.group(1).strip() if issuer else "Fritanga"}


EN_TRANSFORMS = {"security": en_security, "it-guide": en_it_guide,
                 "license-terms": en_license_terms}

# --------------------------------------------------------------------------
# Fixed per-language fragments (diagram, certificate, notes)
# --------------------------------------------------------------------------
FLOW = {
    "en": [("Imaging media", "CDs, USB folders, ZIP downloads (source PHI)"),
           ("Workstation", "100% local processing; ~/Documents/MedicalArchive"),
           ("DICOMDIR on USB", "standard DICOM media file-set, handed to the radiologist")],
    "es": [("Medios de imagen", "CDs, carpetas USB, descargas ZIP (datos de origen del paciente)"),
           ("Estación de trabajo", "procesamiento 100 % local; ~/Documents/MedicalArchive"),
           ("DICOMDIR en USB", "conjunto de archivos DICOM estándar, para el radiólogo")],
}
FLOW_ARROWS = {"en": ("read", "write"), "es": ("lee", "escribe")}
FLOW_CAPTION = {
    "en": "No server · No PHI egress · No telemetry · Only network call: the user-clicked update check (version.json)",
    "es": "Sin servidor · Los datos de pacientes no salen del equipo · Sin telemetría · Única conexión: buscar actualizaciones, a petición del usuario",
}
DAGGER_NOTE = {
    "en": ("† Derived from the installer configuration and the Inno Setup documentation; "
           "not yet tested by us on a Windows machine. Validate these items in a pilot, or "
           f"contact {SUPPORT_EMAIL} before a per-machine (all-users) deployment."),
    "es": ("† Basado en la configuración del instalador y en la documentación de Inno Setup; "
           "aún no lo hemos probado en un equipo Windows. Valide estos puntos en una prueba piloto "
           f"o escriba a {SUPPORT_EMAIL} antes de una instalación para todos los usuarios del equipo."),
}
CERT = {
    "en": {
        "banner": "Sample · for illustration only · not a valid license",
        "watermark": "SAMPLE",
        "h1": "Institutional License Certificate",
        "certifies": "This certifies that",
        "org": "[Organization name]",
        "holds": "holds a valid {tier} Institutional License for MIA Toolkit, covering {scope}, for the term shown below.",
        "fields": [("License number", "[License number]"), ("Tier", "[Clinic / Hospital / Network]"),
                   ("Scope", "[Sites and workstations covered]"), ("Issue date", "[YYYY-MM-DD]"),
                   ("Expiry date", "[YYYY-MM-DD]")],
        "issued_by": "Issued by",
    },
    "es": {
        "banner": "Muestra · solo ilustrativa · no es una licencia válida",
        "watermark": "MUESTRA",
        "h1": "Certificado de licencia institucional",
        "certifies": "Se certifica que",
        "org": "[Nombre de la organización]",
        "holds": "cuenta con una Licencia Institucional {tier} vigente de MIA Toolkit, que cubre {scope}, durante la vigencia indicada abajo.",
        "fields": [("Número de licencia", "[Número de licencia]"), ("Nivel", "[Clínica / Hospital / Red]"),
                   ("Alcance", "[Sitios y estaciones cubiertos]"), ("Fecha de emisión", "[AAAA-MM-DD]"),
                   ("Fecha de vencimiento", "[AAAA-MM-DD]")],
        "issued_by": "Emitido por",
    },
}

# --------------------------------------------------------------------------
# Markdown -> HTML
# --------------------------------------------------------------------------
MD_EXT = ["tables", "fenced_code", "sane_lists", "md_in_html"]


def md_html(md: str) -> str:
    h = markdown.markdown(md, extensions=MD_EXT)
    h = h.replace("<table>", '<table class="data">')
    # Keep "word — word" and "→" from breaking awkwardly; drop empty header cells' text.
    return h


def flow_html(lang: str) -> str:
    a1, a2 = FLOW_ARROWS[lang]
    nodes = FLOW[lang]
    parts = []
    for i, (t, d) in enumerate(nodes):
        cls = "node local" if i == 1 else "node"
        parts.append(f'<div class="{cls}"><b>{html.escape(t)}</b><span>{html.escape(d)}</span></div>')
        if i < len(nodes) - 1:
            parts.append(f'<div class="arrow">{(a1, a2)[i]}<br>→</div>')
    return (f'<div class="flow" role="img" aria-label="{html.escape(" → ".join(t for t, _ in nodes))}">'
            + "".join(parts) + "</div>"
            + f'<p class="flow-caption">{html.escape(FLOW_CAPTION[lang])}</p>')


def control_table(lang: str, title: str, pages: int | None) -> str:
    u = UI[lang]
    vals = [title, DOC_VERSION, DOC_DATE, u["lang_name"], str(pages or "–")]
    th = "".join(f'<th scope="col">{html.escape(c)}</th>' for c in u["control"])
    td = "".join(f"<td>{html.escape(v)}</td>" for v in vals)
    return (f'<table class="control" aria-label="{html.escape(u["control"][0])}">'
            '<colgroup><col style="width:34%"><col style="width:11%"><col style="width:15%">'
            '<col style="width:30%"><col style="width:10%"></colgroup>'
            f"<thead><tr>{th}</tr></thead><tbody><tr>{td}</tr></tbody></table>")


def page_html(lang: str, key: str, inner: str, body_class: str, pages: int | None,
              footer_extra: str = "") -> str:
    u = UI[lang]
    title = DOCS[key]["title"][lang]
    footer = u["footer"] + (f" · {footer_extra}" if footer_extra else "")
    return f"""<!doctype html>
<html lang="{'es-MX' if lang == 'es' else 'en'}">
<head>
<meta charset="utf-8">
<title>{html.escape(title)} – MIA Toolkit</title>
<meta name="author" content="Fritanga">
<meta name="description" content="{html.escape(u['eyebrow'])}: {html.escape(title)}">
<meta name="keywords" content="MIA Toolkit, DICOMDIR, {html.escape(u['kit'])}">
<meta name="generator" content="build_procurement_pdfs.py">
<meta name="dcterms.created" content="{DOC_DATE}T00:00:00Z">
<meta name="dcterms.modified" content="{DOC_DATE}T00:00:00Z">
<link rel="stylesheet" href="kit.css">
</head>
<body class="{body_class}">
<div class="band-top" role="banner"><span class="brand">{html.escape(BRAND[lang])}</span><span class="kit">{html.escape(u['kit'])}</span></div><div class="rule-bottom" aria-hidden="true"></div>
<div class="strings" aria-hidden="true"><span class="s-footer">{html.escape(footer)}</span><span class="s-page">{u['page']}</span><span class="s-of">{u['of']}</span></div>
<p class="eyebrow">{html.escape(u['eyebrow'])}</p>
<h1>{html.escape(title)}</h1>
{control_table(lang, title, pages)}
{inner}
</body>
</html>"""


# --------------------------------------------------------------------------
# Content assembly per language
# --------------------------------------------------------------------------

def read_es(key: str) -> tuple[dict, str]:
    p = CONTENT_DIR / "es" / f"{key}.md"
    meta, body = strip_frontmatter(p.read_text(encoding="utf-8"))
    return meta, body


def parts_from_md(md: str) -> dict:
    """For es files: '<!-- lead -->', '<!-- body -->', '<!-- market -->' markers."""
    out, cur = {}, None
    for line in md.splitlines():
        m = re.match(r"<!--\s*(\w+)\s*-->", line.strip())
        if m:
            cur = m.group(1)
            out[cur] = ""
            continue
        if cur:
            out[cur] += line + "\n"
    return {k: v.strip() for k, v in out.items()}


def inner_html(lang: str, key: str, parts: dict) -> tuple[str, str, str]:
    """-> (inner html, body class, footer extra)."""
    u = UI[lang]
    if key == "certificate":
        c = CERT[lang]
        ph = lambda s: f'<span class="placeholder">{html.escape(s)}</span>'
        tier, scope = c["fields"][1][1], c["fields"][2][1]
        holds = html.escape(c["holds"]).replace("{tier}", f"<strong>{ph(tier)}</strong>") \
                                       .replace("{scope}", f"<strong>{ph(scope)}</strong>")
        rows = "".join(f'<tr><th scope="row">{html.escape(k)}</th><td>{ph(v)}</td></tr>'
                       for k, v in c["fields"])
        inner = f"""<div class="sample-banner">{html.escape(c['banner'])}</div>
<div class="cert">
<div class="watermark" aria-hidden="true">{c['watermark']}</div>
<p class="eyebrow">{html.escape(c['watermark'])}</p>
<h2 style="border:0;font-size:22pt;font-weight:400;margin:2mm 0 1mm;padding:0">{html.escape(c['h1'])}</h2>
<p class="product">MIA Toolkit</p>
<p class="certifies">{html.escape(c['certifies'])}</p>
<p class="org">{ph(c['org'])}</p>
<p class="holds">{holds}</p>
<table class="fields">{rows}</table>
<p class="statement">{html.escape(parts['statement'])}</p>
<div class="issuer"><p class="eyebrow">{html.escape(c['issued_by'])}</p>
<strong>{html.escape(parts['issuer'])}</strong><br>{SUPPORT_EMAIL}<br>https://{SITE}</div>
</div>"""
        return inner, "certificate", ""

    lead = md_html(parts.get("lead", "")).replace("<p>", '<p class="lead">', 1)
    body = parts["body"]
    flow = flow_html(lang)
    if key == "security":
        # Lift the data-flow section out of the two columns: full width, in a band.
        m = re.search(r"^## ([^\n]+)\n+\{\{FLOW\}\}\n*", body, re.M)
        if m:
            body = body[:m.start()] + body[m.end():]
            lead += (f'<div class="band flowband"><h2>{html.escape(m.group(1))}</h2>'
                     f"{flow}</div>")
    def to_html(md: str) -> str:
        h = md_html(md.replace("{{FLOW}}", "FLOWPLACEHOLDER")
                      .replace("{{MARKET}}", "MARKETPLACEHOLDER"))
        h = h.replace("<p>FLOWPLACEHOLDER</p>", flow)
        if parts.get("market"):
            mk = (f'<div class="market" role="note"><p class="eyebrow">{u["by_market"]}</p>'
                  + md_html(parts["market"]) + "</div>")
            h = h.replace("<p>MARKETPLACEHOLDER</p>", mk)
        return h

    if key == "security":
        # Two explicit columns: technical sections left, privacy/regulatory/support right.
        m = re.search(r"^## (Privacy|Privacidad)", body, re.M)
        if not m:
            warn("security: privacy section not found; single column")
            return lead + to_html(body), "onepager", ""
        left, right = to_html(body[:m.start()]), to_html(body[m.start():])
        return (lead + f'<div class="cols"><div class="col">{left}</div>'
                f'<div class="col">{right}</div></div>'), "onepager", ""
    body_html = to_html(body)
    extra = ""
    if key == "it-guide" and parts.get("dagger"):
        lead += f'<div class="band"><p class="note">{html.escape(DAGGER_NOTE[lang])}</p></div>'
    if key == "license-terms" and lang == "es":
        extra = ES_TRANSLATION_NOTE
    return lead + body_html, "doc", extra


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render(html_str: str, out: Path) -> int:
    from weasyprint import HTML
    doc = HTML(string=html_str, base_url=str(TPL_DIR) + "/").render()
    doc.write_pdf(out, pdf_variant="pdf/ua-1", pdf_tags=True)
    return len(doc.pages)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault", default=os.environ.get("MIA_VAULT_LICENSE_PACK", DEFAULT_VAULT),
                    help="path to the vault's legal-finance/license-pack folder")
    ap.add_argument("--preview", help="also render every page to PNG in this folder")
    ap.add_argument("--stamp-translations", action="store_true",
                    help="after updating a Spanish file to match the current English, record "
                         "the English hash in its translated_from field")
    ap.add_argument("--strict", action="store_true",
                    help="fail on warnings (e.g. a stale Spanish translation)")
    args = ap.parse_args()
    vault = Path(args.vault)
    if not vault.is_dir():
        print(f"vault folder not found: {vault}", file=sys.stderr)
        return 2

    (CONTENT_DIR / "en").mkdir(parents=True, exist_ok=True)
    manifest = []
    for key, d in DOCS.items():
        raw = (vault / d["src"]).read_text(encoding="utf-8")
        # English parts from the vault
        if key == "certificate":
            en_parts = en_certificate(raw)
            en_md = f"{en_parts['statement']}\n\nIssued by: {en_parts['issuer']}\n"
        else:
            en_parts = EN_TRANSFORMS[key](clean_common(raw))
            en_md = "".join(f"<!-- {k} -->\n{v}\n\n" for k, v in en_parts.items()
                            if isinstance(v, str) and v)
        en_md_path = CONTENT_DIR / "en" / f"{key}.md"
        en_md_path.write_text(
            "<!-- GENERATED by scripts/build_procurement_pdfs.py from the vault; do not edit. -->\n"
            + en_md, encoding="utf-8")
        en_hash = hashlib.sha256(en_md.encode()).hexdigest()

        # Spanish parts from the repo translation
        if args.stamp_translations:
            p = CONTENT_DIR / "es" / f"{key}.md"
            p.write_text(re.sub(r"^translated_from:.*$", f"translated_from: {en_hash}",
                                p.read_text(encoding="utf-8"), count=1, flags=re.M),
                         encoding="utf-8")
        es_meta, es_md = read_es(key)
        if es_meta.get("translated_from") != en_hash:
            warn(f"es/{key}.md was translated from an older English text "
                 f"(diff scripts/procurement_pdf/content/en/{key}.md in git and update the "
                 f"translation, then set translated_from: {en_hash})")
        es_parts = parts_from_md(es_md)
        if key == "certificate":
            es_parts = {"statement": " ".join(es_parts.get("statement", "").split()),
                        "issuer": en_parts["issuer"]}
        else:
            es_parts["dagger"] = "†" in es_parts.get("body", "")

        for lang, parts in (("en", en_parts), ("es", es_parts)):
            out = OUT_DIR / lang / d["file"][lang]
            out.parent.mkdir(parents=True, exist_ok=True)
            inner, cls, extra = inner_html(lang, key, parts)
            n = render(page_html(lang, key, inner, cls, None, extra), out)
            n2 = render(page_html(lang, key, inner, cls, n, extra), out)
            if n2 != n:
                n2 = render(page_html(lang, key, inner, cls, n2, extra), out)
            if key in ("security", "certificate") and n2 != 1:
                warn(f"{out.name} is {n2} pages (expected 1)")
            manifest.append({"lang": lang, "key": key, "title": d["title"][lang],
                             "filename": f"{lang}/{out.name}", "pages": n2,
                             "bytes": out.stat().st_size, "sha256": sha256(out)})
            print(f"{lang} {key:14s} {n2}p {out.stat().st_size // 1024:4d} KB  {out.relative_to(ROOT)}")

    (OUT_DIR / "manifest.json").write_text(json.dumps({
        "version": DOC_VERSION, "date": DOC_DATE,
        "brand": BRAND, "kit_name": {k: v["kit"] for k, v in UI.items()},
        "base_path": "/kit/", "documents": manifest,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.preview:
        import pymupdf as fitz
        pv = Path(args.preview)
        pv.mkdir(parents=True, exist_ok=True)
        for m in manifest:
            pdf = fitz.open(OUT_DIR / m["filename"])
            for i, page in enumerate(pdf):
                page.get_pixmap(dpi=110).save(pv / f"{Path(m['filename']).stem}-p{i + 1}.png")
        print(f"previews in {pv}")

    if WARNINGS:
        print(f"{len(WARNINGS)} warning(s)", file=sys.stderr)
        return 1 if args.strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
