// Language: auto-select from the browser on the English entry pages, and
// remember a manual choice so a visitor is never bounced against their will.
// Privacy: uses only localStorage (never sent anywhere), no cookies, no network.
// Runs synchronously in <head> so the redirect happens before content paints.
(function () {
  "use strict";

  var FILE_LANG = {            // filename -> language code
    "": "en", "index.html": "en", "support.html": "en",
    "es.html": "es", "soporte.html": "es",
    "zh.html": "zh", "support-zh.html": "zh",
  };
  // Where each English entry page should send a non-English visitor.
  var REDIRECT = {
    "": { es: "es.html", zh: "zh.html" },
    "index.html": { es: "es.html", zh: "zh.html" },
    "support.html": { es: "soporte.html", zh: "support-zh.html" },
  };

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
      if (l.indexOf("es") === 0) return "es";
      if (l.indexOf("zh") === 0) return "zh";
      if (l.indexOf("en") === 0) return "en";
    }
    return "";
  }

  var here = location.pathname.split("/").pop();

  // Remember the language whenever the dropdown is used (the inline onchange
  // still handles navigation; this just records the explicit choice).
  document.addEventListener("DOMContentLoaded", function () {
    var sel = document.querySelector(".langsel");
    if (sel) sel.addEventListener("change", function () {
      if (!this.value) return;
      remember(FILE_LANG[this.value.split("/").pop()] || "en");
    });
  });

  // Auto-redirect only from the English entry pages. A remembered manual choice
  // wins over the browser setting; English (explicit or detected) stays put.
  if (!(here in REDIRECT)) return;
  var pref = remembered() || fromBrowser();
  if (pref && pref !== "en") {
    var dest = REDIRECT[here][pref];
    if (dest) location.replace(dest);
  }
})();
