// Qualitäts-Checkliste (siehe Merkdatei qualitaets-checkliste): Kreuz = darf nicht vorkommen, Haken = muss da sein.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SITE = path.join(__dirname, "..", "site");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk(SITE).filter((f) => /\.(html|css|js)$/.test(f));
const text = (f) => fs.readFileSync(f, "utf8");
const rel = (f) => path.relative(SITE, f);

test("Kreuz: keine Gedankenstriche (—) und kein spaced ‚ – ‘ in Seitentiteln", () => {
  for (const f of files) {
    const s = text(f);
    assert.ok(!s.includes("—"), `${rel(f)}: Gedankenstrich (—)`);
    for (const m of s.matchAll(/<title>([^<]*)<\/title>/g)) assert.ok(!/ – /.test(m[1]), `${rel(f)}: ‚ – ‘ im Titel`);
  }
});

test("Kreuz: keine echten Emoji als Symbole", () => {
  const emoji = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{26FF}\u{2B50}\u{2705}\u{274C}\u{2728}]/u;
  for (const f of files) assert.ok(!emoji.test(text(f)), `${rel(f)}: Emoji`);
});

test("Kreuz: keine pillenförmigen Knöpfe, Eingaben, Reiter und Auswahl-Chips", () => {
  const selectors = [/(^|\n)\.btn\b[^{]*\{[^}]*\}/, /\.rbtn\s*\{[^}]*\}/, /\.inline-form input\s*\{[^}]*\}/, /\.tool-nav a\s*\{[^}]*\}/, /\.chip span\s*\{[^}]*\}/, /\.demo-plats span\s*\{[^}]*\}/];
  for (const f of files.filter((x) => x.endsWith(".css"))) {
    const css = text(f);
    for (const re of selectors) {
      const m = css.match(re);
      if (m) assert.ok(!/border-radius:\s*(999|99)px/.test(m[0]), `${rel(f)}: Pillenform in ${m[0].slice(0, 40).trim()}`);
    }
  }
});

test("Kreuz: kein lila Verlauf, keine Zähl- oder Scroll-Animationen, kein Cursor-Effekt", () => {
  for (const f of files) {
    const s = text(f);
    if (f.endsWith(".css")) {
      for (const m of s.matchAll(/gradient\([^;]*\)/g)) assert.ok(!/#(8b5cf6|7c3aed|a855f7|6d28d9|9333ea|c084fc)/i.test(m[0]) && !/purple|violet/i.test(m[0]), `${rel(f)}: lila Verlauf`);
    }
    if (f.endsWith(".js")) {
      assert.ok(!/IntersectionObserver/.test(s) || /video|lazy/i.test(s), `${rel(f)}: Scroll-Animation (IntersectionObserver)`);
      assert.ok(!/mousemove|pointermove/.test(s) || /drag|range/i.test(s), `${rel(f)}: Cursor-Effekt`);
    }
    if (f.endsWith(".html")) assert.ok(!/data-count=/.test(s), `${rel(f)}: Zähler-Animation`);
  }
});

test("Kreuz: keine erfundenen Bewertungen, Zähler, Kennzahlen und kein „Made with AI“", () => {
  for (const f of files.filter((x) => x.endsWith(".html"))) {
    const s = text(f).replace(/<script[\s\S]*?<\/script>/g, "");
    assert.ok(!/(\d[\d.,]*\s*(\+|plus)?\s*(zufriedene |aktive )?(nutzer|kunden|verkäufer)\b)(?![^<]*Beispiel)/i.test(s.replace(/Verkäufer(innen)? (zeigen|die|, die)/gi, "")), `${rel(f)}: Zahl von Nutzern/Kunden`);
    assert.ok(!/★|⭐|Sterne\b|Rezension|Testimonial/i.test(s), `${rel(f)}: Bewertung`);
    assert.ok(!/made with (ai|claude|chatgpt)|mit ki erstellt|built with ai|powered by (ai|claude)/i.test(s), `${rel(f)}: KI-Hinweis auf der Seite`);
  }
});

test("Kreuz: typische KI-Floskeln im Text vermeiden", () => {
  const bad = /\b(nahtlos|mühelos|revolutionär|game.?changer|in der heutigen (schnelllebigen )?zeit|tauche ein|entfessle|auf die nächste stufe|ganzheitlich)\b/i;
  for (const f of files.filter((x) => x.endsWith(".html"))) assert.ok(!bad.test(text(f).replace(/<[^>]+>/g, " ")), `${rel(f)}: Floskel`);
});

test("Haken: Nutzungsbedingungen, Datenschutz, Impressum und Favicon sind da und von jeder Seite verlinkt", () => {
  for (const n of ["agb.html", "datenschutz.html", "impressum.html", "favicon.svg"]) assert.ok(fs.existsSync(path.join(SITE, n)), `${n} fehlt`);
  for (const f of files.filter((x) => x.endsWith(".html") && !/(report|404|brand)\.html$/.test(x))) {
    const s = text(f);
    assert.match(s, /agb\.html/, `${rel(f)}: Link zu den Nutzungsbedingungen fehlt`);
    assert.match(s, /datenschutz\.html/, `${rel(f)}: Link zur Datenschutzerklärung fehlt`);
    assert.match(s, /rel="icon"/, `${rel(f)}: Favicon fehlt`);
  }
});

test("Haken: Datenschutz nennt Konto und App", () => {
  assert.match(text(path.join(SITE, "datenschutz.html")), /iPhone-App und Konto/);
});

test("Mobil: Raster-Spalten haben keine feste Mindestbreite über der Bildschirmbreite (min(…, 100%))", () => {
  for (const f of files.filter((x) => x.endsWith(".css"))) {
    for (const m of text(f).matchAll(/minmax\((\d+)px, 1fr\)/g)) assert.ok(+m[1] < 200, `${rel(f)}: minmax(${m[1]}px, 1fr) läuft bei kleinen Bildschirmen über`);
  }
});

test("Scannbar: keine Textwände auf Startseite und Tools (Absätze kurz, lange Antworten mit Liste)", () => {
  for (const page of ["index.html", "tools.html"]) {
    const html = text(path.join(SITE, page)).replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, "");
    for (const m of html.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/g)) {
      const t = m[1].replace(/<[^>]+>/g, "").replace(/&[a-z]+;/g, "x").replace(/\s+/g, " ").trim();
      assert.ok(t.length <= 340, `${page}: Absatz mit ${t.length} Zeichen (Richtwert 340): „${t.slice(0, 60)}…“`);
    }
  }
});

test("Datenschutz: Konto für die App ist in allen Stufen freiwillig (Entscheidung Louis 29.10.2026, wie in FREE-VS-PRO.md der App)", () => {
  const s = fs.readFileSync(path.join(SITE, "datenschutz.html"), "utf8");
  assert.ok(!/legst du ein Konto an/.test(s), "Satz „legst du ein Konto an“ unterstellt Kontopflicht");
  assert.ok(!/erst für Essential und Premium/.test(s), "alte Kontopflicht ab Essential steht noch drin");
  assert.match(s, /ohne Konto, in der kostenlosen Stufe Basic und auch mit Essential oder Premium/);
  assert.match(s, /Ein Konto ist freiwillig/);
});

test("Datenschutz: beschreibt Mein SellCheck im Browser, verneint keine Konten mehr, bleibt Entwurf mit Platzhaltern", () => {
  const s = fs.readFileSync(path.join(SITE, "datenschutz.html"), "utf8");
  const t = text(path.join(SITE, "datenschutz.html"));
  assert.match(t, /Mein SellCheck/);
  assert.ok(s.includes("sellcheck.session.v1"), "Sitzung im Browser genannt");
  assert.ok(!/keine Konten|ohne Konten|gibt es keine Konten/i.test(t), "Satz, der Konten verneint");
  assert.match(s, /<strong>Entwurf, nicht veröffentlichen\.<\/strong>/);
  assert.ok((s.match(/class="ph"/g) || []).length >= 10, "Platzhalter wurden nicht ausgefüllt");
  assert.match(t, /Sicherung und Abgleich/, "Abschnitt 10 nennt den Abgleich");
  assert.ok(!/Datensicherung \(freiwillig\)/.test(t), "alte Beschreibung der Sicherung");
  for (const w of ["Anmelden und Registrieren", "Laden und Speichern", "verkleinert", "Übernahme und Datei-Import", "Export", "Konto löschen", "Gelöschte Artikel", "90 Tage"]) assert.ok(t.includes(w), w + " fehlt");
  assert.ok(!/[—–]/.test(t), "Gedankenstrich");
});
