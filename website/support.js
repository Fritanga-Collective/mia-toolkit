// Support page: pick a donation tier (same for everyone). The download is
// always free; this only links to Lemon Squeezy. All client-side: no network,
// no tracking, no geolocation.
(function () {
  "use strict";

  var CONFIG = {
    freeDownload:
      "https://github.com/luis-rodriguez/mia-toolkit/releases/latest",
    // Lemon Squeezy "Pay What You Want" checkout — used as the fallback for any
    // tier whose own product/URL hasn't been created yet, and for "custom".
    pwyw:
      "https://mia-tools.lemonsqueezy.com/checkout/buy/7bb51bbe-d566-480d-9a44-cbde6fc871cc",
    // One fixed-price checkout per tier. Create these in Lemon Squeezy (the
    // first three as one-time, "monthly" as a subscription) and paste each
    // buy-link here. Empty string ⇒ falls back to the PWYW checkout above.
    tiers: [
      { id: "coffee", amount: 5, url: "" },
      { id: "supporter", amount: 15, url: "" },
      { id: "patron", amount: 50, url: "" },
      { id: "monthly", amount: 5, url: "", recurring: true },
    ],
  };

  var STR = {
    en: {
      intro: "Pick an amount — the app is always free.",
      names: { coffee: "Coffee", supporter: "Supporter", patron: "Patron",
               monthly: "Monthly supporter" },
      permo: "/mo",
      custom: "Or give a custom amount →",
      note: "One-time, except the monthly option. Lemon Squeezy handles tax " +
            "and receipts; you'll get an emailed thank-you, nothing to install.",
      freeQ: "Not now?",
      freeLink: "Just download it free →",
    },
    es: {
      intro: "Elige un monto — la app siempre es gratis.",
      names: { coffee: "Un café", supporter: "Colaborador/a", patron: "Mecenas",
               monthly: "Apoyo mensual" },
      permo: "/mes",
      custom: "O aporta el monto que quieras →",
      note: "Pago único, salvo la opción mensual. Lemon Squeezy gestiona los " +
            "impuestos y el recibo; recibirás un agradecimiento por correo.",
      freeQ: "¿Ahora no?",
      freeLink: "Solo descárgala gratis →",
    },
    zh: {
      intro: "选择金额 —— 应用始终免费。",
      names: { coffee: "请喝咖啡", supporter: "支持者", patron: "赞助人",
               monthly: "每月支持" },
      permo: "/月",
      custom: "或自定义金额 →",
      note: "除每月选项外均为一次性支持。Lemon Squeezy 处理税费与收据；" +
            "你会收到一封感谢邮件，无需安装任何东西。",
      freeQ: "现在不方便？",
      freeLink: "直接免费下载 →",
    },
  };

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var lang = (document.documentElement.lang || "en").slice(0, 2);
    var t = STR[lang] || STR.en;

    var intro = document.getElementById("tiers-intro");
    var box = document.getElementById("tiers");
    var custom = document.getElementById("tier-custom");
    var note = document.getElementById("tiers-note");
    var freeQ = document.getElementById("free-q");
    var free = document.getElementById("free-dl");

    if (intro) intro.textContent = t.intro;
    if (note) note.textContent = t.note;
    if (freeQ) freeQ.textContent = t.freeQ;
    if (free) { free.textContent = t.freeLink; free.href = CONFIG.freeDownload; }
    if (custom) { custom.textContent = t.custom; custom.href = CONFIG.pwyw; }
    if (!box) return;

    box.innerHTML = "";
    CONFIG.tiers.forEach(function (tier) {
      var a = document.createElement("a");
      a.className = "tier" + (tier.recurring ? " tier-monthly" : "");
      a.href = tier.url || CONFIG.pwyw;
      var price = "$" + tier.amount + (tier.recurring ? t.permo : "");
      a.innerHTML =
        '<span class="tier-price">' + price + "</span>" +
        '<span class="tier-name">' + (t.names[tier.id] || tier.id) + "</span>";
      box.appendChild(a);
    });
  });
})();
