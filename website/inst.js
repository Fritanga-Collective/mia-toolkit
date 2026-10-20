/* MIA Tools — institutional pages: progressive enhancement only.
 * Everything here also works without JavaScript. First-party, no third
 * parties, no cookies, no localStorage/sessionStorage.
 *  1. Market menu (<details>): close on Escape and on a click outside.
 */
(function () {
  "use strict";

  // 1. Market menu
  var menus = document.querySelectorAll("details.i-market");
  Array.prototype.forEach.call(menus, function (d) {
    d.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && d.open) {
        d.open = false;
        var s = d.querySelector("summary");
        if (s) s.focus();
      }
    });
  });
  document.addEventListener("click", function (ev) {
    Array.prototype.forEach.call(menus, function (d) {
      if (d.open && !d.contains(ev.target)) d.open = false;
    });
  });
})();
