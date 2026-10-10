// Ausführen: node --test tests/
// Jeder Test nennt das Verhalten, das er schützt. Keine Tests ohne denkbare Regression.
const test = require("node:test");
const assert = require("node:assert/strict");
const P = require("../site/parse-lib.js");

const PLATFORMS = ["Vinted", "Kleinanzeigen", "eBay", "Etsy", "Amazon", "Flohmarkt / bar", "Sonstige"];

// Hilfsfunktion: Beispieltext komplett durch die Pipeline schicken.
function run(text, { platform = "", keyword = "", known, positiveOnly = true, dateOrder } = {}) {
  const d = P.detectDelimiter(text);
  const all = P.parseCSV(text, d);
  const h = P.findHeader(all);
  const headers = all[h].map((x) => x.trim());
  const rows = all.slice(h + 1).filter((r) => r.length >= 2);
  const own = P.isOwnFormat(headers);
  const map = own ? P.ownMapping(headers) : P.guessColumns(headers);
  const dateCol = map.date >= 0 ? rows.map((r) => r[map.date]) : [];
  const g = P.guessDateOrder(dateCol);
  const typeChecked = new Map();
  if (map.type >= 0) rows.forEach((r) => { const v = (r[map.type] || "").trim(); if (!typeChecked.has(v)) typeChecked.set(v, P.defaultTypeChecked(v)); });
  const res = P.buildEntries(rows, map, {
    dateOrder: dateOrder || g.order, platform, positiveOnly: own ? false : positiveOnly, keywords: keyword.split(/[|,]/),
    own, typeChecked, known: known || P.indexExisting([]), platforms: PLATFORMS,
  });
  return { ...res, map, headers, order: g };
}

/* ---- Zahlen: falsche Beträge sind der teuerste Fehler ---- */
test("parseNum: deutsche und englische Schreibweisen ergeben denselben Betrag", () => {
  const cases = [["12,50", 12.5], ["1.234,56", 1234.56], ["1,234.56", 1234.56], ["1,240.00", 1240], ["1240.00", 1240], ["1800,00", 1800], ["-177,51", -177.51], ["€ 12,50", 12.5], ["12.50 EUR", 12.5], ["(25,00)", -25], ["0.125", 0.125], ["5.500", 5500]];
  for (const [input, want] of cases) assert.equal(P.parseNum(input), want, input);
  for (const bad of ["", "abc", "–", null, undefined]) assert.ok(Number.isNaN(P.parseNum(bad)), String(bad));
});

/* ---- Datum: falsches Jahr/Monat verschiebt Meldegrenze ---- */
test("parseDate: ISO, deutsch, US, Monatsnamen, Zeitanhang und Unsinn", () => {
  assert.equal(P.parseDate("2026-09-12T10:22:31+00:00"), "2026-09-12");
  assert.equal(P.parseDate("03.09.2026 10:12", "dmy"), "2026-09-03");
  assert.equal(P.parseDate("09/21/2026", "mdy"), "2026-09-21");
  assert.equal(P.parseDate("5.3.26", "dmy"), "2026-03-05");
  assert.equal(P.parseDate("5. März 2026"), "2026-03-05");
  assert.equal(P.parseDate("Sep 5, 2026"), "2026-09-05");
  assert.equal(P.parseDate("31.02.2026", "dmy"), null, "ungültiger Kalendertag");
  assert.equal(P.parseDate("13/13/2026", "mdy"), null);
  assert.equal(P.parseDate("heute"), null);
});

test("guessDateOrder: erkennt US-Reihenfolge, meldet Mehrdeutigkeit statt still zu raten", () => {
  assert.deepEqual(P.guessDateOrder(["09/21/2026", "10/02/2026"]), { order: "mdy", ambiguous: false });
  assert.deepEqual(P.guessDateOrder(["21.09.2026", "02.10.2026"]), { order: "dmy", ambiguous: false });
  const amb = P.guessDateOrder(["09/05/2026", "10/02/2026"]);
  assert.equal(amb.ambiguous, true);
  assert.equal(amb.order, "mdy", "Schrägstrich-Daten sind meist US");
  assert.equal(P.guessDateOrder(["03.09.2026"]).order, "dmy", "Punkt-Daten sind deutsch");
});

/* ---- CSV-Zerlegung ---- */
test("parseCSV: Anführungszeichen, Zeilenumbruch im Feld, BOM-freier Text, CRLF", () => {
  const rows = P.parseCSV('a;b;c\r\n"x;y";"line1\nline2";"he said ""hi"""\r\n', ";");
  assert.deepEqual(rows[1], ["x;y", "line1\nline2", 'he said "hi"']);
  assert.equal(rows.length, 2);
});

test("detectDelimiter: Semikolon trotz Dezimalkomma, Tab und Komma", () => {
  assert.equal(P.detectDelimiter(P.SAMPLES.ebay.text), ";");
  assert.equal(P.detectDelimiter(P.SAMPLES.amazon.text), "\t");
  assert.equal(P.detectDelimiter(P.SAMPLES.etsy.text), ",");
  assert.equal(P.detectDelimiter("Datum;Betrag\n01.01.2026;12,50\n02.01.2026;7,00\n"), ";");
});

test("decode: UTF-8 mit BOM und Windows-1252 mit Umlauten", () => {
  assert.equal(P.decode(new TextEncoder().encode("﻿Gürtel")), "Gürtel");
  assert.equal(P.decode(Uint8Array.from([0x47, 0xfc, 0x72, 0x74, 0x65, 0x6c])), "Gürtel");
});

test("findHeader: überspringt Titelzeilen vor der Kopfzeile (eBay-Stil)", () => {
  const all = P.parseCSV(P.SAMPLES.ebay.text, ";");
  assert.equal(all[P.findHeader(all)][0], "Transaktionserstellungsdatum");
});

/* ---- Alle Beispielformate durch die komplette Pipeline ---- */
test("eBay-Stil: Erstattung und Auszahlung fallen raus, Gebühren werden Kosten", () => {
  const r = run(P.SAMPLES.ebay.text, { platform: "eBay" });
  assert.equal(r.entries.length, 2);
  assert.deepEqual(r.entries.map((e) => [e.name, e.sell, e.cost]), [["Retro Spielekonsole", 79, 8.53], ["Vintage Lederjacke", 120, 12.96]]);
  assert.equal(r.stats.filtered, 2);
  assert.ok(r.entries.every((e) => e.needsBuy), "ohne Einkaufsspalte muss der Einkauf nachgetragen werden");
});

test("Etsy-Stil: US-Datum und englische Beträge, Versand des Käufers wird NICHT als Kosten gezählt", () => {
  const r = run(P.SAMPLES.etsy.text, { platform: "Etsy" });
  assert.equal(r.order.order, "mdy");
  assert.deepEqual(r.entries.map((e) => [e.date, e.sell, e.cost]), [["2026-09-21", 24, 1.32], ["2026-09-25", 1240, 20], ["2026-10-02", 18.5, 1.14]]);
});

test("Amazon-Stil (Tab): ISO-Zeitstempel und Bestellnummer", () => {
  const r = run(P.SAMPLES.amazon.text, { platform: "Amazon" });
  assert.deepEqual(r.entries.map((e) => [e.date, e.name, e.sell]), [["2026-09-12", "Bambus Schneidebrett", 19.9], ["2026-09-19", "Kerzenhalter Set", 34]]);
});

test("PayPal-Stil: Rückzahlung gefiltert, Plattform wird aus dem Text erkannt", () => {
  const r = run(P.SAMPLES.paypal.text);
  assert.deepEqual(r.entries.map((e) => [e.platform, e.sell, e.cost]), [["Kleinanzeigen", 45, 1.66], ["Vinted", 30, 1.27]]);
});

test("Bank-Stil: nur Zeilen mit Stichwort, Gehalt und Einkauf bleiben draußen", () => {
  const r = run(P.SAMPLES.bank.text, { keyword: "Vinted|Kleinanzeigen" });
  assert.deepEqual(r.entries.map((e) => [e.platform, e.sell]), [["Vinted", 34.5], ["Kleinanzeigen", 120]]);
  const none = run(P.SAMPLES.bank.text, { keyword: "" });
  assert.equal(none.entries.length, 3, "ohne Stichwort kommen alle positiven Beträge mit (auch das Gehalt): deshalb das Stichwortfeld");
  assert.equal(none.entries.filter((e) => e.sell < 0).length, 0, "Abbuchungen nie");
});

/* ---- Duplikate ---- */
test("Duplikate: erneuter Import derselben Datei fügt nichts hinzu", () => {
  const first = run(P.SAMPLES.ebay.text, { platform: "eBay" });
  const stored = first.entries.map((e) => ({ ...e }));
  const again = run(P.SAMPLES.ebay.text, { platform: "eBay", known: P.indexExisting(stored) });
  assert.equal(again.entries.length, 0);
  assert.equal(again.stats.dup, 2);
});

test("Duplikate: zwei identische Verkäufe OHNE Bestellnummer gehen nicht verloren", () => {
  const csv = "Datum;Artikel;Betrag\n01.09.2026;T-Shirt;5,00\n01.09.2026;T-Shirt;5,00\n";
  const r = run(csv, { platform: "Vinted" });
  assert.equal(r.entries.length, 2);
  const stored = r.entries.map((e) => ({ ...e }));
  const again = run(csv, { platform: "Vinted", known: P.indexExisting(stored) });
  assert.equal(again.entries.length, 0, "Wiederholung der Datei darf nicht erneut zählen");
  const three = run(csv + "01.09.2026;T-Shirt;5,00\n", { platform: "Vinted", known: P.indexExisting(stored) });
  assert.equal(three.entries.length, 1, "nur das echte dritte Exemplar kommt dazu");
});

test("Duplikate: zwei eBay-Bestellungen mit gleichem Artikel und Preis, aber verschiedener Bestellnummer, bleiben beide", () => {
  const csv = 'Datum;Bestellnummer;Artikel;Brutto\n01.09.2026;A1;Kappe;10,00\n01.09.2026;A2;Kappe;10,00\n';
  const first = run(csv, { platform: "eBay" });
  assert.equal(first.entries.length, 2);
  const oneStored = [{ ...first.entries[0] }];
  const second = run(csv, { platform: "eBay", known: P.indexExisting(oneStored) });
  assert.equal(second.entries.length, 1, "nur die noch fehlende Bestellung wird ergänzt");
});

test("Round-Trip: eigener Export lässt sich wieder einlesen, Bestand bleibt Bestand, schon Vorhandenes wird erkannt", () => {
  const csv = '"Datum";"Artikel";"Plattform";"Status";"Einkauf";"Verkauf";"Kosten";"Gewinn"\n"2026-09-03";"Konsole";"eBay";"Verkauft";"30,00";"79,00";"8,53";"40,47"\n"2026-11-01";"Jacke";"Vinted";"Bestand";"15,00";"";"0,00";""\n';
  const r = run(csv);
  assert.equal(r.entries.length, 2);
  const stock = r.entries.find((e) => e.name === "Jacke");
  assert.equal(stock.status, "stock");
  assert.equal(stock.buy, 15);
  assert.equal(r.entries.find((e) => e.name === "Konsole").needsBuy, false);
  const again = run(csv, { known: P.indexExisting(r.entries.map((e) => ({ ...e }))) });
  assert.equal(again.entries.length, 0);
});

/* ---- Spalten-Erkennung ---- */
test("guessColumns: Summenspalte statt Einzelgebühren (keine Doppelzählung)", () => {
  const m = P.guessColumns(["Datum", "Artikel", "Brutto", "Gebühr fest", "Gebühr variabel", "Gebühren gesamt"]);
  assert.deepEqual(m.fees, [5]);
});

test("guessColumns: Versand wird nie automatisch als eigene Kosten zugeordnet", () => {
  const m = P.guessColumns(["Datum", "Artikel", "Brutto", "Versandkosten"]);
  assert.equal(m.ship, -1);
});

test("detectCurrencies: Fremdwährung wird gemeldet, EUR nicht", () => {
  assert.deepEqual(P.detectCurrencies(["Date", "Currency"], [["x", "EUR"], ["y", "USD"]]), ["USD"]);
  assert.deepEqual(P.detectCurrencies(["Datum", "Währung"], [["x", "EUR"]]), []);
  assert.deepEqual(P.detectCurrencies(["Datum", "Betrag"], [["x", "5"]]), []);
});

/* ---- Eingabe-Härte ---- */
test("Namen: Formel-Zeichen bleiben als Text, Länge begrenzt, Apostroph-Schutz aus eigenem Export wird entfernt", () => {
  const csv = `Datum;Artikel;Betrag\n01.09.2026;'=SUM(A1);5,00\n02.09.2026;${"x".repeat(500)};6,00\n`;
  const r = run(csv, { platform: "Vinted" });
  assert.equal(r.entries[0].name, "=SUM(A1)");
  assert.equal(r.entries[1].name.length, P.MAX_NAME);
});

test("Ungültige Zeilen: ohne Datum oder ohne Betrag werden gezählt, nicht still geschluckt", () => {
  const csv = "Datum;Artikel;Betrag\nkaputt;A;5,00\n01.09.2026;B;\n01.09.2026;C;-4,00\n";
  const r = run(csv, { platform: "Vinted" });
  assert.equal(r.entries.length, 0);
  assert.equal(r.stats.noDate, 1);
  assert.equal(r.stats.noAmount, 2);
});

/* ---- Eigener Export mit Steuer-Spalten ---- */
test("Round-Trip: Einkaufsdatum, Belegnummer und Gegenstandsart überleben Export und Import", () => {
  const csv = '"Datum";"Artikel";"Plattform";"Status";"Einkauf";"Verkauf";"Kosten";"Gewinn";"Einkaufsdatum";"Belegnr";"Art"\n"2026-05-10";"Konsole";"eBay";"Verkauft";"60,00";"125,00";"8,00";"57,00";"2026-03-15";"12-345";"Sonstiges"\n"2026-03-04";"Jacke";"Vinted";"Verkauft";"10,00";"35,00";"3,90";"21,10";"";"";"Gebrauchsgegenstand"\n';
  const r = run(csv);
  assert.equal(r.entries.length, 2);
  const k = r.entries.find((x) => x.name === "Konsole");
  assert.equal(k.buyDate, "2026-03-15");
  assert.equal(k.receipt, "12-345");
  assert.equal(k.kind, "other");
  const j = r.entries.find((x) => x.name === "Jacke");
  assert.equal(j.kind, "everyday");
  assert.equal(j.buyDate, undefined);
});

test("Import mit Bestellnummer übernimmt sie als Belegnummer", () => {
  const r = run(P.SAMPLES.ebay.text, { platform: "eBay" });
  assert.equal(r.entries[0].receipt, "12-34567-89012");
});
