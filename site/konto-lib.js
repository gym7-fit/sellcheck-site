// Datenschicht für „Mein SellCheck“ im Browser (Konzept Laptop und Web, Phase 2). Ohne DOM und ohne Netz, testbar in Node.
// Browser: window.SCKonto. Die Artikel liegen im Konto (Tabelle articles, siehe sellcheck-app/supabase/migrations/0003_sync.sql).
// Der Browser arbeitet online: Das Konto ist die Quelle, Änderungen gehen sofort hoch, der Trigger dort lässt die spätere Änderung gewinnen.
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./tax-lib.js"));
  else root.SCKonto = factory(root.SCTax);
})(typeof self !== "undefined" ? self : this, function (T) {
  "use strict";

  const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
  const day = (s) => (typeof s === "string" && ISO_DAY.test(s.slice(0, 10)) ? s.slice(0, 10) : null);
  const cents = (x) => Math.max(0, Math.round((Number(x) || 0) * 100));
  const clip = (s, n) => String(s == null ? "" : s).trim().slice(0, n);

  /** Zeile aus dem Konto in einen Eintrag der Web-Tools (Euro, ISO-Tage), damit tax-lib.js damit rechnen kann. */
  function rowToEntry(r) {
    const sold = r.is_sold !== false;
    const e = {
      id: String(r.id),
      name: r.name || "Ohne Namen",
      platform: r.platform || "Sonstige",
      buy: (r.buy_cents || 0) / 100,
      sell: sold ? (r.sell_cents || 0) / 100 : 0,
      cost: (r.cost_cents || 0) / 100,
      status: sold ? "sold" : "stock",
      date: (sold ? day(r.sale_date) : day(r.buy_date)) || day(r.created_at) || "",
    };
    if (day(r.buy_date)) e.buyDate = day(r.buy_date);
    if (r.receipt_no) e.receipt = r.receipt_no;
    if (r.ref) e.ref = r.ref;
    if (r.kind) e.kind = r.kind;
    if (r.notes) e.notes = r.notes;
    return e;
  }

  /** Eintrag (aus den Web-Tools oder dem Formular) als Zeile fürs Konto. Grenzen wie die Prüfregeln der Datenbank. */
  function entryToRow(e, opt) {
    const o = opt || {};
    const sold = e.status !== "stock";
    const name = clip(e.name, 120) || "Ohne Namen";
    return {
      id: UUID.test(String(e.id || "")) ? String(e.id) : o.newId(),
      name,
      platform: clip(e.platform, 40),
      buy_cents: cents(e.buy),
      sell_cents: sold ? cents(e.sell) : 0,
      cost_cents: cents(e.cost),
      is_sold: sold,
      sale_date: sold ? day(e.date) : null,
      buy_date: day(e.buyDate) || (sold ? null : day(e.date)),
      notes: clip(e.notes, 1000),
      receipt_no: clip(e.receipt, 60) || null,
      ref: clip(e.ref, 200) || null,
      kind: clip(e.kind, 40) || null,
      changed_at: (o.now || new Date()).toISOString(),
      deleted_at: null,
    };
  }

  /** Inhalt ohne Kennung und Zeitstempel, zum Erkennen doppelter Einträge beim Übernehmen. */
  const dupKey = (r) => [String(r.name || "").trim().toLowerCase(), String(r.platform || "").toLowerCase(), r.sell_cents || 0, r.buy_cents || 0, r.cost_cents || 0, r.is_sold !== false ? 1 : 0, r.sale_date || "", r.buy_date || ""].join("|");

  /**
   * Einträge der Gratis-Tools ins Konto übernehmen. Was es dort schon gibt (gleicher Inhalt), wird nicht doppelt angelegt.
   * Zwei gleiche Verkäufe bleiben zwei, solange die Datei nicht mehr davon enthält als das Konto (wie in der App).
   */
  function planTakeover(entries, existingRows, opt) {
    const have = new Map();
    for (const r of existingRows) if (!r.deleted_at) have.set(dupKey(r), (have.get(dupKey(r)) || 0) + 1);
    const rows = [];
    let present = 0;
    for (const raw of entries) {
      const e = T.sanitizeEntry(raw);
      if (!e) continue;
      const row = entryToRow({ ...e, id: null }, opt);
      const k = dupKey(row);
      if (have.get(k) > 0) { have.set(k, have.get(k) - 1); present++; } else rows.push(row);
    }
    return { rows, present };
  }

  /** Neue Stände aus dem Konto übernehmen: das Konto gewinnt, gelöschte verschwinden. Gibt die neue Liste je Kennung zurück. */
  function mergeChanges(byId, changes) {
    const out = new Map(byId);
    for (const r of changes) { if (r.deleted_at) out.delete(r.id); else out.set(r.id, r); }
    return out;
  }

  /** Neuer Merker „bis hier abgeglichen“ und Abfragebeginn mit zwei Minuten Überlappung (wie Sync.swift). */
  const nextCursor = (prev, rows) => rows.reduce((m, r) => (r.updated_at && (!m || r.updated_at > m) ? r.updated_at : m), prev || null);
  const since = (cursor) => (cursor ? new Date(Date.parse(cursor) - 120000).toISOString() : null);

  /** Umsatzsteuer im Bruttopreis, ganze Cent (gleiche Regel wie VAT in der App und Math.round in tax-lib.js). */
  function vatCents(sell, buy, rate, margin) {
    if (!rate) return 0;
    const net = (g) => Math.round((g * 100) / (100 + rate));
    if (margin) { const d = sell - buy; return d > 0 ? d - net(d) : 0; }
    return sell - net(sell);
  }

  /** Steuer-Einstellungen aus dem Profil: Umsatzsteuer nur bei gewerblich und Regel- oder Differenzbesteuerung. */
  function vatSettings(p) {
    const business = (p && p.seller_mode) !== "private";
    const mode = business ? (p && p.vat_mode) || "small" : "small";
    return { rate: mode === "regular" ? (p.vat_rate === 7 ? 7 : 19) : mode === "margin" ? 19 : 0, margin: mode === "margin" };
  }

  /**
   * Übersicht eines Jahres wie in der App: Gewinn je verkauftem Artikel (Verkauf minus Umsatzsteuer, Einkauf, Kosten),
   * Bestand mit gebundenem Geld, Meldegrenze je Plattform über SCTax.meldeStatus (eine Quelle für alle Seiten).
   */
  function yearStats(rows, year, profile) {
    const v = vatSettings(profile);
    const y = String(year);
    const s = { revenue: 0, profit: 0, vat: 0, sold: 0, stock: 0, stockValue: 0, platforms: [] };
    const plat = new Map();
    for (const name of T.REPORTED_PLATFORMS) plat.set(name, { platform: name, count: 0, revenue: 0 });
    for (const r of rows) {
      if (r.deleted_at) continue;
      if (r.is_sold === false) { s.stock++; s.stockValue += r.buy_cents || 0; continue; }
      if (!(r.sell_cents > 0) || String(r.sale_date || "").slice(0, 4) !== y) continue;
      const vat = vatCents(r.sell_cents, r.buy_cents || 0, v.rate, v.margin);
      s.sold++; s.revenue += r.sell_cents; s.vat += vat;
      s.profit += r.sell_cents - vat - (r.buy_cents || 0) - (r.cost_cents || 0);
      const p = plat.get(r.platform) || { platform: r.platform || "Sonstige", count: 0, revenue: 0 };
      p.count++; p.revenue += r.sell_cents; plat.set(p.platform, p);
    }
    s.platforms = [...plat.values()].map((p) => {
      const reported = T.REPORTED_PLATFORMS.includes(p.platform);
      const st = T.meldeStatus(p.count, p.revenue);
      return { ...p, reported, level: reported ? st.level : "none", percent: st.percent };
    }).sort((a, b) => b.revenue - a.revenue || a.platform.localeCompare(b.platform));
    return s;
  }

  /** Prüfsumme und Pfad im privaten Foto-Ordner, gleich wie Backup.checksum und Backup.storagePath in der App. */
  function checksum(bytes) {
    let h = 0x811c9dc5;
    for (let i = 0; i < bytes.length; i++) { h ^= bytes[i]; h = Math.imul(h, 0x01000193) >>> 0; }
    return h.toString(16).padStart(8, "0");
  }
  const storagePath = (userId, articleId, kind, sum) => `${String(userId).toLowerCase()}/${String(articleId).toLowerCase()}-${kind}-${sum}.jpg`;

  return { rowToEntry, entryToRow, planTakeover, mergeChanges, nextCursor, since, vatCents, vatSettings, yearStats, checksum, storagePath, dupKey, UUID };
});
