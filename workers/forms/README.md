# MIA Tools forms Worker

Cloudflare Worker + D1 backend for the institutional **pilot-request form** on
`/institutions/<market>/#pilot`. One row per request in D1; optional
notification email; a token-protected CSV export. The same form also carries
pricing and procurement-kit requests: a `request_type` field records what was
clicked (`pilot` | `pricing_clinic` | `pricing_hospital` | `pricing_network` |
`pricing_public` | `kit`; missing = `pilot`, anything else is rejected). For a
D1 database created before this column existed, run the `ALTER TABLE` line at
the top of `schema.sql` once.

**MIA Bridge design-partner form** (bridge.miatools.tech): POST with
`form=bridge_partner` (and `request_type=bridge_partner`, the default for that
form). `market` may be empty. Accepted optional fields, size-limited and stored
as NULL when empty: `region` (120), `sites_count` (20), `pacs_vendor` (120),
`pacs_version` (60), `protocol` (`dimse` | `dicomweb` | `unsure`), `timeline`
(120), plus the usual `name`, `email`, `organisation`, `role`,
`discs_per_month`, `message`, `lang`, `utm_campaign` and the `website`
honeypot. No-JS posts 303 to `BRIDGE_THANKS` (default
`https://bridge.miatools.tech/thanks/`). No cookies, no IPs stored or
logged, no third-party scripts on the site.

> **Before going live:** ship the privacy-policy update (launch-readiness
> **R4**: forms, what's collected, retention, per-institution campaign codes)
> **first**. The form's privacy line links to the privacy page and promises
> "used only to reply and run your pilot, no tracking" — the policy must say
> the same before `FORM_ENDPOINT` is set.

## What it does

| Route | |
|---|---|
| `POST /submit` | `application/x-www-form-urlencoded` (no-JS form) or JSON (fetch). Origin must be in `ALLOWED_ORIGINS` (default `https://miatools.tech,https://bridge.miatools.tech`), else 403. Validates and size-limits every field (body ≤ 16 KB). Honeypot `website` filled → pretends success, stores nothing. In-memory per-isolate rate limit (5 per 10 min per client; salted hash in memory only, never persisted). Stores the row in D1, then **303 → thank-you page** (no JS) or `{"ok": true}` (when `Accept: application/json`). |
| `OPTIONS /submit` | CORS preflight, allowed origins only. |
| `GET /export` | CSV of all rows. Needs `Authorization: Bearer $EXPORT_TOKEN`; returns 404 if no token is configured. Cells starting with `= + - @` are prefixed with `'` (spreadsheet formula injection). |
| `GET /health` | `ok` |

Thank-you pages (built by `website/build.py`, `INST_THANKS`): MX →
`/es/institutions/mx/gracias/`, US/SG → `/institutions/thanks/`.

Columns: `id, created_at, form, market, campaign, name, email, organisation,
role, discs_per_month, pacs, message` (`schema.sql`). No IP, user agent or
cookie columns, deliberately.

## Deploy (Luis)

Needs Node ≥ 20. `wrangler` is run through `npx`, nothing to install globally.

```sh
cd workers/forms

# 1. Log in to Cloudflare (opens a browser).
npx wrangler login

# 2. Create the database and paste the printed database_id into wrangler.toml
#    (replace REPLACE_WITH_D1_DATABASE_ID). Optionally set account_id too.
npx wrangler d1 create mia-forms

# 3. Create the table.
npx wrangler d1 execute mia-forms --remote --file=schema.sql

# 4. Secrets.
npx wrangler secret put EXPORT_TOKEN      # long random string, e.g. `openssl rand -hex 32`
# optional, only if you turn on the notification email (see below):
npx wrangler secret put EMAIL_API_KEY

# 5. Deploy. Prints the URL, e.g. https://mia-forms.<your-subdomain>.workers.dev
npx wrangler deploy
```

6. (Optional, nicer) serve it at `https://forms.miatools.tech`: uncomment the
   `routes` line in `wrangler.toml` (needs `miatools.tech` DNS on Cloudflare)
   and deploy again.
7. Test it with the curl commands below.
8. **Ship the privacy-policy update (R4).**
9. In `website/build.py` set
   `FORM_ENDPOINT = "https://forms.miatools.tech/submit"` (or the
   `workers.dev` URL + `/submit`), rebuild, and check that the form's button
   is enabled and the "opens soon" note is gone. Then merge/deploy the site.

Keep `[observability] enabled = false` in `wrangler.toml`: Workers Logs would
record request metadata, including client IPs.

## Notification email (optional)

`miatools.tech` mail is hosted on **Zoho Mail** (its MX records point at Zoho),
so **Cloudflare Email Routing / `send_email` can't be used** without moving the
MX records to Cloudflare — which would break the Zoho mailboxes. Use a
transactional email HTTP API instead:

- **Zoho ZeptoMail** (same vendor as the mailbox; verify `miatools.tech` as a
  sending domain in ZeptoMail and add its SPF/DKIM records) —
  `EMAIL_PROVIDER = "zeptomail"`, `EMAIL_API_KEY` = the "Send Mail token"
  (the part after `Zoho-enczapikey`).
- **Resend** — `EMAIL_PROVIDER = "resend"`, `EMAIL_API_KEY` = `re_…` key,
  domain verified in Resend.

Then set in `wrangler.toml` `[vars]`: `NOTIFY_TO = "support@miatools.tech"`,
`NOTIFY_FROM = "forms@miatools.tech"` (an address the provider has verified),
and `npx wrangler secret put EMAIL_API_KEY`. If any of these is empty the email
is skipped and the row is still stored — check `/export`. The email goes to us
only (never to the requester) with `Reply-To` set to the requester.

## Admin export

```sh
curl -fsS -H "Authorization: Bearer $EXPORT_TOKEN" \
  https://forms.miatools.tech/export -o submissions.csv
```

Prefer SSO over a shared token? Put `/export` behind **Cloudflare Access**
(Zero Trust → Access → Applications → self-hosted, path
`forms.miatools.tech/export`, allow only your email). Access then authenticates
before the Worker runs; you can keep the bearer token as a second factor or
leave `EXPORT_TOKEN` unset — but note that with no token the Worker answers
404, so set one when not using Access.

## Tests

```sh
cd workers/forms && node --test test/*.test.js     # or: npm test
```

Plain `node:test`, no dependencies, no network (D1 and `fetch` are faked).
CI runs it in the `worker` job of `.github/workflows/ci.yml`.

Manual checks against a deployed Worker (replace the host):

```sh
H=https://forms.miatools.tech
# no-JS post → 303 to the thank-you page
curl -si -X POST "$H/submit" -H "Origin: https://miatools.tech" \
  --data 'form=pilot&market=us&lang=en&name=Test&email=test@example.com&organisation=Test%20Org' | head -5
# fetch-style → {"ok":true}
curl -s -X POST "$H/submit" -H "Origin: https://miatools.tech" -H "Accept: application/json" \
  --data 'form=pilot&market=mx&lang=es&name=Prueba&email=p@example.com&organisation=Org'
# wrong origin → 403
curl -si -X POST "$H/submit" -H "Origin: https://evil.example" --data 'name=x' | head -1
# honeypot → 303, nothing stored
curl -si -X POST "$H/submit" -H "Origin: https://miatools.tech" \
  --data 'website=spam&market=us&name=x&email=x@example.com&organisation=x' | head -1
# delete the test rows afterwards
npx wrangler d1 execute mia-forms --remote --command "DELETE FROM submissions WHERE email LIKE '%@example.com'"
```

## Retention

Nothing deletes rows automatically. Decide a retention period in the privacy
policy (R4) and prune with e.g.
`npx wrangler d1 execute mia-forms --remote --command "DELETE FROM submissions WHERE created_at < date('now','-24 months')"`.
