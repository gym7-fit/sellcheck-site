// Oberfläche des Steuer-Exports (Berechnung steckt in tax-lib.js und ist dort getestet).
(function () {
  "use strict";
  const SC = window.SellCheck;
  const T = window.SCTax;
  const $ = (id) => document.getElementById(id);
  const SETTINGS_KEY = "sellcheck.settings.v1";
  const eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
  const money = (c) => eur.format(c / 100);
  const el = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };

  /* ---------- Einstellungen (nur lokal) ---------- */
  function loadSettings() {
    try {
      return T.sanitizeSettings(JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}"));
    } catch {
      return T.sanitizeSettings({});
    }
  }
  function saveSettings(s) {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
    } catch {
      /* Speicher voll oder gesperrt: Einstellungen gelten dann nur für diese Sitzung */
    }
  }
  const settings = loadSettings();
  $("x-mode").value = settings.mode;
  $("x-vat").value = settings.vat;
  $("x-rate").value = String(settings.rate);
  $("x-name").value = settings.name;
  $("x-taxid").value = settings.taxId;

  function readSettings() {
    return T.sanitizeSettings({
      mode: $("x-mode").value, vat: $("x-vat").value, rate: Number($("x-rate").value),
      name: $("x-name").value, taxId: $("x-taxid").value,
    });
  }

  /* ---------- Jahre ---------- */
  function fillYears() {
    const sel = $("x-year");
    const keep = sel.value;
    const years = new Set([new Date().getFullYear()]);
    SC.sales.forEach((s) => years.add(Number(s.date.slice(0, 4))));
    const sorted = [...years].sort((a, b) => b - a);
    sel.replaceChildren(...sorted.map((y) => { const o = el("option", String(y)); o.value = String(y); return o; }));
    // Standard: jüngstes Jahr mit Daten (meist das Jahr, für das gerade abgerechnet wird)
    const withData = sorted.find((y) => SC.sales.some((s) => s.date.startsWith(String(y))));
    sel.value = keep && years.has(Number(keep)) ? keep : String(withData || sorted[0]);
  }

  /* ---------- Anzeige ---------- */
  function stat(value, label, cls) {
    const d = el("div", undefined, "stat");
    d.append(el("div", value, "v" + (cls ? " " + cls : "")), el("div", label, "l"));
    return d;
  }
  function checkItem(level, text) {
    const li = el("li", undefined, "check-item " + level);
    li.append(el("span", level === "ok" ? "✓" : level === "warn" ? "!" : "i", "check-mark"), el("span", text));
    return li;
  }

  function update() {
    const s = readSettings();
    saveSettings(s);
    const year = Number($("x-year").value);
    const business = s.mode === "business";
    $("x-vat-wrap").hidden = !business;
    $("x-rate-wrap").hidden = !business || s.vat !== "regular";
    $("x-journal").hidden = !business;
    $("x-summary").hidden = !business;
    $("x-private").hidden = business;
    $("x-report").href = "report.html?y=" + encodeURIComponent(year);
    $("x-msg").textContent = "";

    const hasData = SC.sales.some((e) => e.date.startsWith(String(year)));
    const checks = $("x-checks");
    const stats = $("x-stats");
    checks.replaceChildren();
    stats.replaceChildren();

    if (!hasData) {
      checks.append(checkItem("info", `Für ${year} gibt es noch keine Einträge im Tracker.`));
      ["x-journal", "x-summary", "x-private"].forEach((id) => ($(id).disabled = true));
      return;
    }
    ["x-journal", "x-summary", "x-private"].forEach((id) => ($(id).disabled = false));

    if (business) {
      const r = T.computeEuer(SC.sales, { year, vat: s.vat, rate: s.rate });
      stats.append(
        stat(String(r.count), "Verkäufe"),
        stat(money(r.revenueNet), s.vat === "regular" ? "Einnahmen netto" : "Betriebseinnahmen"),
        stat(money(r.expensesTotal), "Betriebsausgaben"),
        stat(money(r.profit), "Gewinn / Verlust", r.profit >= 0 ? "pos" : "neg")
      );
      if (r.dataComplete) checks.append(checkItem("ok", "Keine Datenlücken gefunden, die das Ergebnis verfälschen."));
      r.warnings.forEach((w) => checks.append(checkItem(w.level === "warn" ? "warn" : "info", w.text)));
    } else {
      const p = T.computePrivate(SC.sales, { year });
      stats.append(
        stat(String(p.items.length), "Verkäufe"),
        stat(String(p.freeCount), "nicht steuerbar"),
        stat(String(p.relevantCount), "prüfen (≤ 1 Jahr)"),
        stat(money(p.totalProfit), "Gewinn dieser Verkäufe", p.totalProfit >= 0 ? "pos" : "neg")
      );
      if (p.checkCount) checks.append(checkItem("warn", `${p.checkCount} Verkäufe sind nicht einzuordnen, weil Gegenstandsart oder Einkaufsdatum fehlen. Ergänze sie im Tracker (Bearbeiten).`));
      checks.append(checkItem(p.belowFreigrenze ? "ok" : "warn",
        p.belowFreigrenze
          ? `Der Gesamtgewinn der steuerbaren Kandidaten liegt unter der Freigrenze von ${p.freigrenze.toLocaleString("de-DE")} € (§ 23 Abs. 3 EStG). Keine Steuerberatung, bitte prüfen.`
          : `Der Gesamtgewinn erreicht die Freigrenze von ${p.freigrenze.toLocaleString("de-DE")} €. Dann wäre der gesamte Gewinn steuerpflichtig. Bitte steuerlich klären.`));
    }
  }

  /* ---------- Downloads ---------- */
  function run(kind) {
    const s = readSettings();
    const year = Number($("x-year").value);
    if (kind === "private") {
      SC.download(T.privateCsv(T.computePrivate(SC.sales, { year })), `sellcheck-anlage-so-${year}.csv`);
    } else {
      const r = T.computeEuer(SC.sales, { year, vat: s.vat, rate: s.rate });
      if (kind === "journal") SC.download(T.journalCsv(r), `sellcheck-journal-${year}.csv`);
      else SC.download(T.summaryCsv(r), `sellcheck-summen-${year}.csv`);
    }
    $("x-msg").textContent = "Datei erstellt. Sie liegt in deinem Download-Ordner.";
  }
  $("x-journal").addEventListener("click", () => run("journal"));
  $("x-summary").addEventListener("click", () => run("summary"));
  $("x-private").addEventListener("click", () => run("private"));

  ["x-year", "x-mode", "x-vat", "x-rate"].forEach((id) => $(id).addEventListener("change", update));
  ["x-name", "x-taxid"].forEach((id) => $(id).addEventListener("input", () => saveSettings(readSettings())));

  fillYears();
  update();
  SC.onRefresh(() => { fillYears(); update(); });
})();
