// Prüft die Datenschicht von „Mein SellCheck“ (site/konto-lib.js): Umwandlung Konto <-> Web-Tools, Übernahme ohne Doppelte,
// Übersicht wie in der App, Meldegrenze aus SCTax.meldeStatus, Foto-Pfade wie in der App.
const test = require("node:test");
const assert = require("node:assert/strict");
const K = require("../site/konto-lib.js");

const ID = "0b8f3c1e-1111-4a2b-9c3d-123456789abc";
let n = 0;
const opt = { now: new Date("2026-10-29T12:00:00Z"), newId: () => `00000000-0000-4000-8000-${String(++n).padStart(12, "0")}` };
const row = (o) => ({ id: ID, name: "Jacke", platform: "Vinted", buy_cents: 1200, sell_cents: 3000, cost_cents: 250, is_sold: true, sale_date: "2026-05-01", buy_date: null, deleted_at: null, ...o });

test("Zeile aus dem Konto wird ein Eintrag der Web-Tools und zurück, ohne Verlust", () => {
  const e = K.rowToEntry(row({ receipt_no: "B-17", ref: "ORD-9", buy_date: "2026-04-02" }));
  assert.deepEqual([e.buy, e.sell, e.cost, e.status, e.date, e.buyDate, e.receipt, e.ref], [12, 30, 2.5, "sold", "2026-05-01", "2026-04-02", "B-17", "ORD-9"]);
  const back = K.entryToRow(e, opt);
  assert.equal(back.id, ID);
  assert.deepEqual([back.buy_cents, back.sell_cents, back.cost_cents, back.sale_date, back.buy_date, back.receipt_no, back.ref], [1200, 3000, 250, "2026-05-01", "2026-04-02", "B-17", "ORD-9"]);
  assert.equal(back.changed_at, "2026-10-29T12:00:00.000Z");
  assert.equal(back.deleted_at, null, "Schreiben holt einen gelöschten Artikel zurück");
});

test("Bestand: kein Verkaufsdatum, Einkaufsdatum aus dem Tag des Eintrags", () => {
  const r = K.entryToRow({ name: "Kamera", platform: "Kleinanzeigen", buy: 55, sell: 99, status: "stock", date: "2026-03-03" }, opt);
  assert.deepEqual([r.is_sold, r.sell_cents, r.sale_date, r.buy_date], [false, 0, null, "2026-03-03"]);
  assert.match(r.id, K.UUID, "Einträge ohne gültige Kennung bekommen eine neue");
  assert.equal(K.rowToEntry(r).date, "2026-03-03");
});

test("Grenzen der Datenbank werden eingehalten (Name, Plattform, Notiz, keine negativen Beträge)", () => {
  const r = K.entryToRow({ name: " ".repeat(3), platform: "x".repeat(60), notes: "n".repeat(1200), buy: -5, sell: 1, date: "2026-01-01" }, opt);
  assert.equal(r.name, "Ohne Namen");
  assert.equal(r.platform.length, 40);
  assert.equal(r.notes.length, 1000);
  assert.equal(r.buy_cents, 0);
});

test("Übernahme aus den Gratis-Tools legt nichts doppelt an, zwei gleiche Verkäufe bleiben zwei", () => {
  const existing = [row({ name: "Jacke", sell_cents: 3000, buy_cents: 1200, cost_cents: 250 })];
  const tools = [
    { id: "t1", name: "Jacke", platform: "Vinted", buy: 12, sell: 30, cost: 2.5, status: "sold", date: "2026-05-01" },
    { id: "t2", name: "jacke ", platform: "Vinted", buy: 12, sell: 30, cost: 2.5, status: "sold", date: "2026-05-01" },
    { id: "t3", name: "Schal", platform: "eBay", sell: 8, status: "sold", date: "2026-06-01" },
    { kaputt: true },
  ];
  const p = K.planTakeover(tools, existing, opt);
  assert.equal(p.present, 1, "eine Jacke gibt es schon");
  assert.deepEqual(p.rows.map((r) => r.name), ["jacke", "Schal"].map((x) => (x === "jacke" ? "jacke" : x)));
  assert.ok(p.rows.every((r) => K.UUID.test(r.id)));
  assert.equal(K.planTakeover(tools, [...existing, ...p.rows], opt).rows.length, 0, "zweites Übernehmen legt nichts an");
});

test("Änderungen aus dem Konto: das Konto gewinnt, gelöschte verschwinden, Merker mit Überlappung", () => {
  const a = row({ id: "a", name: "Alt" }), b = row({ id: "b" });
  const m = K.mergeChanges(new Map([["a", a], ["b", b]]), [row({ id: "a", name: "Neu" }), row({ id: "b", deleted_at: "2026-10-29T10:00:00Z" })]);
  assert.deepEqual([...m.keys()], ["a"]);
  assert.equal(m.get("a").name, "Neu");
  assert.equal(K.nextCursor("2026-10-29T10:00:00Z", [{ updated_at: "2026-10-29T11:00:00Z" }, { updated_at: "2026-10-29T09:00:00Z" }]), "2026-10-29T11:00:00Z");
  assert.equal(K.since("2026-10-29T11:00:00.000Z"), "2026-10-29T10:58:00.000Z");
  assert.equal(K.since(null), null);
});

test("Übersicht wie in der App: Gewinn je Artikel, Bestand, Umsatzsteuer nur bei Regel- oder Differenzbesteuerung", () => {
  const rows = [row({ id: "1" }), row({ id: "2", sell_cents: 5000, buy_cents: 2000, cost_cents: 0, sale_date: "2025-12-31" }), row({ id: "3", is_sold: false, sell_cents: 0, buy_cents: 700 }), row({ id: "4", deleted_at: "2026-01-01T00:00:00Z" })];
  const s = K.yearStats(rows, 2026, { seller_mode: "business", vat_mode: "small" });
  assert.deepEqual([s.sold, s.revenue, s.profit, s.vat, s.stock, s.stockValue], [1, 3000, 1550, 0, 1, 700]);
  const r = K.yearStats(rows, 2026, { seller_mode: "business", vat_mode: "regular", vat_rate: 19 });
  assert.equal(r.vat, 3000 - Math.round(3000 / 1.19), "gleiche Rundung wie tax-lib.js");
  const m = K.yearStats([row({ sell_cents: 3000, buy_cents: 1000 })], 2026, { seller_mode: "business", vat_mode: "margin" });
  assert.equal(m.vat, 2000 - Math.round(2000 / 1.19), "Differenzbesteuerung: Steuer nur auf die Differenz");
  assert.equal(K.yearStats([row({ buy_cents: 4000 })], 2026, { seller_mode: "business", vat_mode: "margin" }).vat, 0, "kein Gewinn, keine Steuer");
  assert.equal(K.yearStats(rows, 2026, { seller_mode: "private", vat_mode: "regular" }).vat, 0, "privat: nie Umsatzsteuer");
});

test("Meldegrenze je Plattform kommt aus SCTax.meldeStatus: 2.000,00 € ist Rot, 1.999,99 € Gelb", () => {
  const at = (sum) => K.yearStats([row({ sell_cents: sum })], 2026, {}).platforms.find((p) => p.platform === "Vinted");
  assert.equal(at(200000).level, "red");
  assert.equal(at(199999).level, "yellow");
  const s = K.yearStats([row({ platform: "Flohmarkt / bar", sell_cents: 500000 })], 2026, {});
  assert.equal(s.platforms.find((p) => p.platform === "Flohmarkt / bar").level, "none", "nicht meldende Plattform ohne Ampel");
  assert.ok(s.platforms.some((p) => p.platform === "Etsy" && p.count === 0), "meldende Plattformen erscheinen auch ohne Verkäufe");
});

test("Foto-Pfade und Prüfsumme wie in der App (FNV-1a, 8 Hexstellen, kleingeschrieben)", () => {
  assert.equal(K.checksum(new TextEncoder().encode("a")), "e40c292c");
  assert.equal(K.storagePath("ABC", "DEF", "foto", "00ff00ff"), "abc/def-foto-00ff00ff.jpg");
});
