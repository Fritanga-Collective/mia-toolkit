/* MIA Tools — use-case chooser (/ and /<lang>/): progressive enhancement.
 * Without JavaScript the region form is a plain GET to the /institutions/
 * hub (which lists every market) and a <noscript> list links each market
 * page directly. With JavaScript, "See solutions" goes straight to the
 * selected market page and counts a name-only region_select:<market> event
 * (see track.js). First-party, no storage, no cookies.
 */
(function () {
  "use strict";
  var form = document.querySelector("form[data-region-form]");
  if (!form) return;
  var select = form.querySelector("select");
  if (!select) return;

  form.addEventListener("submit", function (ev) {
    var opt = select.options[select.selectedIndex];
    var href = opt && opt.value;
    // Only ever navigate to one of our own root-relative market pages.
    if (!href || !/^\/[a-z0-9/-]*\/$/.test(href)) return;
    ev.preventDefault();
    var market = opt.getAttribute("data-market") || "";
    if (window.miaTrack && market) window.miaTrack("region_select:" + market);
    window.location.href = href;
  });
})();
