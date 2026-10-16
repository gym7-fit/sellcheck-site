const test = require("node:test");
const assert = require("node:assert/strict");
const G = require("../site/gate-lib.js");

test("validEmail: übliche Adressen", () => {
  assert.equal(G.validEmail("anna@example.de"), true);
  assert.equal(G.validEmail("  anna.muster+shop@mail.example.com "), true);
});

test("validEmail: ungültige und gefährliche Eingaben", () => {
  ["", "anna", "anna@", "@example.de", "anna@example", "a b@example.de", "anna@exa..mple.de", "<x>@example.de", "anna@example.de,bob@example.de", 'a"b@example.de', "x".repeat(250) + "@a.de"]
    .forEach((v) => assert.equal(G.validEmail(v), false, v));
  assert.equal(G.validEmail(null), false);
  assert.equal(G.validEmail(undefined), false);
});

test("sanitizeLead: nur gültige Freischaltungen, Einwilligungen nur bei true", () => {
  assert.equal(G.sanitizeLead(null), null);
  assert.equal(G.sanitizeLead("x"), null);
  assert.equal(G.sanitizeLead({ email: "kaputt" }), null);
  const l = G.sanitizeLead({ email: " anna@example.de ", report: "ja", tips: true, at: "1700000000000", extra: "x" });
  assert.deepEqual(l, { v: 1, email: "anna@example.de", report: false, tips: true, reportSent: false, at: 1700000000000 });
});

test("isUnlocked folgt sanitizeLead", () => {
  assert.equal(G.isUnlocked({ email: "anna@example.de" }), true);
  assert.equal(G.isUnlocked({ email: "nein" }), false);
  assert.equal(G.isUnlocked(undefined), false);
});

test("leadPayload: keine Verkaufsdaten, Einwilligungen mit Text und Zeitpunkt", () => {
  const p = G.leadPayload({ email: "anna@example.de", tips: true, report: false }, "2026-10-13T08:00:00.000Z");
  assert.equal(p.email, "anna@example.de");
  assert.equal(p.source, "tools-gate");
  assert.equal(p.consents.tips.given, true);
  assert.match(p.consents.tips.text, /Tipps und Tricks/);
  assert.equal(p.consents.tips.at, "2026-10-13T08:00:00.000Z");
  assert.deepEqual(p.consents.report, { given: false });
  assert.deepEqual(Object.keys(p).sort(), ["consents", "email", "source"]);
  assert.equal(G.leadPayload({ email: "kaputt" }, "x"), null);
});

test("mailtoHref: kodiert, kürzt lange Texte, lehnt ungültige Adressen ab", () => {
  const href = G.mailtoHref("anna@example.de", "SellCheck: Zusammenfassung 2026", "Zeile 1\nZeile 2 & mehr");
  assert.ok(href.startsWith("mailto:anna@example.de?subject="));
  assert.match(href, /body=Zeile%201%0AZeile%202%20%26%20mehr$/);
  const long = G.mailtoHref("anna@example.de", "s", "wort ".repeat(1000));
  assert.ok(decodeURIComponent(long.split("body=")[1]).length <= 1510);
  assert.equal(G.mailtoHref("kaputt", "s", "b"), "");
});
