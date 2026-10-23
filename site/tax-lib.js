// Steuerlogik für den Export (ohne DOM, damit sie im Browser UND in Node getestet werden kann).
// Browser: window.SCTax   |   Node: require("./tax-lib.js")
//
// Wichtige Grundlagen (Quellen in STEUER-EXPORT.md):
//  - EÜR (§ 4 Abs. 3 EStG): Einnahmen zählen im Jahr des Zuflusses, Ausgaben im Jahr der Zahlung (§ 11 EStG).
//    Wareneinkauf ist deshalb im Zahlungsjahr abzugsfähig, auch wenn die Ware noch nicht verkauft ist.
//  - Kleinunternehmer (§ 19 UStG): Vorjahr bis 25.000 €, laufendes Jahr bis 100.000 €.
//  - Private Veräußerungsgeschäfte (§ 23 EStG): Frist 1 Jahr, Gegenstände des täglichen Gebrauchs ausgenommen,
//    Freigrenze 1.000 € Gesamtgewinn im Kalenderjahr (§ 23 Abs. 3 Satz 5).
//  - Alle Beträge werden intern in Cent (ganze Zahlen) gerechnet, um Rundungsdrift zu vermeiden.
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SCTax = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const KU_LIMIT_PREVIOUS = 25000;
  const KU_LIMIT_CURRENT = 100000;
  const GEWERBESTEUER_FREIBETRAG = 24500; // Quelle: Taxfix (Anbieterangabe), vor Verwendung prüfen
  const REPORTED_PLATFORMS = ["Vinted", "Kleinanzeigen", "eBay", "Etsy", "Amazon"];
  const MELDE_COUNT = 30;
  const MELDE_SUM = 2000;

  const cents = (x) => Math.round((Number(x) || 0) * 100);
  const fromCents = (c) => c / 100;
  const freigrenzePrivat = (year) => (Number(year) >= 2024 ? 1000 : 600);

  /* ---------- Meldegrenze (eine Quelle für Startseite, Tools und Report) ---------- */
  // § 4 Abs. 5 Satz 1 Nr. 4 PStTG: Freigestellt ist nur, wer auf derselben Plattform in weniger als 30 Fällen
  // verkauft UND dafür insgesamt weniger als 2.000 € erhalten hat. Bei genau 2.000,00 € meldet die Plattform also.
  // Rot = Grenze erreicht, Gelb ab 60 % einer der beiden Grenzen (Hinweisstufe, keine gesetzliche Größe).
  // Beträge in Cent, damit Summen wie 0,1 + 0,2 genau an der Grenze nicht als knapp darunter gelten.
  const MELDE_WARN = 0.6;
  function meldeStatus(count, revenueCents) {
    const c = Math.max(0, Math.floor(Number(count) || 0));
    const s = Math.max(0, Math.round(Number(revenueCents) || 0));
    const ratio = Math.max(c / MELDE_COUNT, s / (MELDE_SUM * 100));
    const reached = c >= MELDE_COUNT || s >= MELDE_SUM * 100;
    return {
      ratio,
      reached,
      level: reached ? "red" : ratio >= MELDE_WARN ? "yellow" : "green",
      // Unter der Grenze nie „100 %“ anzeigen (99,6 % wäre sonst gerundet 100 % bei Gelb)
      percent: reached ? Math.max(100, Math.floor(ratio * 100)) : Math.min(99, Math.floor(ratio * 100)),
    };
  }
  const sumCents = (list, key) => list.reduce((a, x) => a + cents(x[key]), 0);

  /* ---------- Bereinigen (auch gegen beschädigten localStorage) ---------- */
  const clampNum = (v) => (Number.isFinite(Number(v)) && Number(v) >= 0 && Number(v) < 1e9 ? Number(v) : 0);
  const ISO = /^\d{4}-\d{2}-\d{2}$/;
  const validIso = (s) => {
    if (!ISO.test(s)) return false;
    const [y, m, d] = s.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d));
    return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
  };
  const KINDS = ["everyday", "other"];

  function sanitizeEntry(e) {
    if (!e || typeof e !== "object") return null;
    const date = String(e.date || "");
    if (!validIso(date)) return null;
    const out = {
      id: String(e.id || Date.now() + Math.random().toString(36).slice(2, 7)).slice(0, 60),
      name: String(e.name || "Ohne Namen").slice(0, 80),
      date,
      platform: String(e.platform || "Sonstige").slice(0, 40),
      buy: clampNum(e.buy),
      sell: clampNum(e.sell),
      cost: clampNum(e.cost),
      status: e.status === "stock" ? "stock" : "sold",
    };
    if (e.needsBuy) out.needsBuy = true;
    if (typeof e.ref === "string") out.ref = e.ref.slice(0, 200);
    if (typeof e.batch === "string") out.batch = e.batch.slice(0, 40);
    if (typeof e.buyDate === "string" && validIso(e.buyDate)) out.buyDate = e.buyDate;
    if (typeof e.receipt === "string" && e.receipt.trim()) out.receipt = e.receipt.trim().slice(0, 60);
    if (KINDS.includes(e.kind)) out.kind = e.kind;
    return out;
  }

  const sanitizeSettings = (s) => {
    s = s && typeof s === "object" ? s : {};
    const rate = Number(s.rate);
    return {
      mode: s.mode === "private" ? "private" : "business",
      vat: s.vat === "regular" ? "regular" : "small",
      rate: rate === 7 || rate === 19 ? rate : 19,
      name: String(s.name || "").slice(0, 80),
      taxId: String(s.taxId || "").slice(0, 40),
    };
  };

  /* ---------- CSV (Excel-tauglich, deutsche Zahlen) ---------- */
  // Text: führendes = + - @ wird entschärft (Formel-Injection). Zahlen bleiben Zahlen.
  function csvText(v) {
    let s = String(v == null ? "" : v);
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }
  const csvNum = (c) => '"' + (c / 100).toFixed(2).replace(".", ",") + '"';
  const deDate = (iso) => (validIso(iso) ? iso.slice(8, 10) + "." + iso.slice(5, 7) + "." + iso.slice(0, 4) : "");
  function toCsv(headers, rows) {
    // rows: Arrays aus {t:Text}|{n:Cent}|"" -> bereits formatiert über cell()
    return "﻿" + [headers.map(csvText).join(";")].concat(rows.map((r) => r.join(";"))).join("\r\n") + "\r\n";
  }
  const cellT = (v) => csvText(v);
  const cellN = (c) => csvNum(c);

  /* ---------- EÜR ---------- */
  const inYear = (iso, y) => typeof iso === "string" && iso.slice(0, 4) === String(y);

  function buildLines(sales, opt) {
    const y = String(opt.year);
    const rate = opt.vat === "regular" ? opt.rate : 0;
    const lines = [];
    sales.forEach((s, idx) => {
      const base = { platform: s.platform, name: s.name, receipt: s.receipt || "", entryIndex: idx };
      if (s.status !== "stock" && s.sell > 0 && inYear(s.date, y)) {
        const gross = cents(s.sell);
        const net = rate ? Math.round(gross / (1 + rate / 100)) : gross;
        lines.push({ ...base, date: s.date, type: "in", category: "Erlöse", gross, net, vat: gross - net, rate, note: "" });
      }
      if (s.buy > 0) {
        const pdate = s.buyDate || s.date;
        if (inYear(pdate, y)) {
          const estimated = !s.buyDate && s.status !== "stock";
          const c = cents(s.buy);
          lines.push({ ...base, date: pdate, type: "out", category: "Wareneinkauf", gross: c, net: c, vat: 0, rate: 0, note: estimated ? "Einkaufsdatum fehlt, Verkaufsdatum angesetzt" : "", estimated });
        }
      }
      if (s.cost > 0 && inYear(s.date, y)) {
        const c = cents(s.cost);
        lines.push({ ...base, date: s.date, type: "out", category: "Sonstige Betriebsausgaben", gross: c, net: c, vat: 0, rate: 0, note: "" });
      }
    });
    lines.sort((a, b) => a.date.localeCompare(b.date) || (a.type === b.type ? 0 : a.type === "in" ? -1 : 1));
    lines.forEach((l, i) => (l.no = i + 1));
    return lines;
  }

  function computeEuer(rawSales, opt) {
    const sales = rawSales.map(sanitizeEntry).filter(Boolean);
    const o = { year: opt.year, vat: opt.vat === "regular" ? "regular" : "small", rate: opt.rate === 7 ? 7 : 19 };
    const y = String(o.year);
    const lines = buildLines(sales, o);

    const sum = (arr, k) => arr.reduce((a, l) => a + l[k], 0);
    const ins = lines.filter((l) => l.type === "in");
    const outs = lines.filter((l) => l.type === "out");
    const goods = outs.filter((l) => l.category === "Wareneinkauf");
    const other = outs.filter((l) => l.category !== "Wareneinkauf");

    const res = {
      year: o.year,
      vat: o.vat,
      rate: o.vat === "regular" ? o.rate : 0,
      revenueGross: sum(ins, "gross"),
      revenueNet: sum(ins, "net"),
      vatCollected: sum(ins, "vat"),
      goods: sum(goods, "gross"),
      other: sum(other, "gross"),
      lines,
      count: ins.length,
    };
    res.revenueTotal = res.revenueNet + res.vatCollected; // Summe Betriebseinnahmen (inkl. vereinnahmter USt bei Regelbesteuerung)
    res.expensesTotal = res.goods + res.other;
    res.profit = res.revenueNet - res.expensesTotal; // Gewinn auf Basis der Netto-Einnahmen (USt ist durchlaufender Posten)

    // Je Plattform
    const plat = new Map();
    const get = (p) => {
      if (!plat.has(p)) plat.set(p, { platform: p, count: 0, revenue: 0, goods: 0, other: 0 });
      return plat.get(p);
    };
    lines.forEach((l) => {
      const r = get(l.platform);
      if (l.type === "in") { r.count++; r.revenue += l.gross; }
      else if (l.category === "Wareneinkauf") r.goods += l.gross;
      else r.other += l.gross;
    });
    res.byPlatform = [...plat.values()].map((r) => {
      const reported = REPORTED_PLATFORMS.includes(r.platform);
      const st = meldeStatus(r.count, r.revenue);
      return { ...r, profit: r.revenue - r.goods - r.other, reported, meldegrenze: reported && st.reached, level: reported ? st.level : "none" };
    }).sort((a, b) => b.revenue - a.revenue);

    // Je Monat
    res.byMonth = Array.from({ length: 12 }, (_, i) => ({ month: i + 1, revenue: 0, expenses: 0 }));
    lines.forEach((l) => {
      const m = Number(l.date.slice(5, 7)) - 1;
      if (l.type === "in") res.byMonth[m].revenue += l.gross; else res.byMonth[m].expenses += l.gross;
    });

    res.warnings = qualityWarnings(sales, res, o);
    return res;
  }

  function qualityWarnings(sales, res, o) {
    const y = String(o.year);
    const w = [];
    const soldY = sales.filter((s) => s.status !== "stock" && inYear(s.date, y));
    const estimated = res.lines.filter((l) => l.estimated).length;
    if (estimated) w.push({ level: "warn", code: "buyDateMissing", count: estimated, text: `Bei ${estimated} Verkäufen fehlt das Einkaufsdatum. Der Einkauf wurde im Verkaufsjahr angesetzt. In der EÜR zählt das Jahr der Bezahlung: Trage das Einkaufsdatum nach, wenn die Ware in einem anderen Jahr gekauft wurde.` });
    // Bestand: bezahlt, aber noch nicht verkauft. In der EÜR trotzdem im Zahlungsjahr abzugsfähig.
    const stockLines = res.lines.filter((l) => l.category === "Wareneinkauf" && sales[l.entryIndex] && sales[l.entryIndex].status === "stock");
    if (stockLines.length) {
      const sumStock = stockLines.reduce((a, l) => a + l.gross, 0);
      w.push({ level: "info", code: "stock", count: stockLines.length, text: `Im Wareneinkauf sind ${(sumStock / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" })} für ${stockLines.length} noch nicht verkaufte Artikel enthalten. In der EÜR zählt die Bezahlung, nicht der Verkauf, deshalb mindert dieser Einkauf den Gewinn schon in diesem Jahr.` });
    }
    const noBuy = soldY.filter((s) => s.needsBuy && !(s.buy > 0)).length;
    if (noBuy) w.push({ level: "warn", code: "buyMissing", count: noBuy, text: `Bei ${noBuy} importierten Verkäufen fehlt der Einkaufspreis. Der Gewinn ist dadurch zu hoch angesetzt.` });
    const noReceipt = soldY.filter((s) => !s.receipt).length;
    if (noReceipt) w.push({ level: "info", code: "receiptMissing", count: noReceipt, text: `${noReceipt} Verkäufe haben keine Belegnummer. Eine Belegnummer (z. B. Bestellnummer) erleichtert die Prüfung.` });
    if (o.vat === "small" && fromCents(res.revenueGross) > KU_LIMIT_PREVIOUS) w.push({ level: "warn", code: "kuLimit", text: `Die Einnahmen liegen über ${KU_LIMIT_PREVIOUS.toLocaleString("de-DE")} €. Für das Folgejahr kann die Kleinunternehmerregelung entfallen (Grenze Vorjahr ${KU_LIMIT_PREVIOUS.toLocaleString("de-DE")} €, laufendes Jahr ${KU_LIMIT_CURRENT.toLocaleString("de-DE")} €, § 19 UStG). Bitte steuerlich klären.` });
    if (o.vat === "small" && fromCents(res.revenueGross) > KU_LIMIT_CURRENT) w.push({ level: "warn", code: "kuLimitCurrent", text: `Die Einnahmen liegen über ${KU_LIMIT_CURRENT.toLocaleString("de-DE")} €. Die Kleinunternehmerregelung gilt dann bereits im laufenden Jahr nicht mehr. Bitte umgehend mit dem Steuerberater klären.` });
    if (fromCents(res.profit) > GEWERBESTEUER_FREIBETRAG) w.push({ level: "info", code: "gewerbesteuer", text: `Der Gewinn liegt über dem Gewerbesteuer-Freibetrag für Einzelunternehmen (${GEWERBESTEUER_FREIBETRAG.toLocaleString("de-DE")} €, Anbieterangabe, bitte prüfen). Gewerbesteuer kann anfallen.` });
    if (res.vat === "regular") w.push({ level: "info", code: "vorsteuer", text: "Vorsteuer aus Einkäufen und die Umsatzsteuer-Voranmeldung bzw. -Erklärung sind in diesem Report nicht enthalten. Einkaufspreise werden unverändert als Betriebsausgaben angesetzt." });
    res.dataComplete = !w.some((x) => x.level === "warn");
    return w;
  }

  /* ---------- Journal & Summen als CSV ---------- */
  function journalCsv(res) {
    const head = ["Lfd. Nr.", "Belegdatum", "Belegnr.", "Plattform", "Beschreibung", "Buchungsart", "Kategorie", "Betrag brutto", "USt-Satz %", "Netto", "Umsatzsteuer", "Hinweis"];
    const rows = res.lines.map((l) => [
      cellT(l.no), cellT(deDate(l.date)), cellT(l.receipt), cellT(l.platform), cellT(l.name),
      cellT(l.type === "in" ? "Einnahme" : "Ausgabe"), cellT(l.category), cellN(l.gross),
      cellT(l.rate ? String(l.rate) : ""), cellN(l.net), cellN(l.vat), cellT(l.note),
    ]);
    return toCsv(head, rows);
  }

  function summaryRows(res) {
    const small = res.vat === "small";
    const rows = [];
    if (small) rows.push(["Betriebseinnahmen als umsatzsteuerlicher Kleinunternehmer (§ 19 Abs. 1 UStG)", res.revenueNet, ""]);
    else {
      rows.push([`Umsatzsteuerpflichtige Betriebseinnahmen (netto, ${res.rate} %)`, res.revenueNet, ""]);
      rows.push(["Vereinnahmte Umsatzsteuer", res.vatCollected, ""]);
    }
    rows.push(["Summe Betriebseinnahmen", res.revenueTotal, ""]);
    rows.push(["Waren, Roh- und Hilfsstoffe einschließlich Nebenkosten", res.goods, "Wareneinkauf im Jahr der Bezahlung"]);
    rows.push(["Sonstige Betriebsausgaben (Versand, Porto, Plattform- und Zahlungsgebühren u. Ä.)", res.other, "Im Formular auf die passenden Ausgabenzeilen verteilen"]);
    rows.push(["Summe Betriebsausgaben", res.expensesTotal, ""]);
    rows.push(["Gewinn / Verlust", res.profit, "Weiter in die Anlage G (Einkünfte aus Gewerbebetrieb)"]);
    return rows;
  }
  const summaryCsv = (res) =>
    toCsv(["Position (Bezeichnung wie in der Anlage EÜR)", "Betrag in EUR", "Hinweis"], summaryRows(res).map((r) => [cellT(r[0]), cellN(r[1]), cellT(r[2])]));

  /* ---------- Privat: Vorbereitung Anlage SO (§ 23 EStG) ---------- */
  const addYears = (iso, n) => {
    const [y, m, d] = iso.split("-").map(Number);
    const dt = new Date(Date.UTC(y + n, m - 1, d));
    // 29.02. -> 01.03. im Nicht-Schaltjahr: auf den letzten Tag des Monats zurück (Frist endet mit Ablauf des Tages der Anschaffung im Folgejahr)
    if (dt.getUTCMonth() !== m - 1) dt.setUTCDate(0);
    return dt.toISOString().slice(0, 10);
  };

  function computePrivate(rawSales, opt) {
    const sales = rawSales.map(sanitizeEntry).filter(Boolean);
    const y = String(opt.year);
    const items = sales
      .filter((s) => s.status !== "stock" && s.sell > 0 && inYear(s.date, y))
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((s, i) => {
        const profit = cents(s.sell) - cents(s.buy) - cents(s.cost);
        let status, reason;
        if (s.kind === "everyday") { status = "free"; reason = "Gegenstand des täglichen Gebrauchs: nicht steuerbar (§ 23 Abs. 1 Satz 1 Nr. 2 Satz 2 EStG)"; }
        else if (s.kind === "other" && s.buyDate) {
          if (s.date <= addYears(s.buyDate, 1)) { status = "relevant"; reason = "Verkauf innerhalb eines Jahres nach Anschaffung: steuerbar, wenn die Freigrenze überschritten wird"; }
          else { status = "free"; reason = "Haltefrist von einem Jahr überschritten: nicht steuerbar"; }
        } else if (s.kind === "other") { status = "check"; reason = "Einkaufsdatum fehlt, Haltefrist nicht prüfbar"; }
        else { status = "check"; reason = "Gegenstandsart nicht angegeben (Gebrauchsgegenstand oder Sonstiges?)"; }
        return { no: i + 1, name: s.name, platform: s.platform, receipt: s.receipt || "", buyDate: s.buyDate || "", date: s.date, buy: cents(s.buy), sell: cents(s.sell), cost: cents(s.cost), profit, status, reason };
      });
    const relevant = items.filter((i) => i.status === "relevant");
    const total = relevant.reduce((a, i) => a + i.profit, 0);
    const limit = freigrenzePrivat(opt.year);
    return {
      year: opt.year, items, relevantCount: relevant.length, checkCount: items.filter((i) => i.status === "check").length,
      freeCount: items.filter((i) => i.status === "free").length, totalProfit: total, freigrenze: limit,
      // Freigrenze: Gesamtgewinn < Grenze bleibt steuerfrei; ab der Grenze ist der gesamte Gewinn steuerpflichtig.
      belowFreigrenze: fromCents(total) < limit,
      revenue: items.reduce((a, i) => a + i.sell, 0),
    };
  }

  function privateCsv(p) {
    const head = ["Lfd. Nr.", "Bezeichnung des Wirtschaftsguts", "Plattform", "Belegnr.", "Datum der Anschaffung", "Datum der Veräußerung", "Veräußerungspreis", "Anschaffungskosten", "Werbungskosten (Versand, Gebühren)", "Gewinn / Verlust", "Einordnung", "Begründung"];
    const label = { relevant: "Steuerbar prüfen (innerhalb 1 Jahr)", free: "Nicht steuerbar", check: "Angaben fehlen" };
    return toCsv(head, p.items.map((i) => [cellT(i.no), cellT(i.name), cellT(i.platform), cellT(i.receipt), cellT(deDate(i.buyDate)), cellT(deDate(i.date)), cellN(i.sell), cellN(i.buy), cellN(i.cost), cellN(i.profit), cellT(label[i.status]), cellT(i.reason)]));
  }

  return {
    KU_LIMIT_PREVIOUS, KU_LIMIT_CURRENT, GEWERBESTEUER_FREIBETRAG, REPORTED_PLATFORMS, MELDE_COUNT, MELDE_SUM, MELDE_WARN,
    meldeStatus, sumCents, cents, fromCents, freigrenzePrivat, sanitizeEntry, sanitizeSettings, validIso, csvText, csvNum, deDate, toCsv, cellT, cellN,
    computeEuer, journalCsv, summaryRows, summaryCsv, computePrivate, privateCsv, addYears,
  };
});
