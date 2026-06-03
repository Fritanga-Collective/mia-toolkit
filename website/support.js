// Support page: fair-trade geo suggestion (client-side, no network, no tracking)
// + Lemon Squeezy "Pay What You Want" checkout link. The download is always
// free; this only suggests a fair amount based on the visitor's region.
(function () {
  "use strict";

  var CONFIG = {
    // Lemon Squeezy "Pay What You Want" checkout URL (replace when the store
    // exists). Until then the button points at the GitHub repo.
    checkout: "https://github.com/luis-rodriguez/mia-toolkit",
    freeDownload:
      "https://github.com/luis-rodriguez/mia-toolkit/releases/latest",
  };

  // Suggested fair-trade amounts (USD); the real local price is handled at
  // checkout. Bands mirror internal notes.
  var BANDS = {
    high: 19,
    upper: 7,
    lower: 3,
    free: 0,
    other: 7,
  };

  // Coarse, privacy-preserving region guess from the browser time zone — no IP
  // lookup, no network call. It only *preselects* the dropdown; the visitor can
  // change it freely.
  var TZ_BAND = {
    "America/Mexico_City": "upper", "America/Tijuana": "upper",
    "America/Monterrey": "upper", "America/Merida": "upper",
    "America/Cancun": "upper", "America/Chihuahua": "upper",
    "America/Hermosillo": "upper", "America/Matamoros": "upper",
    "America/Mazatlan": "upper", "America/Bogota": "upper",
    "America/Lima": "upper", "America/Santiago": "upper",
    "America/Sao_Paulo": "upper", "America/Argentina/Buenos_Aires": "upper",
    "Europe/Istanbul": "upper",
    "Asia/Kolkata": "lower", "Asia/Jakarta": "lower", "Asia/Manila": "lower",
    "Asia/Dhaka": "lower", "Asia/Karachi": "lower", "Africa/Lagos": "lower",
    "America/New_York": "high", "America/Chicago": "high",
    "America/Denver": "high", "America/Los_Angeles": "high",
    "America/Toronto": "high", "America/Vancouver": "high",
    "Australia/Sydney": "high", "Asia/Tokyo": "high", "Asia/Singapore": "high",
  };

  function guessBand() {
    try {
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      if (TZ_BAND[tz]) return TZ_BAND[tz];
      if (/^Europe\//.test(tz) || /^Australia\//.test(tz)) return "high";
    } catch (e) { /* ignore */ }
    return "other";
  }

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var sel = document.getElementById("region");
    var out = document.getElementById("suggestion");
    var btn = document.getElementById("support-btn");
    var free = document.getElementById("free-dl");
    if (free) free.href = CONFIG.freeDownload;
    if (!sel || !out || !btn) return;

    var tmpl = out.getAttribute("data-tmpl") || "Suggested: ${amount}";
    var tmplFree = out.getAttribute("data-tmpl-free") || "Pay later — that's ok.";
    var labelTmpl = btn.getAttribute("data-tmpl") || "Support — ${amount}";
    var labelFree = btn.getAttribute("data-tmpl-free") || "Support if you can";

    function update() {
      var amount = BANDS[sel.value];
      if (amount > 0) {
        out.textContent = tmpl.replace("${amount}", "$" + amount + " USD");
        btn.textContent = labelTmpl.replace("${amount}", "$" + amount);
      } else {
        out.textContent = tmplFree;
        btn.textContent = labelFree;
      }
      btn.href = CONFIG.checkout;
    }

    sel.value = guessBand();
    sel.addEventListener("change", update);
    update();
  });
})();
