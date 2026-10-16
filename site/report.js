// Druckbarer Steuer-Report. Liest die Daten aus dem lokalen Speicher (nichts wird gesendet).
// Alle Inhalte kommen per textContent ins DOM, nie als HTML.
(function () {
  "use strict";
  const T = window.SCTax;
  const root = document.getElementById("report");
  const eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
  const money = (c) => eur.format(c / 100);

  const h = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined && text !== null) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  const row = (cells, cls) => {
    const tr = h("tr", undefined, cls);
    cells.forEach((c) => {
      const td = h("td", c.text !== undefined ? c.text : c, c.cls);
      tr.append(td);
    });
    return tr;
  };
  // Weiche Trennstellen in langen Spaltenköpfen (Veräußerungs|preis), damit nichts über den Rand läuft
  const shy = (x) => String(x).replace(/ungs(?=[a-zß]{4,})/g, "ungs\u00AD").replace(/Waren(?=einkauf)/g, "Waren\u00AD");
  // widths: Spaltenbreiten in Prozent (Summe 100). Mit Breiten ist das Layout fest und die Tabelle bleibt im Blatt.
  const table = (headers, rows, numCols, widths) => {
    const t = h("table", undefined, headers.length >= 6 ? "wide" : "");
    if (widths && widths.length === headers.length) {
      const cg = h("colgroup");
      widths.forEach((w) => { const c = h("col"); c.style.width = w + "%"; cg.append(c); });
      t.append(cg);
      t.classList.add("fixed");
    }
    const thead = h("thead");
    const hr = h("tr");
    headers.forEach((x, i) => hr.append(h("th", shy(x), numCols && numCols.includes(i) ? "num" : "")));
    thead.append(hr);
    const tb = h("tbody");
    rows.forEach((r) => tb.append(r));
    t.append(thead, tb);
    const wrap = h("div", undefined, "tablewrap");
    wrap.append(t);
    return wrap;
  };
  const note = (text, cls) => h("p", text, "note" + (cls ? " " + cls : ""));

  function load() {
    let sales = [];
    try {
      const raw = localStorage.getItem("sellcheck.sales.v1") || localStorage.getItem("vintcheck.sales.v1") || "[]";
      const d = JSON.parse(raw);
      if (Array.isArray(d)) sales = d.map(T.sanitizeEntry).filter(Boolean);
    } catch { /* leerer Bestand */ }
    let settings;
    try { settings = T.sanitizeSettings(JSON.parse(localStorage.getItem("sellcheck.settings.v1") || "{}")); }
    catch { settings = T.sanitizeSettings({}); }
    return { sales, settings };
  }

  function header(title, subtitle, year, s, extraMeta) {
    const wrap = document.createDocumentFragment();
    const bl = h("div", undefined, "brandline");
    const mark = h("span", undefined, "mark");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "12.8 4.8 38.4 54.4");
    svg.setAttribute("aria-hidden", "true");
    const p1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p1.setAttribute("d", "M14 6H50V58L45 52.5 40 58 35 52.5 30 58 25 52.5 20 58 14 52.5Z");
    p1.setAttribute("fill", "#111318");
    p1.setAttribute("stroke", "#111318");
    p1.setAttribute("stroke-width", "2.4");
    p1.setAttribute("stroke-linejoin", "round");
    const p2 = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p2.setAttribute("d", "M22 30l7.5 7.5L43 22");
    p2.setAttribute("fill", "none");
    p2.setAttribute("stroke", "#c8f169");
    p2.setAttribute("stroke-width", "6.4");
    p2.setAttribute("stroke-linecap", "round");
    p2.setAttribute("stroke-linejoin", "round");
    svg.append(p1, p2);
    mark.append(svg, document.createTextNode("SellCheck"));
    bl.append(mark, h("small", "Erstellt am " + new Date().toLocaleDateString("de-DE")));
    wrap.append(bl, h("h1", title), h("p", subtitle, "sub"));

    const meta = [
      ["Steuerjahr", String(year)],
      ["Zeitraum", `01.01.${year} bis 31.12.${year}`],
    ];
    if (s.name) meta.unshift(["Name", s.name]);
    if (s.taxId) meta.splice(1, 0, ["Steuernummer", s.taxId]);
    extraMeta.forEach((m) => meta.push(m));
    const t = h("table", undefined, "meta");
    const tb = h("tbody");
    meta.forEach((m) => tb.append(row([m[0], m[1]])));
    t.append(tb);
    wrap.append(t);
    return wrap;
  }

  /* ---------- Gewerblich: Anlage EÜR ---------- */
  function businessReport(sales, s, year) {
    const r = T.computeEuer(sales, { year, vat: s.vat, rate: s.rate });
    const frag = document.createDocumentFragment();
    frag.append(
      header("Einnahmen und Ausgaben " + year, "Ausfüllhilfe für die Anlage EÜR (Gewinnermittlung nach § 4 Abs. 3 EStG)", year, s, [
        ["Umsatzsteuer", s.vat === "small" ? "Kleinunternehmer (§ 19 UStG), keine Umsatzsteuer" : `Regelbesteuerung, Preise inkl. ${s.rate} % USt`],
        ["Buchungen im Jahr", String(r.lines.length)],
      ])
    );
    frag.append(note("Diese Aufstellung ist eine Ausfüllhilfe und keine Steuererklärung. Sie wird nicht an das Finanzamt übermittelt. Die Anlage EÜR ist grundsätzlich elektronisch (z. B. über Mein ELSTER) abzugeben. Sie ersetzt keine Steuerberatung. Bitte alle Angaben vor der Abgabe prüfen.", "warn"));

    // 1. Übertragungsbogen
    frag.append(h("h2", "1. Beträge für die Anlage EÜR"));
    const rows = T.summaryRows(r).map((x) => {
      const cls = x[0] === "Gewinn / Verlust" ? "result" : x[0].startsWith("Summe") ? "sum" : "";
      return row([x[0], { text: money(x[1]), cls: "num" + (x[1] < 0 ? " neg" : "") }, { text: x[2], cls: "small" }], cls);
    });
    frag.append(table(["Position (Bezeichnung wie im Formular)", "Betrag", "Hinweis"], rows, [1]));
    frag.append(h("p", "Zeilennummern ändern sich von Jahr zu Jahr und sind hier bewusst nicht angegeben. Ordne die Beträge in Mein ELSTER über die Bezeichnung zu.", "small"));

    // 2. Hinweise
    frag.append(h("h2", "2. Datenqualität und Hinweise"));
    if (r.dataComplete) frag.append(note("Keine Datenlücken gefunden, die das Ergebnis verfälschen.", "good"));
    r.warnings.forEach((w) => frag.append(note(w.text, w.level === "warn" ? "warn" : "")));

    // 3. Plattform
    frag.append(h("h2", "3. Nach Plattform"));
    frag.append(h("p", s.vat === "regular" ? "Beträge brutto (inklusive Umsatzsteuer), soweit nicht anders angegeben." : "Beträge in Euro.", "small"));
    const prow = r.byPlatform.map((p) =>
      row([p.platform, { text: String(p.count), cls: "num" }, { text: money(p.revenue), cls: "num" }, { text: money(p.goods), cls: "num" }, { text: money(p.other), cls: "num" },
        { text: money(p.profit), cls: "num" + (p.profit < 0 ? " neg" : "") }, p.reported ? (p.meldegrenze ? "Grenze erreicht" : "darunter") : "keine Meldung"]));
    frag.append(table(["Plattform", "Verkäufe", "Einnahmen", "Wareneinkauf", "Sonstige Ausgaben", "Ergebnis", "Meldegrenze"], prow, [1, 2, 3, 4, 5], [16, 9, 14, 15, 17, 14, 15]));
    frag.append(h("p", `Meldegrenze: ${T.MELDE_COUNT} Verkäufe oder ${T.MELDE_SUM.toLocaleString("de-DE")} € pro Plattform und Jahr (§ 4 Abs. 5 PStTG). Eine Meldung ist keine Steuerforderung.`, "small"));

    // 4. Monate
    frag.append(h("h2", "4. Nach Monat"));
    const months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];
    const mrows = r.byMonth.map((m, i) => row([months[i], { text: money(m.revenue), cls: "num" }, { text: money(m.expenses), cls: "num" }, { text: money(m.revenue - m.expenses), cls: "num" + (m.revenue - m.expenses < 0 ? " neg" : "") }]));
    frag.append(table(["Monat", "Einnahmen", "Ausgaben", "Saldo"], mrows, [1, 2, 3]));

    // 5. Journal
    const j = h("div", undefined, "pagebreak");
    j.append(h("h2", "5. Journal aller Buchungen"));
    const regular = s.vat === "regular";
    const jrows = r.lines.map((l) => {
      const cells = [{ text: String(l.no), cls: "num" }, T.deDate(l.date), l.receipt || "–", l.platform, l.name, l.type === "in" ? "Einnahme" : "Ausgabe", l.category];
      cells.push({ text: money(l.gross), cls: "num" });
      if (regular) cells.push({ text: l.type === "in" ? money(l.vat) : "", cls: "num" });
      return row(cells);
    });
    const jh = ["Nr.", "Datum", "Beleg", "Plattform", "Beschreibung", "Art", "Kategorie", "Betrag"];
    if (regular) jh.push("USt");
    j.append(jrows.length ? table(jh, jrows, regular ? [0, 7, 8] : [0, 7], regular ? [5, 10, 11, 13, 20, 8, 15, 9, 9] : [5, 11, 12, 13, 25, 9, 17, 8]) : h("p", "Keine Buchungen in diesem Jahr."));
    j.append(h("p", "Einnahmen zählen im Jahr des Zuflusses, Ausgaben im Jahr der Zahlung (§ 11 EStG). Als Einnahmedatum wird das Verkaufsdatum verwendet. Weicht der Zahlungseingang auf dein Konto in ein anderes Jahr ab, bitte prüfen.", "small"));
    frag.append(j);

    // 6. Abgabe
    frag.append(h("h2", "6. So geht es weiter"));
    const ul = h("ul", undefined, "plain");
    [
      "Selbst eintragen: Mein ELSTER, Formulare und Leistungen, Alle Formulare, Gewinnermittlung, Anlage EÜR (Pfad laut Ratgebern, die Oberfläche kann abweichen). Nicht betroffene Felder leer lassen.",
      "Den Gewinn übernimmst du in die Anlage G (Einkünfte aus Gewerbebetrieb) der Einkommensteuererklärung.",
      "Mit Steuerberater: diesen Report als PDF und das Journal als CSV übergeben.",
      "Papier ist nur in Härtefällen auf Antrag möglich (§ 150 Abs. 8 AO).",
      "Belege (Einkaufsbelege, Verkaufsbestätigungen, Plattform-Abrechnungen) geordnet aufbewahren. Aufbewahrungsfristen bitte mit dem Steuerberater klären.",
    ].forEach((t) => ul.append(h("li", t)));
    frag.append(ul);
    const sign = h("div", undefined, "sign");
    sign.append(h("div", "Ort, Datum"), h("div", "Unterschrift"));
    frag.append(sign);
    frag.append(h("p", "Erstellt mit SellCheck, einem unabhängigen Projekt, das mit keiner Plattform und keiner Behörde verbunden ist. Keine Steuer- oder Rechtsberatung. Alle Angaben ohne Gewähr.", "footer-note"));
    return frag;
  }

  /* ---------- Privat: Anlage SO ---------- */
  function privateReport(sales, s, year) {
    const p = T.computePrivate(sales, { year });
    const frag = document.createDocumentFragment();
    frag.append(header("Private Verkäufe " + year, "Vorbereitung für die Anlage SO (private Veräußerungsgeschäfte, § 23 EStG)", year, s, [["Verkäufe im Jahr", String(p.items.length)]]));
    frag.append(note("Diese Aufstellung ist eine Ausfüllhilfe und keine Steuererklärung. Sie ersetzt keine Beratung. Die Einordnung beruht auf deinen Angaben.", "warn"));

    frag.append(h("h2", "1. Ergebnis"));
    const sumRows = [
      row(["Verkäufe insgesamt", { text: String(p.items.length), cls: "num" }]),
      row(["davon nicht steuerbar (Gebrauchsgegenstand oder Haltefrist überschritten)", { text: String(p.freeCount), cls: "num" }]),
      row(["davon zu prüfen (Verkauf innerhalb eines Jahres, kein Gebrauchsgegenstand)", { text: String(p.relevantCount), cls: "num" }]),
      row(["davon nicht einzuordnen (Angaben fehlen)", { text: String(p.checkCount), cls: "num" }]),
      row(["Gesamtgewinn der zu prüfenden Verkäufe", { text: money(p.totalProfit), cls: "num" + (p.totalProfit < 0 ? " neg" : "") }], "result"),
      row([`Freigrenze für ${year} (§ 23 Abs. 3 Satz 5 EStG)`, { text: p.freigrenze.toLocaleString("de-DE") + " €", cls: "num" }]),
    ];
    frag.append(table(["Angabe", "Wert"], sumRows, [1]));
    if (p.checkCount) frag.append(note(`${p.checkCount} Verkäufe konnten nicht eingeordnet werden. Das Ergebnis ist vorläufig. Ergänze Gegenstandsart und Einkaufsdatum im Tracker.`, "warn"));
    frag.append(note(p.belowFreigrenze
      ? `Der Gesamtgewinn der zu prüfenden Verkäufe liegt unter der Freigrenze von ${p.freigrenze.toLocaleString("de-DE")} €. Nach diesen Angaben bleibt er steuerfrei. Bitte prüfen.`
      : `Der Gesamtgewinn erreicht die Freigrenze von ${p.freigrenze.toLocaleString("de-DE")} €. Dann ist der gesamte Gewinn steuerpflichtig und in der Anlage SO anzugeben. Bitte steuerlich klären.`, p.belowFreigrenze ? "good" : "bad"));
    frag.append(h("p", "Freigrenze heißt: Ab dem Erreichen der Grenze ist der gesamte Gewinn steuerpflichtig, nicht nur der übersteigende Teil. Für Jahre vor 2024 galt 600 €. Den Anwendungszeitpunkt bitte prüfen.", "small"));

    frag.append(h("h2", "2. Verkäufe im Einzelnen (Spalten wie in der Anlage SO)"));
    const label = { relevant: "zu prüfen", free: "nicht steuerbar", check: "Angaben fehlen" };
    const rows = p.items.map((i) => row([
      { text: String(i.no), cls: "num" }, i.name + (i.receipt ? ` (${i.receipt})` : ""), T.deDate(i.buyDate) || "–", T.deDate(i.date),
      { text: money(i.sell), cls: "num" }, { text: money(i.buy), cls: "num" }, { text: money(i.cost), cls: "num" },
      { text: money(i.profit), cls: "num" + (i.profit < 0 ? " neg" : "") }, label[i.status],
    ]));
    frag.append(p.items.length ? table(["Nr.", "Bezeichnung", "Anschaffung", "Veräußerung", "Veräußerungspreis", "Anschaffungskosten", "Werbungskosten", "Gewinn", "Einordnung"], rows, [0, 4, 5, 6, 7], [5, 18.5, 10.5, 10.5, 11.5, 11.5, 10, 8.5, 13.5]) : h("p", "Keine Verkäufe in diesem Jahr."));

    frag.append(h("h2", "3. Hinweise"));
    const ul = h("ul", undefined, "plain");
    [
      "Gegenstände des täglichen Gebrauchs (z. B. Kleidung) sind von der Besteuerung ausgenommen (§ 23 Abs. 1 Satz 1 Nr. 2 Satz 2 EStG).",
      "Verkäufe anderer Gegenstände sind nur steuerbar, wenn zwischen Anschaffung und Verkauf höchstens ein Jahr liegt.",
      "Wer regelmäßig zum Weiterverkauf einkauft, kann gewerblich handeln. Dann gelten andere Regeln (Anlage EÜR). Nutze dafür den Modus „gewerblich“.",
      "Die Daten der Plattformen (Meldung ab 30 Verkäufen oder 2.000 € pro Plattform) ersetzen diese Prüfung nicht.",
    ].forEach((t) => ul.append(h("li", t)));
    frag.append(ul);
    frag.append(h("p", "Erstellt mit SellCheck, einem unabhängigen Projekt, das mit keiner Plattform und keiner Behörde verbunden ist. Keine Steuer- oder Rechtsberatung. Alle Angaben ohne Gewähr.", "footer-note"));
    return frag;
  }

  /* ---------- Aufbau und Datei ---------- */
  function buildFor(year) {
    const { sales, settings } = load();
    if (!sales.some((e) => e.date.startsWith(String(year)))) return null;
    return settings.mode === "private" ? privateReport(sales, settings, year) : businessReport(sales, settings, year);
  }

  const escapeHtml = (x) => String(x).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  // Eigenständige HTML-Datei (Stil eingebettet, keine Skripte), lässt sich offline öffnen und drucken.
  async function buildHtml(year) {
    const node = buildFor(year);
    if (!node) return null;
    let css = "";
    try {
      const res = await fetch("report.css", { credentials: "omit" });
      if (res.ok) css = await res.text();
    } catch { /* ohne Stil trotzdem lesbar */ }
    const box = document.createElement("div");
    box.append(node);
    const title = `Steuer-Report ${year} – SellCheck`;
    return `<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="color-scheme" content="light">\n<meta name="robots" content="noindex">\n<title>${escapeHtml(title)}</title>\n<style>\n${css}\n</style>\n</head>\n<body>\n<main class="sheet">\n${box.innerHTML}\n</main>\n</body>\n</html>\n`;
  }

  window.SCReport = { buildHtml };

  /* ---------- Start (nur auf der Report-Seite) ---------- */
  if (!root) return;
  const q = new URLSearchParams(location.search);
  let year = Number(q.get("y"));
  if (!Number.isInteger(year) || year < 2000 || year > 2100) year = new Date().getFullYear();

  root.replaceChildren();
  const built = buildFor(year);
  if (!built) {
    root.append(h("h1", "Keine Daten"), h("p", `Für ${year} gibt es keine Einträge im Tracker. Öffne die Tools-Seite im selben Browser, in dem du deine Daten erfasst hast.`));
  } else {
    root.append(built);
  }
  document.title = `Steuer-Report ${year} – SellCheck`;
  document.getElementById("print").addEventListener("click", () => window.print());
  const dl = document.getElementById("download");
  if (dl) {
    dl.addEventListener("click", async () => {
      const html = await buildHtml(year);
      if (!html) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
      a.download = `sellcheck-report-${year}.html`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
  }
})();
