// Support page: pick your country, see a suggested fair-trade amount.
// No income-tier labels are ever shown — just a country and a price. All
// client-side: no IP lookup, no network, no tracking. The download is always
// free; this only suggests a fair amount and links to Lemon Squeezy (PWYW).
(function () {
  "use strict";

  var CONFIG = {
    // Lemon Squeezy "Pay What You Want" checkout URL (replace when the store
    // exists). Until then the button points at the GitHub repo.
    checkout: "https://github.com/luis-rodriguez/mia-toolkit",
    freeDownload:
      "https://github.com/luis-rodriguez/mia-toolkit/releases/latest",
  };

  // Single source of truth: code, English name, Spanish name, suggested USD.
  // (Bands are internal only and never shown to the visitor.)
  var COUNTRIES = [
    ["US", "United States", "Estados Unidos", 19],
    ["CA", "Canada", "Canadá", 19],
    ["GB", "United Kingdom", "Reino Unido", 19],
    ["IE", "Ireland", "Irlanda", 19],
    ["DE", "Germany", "Alemania", 19],
    ["FR", "France", "Francia", 19],
    ["ES", "Spain", "España", 19],
    ["IT", "Italy", "Italia", 19],
    ["NL", "Netherlands", "Países Bajos", 19],
    ["BE", "Belgium", "Bélgica", 19],
    ["CH", "Switzerland", "Suiza", 19],
    ["AT", "Austria", "Austria", 19],
    ["SE", "Sweden", "Suecia", 19],
    ["NO", "Norway", "Noruega", 19],
    ["DK", "Denmark", "Dinamarca", 19],
    ["PT", "Portugal", "Portugal", 19],
    ["AU", "Australia", "Australia", 19],
    ["NZ", "New Zealand", "Nueva Zelanda", 19],
    ["JP", "Japan", "Japón", 19],
    ["KR", "South Korea", "Corea del Sur", 19],
    ["SG", "Singapore", "Singapur", 19],
    ["AE", "United Arab Emirates", "Emiratos Árabes Unidos", 19],
    ["IL", "Israel", "Israel", 19],
    ["MX", "Mexico", "México", 7],
    ["BR", "Brazil", "Brasil", 7],
    ["AR", "Argentina", "Argentina", 7],
    ["CL", "Chile", "Chile", 7],
    ["CO", "Colombia", "Colombia", 7],
    ["PE", "Peru", "Perú", 7],
    ["EC", "Ecuador", "Ecuador", 7],
    ["CR", "Costa Rica", "Costa Rica", 7],
    ["PA", "Panama", "Panamá", 7],
    ["UY", "Uruguay", "Uruguay", 7],
    ["DO", "Dominican Republic", "República Dominicana", 7],
    ["GT", "Guatemala", "Guatemala", 7],
    ["TR", "Turkey", "Turquía", 7],
    ["CN", "China", "China", 7],
    ["MY", "Malaysia", "Malasia", 7],
    ["TH", "Thailand", "Tailandia", 7],
    ["ZA", "South Africa", "Sudáfrica", 7],
    ["PL", "Poland", "Polonia", 7],
    ["RO", "Romania", "Rumania", 7],
    ["IN", "India", "India", 3],
    ["ID", "Indonesia", "Indonesia", 3],
    ["PH", "Philippines", "Filipinas", 3],
    ["PK", "Pakistan", "Pakistán", 3],
    ["BD", "Bangladesh", "Bangladés", 3],
    ["VN", "Vietnam", "Vietnam", 3],
    ["NG", "Nigeria", "Nigeria", 3],
    ["EG", "Egypt", "Egipto", 3],
    ["KE", "Kenya", "Kenia", 3],
    ["MA", "Morocco", "Marruecos", 3],
    ["UA", "Ukraine", "Ucrania", 3],
    ["BO", "Bolivia", "Bolivia", 3],
    ["HN", "Honduras", "Honduras", 3],
    ["SV", "El Salvador", "El Salvador", 3],
    ["NI", "Nicaragua", "Nicaragua", 3],
    ["VE", "Venezuela", "Venezuela", 3],
  ];

  // Best-effort time-zone -> country code, to preselect the dropdown (no IP).
  var TZ_CODE = {
    "America/Mexico_City": "MX", "America/Tijuana": "MX",
    "America/Monterrey": "MX", "America/Merida": "MX", "America/Cancun": "MX",
    "America/Chihuahua": "MX", "America/Hermosillo": "MX",
    "America/Mazatlan": "MX", "America/Matamoros": "MX",
    "America/New_York": "US", "America/Chicago": "US", "America/Denver": "US",
    "America/Los_Angeles": "US", "America/Phoenix": "US",
    "America/Toronto": "CA", "America/Vancouver": "CA", "America/Edmonton": "CA",
    "Europe/London": "GB", "Europe/Dublin": "IE", "Europe/Madrid": "ES",
    "Europe/Paris": "FR", "Europe/Berlin": "DE", "Europe/Rome": "IT",
    "Europe/Amsterdam": "NL", "Europe/Brussels": "BE", "Europe/Zurich": "CH",
    "Europe/Vienna": "AT", "Europe/Stockholm": "SE", "Europe/Oslo": "NO",
    "Europe/Copenhagen": "DK", "Europe/Lisbon": "PT", "Europe/Warsaw": "PL",
    "Europe/Bucharest": "RO", "Europe/Istanbul": "TR", "Europe/Kyiv": "UA",
    "Europe/Kiev": "UA",
    "America/Sao_Paulo": "BR", "America/Argentina/Buenos_Aires": "AR",
    "America/Santiago": "CL", "America/Bogota": "CO", "America/Lima": "PE",
    "America/Guayaquil": "EC", "America/Costa_Rica": "CR",
    "America/Panama": "PA", "America/Montevideo": "UY",
    "America/Santo_Domingo": "DO", "America/Guatemala": "GT",
    "America/La_Paz": "BO", "America/Tegucigalpa": "HN",
    "America/El_Salvador": "SV", "America/Managua": "NI",
    "America/Caracas": "VE",
    "Asia/Kolkata": "IN", "Asia/Jakarta": "ID", "Asia/Manila": "PH",
    "Asia/Karachi": "PK", "Asia/Dhaka": "BD", "Asia/Ho_Chi_Minh": "VN",
    "Asia/Bangkok": "TH", "Asia/Singapore": "SG", "Asia/Tokyo": "JP",
    "Asia/Seoul": "KR", "Asia/Shanghai": "CN", "Asia/Kuala_Lumpur": "MY",
    "Asia/Dubai": "AE", "Asia/Jerusalem": "IL",
    "Africa/Lagos": "NG", "Africa/Cairo": "EG", "Africa/Nairobi": "KE",
    "Africa/Casablanca": "MA", "Africa/Johannesburg": "ZA",
    "Australia/Sydney": "AU", "Australia/Melbourne": "AU",
    "Pacific/Auckland": "NZ",
  };

  var STR = {
    en: {
      placeholder: "— Select your country —",
      other: "Somewhere else / I'll choose",
      cant: "I can't pay right now",
      prompt: "Select your country to see a suggested amount.",
      suggest: "Suggested amount: $AMOUNT USD",
      free: "Download it free — pay later if you ever can.",
      choose: "Pay whatever feels fair where you live.",
      btn: "Support — $AMOUNT",
      btnFree: "Support if you can",
    },
    es: {
      placeholder: "— Elige tu país —",
      other: "En otro lugar / yo elijo",
      cant: "Ahora mismo no puedo pagar",
      prompt: "Elige tu país para ver una sugerencia.",
      suggest: "Aportación sugerida: $AMOUNT USD",
      free: "Descárgala gratis — apoya después si algún día puedes.",
      choose: "Paga lo que sea justo donde vives.",
      btn: "Apoyar — $AMOUNT",
      btnFree: "Apoya si puedes",
    },
  };

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function guessCode() {
    try {
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      return TZ_CODE[tz] || "";
    } catch (e) { return ""; }
  }

  ready(function () {
    var lang = (document.documentElement.lang || "en").slice(0, 2);
    var t = STR[lang] || STR.en;
    var sel = document.getElementById("region");
    var out = document.getElementById("suggestion");
    var btn = document.getElementById("support-btn");
    var free = document.getElementById("free-dl");
    if (free) free.href = CONFIG.freeDownload;
    if (!sel || !out || !btn) return;

    function add(value, text, price) {
      var o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      if (price != null) o.setAttribute("data-price", price);
      sel.appendChild(o);
      return o;
    }

    sel.innerHTML = "";
    add("", t.placeholder);
    COUNTRIES.slice()
      .sort(function (a, b) {
        var na = lang === "es" ? a[2] : a[1];
        var nb = lang === "es" ? b[2] : b[1];
        return na.localeCompare(nb);
      })
      .forEach(function (c) { add(c[0], lang === "es" ? c[2] : c[1], c[3]); });
    add("__other", t.other, -1);
    add("__cant", t.cant, 0);

    function update() {
      var opt = sel.options[sel.selectedIndex];
      var price = opt ? parseInt(opt.getAttribute("data-price"), 10) : NaN;
      btn.href = CONFIG.checkout;
      if (!sel.value) {            // placeholder
        out.textContent = t.prompt;
        btn.textContent = t.btnFree;
      } else if (sel.value === "__cant") {
        out.textContent = t.free;
        btn.textContent = t.btnFree;
      } else if (sel.value === "__other" || isNaN(price) || price <= 0) {
        out.textContent = t.choose;
        btn.textContent = t.btnFree;
      } else {
        out.textContent = t.suggest.replace("AMOUNT", price);
        btn.textContent = t.btn.replace("AMOUNT", price);
      }
    }

    var code = guessCode();
    if (code) sel.value = code;
    sel.addEventListener("change", update);
    update();
  });
})();
