/**
 * MIA Tools — forms Worker (Cloudflare Workers + D1).
 *
 * Receives the institutional pilot-request form from https://miatools.tech
 * (and the MIA Bridge design-partner form from https://bridge.miatools.tech),
 * validates it, stores one row in D1 and either 303-redirects (plain HTML
 * POST, no JS) or answers JSON (fetch from website/inst.js).
 *
 * Privacy rules this file keeps (see README.md):
 *   - No IP address is ever written to D1 or to logs. The rate limiter keeps
 *     a short-lived in-memory counter per isolate only, keyed by a salted
 *     hash of the client IP; it disappears when the isolate is recycled.
 *   - No cookies are set or read.
 *   - Error logs never include submitted field values.
 *
 * Routes:
 *   POST /submit   form-urlencoded or JSON → store → 303 / JSON
 *   OPTIONS /submit  CORS preflight (allowed origins only)
 *   GET /export    CSV of all rows; needs "Authorization: Bearer <EXPORT_TOKEN>"
 *   GET /health    "ok"
 */

export const LIMITS = {
  name: 120,
  email: 254,
  organisation: 200,
  role: 120,
  pacs: 200,
  message: 2000,
};
// MIA Bridge design-partner form (form=bridge_partner, bridge.miatools.tech;
// field table in the mia-bridge-site README). It sends no `market`; `role`
// is an enum there and, with `country`, required. The other enums are
// optional ("" allowed) and stored as NULL when empty.
export const BRIDGE_ENUMS = {
  role: new Set(["clinical", "management", "it", "other"]),
  country: new Set(["mx", "us", "sg", "latam", "other"]),
  segment: new Set(["", "chain", "imaging_centre", "hospital", "telerad", "other"]),
  sites: new Set(["", "1", "2-5", "6-20", "gt20"]),
  protocol: new Set(["", "dimse", "dicomweb", "both", "unsure"]),
  timeline: new Set(["", "now", "1-3m", "3-6m", "exploring"]),
};
export const BRIDGE_REQUIRED = new Set(["role", "country"]);
export const BRIDGE_COLUMNS = ["country", "segment", "sites", "protocol", "timeline"];
// Keep in sync with the Bridge site's thank-you pages.
export const BRIDGE_THANKS = { es: "/gracias/", en: "/en/thanks/" };
export const BRIDGE_HOME = { es: "/", en: "/en/" };
export const MAX_BODY_BYTES = 16 * 1024;
export const FORMS = new Set(["pilot", "bridge_partner"]);
export const MARKETS = new Set(["mx", "us", "sg"]);
// What the visitor clicked before the form opened (pilot CTA, a pricing
// tier, the procurement kit). Keep in sync with INST_REQUEST_TYPES in
// website/build.py. Missing = "pilot" (older pages); unknown = rejected.
export const REQUEST_TYPES = new Set(["pilot", "pricing_clinic",
  "pricing_hospital", "pricing_network", "pricing_public", "kit",
  "bridge_partner"]);
// Keep in sync with INST_DISC_RANGES in website/build.py.
export const DISCS = new Set(["", "lt10", "10-50", "51-200", "gt200", "unsure"]);
// Keep in sync with INST_THANKS in website/build.py.
export const THANKS = {
  mx: "/es/institutions/mx/gracias/",
  us: "/institutions/thanks/",
  sg: "/institutions/thanks/",
};
const EMAIL_RE = /^[^\s@<>"',;]+@[^\s@<>"',;]+\.[^\s@<>"',;]{2,}$/;
const CAMPAIGN_RE = /^[A-Za-z0-9_-]{1,32}$/;

// ───────────────────────── rate limit (in memory) ─────────────────────────
export const RATE = { windowMs: 10 * 60 * 1000, max: 5 };
const buckets = new Map(); // hashed-ip -> { count, reset }
// Per-isolate random salt, created lazily (Workers forbid generating random
// values in global scope).
let SALT = null;

async function rateKey(ip) {
  if (!SALT) SALT = crypto.getRandomValues(new Uint8Array(16));
  const data = new Uint8Array([...SALT, ...new TextEncoder().encode(ip)]);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return btoa(String.fromCharCode(...new Uint8Array(digest).slice(0, 12)));
}

export async function rateLimited(ip, now = Date.now()) {
  if (!ip) return false;
  const key = await rateKey(ip);
  if (buckets.size > 5000) {
    for (const [k, b] of buckets) if (b.reset <= now) buckets.delete(k);
  }
  const b = buckets.get(key);
  if (!b || b.reset <= now) {
    buckets.set(key, { count: 1, reset: now + RATE.windowMs });
    return false;
  }
  b.count += 1;
  return b.count > RATE.max;
}

export function _resetRateLimit() {
  buckets.clear();
}

// ───────────────────────────── helpers ─────────────────────────────
function allowedOrigins(env) {
  return (env.ALLOWED_ORIGINS || "https://miatools.tech,https://bridge.miatools.tech")
    .split(",").map((s) => s.trim()).filter(Boolean);
}

function siteOrigin(env) {
  return (env.SITE_ORIGIN || "https://miatools.tech").replace(/\/+$/, "");
}

/** The request's origin if it is on the allow-list, else null. Browsers send
 * Origin on every cross-origin POST (form or fetch); Referer is a fallback for
 * old clients. A request with neither is refused. */
export function checkOrigin(request, env) {
  const allowed = allowedOrigins(env);
  const origin = request.headers.get("Origin");
  if (origin) return allowed.includes(origin) ? origin : null;
  const ref = request.headers.get("Referer");
  if (ref) {
    try {
      const o = new URL(ref).origin;
      return allowed.includes(o) ? o : null;
    } catch {
      return null;
    }
  }
  return null;
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function clean(v, max) {
  if (typeof v !== "string") v = v == null ? "" : String(v);
  // Drop control characters except tab/newline; normalise newlines; trim.
  v = v.replace(/\r\n?/g, "\n").replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "");
  v = v.trim();
  return v.length > max ? null : v;
}

/** Validate a submission. Returns { ok, row, errors, spam }. */
export function validate(input) {
  const errors = [];
  const get = (k) => (input[k] == null ? "" : input[k]);
  if (clean(get("website"), 500)) return { ok: true, spam: true }; // honeypot

  const form = clean(get("form"), 20) || "pilot";
  if (!FORMS.has(form)) errors.push("form");
  const bridge = form === "bridge_partner";
  let market = clean(get("market"), 4) || "";
  // The Bridge form sends no market (country comes in `country`): skip the
  // check there. The pilot form must name one of its market pages.
  if (bridge) market = MARKETS.has(market) ? market : "";
  else if (!MARKETS.has(market)) errors.push("market");

  const requestType = clean(get("request_type"), 32) || (bridge ? "bridge_partner" : "pilot");
  if (!REQUEST_TYPES.has(requestType)) errors.push("request_type");
  // bridge_partner goes with the Bridge form only, and vice versa.
  if (bridge !== (requestType === "bridge_partner")) errors.push("request_type");

  const row = { form, market, request_type: requestType };
  for (const [k, max] of Object.entries(LIMITS)) {
    const v = clean(get(k), max);
    if (v === null) errors.push(k);
    row[k] = v || "";
  }
  if (!row.name) errors.push("name");
  if (!row.organisation) errors.push("organisation");
  if (!row.email || !EMAIL_RE.test(row.email)) errors.push("email");

  for (const k of BRIDGE_COLUMNS) row[k] = null;
  if (bridge) {
    for (const [k, allowed] of Object.entries(BRIDGE_ENUMS)) {
      const v = clean(get(k), 20);
      if (v === null || !allowed.has(v) || (BRIDGE_REQUIRED.has(k) && !v)) {
        errors.push(k);
        continue;
      }
      if (k === "role") row.role = v;
      else row[k] = v || null;
    }
  }

  const discs = clean(get("discs_per_month"), 10);
  row.discs_per_month = discs !== null && DISCS.has(discs) ? discs : "";
  if (discs !== null && discs && !DISCS.has(discs)) errors.push("discs_per_month");

  // Campaign code: opaque, short; anything else is silently dropped.
  const c = clean(get("utm_campaign") || get("campaign"), 64) || "";
  row.campaign = CAMPAIGN_RE.test(c) ? c : "";

  const lang = clean(get("lang"), 5);
  row.lang = lang === "es" ? "es" : "en";

  return { ok: errors.length === 0, row, errors: [...new Set(errors)] };
}

async function readBody(request) {
  const len = Number(request.headers.get("Content-Length") || "0");
  if (len > MAX_BODY_BYTES) return { tooLarge: true };
  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
    return { tooLarge: true };
  }
  const type = (request.headers.get("Content-Type") || "").toLowerCase();
  if (type.startsWith("application/json")) {
    try {
      const data = JSON.parse(text);
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        return { bad: true };
      }
      return { data, json: true };
    } catch {
      return { bad: true };
    }
  }
  if (type.startsWith("application/x-www-form-urlencoded") || type === "") {
    return { data: Object.fromEntries(new URLSearchParams(text)) };
  }
  return { bad: true };
}

function wantsJson(request, parsed) {
  const accept = (request.headers.get("Accept") || "").toLowerCase();
  return Boolean(parsed && parsed.json) || accept.includes("application/json");
}

function json(body, status, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store", ...headers },
  });
}

const ERROR_PAGE = {
  en: { title: "Please check the form",
    p: "Some fields were missing or too long. Please go back, check the form and send it again — or email us at support@miatools.tech.",
    back: "Back" },
  es: { title: "Revise el formulario",
    p: "Faltan algunos campos o son demasiado largos. Regrese, revise el formulario y envíelo de nuevo, o escríbanos a support@miatools.tech.",
    back: "Regresar" },
};

function errorPage(lang, status, backUrl) {
  const t = ERROR_PAGE[lang] || ERROR_PAGE.en;
  const html = `<!DOCTYPE html><html lang="${lang === "es" ? "es-MX" : "en"}"><head>`
    + `<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">`
    + `<meta name="robots" content="noindex"><title>${t.title}</title></head>`
    + `<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 16px;line-height:1.5">`
    + `<h1>${t.title}</h1><p>${t.p}</p><p><a href="${backUrl}">${t.back}</a></p></body></html>`;
  return new Response(html, { status,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
}

function marketPage(env, market) {
  const path = market === "mx" ? "/es/institutions/mx/" : `/institutions/${MARKETS.has(market) ? market + "/" : ""}`;
  return siteOrigin(env) + path + "#pilot";
}

// ───────────────────────────── storage ─────────────────────────────
export const INSERT_SQL =
  "INSERT INTO submissions (form, request_type, market, campaign, name, email, "
  + "organisation, role, discs_per_month, pacs, message, country, segment, "
  + "sites, protocol, timeline) "
  + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

async function store(env, row) {
  await env.DB.prepare(INSERT_SQL).bind(
    row.form, row.request_type, row.market, row.campaign, row.name, row.email, row.organisation,
    row.role, row.discs_per_month, row.pacs, row.message, row.country,
    row.segment, row.sites, row.protocol, row.timeline,
  ).run();
}

// ─────────────────────── optional notification email ───────────────────────
/** Build the provider request (or null when email is not configured).
 * EMAIL_PROVIDER = "zeptomail" | "resend"; EMAIL_API_KEY (secret);
 * NOTIFY_TO (e.g. support@miatools.tech); NOTIFY_FROM (a verified sender). */
export function emailRequest(env, row) {
  const provider = (env.EMAIL_PROVIDER || "").toLowerCase();
  if (!provider || !env.EMAIL_API_KEY || !env.NOTIFY_TO || !env.NOTIFY_FROM) {
    return null;
  }
  const subject = `New ${row.request_type} request — ${row.organisation} (${(row.market || row.country || "-").toUpperCase()})`;
  const text = [
    `Form: ${row.form}`, `Request type: ${row.request_type}`, `Market: ${row.market}`,
    `Campaign: ${row.campaign || "-"}`, `Name: ${row.name}`,
    `Email: ${row.email}`, `Organisation: ${row.organisation}`,
    `Role: ${row.role || "-"}`, `Discs per month: ${row.discs_per_month || "-"}`,
    `PACS/viewer: ${row.pacs || "-"}`,
    ...(row.form === "bridge_partner" ? [
      `Country: ${row.country || "-"}`, `Segment: ${row.segment || "-"}`,
      `Sites: ${row.sites || "-"}`, `Protocol: ${row.protocol || "-"}`,
      `Timeline: ${row.timeline || "-"}`,
    ] : []),
    "", row.message || "(no message)",
  ].join("\n");
  if (provider === "zeptomail") {
    return {
      url: "https://api.zeptomail.com/v1.1/email",
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json",
          "Authorization": `Zoho-enczapikey ${env.EMAIL_API_KEY}` },
        body: JSON.stringify({
          from: { address: env.NOTIFY_FROM, name: "MIA Tools forms" },
          to: [{ email_address: { address: env.NOTIFY_TO } }],
          reply_to: [{ address: row.email, name: row.name }],
          subject, textbody: text,
        }),
      },
    };
  }
  if (provider === "resend") {
    return {
      url: "https://api.resend.com/emails",
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json",
          "Authorization": `Bearer ${env.EMAIL_API_KEY}` },
        body: JSON.stringify({ from: env.NOTIFY_FROM, to: [env.NOTIFY_TO],
          reply_to: row.email, subject, text }),
      },
    };
  }
  return null;
}

async function notify(env, row, fetchImpl) {
  const req = emailRequest(env, row);
  if (!req) return;
  try {
    const r = await fetchImpl(req.url, req.init);
    if (!r.ok) console.error(`notify: provider answered ${r.status}`);
  } catch (e) {
    console.error("notify: request failed");
  }
}

// ───────────────────────────── export (CSV) ─────────────────────────────
export const COLUMNS = ["id", "created_at", "form", "request_type", "market",
  "campaign", "name",
  "email", "organisation", "role", "discs_per_month", "pacs", "message",
  ...BRIDGE_COLUMNS];

export function csvCell(v) {
  let s = v == null ? "" : String(v);
  // Neutralise spreadsheet formula injection (=, +, -, @, tab, CR).
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(rows) {
  const lines = [COLUMNS.join(",")];
  for (const r of rows) lines.push(COLUMNS.map((c) => csvCell(r[c])).join(","));
  return lines.join("\r\n") + "\r\n";
}

function timingSafeEqual(a, b) {
  const ea = new TextEncoder().encode(a);
  const eb = new TextEncoder().encode(b);
  let diff = ea.length ^ eb.length;
  for (let i = 0; i < Math.max(ea.length, eb.length); i++) {
    diff |= (ea[i] || 0) ^ (eb[i] || 0);
  }
  return diff === 0;
}

async function handleExport(request, env) {
  if (!env.EXPORT_TOKEN) return new Response("Not found", { status: 404 });
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!token || !timingSafeEqual(token, env.EXPORT_TOKEN)) {
    return new Response("Unauthorized", { status: 401,
      headers: { "WWW-Authenticate": "Bearer", "Cache-Control": "no-store" } });
  }
  const { results } = await env.DB.prepare(
    `SELECT ${COLUMNS.join(", ")} FROM submissions ORDER BY id`).all();
  return new Response(toCsv(results || []), {
    status: 200,
    headers: { "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="submissions.csv"',
      "Cache-Control": "no-store" },
  });
}

// ───────────────────────────── submit ─────────────────────────────
async function handleSubmit(request, env, ctx, fetchImpl) {
  const origin = checkOrigin(request, env);
  if (!origin) return new Response("Forbidden", { status: 403 });
  const cors = corsHeaders(origin);

  const ip = request.headers.get("CF-Connecting-IP") || "";
  if (await rateLimited(ip)) {
    return wantsJson(request, null)
      ? json({ ok: false, error: "rate_limited" }, 429, cors)
      : new Response("Too many requests — please try again later.",
        { status: 429, headers: cors });
  }

  const parsed = await readBody(request);
  const asJson = wantsJson(request, parsed);
  if (parsed.tooLarge) {
    return asJson ? json({ ok: false, error: "too_large" }, 413, cors)
      : new Response("Payload too large", { status: 413, headers: cors });
  }
  if (parsed.bad) {
    return asJson ? json({ ok: false, error: "bad_request" }, 400, cors)
      : new Response("Bad request", { status: 400, headers: cors });
  }

  const v = validate(parsed.data);
  const market = MARKETS.has(parsed.data.market) ? parsed.data.market : "us";
  const isBridge = parsed.data.form === "bridge_partner";
  const blang = parsed.data.lang === "en" ? "en" : "es";  // Bridge default: es
  const bridgeOrigin = (env.BRIDGE_ORIGIN || "https://bridge.miatools.tech").replace(/\/+$/, "");
  const thanks = isBridge ? bridgeOrigin + BRIDGE_THANKS[blang]
    : siteOrigin(env) + THANKS[market];
  const back = isBridge ? bridgeOrigin + BRIDGE_HOME[blang] : marketPage(env, market);
  if (v.spam) {
    // Honeypot filled: pretend success, store nothing.
    return asJson ? json({ ok: true }, 200, cors)
      : new Response(null, { status: 303, headers: { ...cors, Location: thanks } });
  }
  if (!v.ok) {
    return asJson ? json({ ok: false, error: "invalid", fields: v.errors }, 400, cors)
      : errorPage(parsed.data.lang === "es" ? "es" : "en", 400, back);
  }

  try {
    await store(env, v.row);
  } catch (e) {
    console.error("store: D1 insert failed");
    return asJson ? json({ ok: false, error: "server" }, 500, cors)
      : errorPage(v.row.lang, 500, back);
  }
  const send = notify(env, v.row, fetchImpl);
  if (ctx && typeof ctx.waitUntil === "function") ctx.waitUntil(send);
  else await send;

  return asJson ? json({ ok: true }, 200, cors)
    : new Response(null, { status: 303, headers: { ...cors, Location: thanks } });
}

export async function handle(request, env, ctx, fetchImpl = fetch) {
  const url = new URL(request.url);
  if (url.pathname === "/submit") {
    if (request.method === "OPTIONS") {
      const origin = checkOrigin(request, env);
      return origin ? new Response(null, { status: 204, headers: corsHeaders(origin) })
        : new Response(null, { status: 403 });
    }
    if (request.method === "POST") return handleSubmit(request, env, ctx, fetchImpl);
    return new Response("Method not allowed", { status: 405, headers: { Allow: "POST, OPTIONS" } });
  }
  if (url.pathname === "/export" && request.method === "GET") {
    return handleExport(request, env);
  }
  if (url.pathname === "/health") return new Response("ok");
  return new Response("Not found", { status: 404 });
}

export default {
  fetch(request, env, ctx) {
    return handle(request, env, ctx);
  },
};
