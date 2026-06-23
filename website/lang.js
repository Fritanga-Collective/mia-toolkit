// Language routing for the generated /{lang}/ site: auto-select from the
// browser on the English (root) pages, and remember a manual choice so a
// visitor is never bounced against their will.
// Privacy: uses only localStorage (never sent anywhere), no cookies, no
// network. Runs synchronously in <head> so the redirect precedes paint.
(function () {
  "use strict";

  // Non-default languages = the /{code}/ folders build.py generates.
  var EXTRA = ["es", "zh", "ms", "ta", "de", "fr"];
  var KNOWN = ["en"].concat(EXTRA);

  function parts() {
    return location.pathname.split("/").filter(Boolean);
  }
  function pathLang() {
    var p = parts();
    return p.length && EXTRA.indexOf(p[0]) >= 0 ? p[0] : "en";
  }
  function pageName() {
    var p = parts();
    if (pathLang() !== "en") p = p.slice(1);
    var last = p[p.length - 1] || "index.html";
    var name = last.replace(/\.html$/, "");
    return name || "index";
  }
  function urlFor(lang, page) {
    var prefix = lang === "en" ? "/" : "/" + lang + "/";
    return page === "index" ? prefix : prefix + page + ".html";
  }

  function remembered() {
    try { return localStorage.getItem("mia-lang") || ""; } catch (e) { return ""; }
  }
  function remember(code) {
    try { localStorage.setItem("mia-lang", code); } catch (e) {}
  }
  function fromBrowser() {
    var langs = navigator.languages || [navigator.language || ""];
    for (var i = 0; i < langs.length; i++) {
      var l = (langs[i] || "").toLowerCase();
      for (var j = 0; j < KNOWN.length; j++) {
        if (l.indexOf(KNOWN[j]) === 0) return KNOWN[j];
      }
    }
    return "";
  }

  // Remember the language whenever the dropdown is used (the inline onchange
  // still navigates; this just records the explicit choice).
  document.addEventListener("DOMContentLoaded", function () {
    var sel = document.querySelector(".langsel");
    if (sel) sel.addEventListener("change", function () {
      if (!this.value) return;
      var seg = this.value.split("/").filter(Boolean)[0];
      remember(EXTRA.indexOf(seg) >= 0 ? seg : "en");
    });
  });

  // Auto-redirect only from the English (root) pages. A remembered manual
  // choice wins over the browser setting; English stays put. Language pages
  // never redirect, so there are no loops.
  if (pathLang() !== "en") return;
  var pref = remembered() || fromBrowser();
  if (pref && pref !== "en" && EXTRA.indexOf(pref) >= 0) {
    // Preserve ?query and #fragment (e.g. /support.html#institutions must
    // land on /{lang}/support.html#institutions, not the top of the page).
    location.replace(urlFor(pref, pageName()) + location.search + location.hash);
  }
})();
