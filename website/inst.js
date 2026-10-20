/* MIA Tools — institutional pages: progressive enhancement only.
 * Everything here also works without JavaScript. First-party, no third
 * parties, no cookies, no browser storage, nothing sent anywhere
 * except the form the visitor submits.
 *  1. Market menu (<details>): close on Escape and on a click outside.
 *  2. Pilot form: copy ?utm_campaign= (or ?c=) from this page's URL into the
 *     hidden field, and submit with fetch for an inline success/error
 *     message. Without JS the form is a plain POST and the Worker redirects
 *     to the thank-you page.
 */
(function () {
  "use strict";
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  // 1. Market menu
  var menus = document.querySelectorAll("details.i-market");
  each(menus, function (d) {
    d.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && d.open) {
        d.open = false;
        var s = d.querySelector("summary");
        if (s) s.focus();
      }
    });
  });
  document.addEventListener("click", function (ev) {
    each(menus, function (d) {
      if (d.open && !d.contains(ev.target)) d.open = false;
    });
  });

  // 2. Pilot form
  function campaign() {
    try {
      var q = new URLSearchParams(window.location.search);
      var c = q.get("utm_campaign") || q.get("c") || "";
      return /^[A-Za-z0-9_-]{1,32}$/.test(c) ? c : "";
    } catch (e) {
      return "";
    }
  }

  each(document.querySelectorAll("form.i-form"), function (form) {
    var hidden = form.querySelector('input[name="utm_campaign"]');
    var code = campaign();
    if (hidden) hidden.value = code;

    var action = form.getAttribute("action");
    var button = form.querySelector('button[type="submit"]');
    var status = form.querySelector(".i-form-status");
    if (!action || !button || button.disabled || !status) return;
    if (!window.fetch || !window.URLSearchParams || !window.FormData) return;

    function show(kind, text) {
      status.hidden = false;
      status.className = "i-form-status" + (kind ? " is-" + kind : "");
      status.textContent = text;
    }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      button.disabled = true;
      show("", form.getAttribute("data-msg-sending") || "…");
      var body = new URLSearchParams(new FormData(form));
      window.fetch(action, {
        method: "POST",
        body: body,
        headers: { "Accept": "application/json" },
        credentials: "omit",
        mode: "cors"
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok || !j.ok) throw new Error("rejected");
        });
      }).then(function () {
        form.reset();
        if (hidden) hidden.value = code;
        show("ok", form.getAttribute("data-msg-ok"));
        button.disabled = false;
      }).catch(function () {
        show("err", form.getAttribute("data-msg-err"));
        button.disabled = false;
      });
    });
  });
})();
