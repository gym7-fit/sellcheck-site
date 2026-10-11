// Oberfläche des Datei-Imports. Die Logik steckt in parse-lib.js (dort getestet).
// Alles läuft lokal im Browser, es wird nichts hochgeladen.
(function () {
  "use strict";
  const SC = window.SellCheck;
  const P = window.SCParse;
  const $ = (id) => document.getElementById(id);
  const MAX_BYTES = 5 * 1024 * 1024;
  const eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
  const el = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  const debounce = (fn, ms) => {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  };

  /* ---------- Plattform-Auswahl ---------- */
  (function () {
    const sel = $("i-platform");
    const auto = el("option", "Automatisch erkennen (Spalte oder Text)");
    auto.value = "";
    sel.replaceChildren(auto, ...SC.PLATFORMS.map((p) => { const o = el("option", p.name); o.value = p.name; return o; }));
  })();
  const platformNames = SC.PLATFORMS.map((p) => p.name);

  /* ---------- Zustand ---------- */
  const state = { headers: [], rows: [], map: null, own: false, typeChecked: new Map() };
  let current = { entries: [], stats: null };

  /* ---------- Einlesen ---------- */
  function load(text, presetPlatform, keyword) {
    const msg = $("i-msg");
    msg.textContent = "";
    if (!text || !text.trim()) {
      msg.textContent = "Die Datei ist leer.";
      return;
    }
    const d = P.detectDelimiter(text);
    const all = P.parseCSV(text, d);
    if (all.length < 2) {
      msg.textContent = "Ich konnte keine Tabelle erkennen. Ist das eine CSV- oder Textdatei (kein Excel .xlsx)?";
      return;
    }
    const h = P.findHeader(all);
    state.headers = all[h].map((x, i) => x.trim() || `Spalte ${i + 1}`);
    state.rows = all.slice(h + 1).filter((r) => r.length >= 2).slice(0, P.MAX_ROWS);
    if (!state.rows.length) {
      msg.textContent = "Keine Datenzeilen unter der Kopfzeile gefunden. Die Datei braucht eine Kopfzeile mit Spaltennamen.";
      return;
    }
    state.own = P.isOwnFormat(state.headers);
    state.map = state.own ? P.ownMapping(state.headers) : P.guessColumns(state.headers);
    const dateCol = state.map.date >= 0 ? state.rows.map((r) => r[state.map.date]) : [];
    const g = P.guessDateOrder(dateCol);
    $("i-dateorder").value = g.order;
    $("i-datewarn").hidden = !g.ambiguous;
    if (g.ambiguous) {
      $("i-datewarn").textContent = `Das Datumsformat ist aus den Daten nicht eindeutig (alle Tage ≤ 12). Ich habe „${g.order === "mdy" ? "Monat/Tag/Jahr" : "Tag.Monat.Jahr"}“ angenommen. Bitte prüfe in der Vorschau, ob die Daten stimmen.`;
    }
    const cur = P.detectCurrencies(state.headers, state.rows);
    $("i-curwarn").hidden = cur.length === 0;
    if (cur.length) $("i-curwarn").textContent = `Die Datei enthält andere Währungen (${cur.join(", ")}). SellCheck rechnet nicht um, alle Beträge würden als Euro gezählt. Importiere nur die Euro-Zeilen oder rechne vorher um.`;

    $("i-platform").value = presetPlatform || "";
    $("i-keyword").value = keyword || "";
    $("i-positive").checked = !state.own;
    state.typeChecked = new Map();
    if ($("i-adv")) $("i-adv").open = false;
    buildMapping();
    $("i-panel").hidden = false;
    $("i-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    msg.textContent = `${state.rows.length} Zeilen erkannt (Trennzeichen: ${d === "\t" ? "Tab" : d}). Prüfe unten die Vorschau.`;
  }

  /* ---------- Zuordnung ---------- */
  const FIELDS = [
    { key: "date", label: "Datum *", hint: "Verkaufs- bzw. Bestelldatum" },
    { key: "amount", label: "Verkaufsbetrag *", hint: "Was der Käufer für den Artikel gezahlt hat (brutto)" },
    { key: "name", label: "Artikel / Beschreibung", hint: "Wird als Artikelname verwendet" },
    { key: "fees", label: "Gebühren (mehrere möglich)", hint: "Plattform- und Zahlungsgebühren, werden als Kosten gerechnet", multi: true },
    { key: "ship", label: "Versand, den du zahlst", hint: "Nur wenn die Datei deine Versandkosten enthält. Von Käufern gezahlter Versand gehört nicht hierher" },
    { key: "buy", label: "Einkaufspreis", hint: "Fehlt meist. Dann trägst du ihn später im Tracker nach" },
    { key: "orderId", label: "Bestellnummer", hint: "Verhindert doppelte Einträge beim erneuten Import" },
    { key: "type", label: "Typ / Status (zum Filtern)", hint: "Damit Erstattungen und Gebührenzeilen herausfallen" },
    { key: "plat", label: "Plattform-Spalte", hint: "Nur falls die Datei mehrere Plattformen enthält" },
  ];

  function buildMapping() {
    const box = $("i-map");
    box.replaceChildren();
    FIELDS.forEach((f) => {
      const wrap = el("div");
      const lab = el("label", f.label);
      lab.htmlFor = "i-col-" + f.key;
      const sel = document.createElement("select");
      sel.id = "i-col-" + f.key;
      if (f.multi) {
        sel.multiple = true;
        sel.size = Math.min(5, state.headers.length);
      } else {
        const none = el("option", "– nicht verwenden –");
        none.value = "-1";
        sel.append(none);
      }
      state.headers.forEach((h, i) => {
        const o = el("option", h);
        o.value = String(i);
        sel.append(o);
      });
      if (f.multi) [...sel.options].forEach((o) => (o.selected = (state.map.fees || []).includes(Number(o.value))));
      else sel.value = String(state.map[f.key] ?? -1);
      sel.addEventListener("change", () => {
        readMapping();
        if (f.key === "type") state.typeChecked = new Map();
        refreshAll();
      });
      wrap.append(lab, sel, el("div", f.hint, "small muted"));
      box.append(wrap);
    });
    refreshAll();
  }

  function readMapping() {
    FIELDS.forEach((f) => {
      const sel = $("i-col-" + f.key);
      if (!sel) return;
      if (f.multi) state.map.fees = [...sel.selectedOptions].map((o) => Number(o.value));
      else state.map[f.key] = Number(sel.value);
    });
  }

  function buildTypes() {
    const box = $("i-types");
    box.replaceChildren();
    const col = state.map.type;
    if (col < 0) {
      box.hidden = true;
      return;
    }
    const counts = new Map();
    state.rows.forEach((r) => {
      const v = (r[col] || "").trim();
      counts.set(v, (counts.get(v) || 0) + 1);
    });
    if (counts.size > 40) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    box.append(el("div", "Welche Zeilen importieren? (nach Spalte „" + state.headers[col] + "“)", "small muted"));
    for (const [v, n] of counts) {
      if (!state.typeChecked.has(v)) state.typeChecked.set(v, P.defaultTypeChecked(v));
      const lab = el("label", undefined, "type-opt");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = state.typeChecked.get(v);
      cb.addEventListener("change", () => {
        state.typeChecked.set(v, cb.checked);
        renderPreview();
      });
      lab.append(cb, el("span", `${v || "(leer)"} (${n})`));
      box.append(lab);
    }
  }

  /* ---------- Vorschau ---------- */
  function renderPreview() {
    readMapping();
    const res = P.buildEntries(state.rows, state.map, {
      dateOrder: $("i-dateorder").value,
      platform: $("i-platform").value,
      positiveOnly: $("i-positive").checked,
      keywords: $("i-keyword").value.split(/[|,]/),
      own: state.own,
      typeChecked: state.typeChecked,
      known: P.indexExisting(SC.sales),
      platforms: platformNames,
    });
    current = res;
    const s = res.stats;
    const parts = [`${s.ok} von ${s.total} Zeilen importierbar`];
    if (s.dup) parts.push(`${s.dup} schon vorhanden`);
    if (s.filtered) parts.push(`${s.filtered} per Typ-Filter übersprungen`);
    if (s.keyword) parts.push(`${s.keyword} ohne Stichwort`);
    if (s.noAmount) parts.push(`${s.noAmount} ohne gültigen Betrag (z. B. Erstattungen)`);
    if (s.noDate) parts.push(`${s.noDate} ohne lesbares Datum`);
    $("i-summary").textContent = parts.join(" · ");
    // Kurz sagen, was erkannt wurde, damit niemand das Raster öffnen muss, um es zu prüfen
    const nm = (c) => (c >= 0 && state.headers[c] ? `„${state.headers[c]}“` : null);
    const seen = [["Datum", nm(state.map.date)], ["Verkaufsbetrag", nm(state.map.amount)], ["Artikel", nm(state.map.name)]]
      .filter((x) => x[1]).map((x) => `${x[0]} = ${x[1]}`);
    const feeCols = (state.map.fees || []).map(nm).filter(Boolean);
    if (feeCols.length) seen.push(`Gebühren = ${feeCols.join(", ")}`);
    $("i-recognized").textContent = seen.length ? "Spalten: " + seen.join(" · ") : "";
    // Ist nichts importierbar, die Anpassungen gleich aufklappen
    if (s.ok === 0 && $("i-adv")) $("i-adv").open = true;
    $("i-go").disabled = s.ok === 0;
    $("i-prev").replaceChildren(
      ...res.entries.slice(0, 8).map((e) => {
        const tr = document.createElement("tr");
        [new Date(e.date).toLocaleDateString("de-DE"), e.name, e.platform, eur.format(e.sell), eur.format(e.cost)].forEach((t, i) => {
          const td = el("td", t);
          if (i >= 3) td.className = "num";
          tr.append(td);
        });
        return tr;
      })
    );
    $("i-prevwrap").hidden = res.entries.length === 0;
    const missing = res.entries.filter((e) => e.needsBuy).length;
    $("i-buywarn").hidden = missing === 0;
    if (missing) $("i-buywarn").textContent = `Hinweis: Die Datei enthält keine Einkaufspreise. Dein Gewinn wirkt zu hoch, bis du sie im Tracker nachträgst (${missing} Einträge).`;
  }
  const refreshAll = () => { buildTypes(); renderPreview(); };

  /* ---------- Import / Rückgängig ---------- */
  $("i-go").addEventListener("click", () => {
    if (!current.entries.length) return;
    const batch = "b" + Date.now();
    const stamp = Date.now() + Math.random().toString(36).slice(2, 7);
    const fresh = current.entries.map((e, i) => ({ ...e, id: `${stamp}-${i}`, batch }));
    if (!SC.commit(SC.sales.concat(fresh))) {
      $("i-msg").textContent = "Der Import konnte nicht gespeichert werden (Speicher voll oder gesperrt). Es wurde nichts übernommen. Exportiere deine alten Einträge als CSV, lösche sie und versuche es erneut, oder teile die Datei auf.";
      return;
    }
    updateUndo();
    $("i-msg").textContent = `${fresh.length} Einträge importiert.`;
    $("i-panel").hidden = true;
    const byYear = {};
    fresh.forEach((e) => { const y = e.date.slice(0, 4); byYear[y] = (byYear[y] || 0) + 1; });
    document.dispatchEvent(new CustomEvent("sellcheck:imported", { detail: { count: fresh.length, byYear } }));
    current = { entries: [], stats: null };
  });

  function updateUndo() {
    $("i-undo").hidden = SC.latestBatch() === null;
  }
  $("i-undo").addEventListener("click", () => {
    const batch = SC.latestBatch();
    if (!batch) return;
    const kept = SC.sales.filter((s) => s.batch !== batch);
    const removed = SC.sales.length - kept.length;
    if (!SC.commit(kept)) {
      $("i-msg").textContent = "Das Rückgängigmachen konnte nicht gespeichert werden.";
      return;
    }
    $("i-msg").textContent = `${removed} importierte Einträge wieder entfernt.`;
    updateUndo();
  });
  updateUndo();

  /* ---------- Eingabewege ---------- */
  function handleFile(file) {
    if (!file) return;
    if (file.size > MAX_BYTES) {
      $("i-msg").textContent = "Die Datei ist größer als 5 MB. Bitte teile sie nach Jahren auf.";
      return;
    }
    if (/\.(xlsx|xls|numbers|pdf|zip)$/i.test(file.name)) {
      $("i-msg").textContent = "Dieses Format kann ich nicht lesen. Speichere die Tabelle bitte als CSV (Excel: Speichern unter → CSV).";
      return;
    }
    const fr = new FileReader();
    fr.onload = () => load(P.decode(fr.result));
    fr.onerror = () => ($("i-msg").textContent = "Die Datei konnte nicht gelesen werden.");
    fr.readAsArrayBuffer(file);
  }
  $("i-file").addEventListener("change", (e) => {
    handleFile(e.target.files[0]);
    e.target.value = ""; // dieselbe Datei später erneut wählbar
  });
  const drop = $("i-drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));
  $("i-paste-go").addEventListener("click", () => load($("i-paste").value));
  const slowPreview = debounce(renderPreview, 150);
  $("i-keyword").addEventListener("input", slowPreview);
  ["i-dateorder", "i-platform", "i-positive"].forEach((id) => $(id).addEventListener("input", renderPreview));

  $("i-sample").addEventListener("change", (e) => {
    const s = P.SAMPLES[e.target.value];
    if (s) load(s.text, s.platform, s.keyword);
    e.target.value = "";
  });

  /* ---------- Kachel-Auswahl (Datenquellen, Abgabewege) ---------- */
  document.documentElement.classList.add("js");
  document.querySelectorAll("[data-tabs]").forEach((root) => {
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const panels = tabs.map((t) => document.getElementById(t.getAttribute("aria-controls")));
    if (!tabs.length) return;
    function select(i, focus) {
      tabs.forEach((t, k) => {
        const on = k === i;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        panels[k].hidden = !on;
      });
      if (focus) tabs[i].focus();
    }
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(i, false));
      t.addEventListener("keydown", (e) => {
        const map = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
        if (e.key in map) {
          e.preventDefault();
          select((i + map[e.key] + tabs.length) % tabs.length, true);
        } else if (e.key === "Home") { e.preventDefault(); select(0, true); }
        else if (e.key === "End") { e.preventDefault(); select(tabs.length - 1, true); }
      });
    });
    select(0, false);
  });
})();
