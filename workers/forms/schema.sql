-- D1 schema for the MIA Tools forms Worker.
-- Apply with:  npx wrangler d1 execute mia-forms --remote --file=schema.sql
-- Deliberately NO ip / user-agent / cookie columns: the Worker never stores
-- them (privacy policy, launch-readiness R4).
CREATE TABLE IF NOT EXISTS submissions (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  form             TEXT    NOT NULL,             -- "pilot"
  market           TEXT    NOT NULL,             -- "mx" | "us" | "sg"
  campaign         TEXT    NOT NULL DEFAULT '',  -- opaque utm_campaign code
  name             TEXT    NOT NULL,
  email            TEXT    NOT NULL,
  organisation     TEXT    NOT NULL,
  role             TEXT    NOT NULL DEFAULT '',
  discs_per_month  TEXT    NOT NULL DEFAULT '',  -- lt10 | 10-50 | 51-200 | gt200 | unsure
  pacs             TEXT    NOT NULL DEFAULT '',
  message          TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS submissions_created_at ON submissions (created_at);
