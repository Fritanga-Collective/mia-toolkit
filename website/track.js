/* MIA Tools — first-party, name-only event counting.
 *
 * miaTrack("pilot_cta_click:sg") forwards ONE short event NAME to whichever
 * cookieless analytics the build configured (ANALYTICS_PROVIDER in
 * website/build.py, substituted below at build time). The name is the whole
 * payload: no field values, no emails, no names, no URLs, no identifiers —
 * just an aggregate "this button was clicked" counter. Names are restricted
 * to [A-Za-z0-9_:-] and 64 characters, so free text can never slip through.
 *
 * If no provider is configured, or its script is blocked or not loaded yet,
 * miaTrack is a silent no-op. No cookies, no storage, no network of its own.
 */
(function () {
  "use strict";

  var PROVIDER = "__ANALYTICS_PROVIDER__"; // "goatcounter" | "umami" | "plausible" | ""

  function clean(name) {
    name = String(name || "").replace(/[^A-Za-z0-9_:-]/g, "");
    return name.slice(0, 64);
  }

  function send(name) {
    var w = window;
    if (PROVIDER === "goatcounter") {
      // https://www.goatcounter.com/help/events
      if (w.goatcounter && typeof w.goatcounter.count === "function") {
        w.goatcounter.count({ path: name, title: name, event: true });
      }
    } else if (PROVIDER === "umami") {
      if (w.umami && typeof w.umami.track === "function") w.umami.track(name);
    } else if (PROVIDER === "plausible") {
      if (typeof w.plausible === "function") w.plausible(name);
    }
  }

  window.miaTrack = function (name) {
    var n = clean(name);
    if (!n) return;
    try { send(n); } catch (e) { /* analytics must never break the page */ }
  };
})();
