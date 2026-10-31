// Kleiner Nachbau der Anmelde-Schnittstelle (Supabase GoTrue) für Tests, läuft im selben Prozess. Verhalten wie sellcheck-app/Tests/mock_supabase.py:
// Passwort mindestens 10 Zeichen, Bestätigung der E-Mail Pflicht, Code zum Zurücksetzen immer 123456, Antworten verraten keine Konten.
// Dazu Artikel (Tabelle articles samt Trigger-Regel aus 0003_sync.sql: ältere Änderung wird verworfen, updated_at setzt der Server),
// Profile, privater Foto-Ordner und /mock/remote (ein zweites Gerät ändert oder löscht) wie im Python-Nachbau der App.
const http = require("node:http");
const KEY = "test-anon-key";

function start(clock) {
  const users = new Map();          // E-Mail -> { id, password, confirmed }
  const tokens = new Map(), refresh = new Map(), recovery = new Set();
  const log = [];
  const articles = new Map();       // Nutzerkennung -> Map(Artikelkennung -> Zeile)
  const files = new Map();          // Pfad -> Buffer (Foto-Ordner, erster Teil = Nutzerkennung)
  const profiles = new Map();       // Nutzerkennung -> Profil
  const writes = { n: 0 };
  const fail = {};                  // z. B. fail.deleteAccount = 500: die Funktion scheitert
  let n = 0;
  const stamp = (later = 0) => new Date(clock.now() + later * 1000).toISOString();
  const tsOf = (v) => (v ? Date.parse(v) : -Infinity);
  const mineOf = (uid) => { if (!articles.has(uid)) articles.set(uid, new Map()); return articles.get(uid); };
  const DEFAULTS = { platform: "", buy_cents: 0, sell_cents: 0, cost_cents: 0, is_sold: true, sale_date: null, buy_date: null, notes: "", photo_path: null, receipt_path: null, receipt_no: null, ref: null, kind: null, deleted_at: null };
  /** Trigger articles_sync_guard: eine ältere Änderung (changed_at) überschreibt keine neuere; sonst gewinnt sie und updated_at ist jetzt. */
  function writeRow(mine, row) {
    const old = mine.get(row.id);
    if (old && tsOf(row.changed_at) < tsOf(old.changed_at)) return false;
    const next = { ...(old || { ...DEFAULTS, created_at: stamp() }), ...row };
    if (!next.changed_at) next.changed_at = stamp();
    next.updated_at = stamp(); mine.set(row.id, next); writes.n++;
    return true;
  }
  const FIELDS = ["id", "user_id", "name", "platform", "buy_cents", "sell_cents", "cost_cents", "is_sold", "sale_date", "buy_date", "notes", "photo_path", "receipt_path", "receipt_no", "ref", "kind", "created_at", "changed_at", "deleted_at"];
  const session = (email) => {
    const a = "acc-" + ++n, r = "ref-" + n;
    tokens.set(a, email); refresh.set(r, email);
    return { access_token: a, refresh_token: r, expires_in: 3600, expires_at: Math.floor(clock.now() / 1000) + 3600, token_type: "bearer", user: { id: users.get(email).id, email } };
  };
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const buf = Buffer.concat(chunks), raw = buf.toString("utf8");
      const url = new URL(req.url, "http://x"), p = url.pathname, q = url.searchParams;
      let b = {}; try { b = raw ? JSON.parse(raw) : {}; } catch { /* leer */ }
      log.push({ method: req.method, path: p, query: Object.fromEntries(q), body: p.startsWith("/storage/") ? {} : b, headers: req.headers, auth: req.headers.authorization || "", apikey: req.headers.apikey || "" });
      const send = (st, o) => { res.writeHead(st, { "Content-Type": "application/json" }); res.end(o === undefined ? "" : JSON.stringify(o)); };
      if (p === "/mock/confirm") { const u = users.get(q.get("email")); if (u) u.confirmed = true; return send(200, { confirmed: !!u }); }
      const uidOf = (email) => (email && users.get(email) ? users.get(email).id : null);
      if (p === "/mock/remote" && req.method === "POST") {   // ein zweites Gerät ändert oder löscht eine Zeile
        const mine = mineOf(uidOf(b.email)), row = { ...b.row };
        if (b.op === "delete") Object.assign(row, { deleted_at: stamp(), changed_at: stamp(b.later || 0) });
        else Object.assign(row, { changed_at: stamp(b.later || 0), deleted_at: null });
        if (!mine.has(row.id) && !row.name) return send(400, { message: "neue Zeile braucht einen Namen" });
        return send(200, { written: writeRow(mine, row) });
      }
      if (p === "/mock/state") {
        const uid = uidOf(q.get("email")), rows = [...mineOf(uid).values()];
        return send(200, { articles: rows.filter((r) => !r.deleted_at).length, deleted: rows.filter((r) => r.deleted_at).length, files: [...files.keys()].filter((k) => k.startsWith(uid + "/")).sort(), rows, writes: writes.n });
      }
      if (req.headers.apikey !== KEY) return send(401, { message: "Invalid API key" });
      const me = tokens.get((req.headers.authorization || "").replace("Bearer ", ""));
      if (p === "/auth/v1/signup") {
        const email = b.email, pw = b.password || "";
        if (pw.length < 10) return send(422, { error_code: "weak_password" });
        if (users.has(email)) return send(200, { id: "x", email, identities: [] });
        users.set(email, { id: "u" + (users.size + 1) + "-0000-0000-0000-000000000000", password: pw, confirmed: false });
        profiles.set(users.get(email).id, { first_name: "", last_name: "", seller_mode: "business", vat_mode: "small", vat_rate: 19 });
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
      if (p.startsWith("/storage/v1/object/")) {   // Foto-Ordner: Bytes, nicht JSON
        if (!me) return send(401, { message: "JWT expired" });
        const uid = uidOf(me);
        if (req.method === "DELETE" && p === "/storage/v1/object/photos") {
          for (const f of b.prefixes || []) if (f.startsWith(uid + "/")) files.delete(f);
          return send(200, []);
        }
        if (req.method === "POST" && p.startsWith("/storage/v1/object/photos/")) {
          const path = decodeURIComponent(p.slice("/storage/v1/object/photos/".length));
          if (!path.startsWith(uid + "/")) return send(403, { message: "new row violates row-level security policy" });
          if (req.headers["content-type"] !== "image/jpeg" || buf.length > 5 * 1024 * 1024) return send(415, { message: "mime type or size not allowed" });
          files.set(path, buf); return send(200, { Key: "photos/" + path });
        }
        if (req.method === "GET" && p.startsWith("/storage/v1/object/authenticated/photos/")) {
          const path = decodeURIComponent(p.slice("/storage/v1/object/authenticated/photos/".length));
          if (!path.startsWith(uid + "/") || !files.has(path)) return send(404, { message: "Object not found" });
          res.writeHead(200, { "Content-Type": "image/jpeg", "Content-Length": files.get(path).length }); return res.end(files.get(path));
        }
        return send(404, { message: "nicht gefunden" });
      }
      if (p === "/functions/v1/delete-account" && req.method === "POST") {   // wie die Funktion: Konto, Profil, Artikel und alle Fotos weg
        if (!me) return send(401, { message: "JWT expired" });
        if (fail.deleteAccount) return send(fail.deleteAccount, { message: "boom" });
        const uid = uidOf(me);
        articles.delete(uid); profiles.delete(uid);
        for (const k of [...files.keys()]) if (k.startsWith(uid + "/")) files.delete(k);
        for (const [t, e] of [...tokens]) if (e === me) tokens.delete(t);
        for (const [t, e] of [...refresh]) if (e === me) refresh.delete(t);
        users.delete(me);
        return send(200, { deleted: true });
      }
      if (p === "/rest/v1/profiles") {
        if (!me) return send(401, { message: "JWT expired" });
        const uid = uidOf(me);
        if ((q.get("id") || "").replace("eq.", "") !== uid) return send(200, []);
        if (req.method === "PATCH") { Object.assign(profiles.get(uid), b); return send(204); }
        return req.method === "GET" ? send(200, [profiles.get(uid)]) : send(404, { message: "nicht gefunden" });
      }
      if (p === "/rest/v1/articles") {
        if (!me) return send(401, { message: "JWT expired" });
        const uid = uidOf(me), mine = mineOf(uid);
        if (req.method === "GET") {
          let rows = [...mine.values()].sort((a, c) => tsOf(a.updated_at) - tsOf(c.updated_at) || (a.id < c.id ? -1 : 1));
          const idf = q.get("id");
          if (idf) { const ids = idf.startsWith("in.(") ? idf.slice(4, -1).split(",") : [idf.replace("eq.", "")]; rows = rows.filter((r) => ids.includes(r.id)); }
          if (q.get("updated_at")) rows = rows.filter((r) => tsOf(r.updated_at) >= tsOf(q.get("updated_at").replace("gte.", "")));
          const off = Number(q.get("offset") || 0), lim = Number(q.get("limit") || 100000);
          return send(200, rows.slice(off, off + lim));
        }
        if (req.method === "PATCH") {
          const id = (q.get("id") || "").replace("eq.", "");
          if (mine.has(id)) writeRow(mine, { ...b, id });
          return send(204);
        }
        if (req.method === "POST") {
          const items = Array.isArray(b) ? b : [b];
          for (const r of items) {
            if (r.user_id !== uid) return send(403, { message: "new row violates row-level security policy" });
            if (!(r.name && r.name.length >= 1 && r.name.length <= 120) || (r.platform || "").length > 40 || (r.notes || "").length > 1000 || Math.min(r.buy_cents || 0, r.sell_cents || 0, r.cost_cents || 0) < 0) return send(400, { code: "23514", message: "new row violates check constraint" });
          }
          for (const r of items) writeRow(mine, Object.fromEntries(FIELDS.filter((k) => k in r && k !== "user_id").map((k) => [k, r[k]])));
          return send(201);
        }
      }
      send(404, { message: "nicht gefunden" });
    });
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({
    url: "http://127.0.0.1:" + server.address().port, key: KEY, log, users, tokens, refresh, articles, files, profiles, writes, fail, close: () => new Promise((r) => { server.close(r); if (server.closeAllConnections) server.closeAllConnections(); }),
  })));
}
module.exports = { start, KEY };
