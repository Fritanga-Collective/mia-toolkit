// Download configuration + OS detection. No tracking, no external calls.
// The release workflow (.github/workflows/release.yml) auto-updates version /
// macUrl / winUrl on each tagged release and commits this file back to main.
(function () {
  "use strict";

  var CONFIG = {
    version: "0.1.9",
    releasesLatest:
      "https://github.com/Fritanga-Collective/mia-toolkit/releases/latest",
    macUrl:
      "https://github.com/Fritanga-Collective/mia-toolkit/releases/download/v0.1.9/MIA-Toolkit-0.1.9.dmg",
    winUrl:
      "https://github.com/Fritanga-Collective/mia-toolkit/releases/download/v0.1.9/MIA-Toolkit-Setup-0.1.9.exe",
  };

  function detectOS() {
    var ua = (navigator.userAgent || "") + " " +
      ((navigator.userAgentData && navigator.userAgentData.platform) ||
        navigator.platform || "");
    // iOS/iPadOS can't run the desktop app — treat as "other" (some iPads even
    // report as "Mac", but there's no harm in routing them to the general page).
    if (/iPhone|iPad|iPod/i.test(ua)) return "other";
    if (/Mac/i.test(ua)) return "mac";
    if (/Win/i.test(ua)) return "win";
    return "other";
  }

  function macHref() { return CONFIG.macUrl || CONFIG.releasesLatest; }
  function winHref() { return CONFIG.winUrl || CONFIG.releasesLatest; }

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var macLink = document.getElementById("dl-mac");
    var winLink = document.getElementById("dl-win");
    if (macLink) macLink.href = macHref();
    if (winLink) winLink.href = winHref();

    var primary = document.getElementById("dl-primary");
    if (!primary) return;

    var os = detectOS();
    var label = primary.getAttribute("data-label-" + os) ||
      primary.getAttribute("data-label-other");
    primary.querySelector(".label").textContent = label;
    // Default the primary button to the detected OS's installer; anything that
    // isn't clearly macOS or Windows goes to the general Releases page.
    primary.href = os === "mac" ? macHref()
      : os === "win" ? winHref()
      : CONFIG.releasesLatest;

    var ver = document.querySelectorAll(".version");
    for (var i = 0; i < ver.length; i++) ver[i].textContent = CONFIG.version;
  });
})();
