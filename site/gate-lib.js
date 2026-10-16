// Freischaltung per E-Mail-Adresse (ohne DOM, damit sie im Browser UND in Node getestet werden kann).
// Browser: window.SCGateLib   |   Node: require("./gate-lib.js")
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SCGateLib = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Diese Texte erscheinen im Formular und werden als Einwilligungsnachweis mitgesendet. Eine Quelle für beides.
  const TEXTS = {
    report: "Report zusätzlich per E-Mail an mich senden",
    reportHint: "Dafür wird der Report einmalig an unseren E-Mail-Dienst übermittelt. Ohne Haken bleibt alles auf deinem Gerät.",
    tips: "Tipps und Tricks per E-Mail erhalten",
    tipsHint: "Hinweise zu Meldegrenzen, Fristen und neuen Funktionen. Jederzeit abbestellbar.",
  };

  const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;
  const FORBIDDEN = /[<>()[\]\\,;:"]|\.\./;

  function validEmail(value) {
    const e = String(value == null ? "" : value).trim();
    return e.length >= 6 && e.length <= 254 && EMAIL_RE.test(e) && !FORBIDDEN.test(e);
  }

  // Gespeicherten Zustand bereinigen (kommt aus localStorage und ist nicht vertrauenswürdig).
  function sanitizeLead(raw) {
    if (!raw || typeof raw !== "object") return null;
    const email = String(raw.email == null ? "" : raw.email).trim();
    if (!validEmail(email)) return null;
    const at = Number(raw.at);
    return {
      v: 1,
      email,
      report: raw.report === true,
      tips: raw.tips === true,
      reportSent: raw.reportSent === true,
      at: Number.isFinite(at) && at > 0 ? at : 0,
    };
  }

  const isUnlocked = (lead) => sanitizeLead(lead) !== null;

  // Was an den Mailanbieter geht, wenn eine Adresse eingetragen wird. Keine Verkaufsdaten.
  function leadPayload(lead, nowIso) {
    const l = sanitizeLead(lead);
    if (!l) return null;
    return {
      email: l.email,
      source: "tools-gate",
      consents: {
        tips: l.tips ? { given: true, text: TEXTS.tips + ". " + TEXTS.tipsHint, at: nowIso } : { given: false },
        report: l.report ? { given: true, text: TEXTS.report + ". " + TEXTS.reportHint, at: nowIso } : { given: false },
      },
    };
  }

  // mailto-Adresse für die Zusammenfassung an die eigene Adresse. Lange Texte werden gekürzt.
  function mailtoHref(email, subject, body) {
    const to = String(email || "").trim();
    if (!validEmail(to)) return "";
    let text = String(body || "");
    if (text.length > 1500) text = text.slice(0, 1500).replace(/\s+\S*$/, "") + "\n…";
    return "mailto:" + encodeURIComponent(to).replace(/%40/g, "@") + "?subject=" + encodeURIComponent(subject || "") + "&body=" + encodeURIComponent(text);
  }

  return { TEXTS, validEmail, sanitizeLead, isUnlocked, leadPayload, mailtoHref };
});
