/* MIA Tools — institutional pages: progressive enhancement only.
 * Everything here also works without JavaScript. First-party, no third
 * parties, no cookies, no browser storage, nothing sent anywhere
 * except the form the visitor submits.
 *  1. Market menu (<details>): close on Escape and on a click outside.
 *  2. Request form: copy ?utm_campaign= (or ?c=) from this page's URL into
 *     the hidden field, and submit with fetch for an inline success/error
 *     message. Without JS the form is a plain POST and the Worker redirects
 *     to the thank-you page.
 *  3. Request modal: every request CTA (pilot, pricing tiers, procurement
 *     kit — links carrying data-request) is a real link to a standalone,
 *     prefilled form page; with JS (and <dialog> support) it opens the same
 *     form in a modal instead, set to that request_type.
 *  4. Funnel counts: name-only events via window.miaTrack (track.js), as
 *     "<event>:<request_type>:<market>", e.g. "form_open:pricing_hospital:us".
 *     Never field values or any personal data.
 */
(function () {
  "use strict";
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };
  // Event NAME only. Silent no-op without track.js.
  var track = function (name) {
    if (window.miaTrack) window.miaTrack(name);
  };
  var funnel = function (event, type, market) {
    track(event + ":" + (type || "pilot") + (market ? ":" + market : ""));
  };

  // Simple click counters: <a data-track="kit_download:security">.
  each(document.querySelectorAll("[data-track]"), function (el) {
    el.addEventListener("click", function () {
      track(el.getAttribute("data-track"));
    });
  });

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

  // 2. Request form
  function campaign() {
    try {
      var q = new URLSearchParams(window.location.search);
      var c = q.get("utm_campaign") || q.get("c") || "";
      return /^[A-Za-z0-9_-]{1,32}$/.test(c) ? c : "";
    } catch (e) {
      return "";
    }
  }
  function fieldValue(form, name) {
    var f = form.querySelector('input[name="' + name + '"]');
    return f ? f.value : "";
  }

  each(document.querySelectorAll("form.i-form"), function (form) {
    var hidden = form.querySelector('input[name="utm_campaign"]');
    var code = campaign();
    if (hidden) hidden.value = code;
    var ev = function (name) {
      funnel(name, fieldValue(form, "request_type"), fieldValue(form, "market"));
    };

    // Funnel: first focus in any field (once per modal open / page view),
    // then every submit attempt. The modal resets miaStarted on each open.
    form.miaStarted = false;
    form.addEventListener("focusin", function (e) {
      var t = e.target;
      if (form.miaStarted || !t || !/^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName)
          || t.type === "hidden" || t.name === "website") return;
      form.miaStarted = true;
      ev("form_start");
    });
    form.addEventListener("submit", function () { ev("submit_attempt"); });

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

    form.addEventListener("submit", function (e) {
      e.preventDefault();
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
        var type = fieldValue(form, "request_type");
        form.reset();  // keeps hidden inputs' value attributes
        if (hidden) hidden.value = code;
        var rt = form.querySelector('input[name="request_type"]');
        if (rt) rt.value = type;
        form.miaSubmitted = true;
        ev("submit_success");
        show("ok", form.getAttribute("data-msg-ok"));
        button.disabled = false;
      }).catch(function () {
        show("err", form.getAttribute("data-msg-err"));
        button.disabled = false;
      });
    });
  });

  // 3. Request modal. No JS or no <dialog> support: each CTA stays a plain
  // link to its standalone form page. Native showModal() makes the rest of
  // the page inert, keeps Tab inside the dialog and closes it on Escape.
  var dialog = document.getElementById("pilot-dialog");
  var triggers = document.querySelectorAll("a[data-request]");
  if (!dialog || !triggers.length || typeof dialog.showModal !== "function") return;
  var dform = dialog.querySelector("form.i-form");
  if (!dform) return;
  var heading = dialog.querySelector("#pf-h");
  var context = dialog.querySelector("#pf-context");
  var submit = dform.querySelector('button[type="submit"]');
  var pendingLink = dform.querySelector("#pf-pending a");
  var typeField = dform.querySelector('input[name="request_type"]');
  var opener = null;
  var current = { type: "pilot", market: "" };

  each(triggers, function (a) {
    a.setAttribute("aria-haspopup", "dialog");
    a.setAttribute("aria-controls", "pilot-dialog");
    a.addEventListener("click", function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
      e.preventDefault();
      var type = a.getAttribute("data-request") || "pilot";
      current = { type: type, market: a.getAttribute("data-market") || "" };
      funnel("cta_click", type, current.market);
      // Point the shared form at what was clicked.
      if (typeField) typeField.value = type;
      if (heading && a.getAttribute("data-title")) heading.textContent = a.getAttribute("data-title");
      if (context && a.getAttribute("data-context")) context.textContent = a.getAttribute("data-context");
      if (submit && a.getAttribute("data-submit")) submit.textContent = a.getAttribute("data-submit");
      if (pendingLink && a.getAttribute("data-mailto")) pendingLink.href = a.getAttribute("data-mailto");
      var status = dform.querySelector(".i-form-status");
      if (status) status.hidden = true;
      dform.miaStarted = false;
      dform.miaSubmitted = false;
      opener = a;
      dialog.showModal();
      document.documentElement.classList.add("i-modal-open");
      funnel("form_open", type, current.market);
      var first = dform.querySelector(
        "input:not([type=hidden]):not([tabindex='-1']), select, textarea");
      if (first) first.focus();
    });
  });

  each(dialog.querySelectorAll("[data-close]"), function (b) {
    b.addEventListener("click", function () { dialog.close(); });
  });
  // A click on the backdrop (outside the panel) closes it too.
  dialog.addEventListener("click", function (e) {
    if (e.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", function () {
    document.documentElement.classList.remove("i-modal-open");
    if (!dform.miaSubmitted) {
      funnel("close_without_submit", current.type, current.market);
    }
    if (opener) opener.focus();
  });
})();
