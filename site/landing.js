/* Startseite: Ampel zum Ausprobieren, Hochzählen des Beispielbetrags, Einblenden der Werkzeug-Karten.
   Keine Daten werden gespeichert oder gesendet. Bewegung nur ohne prefers-reduced-motion. */
(function () {
  "use strict";
  var LIMIT_COUNT = 30; // wird unten aus tax-lib.js übernommen, damit Startseite und Tools dieselben Grenzen nutzen
  var LIMIT_SUM = 2000;
  var eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

  /* ---- Ampel je Plattform (gleiche Grenzen und Schwellen wie in den Tools: ab 60 % gelb, ab 100 % rot) ---- */
  var T = window.SCTax || {};
  LIMIT_COUNT = T.MELDE_COUNT || LIMIT_COUNT;
  LIMIT_SUM = T.MELDE_SUM || LIMIT_SUM;
  var levelOf = function (c, s) {
    var worst = Math.max(c / LIMIT_COUNT, s / LIMIT_SUM);
    return { worst: worst, level: worst >= 1 ? "red" : worst >= 0.6 ? "yellow" : "green" };
  };
  var count = document.getElementById("d-count");
  var sum = document.getElementById("d-sum");
  if (count && sum) {
    var out = {
      count: document.getElementById("d-count-out"),
      sum: document.getElementById("d-sum-out"),
      meter: document.getElementById("d-meter"),
      box: document.getElementById("d-result"),
    };
    // Beispielstände je Plattform: eine gelb, zwei grün, eine rot, damit alle drei Stufen sofort sichtbar sind
    var plats = {
      vinted: { c: 21, s: 1280 },
      kleinanzeigen: { c: 8, s: 420 },
      ebay: { c: 2, s: 90 },
      etsy: { c: 31, s: 1500 },
    };
    var radios = document.querySelectorAll('input[name="d-plat"]');
    var current = "vinted";
    var paintDots = function () {
      radios.forEach(function (r) {
        var st = plats[r.value];
        r.parentNode.querySelector("i").className = levelOf(st.c, st.s).level;
      });
    };
    var render = function () {
      var st = plats[current];
      var c = st.c;
      var s = st.s;
      var lv = levelOf(c, s);
      var level = lv.level;
      out.count.textContent = String(c);
      out.sum.textContent = eur.format(s);
      out.meter.style.width = Math.min(100, lv.worst * 100) + "%";
      out.meter.className = level === "green" ? "" : level;
      var text;
      if (level === "red") {
        text = ["Rot: Grenze erreicht", "Die Plattform meldet dich voraussichtlich ans BZSt. Das ist noch keine Steuerforderung. Halte Einkaufsbelege und Verkaufsdaten bereit."];
      } else if (level === "yellow") {
        text = ["Gelb: Du näherst dich der Grenze", "Bei diesem Tempo erreichst du die Grenze voraussichtlich bald. Es fehlen noch " + Math.max(0, LIMIT_COUNT - c) + " Verkäufe oder " + eur.format(Math.max(0, LIMIT_SUM - s)) + "."];
      } else {
        text = ["Grün: Weit entfernt", "Du liegst deutlich unter der Meldegrenze dieser Plattform. Für gelegentliche Verkäufe besteht in der Regel kein Handlungsbedarf."];
      }
      out.box.className = "ampel " + level;
      out.box.querySelector("strong").textContent = text[0];
      out.box.querySelector("div").textContent = text[1];
      count.setAttribute("aria-valuetext", c + " Verkäufe");
      sum.setAttribute("aria-valuetext", eur.format(s) + " Umsatz");
      paintDots();
    };
    var onSlide = function () {
      plats[current] = { c: Number(count.value), s: Number(sum.value) };
      render();
    };
    radios.forEach(function (r) {
      r.addEventListener("change", function () {
        if (!r.checked) return;
        current = r.value;
        count.value = plats[current].c;
        sum.value = plats[current].s;
        render();
      });
    });
    count.addEventListener("input", onSlide);
    sum.addEventListener("input", onSlide);
    render();
  }

  // Keine Zähl- und Scroll-Animationen: Zahlen stehen sofort da (Checkliste: keine erfundenen Zähler, wenige Animationen).
})();
