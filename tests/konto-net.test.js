// Prüft die Netzschicht von „Mein SellCheck“ (site/konto-net.js) gegen den Nachbau der Schnittstelle (tests/support/fake-supabase.js).
// Ausführen: node --test tests/konto-net.test.js
const test = require("node:test");
const { after } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const A = require("../site/auth-lib.js");
const K = require("../site/konto-lib.js");
const N = require("../site/konto-net.js");
const fake = require("./support/fake-supabase.js");

const memStorage = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }; };
const servers = [];
after(() => Promise.all(servers.map((x) => x.close())));
const PW = "Fuchs-Mond-Wiese#7", MAIL = "max@beispiel.de";
const id = (n) => "00000000-0000-4000-8000-" + String(n).padStart(12, "0");
const T0 = Date.UTC(2026, 9, 30, 12, 0, 0);
const row = (n, extra = {}) => ({ id: id(n), name: "Artikel " + n, platform: "Vinted", buy_cents: 500, sell_cents: 1500, cost_cents: 0, is_sold: true, sale_date: "2026-05-01", buy_date: null, notes: "", changed_at: new Date(T0).toISOString(), deleted_at: null, ...extra });
const jpeg = (n, fill = 7) => { const b = new Uint8Array(n); b.fill(fill); b[0] = 0xff; b[1] = 0xd8; b[2] = 0xff; return b; };

/** Konto anlegen, bestätigen, anmelden. Gibt Server, Uhr, Zugang und die Netzschicht zurück. */
async function setup(opts = {}) {
  let t = T0;
  const clock = { now: () => t, advance: (ms) => (t += ms) };
  const srv = await fake.start(clock);
  servers.push(srv);
  const client = A.createClient({ url: srv.url, anonKey: srv.key, storage: memStorage(), now: clock.now });
  await client.signUp(MAIL, PW, { firstName: "Max", lastName: "Meier", sellerMode: "business" });
  await fetch(srv.url + "/mock/confirm?email=" + MAIL);
  const s = await client.signIn(MAIL, PW);
  assert.equal(s.ok, true);
  const store = N.createStore({ url: srv.url, anonKey: srv.key, client, ...opts });
  const remote = (op, r, later = 0) => fetch(srv.url + "/mock/remote", { method: "POST", body: JSON.stringify({ email: MAIL, op, row: r, later }) }).then((x) => x.json());
  const state = () => fetch(srv.url + "/mock/state?email=" + MAIL).then((x) => x.json());
  return { srv, clock, client, store, uid: s.session.userId, remote, state };
}
const calls = (srv, method, p) => srv.log.filter((x) => x.method === method && x.path.startsWith(p));

test("Laden: alle Zeilen seitenweise, ohne gelöschte, mit Merker", async () => {
  const { srv, store, clock } = await setup({ pageSize: 2 });
  await store.save([1, 2, 3, 4, 5].map((n) => row(n)));
  clock.advance(1000);
  await store.remove(id(2), new Date(clock.now()));
  srv.log.length = 0;
  const r = await store.loadAll();
  assert.equal(r.ok, true);
  assert.deepEqual(r.rows.map((x) => x.id), [id(1), id(3), id(4), id(5)].sort());
  assert.equal(calls(srv, "GET", "/rest/v1/articles").length, 3, "5 Zeilen bei Seite 2: drei Anfragen");
  assert.deepEqual(calls(srv, "GET", "/rest/v1/articles").map((x) => x.query.offset), ["0", "2", "4"]);
  assert.equal(calls(srv, "GET", "/rest/v1/articles")[0].query.order, "updated_at.asc,id.asc");
  assert.ok(r.cursor, "Merker vorhanden");
});

test("Änderungen seit dem Merker: 120 Sekunden Überlappung", async () => {
  const { srv, store, clock } = await setup();
  await store.save([row(1), row(2)]);
  const first = await store.loadAll();
  clock.advance(60 * 1000);
  await store.save([row(3, { changed_at: new Date(clock.now()).toISOString() })]);
  srv.log.length = 0;
  const ch = await store.loadChanges(first.cursor);
  const q = calls(srv, "GET", "/rest/v1/articles")[0].query.updated_at;
  assert.equal(q, "gte." + new Date(Date.parse(first.cursor) - 120000).toISOString());
  assert.deepEqual(ch.rows.map((x) => x.id).sort(), [id(1), id(2), id(3)], "Überlappung holt auch die zuletzt gesehenen Zeilen noch einmal");
  const merged = K.mergeChanges(new Map(first.rows.map((x) => [x.id, x])), ch.rows);
  assert.equal(merged.size, 3);
  assert.ok(ch.cursor >= first.cursor);
  clock.advance(10 * 60 * 1000);
  await store.save([row(4, { changed_at: new Date(clock.now()).toISOString() })]);
  const c2 = (await store.loadChanges(ch.cursor)).cursor;
  clock.advance(10 * 60 * 1000);
  await store.save([row(5, { changed_at: new Date(clock.now()).toISOString() })]);
  const later = await store.loadChanges(c2);
  assert.deepEqual(later.rows.map((x) => x.id), [id(4), id(5)], "was mehr als 120 s vor dem Merker liegt, kommt nicht noch einmal; die Zeile am Merker schon");
});

test("Zweites Gerät ändert und löscht: kommt beim nächsten Abgleich an", async () => {
  const { store, clock, remote } = await setup();
  await store.save([row(1), row(2)]);
  const all = await store.loadAll();
  let byId = new Map(all.rows.map((x) => [x.id, x]));
  clock.advance(5 * 60 * 1000);
  await remote("update", { id: id(1), name: "Vom Laptop" });
  await remote("delete", { id: id(2) });
  const ch = await store.loadChanges(all.cursor);
  byId = K.mergeChanges(byId, ch.rows);
  assert.equal(byId.get(id(1)).name, "Vom Laptop");
  assert.equal(byId.has(id(2)), false, "gelöscht verschwindet");
});

test("Speichern in Paketen zu 500, jede Zeile mit user_id", async () => {
  const { srv, store, uid, state } = await setup();
  const rows = Array.from({ length: 1201 }, (_, i) => row(i + 1));
  const r = await store.save(rows);
  assert.deepEqual([r.ok, r.saved], [true, 1201]);
  const posts = calls(srv, "POST", "/rest/v1/articles");
  assert.deepEqual(posts.map((x) => x.body.length), [500, 500, 201]);
  assert.ok(posts.every((x) => x.query.on_conflict === "user_id,id" && x.headers.prefer === "resolution=merge-duplicates,return=minimal"));
  assert.ok(posts.every((x) => x.body.every((z) => z.user_id === uid && !("updated_at" in z))));
  assert.equal((await state()).articles, 1201);
});

test("Speichern und neu laden ergibt dieselben Zeilen", async () => {
  const { store } = await setup();
  const mine = [row(1, { notes: "mit Umlaut äöü" }), row(2, { is_sold: false, sell_cents: 0, sale_date: null, buy_date: "2026-04-01" })];
  await store.save(mine);
  const back = (await store.loadAll()).rows;
  for (const m of mine) {
    const got = back.find((x) => x.id === m.id);
    for (const k of Object.keys(m)) assert.deepEqual(got[k], m[k], k);
  }
});

test("Trigger-Regel: eine ältere changed_at überschreibt keine neuere", async () => {
  const { store, state } = await setup();
  await store.save([row(1, { name: "Neu", changed_at: new Date(T0 + 60000).toISOString() })]);
  const r = await store.save([row(1, { name: "Alt", changed_at: new Date(T0).toISOString() })]);
  assert.equal(r.ok, true, "der Server nimmt die Anfrage an und verwirft die Zeile still");
  assert.equal((await store.loadAll()).rows[0].name, "Neu");
  await store.save([row(1, { name: "Neuer", changed_at: new Date(T0 + 120000).toISOString() })]);
  assert.equal((await store.loadAll()).rows[0].name, "Neuer");
  assert.equal((await state()).articles, 1);
});

test("Löschen ist nur eine Markierung", async () => {
  const { srv, store, state, clock } = await setup();
  await store.save([row(1), row(2)]);
  clock.advance(1000);
  const now = new Date(clock.now());
  srv.log.length = 0;
  assert.equal((await store.remove(id(1), now)).ok, true);
  const p = calls(srv, "PATCH", "/rest/v1/articles")[0];
  assert.equal(p.query.id, "eq." + id(1));
  assert.deepEqual(p.body, { deleted_at: now.toISOString(), changed_at: now.toISOString() });
  assert.equal(calls(srv, "DELETE", "/rest/v1/articles").length, 0, "kein DELETE");
  const s = await state();
  assert.deepEqual([s.articles, s.deleted], [1, 1], "Zeile bleibt im Konto, mit Markierung");
  assert.deepEqual((await store.loadAll()).rows.map((x) => x.id), [id(2)]);
  assert.equal((await store.remove("kein-uuid", now)).ok, false);
});

test("Löschen prüfen: loadByIds zeigt deleted_at, ein neuerer Stand vom zweiten Gerät verwirft die Löschung", async () => {
  const { srv, store, clock, remote } = await setup();
  await store.save([row(1, { photo_path: "p/1.jpg" }), row(2), row(3)]);
  clock.advance(1000);
  await store.remove(id(1), new Date(clock.now()));
  const ok = await store.loadByIds([id(1), id(2)]);
  assert.equal(ok.ok, true);
  assert.deepEqual(ok.rows.map((x) => [x.id, !!x.deleted_at]).sort(), [[id(1), true], [id(2), false]], "nur die gefragten Zeilen, auch gelöschte");
  const q = calls(srv, "GET", "/rest/v1/articles").pop().query;
  assert.equal(q.id, "in.(" + id(1) + "," + id(2) + ")");
  assert.equal(q.select, "id,deleted_at,photo_path,receipt_path");
  // Das zweite Gerät hat Artikel 3 später geändert: Die Löschung von hier trägt einen älteren Zeitstempel und wird vom Trigger verworfen.
  await remote("upsert", row(3, { name: "Neuer Name" }), 60);
  assert.equal((await store.remove(id(3), new Date(clock.now()))).ok, true, "der Server antwortet trotzdem mit Erfolg");
  const lost = await store.loadByIds([id(3)]);
  assert.equal(lost.rows[0].deleted_at, null, "deleted_at fehlt: Fotos dürfen nicht gelöscht werden");
  assert.equal((await store.loadByIds(["kein-uuid"])).ok, false);
  assert.equal((await store.loadByIds([])).ok, false);
});

test("Profil lesen wie in der App", async () => {
  const { srv, store } = await setup();
  const r = await store.loadProfile();
  assert.deepEqual(r.profile, { first_name: "", last_name: "", seller_mode: "business", vat_mode: "small", vat_rate: 19 });
  const q = calls(srv, "GET", "/rest/v1/profiles")[0].query;
  assert.equal(q.select, "first_name,last_name,seller_mode,vat_mode,vat_rate");
  assert.equal(q.id, "eq." + (await store.loadProfile(), srv.users.get(MAIL).id));
});

test("Foto hoch und wieder runter, byte-gleich, Pfad wie in der App", async () => {
  const { srv, store, uid, state } = await setup();
  const bytes = jpeg(3000, 42);
  const up = await store.uploadPhoto(id(1).toUpperCase(), "foto", bytes);
  assert.equal(up.ok, true);
  assert.equal(up.path, K.storagePath(uid, id(1), "foto", K.checksum(bytes)));
  assert.match(up.path, new RegExp("^" + uid + "/" + id(1) + "-foto-[0-9a-f]{8}\\.jpg$"));
  const post = calls(srv, "POST", "/storage/")[0];
  assert.equal(post.headers["content-type"], "image/jpeg");
  assert.equal(post.headers["x-upsert"], "true");
  const down = await store.photoBlob(up.path);
  assert.equal(down.ok, true);
  assert.deepEqual(new Uint8Array(await down.blob.arrayBuffer()), bytes);
  assert.deepEqual((await state()).files, [up.path]);
  // fester Inhalt gegen festen Pfad (FNV-1a von "a" ist e40c292c, siehe konto-lib.test.js)
  const fixed = new Uint8Array([0xff, 0xd8, 0xff, 0x61]);
  const r2 = await store.uploadPhoto(id(2), "beleg", fixed);
  assert.equal(r2.path, uid + "/" + id(2) + "-beleg-" + K.checksum(fixed) + ".jpg");
  const del = await store.deletePhotos([up.path, r2.path]);
  assert.deepEqual([del.ok, del.deleted, del.skipped], [true, 2, 0]);
  assert.deepEqual((await state()).files, []);
});

test("Fremde Pfade werden weder geladen noch gelöscht", async () => {
  const { srv, store, uid } = await setup();
  srv.log.length = 0;
  for (const p of ["andere-kennung/" + id(1) + "-foto-00000000.jpg", uid + "/../andere/x.jpg", uid + "//x.jpg", "/" + uid + "/x.jpg", uid + "x/y.jpg", null, 5]) {
    const r = await store.photoBlob(p);
    assert.equal(r.ok, false, String(p));
  }
  const del = await store.deletePhotos(["andere-kennung/x.jpg", uid + "/../x.jpg"]);
  assert.deepEqual([del.ok, del.deleted, del.skipped], [true, 0, 2]);
  assert.equal(calls(srv, "GET", "/storage/").length + calls(srv, "DELETE", "/storage/").length, 0, "keine Anfrage");
});

test("Fotos: nur JPEG bis 5 MB, sonst Meldung ohne Anfrage", async () => {
  const { srv, store, state } = await setup();
  srv.log.length = 0;
  const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 1, 2, 3]);
  const big = jpeg(5 * 1024 * 1024 + 1);
  assert.match((await store.uploadPhoto(id(1), "foto", png)).message, /JPEG/);
  assert.match((await store.uploadPhoto(id(1), "foto", big)).message, /5 MB/);
  assert.equal((await store.uploadPhoto(id(1), "video", jpeg(10))).ok, false);
  assert.equal((await store.uploadPhoto("kaputt", "foto", jpeg(10))).ok, false);
  assert.equal(calls(srv, "POST", "/storage/").length, 0, "keine Anfrage");
  assert.equal((await store.uploadPhoto(id(1), "foto", jpeg(5 * 1024 * 1024))).ok, true, "genau 5 MB gehen");
  assert.equal((await state()).files.length, 1);
});

test("401: genau einmal erneuern und wiederholen, sonst abgelaufen", async () => {
  const { srv, store, client } = await setup();
  await store.save([row(1)]);
  // Zugangs-Token beim Server ungültig, Erneuerung möglich
  srv.tokens.clear();
  srv.log.length = 0;
  const ok = await store.loadAll();
  assert.equal(ok.ok, true, "nach der Erneuerung klappt es");
  assert.equal(srv.log.filter((x) => x.path === "/auth/v1/token").length, 1, "genau eine Erneuerung");
  assert.equal(calls(srv, "GET", "/rest/v1/articles").length, 2, "erste Anfrage 401, Wiederholung 200");
  // Zugangs-Token und Erneuerungs-Token ungültig
  srv.tokens.clear(); srv.refresh.clear();
  srv.log.length = 0;
  const r = await store.loadAll();
  assert.deepEqual(r, { ok: false, expired: true });
  assert.equal(srv.log.filter((x) => x.path === "/auth/v1/token").length, 1, "nur ein Erneuerungsversuch");
  assert.equal(calls(srv, "GET", "/rest/v1/articles").length, 1, "keine Wiederholung ohne neue Sitzung");
  assert.equal((await client.getSession()).session, null, "die Sitzung ist gelöscht");
  assert.deepEqual(await store.save([row(2)]), { ok: false, expired: true });
});

test("Keine Verbindung: Text aus auth-lib, keine Einzelheiten", async () => {
  const { srv, store } = await setup();
  await srv.close();
  for (const r of [await store.loadAll(), await store.save([row(1)]), await store.remove(id(1), new Date(T0)), await store.loadProfile(), await store.uploadPhoto(id(1), "foto", jpeg(10))]) {
    assert.deepEqual([r.ok, r.message], [false, A.NETWORK]);
  }
});

test("Serverfehler: nur die allgemeine Meldung, nichts aus der Antwort", async () => {
  const { store } = await setup({ fetch: async () => new Response(JSON.stringify({ message: "secret detail user_id=u1" }), { status: 500 }) });
  const r = await store.loadAll();
  assert.equal(r.ok, false);
  assert.equal(r.message, A.errorMessage(500, null, "other"));
  assert.doesNotMatch(JSON.stringify(r), /secret|user_id/);
  const s = N.createStore({ url: "http://127.0.0.1:1", anonKey: "k", client: { getSession: async () => ({ session: { accessToken: "t", userId: "u" } }) }, fetch: async () => new Response("{}", { status: 400 }) });
  assert.match((await s.loadAll()).message, /Fehler 400/);
});

test("Aufbau: Adresse und Schlüssel sind Pflicht, konto-net.js hat kein DOM und keine Supabase-Adresse", () => {
  assert.throws(() => N.createStore({ url: "", anonKey: "k", client: {} }));
  assert.throws(() => N.createStore({ url: "http://127.0.0.1:1", anonKey: "", client: {} }));
  assert.throws(() => N.createStore({ url: "http://127.0.0.1:1", anonKey: "k" }));
  const src = fs.readFileSync(path.join(__dirname, "..", "site", "konto-net.js"), "utf8");
  assert.doesNotMatch(src, /supabase\.co/);
  const code = src.split("\n").filter((l) => !l.trim().startsWith("//") && !l.trim().startsWith("/**")).join("\n");
  assert.doesNotMatch(code, /\b(document|window|localStorage|sessionStorage|innerHTML|console)\b/);
});
