-- D1 schema for the MIA Tools forms Worker.
-- Apply with:  npx wrangler d1 execute mia-forms --remote --file=schema.sql
-- Deliberately NO ip / user-agent / cookie columns: the Worker never stores
-- them (privacy policy, launch-readiness R4).
-- Existing database created before request_type existed? Run once:
--   ALTER TABLE submissions ADD COLUMN request_type TEXT NOT NULL DEFAULT 'pilot';
--   ALTER TABLE submissions ADD COLUMN country TEXT;
--   ALTER TABLE submissions ADD COLUMN segment TEXT;
--   ALTER TABLE submissions ADD COLUMN sites TEXT;
--   ALTER TABLE submissions ADD COLUMN protocol TEXT;
--   ALTER TABLE submissions ADD COLUMN timeline TEXT;
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
  role             TEXT    NOT NULL DEFAULT '',  -- free text (pilot) | clinical | management | it | other (bridge_partner)
  discs_per_month  TEXT    NOT NULL DEFAULT '',  -- lt10 | 10-50 | 51-200 | gt200 | unsure
  pacs             TEXT    NOT NULL DEFAULT '',
  message          TEXT    NOT NULL DEFAULT '',
  -- MIA Bridge design-partner fields (form = bridge_partner); NULL otherwise.
  -- discs_per_month, pacs and message are shared with the pilot form.
  country          TEXT,                         -- mx | us | sg | latam | other
  segment          TEXT,                         -- chain | imaging_centre | hospital | telerad | other
  sites            TEXT,                         -- 1 | 2-5 | 6-20 | gt20
  protocol         TEXT,                         -- dimse | dicomweb | both | unsure
  timeline         TEXT                          -- now | 1-3m | 3-6m | exploring
);
CREATE INDEX IF NOT EXISTS submissions_created_at ON submissions (created_at);

-- Go links (https://go.miatools.tech/<code>): one row per institutional
-- outreach code (bucket `k` in the private UTM legend). Deliberately NO
-- institution name, IP, user agent or cookie: the code→institution key lives
-- only in the private CRM, which upserts rows with scripts/crm_sync.py
-- push-links. clicks counts redirects followed by a person (HEAD, prefetch and
-- preview bots excluded); last_click is a UTC date (YYYY-MM-DD), no time.
-- Added 2026-10-20; on an existing database just re-run this file (IF NOT EXISTS).
CREATE TABLE IF NOT EXISTS links (
  code        TEXT    PRIMARY KEY,               -- ^k[a-z2-7]{3}$
  market      TEXT,                              -- "mx" | "us" | "sg"
  lang        TEXT,                              -- site language code (es, en, …)
  active      INTEGER DEFAULT 1,                 -- 0 = closed institution → neutral hub
  clicks      INTEGER DEFAULT 0,
  last_click  TEXT                               -- UTC date only
);
