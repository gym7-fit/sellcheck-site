// Ausführen: node --test tests/wizard.test.js
// Schützt die Freischalt-Regeln des geführten Ablaufs: Was ist erledigt, was gesperrt, wohin geht es als Nächstes?
const test = require("node:test");
const assert = require("node:assert/strict");
const W = require("../site/wizard-lib.js");

const PLATFORMS = ["Vinted", "Kleinanzeigen", "eBay", "Etsy", "Amazon", "Flohmarkt / bar", "Sonstige"];
const e = (o) => ({ id: Math.random().toString(36).slice(2), name: "Artikel", platform: "Vinted", buy: 5, sell: 20, cost: 0, status: "sold", date: "2026-05-01", ...o });
const st = (o = {}) => W.sanitizeState({ year: 2026, mode: "business", vat: "small", platforms: ["Vinted"], ack: { 2: true }, ...o }, PLATFORMS);

test("Leerer Zustand: Schritt 1 ist aktiv, alles andere gesperrt", () => {
  const p = W.progress(W.sanitizeState({}, PLATFORMS), []);
  assert.equal(p.active, 1);
  assert.equal(p.canReview, false);
  assert.equal(W.isUnlocked(p, 1), true);
  assert.equal(W.isUnlocked(p, 2), false);
});

test("Schritt 1: gewerblich braucht die Umsatzsteuer-Wahl, privat nicht", () => {
  const noVat = W.progress(W.sanitizeState({ year: 2026, mode: "business" }, PLATFORMS), []);
  assert.equal(noVat.done[1], false);
  const withVat = W.progress(W.sanitizeState({ year: 2026, mode: "business", vat: "regular" }, PLATFORMS), []);
  assert.equal(withVat.done[1], true);
  const priv = W.progress(W.sanitizeState({ year: 2026, mode: "private" }, PLATFORMS), []);
  assert.equal(priv.done[1], true);
});

test("Schritt 2: Plattform gewählt UND bestätigt; ohne Plattform nicht erledigt, auch wenn bestätigt", () => {
  assert.equal(W.progress(st({ ack: {} }), []).done[2], false, "nicht bestätigt");
  assert.equal(W.progress(st({ platforms: [], ack: { 2: true } }), []).done[2], false, "keine Plattform");
  assert.equal(W.progress(st(), []).done[2], true);
});

test("Schritt 3: braucht mindestens einen Eintrag im gewählten Jahr, Einträge anderer Jahre zählen nicht", () => {
  const p = W.progress(st(), [e({ date: "2025-12-31" })]);
  assert.equal(p.done[3], false);
  assert.equal(p.active, 3);
  assert.deepEqual(p.otherYears, { 2025: 1 });
  const q = W.progress(st(), [e({ date: "2026-01-01" })]);
  assert.equal(q.done[3], true);
  assert.equal(q.count, 1);
});

test("Schritt 4: importierte Verkäufe ohne Einkaufspreis halten den Ablauf an, Bestätigung schaltet frei", () => {
  const sales = [e({ needsBuy: true, buy: 0 })];
  const p = W.progress(st(), sales);
  assert.equal(p.done[3], true);
  assert.equal(p.done[4], false);
  assert.equal(p.active, 4);
  assert.equal(p.incomplete.length, 1);
  assert.deepEqual(p.incomplete[0].missing, ["buy"]);
  const ok = W.progress(st({ ack: { 2: true, 4: "2026" } }), sales);
  assert.equal(ok.done[4], true);
  assert.equal(ok.active, 5);
});

test("Schritt 4: Bestätigung gilt nur für das Jahr, für das sie gegeben wurde", () => {
  const sales = [e({ needsBuy: true, buy: 0, date: "2027-02-01" })];
  const p = W.progress(st({ year: 2027, ack: { 2: true, 4: "2026" } }), sales);
  assert.equal(p.done[4], false);
});

test("Schritt 4: im Privat-Modus fehlt die Gegenstandsart, im Gewerbe-Modus nicht", () => {
  const sales = [e({ buy: 5 })];
  assert.equal(W.progress(st({ mode: "private" }), sales).incomplete.length, 1);
  assert.deepEqual(W.progress(st({ mode: "private" }), sales).incomplete[0].missing, ["kind"]);
  assert.equal(W.progress(st({ mode: "business" }), sales).incomplete.length, 0);
  assert.equal(W.progress(st({ mode: "private" }), [e({ kind: "everyday" })]).incomplete.length, 0);
});

test("Schritt 4: Bestand braucht weder Einkaufsdatum noch Art", () => {
  const sales = [e({ status: "stock", sell: 0, needsBuy: true, buy: 0 })];
  assert.equal(W.progress(st({ mode: "private" }), sales).incomplete.length, 0);
});

test("Schritte 5 und 6 brauchen eine ausdrückliche Bestätigung; erst dann ist die Überprüfung frei", () => {
  const sales = [e()];
  const base = { ack: { 2: true, 4: "2026" } };
  assert.equal(W.progress(st(base), sales).canReview, false);
  assert.equal(W.progress(st({ ack: { ...base.ack, 5: true } }), sales).canReview, false);
  const all = W.progress(st({ ack: { ...base.ack, 5: true, 6: true } }), sales);
  assert.equal(all.canReview, true);
  assert.equal(all.active, 7);
});

test("Kumulativ: Wird ein früherer Schritt ungültig, sperren sich alle späteren wieder", () => {
  const sales = [e()];
  const full = st({ ack: { 2: true, 4: "2026", 5: true, 6: true } });
  assert.equal(W.progress(full, sales).canReview, true);
  const broken = W.progress(full, []); // alle Einträge gelöscht
  assert.equal(broken.done[3], false);
  assert.equal(broken.done[5], false, "5 war bestätigt, ist aber ohne Daten nicht mehr gültig");
  assert.equal(broken.active, 3);
  assert.equal(broken.canReview, false);
});

test("Zustand aus dem Speicher wird bereinigt: unbekannte Plattformen, Fantasiewerte, falsche Typen", () => {
  const s = W.sanitizeState({ year: "abc", mode: "boss", vat: 5, rate: 99, platforms: ["Vinted", "Evil", "Vinted", 7], name: "x".repeat(300), ack: { 2: "ja", 6: true } }, PLATFORMS);
  assert.equal(s.year, null);
  assert.equal(s.mode, null);
  assert.equal(s.vat, null);
  assert.equal(s.rate, 19);
  assert.deepEqual(s.platforms, ["Vinted"]);
  assert.equal(s.name.length, 80);
  assert.equal(s.ack[2], false, "nur echtes true zählt");
  assert.equal(s.ack[6], true);
  assert.deepEqual(W.sanitizeState(null, PLATFORMS).platforms, []);
});

test("Schritt-Liste: sechs Schritte in fester Reihenfolge", () => {
  assert.deepEqual(W.STEPS.map((x) => x.n), [1, 2, 3, 4, 5, 6]);
});
