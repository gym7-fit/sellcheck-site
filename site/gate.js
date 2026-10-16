// Freischaltung per E-Mail-Adresse: Formular, Speicherung der Freischaltung, optionaler Versand.
// Eingaben und Verkaufsdaten bleiben im Browser. Gesendet wird nur, was unten beschrieben ist und nur,
// wenn in gate-config.js ein Endpunkt eingetragen ist.
(function () {
  "use strict";
  const G = window.SCGateLib;
  const cfg = Object.assign({ leadEndpoint: "", reportEndpoint: "" }, window.SC_GATE || {});
  const KEY = "sellcheck.lead.v1";
  const TIMEOUT_MS = 10000;
  const COOLDOWN_MS = 4000;
  let lead = null;
  let pending = null;
  let lastSent = 0;
  const listeners = [];

  function load() {
    try { return G.sanitizeLead(JSON.parse(localStorage.getItem(KEY) || "null")); } catch { return null; }
  }
  function save() {
    try {
      if (lead) localStorage.setItem(KEY, JSON.stringify(lead));
      else localStorage.removeItem(KEY);
    } catch { /* Speicher gesperrt */ }
  }
  lead = load();

  const httpsOk = (u) => { try { return new URL(u).protocol === "https:"; } catch { return false; } };

  async function postJson(url, body) {
    if (!url || !httpsOk(url)) return { ok: false, reason: "not-configured" };
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        credentials: "omit",
        referrerPolicy: "no-referrer",
        redirect: "error",
        signal: ctl.signal,
      });
      return { ok: res.ok, reason: res.ok ? "" : "status-" + res.status };
    } catch {
      return { ok: false, reason: "network" };
    } finally {
      clearTimeout(timer);
    }
  }

  const notify = () => listeners.forEach((fn) => { try { fn(lead); } catch { /* Hörer dürfen nichts blockieren */ } });

  /* ---------- Formular ---------- */
  const dlg = document.getElementById("gate-dialog");
  const form = document.getElementById("gate-form");
  if (dlg && form) {
    const note = document.getElementById("gate-note");
    const email = document.getElementById("gate-email");
    // Texte aus der Bibliothek, damit Formular und Einwilligungsnachweis identisch sind.
    document.getElementById("gate-report-text").textContent = G.TEXTS.report;
    document.getElementById("gate-report-hint").textContent = G.TEXTS.reportHint;
    document.getElementById("gate-tips-text").textContent = G.TEXTS.tips;
    document.getElementById("gate-tips-hint").textContent = G.TEXTS.tipsHint;

    const close = () => { if (dlg.open) dlg.close(); };
    document.getElementById("gate-cancel").addEventListener("click", () => { pending = null; close(); });
    dlg.addEventListener("cancel", () => { pending = null; });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      note.textContent = "";
      const value = email.value.trim();
      if (!G.validEmail(value)) {
        SCField.show(email, "Das ist keine gültige E-Mail-Adresse. Beispiel: du@beispiel.de");
        return;
      }
      if (form.website.value) { // Honeypot: Bots füllen das unsichtbare Feld
        close();
        return;
      }
      if (Date.now() - lastSent < COOLDOWN_MS) {
        note.textContent = "Bitte einen Moment warten.";
        return;
      }
      lastSent = Date.now();
      lead = G.sanitizeLead({
        email: value,
        report: form.report.checked,
        tips: form.tips.checked,
        at: Date.now(),
      });
      save();
      const payload = G.leadPayload(lead, new Date().toISOString());
      const result = await postJson(cfg.leadEndpoint, payload); // Ergebnis wird auch bei Ausfall des Dienstes freigeschaltet
      lead.delivery = cfg.leadEndpoint ? (result.ok ? "sent" : "failed") : "demo";
      close();
      form.reset();
      notify();
      const cb = pending;
      pending = null;
      if (cb) cb();
    });
  }

  function requireUnlock(cb) {
    if (lead) { cb(); return; }
    if (!dlg || typeof dlg.showModal !== "function") { location.href = "tools.html#review"; return; }
    pending = cb;
    const note = document.getElementById("gate-note");
    if (note) note.textContent = "";
    dlg.showModal();
    const field = document.getElementById("gate-email");
    if (field) field.focus();
  }

  window.SCGate = {
    unlocked: () => !!lead,
    lead: () => lead,
    require: requireUnlock,
    clear() { lead = null; save(); notify(); },
    markReportSent() { if (lead) { lead.reportSent = true; save(); } },
    onChange(fn) { listeners.push(fn); },
    config: () => ({ leadEndpoint: cfg.leadEndpoint, reportEndpoint: cfg.reportEndpoint }),
    sendReport: (payload) => postJson(cfg.reportEndpoint, payload),
  };
})();
