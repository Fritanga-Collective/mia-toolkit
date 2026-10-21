"""Tests for scripts/crm_sync.py (CRM vault <-> forms Worker sync). No network."""
import importlib.util
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("crm_sync", ROOT / "scripts" / "crm_sync.py")
crm_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crm_sync)

NOTE = """---
type: crm-institution
id: {id}
name: "{name}"
market: {market}
segment: imaging
language: {lang}
link_code: {code}
stage: {stage}
pain_points: []
last_contact:{last}
source: "test"
tags: [mia-toolkit, crm, institution]
---

# {name}

## Pain points (in their words)

- unknown

## Touch log

- 2026-10-20 — imported.
"""


def make_vault(tmp_path, rows):
    inst = tmp_path / "strategy" / "outreach" / "crm" / "institutions"
    inst.mkdir(parents=True)
    for r in rows:
        r = {"lang": "es", "market": "mx", "stage": "identified", "last": "", **r}
        if r["last"]:
            r["last"] = " " + r["last"]
        (inst / f"{r['id']}-x.md").write_text(NOTE.format(**r), encoding="utf-8")
    (inst / "US-TARGET-SEGMENTS.md").write_text(
        "---\ntype: crm-segment-note\nmarket: us\n---\n\n# US\n", encoding="utf-8")
    return tmp_path


def read(vault, id_):
    return next((vault / "strategy/outreach/crm/institutions").glob(f"{id_}-*.md")).read_text(
        encoding="utf-8")


def test_link_rows_validate_and_never_carry_names(tmp_path):
    v = make_vault(tmp_path, [
        {"id": "I001", "name": "Clínica O'Brien", "code": "kab2"},
        {"id": "I002", "name": "SG Hosp", "code": "kzz7", "market": "sg", "lang": "en",
         "stage": "closed"},
        {"id": "I003", "name": "Bad", "code": "k1x9"},          # 1 and 9 not in a-z2-7
        {"id": "I004", "name": "Dup", "code": "kab2"},
        {"id": "I005", "name": "Bad market", "code": "kqqq", "market": "es"},
    ])
    rows, problems = crm_sync.link_rows(crm_sync.institutions(v))
    assert rows == [("kab2", "mx", "es", 1), ("kzz7", "sg", "en", 0)]
    assert len(problems) == 3
    sql = crm_sync.upsert_sql(rows)
    assert "O'Brien" not in sql and "Clínica" not in sql and "SG Hosp" not in sql
    assert sql.startswith("INSERT INTO links (code, market, lang, active) VALUES ('kab2', 'mx', 'es', 1)")
    assert "ON CONFLICT(code) DO UPDATE SET" in sql
    assert crm_sync.sql_str("a'b") == "'a''b'"


def test_push_links_dry_run(tmp_path, capsys, monkeypatch):
    v = make_vault(tmp_path, [{"id": "I001", "name": "A", "code": "kab2"}])
    monkeypatch.setattr(crm_sync.subprocess, "run",
                        lambda *a, **k: pytest.fail("dry run must not call wrangler"))
    rc = crm_sync.main(["push-links", "--vault", str(v), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0 and "1 codes upserted" in out and "INSERT INTO links" in out


def test_push_links_calls_wrangler_without_a_shell(tmp_path, monkeypatch):
    v = make_vault(tmp_path, [{"id": "I001", "name": "A", "code": "kab2"}])
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(crm_sync.subprocess, "run", fake_run)
    assert crm_sync.main(["push-links", "--vault", str(v), "--worker-dir", str(tmp_path)]) == 0
    assert seen["cmd"][1:7] == ["wrangler", "d1", "execute", "mia-forms", "--remote", "--command"]
    assert "shell" not in seen["kw"]


SUBS = [
    {"id": "1", "created_at": "2026-10-21T10:00:00Z", "form": "pilot",
     "request_type": "pricing_hospital", "market": "mx", "campaign": "kab2",
     "name": "Ana", "email": "ana@clinica.mx", "organisation": "Clínica A"},
    {"id": "2", "created_at": "2026-10-22T10:00:00Z", "form": "pilot", "request_type": "kit",
     "market": "sg", "campaign": "kzz7", "name": "Bo", "email": "bo@h.sg", "organisation": "H"},
    {"id": "3", "created_at": "2026-10-22T11:00:00Z", "form": "pilot", "request_type": "pilot",
     "market": "us", "campaign": "", "name": "Cy", "email": "cy@rural.org",
     "organisation": "Rural | Hospital\nNorth"},
    {"id": "4", "created_at": "2026-10-22T12:00:00Z", "form": "pilot", "request_type": "pilot",
     "market": "us", "campaign": "", "name": "Test", "email": "t@example.com",
     "organisation": "Test Org"},
]
LINKS = [
    {"code": "kab2", "market": "mx", "lang": "es", "active": "1", "clicks": "3",
     "last_click": "2026-10-21"},
    {"code": "kzz7", "market": "sg", "lang": "en", "active": "1", "clicks": "0", "last_click": ""},
]


def test_pull_matches_raises_stage_logs_activity_and_is_idempotent(tmp_path):
    v = make_vault(tmp_path, [
        {"id": "I001", "name": "A", "code": "kab2"},
        {"id": "I002", "name": "B", "code": "kzz7", "market": "sg", "lang": "en",
         "stage": "pilot", "last": "2026-12-01"},
    ])
    s = crm_sync.apply_pull(v, SUBS, LINKS)
    assert s["matched"] == 2 and s["unmatched"] == 1 and s["skipped_test"] == 1
    assert s["stage_raised"] == 1 and s["new_activity"] == 2

    a = read(v, "I001")
    assert "stage: engaged" in a
    assert "last_contact: 2026-10-21" in a
    assert "link_clicks: 3" in a and "link_last_click: 2026-10-21" in a
    assert "## Activity\n\n- 2026-10-21 — form: pricing_hospital (submission #1;" in a
    assert a.index("## Activity") < a.index("## Touch log")
    assert "Ana" not in a and "ana@clinica.mx" not in a

    b = read(v, "I002")
    assert "stage: pilot" in b                      # never downgraded
    assert "last_contact: 2026-12-01" in b          # never moved back

    inbox = (v / "strategy/outreach/crm/INBOX-UNMATCHED.md").read_text(encoding="utf-8")
    assert "- [ ] 2026-10-22 — Rural Hospital North — pilot (submission #3)" in inbox
    assert "cy@rural.org" not in inbox and "Cy" not in inbox and "Test Org" not in inbox

    before = {i: read(v, i) for i in ("I001", "I002")}
    s2 = crm_sync.apply_pull(v, SUBS, LINKS)
    assert s2["new_activity"] == 0 and s2["new_unmatched"] == 0 and s2["notes_written"] == 0
    assert {i: read(v, i) for i in ("I001", "I002")} == before
    assert (v / "strategy/outreach/crm/INBOX-UNMATCHED.md").read_text(encoding="utf-8") == inbox


def test_closed_stays_closed(tmp_path):
    v = make_vault(tmp_path, [{"id": "I001", "name": "A", "code": "kab2", "stage": "closed"}])
    crm_sync.apply_pull(v, SUBS[:1], [])
    assert "stage: closed" in read(v, "I001")


def test_fields_adds_defaults_without_clobbering(tmp_path):
    v = make_vault(tmp_path, [{"id": "I001", "name": "A", "code": "kab2"}])
    p = next((v / "strategy/outreach/crm/institutions").glob("I001-*.md"))
    p.write_text(p.read_text(encoding="utf-8").replace("tags:", "touches: 1\nreply: yes\ntags:"),
                 encoding="utf-8")
    assert crm_sync.ensure_fields(v) == 1
    t = read(v, "I001")
    assert "touches: 1" in t and "touches: 0" not in t
    assert "reply: yes" in t and "reply: no" not in t
    for key in ("next_action:", "next_action_date:", "last_channel:", "last_touch_date:",
                "link_clicks: 0", "link_last_click:", "contact:"):
        assert key in t
    fm = t.split("---")[1]
    assert fm.rstrip().endswith("tags: [mia-toolkit, crm, institution]")
    assert crm_sync.ensure_fields(v) == 0


def test_token_from_env_and_cmd_pull_uses_injected_fetch(tmp_path, monkeypatch, capsys):
    v = make_vault(tmp_path, [{"id": "I001", "name": "A", "code": "kab2"}])
    monkeypatch.setenv("MIA_FORMS_TOKEN", "tok")
    calls = []

    def fetch(path, token):
        calls.append((path, token))
        return SUBS if path == "/export" else LINKS

    args = types.SimpleNamespace(vault=str(v))
    assert crm_sync.cmd_pull(args, fetch=fetch) == 0
    assert calls == [("/export", "tok"), ("/export-links", "tok")]
    assert "tok" not in capsys.readouterr().out


def test_yaml_scalar():
    assert crm_sync.yaml_scalar("") == ""
    assert crm_sync.yaml_scalar(3) == "3"
    assert crm_sync.yaml_scalar("2026-10-21") == "2026-10-21"
    assert crm_sync.yaml_scalar('say "hi": x') == '"say \\"hi\\": x"'
