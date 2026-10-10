// Ausführen: node --test tests/auth.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const A = require("../site/auth-lib.js");

const memStorage = () => {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k), _m: m };
};
const demo = (extra = {}) => {
  const storage = memStorage();
  let t = 1_000_000;
  const clock = { now: () => t, advance: (ms) => (t += ms) };
  const auth = A.createDemoAuth({ storage, crypto: globalThis.crypto, now: clock.now, iterations: 1000, ...extra });
  return { storage, clock, auth };
};

/* ---- Eingaben ---- */
test("E-Mail: trimmt, macht klein, lehnt Unsinn ab", () => {
  assert.deepEqual(A.validateEmail("  Max@Example.DE "), { ok: true, value: "max@example.de" });
  for (const bad of ["", "max", "max@", "@x.de", "a b@c.de", "max@x", "a@b.c", "x".repeat(250) + "@a.de"]) assert.equal(A.validateEmail(bad).ok, false, bad);
});

test("Passwort: Mindestlänge, nur Ziffern, zu einfach, bekannte Passwörter, gleich der E-Mail", () => {
  assert.equal(A.validatePassword("kurz").ok, false);
  assert.equal(A.validatePassword("12345678901").ok, false, "nur Ziffern");
  assert.equal(A.validatePassword("aaaaaaaaaaaa").ok, false, "zu wenig verschiedene Zeichen");
  assert.equal(A.validatePassword("Passwort123").ok, false, "bekannt");
  assert.equal(A.validatePassword("max@example.de", "max@example.de").ok, false);
  assert.equal(A.validatePassword("Kaffee-und-Kuchen-7").ok, true);
  assert.equal(A.validatePassword("x".repeat(129) + "ab1").ok, false, "Obergrenze");
});

/* ---- Demo: Registrieren und Anmelden ---- */
test("Demo: Registrieren legt Konto an, Passwort steht nicht im Klartext im Speicher", async () => {
  const { storage, auth } = demo();
  const r = await auth.register("Max@Example.de", "Kaffee-und-Kuchen-7");
  assert.equal(r.ok, true);
  const raw = storage.getItem(A.ACCOUNTS_KEY);
  assert.ok(raw.includes("max@example.de"));
  assert.ok(!raw.includes("Kaffee"), "Klartext-Passwort darf nie gespeichert werden");
  const acc = JSON.parse(raw)["max@example.de"];
  assert.ok(acc.salt && acc.hash && acc.iter === 1000);
});

test("Demo: doppelte Registrierung wird abgelehnt (auch mit anderer Schreibweise)", async () => {
  const { auth } = demo();
  await auth.register("max@example.de", "Kaffee-und-Kuchen-7");
  const again = await auth.register("MAX@example.de", "Anderes-Passwort-99");
  assert.equal(again.ok, false);
  assert.equal(again.code, "exists");
});

test("Demo: Anmeldung klappt mit richtigem Passwort und erzeugt eine Sitzung mit Ablauf", async () => {
  const { storage, clock, auth } = demo();
  await auth.register("max@example.de", "Kaffee-und-Kuchen-7");
  const r = await auth.login("MAX@example.de", "Kaffee-und-Kuchen-7");
  assert.equal(r.ok, true);
  assert.equal(r.session.email, "max@example.de");
  assert.equal(r.session.exp, clock.now() + A.SESSION_MS);
  assert.deepEqual(A.getSession(storage, clock.now()).email, "max@example.de");
});

test("Demo: falsches Passwort und unbekannte E-Mail liefern dieselbe Antwort", async () => {
  const { auth } = demo();
  await auth.register("max@example.de", "Kaffee-und-Kuchen-7");
  const wrong = await auth.login("max@example.de", "Falsches-Passwort-1");
  const unknown = await auth.login("niemand@example.de", "Kaffee-und-Kuchen-7");
  assert.equal(wrong.ok, false);
  assert.equal(unknown.ok, false);
  assert.equal(wrong.message, unknown.message);
  assert.equal(wrong.code, "credentials");
});

test("Demo: nach 5 Fehlversuchen gesperrt, auch das richtige Passwort wird dann abgewiesen, später wieder möglich", async () => {
  const { clock, auth } = demo();
  await auth.register("max@example.de", "Kaffee-und-Kuchen-7");
  for (let i = 0; i < A.MAX_ATTEMPTS; i++) await auth.login("max@example.de", "falsch-falsch-1");
  const locked = await auth.login("max@example.de", "Kaffee-und-Kuchen-7");
  assert.equal(locked.ok, false);
  assert.equal(locked.code, "locked");
  clock.advance(A.LOCK_MS + 1);
  const ok = await auth.login("max@example.de", "Kaffee-und-Kuchen-7");
  assert.equal(ok.ok, true);
});

test("Demo: erfolgreiche Anmeldung setzt den Fehlversuchszähler zurück", async () => {
  const { auth } = demo();
  await auth.register("max@example.de", "Kaffee-und-Kuchen-7");
  for (let i = 0; i < A.MAX_ATTEMPTS - 1; i++) await auth.login("max@example.de", "falsch-falsch-1");
  assert.equal((await auth.login("max@example.de", "Kaffee-und-Kuchen-7")).ok, true);
  for (let i = 0; i < A.MAX_ATTEMPTS - 1; i++) await auth.login("max@example.de", "falsch-falsch-1");
  assert.equal((await auth.login("max@example.de", "Kaffee-und-Kuchen-7")).ok, true, "kein Rest vom ersten Durchgang");
});

test("Demo: zwei Konten mit gleichem Passwort haben unterschiedliche Hashes (Salt)", async () => {
  const { storage, auth } = demo();
  await auth.register("a@example.de", "Kaffee-und-Kuchen-7");
  await auth.register("b@example.de", "Kaffee-und-Kuchen-7");
  const acc = JSON.parse(storage.getItem(A.ACCOUNTS_KEY));
  assert.notEqual(acc["a@example.de"].hash, acc["b@example.de"].hash);
  assert.notEqual(acc["a@example.de"].salt, acc["b@example.de"].salt);
});

/* ---- Sitzung ---- */
test("Sitzung: abgelaufene, beschädigte und fremde Einträge werden verworfen", () => {
  const s = memStorage();
  const now = 5000;
  s.setItem(A.SESSION_KEY, JSON.stringify({ provider: "demo", email: "a@b.de", exp: 4000 }));
  assert.equal(A.getSession(s, now), null, "abgelaufen");
  assert.equal(s.getItem(A.SESSION_KEY), null, "wird entfernt");
  s.setItem(A.SESSION_KEY, "{kaputt");
  assert.equal(A.getSession(s, now), null);
  s.setItem(A.SESSION_KEY, JSON.stringify({ provider: "evil", email: "a@b.de", exp: 9999 }));
  assert.equal(A.getSession(s, now), null);
  s.setItem(A.SESSION_KEY, JSON.stringify({ provider: "supabase", email: "a@b.de", exp: 9999 }));
  assert.equal(A.getSession(s, now), null, "Supabase-Sitzung braucht ein Token");
  s.setItem(A.SESSION_KEY, JSON.stringify({ provider: "demo", email: "a@b.de", exp: 9999 }));
  assert.equal(A.getSession(s, now).email, "a@b.de");
});

test("Weiterleitung: nur Tools und Report sind erlaubte Ziele (kein offener Redirect)", () => {
  assert.equal(A.safeNext("report.html?y=2026"), "report.html?y=2026");
  assert.equal(A.safeNext("tools.html"), "tools.html");
  for (const bad of ["https://evil.example", "//evil.example", "javascript:alert(1)", "../x.html", "tools.html?next=1", "report.html?y=abcd", ""]) {
    assert.equal(A.safeNext(bad), "tools.html", bad);
  }
});

/* ---- Supabase-Client mit simuliertem Netzwerk ---- */
const jwt = (payload) => "x." + Buffer.from(JSON.stringify(payload)).toString("base64url") + ".y";
const fakeFetch = (routes) => async (url, init) => {
  const u = new URL(url);
  const hit = routes[`${init.method} ${u.pathname}${u.searchParams.get("grant_type") ? "?" + u.searchParams.get("grant_type") : ""}`];
  fakeFetch.calls.push({ url, init });
  if (!hit) return { ok: false, status: 404, json: async () => ({ msg: "nicht gefunden" }) };
  return { ok: hit.status < 400, status: hit.status, json: async () => hit.body };
};
fakeFetch.calls = [];
const sb = (routes, now = () => 1_000_000) => A.createSupabase({ url: "https://abc.supabase.co/", anonKey: "anon", fetch: fakeFetch(routes), now });

test("Supabase: URL muss https sein, Key ist Pflicht", () => {
  assert.throws(() => A.createSupabase({ url: "http://abc.supabase.co", anonKey: "k", fetch: () => {} }));
  assert.throws(() => A.createSupabase({ url: "https://abc.supabase.co", anonKey: "", fetch: () => {} }));
});

test("Supabase: Registrierung mit E-Mail-Bestätigung liefert keine Sitzung, sendet Anon-Key und Redirect", async () => {
  fakeFetch.calls.length = 0;
  const c = sb({ "POST /auth/v1/signup": { status: 200, body: { id: "u1", email: "max@example.de" } } });
  const r = await c.signUp("Max@Example.de", "Kaffee-und-Kuchen-7", "https://x.test/login.html");
  assert.equal(r.ok, true);
  assert.equal(r.needsConfirmation, true);
  const call = fakeFetch.calls[0];
  assert.equal(call.init.headers.apikey, "anon");
  assert.ok(call.url.includes("redirect_to="));
  assert.equal(JSON.parse(call.init.body).email, "max@example.de");
  assert.equal(call.init.credentials, "omit");
});

test("Supabase: Anmeldung liefert Sitzung mit Token und Ablauf aus dem JWT", async () => {
  const exp = Math.floor(1_000_000 / 1000) + 3600;
  const c = sb({ "POST /auth/v1/token?password": { status: 200, body: { access_token: jwt({ exp, email: "max@example.de" }), refresh_token: "r", expires_in: 3600, user: { email: "max@example.de" } } } });
  const r = await c.signIn("max@example.de", "irgendwas-langes-1");
  assert.equal(r.ok, true);
  assert.equal(r.session.provider, "supabase");
  assert.equal(r.session.exp, exp * 1000);
  assert.equal(r.session.refreshToken, "r");
});

test("Supabase: Fehlermeldungen werden verständlich übersetzt", async () => {
  const bad = sb({ "POST /auth/v1/token?password": { status: 400, body: { error_code: "invalid_credentials", msg: "Invalid login credentials" } } });
  assert.equal((await bad.signIn("max@example.de", "x-y-z-1234567")).code, "credentials");
  const unconf = sb({ "POST /auth/v1/token?password": { status: 400, body: { error_code: "email_not_confirmed", msg: "Email not confirmed" } } });
  assert.equal((await unconf.signIn("max@example.de", "x-y-z-1234567")).code, "unconfirmed");
  const exists = sb({ "POST /auth/v1/signup": { status: 422, body: { error_code: "user_already_exists", msg: "User already registered" } } });
  assert.equal((await exists.signUp("max@example.de", "Kaffee-und-Kuchen-7")).code, "exists");
  const down = A.createSupabase({ url: "https://abc.supabase.co", anonKey: "k", fetch: async () => { throw new Error("offline"); } });
  assert.equal((await down.signIn("max@example.de", "x-y-z-1234567")).code, "network");
});

test("Supabase: abgelaufener Token ergibt keine Sitzung", async () => {
  const c = sb({ "POST /auth/v1/token?password": { status: 200, body: { access_token: jwt({ exp: 1 }), expires_in: 3600 } } }, () => 5_000_000);
  const r = await c.signIn("max@example.de", "x-y-z-1234567");
  assert.equal(r.ok, false);
});

test("Supabase: Passwort-Zurücksetzen antwortet immer gleich (keine Konten-Abfrage)", async () => {
  const c = sb({ "POST /auth/v1/recover": { status: 400, body: { msg: "User not found" } } });
  assert.equal((await c.recover("niemand@example.de")).ok, true);
});

test("Link aus der Bestätigungs-Mail: Sitzung wird aus dem Hash gelesen, Fehler werden erkannt", () => {
  const c = sb({});
  const exp = Math.floor(1_000_000 / 1000) + 600;
  const ok = c.sessionFromHash(`#access_token=${jwt({ exp, email: "max@example.de" })}&refresh_token=r&expires_in=600&type=signup`);
  assert.equal(ok.ok, true);
  assert.equal(ok.type, "signup");
  assert.equal(ok.session.email, "max@example.de");
  assert.equal(c.sessionFromHash("#error=access_denied&error_description=Link+expired").ok, false);
  assert.equal(c.sessionFromHash("").none, true);
  assert.equal(c.sessionFromHash("#access_token=kaputt&expires_in=0").ok, false);
});

test("timingSafeEqual: gleiche, ungleiche und verschieden lange Texte", () => {
  assert.equal(A.timingSafeEqual("abc", "abc"), true);
  assert.equal(A.timingSafeEqual("abc", "abd"), false);
  assert.equal(A.timingSafeEqual("abc", "abcd"), false);
});
