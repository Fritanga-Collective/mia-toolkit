// Support page: pick a donation tier (same for everyone). The download is
// always free; this only links to Lemon Squeezy. All client-side: no network,
// no tracking, no geolocation.
(function () {
  "use strict";

  var CONFIG = {
    freeDownload:
      "https://github.com/Fritanga-Collective/mia-toolkit/releases/latest",
    // Each tier is now its own Lemon Squeezy product with a direct checkout
    // URL (decision 2026-06-11 — individual products, not variants; drops the
    // `?enabled=` deep-link that couldn't pre-select a non-default variant).
    // `checkout` is just a defensive fallback if a tier ever lacks a `url`;
    // there's no "compare all options" chooser anymore. Served from our Lemon
    // Squeezy store custom domain (CNAME).
    checkout:
      "https://support.miatools.tech/checkout/buy/9d2bf6af-6bbc-4a07-a55e-af6a5de6a5f9",
    // Per tier: `url` is the product's direct checkout; `amount` is only for
    // display. The monthly product is a real subscription (recurring).
    tiers: [
      { id: "coffee", amount: 5.99,
        url: "https://support.miatools.tech/checkout/buy/931b7467-55cd-48e7-bc85-101530b6b175" },
      { id: "supporter", amount: 15.99,
        url: "https://support.miatools.tech/checkout/buy/367767d8-4496-480f-ae73-44e5765cb9c3" },
      { id: "patron", amount: 50.99,
        url: "https://support.miatools.tech/checkout/buy/28aee3c3-2162-46be-92fd-e546de7bd443" },
      { id: "monthly", amount: 5, recurring: true,
        url: "https://support.miatools.tech/checkout/buy/65cb3914-7437-4c59-ad79-516118471601" },
    ],
  };

  // Checkout URL for a tier: its own direct product link.
  function checkoutUrl(tier) {
    if (!tier || !tier.url) return CONFIG.checkout; // defensive fallback only
    return tier.url;
  }

  var STR = {
    en: {
      intro: "Pick an amount — the app is always free.",
      names: { coffee: "Coffee", supporter: "Supporter", patron: "Patron",
               monthly: "Monthly supporter" },
      permo: "/mo",
      note: "One-time, except the monthly option. Lemon Squeezy handles tax " +
            "and receipts; you'll get an emailed thank-you, nothing to install.",
      freeQ: "Not now?",
    },
    es: {
      intro: "Elige un monto — la app siempre es gratis.",
      names: { coffee: "Un café", supporter: "Colaborador/a", patron: "Mecenas",
               monthly: "Apoyo mensual" },
      permo: "/mes",
      note: "Pago único, salvo la opción mensual. Lemon Squeezy gestiona los " +
            "impuestos y el recibo; recibirás un agradecimiento por correo.",
      freeQ: "¿Ahora no?",
    },
    zh: {
      intro: "选择金额 —— 应用始终免费。",
      names: { coffee: "请喝咖啡", supporter: "支持者", patron: "赞助人",
               monthly: "每月支持" },
      permo: "/月",
      note: "除每月选项外均为一次性支持。Lemon Squeezy 处理税费与收据；" +
            "你会收到一封感谢邮件，无需安装任何东西。",
      freeQ: "现在不方便？",
    },
    ms: {
      intro: "Pilih jumlah — aplikasi ini sentiasa percuma.",
      names: { coffee: "Belanja kopi", supporter: "Penyokong",
               patron: "Penaung", monthly: "Penyokong bulanan" },
      permo: "/bln",
      note: "Sekali sahaja, kecuali pilihan bulanan. Lemon Squeezy " +
            "menguruskan cukai dan resit; anda akan menerima e-mel terima " +
            "kasih, tiada apa-apa perlu dipasang.",
      freeQ: "Bukan sekarang?",
    },
    de: {
      intro: "Wählen Sie einen Betrag — die App ist immer kostenlos.",
      names: { coffee: "Ein Kaffee", supporter: "Unterstützer:in",
               patron: "Förderer:in", monthly: "Monatliche Unterstützung" },
      permo: "/Monat",
      note: "Einmalig, außer bei der monatlichen Option. Lemon Squeezy " +
            "übernimmt Steuern und Belege; Sie erhalten ein Dankeschön per " +
            "E-Mail, nichts muss installiert werden.",
      freeQ: "Jetzt nicht?",
    },
    fr: {
      intro: "Choisissez un montant — l'application est toujours gratuite.",
      names: { coffee: "Un café", supporter: "Soutien",
               patron: "Mécène", monthly: "Soutien mensuel" },
      permo: "/mois",
      note: "Paiement unique, sauf pour l'option mensuelle. Lemon Squeezy " +
            "gère les taxes et les reçus ; vous recevrez un remerciement par " +
            "e-mail, rien à installer.",
      freeQ: "Pas maintenant ?",
    },
    ta: {
      intro: "தொகையைத் தேர்ந்தெடுங்கள் — இந்த ஆப் எப்போதும் இலவசம்.",
      names: { coffee: "ஒரு காபி", supporter: "ஆதரவாளர்",
               patron: "பெரும் ஆதரவாளர்", monthly: "மாதாந்திர ஆதரவாளர்" },
      permo: "/மாதம்",
      note: "மாதாந்திர விருப்பம் தவிர, மற்றவை ஒருமுறை மட்டுமே. வரிகளும் " +
            "ரசீதுகளும் Lemon Squeezy மூலம் கையாளப்படும்; நன்றி மின்னஞ்சல் " +
            "பெறுவீர்கள், எதையும் நிறுவ வேண்டியதில்லை.",
      freeQ: "இப்போது வேண்டாமா?",
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
    var note = document.getElementById("tiers-note");
    var freeQ = document.getElementById("free-q");
    var free = document.getElementById("free-dl");

    if (intro) intro.textContent = t.intro;
    if (note) note.textContent = t.note;
    if (freeQ) freeQ.textContent = t.freeQ;
    // The anchor's text is rendered by the page template from i18n JSON
    // (support.free_dl) — only the destination is set here.
    if (free) free.href = CONFIG.freeDownload;
    if (!box) return;

    box.innerHTML = "";
    CONFIG.tiers.forEach(function (tier) {
      var a = document.createElement("a");
      a.className = "tier" + (tier.recurring ? " tier-monthly" : "");
      a.href = checkoutUrl(tier);
      var amt = tier.amount % 1 === 0
        ? "$" + tier.amount : "$" + tier.amount.toFixed(2);
      var price = amt + (tier.recurring ? t.permo : "");
      a.innerHTML =
        '<span class="tier-price">' + price + "</span>" +
        '<span class="tier-name">' + (t.names[tier.id] || tier.id) + "</span>";
      box.appendChild(a);
    });
  });
})();
