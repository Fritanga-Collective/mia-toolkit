// Download configuration + OS detection. No tracking, no external calls.
// The release workflow (.github/workflows/release.yml) auto-updates version /
// macUrl / winUrl on each tagged release and commits this file back to main.
(function () {
  "use strict";

  var CONFIG = {
    version: "0.1.1",
    releasesLatest:
      "https://github.com/luis-rodriguez/mia-toolkit/releases/latest",
    macUrl:
      "https://github.com/luis-rodriguez/mia-toolkit/releases/download/v0.1.1/MIA-Toolkit-0.1.1.dmg",
    winUrl:
      "https://github.com/luis-rodriguez/mia-toolkit/releases/download/v0.1.1/MIA-Toolkit-Setup-0.1.1.exe",
  };

  function detectOS() {
    var ua = (navigator.userAgent || "") + " " +
      ((navigator.userAgentData && navigator.userAgentData.platform) || "");
    if (/Mac|iPhone|iPad|iPod/i.test(ua)) return "mac";
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
    primary.href = os === "win" ? winHref() : macHref();

    var ver = document.querySelectorAll(".version");
    for (var i = 0; i < ver.length; i++) ver[i].textContent = CONFIG.version;
  });
})();
