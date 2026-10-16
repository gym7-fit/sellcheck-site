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
