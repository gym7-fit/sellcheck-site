// Ausführen: node --test tests/tax.test.js
// Jeder Test schützt eine Aussage, die später in einer Steuererklärung stehen könnte.
const test = require("node:test");
const assert = require("node:assert/strict");
const T = require("../site/tax-lib.js");

const e = (o) => ({ id: Math.random().toString(36).slice(2), name: "Artikel", platform: "Vinted", buy: 0, sell: 0, cost: 0, status: "sold", ...o });
const eur = (c) => c / 100;

/* ---- EÜR: Zeitpunkt (Abfluss-/Zuflussprinzip) ---- */
test("EÜR: Einkauf zählt im Jahr der Bezahlung, nicht im Verkaufsjahr", () => {
  const sales = [e({ date: "2026-02-10", buyDate: "2025-11-20", buy: 10, sell: 30 })];
  const y25 = T.computeEuer(sales, { year: 2025, vat: "small" });
  const y26 = T.computeEuer(sales, { year: 2026, vat: "small" });
  assert.equal(eur(y25.goods), 10, "2025: Einkauf abzugsfähig");
  assert.equal(eur(y25.revenueNet), 0, "2025: noch keine Einnahme");
  assert.equal(eur(y26.goods), 0, "2026: Einkauf nicht noch einmal");
  assert.equal(eur(y26.revenueNet), 30);
  assert.equal(eur(y25.profit) + eur(y26.profit), 20, "über beide Jahre stimmt der Gesamtgewinn");
});

test("EÜR: unverkaufter Bestand mindert den Gewinn schon im Einkaufsjahr", () => {
  const sales = [e({ date: "2026-05-01", status: "stock", buy: 40 }), e({ date: "2026-06-01", buy: 5, sell: 20 })];
  const r = T.computeEuer(sales, { year: 2026, vat: "small" });
  assert.equal(eur(r.goods), 45);
  assert.equal(eur(r.profit), 20 - 45);
});

test("EÜR: Bestand erscheint als eigener Hinweis mit Betrag und Anzahl", () => {
  const r = T.computeEuer([e({ date: "2026-05-01", status: "stock", buy: 40 }), e({ date: "2026-05-02", status: "stock", buy: 2.5 })], { year: 2026, vat: "small" });
  const w = r.warnings.find((x) => x.code === "stock");
  assert.ok(w);
  assert.equal(w.count, 2);
  assert.ok(w.text.includes("42,50"));
  assert.equal(r.dataComplete, true, "ein Info-Hinweis ist kein Datenfehler");
});

test("EÜR: fehlendes Einkaufsdatum wird geschätzt und deutlich gewarnt", () => {
  const r = T.computeEuer([e({ date: "2026-03-03", buy: 8, sell: 20 })], { year: 2026, vat: "small" });
  assert.equal(eur(r.goods), 8);
  const w = r.warnings.find((x) => x.code === "buyDateMissing");
  assert.ok(w && w.count === 1);
  assert.equal(r.dataComplete, false);
  assert.ok(r.lines.find((l) => l.category === "Wareneinkauf").note.includes("Einkaufsdatum fehlt"));
});

test("EÜR: Einträge anderer Jahre bleiben draußen", () => {
  const r = T.computeEuer([e({ date: "2025-12-31", buy: 1, sell: 10, cost: 1 }), e({ date: "2026-01-01", buy: 2, sell: 20, cost: 2 })], { year: 2026, vat: "small" });
  assert.equal(eur(r.revenueNet), 20);
  assert.equal(eur(r.other), 2);
});

/* ---- Umsatzsteuer ---- */
test("Regelbesteuerung: Brutto wird in Netto und Umsatzsteuer zerlegt, Gewinn rechnet mit Netto", () => {
  const r = T.computeEuer([e({ date: "2026-04-01", sell: 119, buy: 50 })], { year: 2026, vat: "regular", rate: 19 });
  assert.equal(eur(r.revenueNet), 100);
  assert.equal(eur(r.vatCollected), 19);
  assert.equal(eur(r.revenueTotal), 119);
  assert.equal(eur(r.profit), 100 - 50);
  assert.ok(r.warnings.some((w) => w.code === "vorsteuer"));
});

test("Regelbesteuerung: Rundung pro Beleg, Netto plus USt ergibt immer exakt Brutto", () => {
  const sales = [];
  for (let i = 0; i < 50; i++) sales.push(e({ date: "2026-04-01", sell: 9.99 + i * 0.37 }));
  const r = T.computeEuer(sales, { year: 2026, vat: "regular", rate: 19 });
  assert.equal(r.revenueNet + r.vatCollected, r.revenueGross);
  r.lines.filter((l) => l.type === "in").forEach((l) => assert.equal(l.net + l.vat, l.gross));
});

test("Kleinunternehmer: keine Umsatzsteuer, Grenzwarnung über 25.000 € und 100.000 €", () => {
  const some = T.computeEuer([e({ date: "2026-04-01", sell: 100 })], { year: 2026, vat: "small" });
  assert.equal(some.vatCollected, 0);
  assert.ok(!some.warnings.some((w) => w.code.startsWith("ku")));
  const big = T.computeEuer([e({ date: "2026-04-01", sell: 26000 })], { year: 2026, vat: "small" });
  assert.ok(big.warnings.some((w) => w.code === "kuLimit"));
  const huge = T.computeEuer([e({ date: "2026-04-01", sell: 101000 })], { year: 2026, vat: "small" });
  assert.ok(huge.warnings.some((w) => w.code === "kuLimitCurrent"));
});

/* ---- Rechenintegrität ---- */
test("Journal und Summen gehen auf: Summe der Journalzeilen = Positionen im Report", () => {
  const sales = [
    e({ date: "2026-01-05", sell: 19.9, buy: 5, cost: 3.9, buyDate: "2026-01-01" }),
    e({ date: "2026-02-05", sell: 0.1, buy: 0.2, cost: 0.3 }),
    e({ date: "2026-03-05", status: "stock", buy: 12.34 }),
    e({ date: "2026-07-07", sell: 1234.56, buy: 800, cost: 12.5, buyDate: "2025-12-30" }),
  ];
  const r = T.computeEuer(sales, { year: 2026, vat: "small" });
  const jin = r.lines.filter((l) => l.type === "in").reduce((a, l) => a + l.gross, 0);
  const jout = r.lines.filter((l) => l.type === "out").reduce((a, l) => a + l.gross, 0);
  assert.equal(jin, r.revenueGross);
  assert.equal(jout, r.expensesTotal);
  assert.equal(r.revenueNet - r.expensesTotal, r.profit);
  assert.equal(r.byMonth.reduce((a, m) => a + m.revenue, 0), r.revenueGross);
  assert.equal(r.byMonth.reduce((a, m) => a + m.expenses, 0), r.expensesTotal);
  assert.equal(r.byPlatform.reduce((a, p) => a + p.revenue, 0), r.revenueGross);
  const rows = T.summaryRows(r);
  assert.equal(rows.find((x) => x[0] === "Gewinn / Verlust")[1], r.profit);
});

test("Cent-Rechnung: 0,1 + 0,2 ergibt exakt 0,30 (keine Gleitkomma-Drift)", () => {
  const r = T.computeEuer([e({ date: "2026-01-01", sell: 0.1 }), e({ date: "2026-01-02", sell: 0.2 })], { year: 2026, vat: "small" });
  assert.equal(r.revenueGross, 30);
});

test("Plattform: Meldegrenze wird je Plattform erkannt, bar/Sonstige nie", () => {
  const sales = [];
  for (let i = 0; i < 30; i++) sales.push(e({ date: "2026-03-01", sell: 5, platform: "Vinted" }));
  for (let i = 0; i < 40; i++) sales.push(e({ date: "2026-03-01", sell: 5, platform: "Flohmarkt / bar" }));
  sales.push(e({ date: "2026-03-01", sell: 2500, platform: "eBay" }));
  const r = T.computeEuer(sales, { year: 2026, vat: "small" });
  const by = Object.fromEntries(r.byPlatform.map((p) => [p.platform, p]));
  assert.equal(by["Vinted"].meldegrenze, true, "30 Verkäufe");
  assert.equal(by["eBay"].meldegrenze, true, "2.500 €");
  assert.equal(by["Flohmarkt / bar"].meldegrenze, false);
});

/* ---- Privat (§ 23 EStG) ---- */
test("Privat: Gebrauchsgegenstand ist nicht steuerbar, Rest wird nach Haltefrist eingeordnet", () => {
  const sales = [
    e({ date: "2026-05-01", sell: 50, buy: 10, kind: "everyday" }),
    e({ date: "2026-05-01", sell: 900, buy: 500, kind: "other", buyDate: "2026-01-15" }),
    e({ date: "2026-05-01", sell: 300, buy: 100, kind: "other", buyDate: "2024-01-15" }),
    e({ date: "2026-05-01", sell: 70, buy: 20 }),
    e({ date: "2026-05-01", sell: 70, buy: 20, kind: "other" }),
  ];
  const p = T.computePrivate(sales, { year: 2026 });
  const st = p.items.map((i) => i.status);
  assert.deepEqual(st, ["free", "relevant", "free", "check", "check"]);
  assert.equal(eur(p.totalProfit), 400);
  assert.equal(p.checkCount, 2);
});

test("Privat: Freigrenze 1.000 €: darunter steuerfrei, ab 1.000 € der gesamte Gewinn (Freigrenze, kein Freibetrag)", () => {
  const mk = (gain) => [e({ date: "2026-05-01", sell: gain + 100, buy: 100, kind: "other", buyDate: "2026-04-01" })];
  assert.equal(T.computePrivate(mk(999.99), { year: 2026 }).belowFreigrenze, true);
  assert.equal(T.computePrivate(mk(1000), { year: 2026 }).belowFreigrenze, false);
  assert.equal(T.freigrenzePrivat(2023), 600);
  assert.equal(T.freigrenzePrivat(2024), 1000);
});

test("Privat: Haltefrist endet am Jahrestag der Anschaffung (Schaltjahr-Grenzfall)", () => {
  assert.equal(T.addYears("2024-02-29", 1), "2025-02-28");
  const s = (d) => [e({ date: d, sell: 10, buy: 5, kind: "other", buyDate: "2025-06-10" })];
  assert.equal(T.computePrivate(s("2026-06-10"), { year: 2026 }).items[0].status, "relevant", "am Jahrestag noch innerhalb");
  assert.equal(T.computePrivate(s("2026-06-11"), { year: 2026 }).items[0].status, "free", "einen Tag später nicht mehr");
});

test("Privat: Verluste werden mit Gewinnen desselben Jahres verrechnet", () => {
  const sales = [
    e({ date: "2026-05-01", sell: 1500, buy: 100, kind: "other", buyDate: "2026-01-01" }),
    e({ date: "2026-05-02", sell: 100, buy: 700, kind: "other", buyDate: "2026-01-01" }),
  ];
  const p = T.computePrivate(sales, { year: 2026 });
  assert.equal(eur(p.totalProfit), 800);
  assert.equal(p.belowFreigrenze, true);
});

/* ---- CSV ---- */
test("CSV: Zahlen bleiben Zahlen (auch negativ), Text mit Formelzeichen wird entschärft, Anführungszeichen verdoppelt", () => {
  assert.equal(T.csvNum(-590), '"-5,90"');
  assert.equal(T.csvText("=SUM(A1)"), '"\'=SUM(A1)"');
  assert.equal(T.csvText('Er sagte "hi"'), '"Er sagte ""hi"""');
  assert.equal(T.csvText("+49 170"), '"\'+49 170"');
});

test("Journal-CSV: Kopfzeile, deutsches Datum, BOM, Wert je Zeile, Formel im Namen entschärft", () => {
  const r = T.computeEuer([e({ name: "=EVIL()", date: "2026-02-03", buy: 5, buyDate: "2026-02-01", sell: 20, cost: 2, receipt: "12-345" })], { year: 2026, vat: "small" });
  const csv = T.journalCsv(r);
  assert.ok(csv.startsWith("﻿\"Lfd. Nr.\";"));
  const lines = csv.trim().split("\r\n");
  assert.equal(lines.length, 1 + 3);
  assert.ok(lines[1].includes('"01.02.2026"') || lines[2].includes('"01.02.2026"'));
  assert.ok(csv.includes("\"'=EVIL()\""));
  assert.ok(!/;"=/.test(csv), "kein Feld darf mit = beginnen");
});

test("Summen-CSV: Positionen mit Bezeichnungen wie in der Anlage EÜR, keine erfundenen Zeilennummern", () => {
  const r = T.computeEuer([e({ date: "2026-02-03", sell: 20 })], { year: 2026, vat: "small" });
  const csv = T.summaryCsv(r);
  assert.ok(csv.includes("Kleinunternehmer"));
  assert.ok(csv.includes("Waren, Roh- und Hilfsstoffe"));
  assert.ok(!/Zeile \d/.test(csv));
});

/* ---- Härtung ---- */
test("sanitizeEntry: beschädigte oder fremde Werte werden abgewiesen oder begrenzt", () => {
  assert.equal(T.sanitizeEntry(null), null);
  assert.equal(T.sanitizeEntry({ date: "2026-13-40" }), null);
  const s = T.sanitizeEntry({ date: "2026-05-01", name: "x".repeat(500), buy: "abc", sell: -5, kind: "evil", buyDate: "kaputt", receipt: "  R1  " });
  assert.equal(s.name.length, 80);
  assert.equal(s.buy, 0);
  assert.equal(s.sell, 0);
  assert.equal(s.kind, undefined);
  assert.equal(s.buyDate, undefined);
  assert.equal(s.receipt, "R1");
});

test("sanitizeSettings: Standardwerte und Längenbegrenzung", () => {
  assert.deepEqual(T.sanitizeSettings(null), { mode: "business", vat: "small", rate: 19, name: "", taxId: "" });
  const s = T.sanitizeSettings({ mode: "private", vat: "regular", rate: 7, name: "N".repeat(200), taxId: 123 });
  assert.equal(s.name.length, 80);
  assert.equal(s.rate, 7);
  assert.equal(s.mode, "private");
  assert.equal(T.sanitizeSettings({ rate: 99 }).rate, 19);
});
