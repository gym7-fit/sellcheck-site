// Prüft die Seite „Mein SellCheck“ (Auftrag 03): Anzeigelogik aus site/konto-lib.js (Zahlen, Ampel, Suche, Formular) und die Regeln für site/mein.js.
// Ausführen: node --test tests/mein.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const K = require("../site/konto-lib.js");
const P = require("../site/parse-lib.js");

const SITE = path.join(__dirname, "..", "site");
const read = (f) => fs.readFileSync(path.join(SITE, f), "utf8");
const ID = (n) => "00000000-0000-4000-8000-" + String(n).padStart(12, "0");
const row = (n, o = {}) => ({ id: ID(n), name: "Artikel " + n, platform: "Vinted", buy_cents: 0, sell_cents: 0, cost_cents: 0, is_sold: true, sale_date: "2026-05-01", buy_date: null, created_at: "2026-01-01T10:00:00Z", deleted_at: null, ...o });
const NOW = new Date("2026-10-30T12:00:00Z");
const opt = { now: NOW, newId: () => ID(99) };

/* ---------- Zahlen wie in der App ---------- */

test("Zahlen: dasselbe Beispiel für alle Steuerarten (Verkauf 119,00, Einkauf 50,00, Kosten 5,00)", () => {
  const r = row(1, { sell_cents: 11900, buy_cents: 5000, cost_cents: 500 });
  const cases = [
    [{ seller_mode: "private" }, 0, 6400],
    [{ seller_mode: "business", vat_mode: "small" }, 0, 6400],
    [{ seller_mode: "business", vat_mode: "regular", vat_rate: 19 }, 1900, 4500],
    [{ seller_mode: "business", vat_mode: "regular", vat_rate: 7 }, 779, 5621],
    [{ seller_mode: "business", vat_mode: "margin" }, 1102, 5298],
  ];
  for (const [profile, vat, profit] of cases) {
    const s = K.yearStats([r], 2026, profile);
    assert.deepEqual([s.revenue, s.vat, s.profit, s.sold], [11900, vat, profit, 1], JSON.stringify(profile));
    assert.equal(K.rowProfit(r, profile), profit, "Gewinn je Artikel gleich Jahresgewinn");
  }
});

test("Übersicht: nur das gewählte Jahr, gelöschte und Bestand zählen nicht als Verkauf", () => {
  const rows = [
    row(1, { sell_cents: 3000, buy_cents: 1000 }),
    row(2, { sell_cents: 5000, buy_cents: 2000, sale_date: "2025-12-31" }),
    row(3, { sell_cents: 7000, deleted_at: "2026-06-01T00:00:00Z" }),
    row(4, { is_sold: false, sell_cents: 0, buy_cents: 4000, sale_date: null, buy_date: "2026-08-01" }),
  ];
  const s = K.yearStats(rows, 2026, { seller_mode: "private" });
  assert.deepEqual([s.revenue, s.profit, s.sold, s.stock, s.stockValue], [3000, 2000, 1, 1, 4000]);
  assert.deepEqual(K.yearsOf(rows, 2026), [2026, 2025]);
  assert.deepEqual(K.yearsOf([], 2026), [2026]);
});

test("Bestand: Lagerdauer, Ladenhüter ab 60 Tagen, Texte wie in der App", () => {
  const now = Date.UTC(2026, 9, 30, 12);
  const a = row(1, { is_sold: false, buy_cents: 1000, buy_date: "2026-10-30" });
  const b = row(2, { is_sold: false, buy_cents: 2500, buy_date: "2026-08-31" });   // genau 60 Tage
  const c = row(3, { is_sold: false, buy_cents: 500, buy_date: null, created_at: "2026-10-29T08:00:00Z" });   // ohne Einkaufsdatum: ab dem Anlegen
  assert.deepEqual([K.stockDays(a, now), K.stockDays(b, now), K.stockDays(c, now)], [0, 60, 1]);
  assert.deepEqual(K.stockStats([a, b, c, row(4)], now), { count: 3, valueCents: 4000, stale: 1 });
  assert.deepEqual([0, 1, 59, 60, 75, 365].map(K.ageText), ["heute gekauft", "seit 1 Tag", "seit 59 Tagen", "seit 2 Monaten", "seit 2 Monaten", "seit 12 Monaten"]);
  assert.equal(K.euro(150000), "1.500,00\u00a0€", "fester Leerraum vor dem Euro-Zeichen, wie Money.format der App");
  assert.equal(K.sales(1), "1 Verkauf"); assert.equal(K.sales(2), "2 Verkäufe");
});

/* ---------- Ampelgrenzen ---------- */

test("Meldegrenze: 1.999,99 € Gelb, 2.000,00 € Rot, 29 Verkäufe Gelb, 30 Rot, Flohmarkt ohne Ampel", () => {
  const p = { seller_mode: "private" };
  const level = (rows, name = "Vinted") => K.yearStats(rows, 2026, p).platforms.find((x) => x.platform === name).level;
  assert.equal(level([row(1, { sell_cents: 199999 })]), "yellow");
  assert.equal(level([row(1, { sell_cents: 200000 })]), "red");
  assert.equal(level([row(1, { sell_cents: 100000 }), row(2, { sell_cents: 100000 })]), "red", "Summe zählt");
  assert.equal(level([row(1, { sell_cents: 120000 })]), "yellow", "ab 60 % Gelb (1.200,00 €)");
  assert.equal(level([row(1, { sell_cents: 119999 })]), "green", "knapp darunter Grün");
  assert.equal(level([row(1, { sell_cents: 100 })]), "green");
  const many = (n) => Array.from({ length: n }, (_, i) => row(i + 1, { sell_cents: 100 }));
  assert.equal(level(many(29)), "yellow");
  assert.equal(level(many(30)), "red");
  assert.equal(level([row(1, { sell_cents: 900000, platform: "Flohmarkt" })], "Flohmarkt"), "none", "keine Ampel ohne Meldepflicht");
  const flohmarkt = K.yearStats([row(1, { sell_cents: 900000, platform: "Flohmarkt" })], 2026, p).platforms.find((x) => x.platform === "Flohmarkt");
  assert.equal(flohmarkt.reported, false);
  assert.match(K.unreportedText(flohmarkt), /^1 Verkauf, 9\.000,00\u00a0€\. Diese Plattform meldet nicht automatisch/);
});

test("Balken: ganze Prozent ohne Rundungsfehler, höchstens 100", () => {
  assert.deepEqual([K.ratioPct(18, 30), K.ratioPct(29, 30), K.ratioPct(30, 30), K.ratioPct(45, 30), K.ratioPct(0, 30)], [60, 96, 100, 100, 0]);
  assert.deepEqual([K.ratioPct(199999, 200000), K.ratioPct(200000, 200000), K.ratioPct(120000, 200000)], [99, 100, 60]);
});

/* ---------- Suche, Filter, Sortierung ---------- */

test("Liste: Suche nach Name und Plattform, Filter, neueste zuerst, im Bestand der Älteste oben", () => {
  const now = Date.UTC(2026, 9, 30);
  const rows = [
    row(1, { name: "Daunenjacke", platform: "Vinted", sale_date: "2026-03-01" }),
    row(2, { name: "Kamera", platform: "eBay", sale_date: "2026-09-10" }),
    row(3, { name: "Lego Technic", platform: "Kleinanzeigen", is_sold: false, sale_date: null, buy_date: "2026-10-01" }),
    row(4, { name: "Mantel", platform: "Vinted", is_sold: false, sale_date: null, buy_date: "2026-06-01" }),
    row(5, { name: "Gelöscht", deleted_at: "2026-10-01T00:00:00Z" }),
  ];
  const names = (o) => K.filterRows(rows, o, now).map((r) => r.name);
  assert.deepEqual(names({ filter: "all" }), ["Lego Technic", "Kamera", "Mantel", "Daunenjacke"], "nach Verkaufs-, sonst Einkaufsdatum, neueste zuerst");
  assert.deepEqual(names({ filter: "sold" }), ["Kamera", "Daunenjacke"]);
  assert.deepEqual(names({ filter: "stock" }), ["Mantel", "Lego Technic"], "Bestand: der Älteste oben");
  assert.deepEqual(names({ filter: "all", query: "VINTED" }), ["Mantel", "Daunenjacke"], "Plattform, ohne Groß-/Kleinschreibung");
  assert.deepEqual(names({ filter: "all", query: " lego " }), ["Lego Technic"], "Name, Leerzeichen am Rand egal");
  assert.deepEqual(names({ filter: "sold", query: "mantel" }), []);
  assert.deepEqual(names({}), ["Lego Technic", "Kamera", "Mantel", "Daunenjacke"], "ohne Angaben: alle");
  assert.ok(!names({ filter: "all", query: "gelöscht" }).length, "Gelöschte tauchen nicht auf");
});

/* ---------- Anker ---------- */

test("Reiter: nur vier erlaubte Anker, alles andere öffnet die Übersicht", () => {
  assert.deepEqual(K.TABS, ["uebersicht", "artikel", "meldegrenze", "konto"]);
  for (const t of K.TABS) { assert.equal(K.tabFromHash("#" + t), t); assert.equal(K.tabFromHash(t), t); }
  for (const bad of ["", "#", "#Artikel", "#artikel ", "#admin", "#javascript:alert(1)", "#../konto", "#konto#x", null, undefined, 5, "#__proto__", "#constructor"]) assert.equal(K.tabFromHash(bad), "uebersicht", String(bad));
});

/* ---------- Formular und Speichern ---------- */

const form = (o = {}) => ({ sold: true, name: "Jacke", platform: "Vinted", buy: "10", sell: "25,50", cost: "2", saleDate: "2026-10-20", hasBuyDate: false, buyDate: "", notes: "", ...o });

test("Formular: Beträge in deutscher Schreibweise werden zu Cent, „1.500“ ist 1500", () => {
  const r = K.formToRow(form({ buy: "1.500", sell: "2.499,90", cost: "12,5" }), null, opt, P.parseNum);
  assert.equal(r.ok, true);
  assert.deepEqual([r.row.buy_cents, r.row.sell_cents, r.row.cost_cents], [150000, 249990, 1250]);
  assert.deepEqual([r.row.is_sold, r.row.sale_date, r.row.buy_date, r.row.platform, r.row.name], [true, "2026-10-20", null, "Vinted", "Jacke"]);
  assert.equal(r.row.id, ID(99), "neue Kennung für neue Artikel");
  assert.equal(r.row.changed_at, "2026-10-30T12:00:00.000Z");
  assert.equal(r.row.deleted_at, null);
  assert.equal(r.row.photo_path, null); assert.equal(r.row.receipt_path, null);
});

test("Formular: Bestand hat keinen Verkaufspreis und kein Verkaufsdatum, das Einkaufsdatum ist freiwillig", () => {
  const r = K.formToRow(form({ sold: false, sell: "99", hasBuyDate: true, buyDate: "2026-09-01" }), null, opt, P.parseNum);
  assert.deepEqual([r.row.is_sold, r.row.sell_cents, r.row.sale_date, r.row.buy_date], [false, 0, null, "2026-09-01"]);
  const no = K.formToRow(form({ sold: false, hasBuyDate: false, buyDate: "2026-09-01" }), null, opt, P.parseNum);
  assert.equal(no.row.buy_date, null, "Haken aus: kein Datum");
});

test("Formular: Fehler direkt am Feld, mit den Texten der App", () => {
  const e = (f) => K.formToRow(form(f), null, opt, P.parseNum).errors;
  assert.equal(e({ name: "   " }).name, "Gib dem Artikel einen Namen.");
  assert.equal(e({ buy: "abc" }).buy, "Das ist keine gültige Zahl. Beispiel: 12,50");
  assert.equal(e({ cost: "-3" }).cost, "Das ist keine gültige Zahl. Beispiel: 12,50", "keine negativen Beträge");
  assert.equal(e({ sell: "" }).sell, "Wie viel hast du für den Verkauf bekommen?");
  assert.equal(e({ sell: "0" }).sell, "Wie viel hast du für den Verkauf bekommen?");
  assert.equal(e({ sell: "x" }).sell, "Das ist keine gültige Zahl. Beispiel: 12,50");
  assert.deepEqual(Object.keys(e({ name: "", buy: "?", cost: "?", sell: "" })).sort(), ["buy", "cost", "name", "sell"], "alle Fehler auf einmal");
  assert.equal(K.formToRow(form({ sold: false, sell: "" }), null, opt, P.parseNum).ok, true, "im Bestand ist kein Verkaufspreis nötig");
});

test("Formular: lange Namen werden auf 120 Zeichen gekürzt, Ändern behält Kennung und Fotos", () => {
  const long = "Ä".repeat(150);
  assert.equal(K.formToRow(form({ name: long }), null, opt, P.parseNum).row.name.length, 120);
  const old = row(7, { photo_path: "u/a-foto-1.jpg", receipt_path: "u/a-beleg-2.jpg", receipt_no: "B-1", ref: "R-2", kind: "sale" });
  const r = K.formToRow(form({ name: "Neu" }), old, opt, P.parseNum).row;
  assert.deepEqual([r.id, r.photo_path, r.receipt_path, r.receipt_no, r.ref, r.kind], [ID(7), "u/a-foto-1.jpg", "u/a-beleg-2.jpg", "B-1", "R-2", "sale"]);
});

test("Fotos: längste Kante höchstens 1400 px, nie vergrößern, Seitenverhältnis bleibt", () => {
  assert.deepEqual(K.fitSize(4000, 3000, 1400), { width: 1400, height: 1050 });
  assert.deepEqual(K.fitSize(3000, 4000, 1400), { width: 1050, height: 1400 });
  assert.deepEqual(K.fitSize(800, 600, 1400), { width: 800, height: 600 });
  assert.deepEqual(K.fitSize(20000, 10, 1400), { width: 1400, height: 1 }, "nie 0 Pixel");
});

/* ---------- Sicherheit und Aufbau von mein.js und mein.html ---------- */

test("mein.js: kein innerHTML, keine unsichere Ausgabe, keine Stile per Skript, Ziele nur fest", () => {
  const js = read("mein.js"), code = js.replace(/^\s*\/\/.*$/gm, "");
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|new Function|setAttribute\(\s*["']on|\.style\b|cssText/.test(code), "unsichere Ausgabe oder Stil per Skript");
  assert.ok(!/location\.(search|href\s*=\s*[^"]|assign|replace)/.test(js.replace(/window\.location\.href = target/, "").replace(/^\s*\/\/.*$/gm, "")), "keine Ziele aus der Adresszeile");
  for (const m of js.matchAll(/\bgo\(([^)]*)\)/g)) assert.match(m[1], /^"anmelden\.html(#abgelaufen)?"$|^g\.expired \? "anmelden\.html#abgelaufen" : "anmelden\.html"$|^target$/, "go(" + m[1] + ")");
  assert.match(js, /K\.tabFromHash\(window\.location\.hash\)/, "der Anker geht nur durch die Liste der vier Werte");
});

test("mein.js: Abgleich beim Zurückkehren in den Tab höchstens alle 60 Sekunden, abgelaufene Sitzung führt zu anmelden.html#abgelaufen", () => {
  const js = read("mein.js");
  assert.match(js, /SYNC_MIN_MS = 60000/);
  assert.match(js, /visibilitychange/);
  assert.match(js, /r\.expired\) \{ go\("anmelden\.html#abgelaufen"\)/);
  assert.match(js, /deletePhotos/, "altes Foto wird gelöscht");
  assert.ok(js.indexOf("store.save([row])") < js.indexOf("await cleanupPhotos(row, old)"), "altes Foto erst nach erfolgreichem Speichern löschen");
  assert.match(js, /revokeObjectURL/);
});

test("mein.js: Fotos eines gelöschten Artikels erst löschen, wenn die Zeile im Konto deleted_at hat", () => {
  const js = read("mein.js"), body = js.slice(js.indexOf("async function removeArticle()"), js.indexOf("function wireForm()"));
  assert.ok(body.indexOf("store.remove(") < body.indexOf("store.loadByIds(") && body.indexOf("store.loadByIds(") < body.indexOf("store.deletePhotos("), "erst löschen, dann nachlesen, dann Fotos");
  assert.match(body, /server && !server\.deleted_at/, "verworfene Löschung erkennen");
  assert.match(body, /else if \(server && paths\.length\) store\.deletePhotos/, "ohne Bestätigung (kein Ergebnis, Netzfehler) bleiben die Fotos liegen");
  assert.equal((body.match(/deletePhotos/g) || []).length, 1, "nur an dieser einen Stelle");
});

test("mein.html: kein Inline-Skript, kein Inline-Stil, genau ein h1, jedes Feld mit Beschriftung, Reiter mit Rollen", () => {
  const h = read("mein.html"), body = h.replace(/<head>[\s\S]*?<\/head>/, "");
  assert.ok(!/<script>[\s\S]*?<\/script>/.test(h), "Inline-Skript");
  assert.ok(!/\sstyle=/.test(body), "Inline-Stil");
  assert.equal((body.match(/<h1[\s>]/g) || []).length, 1);
  const tabs = [...body.matchAll(/<button[^>]*role="tab"[^>]*>/g)].map((m) => m[0]);
  assert.equal(tabs.length, 4);
  assert.equal(tabs.filter((t) => /aria-selected="true"/.test(t)).length, 1);
  for (const t of tabs) { const c = t.match(/aria-controls="([^"]+)"/)[1]; assert.match(body, new RegExp('<section[^>]*role="tabpanel"[^>]*id="' + c + '"')); }
  assert.match(body, /role="tablist"/);
  for (const m of body.matchAll(/<(input|select|textarea)\b([^>]*)>/g)) {
    const attrs = m[2];
    if (/type="hidden"/.test(attrs)) continue;
    const id = (attrs.match(/\bid="([^"]+)"/) || [])[1];
    const inLabel = id ? new RegExp('<label[^>]*for="' + id + '"').test(body) : false;
    const wrapped = /type="(radio|checkbox)"/.test(attrs);   // Radio und Haken stehen im Label
    assert.ok(inLabel || wrapped, "Feld ohne Beschriftung: " + m[0]);
  }
  for (const f of ["mein.js", "konto-lib.js", "konto-net.js"]) assert.match(h, new RegExp('<script src="' + f.replace(".", "\\.") + '">'));
  assert.ok(h.indexOf("konto-lib.js") < h.indexOf("konto-net.js") && h.indexOf("konto-net.js") < h.indexOf("mein.js"), "Reihenfolge der Skripte");
});

test("mein.html: kein Schlusspunkt in Überschriften, Texte der Meldegrenze wie in der App", () => {
  const h = read("mein.html");
  assert.ok(!/<h[1-6][^>]*>[^<]*\.<\/h[1-6]>/.test(h));
  assert.match(h, /Ab 30 Verkäufen oder 2\.000 € Einnahmen im Jahr meldet eine Plattform deine Verkäufe an das Bundeszentralamt für Steuern\./);
  assert.ok(!/Alles bleibt auf deinem iPhone/.test(h + read("mein.js")), "gilt im Browser nicht");
});

/* ---------- Auftrag 04: Fotos ersetzen mit Nachlesen, Übernahme, Datei-Import, Export ---------- */
const { after } = require("node:test");
const A = require("../site/auth-lib.js");
const N = require("../site/konto-net.js");
const fake = require("./support/fake-supabase.js");
const T = require("../site/tax-lib.js");
const servers = [];
after(() => Promise.all(servers.map((x) => x.close())));
const memStorage = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }; };
const jpeg = (n, fill) => { const b = new Uint8Array(n).fill(fill); b[0] = 0xff; b[1] = 0xd8; b[2] = 0xff; return b; };
const T0 = Date.UTC(2026, 9, 31, 12, 0, 0);
async function setup() {
  let t = T0;
  const clock = { now: () => t, advance: (ms) => (t += ms) };
  const srv = await fake.start(clock);
  servers.push(srv);
  const client = A.createClient({ url: srv.url, anonKey: srv.key, storage: memStorage(), now: clock.now });
  await client.signUp("a@beispiel.de", "Fuchs-Mond-Wiese#7", { firstName: "A", sellerMode: "business" });
  await fetch(srv.url + "/mock/confirm?email=a@beispiel.de");
  await client.signIn("a@beispiel.de", "Fuchs-Mond-Wiese#7");
  const store = N.createStore({ url: srv.url, anonKey: srv.key, client });
  const remote = (op, r, later = 0) => fetch(srv.url + "/mock/remote", { method: "POST", body: JSON.stringify({ email: "a@beispiel.de", op, row: r, later }) });
  const state = () => fetch(srv.url + "/mock/state?email=a@beispiel.de").then((x) => x.json());
  return { srv, clock, store, remote, state };
}

test("Fotos ersetzen: Das alte Foto geht nur weg, wenn die Zeile im Konto den neuen Pfad trägt", async () => {
  const { store, remote, state, clock } = await setup();
  const oldUp = await store.uploadPhoto(ID(1), "foto", jpeg(500, 1));
  await store.save([{ ...row(1), changed_at: new Date(clock.now()).toISOString(), photo_path: oldUp.path }]);
  // Erster Fall: ruhiges Konto, das neue Foto wird gespeichert, das alte darf weg
  clock.advance(60000);
  const up1 = await store.uploadPhoto(ID(1), "foto", jpeg(500, 2));
  const r1 = { ...row(1), changed_at: new Date(clock.now()).toISOString(), photo_path: up1.path };
  await store.save([r1]);
  let server = (await store.loadByIds([ID(1)])).rows[0];
  let c = K.photoCleanup([{ col: "photo_path", path: oldUp.path }], server, r1);
  assert.deepEqual(c, { remove: [oldUp.path], keep: [] });
  await store.deletePhotos(c.remove);
  assert.deepEqual((await state()).files, [up1.path]);
  // Zweiter Fall: Ein zweites Gerät ändert später, der Server verwirrft unsere ältere Änderung
  const up2 = await store.uploadPhoto(ID(1), "foto", jpeg(500, 3));
  await remote("update", { id: ID(1), name: "Vom Laptop", photo_path: up1.path }, 3600);
  clock.advance(1000);
  const r2 = { ...row(1), changed_at: new Date(clock.now()).toISOString(), photo_path: up2.path };
  await store.save([r2]);
  server = (await store.loadByIds([ID(1)])).rows[0];
  assert.equal(server.photo_path, up1.path, "der Server hat unsere ältere Änderung verworfen");
  c = K.photoCleanup([{ col: "photo_path", path: up1.path }], server, r2);
  assert.deepEqual(c, { remove: [], keep: [up1.path] }, "das alte Foto bleibt liegen");
  assert.ok((await state()).files.includes(up1.path));
  // Foto entfernen: Zeile trägt kein Foto mehr -> altes darf weg; trägt sie noch eins -> bleibt
  assert.deepEqual(K.photoCleanup([{ col: "photo_path", path: "x" }], { photo_path: null }, { photo_path: null }), { remove: ["x"], keep: [] });
  assert.deepEqual(K.photoCleanup([{ col: "photo_path", path: "x" }], { photo_path: "x" }, { photo_path: null }), { remove: [], keep: ["x"] });
  assert.deepEqual(K.photoCleanup([{ col: "photo_path", path: "x" }], null, { photo_path: "y" }), { remove: [], keep: ["x"] }, "ohne Antwort aus dem Konto bleibt es liegen");
  const js = read("mein.js"), f = js.slice(js.indexOf("async function cleanupPhotos"));
  assert.ok(f.indexOf("loadByIds") < f.indexOf("deletePhotos"), "erst nachlesen, dann löschen");
});

const tools = [
  { id: "t1", name: "Jacke", date: "2026-05-02", platform: "Vinted", buy: 10, sell: 25, cost: 2, status: "sold" },
  { id: "t2", name: "Jacke", date: "2026-05-02", platform: "Vinted", buy: 10, sell: 25, cost: 2, status: "sold" },
  { id: "t3", name: "Lampe", date: "2026-06-01", platform: "eBay", buy: 5, sell: 0, cost: 0, status: "stock" },
];
test("Übernahme: beim zweiten Mal keine neuen, zwei gleiche Verkäufe bleiben zwei, die Daten der Tools bleiben unverändert", async () => {
  const { store, state } = await setup();
  const before = JSON.stringify(tools);
  const plan1 = K.planTakeover(tools, [], opt);
  assert.deepEqual([plan1.rows.length, plan1.present], [3, 0], "zwei gleiche Jacken bleiben zwei");
  let n = 0;
  const rows = K.planTakeover(tools, [], { now: NOW, newId: () => ID(100 + n++) }).rows;
  assert.equal((await store.save(rows)).ok, true);
  const live = (await store.loadAll()).rows;
  const plan2 = K.planTakeover(tools, live, opt);
  assert.deepEqual([plan2.rows.length, plan2.present], [0, 3], "beim zweiten Mal liegt nichts doppelt");
  assert.equal(JSON.stringify(tools), before, "Daten der Tools unverändert");
  assert.equal((await state()).articles, 3);
  const more = K.planTakeover(tools.concat([{ ...tools[0], id: "t4" }]), live, opt);
  assert.equal(more.rows.length, 1, "ein dritter gleicher Verkauf ist neu");
});

test("Datei-Import: dieselbe Anzahl Einträge wie in den Tools, zweiter Import derselben Datei legt nichts an", () => {
  const platforms = [...T.REPORTED_PLATFORMS, "Flohmarkt / bar", "Sonstige"];
  const expected = { ebay: 2, etsy: 3, amazon: 2, paypal: 2, bank: 2 };
  for (const [key, sample] of Object.entries(P.SAMPLES)) {
    const a = P.analyze(sample.text, { maxRows: K.MAX_IMPORT_ROWS });
    assert.equal(a.ok, true, key);
    const o = { platform: sample.platform, keyword: sample.keyword, platforms };
    const e = P.entriesFrom(a, o);
    // gleiche Zeilen wie die Tools: dort läuft dieselbe buildEntries mit denselben Angaben
    const viaTools = P.buildEntries(a.rows, a.map, { dateOrder: a.dateOrder, platform: sample.platform, positiveOnly: !a.own, keywords: (sample.keyword || "").split(/[|,]/), own: a.own, typeChecked: a.typeChecked, known: P.indexExisting([]), platforms });
    assert.equal(e.entries.length, viaTools.entries.length, key);
    assert.equal(e.entries.length, expected[key], key);
    const plan1 = K.planTakeover(e.entries, [], opt);
    assert.equal(plan1.rows.length, expected[key], key);
    const plan2 = K.planTakeover(e.entries, plan1.rows, opt);
    assert.deepEqual([plan2.rows.length, plan2.present], [0, expected[key]], key + ": zweiter Import");
  }
});

test("Datei-Import: mehr als 5000 Zeilen werden abgelehnt, genau 5000 gehen", () => {
  const body = (n) => "Datum;Artikel;Betrag\n" + Array.from({ length: n }, (_, i) => `01.05.2026;Artikel ${i};10,00`).join("\n");
  const big = P.analyze(body(5001), { maxRows: K.MAX_IMPORT_ROWS });
  assert.deepEqual([big.ok, big.tooMany, big.count], [false, true, 5001]);
  assert.match(big.message, /nichts gespeichert/i);
  const ok = P.analyze(body(5000), { maxRows: K.MAX_IMPORT_ROWS });
  assert.equal(ok.ok, true);
  assert.equal(P.entriesFrom(ok, { platform: "Vinted", platforms: ["Vinted"] }).entries.length, 5000);
  assert.equal(K.MAX_IMPORT_ROWS, 5000);
});

test("Datei-Import: leere und kaputte Dateien bekommen die Meldungen der Tools", () => {
  assert.equal(P.analyze("  ", {}).message, "Die Datei ist leer.");
  assert.match(P.analyze("nur eine Zeile", {}).message, /keine Tabelle/);
});

test("Export: Zahlen mit Komma, Formel-Schutz, Datum, BOM, Spalten wie die App, Dateiname", () => {
  const rows = [
    row(1, { name: "=SUMME(1)", sell_cents: 150000, buy_cents: 12345, cost_cents: 5, sale_date: "2026-05-01" }),
    row(2, { name: '+49 "Handy"', is_sold: false, sell_cents: 0, buy_cents: 700, sale_date: null, buy_date: "2026-04-02" }),
    row(3, { name: "gelöscht", deleted_at: "2026-06-01T00:00:00Z" }),
  ];
  const csv = K.exportCsv(rows, { seller_mode: "private" });
  assert.equal(csv.charCodeAt(0), 0xfeff, "BOM für Excel und Numbers");
  const lines = csv.slice(1).trimEnd().split("\r\n");
  assert.equal(lines[0], '"Datum";"Plattform";"Artikel";"Status";"Einkaufsdatum";"Einkaufspreis";"Verkaufspreis";"Nebenkosten";"Gewinn"');
  assert.equal(lines.length, 3, "gelöschte Artikel fehlen");
  assert.ok(lines.some((l) => l === '"02.04.2026";"Vinted";"\'+49 ""Handy""";"im Bestand";"02.04.2026";"7,00";"0,00";"0,00";"0,00"'), lines.join("\n"));
  assert.ok(lines.some((l) => l === '"01.05.2026";"Vinted";"\'=SUMME(1)";"verkauft";"";"123,45";"1500,00";"0,05";"1376,50"'), lines.join("\n"));
  assert.equal(K.exportName(new Date(2026, 9, 31, 12)), "sellcheck-artikel-2026-10-31.csv");
});

test("mein.html und mein.js: Bereich zum Importieren und Exportieren, nur im Browser gelesen, kein neuer Host", () => {
  const h = read("mein.html"), js = read("mein.js");
  for (const id of ["io-take", "io-file", "io-go", "io-cancel", "io-export", "io-dateorder", "io-platform", "io-keyword"]) assert.ok(h.includes('id="' + id + '"'), id);
  assert.match(h, /type="file"[^>]*multiple/);
  assert.ok(!/<form[^>]*action=/.test(h));
  assert.ok(!/localStorage\.(setItem|removeItem)\(\s*(TOOLS_KEYS|"sellcheck\.sales)/.test(js), "Daten der Tools werden nie geschrieben");
  assert.ok(!/https?:\/\//.test(js.replace(/https:\/\/xjogkqttzfsgjeqhkndf/g, "")), "kein Host im Skript");
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(/.test(js.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n")));
  assert.match(h, /<meta http-equiv="Content-Security-Policy" content="[^"]*connect-src 'self' https:\/\/xjogkqttzfsgjeqhkndf\.supabase\.co;/);
});
