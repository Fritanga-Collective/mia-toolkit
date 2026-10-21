-- D1 schema for the MIA Tools forms Worker.
-- Apply with:  npx wrangler d1 execute mia-forms --remote --file=schema.sql
-- Deliberately NO ip / user-agent / cookie columns: the Worker never stores
-- them (privacy policy, launch-readiness R4).
-- Existing database created before request_type existed? Run once:
--   ALTER TABLE submissions ADD COLUMN request_type TEXT NOT NULL DEFAULT 'pilot';
--   ALTER TABLE submissions ADD COLUMN sites_count TEXT;
--   ALTER TABLE submissions ADD COLUMN pacs_vendor TEXT;
--   ALTER TABLE submissions ADD COLUMN pacs_version TEXT;
--   ALTER TABLE submissions ADD COLUMN protocol TEXT;
--   ALTER TABLE submissions ADD COLUMN timeline TEXT;
--   ALTER TABLE submissions ADD COLUMN region TEXT;
CREATE TABLE IF NOT EXISTS submissions (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  form             TEXT    NOT NULL,             -- "pilot" | "bridge_partner"
  request_type     TEXT    NOT NULL DEFAULT 'pilot', -- pilot | pricing_clinic | pricing_hospital | pricing_network | pricing_public | kit | bridge_partner
  market           TEXT    NOT NULL,             -- "mx" | "us" | "sg" ('' for bridge_partner)
  campaign         TEXT    NOT NULL DEFAULT '',  -- opaque utm_campaign code
  name             TEXT    NOT NULL,
  email            TEXT    NOT NULL,
  organisation     TEXT    NOT NULL,
  role             TEXT    NOT NULL DEFAULT '',
  discs_per_month  TEXT    NOT NULL DEFAULT '',  -- lt10 | 10-50 | 51-200 | gt200 | unsure
  pacs             TEXT    NOT NULL DEFAULT '',
  message          TEXT    NOT NULL DEFAULT '',
  -- MIA Bridge design-partner fields (form = bridge_partner); NULL otherwise.
  sites_count      TEXT,
  pacs_vendor      TEXT,
  pacs_version     TEXT,
  protocol         TEXT,                         -- dimse | dicomweb | unsure
  timeline         TEXT,
  region           TEXT
);
CREATE INDEX IF NOT EXISTS submissions_created_at ON submissions (created_at);
