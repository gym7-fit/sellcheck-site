// Reine Logik des Datei-Imports (ohne DOM), damit sie im Browser UND in Node getestet werden kann.
// Browser: window.SCParse   |   Node: require("./parse-lib.js")
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SCParse = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const MAX_ROWS = 20000;
  const MAX_NAME = 80;

  const norm = (s) =>
    String(s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/ß/g, "ss")
      .replace(/[^a-z0-9]/g, "");

  function decode(buf) {
    let txt;
    try {
      txt = new TextDecoder("utf-8", { fatal: true }).decode(buf);
    } catch {
      txt = new TextDecoder("windows-1252").decode(buf);
    }
    return txt.replace(/^﻿/, "");
  }

  /* ---------- CSV ---------- */
  function detectDelimiter(text) {
    const lines = text.split(/\r?\n/).filter((l) => l.trim()).slice(0, 40);
    let best = { d: ";", score: -1 };
    for (const d of [";", ",", "\t", "|"]) {
      const hist = new Map();
      for (const l of lines) {
        let n = 0;
        let q = false;
        for (const ch of l) {
          if (ch === '"') q = !q;
          else if (ch === d && !q) n++;
        }
        if (n > 0) hist.set(n, (hist.get(n) || 0) + 1);
      }
      for (const [n, freq] of hist) {
        const score = freq * 100 + n;
        if (score > best.score) best = { d, score };
      }
    }
    return best.d;
  }

  function parseCSV(text, d) {
    const rows = [];
    let row = [];
    let field = "";
    let q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"') {
          if (text[i + 1] === '"') {
            field += '"';
            i++;
          } else q = false;
        } else field += c;
      } else if (c === '"' && field === "") q = true;
      else if (c === d) {
        row.push(field);
        field = "";
      } else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(field);
        field = "";
        if (row.some((x) => x.trim() !== "")) rows.push(row);
        row = [];
        if (rows.length > MAX_ROWS + 60) return rows;
      } else field += c;
    }
    row.push(field);
    if (row.some((x) => x.trim() !== "")) rows.push(row);
    return rows;
  }

  function findHeader(rows) {
    const hist = new Map();
    rows.slice(0, 80).forEach((r) => hist.set(r.length, (hist.get(r.length) || 0) + 1));
    let width = 1;
    let top = 0;
    for (const [w, f] of hist) if (w >= 2 && (f > top || (f === top && w > width))) { width = w; top = f; }
    for (let i = 0; i < Math.min(rows.length, 60); i++) {
      const r = rows[i];
      const filled = r.filter((c) => c.trim() !== "");
      if (r.length === width && filled.length >= Math.min(3, width)) {
        const numeric = filled.filter((c) => !isNaN(parseNum(c))).length;
        if (numeric / filled.length < 0.3) return i;
      }
    }
    return 0;
  }

  /* ---------- Zahlen & Datum ---------- */
  function parseNum(v) {
    if (v == null) return NaN;
    let s = String(v).trim();
    if (!s) return NaN;
    const neg = /^\(.*\)$/.test(s) || /-/.test(s);
    s = s.replace(/[^\d.,]/g, "");
    if (!/\d/.test(s)) return NaN;
    const dots = (s.match(/\./g) || []).length;
    const commas = (s.match(/,/g) || []).length;
    if (dots && commas) {
      const dec = s.lastIndexOf(",") > s.lastIndexOf(".") ? "," : ".";
      const th = dec === "," ? "." : ",";
      s = s.split(th).join("").replace(dec, ".");
    } else if (commas || dots) {
      const sep = commas ? "," : ".";
      const count = commas || dots;
      const parts = s.split(sep);
      const last = parts[parts.length - 1];
      if (count > 1 || (last.length === 3 && parts[0].length <= 3 && parts[0] !== "0")) s = parts.join("");
      else s = parts.join(".");
    }
    const n = parseFloat(s);
    return Number.isFinite(n) ? (neg ? -n : n) : NaN;
  }

  const MONTHS = Object.assign(Object.create(null), { jan: 1, feb: 2, mar: 3, apr: 4, mai: 5, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, okt: 10, oct: 10, nov: 11, dez: 12, dec: 12 });
  function validDate(y, m, d) {
    if (y < 2000 || y > 2100 || m < 1 || m > 12 || d < 1 || d > 31) return null;
    const dt = new Date(Date.UTC(y, m - 1, d));
    if (dt.getUTCMonth() !== m - 1) return null;
    return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  }
  // Zeitstempel mit Zeitzone (z. B. Amazon „2026-12-31T23:30:00+00:00“) auf den Kalendertag in Deutschland umrechnen,
  // sonst landet ein Verkauf in der Silvesternacht im falschen Jahr. Ohne Zeitzone bleibt das Datum, wie es dasteht.
  const BERLIN_DAY = (() => {
    try { return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin", year: "numeric", month: "2-digit", day: "2-digit" }); } catch { return null; }
  })();
  function berlinDay(s) {
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})$/i);
    if (!m || !BERLIN_DAY) return null;
    const off = m[7].toUpperCase() === "Z" ? "Z" : m[7].replace(/^([+-]\d{2}):?(\d{2})$/, "$1:$2");
    const t = Date.parse(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6] || "00"}${off}`);
    if (!Number.isFinite(t) || !validDate(+m[1], +m[2], +m[3])) return null;
    const out = BERLIN_DAY.format(new Date(t));
    const [y, mo, d] = out.split("-").map(Number);
    return validDate(y, mo, d);
  }

  function parseDate(v, order) {
    const s = String(v || "").trim();
    if (!s) return null;
    const tz = berlinDay(s);
    if (tz) return tz;
    let m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
    if (m) return validDate(+m[1], +m[2], +m[3]);
    m = s.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})/);
    if (m) {
      const a = +m[1], b = +m[2];
      let y = +m[3];
      if (y < 100) y += 2000;
      return order === "mdy" ? validDate(y, a, b) : validDate(y, b, a);
    }
    m = s.match(/^(\d{1,2})\.?\s+([A-Za-zÄäÖöÜü]+)\.?,?\s+(\d{4})/);
    if (m) {
      const mo = MONTHS[norm(m[2]).slice(0, 3)];
      if (mo) return validDate(+m[3], mo, +m[1]);
    }
    m = s.match(/^([A-Za-zÄäÖöÜü]+)\.?\s+(\d{1,2}),?\s+(\d{4})/);
    if (m) {
      const mo = MONTHS[norm(m[1]).slice(0, 3)];
      if (mo) return validDate(+m[3], mo, +m[2]);
    }
    return null;
  }

  // Liefert {order, ambiguous}. ambiguous = aus den Daten nicht eindeutig (z. B. alle Tage <= 12).
  function guessDateOrder(values) {
    let dmy = false, mdy = false, seen = 0, slashes = 0;
    for (const v of values.slice(0, 300)) {
      const m = String(v || "").trim().match(/^(\d{1,2})([./-])(\d{1,2})[./-](\d{2,4})/);
      if (!m) continue;
      seen++;
      if (m[2] === "/") slashes++;
      if (+m[1] > 12) dmy = true;
      if (+m[3] > 12) mdy = true;
    }
    if (mdy && !dmy) return { order: "mdy", ambiguous: false };
    if (dmy && !mdy) return { order: "dmy", ambiguous: false };
    const order = slashes > seen / 2 ? "mdy" : "dmy";
    return { order, ambiguous: seen > 0 };
  }

  /* ---------- Spalten raten (über Begriffe, nicht über feste Namen) ---------- */
  // norm() entfernt Umlaute (ä -> a), deshalb enthalten die Regeln beide Schreibweisen.
  const RULES = {
    date: { want: [/transaktionserstellungsdatum|transactioncreationdate/, /^(sale|verkaufs|bestell|order|purchase|kauf|buchungs)?(date|datum|tag)$/, /datum|date|buchungstag|zeitpunkt/], skip: /payout|auszahlung|versand|ship|valuta|wertstellung|delivery|lieferung|update|geandert|geaendert|modified/ },
    amount: { want: [/^(brutto|gross)(betrag|amount)?$/, /bruttobetrag|grossamount/, /ordervalue|bestellwert|artikelpreis|itemprice|verkaufspreis|itemsubtotal|zwischensumme|subtotal/, /^(betrag|amount)$/, /^(preis|price|umsatz)$/, /betrag|amount/], skip: /netto|net|gebuhr|fee|steuer|tax|versand|ship|rabatt|discount|balance|saldo|payout|auszahlung|currency|wahrung|waehrung/ },
    name: { want: [/artikelbezeichnung|itemtitle|listingtitle|itemname|artikelname/, /^(artikel|titel|title|produkt|product|item)$/, /artikel|titel|title|produkt|product|beschreibung|description|verwendungszweck|buchungstext|betreff/], skip: /nummer|number|id$|^id|kaufer|kaeufer|buyer|ship|empfanger|empfaenger|adresse|address|steuer|tax/ },
    fees: { want: [/endwertgebuhr|finalvaluefee|transaktionsgebuhr|transactionfee|cardprocessingfee|processingfee|verkaufsgebuhr|sellingfee|provision|commission|gebuhr|fee/], skip: /^$/ },
    orderId: { want: [/bestellnummer|orderid|ordernumber|bestellid|transaktionscode|transaktionsid|transactionid|belegnummer|referenz|reference/], skip: /^$/ },
    type: { want: [/^(typ|type|transaktionsart|transactiontype|buchungsart|art)$/, /^(status|kategorie|category)$/], skip: /^$/ },
    plat: { want: [/plattform|platform|marketplace|vertriebskanal|saleschannel|kanal/], skip: /^$/ },
    buy: { want: [/^(einkauf|einkaufspreis|ekpreis|ek|anschaffungskosten|purchaseprice|costofgoods|cogs)$/], skip: /^$/ },
  };

  function guessColumns(headers) {
    const n = headers.map(norm);
    const used = new Set();
    const pick = (key) => {
      const rule = RULES[key];
      for (const rx of rule.want) {
        for (let i = 0; i < n.length; i++) {
          if (used.has(i) || !n[i]) continue;
          if (rx.test(n[i]) && !rule.skip.test(n[i])) return i;
        }
      }
      return -1;
    };
    const m = {};
    for (const key of ["date", "amount", "type", "name", "orderId"]) {
      m[key] = pick(key);
      if (m[key] >= 0) used.add(m[key]);
    }
    m.plat = pick("plat");
    m.buy = pick("buy");
    m.ship = -1; // bewusst nie geraten: Versand in Exporten ist meist das, was der Käufer zahlt
    m.fees = [];
    n.forEach((h, i) => {
      if (used.has(i) || !h) return;
      if (RULES.fees.want.some((rx) => rx.test(h)) && !/netto|net$/.test(h)) m.fees.push(i);
    });
    // Gibt es eine Summenspalte neben Einzelposten, nur die Summe nehmen (sonst doppelt gezählt).
    if (m.fees.length > 1) {
      const total = m.fees.find((i) => /gesamt|total|insgesamt|summe/.test(n[i]));
      if (total !== undefined) m.fees = [total];
    }
    m.state = -1;
    return m;
  }

  const OWN_HEADERS = ["datum", "artikel", "plattform", "status", "einkauf", "verkauf", "kosten"];
  function isOwnFormat(headers) {
    const n = headers.map(norm);
    return OWN_HEADERS.every((k) => n.includes(k));
  }
  function ownMapping(headers) {
    const n = headers.map(norm);
    return {
      date: n.indexOf("datum"), name: n.indexOf("artikel"), plat: n.indexOf("plattform"), state: n.indexOf("status"),
      buy: n.indexOf("einkauf"), amount: n.indexOf("verkauf"), fees: [n.indexOf("kosten")], ship: -1, orderId: -1, type: -1,
      // optionale Spalten neuerer Exporte (ältere Dateien ohne diese Spalten bleiben importierbar)
      buyDate: n.indexOf("einkaufsdatum"), receipt: n.indexOf("belegnr"), kind: n.indexOf("art"),
    };
  }

  // Andere Währungen als EUR erkennen (werden nicht umgerechnet).
  function detectCurrencies(headers, rows) {
    const col = headers.findIndex((h) => /^(currency|currencycode|wahrung|waehrung|wahrungscode|waehrungscode)$/.test(norm(h)));
    if (col < 0) return [];
    const set = new Set();
    for (const r of rows) {
      const v = String(r[col] || "").trim().toUpperCase();
      if (v && v !== "EUR" && v !== "€") set.add(v);
    }
    return [...set].slice(0, 5);
  }

  /* ---------- Duplikat-Index ---------- */
  const plainKey = (platform, date, name, sell) => `${platform}|${date}|${name}|${Number(sell).toFixed(2)}`;

  function indexExisting(sales) {
    const refs = new Set();
    const plainAll = new Map();
    const plainNoRef = new Map();
    const bump = (map, k) => map.set(k, (map.get(k) || 0) + 1);
    for (const s of sales) {
      const k = plainKey(s.platform, s.date, s.name, s.sell);
      bump(plainAll, k);
      if (s.ref) refs.add(s.ref);
      else bump(plainNoRef, k);
    }
    return { refs, plainAll, plainNoRef };
  }

  const TYPE_BAD = /erstatt|refund|storn|cancel|gebuhr|fee|auszahl|payout|withdraw|transfer|abbuch|versandetikett|shippinglabel|dispute|reversal|chargeback|ruckbuch|rueckbuch|ruckzahl|rueckzahl|reklam/;
  const defaultTypeChecked = (value) => !TYPE_BAD.test(norm(value));

  /* ---------- Zeilen -> Einträge ---------- */
  // opts: { dateOrder, platform ("" = automatisch), positiveOnly, keywords[], own, typeChecked(Map), known, platforms[] }
  function buildEntries(rows, m, opts) {
    const platforms = opts.platforms || [];
    const known = opts.known || { refs: new Set(), plainAll: new Map(), plainNoRef: new Map() };
    const kws = (opts.keywords || []).map(norm).filter(Boolean);
    const fileSeenPlain = new Map();
    const fileRefs = new Set();
    const stats = { total: rows.length, ok: 0, noDate: 0, noAmount: 0, filtered: 0, keyword: 0, dup: 0 };
    const entries = [];

    const platformFromText = (text) => {
      const t = norm(text);
      for (const p of platforms) {
        const key = norm(p.split(" ")[0]);
        if (key.length >= 4 && t.includes(key)) return p;
      }
      return null;
    };

    for (const r of rows) {
      const get = (i) => (i >= 0 && i < r.length ? r[i] : "");
      if (m.type >= 0 && opts.typeChecked && opts.typeChecked.get((get(m.type) || "").trim()) === false) { stats.filtered++; continue; }
      if (kws.length) {
        const t = norm(r.join(" "));
        if (!kws.some((k) => t.includes(k))) { stats.keyword++; continue; }
      }
      const date = parseDate(get(m.date), opts.dateOrder);
      if (!date) { stats.noDate++; continue; }
      const isStock = !!opts.own && m.state >= 0 && /bestand|stock/i.test(get(m.state));
      let sell = parseNum(get(m.amount));
      if (isStock) sell = 0;
      if (!isStock && (!Number.isFinite(sell) || sell === 0 || (opts.positiveOnly && sell < 0))) { stats.noAmount++; continue; }
      if (!Number.isFinite(sell)) sell = 0;

      let cost = 0;
      (m.fees || []).forEach((i) => {
        if (i >= 0) { const f = parseNum(get(i)); if (Number.isFinite(f)) cost += Math.abs(f); }
      });
      if (m.ship >= 0) { const sh = parseNum(get(m.ship)); if (Number.isFinite(sh)) cost += Math.abs(sh); }
      const hasBuyCol = m.buy >= 0;
      const buy = hasBuyCol ? Math.abs(parseNum(get(m.buy)) || 0) : 0;

      let platform = opts.platform;
      if (!platform) {
        const col = (get(m.plat) || "").trim();
        const hit = platforms.find((p) => norm(p) === norm(col));
        platform = hit || platformFromText(col) || platformFromText(r.join(" ")) || "Sonstige";
      }
      let name = String(get(m.name) || "").trim() || String(get(m.orderId) || "").trim() || "Import";
      name = name.replace(/\s+/g, " ").replace(/^'(?=[=+\-@])/, "").slice(0, MAX_NAME);
      const oid = String(get(m.orderId) || "").trim();
      const plain = plainKey(platform, date, name, sell);
      const ref = oid ? `${platform}|${oid}|${sell.toFixed(2)}|${name}` : plain;

      let dup;
      if (oid) {
        dup = known.refs.has(ref) || fileRefs.has(ref) || (known.plainNoRef.get(plain) || 0) > 0;
        fileRefs.add(ref);
      } else {
        // Gleiche Zeilen ohne Bestellnummer sind legitim möglich (zwei identische Verkäufe am selben Tag):
        // die n-te Wiederholung gilt nur dann als doppelt, wenn schon n Einträge vorhanden sind.
        const n = (fileSeenPlain.get(plain) || 0) + 1;
        fileSeenPlain.set(plain, n);
        dup = n <= (known.plainAll.get(plain) || 0);
      }
      if (dup) { stats.dup++; continue; }

      const entry = {
        name, date, platform, buy, sell,
        cost: Math.round(cost * 100) / 100,
        status: isStock ? "stock" : "sold",
        needsBuy: !hasBuyCol && !isStock,
        ref,
      };
      if (oid) entry.receipt = oid.slice(0, 60);
      if (opts.own) {
        const bd = m.buyDate >= 0 ? parseDate(get(m.buyDate), "dmy") : null;
        if (bd) entry.buyDate = bd;
        const rc = m.receipt >= 0 ? String(get(m.receipt) || "").trim().slice(0, 60) : "";
        if (rc) entry.receipt = rc;
        const kd = m.kind >= 0 ? norm(get(m.kind)) : "";
        if (kd.startsWith("gebrauch")) entry.kind = "everyday";
        else if (kd.startsWith("sonstig")) entry.kind = "other";
      }
      entries.push(entry);
      stats.ok++;
    }
    return { entries, stats };
  }

  /* ---------- Datei -> Einträge ohne Oberfläche (für „Mein SellCheck“, gleiche Erkennung wie die Tools in import.js) ---------- */
  const BANKISH = /verwendungszweck|buchungstext|wertstellung|valuta|\biban\b|auftraggeber|beguenstigter|begünstigter|zahlungspflichtiger|zahlungsempfänger/i;
  /** Text einer CSV erkennen. o.maxRows: mehr Datenzeilen werden abgelehnt (nichts wird gelesen). */
  function analyze(text, o) {
    const limit = (o && o.maxRows) || MAX_ROWS;
    if (!text || !text.trim()) return { ok: false, message: "Die Datei ist leer." };
    const d = detectDelimiter(text);
    const all = parseCSV(text, d);
    if (all.length < 2) return { ok: false, message: "Ich konnte keine Tabelle erkennen. Ist das eine CSV- oder Textdatei (kein Excel .xlsx)?" };
    const h = findHeader(all);
    const headers = all[h].map((x, i) => x.trim() || `Spalte ${i + 1}`);
    const rows = all.slice(h + 1).filter((r) => r.length >= 2);
    if (!rows.length) return { ok: false, message: "Keine Datenzeilen unter der Kopfzeile gefunden. Die Datei braucht eine Kopfzeile mit Spaltennamen." };
    if (rows.length > limit) return { ok: false, tooMany: true, count: rows.length, message: `Die Datei hat ${rows.length} Zeilen, erlaubt sind ${limit} je Durchgang. Es wurde nichts gespeichert. Teile die Datei nach Jahren auf.` };
    const own = isOwnFormat(headers);
    const map = own ? ownMapping(headers) : guessColumns(headers);
    const g = guessDateOrder(map.date >= 0 ? rows.map((r) => r[map.date]) : []);
    const bankLike = !own && headers.some((x) => BANKISH.test(x));
    const typeChecked = new Map();
    if (map.type >= 0) for (const r of rows) { const v = (r[map.type] || "").trim(); if (!typeChecked.has(v)) typeChecked.set(v, defaultTypeChecked(v)); }
    return { ok: true, delimiter: d, headers, rows, own, map, dateOrder: g.order, ambiguous: g.ambiguous, currencies: detectCurrencies(headers, rows), bankLike, keyword: bankLike ? "Vinted|Kleinanzeigen" : "", typeChecked };
  }
  /** Einträge zur erkannten Datei. Doppelte gegen das Konto prüft SCKonto.planTakeover, deshalb ohne Vergleich mit vorhandenen Einträgen. */
  function entriesFrom(a, o) {
    const x = o || {};
    return buildEntries(a.rows, a.map, {
      dateOrder: x.dateOrder || a.dateOrder, platform: x.platform || "", positiveOnly: x.positiveOnly == null ? !a.own : !!x.positiveOnly,
      keywords: String(x.keyword == null ? a.keyword : x.keyword).split(/[|,]/), own: a.own, typeChecked: a.typeChecked, platforms: x.platforms || [],
    });
  }

  /* ---------- Beispieldateien (frei erfunden, KEINE Originalexporte) ---------- */
  const SAMPLES = {
    ebay: { platform: "eBay", keyword: "", text:
`"Transaktionsbericht";;;;;;
"Erstellt am: 05.10.2026";;;;;;
;;;;;;
"Transaktionserstellungsdatum";"Typ";"Bestellnummer";"Artikelbezeichnung";"Bruttobetrag";"Endwertgebühr";"Nettobetrag"
"03.09.2026";"Bestellung";"12-34567-89012";"Retro Spielekonsole";"79,00";"-8,53";"70,47"
"04.09.2026";"Erstattung";"12-34567-89013";"Kopfhörer";"-25,00";"2,70";"-22,30"
"09.09.2026";"Bestellung";"12-34567-89014";"Vintage Lederjacke";"120,00";"-12,96";"107,04"
"15.09.2026";"Auszahlung";"";"";"-177,51";"0,00";"-177,51"
` },
    etsy: { platform: "Etsy", keyword: "", text:
`Sale Date,Order ID,Buyer,Order Value,Shipping,Sales Tax,Order Total,Card Processing Fees,Order Net
09/21/2026,3011122233,Anna K.,"24.00","4.50","0.00","28.50","1.32","27.18"
09/25/2026,3011122244,Max B.,"1,240.00","6.90","0.00","1,246.90","20.00","1,226.90"
10/02/2026,3011122255,Lea S.,"18.50","3.90","0.00","22.40","1.14","21.26"
` },
    amazon: { platform: "Amazon", keyword: "", text:
`order-id\tpurchase-date\titem-name\tquantity-purchased\titem-price\tshipping-price
028-1234567-1234567\t2026-09-12T10:22:31+00:00\tBambus Schneidebrett\t1\t19,90\t0,00
028-1234567-7654321\t2026-09-19T08:05:12+00:00\tKerzenhalter Set\t2\t34,00\t4,99
` },
    paypal: { platform: "", keyword: "", text:
`"Datum","Uhrzeit","Zeitzone","Name","Typ","Status","Brutto","Gebühr","Netto","Transaktionscode","Artikelbezeichnung"
"15.09.2026","10:01:12","CEST","Julia M.","Allgemeine Zahlung","Abgeschlossen","45,00","-1,66","43,34","1AB23456CD789012E","Kleinanzeigen Kamera"
"16.09.2026","09:12:40","CEST","Tom R.","Rückzahlung","Abgeschlossen","-12,00","0,00","-12,00","2BC34567DE890123F","Rückzahlung Kleinanzeigen Buch"
"20.09.2026","18:44:03","CEST","Sven L.","Allgemeine Zahlung","Abgeschlossen","30,00","-1,27","28,73","3CD45678EF901234G","Vinted Sneaker"
` },
    bank: { platform: "", keyword: "Vinted|Kleinanzeigen", text:
`Buchungstag;Wertstellung;Auftraggeber/Empfänger;Verwendungszweck;Betrag;Währung
02.09.2026;02.09.2026;VINTED UAB;Auszahlung Vinted Guthaben;34,50;EUR
03.09.2026;03.09.2026;REWE Markt;Kartenzahlung;-23,10;EUR
10.09.2026;10.09.2026;Kleinanzeigen GmbH;Auszahlung Kleinanzeigen Verkauf Fahrrad;120,00;EUR
14.09.2026;14.09.2026;Arbeitgeber GmbH;Gehalt;1800,00;EUR
` },
  };

  return {
    MAX_ROWS, MAX_NAME, norm, decode, detectDelimiter, parseCSV, findHeader, parseNum, parseDate,
    guessDateOrder, guessColumns, isOwnFormat, ownMapping, detectCurrencies, indexExisting,
    defaultTypeChecked, buildEntries, analyze, entriesFrom, SAMPLES,
  };
});
