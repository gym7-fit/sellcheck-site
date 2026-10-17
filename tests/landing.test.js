// Prüft, dass die Meldegrenze auf der Startseite im Mittelpunkt steht und mit den Tools übereinstimmt.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Tax = require("../site/tax-lib.js");

const SITE = path.join(__dirname, "..", "site");
const html = fs.readFileSync(path.join(SITE, "index.html"), "utf8");
const js = fs.readFileSync(path.join(SITE, "landing.js"), "utf8");
const hero = html.slice(html.indexOf('<div class="hero on-dark">'), html.indexOf("<!-- PLATTFORMEN -->"));
const demo = html.slice(html.indexOf('<section id="demo"'), html.indexOf("</section>", html.indexOf('<section id="demo"')));

test("Titel, Beschreibung und Link-Vorschau nennen die Meldegrenze", () => {
  assert.match(html.match(/<title>([^<]+)/)[1], /Meldegrenze/);
  assert.match(html.match(/name="description" content="([^"]+)"/)[1], /Meldegrenze/);
  assert.match(html.match(/property="og:title" content="([^"]+)"/)[1], /Meldegrenze/);
  assert.match(html.match(/property="og:description" content="([^"]+)"/)[1], /Meldegrenze/);
});

test("Hero: Meldegrenze ist der erste Aufruf, Überschrift (Claim) bleibt", () => {
  assert.match(hero, /<h1>Check, was <em>wirklich bleibt\.<\/em><\/h1>/);
  assert.match(hero, /<p class="lead">Wie nah bist du an der Meldegrenze\?/);
  const buttons = [...hero.matchAll(/<a class="btn( secondary)?" href="([^"]+)">\s*([^<]+)/g)].map((m) => ({ secondary: !!m[1], href: m[2], text: m[3].trim() }));
  assert.equal(buttons[0].href, "#demo");
  assert.equal(buttons[0].secondary, false);
  assert.match(buttons[0].text, /Meldegrenze prüfen/);
  assert.equal(buttons[1].href, "tools.html");
});

test("Navigation führt zur Meldegrenze", () => {
  assert.match(html, /<a class="hide-sm" href="#demo">Meldegrenze<\/a>/);
});

test("Demo: vier Plattformen mit Ampelpunkt, beide Regler, ehrliche Quelle", () => {
  const values = [...demo.matchAll(/name="d-plat" value="([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(values, ["vinted", "kleinanzeigen", "ebay", "etsy"]);
  assert.equal((demo.match(/<i><\/i>/g) || []).length, 4);
  assert.ok(demo.includes('id="d-count"') && demo.includes('id="d-sum"'));
  assert.match(demo, /Je Plattform und Jahr/);
  assert.match(demo, /abgeschlossene Verkäufe, nicht Artikel/);
  assert.match(demo, /keine Steuerforderung/);
  assert.match(demo, /href="https:\/\/www\.finanzamt\.nrw\.de\/[^"]+" target="_blank" rel="noopener noreferrer"/);
});

test("FAQ erklärt, was als Verkauf zählt", () => {
  assert.match(html, /<summary>Was zählt als Verkauf\?<\/summary>/);
});

test("Grenzen kommen aus tax-lib.js (eine Quelle für Startseite und Tools), Skript-Reihenfolge stimmt", () => {
  assert.equal(Tax.MELDE_COUNT, 30);
  assert.equal(Tax.MELDE_SUM, 2000);
  assert.ok(html.indexOf('src="tax-lib.js"') > 0 && html.indexOf('src="tax-lib.js"') < html.indexOf('src="landing.js"'));
  assert.match(js, /T\.MELDE_COUNT/);
});

test("Ampel-Schwellen der Startseite entsprechen denen der Tools (ab 60 % gelb, ab 100 % rot)", () => {
  assert.match(js, /worst >= 1 \? "red" : worst >= 0\.6 \? "yellow" : "green"/);
  const tools = fs.readFileSync(path.join(SITE, "tools.js"), "utf8");
  assert.match(tools, /ratio >= 1 \? "red" : ratio >= 0\.6 \? "yellow" : "green"/);
});

test("Beispielstände zeigen alle drei Stufen", () => {
  const levelOf = (c, s) => { const w = Math.max(c / 30, s / 2000); return w >= 1 ? "red" : w >= 0.6 ? "yellow" : "green"; };
  const states = js.match(/vinted: \{ c: (\d+), s: (\d+) \},\s*kleinanzeigen: \{ c: (\d+), s: (\d+) \},\s*ebay: \{ c: (\d+), s: (\d+) \},\s*etsy: \{ c: (\d+), s: (\d+) \}/);
  assert.ok(states);
  const n = states.slice(1).map(Number);
  const levels = [levelOf(n[0], n[1]), levelOf(n[2], n[3]), levelOf(n[4], n[5]), levelOf(n[6], n[7])];
  assert.deepEqual(new Set(levels), new Set(["green", "yellow", "red"]));
});

test("Sprungmarken: Abschnitte haben einen Abstand nach oben, damit die feste Kopfleiste nichts verdeckt", () => {
  const css = fs.readFileSync(path.join(SITE, "landing.css"), "utf8");
  assert.match(css, /section\[id\][^{]*\{[^}]*scroll-margin-top: \d+px/);
  assert.match(css, /\.demo-plats label \{[^}]*-webkit-tap-highlight-color: transparent/);
});

test("Angebot: Stufen Essential und Premium, Preis aufgeschlüsselt, nur Vorhandenes als Leistung, Geplantes als geplant markiert", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "site", "index.html"), "utf8");
  const sec = html.slice(html.indexOf('<section id="angebot"'), html.indexOf("<!-- VERTRAUEN -->"));
  for (const h of ["Starter</h3>", "Essential</h3>", "Premium</h3>"]) assert.ok(sec.includes(h), `Karte ${h} fehlt`);
  assert.match(sec, /4,99 €[\s\S]*oder 39 € im Jahr/, "Essential-Preise");
  assert.match(sec, /6,99 €[\s\S]*oder 49 € im Jahr/, "Premium-Preise");
  assert.match(sec, /rund 3,25 Euro im Monat/, "Monatsanteil Essential");
  assert.match(sec, /rund 4,08 Euro im Monat/, "Monatsanteil Premium");
  assert.equal((sec.match(/class="plan-lead"/g) || []).length, 2, "Ergebnis-Satz je Bezahl-Stufe");
  assert.match(sec, /Alles aus Essential/, "Premium nennt „Alles aus Essential“");
  assert.match(sec, /Unbegrenzt viele Artikel/, "unbegrenzte Artikel als eigener Punkt");
  assert.match(sec, /class="plan-cost"/, "Vergleich mit dem Problem fehlt");
  assert.match(sec, /href="#demo"/, "Beispielrechnung fehlt");
  // Noch nicht gebaute Funktionen (Screenshot-Import, KI-Inserate, Sync) dürfen nirgends als Leistung stehen
  const lists = [...sec.matchAll(/<ul class="check">[\s\S]*?<\/ul>/g)].map((m) => m[0]).join("");
  assert.ok(!/Screenshot|KI|Weiterleitung|Inserat|Synchron|Geräte/i.test(lists), "Geplantes gehört nicht in die Leistungslisten");
  assert.match(sec, /Noch nicht erhältlich/, "Hinweis auf Geplantes fehlt");
  assert.match(sec, /Basic kostenlos/, "kostenlose Stufe Basic wird genannt");
  assert.ok(!/\d+ Stunden|\$\s?\d+|\d+\s?€ deiner Zeit/.test(sec), "keine erfundenen Zeit- oder Geldersparnisse");
  assert.ok(!/SellCheck Pro|Pro-Karte/.test(sec), "alter Name Pro ist ersetzt");
});
