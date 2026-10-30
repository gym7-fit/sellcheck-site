// Anmeldung im Browser (site/auth-lib.js): Passwort-Regeln wie in der App, Ablauf gegen einen Nachbau der Schnittstelle, Seiten und Sicherheitsrichtlinie.
// Ausführen: node --test tests/auth.test.js
const test = require("node:test");
const { after } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const A = require("../site/auth-lib.js");
const fake = require("./support/fake-supabase.js");

const SITE = path.join(__dirname, "..", "site");
const read = (f) => fs.readFileSync(path.join(SITE, f), "utf8");
const memStorage = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k), _m: m }; };
const SUPABASE_HOST = "https://xjogkqttzfsgjeqhkndf.supabase.co";

/* ---------- Passwort-Regeln: dieselben Beispiele wie Tests/main.swift der App ---------- */
const ok = (p, email = "", names = []) => A.evaluatePassword(p, email, names).valid;

test("Passwort: gute Passwörter gehen durch, auch mit Umlauten", () => {
  for (const p of ["Fuchs-Mond-Wiese#7", "Zebra#Regal!Tisch", "Küchenschrank?Blau"]) assert.equal(ok(p), true, p);
});
test("Passwort: Großbuchstabe, Sonderzeichen und zehn Zeichen sind Pflicht", () => {
  assert.equal(ok("fuchs-mond-wiese-7"), false);
  assert.equal(A.evaluatePassword("fuchs-mond-wiese-7").rules.find((r) => r.id === "upper").ok, false);
  assert.equal(ok("FuchsMondWiese7"), false);
  assert.equal(A.evaluatePassword("FuchsMondWiese7").rules.find((r) => r.id === "special").ok, false);
  assert.equal(ok("Fuchs-9"), false);
  assert.equal(A.passwordError("kurz"), "Das Passwort braucht mindestens 10 Zeichen. Noch 6.");
  assert.equal(A.passwordError(""), "");
  assert.equal(A.passwordError("Fuchs-Mond-Wiese#7"), "");
  assert.equal(ok("Fuchs-Mond-Wiese-" + "x".repeat(60)), false, "über 72 Zeichen");
});
test("Passwort: bekannte Passwörter auch mit Zahlen, Leetspeak und Zeichen verboten", () => {
  for (const p of ["Passwort123!", "Password1234!", "P4ssw0rt!!!", "Hallo12345!", "Sommer2024!!"]) assert.equal(ok(p), false, p);
  assert.equal(A.passwordError("Passwort123!"), "Dieses Passwort ist zu bekannt. Wähle etwas Eigenes.");
});
test("Passwort: Tastatur- und Zahlenfolgen, gleiche Zeichen und Wiederholblöcke verboten", () => {
  for (const p of ["Qwertz-Mond-9", "Abcd#Wiese-Mond", "Fuchs-1234-Mond", "Fuchs-Mond-4321", "Fuchs!!!Mond-Wiese", "Abc#Abc#Abc#", "Xy-Xy-Xy-Xy-"]) assert.equal(ok(p), false, p);
});
test("Passwort: Name, E-Mail und SellCheck im Passwort verboten", () => {
  assert.equal(ok("Louis-Meier-Fuchs#9", "", ["Louis"]), false);
  assert.equal(ok("Mond-Wiese-louis.thk14!", "louis.thk14@gmail.com"), false);
  assert.equal(ok("Mein-SellCheck-Pw#9"), false);
  assert.equal(ok("Mond-Wiese-Fuchs#7", "max@beispiel.de", ["Max"]), true);
});
test("Passwort: leeres Feld zeigt nur offene Regeln, keine Verbote", () => {
  const r = A.evaluatePassword("");
  assert.equal(r.problems.length, 0);
  assert.ok(r.rules.every((x) => !x.ok));
});
test("Fehlertexte wie in der App, ohne rohe Servertexte", () => {
  assert.match(A.errorMessage(400, { error_code: "invalid_credentials" }, "signIn"), /^E-Mail oder Passwort stimmt nicht/);
  assert.match(A.errorMessage(400, { error_code: "email_not_confirmed" }), /^Bestätige zuerst/);
  assert.match(A.errorMessage(422, { error_code: "weak_password" }), /zu schwach/);
  assert.match(A.errorMessage(422, { error_code: "same_password" }), /anders/);
  assert.match(A.errorMessage(500, {}), /Server/);
  assert.ok(!/Invalid|JWT|supabase/i.test(A.errorMessage(400, { msg: "Invalid login credentials" }, "signIn")));
});
test("Code: nur Ziffern, 6 bis 10 Stellen, Leerzeichen und Striche werden entfernt", () => {
  assert.equal(A.normalizeCode(" 123 456 "), "123456");
  assert.equal(A.validCode("12345678"), true);
  assert.equal(A.validCode("12345"), false);
  assert.equal(A.validCode("12345678901"), false);
});
test("Registrierung: Angaben im Konto wie SignupProfile.metadata() der App", () => {
  const m = A.signupMetadata({ firstName: " Louis ", lastName: "Meier", sellerMode: "business", privacyAccepted: true, marketingOptIn: true }, Date.UTC(2026, 9, 30, 12, 0, 0));
  assert.deepEqual(m, { first_name: "Louis", last_name: "Meier", seller_mode: "business", vat_mode: "small", vat_rate: 19, privacy_accepted_at: "2026-10-30T12:00:00Z", marketing_opt_in: true, marketing_opt_in_at: "2026-10-30T12:00:00Z" });
  const p = A.signupMetadata({ firstName: "A", lastName: "", sellerMode: "private", privacyAccepted: true, marketingOptIn: false }, 0);
  assert.equal(p.seller_mode, "private"); assert.equal(p.vat_mode, undefined); assert.equal(p.marketing_opt_in, false); assert.equal(p.marketing_opt_in_at, undefined); assert.equal(p.last_name, undefined);
});

test("Registrierung: Differenzbesteuerung wird gespeichert, Satz bleibt 19", () => {
  const margin = A.signupMetadata({ firstName: "A", sellerMode: "business", vatMode: "margin", vatRate: 7 }, 0);
  assert.equal(margin.vat_mode, "margin"); assert.equal(margin.vat_rate, 19);   // Satz 7 gilt nur bei regular
});
test("Registrierung: Regelbesteuerung mit 7 %, unbekannter Wert wird Kleinunternehmer, privat ohne Steuerfelder", () => {
  const reg7 = A.signupMetadata({ firstName: "A", sellerMode: "business", vatMode: "regular", vatRate: 7 }, 0);
  assert.equal(reg7.vat_mode, "regular"); assert.equal(reg7.vat_rate, 7);
  assert.equal(A.signupMetadata({ firstName: "A", sellerMode: "business", vatMode: "quatsch" }, 0).vat_mode, "small");
  assert.equal(A.signupMetadata({ firstName: "A", sellerMode: "private", vatMode: "regular", vatRate: 7 }, 0).vat_mode, undefined);
  assert.match(A.vatExplainer("regular", 7), /\(7 %\)/);
});

/* ---------- Ablauf gegen den Nachbau der Schnittstelle ---------- */
const servers = [];
after(() => Promise.all(servers.map((x) => x.close())));   // auch bei einem Fehler im Test: Server schließen, sonst hängt der Lauf
async function setup(extra = {}) {
  let t = Date.UTC(2026, 9, 30, 12, 0, 0);
  const clock = { now: () => t, advance: (ms) => (t += ms) };
  const srv = await fake.start(clock);
  servers.push(srv);
  const storage = memStorage();
  const client = A.createClient({ url: srv.url, anonKey: srv.key, storage, now: clock.now, redirectTo: "https://x.example/bestaetigt.html", ...extra });
  return { srv, storage, clock, client };
}
const PW = "Fuchs-Mond-Wiese#7";

test("Registrieren: zu schwaches Passwort wird abgelehnt, bevor etwas gesendet wird", async () => {
  const { srv, client } = await setup();
  const r = await client.signUp("a@b.de", "kurz", { firstName: "A", lastName: "B" });
  assert.equal(r.ok, false);
  assert.equal(srv.log.length, 0, "keine Anfrage");
  await srv.close();
});

test("Registrieren, Anmelden vor und nach der Bestätigung, gleiche Meldung bei falschem Passwort und fehlendem Konto", async () => {
  const { srv, storage, client } = await setup();
  const r = await client.signUp("Max@Beispiel.de", PW, { firstName: "Max", lastName: "Meier", sellerMode: "private", privacyAccepted: true, marketingOptIn: false });
  assert.deepEqual([r.ok, r.needsConfirmation, r.email], [true, true, "max@beispiel.de"]);
  const call = srv.log.find((x) => x.path === "/auth/v1/signup");
  assert.equal(call.query.redirect_to, "https://x.example/bestaetigt.html");
  assert.equal(call.body.data.first_name, "Max");
  assert.equal(call.body.password, PW);
  assert.equal(call.auth, "Bearer " + srv.key, "ohne Anmeldung gilt der öffentliche Schlüssel");

  let s = await client.signIn("max@beispiel.de", PW);
  assert.equal(s.ok, false); assert.match(s.message, /^Bestätige zuerst/);
  assert.equal(storage.getItem(A.SESSION_KEY), null);

  await fetch(srv.url + "/mock/confirm?email=max@beispiel.de");
  const wrong = await client.signIn("max@beispiel.de", "Falsch-Passwort#1");
  const nobody = await client.signIn("niemand@beispiel.de", "Falsch-Passwort#1");
  assert.equal(wrong.message, nobody.message, "verrät nicht, ob es das Konto gibt");
  assert.match(wrong.message, /^E-Mail oder Passwort stimmt nicht/);

  s = await client.signIn("max@beispiel.de", PW);
  assert.equal(s.ok, true);
  assert.ok(storage.getItem(A.SESSION_KEY).includes("max@beispiel.de"));
  assert.equal((await client.getSession()).session.email, "max@beispiel.de");
  await srv.close();
});

test("Sitzung: wird 60 Sekunden vor Ablauf erneuert, bei abgelaufener Erneuerung gelöscht", async () => {
  const { srv, storage, clock, client } = await setup();
  await client.signUp("a@beispiel.de", PW, { firstName: "A", lastName: "B" });
  await fetch(srv.url + "/mock/confirm?email=a@beispiel.de");
  const first = (await client.signIn("a@beispiel.de", PW)).session;
  clock.advance(3600 * 1000 - 120000);
  assert.equal((await client.getSession()).session.accessToken, first.accessToken, "noch früh genug");
  clock.advance(70000);
  const renewed = (await client.getSession()).session;
  assert.notEqual(renewed.accessToken, first.accessToken, "erneuert");
  assert.equal(JSON.parse(storage.getItem(A.SESSION_KEY)).accessToken, renewed.accessToken);
  srv.refresh.clear();   // Erneuerung am Server abgelaufen
  clock.advance(3600 * 1000);
  const r = await client.getSession();
  assert.deepEqual([r.session, r.expired], [null, true]);
  assert.equal(storage.getItem(A.SESSION_KEY), null);
  await srv.close();
});

test("Abmelden löscht den Eintrag in jedem Fall, auch wenn der Server nicht antwortet", async () => {
  const { srv, storage, client } = await setup();
  await client.signUp("a@beispiel.de", PW, { firstName: "A", lastName: "B" });
  await fetch(srv.url + "/mock/confirm?email=a@beispiel.de");
  await client.signIn("a@beispiel.de", PW);
  await srv.close();
  assert.ok(storage.getItem(A.SESSION_KEY));
  await client.signOut();
  assert.equal(storage.getItem(A.SESSION_KEY), null);
  assert.equal((await client.getSession()).session, null);
});

test("Zurücksetzen in drei Schritten: Code anfordern, Code prüfen, neues Passwort", async () => {
  const { srv, storage, client } = await setup();
  await client.signUp("a@beispiel.de", PW, { firstName: "A", lastName: "B" });
  await fetch(srv.url + "/mock/confirm?email=a@beispiel.de");
  const known = await client.requestReset("a@beispiel.de"), unknown = await client.requestReset("niemand@beispiel.de");
  assert.deepEqual([known.ok, unknown.ok], [true, true], "gleiche Antwort, egal ob es das Konto gibt");
  const bad = await client.verifyResetCode("a@beispiel.de", "000000");
  assert.equal(bad.ok, false); assert.match(bad.message, /falsch oder abgelaufen/);
  const short = await client.verifyResetCode("a@beispiel.de", "123");
  assert.match(short.message, /nur aus Ziffern/);
  const v = await client.verifyResetCode("a@beispiel.de", "123 456");
  assert.equal(v.ok, true);
  assert.equal(storage.getItem(A.SESSION_KEY), null, "vor dem neuen Passwort noch nicht angemeldet");
  const weak = await client.completeReset(v.session, "schwach", []);
  assert.equal(weak.ok, false);
  const same = await client.completeReset(v.session, PW, []);   // gleich dem alten Passwort
  assert.equal(same.ok, false); assert.match(same.message, /anders/);
  const done = await client.completeReset(v.session, "Neuer-Hase-Kaffee#42", []);
  assert.equal(done.ok, true);
  assert.ok(storage.getItem(A.SESSION_KEY));
  await client.signOut();
  assert.equal((await client.signIn("a@beispiel.de", PW)).ok, false);
  assert.equal((await client.signIn("a@beispiel.de", "Neuer-Hase-Kaffee#42")).ok, true);
  await srv.close();
});

test("Keine Verbindung: verständliche Meldung, Sitzung bleibt bis zum Ablauf erhalten", async () => {
  const { srv, clock, client } = await setup();
  await client.signUp("a@beispiel.de", PW, { firstName: "A", lastName: "B" });
  await fetch(srv.url + "/mock/confirm?email=a@beispiel.de");
  await client.signIn("a@beispiel.de", PW);
  await srv.close();
  const r = await client.signIn("a@beispiel.de", PW);
  assert.match(r.message, /^Keine Verbindung/);
  clock.advance(3600 * 1000 - 30000);
  const s = await client.getSession();
  assert.equal(s.offline, true); assert.ok(s.session, "noch nicht abgelaufen");
});

/* ---------- Seiten und Sicherheitsrichtlinie ---------- */
const ACCOUNT_PAGES = ["anmelden.html", "registrieren.html", "mein.html"];
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

test("Seiten: Konto-Seiten sind nicht indexiert, ohne Inline-Skript, mit Archivo-Kopf und Fuß", () => {
  for (const f of ACCOUNT_PAGES) {
    const h = read(f);
    assert.match(h, /<meta name="robots" content="noindex">/, f);
    assert.ok(!/<script>[\s\S]*?<\/script>/.test(h), f + ": Inline-Skript");
    assert.match(h, /<header class="site-header">/, f); assert.match(h, /<footer/, f);
    assert.match(h, /<script src="auth-ui\.js"><\/script>/, f);
    assert.ok(!/<h[1-6][^>]*>[^<]*\.<\/h[1-6]>/.test(h), f + ": Überschrift mit Schlusspunkt");
  }
});
test("Sicherheitsrichtlinie: Der Anmeldedienst steht nur in den drei Konto-Seiten, mein.html darf zusätzlich blob-Bilder", () => {
  for (const f of walk(SITE).filter((x) => x.endsWith(".html"))) {
    const rel = path.relative(SITE, f), h = fs.readFileSync(f, "utf8");
    const csp = (h.match(/Content-Security-Policy" content="([^"]*)"/) || [])[1] || "";
    if (ACCOUNT_PAGES.includes(rel)) {
      assert.ok(csp.includes("connect-src 'self' " + SUPABASE_HOST), rel);
      assert.equal(csp.includes("blob:"), rel === "mein.html", rel + ": blob nur in mein.html");
    } else assert.ok(!csp.includes("supabase") && !csp.includes("blob:"), rel + ": Richtlinie unverändert");
  }
  assert.equal(read("auth-config.js").match(/https:\/\/[a-z0-9.-]+\.supabase\.co/g).length, 1);
});
test("Weiterleitung: nur feste Ziele, nichts aus der Adresszeile", () => {
  const ui = read("auth-ui.js");
  assert.ok(!/location\.(search|hash)\s*(?!===)/.test(ui.replace('window.location.hash === "#abgelaufen"', "")), "keine Ziele aus der Adresszeile");
  for (const m of ui.matchAll(/\bgo\(([^)]*)\)/g)) assert.match(m[1], /^"(mein|anmelden)\.html(#abgelaufen)?"$|^r\.expired \? "anmelden\.html#abgelaufen" : "anmelden\.html"$|^target$/, "go(" + m[1] + ")");
  assert.ok(!/innerHTML|outerHTML|document\.write|eval\(/.test(ui + read("auth-lib.js")), "keine unsichere Ausgabe");
});
test("Fußzeile: Link „Mein SellCheck“ führt zu anmelden.html, in der Kopfzeile nicht", () => {
  for (const f of walk(SITE).filter((x) => x.endsWith(".html"))) {
    const rel = path.relative(SITE, f), h = fs.readFileSync(f, "utf8");
    if (!/<footer/.test(h) || !h.includes("Gratis-Tools")) continue;
    assert.match(h, /<li><a href="(\.\.\/)?anmelden\.html">Mein SellCheck<\/a><\/li>/, rel);
    assert.ok(!/<header[\s\S]*?Mein SellCheck[\s\S]*?<\/header>/.test(h), rel + ": nicht in die Kopfzeile");
  }
  assert.match(read("bestaetigt.html"), /href="anmelden\.html">Im Browser anmelden</);
  assert.match(read("bestaetigt.html"), /href="sellcheck:\/\/bestaetigt"/);
});
