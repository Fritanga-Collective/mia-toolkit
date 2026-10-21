// Unit tests for the forms Worker. Plain Node (>=20), no network, no deps:
//   cd workers/forms && node --test test/*.test.js   (or: npm test)
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  handle, validate, toCsv, csvCell, emailRequest, _resetRateLimit, RATE,
  INSERT_SQL, MAX_BODY_BYTES, REQUEST_TYPES, COLUMNS, BRIDGE_LIMITS,
} from "../src/index.js";

const ORIGIN = "https://miatools.tech";

function fakeDB(rows = []) {
  const calls = [];
  return {
    calls,
    rows,
    prepare(sql) {
      return {
        bind(...args) {
          return { run: async () => { calls.push({ sql, args }); return { success: true }; } };
        },
        all: async () => ({ results: rows }),
      };
    },
  };
}

function env(extra = {}) {
  return { DB: fakeDB(), ALLOWED_ORIGINS: ORIGIN, SITE_ORIGIN: ORIGIN, ...extra };
}

const GOOD = {
  form: "pilot", request_type: "pilot", market: "us", lang: "en", utm_campaign: "k7q2",
  name: "Dana Lee", email: "dana@hospital.example", organisation: "General Hospital",
  role: "Imaging manager", discs_per_month: "10-50", pacs: "Acme PACS",
  message: "Hello", website: "",
};

function post(fields, { origin = ORIGIN, accept, json = false, ip = "203.0.113.9", headers = {} } = {}) {
  const h = { ...headers };
  if (origin) h.Origin = origin;
  if (accept) h.Accept = accept;
  if (ip) h["CF-Connecting-IP"] = ip;
  let body;
  if (json) {
    h["Content-Type"] = "application/json";
    body = JSON.stringify(fields);
  } else {
    h["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(fields).toString();
  }
  return new Request("https://forms.example/submit", { method: "POST", headers: h, body });
}

const noFetch = async () => { throw new Error("network not allowed in tests"); };

beforeEach(() => _resetRateLimit());

test("no-JS form post is stored and 303-redirected to the thank-you page", async () => {
  const e = env();
  const r = await handle(post(GOOD), e, undefined, noFetch);
  assert.equal(r.status, 303);
  assert.equal(r.headers.get("Location"), ORIGIN + "/institutions/thanks/");
  assert.equal(e.DB.calls.length, 1);
  assert.equal(e.DB.calls[0].sql, INSERT_SQL);
  assert.deepEqual(e.DB.calls[0].args, [
    "pilot", "pilot", "us", "k7q2", "Dana Lee", "dana@hospital.example", "General Hospital",
    "Imaging manager", "10-50", "Acme PACS", "Hello",
    null, null, null, null, null, null,
  ]);
});

test("request_type: pricing/kit types stored; missing defaults to pilot; unknown rejected", async () => {
  let n = 0;
  for (const t of [...REQUEST_TYPES].filter((x) => x !== "bridge_partner")) {
    const e = env();
    const r = await handle(post({ ...GOOD, request_type: t }, { ip: `192.0.2.${++n}` }),
      e, undefined, noFetch);
    assert.equal(r.status, 303, t);
    assert.equal(e.DB.calls[0].args[1], t);
  }
  const { request_type, ...legacy } = GOOD;
  assert.equal(validate(legacy).row.request_type, "pilot");
  const bad = validate({ ...GOOD, request_type: "pricing_<script>" });
  assert.equal(bad.ok, false);
  assert.ok(bad.errors.includes("request_type"));
  const e = env();
  const r = await handle(post({ ...GOOD, request_type: "free_money" }), e, undefined, noFetch);
  assert.equal(r.status, 400);
  assert.equal(e.DB.calls.length, 0);
  assert.ok(COLUMNS.includes("request_type"));
  const mail = emailRequest(env({ EMAIL_PROVIDER: "resend", EMAIL_API_KEY: "k",
    NOTIFY_TO: "a@b.co", NOTIFY_FROM: "c@d.co" }),
  validate({ ...GOOD, request_type: "pricing_hospital" }).row);
  assert.match(JSON.parse(mail.init.body).subject, /pricing_hospital/);
});

const BRIDGE = {
  form: "bridge_partner", request_type: "bridge_partner", lang: "en", utm_campaign: "b1",
  name: "Sam Tan", email: "sam@imaging.example", organisation: "Imaging Group",
  role: "IT lead", region: "Singapore", discs_per_month: "51-200",
  sites_count: "4", pacs_vendor: "Acme", pacs_version: "7.2", protocol: "dicomweb",
  timeline: "Q1 2027", message: "Interested", website: "",
};
const BRIDGE_ORIGIN = "https://bridge.miatools.tech";

test("bridge_partner: allowed from bridge.miatools.tech, stored with its fields", async () => {
  const e = env({ ALLOWED_ORIGINS: undefined });
  const r = await handle(post(BRIDGE, { origin: BRIDGE_ORIGIN }), e, undefined, noFetch);
  assert.equal(r.status, 303);
  assert.equal(r.headers.get("Location"), "https://bridge.miatools.tech/thanks/");
  const args = e.DB.calls[0].args;
  assert.deepEqual(args.slice(0, 3), ["bridge_partner", "bridge_partner", ""]);
  assert.deepEqual(args.slice(-6), ["4", "Acme", "7.2", "dicomweb", "Q1 2027", "Singapore"]);
  const j = await handle(post(BRIDGE, { origin: BRIDGE_ORIGIN, accept: "application/json", ip: "192.0.2.50" }),
    env({ ALLOWED_ORIGINS: undefined }), undefined, noFetch);
  assert.equal(j.headers.get("Access-Control-Allow-Origin"), BRIDGE_ORIGIN);
  // Default allow-list (no ALLOWED_ORIGINS var) includes both sites, nothing else.
  const evil = await handle(post(BRIDGE, { origin: "https://evil.example", ip: "192.0.2.51" }),
    env({ ALLOWED_ORIGINS: undefined }), undefined, noFetch);
  assert.equal(evil.status, 403);
});

test("bridge_partner: enum + size validation, optional fields become null", () => {
  assert.equal(validate(BRIDGE).ok, true);
  assert.ok(validate({ ...BRIDGE, protocol: "ftp" }).errors.includes("protocol"));
  for (const [k, max] of Object.entries(BRIDGE_LIMITS)) {
    assert.ok(validate({ ...BRIDGE, [k]: "x".repeat(max + 1) }).errors.includes(k), k);
  }
  const minimal = validate({ form: "bridge_partner", name: "A", email: "a@b.co",
    organisation: "Org" });
  assert.equal(minimal.ok, true);
  assert.equal(minimal.row.request_type, "bridge_partner");
  assert.equal(minimal.row.protocol, null);
  assert.equal(minimal.row.sites_count, null);
  // The pilot form still needs a market and can't claim bridge_partner.
  assert.ok(validate({ ...GOOD, market: "" }).errors.includes("market"));
  assert.ok(validate({ ...GOOD, request_type: "bridge_partner" }).errors.includes("request_type"));
  assert.ok(validate({ ...BRIDGE, request_type: "pilot" }).errors.includes("request_type"));
  // Pilot rows carry NULL for the Bridge columns.
  assert.equal(validate(GOOD).row.pacs_vendor, null);
});

test("MX posts redirect to the Spanish thank-you page", async () => {
  const r = await handle(post({ ...GOOD, market: "mx", lang: "es" }), env(), undefined, noFetch);
  assert.equal(r.headers.get("Location"), ORIGIN + "/es/institutions/mx/gracias/");
});

test("fetch (Accept: application/json) gets JSON + CORS", async () => {
  const r = await handle(post(GOOD, { accept: "application/json" }), env(), undefined, noFetch);
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { ok: true });
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGIN);
});

test("JSON bodies are accepted", async () => {
  const e = env();
  const r = await handle(post(GOOD, { json: true }), e, undefined, noFetch);
  assert.equal(r.status, 200);
  assert.equal(e.DB.calls.length, 1);
});

test("other origins and origin-less requests are refused", async () => {
  for (const origin of ["https://evil.example", null]) {
    const e = env();
    const r = await handle(post(GOOD, { origin }), e, undefined, noFetch);
    assert.equal(r.status, 403);
    assert.equal(e.DB.calls.length, 0);
  }
  const ok = await handle(post(GOOD, { origin: null, headers: { Referer: ORIGIN + "/institutions/us/" } }),
    env(), undefined, noFetch);
  assert.equal(ok.status, 303);
});

test("CORS preflight only for allowed origins", async () => {
  const pre = (o) => new Request("https://forms.example/submit",
    { method: "OPTIONS", headers: { Origin: o } });
  const r = await handle(pre(ORIGIN), env());
  assert.equal(r.status, 204);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGIN);
  assert.equal((await handle(pre("https://evil.example"), env())).status, 403);
});

test("honeypot: silently accepted, nothing stored", async () => {
  const e = env();
  const r = await handle(post({ ...GOOD, website: "http://spam" }), e, undefined, noFetch);
  assert.equal(r.status, 303);
  assert.equal(e.DB.calls.length, 0);
  const j = await handle(post({ ...GOOD, website: "x" }, { accept: "application/json" }), e, undefined, noFetch);
  assert.deepEqual(await j.json(), { ok: true });
  assert.equal(e.DB.calls.length, 0);
});

test("validation: required fields, email, enums, size limits", () => {
  assert.equal(validate(GOOD).ok, true);
  for (const k of ["name", "email", "organisation"]) {
    const v = validate({ ...GOOD, [k]: "" });
    assert.equal(v.ok, false);
    assert.ok(v.errors.includes(k), k);
  }
  assert.ok(validate({ ...GOOD, email: "not-an-email" }).errors.includes("email"));
  assert.ok(validate({ ...GOOD, market: "fr" }).errors.includes("market"));
  assert.ok(validate({ ...GOOD, form: "other" }).errors.includes("form"));
  assert.ok(validate({ ...GOOD, discs_per_month: "9999" }).errors.includes("discs_per_month"));
  assert.ok(validate({ ...GOOD, message: "x".repeat(2001) }).errors.includes("message"));
  assert.ok(validate({ ...GOOD, name: "x".repeat(121) }).errors.includes("name"));
  // Bad campaign codes are dropped, not rejected.
  const v = validate({ ...GOOD, utm_campaign: "<script>" });
  assert.equal(v.ok, true);
  assert.equal(v.row.campaign, "");
  // Control characters are stripped.
  assert.equal(validate({ ...GOOD, name: "Dana\u0000 Lee" }).row.name, "Dana Lee");
});

test("invalid no-JS post gets a 400 page and nothing is stored", async () => {
  const e = env();
  const r = await handle(post({ ...GOOD, email: "nope", lang: "es", market: "mx" }), e, undefined, noFetch);
  assert.equal(r.status, 400);
  assert.match(await r.text(), /Revise el formulario/);
  assert.equal(e.DB.calls.length, 0);
});

test("oversized body is rejected", async () => {
  const e = env();
  const r = await handle(post({ ...GOOD, message: "x".repeat(MAX_BODY_BYTES + 10) }), e, undefined, noFetch);
  assert.equal(r.status, 413);
  assert.equal(e.DB.calls.length, 0);
});

test("in-memory rate limit per client; IP never stored", async () => {
  const e = env();
  let last;
  for (let i = 0; i < RATE.max + 1; i++) {
    last = await handle(post(GOOD, { ip: "198.51.100.7" }), e, undefined, noFetch);
  }
  assert.equal(last.status, 429);
  assert.equal(e.DB.calls.length, RATE.max);
  for (const c of e.DB.calls) assert.ok(!c.args.includes("198.51.100.7"));
  // A different client is unaffected.
  const other = await handle(post(GOOD, { ip: "198.51.100.8" }), e, undefined, noFetch);
  assert.equal(other.status, 303);
});

test("notification email is skipped unless configured", async () => {
  assert.equal(emailRequest(env(), validate(GOOD).row), null);
  const z = emailRequest(env({ EMAIL_PROVIDER: "zeptomail", EMAIL_API_KEY: "k",
    NOTIFY_TO: "support@miatools.tech", NOTIFY_FROM: "forms@miatools.tech" }), validate(GOOD).row);
  assert.equal(z.url, "https://api.zeptomail.com/v1.1/email");
  assert.equal(z.init.headers.Authorization, "Zoho-enczapikey k");
  const rs = emailRequest(env({ EMAIL_PROVIDER: "resend", EMAIL_API_KEY: "k",
    NOTIFY_TO: "a@b.co", NOTIFY_FROM: "c@d.co" }), validate(GOOD).row);
  assert.equal(rs.url, "https://api.resend.com/emails");
  assert.equal(JSON.parse(rs.init.body).reply_to, "dana@hospital.example");
});

test("configured email is sent via the injected fetch after storing", async () => {
  const sent = [];
  const fakeFetch = async (url, init) => { sent.push({ url, init }); return new Response("{}", { status: 200 }); };
  const waits = [];
  const ctx = { waitUntil: (p) => waits.push(p) };
  const e = env({ EMAIL_PROVIDER: "resend", EMAIL_API_KEY: "k", NOTIFY_TO: "a@b.co", NOTIFY_FROM: "c@d.co" });
  const r = await handle(post(GOOD), e, ctx, fakeFetch);
  await Promise.all(waits);
  assert.equal(r.status, 303);
  assert.equal(sent.length, 1);
  assert.equal(e.DB.calls.length, 1);
});

test("export needs the bearer token and neutralises formulas", async () => {
  const rows = [{ id: 1, created_at: "2026-10-20T00:00:00Z", form: "pilot",
    request_type: "pricing_network", market: "us",
    campaign: "", name: "=HYPERLINK(\"x\")", email: "a@b.co", organisation: "Org, Inc",
    role: "", discs_per_month: "", pacs: "", message: "line1\nline2" }];
  const e = { ...env(), DB: fakeDB(rows), EXPORT_TOKEN: "s3cret-token" };
  const req = (auth) => new Request("https://forms.example/export",
    { headers: auth ? { Authorization: auth } : {} });
  assert.equal((await handle(req(), e)).status, 401);
  assert.equal((await handle(req("Bearer wrong"), e)).status, 401);
  const ok = await handle(req("Bearer s3cret-token"), e);
  assert.equal(ok.status, 200);
  assert.match(ok.headers.get("Content-Type"), /text\/csv/);
  const csv = await ok.text();
  assert.ok(csv.startsWith("id,created_at,form,request_type,market,campaign,name,email,"));
  assert.ok(csv.includes(",pricing_network,us,"));
  assert.ok(csv.includes(`"'=HYPERLINK(""x"")"`));
  assert.ok(csv.includes('"Org, Inc"'));
  assert.ok(csv.includes('"line1\nline2"'));
  // No token configured → endpoint does not exist.
  assert.equal((await handle(req("Bearer x"), env())).status, 404);
});

test("csv helpers", () => {
  assert.equal(csvCell("+1"), "'+1");
  assert.equal(csvCell(null), "");
  assert.equal(toCsv([]).split("\r\n")[0].split(",").length, 19);
});

test("other routes and methods", async () => {
  assert.equal((await handle(new Request("https://forms.example/submit"), env())).status, 405);
  assert.equal((await handle(new Request("https://forms.example/"), env())).status, 404);
  assert.equal(await (await handle(new Request("https://forms.example/health"), env())).text(), "ok");
});
