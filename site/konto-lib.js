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
  // Name nur bis 80 Zeichen vergleichen: Die Erkennung von Dateien und der Tools kürzt dort, ein langer Name soll beim Re-Import nicht doppelt werden.
  const dupKey = (r) => [String(r.name || "").replace(/\s+/g, " ").trim().toLowerCase().slice(0, 80), String(r.platform || "").toLowerCase(), r.sell_cents || 0, r.buy_cents || 0, r.cost_cents || 0, r.is_sold !== false ? 1 : 0, r.sale_date || "", r.buy_date || ""].join("|");

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

  /* ---------- Anzeige und Formular der Seite „Mein SellCheck“ (ohne DOM, Texte wie in der App) ---------- */
  const TABS = ["uebersicht", "artikel", "meldegrenze", "konto"];
  const tabFromHash = (h) => { const t = String(h == null ? "" : h).replace(/^#/, ""); return TABS.includes(t) ? t : "uebersicht"; };
  const PLATFORMS = [...T.REPORTED_PLATFORMS, "Sonstige"];
  const STALE_DAYS = 60;
  const euroFmt = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
  const euro = (c) => euroFmt.format((Number(c) || 0) / 100);
  const sales = (n) => (n === 1 ? "1 Verkauf" : n + " Verkäufe");

  /** Kalendertag als Zahl (lokal), aus „2026-05-01“ oder einem Zeitstempel. */
  function dayNum(x) {
    const m = typeof x === "string" && x.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    const d = m ? null : new Date(x);
    const y = m ? +m[1] : d.getFullYear(), mo = m ? +m[2] - 1 : d.getMonth(), da = m ? +m[3] : d.getDate();
    return Math.round(Date.UTC(y, mo, da) / 86400000);
  }
  /** Tage im Lager: ab Einkaufsdatum, sonst ab dem Anlegen (wie Article.stockDays). */
  const stockDays = (r, now) => Math.max(0, dayNum(now == null ? Date.now() : now) - dayNum(r.buy_date || r.created_at || now || Date.now()));
  function ageText(days) {
    if (days === 0) return "heute gekauft";
    if (days === 1) return "seit 1 Tag";
    if (days < STALE_DAYS) return "seit " + days + " Tagen";
    const mo = Math.floor(days / 30);
    return mo === 1 ? "seit 1 Monat" : "seit " + mo + " Monaten";
  }
  function stockStats(rows, now) {
    const s = { count: 0, valueCents: 0, stale: 0 };
    for (const r of rows) {
      if (r.deleted_at || r.is_sold !== false) continue;
      s.count++; s.valueCents += r.buy_cents || 0;
      if (stockDays(r, now) >= STALE_DAYS) s.stale++;
    }
    return s;
  }
  /** Gewinn eines verkauften Artikels in Cent, mit der Umsatzsteuer aus dem Profil (wie Article.profit). */
  function rowProfit(r, profile) {
    const v = vatSettings(profile);
    return (r.sell_cents || 0) - vatCents(r.sell_cents || 0, r.buy_cents || 0, v.rate, v.margin) - (r.buy_cents || 0) - (r.cost_cents || 0);
  }
  const sortKey = (r) => String(r.sale_date || r.buy_date || r.created_at || "").slice(0, 10);
  /** Neueste zuerst. */
  const sortRows = (rows) => rows.slice().sort((a, b) => (sortKey(a) < sortKey(b) ? 1 : sortKey(a) > sortKey(b) ? -1 : String(b.created_at || "") < String(a.created_at || "") ? -1 : String(b.created_at || "") > String(a.created_at || "") ? 1 : a.id < b.id ? -1 : 1));
  /** Suche nach Name und Plattform, Filter alle / Bestand / Verkauft. Im Bestand steht der Älteste oben. */
  function filterRows(rows, o, now) {
    const q = String((o && o.query) || "").trim().toLowerCase(), f = (o && o.filter) || "all";
    let list = sortRows(rows.filter((r) => !r.deleted_at));
    list = list.filter((r) => (f === "stock" ? r.is_sold === false : f === "sold" ? r.is_sold !== false : true));
    if (q) list = list.filter((r) => String(r.name || "").toLowerCase().includes(q) || String(r.platform || "").toLowerCase().includes(q));
    return f === "stock" ? list.sort((a, b) => stockDays(b, now) - stockDays(a, now)) : list;
  }
  /** Jahre zur Auswahl: alle mit Verkäufen plus das laufende, neuestes zuerst. */
  function yearsOf(rows, currentYear) {
    const set = new Set([currentYear]);
    for (const r of rows) if (!r.deleted_at && r.is_sold !== false && /^\d{4}/.test(r.sale_date || "")) set.add(+r.sale_date.slice(0, 4));
    return [...set].sort((a, b) => b - a);
  }
  const LEVEL_LABEL = { none: "Keine Meldung", green: "Weit entfernt", yellow: "Nähert sich", red: "Grenze erreicht" };
  const LEVEL_HINT = {
    red: "Eine der beiden Grenzen ist erreicht. Die Plattform meldet deine Verkäufe dieses Jahres voraussichtlich an das Bundeszentralamt für Steuern. Das ist noch keine Steuerforderung.",
    yellow: "Du näherst dich der Grenze. Plane Belege und Aufzeichnungen jetzt.",
    green: "Weit unter der Grenze.",
  };
  const unreportedText = (p) => sales(p.count) + ", " + euro(p.revenue) + ". Diese Plattform meldet nicht automatisch; Einnahmen gehören trotzdem in deine Unterlagen.";
  /** Verhältnis für die Balken, höchstens 100 %. */
  const ratioPct = (value, limit) => Math.max(0, Math.min(100, Math.floor((value * 100) / limit)));

  /** Bildgröße mit längster Kante höchstens max (Fotos werden vor dem Hochladen verkleinert). */
  function fitSize(w, h, max) {
    const m = max || 1400, k = Math.min(1, m / Math.max(w, h));
    return { width: Math.max(1, Math.round(w * k)), height: Math.max(1, Math.round(h * k)) };
  }

  /** Nach dem Speichern mit neuem oder entferntem Foto: Das alte darf nur weg, wenn die Zeile im Konto jetzt den neuen Pfad trägt (sonst hat ein anderes Gerät später geändert). */
  function photoCleanup(old, server, row) {
    const out = { remove: [], keep: [] };
    for (const o of old) (server && server[o.col] === (row[o.col] || null) ? out.remove : out.keep).push(o.path);
    return out;
  }

  /** Export aller Artikel als CSV, Spalten und Schutz vor Formeln wie CSVExport.journal der App (Semikolon, Komma, BOM). */
  function exportCsv(rows, profile) {
    const list = rows.filter((r) => !r.deleted_at).slice().sort((a, b) => (sortKey(a) < sortKey(b) ? -1 : sortKey(a) > sortKey(b) ? 1 : a.id < b.id ? -1 : 1));
    const t = T.cellT, n = T.cellN;
    const head = ["Datum", "Plattform", "Artikel", "Status", "Einkaufsdatum", "Einkaufspreis", "Verkaufspreis", "Nebenkosten", "Gewinn"];
    const body = list.map((r) => {
      const sold = r.is_sold !== false;
      return [t(T.deDate(sold ? r.sale_date : r.buy_date)), t(r.platform), t(r.name), t(sold ? "verkauft" : "im Bestand"), t(T.deDate(r.buy_date)),
        n(r.buy_cents || 0), n(sold ? r.sell_cents || 0 : 0), n(r.cost_cents || 0), n(sold ? rowProfit(r, profile) : 0)];
    });
    return T.toCsv(head, body);
  }
  const exportName = (now) => { const d = now || new Date(); return "sellcheck-artikel-" + new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10) + ".csv"; };
  const MAX_IMPORT_ROWS = 5000;

  const NUM_ERROR = "Das ist keine gültige Zahl. Beispiel: 12,50";
  /**
   * Formular zu Konto-Zeile (wie ArticleFormView.save). f: { sold, name, platform, buy, sell, cost, saleDate, hasBuyDate, buyDate, notes } mit Texten wie getippt.
   * existing: bisherige Zeile beim Ändern. Gibt { ok, errors } oder { ok, row } zurück. Fotos (photo_path, receipt_path) setzt die Seite danach.
   */
  function formToRow(f, existing, o, parseNum) {
    const money = (t) => { const s = String(t == null ? "" : t).trim(); if (!s) return { v: 0 }; const n = parseNum(s); return Number.isFinite(n) && n >= 0 ? { v: n } : { err: NUM_ERROR }; };
    const buy = money(f.buy), sell = money(f.sell), cost = money(f.cost), errors = {};
    const name = String(f.name == null ? "" : f.name).trim();
    if (!name) errors.name = "Gib dem Artikel einen Namen.";
    if (buy.err) errors.buy = buy.err;
    if (cost.err) errors.cost = cost.err;
    if (f.sold) { if (sell.err) errors.sell = sell.err; else if (!(sell.v > 0)) errors.sell = "Wie viel hast du für den Verkauf bekommen?"; }
    if (Object.keys(errors).length) return { ok: false, errors };
    const today = new Date((o.now || new Date()).getTime() - (o.now || new Date()).getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    const e = {
      id: existing ? existing.id : null, name, platform: f.platform, buy: buy.v, sell: f.sold ? sell.v : 0, cost: cost.v,
      status: f.sold ? "sold" : "stock", date: f.sold ? (day(f.saleDate) || today) : f.hasBuyDate ? day(f.buyDate) || "" : "",
      buyDate: f.hasBuyDate ? day(f.buyDate) || "" : "", notes: f.notes,
      receipt: existing && existing.receipt_no, ref: existing && existing.ref, kind: existing && existing.kind,
    };
    const row = entryToRow(e, o);
    row.photo_path = existing ? existing.photo_path || null : null;
    row.receipt_path = existing ? existing.receipt_path || null : null;
    return { ok: true, row };
  }

  return { TABS, tabFromHash, PLATFORMS, STALE_DAYS, euro, sales, stockDays, ageText, stockStats, rowProfit, sortRows, filterRows, yearsOf, LEVEL_LABEL, LEVEL_HINT, unreportedText, ratioPct, fitSize, formToRow, photoCleanup, exportCsv, exportName, MAX_IMPORT_ROWS, NUM_ERROR, rowToEntry, entryToRow, planTakeover, mergeChanges, nextCursor, since, vatCents, vatSettings, yearStats, checksum, storagePath, dupKey, UUID };
});
