// Kleiner Nachbau der Anmelde-Schnittstelle (Supabase GoTrue) für Tests, läuft im selben Prozess. Verhalten wie sellcheck-app/Tests/mock_supabase.py:
// Passwort mindestens 10 Zeichen, Bestätigung der E-Mail Pflicht, Code zum Zurücksetzen immer 123456, Antworten verraten keine Konten.
const http = require("node:http");
const KEY = "test-anon-key";

function start(clock) {
  const users = new Map();          // E-Mail -> { id, password, confirmed }
  const tokens = new Map(), refresh = new Map(), recovery = new Set();
  const log = [];
  let n = 0;
  const session = (email) => {
    const a = "acc-" + ++n, r = "ref-" + n;
    tokens.set(a, email); refresh.set(r, email);
    return { access_token: a, refresh_token: r, expires_in: 3600, expires_at: Math.floor(clock.now() / 1000) + 3600, token_type: "bearer", user: { id: users.get(email).id, email } };
  };
  const server = http.createServer((req, res) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      const url = new URL(req.url, "http://x"), p = url.pathname, q = url.searchParams;
      let b = {}; try { b = raw ? JSON.parse(raw) : {}; } catch { /* leer */ }
      log.push({ method: req.method, path: p, query: Object.fromEntries(q), body: b, auth: req.headers.authorization || "", apikey: req.headers.apikey || "" });
      const send = (st, o) => { res.writeHead(st, { "Content-Type": "application/json" }); res.end(o === undefined ? "" : JSON.stringify(o)); };
      if (p === "/mock/confirm") { const u = users.get(q.get("email")); if (u) u.confirmed = true; return send(200, { confirmed: !!u }); }
      if (req.headers.apikey !== KEY) return send(401, { message: "Invalid API key" });
      const me = tokens.get((req.headers.authorization || "").replace("Bearer ", ""));
      if (p === "/auth/v1/signup") {
        const email = b.email, pw = b.password || "";
        if (pw.length < 10) return send(422, { error_code: "weak_password" });
        if (users.has(email)) return send(200, { id: "x", email, identities: [] });
        users.set(email, { id: "u" + (users.size + 1) + "-0000-0000-0000-000000000000", password: pw, confirmed: false });
        return send(200, { id: users.get(email).id, email, identities: [{}] });
      }
      if (p === "/auth/v1/resend") return send(200, {});
      if (p === "/auth/v1/token" && q.get("grant_type") === "password") {
        const u = users.get(b.email);
        if (!u || u.password !== b.password) return send(400, { error_code: "invalid_credentials" });
        if (!u.confirmed) return send(400, { error_code: "email_not_confirmed" });
        return send(200, session(b.email));
      }
      if (p === "/auth/v1/token" && q.get("grant_type") === "refresh_token") {
        const e = refresh.get(b.refresh_token); refresh.delete(b.refresh_token);
        return e ? send(200, session(e)) : send(400, { error_code: "invalid_credentials" });
      }
      if (p === "/auth/v1/recover") { if (users.has(b.email)) recovery.add(b.email); return send(200, {}); }
      if (p === "/auth/v1/verify") {
        if (b.type === "recovery" && recovery.has(b.email) && b.token === "123456") { recovery.delete(b.email); return send(200, session(b.email)); }
        return send(403, { error_code: "otp_expired" });
      }
      if (p === "/auth/v1/user" && req.method === "PUT") {
        if (!me) return send(401, { message: "JWT expired" });
        if ((b.password || "").length < 10) return send(422, { error_code: "weak_password" });
        if (b.password === users.get(me).password) return send(422, { error_code: "same_password" });
        users.get(me).password = b.password; return send(200, { id: users.get(me).id, email: me });
      }
      if (p === "/auth/v1/logout") { tokens.delete((req.headers.authorization || "").replace("Bearer ", "")); return send(204); }
      send(404, { message: "nicht gefunden" });
    });
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({
    url: "http://127.0.0.1:" + server.address().port, key: KEY, log, users, tokens, refresh, close: () => new Promise((r) => { server.close(r); if (server.closeAllConnections) server.closeAllConnections(); }),
  })));
}
module.exports = { start, KEY };
