// 20-Punkte-Checkliste für Webseiten (nur die Punkte, die für SellCheck umsetzbar sind).
// Nicht umgesetzt mit Absicht: Kundenprojekte, Karte und Anfahrt, echte Bewertungen (gibt es nicht), Local-Schema,
// Google Analytics (widerspricht der Datenschutz-Linie: keine Tracker), Teamfoto.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SITE = path.join(__dirname, "..", "site");
const read = (f) => fs.readFileSync(path.join(SITE, f), "utf8");
const pages = [...fs.readdirSync(SITE).filter((f) => f.endsWith(".html")), ...fs.readdirSync(path.join(SITE, "hilfe")).filter((f) => f.endsWith(".html")).map((f) => "hilfe/" + f)];
const publicPages = pages.filter((f) => !/^(report|brand)\.html$/.test(f));

test("1 eigene 404-Seite mit Wegen weiter (Startseite, Tools, Hilfe, Kontakt)", () => {
  const s = read("404.html");
  // Die 404-Seite wird unter beliebigen Pfaden ausgeliefert, deshalb absolute Adressen (die Sicherheitsrichtlinie verbietet <base>).
  assert.ok(!/<base\b/.test(s));
  assert.match(s, /href="https:\/\/[^"]+\/style\.css"/);
  for (const l of ["index.html", "tools.html", "hilfe/index.html", "impressum.html#kontakt"]) assert.ok(s.includes(`/${l}"`), `404: Link ${l}`);
});

test("2 klarer Handlungsknopf auf Startseite, Tools und Danke-Seite", () => {
  assert.match(read("index.html"), /class="btn"[^>]*href="#demo"/);
  assert.match(read("tools.html"), /class="btn/);
  assert.match(read("danke.html"), /class="btn"/);
});

test("3 interne Links: jede öffentliche Seite führt zurück zur Startseite und zu mindestens drei weiteren Seiten", () => {
  for (const f of publicPages) {
    const links = new Set([...read(f).matchAll(/href="([^"#]+\.html|\.\.\/[^"#]*|[^"#]*\/)"/g)].map((m) => m[1]));
    assert.ok(links.size >= 3, `${f}: nur ${links.size} interne Links`);
    assert.ok([...links].some((l) => /index\.html$|^\.\.\/$|^\.\/$/.test(l)), `${f}: kein Link zur Startseite`);
  }
});

test("4 Danke-Seite existiert und die Warteliste leitet dorthin", () => {
  assert.match(read("danke.html"), /<h1>Danke/);
  assert.match(read("waitlist.js"), /location\.href = "danke\.html"/);
});

test("5 Brotkrumen auf den Hilfeseiten", () => {
  for (const f of pages.filter((x) => x.startsWith("hilfe/"))) assert.match(read(f), /class="crumbs" aria-label="Brotkrumen"/, `${f}: Brotkrumen`);
});

test("7 mindestens fünf FAQ-Einträge", () => {
  assert.ok((read("index.html").match(/<details>/g) || []).length >= 5);
});

test("8 und 9 Antwortzeit und Kontakt: Kontakt-Link in der Fußzeile, Antwortzeit im Impressum", () => {
  assert.match(read("impressum.html"), /id="kontakt"/);
  assert.match(read("impressum.html"), /Antwortzeit/);
  for (const f of ["index.html", "tools.html"]) assert.match(read(f), /href="impressum\.html#kontakt"/, `${f}: Kontakt-Link`);
});

test("10 robots.txt vorhanden (bis zum Livegang gesperrt, Hinweis zum Öffnen steht darin)", () => {
  const r = read("robots.txt");
  assert.match(r, /User-agent: \*/);
  assert.match(r, /Livegang/);
});

test("11 bis 13 eigener Titel, Beschreibung und Vorschaubild je öffentlicher Seite, Titel eindeutig", () => {
  const titles = new Map();
  for (const f of publicPages) {
    const s = read(f);
    const t = (s.match(/<title>([^<]+)<\/title>/) || [])[1];
    assert.ok(t && t.length >= 8 && t.length <= 70, `${f}: Titel (${t})`);
    assert.ok(!titles.has(t), `${f}: Titel doppelt mit ${titles.get(t)}`);
    titles.set(t, f);
    const d = (s.match(/name="description" content="([^"]+)"/) || [])[1];
    assert.ok(d && d.length >= 30 && d.length <= 200, `${f}: Beschreibung (${d ? d.length : 0} Zeichen)`);
    if (f !== "404.html") {
      assert.match(s, /rel="canonical"/, `${f}: canonical`);
      assert.match(s, /property="og:image" content="https:\/\/[^"]+\.png"/, `${f}: og:image`);
    }
  }
});

test("16 Alt-Texte, 19 Datenschutzseite: stehen im a11y-Test und im Checklisten-Test", () => {
  assert.ok(fs.existsSync(path.join(SITE, "datenschutz.html")));
});

test("Sitemap-Erzeugung kennt alle öffentlichen Seiten", () => {
  const s = fs.readFileSync(path.join(__dirname, "..", "scripts", "set-site-url.py"), "utf8");
  for (const f of ["agb.html", "datenschutz.html", "impressum.html"]) assert.ok(s.includes(f), `${f} nicht in der Sitemap-Erzeugung`);
});

test("Bestätigungsseite: öffnet die App über sellcheck://, nicht indexiert, Skript extern (strenge CSP), Fehlerfall vorhanden", () => {
  const html = read("bestaetigt.html");
  assert.match(html, /href="sellcheck:\/\/bestaetigt"/, "Knopf zur App fehlt");
  assert.match(html, /<meta name="robots" content="noindex">/, "Seite darf nicht indexiert werden");
  assert.match(html, /<script src="bestaetigt\.js"><\/script>/, "Skript muss extern sein");
  assert.ok(!/<script>[\s\S]*?<\/script>/.test(html), "kein Inline-Skript (CSP)");
  assert.match(html, /id="fehler"[^>]*hidden/, "Fehlerfall (abgelaufener Link) fehlt");
  const js = read("bestaetigt.js");
  assert.match(js, /sellcheck:\/\/bestaetigt/, "Skript öffnet die App nicht");
  assert.match(js, /history\.replaceState/, "Token im Adress-Fragment müssen entfernt werden");
  assert.ok(!/access_token|refresh_token/.test(js.replace(/\/\/.*$/gm, "")), "Tokens dürfen nicht weitergegeben werden");
});
