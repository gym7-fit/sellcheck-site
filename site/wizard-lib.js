// Logik des geführten Ablaufs (ohne DOM, testbar in Node und Browser). Browser: window.SCWizard
//
// Die Schritte werden nie "gemerkt", sondern immer aus den Eingaben und Daten berechnet.
// So kann der Stand nicht von der Wirklichkeit abweichen: Löscht jemand alle Einträge, sperren sich
// die späteren Schritte automatisch wieder.
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SCWizard = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const STEPS = [
    { n: 1, key: "basis", title: "Jahr und Art", short: "Jahr & Art" },
    { n: 2, key: "platforms", title: "Plattformen", short: "Plattformen" },
    { n: 3, key: "data", title: "Verkäufe erfassen", short: "Verkäufe" },
    { n: 4, key: "complete", title: "Angaben vervollständigen", short: "Vervollständigen" },
    { n: 5, key: "limits", title: "Meldegrenzen prüfen", short: "Meldegrenzen" },
    { n: 6, key: "report", title: "Angaben für den Report", short: "Report" },
  ];

  const MODES = ["business", "private"];
  const VATS = ["small", "regular"];

  const inYear = (iso, y) => typeof iso === "string" && String(y) !== "" && iso.slice(0, 4) === String(y);

  /* ---------- Zustand bereinigen (kommt aus localStorage) ---------- */
  function sanitizeState(raw, platformNames) {
    const s = raw && typeof raw === "object" ? raw : {};
    const known = new Set(platformNames || []);
    const platforms = Array.isArray(s.platforms)
      ? [...new Set(s.platforms.map(String).filter((p) => !platformNames || known.has(p)))].slice(0, 20)
      : [];
    const year = Number(s.year);
    const rate = Number(s.rate);
    const ack = s.ack && typeof s.ack === "object" ? s.ack : {};
    return {
      year: Number.isInteger(year) && year >= 2000 && year <= 2100 ? year : null,
      mode: MODES.includes(s.mode) ? s.mode : null,
      vat: VATS.includes(s.vat) ? s.vat : null,
      rate: rate === 7 || rate === 19 ? rate : 19,
      platforms,
      name: String(s.name || "").slice(0, 80),
      taxId: String(s.taxId || "").slice(0, 40),
      ack: {
        2: ack[2] === true,
        4: ack[4] === String(year) ? String(year) : null, // gilt nur für das Jahr, für das bestätigt wurde
        5: ack[5] === true,
        6: ack[6] === true,
      },
    };
  }

  /* ---------- Einträge des gewählten Jahres ---------- */
  const entriesOfYear = (sales, year) => sales.filter((s) => inYear(s.date, year));

  // Pflichtangaben je Eintrag. Nur das, was die Berechnung wirklich verfälscht.
  function missingFields(entry, mode) {
    const missing = [];
    if (entry.status !== "stock" && entry.needsBuy && !(entry.buy > 0)) missing.push("buy");
    if (mode === "private" && entry.status !== "stock" && !entry.kind) missing.push("kind");
    return missing;
  }

  function incompleteEntries(sales, year, mode) {
    return entriesOfYear(sales, year)
      .map((entry) => ({ entry, missing: missingFields(entry, mode) }))
      .filter((x) => x.missing.length);
  }

  /* ---------- Fortschritt ---------- */
  function progress(state, sales) {
    const year = state.year;
    const entries = year ? entriesOfYear(sales, year) : [];
    const incomplete = year && state.mode ? incompleteEntries(sales, year, state.mode) : [];
    const otherYears = {};
    sales.forEach((s) => {
      const y = s.date.slice(0, 4);
      if (String(y) !== String(year)) otherYears[y] = (otherYears[y] || 0) + 1;
    });

    const rule = {
      1: !!year && !!state.mode && (state.mode === "private" || !!state.vat),
      2: state.platforms.length > 0 && state.ack[2] === true,
      3: entries.length > 0,
      4: incomplete.length === 0 || state.ack[4] === String(year),
      5: state.ack[5] === true,
      6: state.ack[6] === true,
    };
    // Kumulativ: Ein Schritt ist nur erledigt, wenn auch alle davor erledigt sind.
    const done = {};
    let prev = true;
    for (const st of STEPS) {
      done[st.n] = prev && rule[st.n];
      prev = done[st.n];
    }
    const firstOpen = STEPS.find((st) => !done[st.n]);
    return {
      year, count: entries.length, incomplete, otherYears, done,
      active: firstOpen ? firstOpen.n : STEPS.length + 1, // 7 = alles erledigt
      canReview: STEPS.every((st) => done[st.n]),
    };
  }

  // Wie viele Schritte sind frei zugänglich (aktiver Schritt und alle davor)?
  const isUnlocked = (p, n) => n <= p.active;

  return { STEPS, MODES, VATS, sanitizeState, entriesOfYear, missingFields, incompleteEntries, progress, isUnlocked, inYear };
});
