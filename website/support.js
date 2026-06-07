// Support page: pick a donation tier (same for everyone). The download is
// always free; this only links to Lemon Squeezy. All client-side: no network,
// no tracking, no geolocation.
(function () {
  "use strict";

  var CONFIG = {
    freeDownload:
      "https://github.com/Fritanga-Collective/mia-toolkit/releases/latest",
    // One Lemon Squeezy product with four fixed-price variants (the old PWYW
    // product is in draft). The bare URL shows all variants for the buyer to
    // choose; `?enabled=<variant_id>` filters the checkout to a single
    // variant, which is how each tier button deep-links its own price.
    // Served from our Lemon Squeezy store custom domain (CNAME).
    checkout:
      "https://support.mia-toolkit.fritanga.co/checkout/buy/9d2bf6af-6bbc-4a07-a55e-af6a5de6a5f9",
    // Per tier: `variant` is the Lemon Squeezy variant id; `amount` is only
    // for display. The monthly variant is a real subscription (recurring).
    tiers: [
      { id: "coffee", amount: 5.99, variant: "1752624" },
      { id: "supporter", amount: 15.99, variant: "1752625" },
      { id: "patron", amount: 50.99, variant: "1752626" },
      { id: "monthly", amount: 5, variant: "1752627", recurring: true },
    ],
  };

  // Checkout URL for a tier: the shared product filtered to its variant.
  function checkoutUrl(tier) {
    if (!tier || !tier.variant) return CONFIG.checkout; // bare = buyer chooses
    return CONFIG.checkout + "?enabled=" + tier.variant;
  }

  var STR = {
    en: {
      intro: "Pick an amount — the app is always free.",
      names: { coffee: "Coffee", supporter: "Supporter", patron: "Patron",
               monthly: "Monthly supporter" },
      permo: "/mo",
      custom: "Or compare all options at checkout →",
      note: "One-time, except the monthly option. Lemon Squeezy handles tax " +
            "and receipts; you'll get an emailed thank-you, nothing to install.",
      freeQ: "Not now?",
    },
    es: {
      intro: "Elige un monto — la app siempre es gratis.",
      names: { coffee: "Un café", supporter: "Colaborador/a", patron: "Mecenas",
               monthly: "Apoyo mensual" },
      permo: "/mes",
      custom: "O compara todas las opciones al pagar →",
      note: "Pago único, salvo la opción mensual. Lemon Squeezy gestiona los " +
            "impuestos y el recibo; recibirás un agradecimiento por correo.",
      freeQ: "¿Ahora no?",
    },
    zh: {
      intro: "选择金额 —— 应用始终免费。",
      names: { coffee: "请喝咖啡", supporter: "支持者", patron: "赞助人",
               monthly: "每月支持" },
      permo: "/月",
      custom: "或在结账页比较所有选项 →",
      note: "除每月选项外均为一次性支持。Lemon Squeezy 处理税费与收据；" +
            "你会收到一封感谢邮件，无需安装任何东西。",
      freeQ: "现在不方便？",
    },
    ms: {
      intro: "Pilih jumlah — aplikasi ini sentiasa percuma.",
      names: { coffee: "Belanja kopi", supporter: "Penyokong",
               patron: "Penaung", monthly: "Penyokong bulanan" },
      permo: "/bln",
      custom: "Atau bandingkan semua pilihan semasa pembayaran →",
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
      custom: "Oder alle Optionen beim Bezahlen vergleichen →",
      note: "Einmalig, außer bei der monatlichen Option. Lemon Squeezy " +
            "übernimmt Steuern und Belege; Sie erhalten ein Dankeschön per " +
            "E-Mail, nichts muss installiert werden.",
      freeQ: "Jetzt nicht?",
    },
    ta: {
      intro: "தொகையைத் தேர்ந்தெடுங்கள் — இந்த ஆப் எப்போதும் இலவசம்.",
      names: { coffee: "ஒரு காபி", supporter: "ஆதரவாளர்",
               patron: "பெரும் ஆதரவாளர்", monthly: "மாதாந்திர ஆதரவாளர்" },
      permo: "/மாதம்",
      custom: "அல்லது அனைத்து விருப்பங்களையும் கட்டண பக்கத்தில் ஒப்பிடுங்கள் →",
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
    var custom = document.getElementById("tier-custom");
    var note = document.getElementById("tiers-note");
    var freeQ = document.getElementById("free-q");
    var free = document.getElementById("free-dl");

    if (intro) intro.textContent = t.intro;
    if (note) note.textContent = t.note;
    if (freeQ) freeQ.textContent = t.freeQ;
    // The anchor's text is rendered by the page template from i18n JSON
    // (support.free_dl) — only the destination is set here.
    if (free) free.href = CONFIG.freeDownload;
    if (custom) { custom.textContent = t.custom; custom.href = CONFIG.checkout; }
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
