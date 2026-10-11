// Ausführen: node --test tests/help.test.js
// Schützt die Hilfeseiten: jede Datenquelle in Schritt 3 hat einen Hilfe-Link, alle Ziele existieren,
// und die Seiten bleiben skriptfrei, nicht indexierbar und sauber verlinkt.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SITE = path.join(__dirname, "..", "site");
const HILFE = path.join(SITE, "hilfe");
const read = (p) => fs.readFileSync(p, "utf8");
const tools = read(path.join(SITE, "tools.html"));
const pages = fs.readdirSync(HILFE).filter((f) => f.endsWith(".html"));

test("Jede Datenquelle in Schritt 3 ist eine Karte mit Anleitungs-Link in neuem Tab (keine Auswahl-Reiter)", () => {
  const cards = tools.match(/<li class="src-card">/g) || [];
  assert.equal(cards.length, 8);
  assert.ok(!/id="tab-(ebay|etsy|amazon|paypal|bank|own|vinted|kleinanzeigen)"/.test(tools), "alte Reiter-Kacheln sind weg");
  const links = [...tools.matchAll(/<a class="src-help" href="(hilfe\/[a-z]+\.html)" target="_blank" rel="noopener"/g)].map((m) => m[1]);
  assert.equal(links.length, 8, "pro Karte genau ein Link mit target=_blank und rel=noopener");
  assert.equal(new Set(links).size, 8, "keine doppelten Ziele");
  for (const l of links) assert.ok(fs.existsSync(path.join(SITE, l)), `${l} fehlt`);
});

test("Es gibt eine Übersicht und eine Seite je Datenquelle", () => {
  for (const n of ["index", "ebay", "etsy", "amazon", "paypal", "bank", "tabelle", "vinted", "kleinanzeigen"]) {
    assert.ok(pages.includes(n + ".html"), `${n}.html fehlt`);
  }
  const hub = read(path.join(HILFE, "index.html"));
  for (const n of ["ebay", "etsy", "amazon", "paypal", "bank", "tabelle", "vinted", "kleinanzeigen"]) {
    assert.ok(hub.includes(`href="${n}.html"`), `Übersicht verlinkt ${n} nicht`);
  }
});

test("Hilfeseiten: kein Skript, nicht indexierbar, Content-Security-Policy ohne script-src", () => {
  for (const f of pages) {
    const h = read(path.join(HILFE, f));
    assert.ok(!/<script/i.test(h), `${f}: enthält <script>`);
    assert.ok(!/\son[a-z]+\s*=/i.test(h), `${f}: enthält Inline-Event-Handler`);
    assert.ok(/<meta name="robots" content="noindex, nofollow">/.test(h), `${f}: noindex fehlt`);
    const csp = (h.match(/Content-Security-Policy" content="([^"]+)"/) || [])[1] || "";
    assert.ok(csp.includes("default-src 'none'") && !csp.includes("script-src"), `${f}: CSP`);
    assert.match(h, /<title>[^<]+ – SellCheck<\/title>/, `${f}: Titel`);
    assert.match(h, /<h1>/, `${f}: Überschrift`);
  }
});

test("Hilfeseiten: interne Links und Dateien existieren, externe Links sind abgesichert", () => {
  for (const f of pages) {
    const h = read(path.join(HILFE, f));
    for (const m of h.matchAll(/(?:href|src)="([^"]+)"/g)) {
      const u = m[1];
      if (/^https:\/\//.test(u)) continue;
      assert.ok(!/^(http:|javascript:|data:)/i.test(u), `${f}: unzulässiges Ziel ${u}`);
      const target = path.join(HILFE, u.split("#")[0]);
      assert.ok(fs.existsSync(target), `${f}: ${u} existiert nicht`);
    }
    for (const m of h.matchAll(/<a [^>]*href="https:\/\/[^"]+"[^>]*>/g)) {
      assert.match(m[0], /rel="noopener noreferrer"/, `${f}: externer Link ohne noopener`);
      assert.match(m[0], /target="_blank"/, `${f}: externer Link ohne neuen Tab`);
    }
  }
});

test("Hilfeseiten nennen den Stand der Beschreibung", () => {
  for (const f of pages) assert.match(read(path.join(HILFE, f)), /Stand der Beschreibung/, f);
});
