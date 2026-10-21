#!/usr/bin/env python3
"""Sync the private institutional CRM (an Obsidian vault) with the forms Worker.

Stdlib only. The CRM lives outside this repo; this script never writes
institution names, people or emails to D1 or to the repo.

Subcommands (``--vault`` is the folder that contains ``strategy/outreach/crm``):

  push-links --vault V   Upsert every institution's go-link code into the D1
                         ``links`` table (code, market, lang, active) with
                         ``npx wrangler d1 execute mia-forms --remote``.
                         ``active`` is 0 for ``stage: closed``. Names are
                         never sent.
  pull --vault V         Fetch /export (form submissions) and /export-links
                         (click counts) from the forms Worker. A submission
                         whose campaign code matches an institution's
                         ``link_code`` raises its stage to at least
                         ``engaged`` (never downgrades), appends a dated line
                         under ``## Activity`` and updates ``last_contact``.
                         Click counts go to ``link_clicks`` /
                         ``link_last_click``. Unmatched submissions go to
                         ``crm/INBOX-UNMATCHED.md`` (organisation, request
                         type, date only). Idempotent.
  fields --vault V       Add the outreach fields (touches, reply, next action,
                         …) with defaults to every institution note that lacks
                         them; existing values are never changed.

The export token comes from ``$MIA_FORMS_TOKEN`` or
``~/.config/mia/forms-export-token``; it is never printed.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

FORMS_ORIGIN = os.environ.get("MIA_FORMS_ORIGIN", "https://forms.miatools.tech")
TOKEN_FILE = Path.home() / ".config" / "mia" / "forms-export-token"
WORKER_DIR = Path(__file__).resolve().parent.parent / "workers" / "forms"
D1_NAME = "mia-forms"

CODE_RE = re.compile(r"^k[a-z2-7]{3}$")
LANG_RE = re.compile(r"^[a-z]{2}$")
MARKETS = {"mx", "us", "sg"}
STAGES = ["identified", "contacted", "engaged", "pilot", "paid"]  # + closed
TEST_EMAIL_RE = re.compile(r"@(?:[\w-]+\.)*example\.(?:com|org|net)$", re.I)

# Outreach fields added by `fields` (key, default YAML value). Order matters:
# they are inserted before `tags:` in this order.
OUTREACH_FIELDS: List[Tuple[str, str]] = [
    ("contact", '""'),
    ("next_action", '""'),
    ("next_action_date", ""),
    ("touches", "0"),
    ("last_channel", '""'),
    ("last_touch_date", ""),
    ("reply", "no"),
    ("link_clicks", "0"),
    ("link_last_click", ""),
]

ACTIVITY_HEADING = "## Activity"


# ───────────────────────────── frontmatter ─────────────────────────────
class Note:
    """An institution note: frontmatter lines kept verbatim, edited in place."""

    def __init__(self, path: Path):
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        lines = self.text.split("\n")
        if not lines or lines[0].strip() != "---":
            raise ValueError(f"{path.name}: no frontmatter")
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        except StopIteration:
            raise ValueError(f"{path.name}: unterminated frontmatter") from None
        self.fm: List[str] = lines[1:end]
        self.body: List[str] = lines[end + 1:]
        self.changed = False

    # Reading
    def _index(self, key: str) -> Optional[int]:
        prefix = key + ":"
        for i, line in enumerate(self.fm):
            if line.startswith(prefix):
                return i
        return None

    def get(self, key: str) -> str:
        i = self._index(key)
        if i is None:
            return ""
        v = self.fm[i][len(key) + 1:].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        return v

    def has(self, key: str) -> bool:
        return self._index(key) is not None

    # Writing
    def set_raw(self, key: str, raw: str) -> None:
        line = f"{key}: {raw}".rstrip()
        i = self._index(key)
        if i is not None:
            if self.fm[i] != line:
                self.fm[i] = line
                self.changed = True
            return
        tags = self._index("tags")
        self.fm.insert(tags if tags is not None else len(self.fm), line)
        self.changed = True

    def set(self, key: str, value) -> None:
        self.set_raw(key, yaml_scalar(value))

    def add_activity(self, line: str) -> bool:
        """Append `- line` under ## Activity (created before ## Touch log, or
        at the end). Returns False if that exact line is already there."""
        bullet = f"- {line}"
        if bullet in self.body:
            return False
        try:
            h = self.body.index(ACTIVITY_HEADING)
        except ValueError:
            try:
                at = self.body.index("## Touch log")
            except ValueError:
                at = len(self.body)
                while at > 0 and self.body[at - 1].strip() == "":
                    at -= 1
                self.body[at:at] = ["", ACTIVITY_HEADING, ""]
                h = at + 1
            else:
                self.body[at:at] = [ACTIVITY_HEADING, "", ""]
                h = at
        # Insert after the last bullet of the section (before the next heading).
        j = h + 1
        last = h + 1
        while j < len(self.body) and not self.body[j].startswith("## "):
            if self.body[j].startswith("- "):
                last = j + 1
            j += 1
        if last == h + 1 and h + 1 < len(self.body) and self.body[h + 1].strip() == "":
            last = h + 2
        self.body.insert(last, bullet)
        self.changed = True
        return True

    def render(self) -> str:
        return "\n".join(["---", *self.fm, "---", *self.body])

    def save(self) -> bool:
        if not self.changed:
            return False
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(self.render())
        return True


def yaml_scalar(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    s = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) or re.fullmatch(r"[A-Za-z0-9_.-]+", s):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ───────────────────────────── vault ─────────────────────────────
def crm_dir(vault: Path) -> Path:
    d = vault / "strategy" / "outreach" / "crm"
    if not d.is_dir():
        raise SystemExit(f"no CRM at {d}")
    return d


def institutions(vault: Path) -> List[Note]:
    notes = []
    for p in sorted((crm_dir(vault) / "institutions").glob("*.md")):
        try:
            n = Note(p)
        except ValueError:
            continue
        if n.get("type") == "crm-institution":
            notes.append(n)
    return notes


def stage_rank(stage: str) -> int:
    return STAGES.index(stage) if stage in STAGES else -1


# ───────────────────────────── push-links ─────────────────────────────
def link_rows(notes: List[Note]) -> Tuple[List[Tuple[str, str, str, int]], List[str]]:
    """(code, market, lang, active) per institution + problems found."""
    rows, problems, seen = [], [], {}
    for n in notes:
        code = n.get("link_code").lower()
        market = n.get("market").lower()
        lang = n.get("language").lower() or ("es" if market == "mx" else "en")
        name = n.path.name
        if not CODE_RE.match(code):
            problems.append(f"{name}: link_code {code!r} is not ^k[a-z2-7]{{3}}$")
            continue
        if market not in MARKETS:
            problems.append(f"{name}: market {market!r} not in mx|us|sg")
            continue
        if not LANG_RE.match(lang):
            problems.append(f"{name}: language {lang!r} is not a 2-letter code")
            continue
        if code in seen:
            problems.append(f"{name}: link_code {code} duplicates {seen[code]}")
            continue
        seen[code] = name
        rows.append((code, market, lang, 0 if n.get("stage") == "closed" else 1))
    return rows, problems


def sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def upsert_sql(rows: List[Tuple[str, str, str, int]]) -> str:
    values = ", ".join(
        f"({sql_str(c)}, {sql_str(m)}, {sql_str(lg)}, {int(a)})" for c, m, lg, a in rows)
    return ("INSERT INTO links (code, market, lang, active) VALUES " + values
            + " ON CONFLICT(code) DO UPDATE SET market = excluded.market, "
            "lang = excluded.lang, active = excluded.active;")


def wrangler_cmd(sql: str) -> List[str]:
    npx = shutil.which("npx") or "npx"
    return [npx, "wrangler", "d1", "execute", D1_NAME, "--remote", "--command", sql]


def cmd_push_links(args) -> int:
    notes = institutions(Path(args.vault))
    rows, problems = link_rows(notes)
    for p in problems:
        print("skip:", p, file=sys.stderr)
    if not rows:
        print("no valid link codes found")
        return 1
    sql = upsert_sql(rows)
    active = sum(r[3] for r in rows)
    if args.dry_run:
        print(sql)
    else:
        r = subprocess.run(wrangler_cmd(sql), cwd=args.worker_dir,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-2000:] or r.stdout[-2000:], file=sys.stderr)
            return r.returncode
    print(f"push-links: {len(rows)} codes upserted ({active} active, "
          f"{len(rows) - active} inactive), {len(problems)} skipped"
          + (" [dry run]" if args.dry_run else ""))
    return 1 if problems else 0


# ───────────────────────────── pull ─────────────────────────────
def read_token() -> str:
    tok = os.environ.get("MIA_FORMS_TOKEN", "").strip()
    if not tok and TOKEN_FILE.is_file():
        tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not tok:
        raise SystemExit("no export token: set MIA_FORMS_TOKEN or create " + str(TOKEN_FILE))
    return tok


def fetch_csv(path: str, token: str) -> List[Dict[str, str]]:
    req = urllib.request.Request(FORMS_ORIGIN + path, headers={
        "Authorization": "Bearer " + token, "User-Agent": "mia-crm-sync/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def clean_cell(v: str, limit: int = 120) -> str:
    v = (v or "").lstrip("'")  # the Worker prefixes formula-like cells with '
    v = re.sub(r"[\s|\[\]]+", " ", v).strip()
    return v[:limit]


def apply_pull(vault: Path, submissions: List[Dict[str, str]],
               links: List[Dict[str, str]]) -> Dict[str, int]:
    notes = institutions(vault)
    by_code = {n.get("link_code").lower(): n for n in notes if n.get("link_code")}
    stats = {"submissions": 0, "matched": 0, "new_activity": 0, "stage_raised": 0,
             "unmatched": 0, "new_unmatched": 0, "skipped_test": 0,
             "link_rows": len(links), "click_updates": 0, "notes_written": 0}
    unmatched: List[Tuple[str, str]] = []  # (marker, line)

    for s in submissions:
        if TEST_EMAIL_RE.search(s.get("email", "")):
            stats["skipped_test"] += 1
            continue
        stats["submissions"] += 1
        sid = (s.get("id") or "").strip()
        day = (s.get("created_at") or "")[:10]
        rtype = clean_cell(s.get("request_type") or s.get("form") or "request", 40)
        n = by_code.get((s.get("campaign") or "").strip().lower())
        if n is None:
            stats["unmatched"] += 1
            org = clean_cell(s.get("organisation", "")) or "(no organisation)"
            marker = f"(submission #{sid})"
            unmatched.append((marker, f"{day} — {org} — {rtype} {marker}"))
            continue
        stats["matched"] += 1
        line = (f"{day} — form: {rtype} (submission #{sid}; no personal data "
                "copied here; see export)")
        if n.add_activity(line):
            stats["new_activity"] += 1
        stage = n.get("stage")
        if stage != "closed" and stage_rank(stage) < stage_rank("engaged"):
            n.set("stage", "engaged")
            stats["stage_raised"] += 1
        if day and n.get("last_contact") < day:
            n.set("last_contact", day)

    for row in links:
        n = by_code.get((row.get("code") or "").strip().lower())
        if n is None:
            continue
        clicks = int(row.get("clicks") or 0)
        last = (row.get("last_click") or "").strip()[:10]
        before = (n.get("link_clicks"), n.get("link_last_click"))
        n.set("link_clicks", clicks)
        n.set_raw("link_last_click", yaml_scalar(last))
        if (n.get("link_clicks"), n.get("link_last_click")) != before:
            stats["click_updates"] += 1

    for n in notes:
        if n.save():
            stats["notes_written"] += 1

    if unmatched:
        stats["new_unmatched"] = write_inbox(crm_dir(vault) / "INBOX-UNMATCHED.md", unmatched)
    return stats


INBOX_HEADER = """---
type: crm-inbox
tags: [mia-toolkit, crm, inbox]
---

# Inbox — form submissions without a matching link code

> Written by `scripts/crm_sync.py pull`. Each line is a pilot / pricing / kit / Bridge request whose campaign code matched no institution's `link_code` (or had none). Only organisation, request type and date are copied here; the person's details stay in the Worker export. Match it by hand: add the institution (or find it in [[00-CRM]]), log it there, then tick the line here.

## Unmatched
"""


def write_inbox(path: Path, items: List[Tuple[str, str]]) -> int:
    text = path.read_text(encoding="utf-8") if path.is_file() else INBOX_HEADER
    added = 0
    lines = text.rstrip("\n").split("\n")
    if lines[-1].startswith("## "):
        lines.append("")
    for marker, line in items:
        if marker in text:
            continue
        lines.append(f"- [ ] {line}")
        text += "\n" + line
        added += 1
    if added or not path.is_file():
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines) + "\n")
    return added


def cmd_pull(args, fetch: Callable[[str, str], List[Dict[str, str]]] = fetch_csv) -> int:
    token = read_token()
    submissions = fetch("/export", token)
    links = fetch("/export-links", token)
    stats = apply_pull(Path(args.vault), submissions, links)
    print("pull: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    return 0


# ───────────────────────────── fields ─────────────────────────────
def ensure_fields(vault: Path) -> int:
    written = 0
    for n in institutions(vault):
        for key, default in OUTREACH_FIELDS:
            if not n.has(key):
                n.set_raw(key, default)
        if n.save():
            written += 1
    return written


def cmd_fields(args) -> int:
    print(f"fields: {ensure_fields(Path(args.vault))} notes updated")
    return 0


# ───────────────────────────── main ─────────────────────────────
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("push-links", help="upsert link codes into D1")
    p.add_argument("--vault", required=True)
    p.add_argument("--worker-dir", default=str(WORKER_DIR),
                   help="folder with wrangler.toml (default: workers/forms)")
    p.add_argument("--dry-run", action="store_true", help="print the SQL only")
    p.set_defaults(func=cmd_push_links)
    p = sub.add_parser("pull", help="pull submissions + click counts into the vault")
    p.add_argument("--vault", required=True)
    p.set_defaults(func=cmd_pull)
    p = sub.add_parser("fields", help="add missing outreach fields with defaults")
    p.add_argument("--vault", required=True)
    p.set_defaults(func=cmd_fields)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
