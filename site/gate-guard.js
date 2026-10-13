// Report-Seite: Ohne Freischaltung zurück zum Ablauf, dort erscheint das Formular.
(function () {
  "use strict";
  let lead = null;
  try { lead = window.SCGateLib.sanitizeLead(JSON.parse(localStorage.getItem("sellcheck.lead.v1") || "null")); } catch { /* ignorieren */ }
  if (!lead) location.replace("tools.html#review");
})();
