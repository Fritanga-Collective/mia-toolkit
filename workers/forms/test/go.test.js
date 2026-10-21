// Unit tests for the go links (go.miatools.tech/<code>) and /export-links.
// Plain Node (>=20), no network, no deps: node --test test/*.test.js
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  handle, goCode, isAutomated, goTarget, linksCsv, GO_HIT_SQL, GO_PEEK_SQL,
  LINK_COLUMNS,
} from "../src/index.js";

const SITE = "https://miatools.tech";
const BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 "
  + "(KHTML, like Gecko) Version/18.0 Safari/605.1.15";

// A tiny in-memory stand-in for the D1 `links` table that runs the two
// statements the Worker uses.
function linksDB(rows) {
  const table = new Map(rows.map((r) => [r.code, { clicks: 0, last_click: null, active: 1, ...r }]));
  const calls = [];
  return {
    calls,
    table,
    prepare(sql) {
      return {
        bind(...args) {
          return {
            first: async () => {
              calls.push({ sql, args });
              if (sql === GO_HIT_SQL) {
                const [day, code] = args;
                const r = table.get(code);
                if (!r || r.active !== 1) return null;
                r.clicks += 1;
                r.last_click = day;
                return { market: r.market };
              }
              if (sql === GO_PEEK_SQL) {
                const r = table.get(args[0]);
                return r && r.active === 1 ? { market: r.market } : null;
              }
              throw new Error("unexpected SQL " + sql);
            },
          };
        },
        all: async () => ({ results: [...table.values()] }),
      };
    },
  };
}

function env(rows = [], extra = {}) {
  return { DB: linksDB(rows), SITE_ORIGIN: SITE, GO_HOST: "go.miatools.tech", ...extra };
}

const ROWS = [
  { code: "k7q2", market: "us", lang: "en" },
  { code: "kmx4", market: "mx", lang: "es" },
  { code: "ksg5", market: "sg", lang: "en" },
  { code: "kold", market: "mx", lang: "es", active: 0 },
];

function get(url, { method = "GET", ua = BROWSER, headers = {} } = {}) {
  const h = { ...headers };
  if (ua) h["User-Agent"] = ua;
  return new Request(url, { method, headers: h });
}

test("go host: /<code> 302s to the market page with the code, and counts the click", async () => {
  const e = env(ROWS);
  const r = await handle(get("https://go.miatools.tech/k7q2"), e);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), SITE + "/institutions/us/?utm_source=o&utm_campaign=k7q2");
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  assert.equal(r.headers.get("Set-Cookie"), null);
  const row = e.DB.table.get("k7q2");
  assert.equal(row.clicks, 1);
  assert.match(row.last_click, /^\d{4}-\d{2}-\d{2}$/); // UTC date only, no time
});

test("each market maps to its page; /go/<code> works on the forms host too", async () => {
  const e = env(ROWS);
  const mx = await handle(get("https://forms.miatools.tech/go/kmx4/"), e);
  assert.equal(mx.headers.get("Location"), SITE + "/es/institutions/mx/?utm_source=o&utm_campaign=kmx4");
  const sg = await handle(get("https://go.miatools.tech/go/KSG5"), e);
  assert.equal(sg.headers.get("Location"), SITE + "/institutions/sg/?utm_source=o&utm_campaign=ksg5");
  assert.equal(e.DB.table.get("kmx4").clicks, 1);
  assert.equal(e.DB.table.get("ksg5").clicks, 1);
});

test("unknown, inactive, malformed codes and the go root → neutral hub, no utm", async () => {
  const e = env(ROWS);
  for (const u of ["https://go.miatools.tech/kzzz", "https://go.miatools.tech/kold",
    "https://go.miatools.tech/not-a-code", "https://go.miatools.tech/", "https://go.miatools.tech",
    "https://forms.miatools.tech/go/k1q2"]) {
    const r = await handle(get(u), e);
    assert.equal(r.status, 302, u);
    assert.equal(r.headers.get("Location"), SITE + "/institutions/", u);
  }
  assert.equal(e.DB.table.get("kold").clicks, 0);
  // Malformed codes never reach the database.
  assert.ok(e.DB.calls.every((c) => /^k[a-z2-7]{3}$/.test(c.args[c.args.length - 1])));
});

test("HEAD, prefetch and preview bots are redirected but not counted", async () => {
  const e = env(ROWS);
  const reqs = [
    get("https://go.miatools.tech/k7q2", { method: "HEAD" }),
    get("https://go.miatools.tech/k7q2", { headers: { "Sec-Purpose": "prefetch" } }),
    get("https://go.miatools.tech/k7q2", { headers: { Purpose: "prefetch" } }),
    get("https://go.miatools.tech/k7q2", { ua: "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)" }),
    get("https://go.miatools.tech/k7q2", { ua: "LinkedInBot/1.0 (compatible; Mozilla/5.0)" }),
    get("https://go.miatools.tech/k7q2", { ua: "facebookexternalhit/1.1" }),
    get("https://go.miatools.tech/k7q2", { ua: "WhatsApp/2.23.20.0 A" }),
    get("https://go.miatools.tech/k7q2", { ua: "Mozilla/5.0 (compatible; Googlebot/2.1)" }),
    get("https://go.miatools.tech/k7q2", { ua: "Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0)" }),
    get("https://go.miatools.tech/k7q2", { ua: "curl/8.7.1" }),
    get("https://go.miatools.tech/k7q2", { ua: "" }),
  ];
  for (const req of reqs) {
    const r = await handle(req, e);
    assert.equal(r.status, 302);
    assert.equal(r.headers.get("Location"), SITE + "/institutions/us/?utm_source=o&utm_campaign=k7q2");
  }
  assert.equal(e.DB.table.get("k7q2").clicks, 0);
  assert.ok(e.DB.calls.every((c) => c.sql === GO_PEEK_SQL));
  // An in-app browser is a person and does count.
  await handle(get("https://go.miatools.tech/k7q2", { ua: BROWSER + " [LinkedInApp]" }), e);
  assert.equal(e.DB.table.get("k7q2").clicks, 1);
});

test("nothing about the visitor reaches the database", async () => {
  const e = env(ROWS);
  await handle(get("https://go.miatools.tech/k7q2", { headers: {
    "CF-Connecting-IP": "203.0.113.7", Cookie: "a=b", Referer: "https://mail.example/" } }), e);
  const flat = JSON.stringify(e.DB.calls);
  assert.ok(!flat.includes("203.0.113.7"));
  assert.ok(!flat.includes("Safari"));
  assert.ok(!flat.includes("mail.example"));
  assert.deepEqual(e.DB.calls[0].args.length, 2); // [utc date, code]
});

test("D1 failure still redirects (to the hub)", async () => {
  const e = { SITE_ORIGIN: SITE, DB: { prepare() { throw new Error("down"); } } };
  const r = await handle(get("https://go.miatools.tech/k7q2"), e);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), SITE + "/institutions/");
});

test("forms host paths that are not go links keep their old behaviour", async () => {
  const e = env(ROWS);
  assert.equal((await handle(get("https://forms.miatools.tech/k7q2"), e)).status, 404);
  assert.equal(await (await handle(get("https://forms.miatools.tech/health"), e)).text(), "ok");
  assert.equal((await handle(new Request("https://go.miatools.tech/k7q2", { method: "POST" }), e)).status, 404);
});

test("goCode / isAutomated / goTarget helpers", () => {
  const e = { GO_HOST: "go.miatools.tech" };
  assert.equal(goCode(new URL("https://go.miatools.tech/K7Q2/"), e), "k7q2");
  assert.equal(goCode(new URL("https://go.miatools.tech/"), e), "");
  assert.equal(goCode(new URL("https://go.miatools.tech/a/b"), e), null);
  assert.equal(goCode(new URL("https://forms.miatools.tech/export"), e), null);
  assert.equal(isAutomated(get("https://x/", { method: "HEAD" })), true);
  assert.equal(isAutomated(get("https://x/")), false);
  assert.equal(goTarget({ SITE_ORIGIN: SITE }, "zz", "k7q2"), SITE + "/institutions/");
});

test("export-links needs the bearer token and returns the CSV", async () => {
  const e = env(ROWS, { EXPORT_TOKEN: "s3cret-token" });
  e.DB.table.get("k7q2").clicks = 3;
  e.DB.table.get("k7q2").last_click = "2026-10-20";
  const req = (auth) => new Request("https://forms.miatools.tech/export-links",
    { headers: auth ? { Authorization: auth } : {} });
  assert.equal((await handle(req(), e)).status, 401);
  assert.equal((await handle(req("Bearer nope"), e)).status, 401);
  const ok = await handle(req("Bearer s3cret-token"), e);
  assert.equal(ok.status, 200);
  assert.match(ok.headers.get("Content-Type"), /text\/csv/);
  const lines = (await ok.text()).trim().split("\r\n");
  assert.equal(lines[0], LINK_COLUMNS.join(","));
  assert.equal(lines[0], "code,market,lang,active,clicks,last_click");
  assert.ok(lines.includes("k7q2,us,en,1,3,2026-10-20"));
  assert.ok(lines.includes("kold,mx,es,0,0,"));
  assert.equal((await handle(req("Bearer x"), env(ROWS))).status, 404);
  assert.equal(linksCsv([]), "code,market,lang,active,clicks,last_click\r\n");
});
