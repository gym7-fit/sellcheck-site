// Netzschicht für „Mein SellCheck“: Artikel, Profil und Fotos aus dem Konto laden und zurückschreiben (Konzept Laptop und Web, Phase 2).
// Ohne DOM, testbar in Node. Browser: window.SCKontoNet. Vorbild: sellcheck-app/SellCheck/Auth/BackupService.swift.
// Das Konto ist die Quelle, Änderungen gehen sofort hoch, der Trigger in 0003_sync.sql lässt die spätere Änderung (changed_at) gewinnen.
// Jede Funktion gibt { ok: true, ... }, { ok: false, message } oder { ok: false, expired: true } zurück (abgelaufen: Seite geht auf anmelden.html#abgelaufen).
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./konto-lib.js"), require("./auth-lib.js"));
  else root.SCKontoNet = factory(root.SCKonto, root.SCAuth);
})(typeof self !== "undefined" ? self : this, function (K, A) {
  "use strict";

  const MAX_PHOTO = 5 * 1024 * 1024;
  const KINDS = ["foto", "beleg"];
  const EXPIRED = { ok: false, expired: true };
  const PROFILE_FIELDS = "first_name,last_name,seller_mode,vat_mode,vat_rate";
  const chunked = (a, n) => { const out = []; for (let i = 0; i < a.length; i += n) out.push(a.slice(i, i + n)); return out; };
  const iso = (d) => (d instanceof Date ? d : new Date(d == null ? Date.now() : d)).toISOString();

  function createStore(opts) {
    const base = String(opts.url || "").replace(/\/+$/, "");
    if (!/^https?:\/\/[a-z0-9.:\-]+$/i.test(base)) throw new Error("Adresse des Dienstes fehlt oder ist ungültig.");
    const key = String(opts.anonKey || "");
    if (!key) throw new Error("Öffentlicher Schlüssel fehlt.");
    if (!opts.client || typeof opts.client.getSession !== "function") throw new Error("Zugang (Anmelde-Client) fehlt.");
    const client = opts.client;
    const doFetch = opts.fetch || (typeof fetch !== "undefined" ? fetch.bind(globalThis) : null);
    const pageSize = opts.pageSize || 1000, batchSize = opts.batchSize || 500;

    const failure = (status) => ({
      ok: false,
      message: status === 0 ? A.NETWORK : status === 429 || status >= 500 ? A.errorMessage(status, null, "other") : "Das hat nicht geklappt (Fehler " + status + "). Versuche es später noch einmal.",
    });

    /** Eine Anfrage mit dem Zugangs-Token. Bei 401 einmal die Sitzung erneuern und wiederholen, sonst { expired }. Antwort: { status, ok, data|bytes, session }. */
    async function call(path, { method = "GET", headers = {}, json, body } = {}) {
      const send = async (session) => {
        const h = { apikey: key, Authorization: "Bearer " + session.accessToken, ...headers };
        let payload = body;
        if (json !== undefined) { h["Content-Type"] = "application/json"; payload = JSON.stringify(json); }
        try {
          const res = await doFetch(base + path, { method, headers: h, body: payload, credentials: "omit", referrerPolicy: "no-referrer" });
          return { status: res.status, ok: res.ok, res, session };
        } catch { return { status: 0, ok: false, session }; }
      };
      let g = await client.getSession();
      if (g.expired || !g.session) return g.offline ? { status: 0, ok: false } : { expired: true };
      let r = await send(g.session);
      if (r.status === 401) {
        g = await client.getSession({ force: true });
        if (g.expired || !g.session) return g.offline ? { status: 0, ok: false } : { expired: true };
        r = await send(g.session);
        if (r.status === 401) return { expired: true };
      }
      return r;
    }
    const readJson = async (r) => { try { return await r.res.json(); } catch { return null; } };
    const wrap = (r, done) => (r.expired ? EXPIRED : r.ok ? done(r) : failure(r.status));

    /** Pfad im privaten Foto-Ordner: muss mit der eigenen Nutzerkennung beginnen, nur einfache Zeichen, keine Umwege. */
    const ownPath = (uid, p) => typeof p === "string" && p.startsWith(String(uid).toLowerCase() + "/") && /^[a-z0-9\-_.\/]+$/.test(p) && !p.includes("..") && !p.includes("//") && !p.endsWith("/");
    const objectUrl = (p, prefix) => "/storage/v1/object/" + prefix + "photos/" + p.split("/").map(encodeURIComponent).join("/");
    const userIdOf = async () => { const g = await client.getSession(); return g.session ? g.session.userId : null; };

    async function fetchRows(since) {
      const out = [];
      const filter = since ? "&updated_at=gte." + encodeURIComponent(since) : "";
      for (let offset = 0; ; offset += pageSize) {
        const r = await call("/rest/v1/articles?select=*&order=updated_at.asc,id.asc&limit=" + pageSize + "&offset=" + offset + filter);
        if (r.expired) return EXPIRED;
        if (!r.ok) return failure(r.status);
        const rows = await readJson(r);
        if (!Array.isArray(rows)) return failure(500);
        for (const x of rows) out.push({ ...x, id: String(x.id).toLowerCase() });
        if (rows.length < pageSize) break;
      }
      return { ok: true, rows: out };
    }

    return {
      /** Alle Artikel, seitenweise. Gelöschte sind nicht dabei. Merker für loadChanges. */
      async loadAll() {
        const r = await fetchRows(null);
        return r.ok ? { ok: true, rows: r.rows.filter((x) => !x.deleted_at), cursor: K.nextCursor(null, r.rows) } : r;
      },

      /** Änderungen seit dem Merker (120 s Überlappung), auch Löschungen. Zusammenführen: SCKonto.mergeChanges. */
      async loadChanges(cursor) {
        const r = await fetchRows(K.since(cursor));
        return r.ok ? { ok: true, rows: r.rows, cursor: K.nextCursor(cursor, r.rows) } : r;
      },

      /** Zeilen speichern (Upsert, höchstens batchSize je Anfrage). Der Zeitstempel updated_at gehört dem Server. */
      async save(rows) {
        const uid = await userIdOf();
        if (!uid) return EXPIRED;
        let saved = 0;
        for (const chunk of chunked(rows, batchSize)) {
          const body = chunk.map((x) => { const o = { ...x, user_id: uid }; delete o.updated_at; return o; });
          const r = await call("/rest/v1/articles?on_conflict=user_id,id", { method: "POST", headers: { Prefer: "resolution=merge-duplicates,return=minimal" }, json: body });
          if (r.expired) return EXPIRED;
          if (!r.ok) return { ...failure(r.status), saved };
          saved += chunk.length;
        }
        return { ok: true, saved };
      },

      /** Löschen = Markierung. Endgültig gelöscht wird nichts (das macht der Server nach der Aufbewahrungszeit). */
      async remove(id, now) {
        if (!K.UUID.test(String(id).toLowerCase())) return { ok: false, message: "Dieser Artikel ist ungültig." };
        const t = iso(now);
        const r = await call("/rest/v1/articles?id=eq." + String(id).toLowerCase(), { method: "PATCH", headers: { Prefer: "return=minimal" }, json: { deleted_at: t, changed_at: t } });
        return wrap(r, () => ({ ok: true }));
      },

      async loadProfile() {
        const uid = await userIdOf();
        if (!uid) return EXPIRED;
        const r = await call("/rest/v1/profiles?id=eq." + encodeURIComponent(uid) + "&select=" + PROFILE_FIELDS);
        if (r.expired) return EXPIRED;
        if (!r.ok) return failure(r.status);
        const rows = await readJson(r);
        return { ok: true, profile: Array.isArray(rows) && rows[0] ? rows[0] : null };
      },

      /** Foto hochladen: nur JPEG bis 5 MB, Pfad wie in der App. Rückgabe: der Pfad. */
      async uploadPhoto(articleId, kind, bytes) {
        const data = bytes instanceof ArrayBuffer ? new Uint8Array(bytes) : bytes;
        if (!KINDS.includes(kind) || !K.UUID.test(String(articleId).toLowerCase())) return { ok: false, message: "Dieses Foto passt zu keinem Artikel." };
        if (!(data instanceof Uint8Array) || data.length < 3 || data[0] !== 0xff || data[1] !== 0xd8 || data[2] !== 0xff) return { ok: false, message: "Nur Fotos im JPEG-Format sind möglich." };
        if (data.length > MAX_PHOTO) return { ok: false, message: "Das Foto ist größer als 5 MB." };
        const uid = await userIdOf();
        if (!uid) return EXPIRED;
        const path = K.storagePath(uid, articleId, kind, K.checksum(data));
        const r = await call(objectUrl(path, ""), { method: "POST", headers: { "Content-Type": "image/jpeg", "x-upsert": "true" }, body: data });
        return wrap(r, () => ({ ok: true, path }));
      },

      /** Foto holen (Blob). Adressen für die Anzeige und revokeObjectURL macht die Seite. */
      async photoBlob(path) {
        const uid = await userIdOf();
        if (!uid) return EXPIRED;
        if (!ownPath(uid, path)) return { ok: false, message: "Dieses Foto kann nicht geladen werden." };
        const r = await call(objectUrl(path, "authenticated/"));
        if (r.expired) return EXPIRED;
        if (!r.ok) return failure(r.status);
        try { return { ok: true, blob: await r.res.blob() }; } catch { return failure(0); }
      },

      /** Fotos löschen. Fremde Pfade werden übersprungen und nie angefragt. */
      async deletePhotos(paths) {
        const uid = await userIdOf();
        if (!uid) return EXPIRED;
        const own = [...new Set(paths)].filter((p) => ownPath(uid, p));
        for (const chunk of chunked(own, 50)) {
          const r = await call("/storage/v1/object/photos", { method: "DELETE", json: { prefixes: chunk } });
          if (r.expired) return EXPIRED;
          if (!r.ok) return failure(r.status);
        }
        return { ok: true, deleted: own.length, skipped: new Set(paths).size - own.length };
      },
    };
  }

  return { createStore, MAX_PHOTO };
});
