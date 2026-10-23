// Statische Barrierefreiheits-Prüfung: Sprache, Landmarks, Überschriften, Alt-Texte, Beschriftungen,
// Kontrast der Farbwerte und keine Drittanbieter-Einbindungen. Die Browser-Prüfung (axe) läuft nicht in CI.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SITE = path.join(__dirname, "..", "site");
const OWN_HOST = fs.readFileSync(path.join(__dirname, "..", "scripts", "build-hilfe.py"), "utf8").match(/^SITE_URL = "https:\/\/([^"]+)"/m)[1];
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const PAGES = walk(SITE).filter((f) => f.endsWith(".html")).map((f) => ({ name: path.relative(SITE, f), html: fs.readFileSync(f, "utf8") }));
// Vom Test ausgenommen: Seiten, die nur als Vorlage oder Ausgabe dienen
const strip = (h) => h.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "").replace(/<!--[\s\S]*?-->/g, "");

test("Seiten: Sprache, Titel, Viewport und genau ein h1", () => {
  assert.ok(PAGES.length >= 13);
  for (const { name, html } of PAGES) {
    assert.match(html, /<html[^>]*\blang="de"/, `${name}: lang fehlt`);
    assert.match(html, /<title>[^<]{3,}<\/title>/, `${name}: Titel fehlt`);
    assert.match(html, /<meta name="viewport" content="[^"]*width=device-width/, `${name}: viewport fehlt`);
    assert.ok(!/user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b/.test(html), `${name}: Zoomen darf nicht gesperrt sein`);
    if (name === "report.html") continue; // h1 entsteht im Skript
    assert.equal((strip(html).match(/<h1[\s>]/g) || []).length, 1, `${name}: genau ein h1 erwartet`);
  }
});

test("Seiten: ein main-Landmark und Sprunglink dorthin", () => {
  for (const { name, html } of PAGES) {
    assert.equal((html.match(/<main[\s>]/g) || []).length, 1, `${name}: genau ein <main>`);
    if (name === "report.html") continue;
    assert.match(html, /<main[^>]*\bid="main"/, `${name}: main braucht id="main"`);
    if (name !== "404.html") assert.match(html, /href="#main"/, `${name}: Sprunglink fehlt`); // 404 hat keine Navigation
  }
});

test("Seiten: Überschriften überspringen keine Ebene", () => {
  for (const { name, html } of PAGES) {
    const levels = [...strip(html).matchAll(/<h([1-6])[\s>]/g)].map((m) => +m[1]);
    levels.forEach((l, i) => {
      if (i) assert.ok(l <= levels[i - 1] + 1, `${name}: h${levels[i - 1]} → h${l} (Position ${i + 1})`);
    });
  }
});

test("Seiten: Bilder haben alt, Eingabefelder eine Beschriftung", () => {
  for (const { name, html } of PAGES) {
    const body = strip(html);
    for (const m of body.matchAll(/<img\b[^>]*>/g)) assert.match(m[0], /\balt="/, `${name}: Bild ohne alt: ${m[0].slice(0, 70)}`);
    for (const m of body.matchAll(/<(input|select|textarea)\b([^>]*)>/g)) {
      const a = m[2];
      if (/type="(hidden|submit|button|reset)"/.test(a) || /aria-hidden="true"/.test(a)) continue; // verstecktes Spam-Feld ist für Tastatur und Screenreader nicht erreichbar
      const id = (a.match(/\bid="([^"]+)"/) || [])[1];
      const labelled = /aria-label(ledby)?="/.test(a) || (id && new RegExp(`for="${id}"`).test(body));
      // Eingaben innerhalb eines <label>…</label> sind ebenfalls beschriftet
      const wrapped = new RegExp(`<label[^>]*>(?:(?!</label>)[\\s\\S])*${m[0].replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`).test(body);
      assert.ok(labelled || wrapped, `${name}: Eingabe ohne Beschriftung: ${m[0].slice(0, 80)}`);
    }
    for (const m of body.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)) {
      const text = m[1].replace(/<[^>]+>/g, "").trim();
      assert.ok(text || /aria-label="/.test(m[0]), `${name}: Knopf ohne Namen`);
    }
  }
});

test("Seiten: ARIA-Rollen sitzen auf passenden Elementen (tabpanel nicht auf article)", () => {
  for (const { name, html } of PAGES) {
    assert.ok(!/<article[^>]*role="tabpanel"/.test(html), `${name}: role=tabpanel auf <article>`);
  }
});

test("Farben: Textfarben erreichen 4,5:1 auf ihren Flächen (hell)", () => {
  const css = fs.readFileSync(path.join(SITE, "style.css"), "utf8");
  const root = css.match(/:root\s*\{([\s\S]*?)\n\}/)[1];
  const v = (n) => root.match(new RegExp(`--${n}:\\s*(#[0-9a-fA-F]{6})`))[1];
  const lum = (h) => {
    const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const grounds = ["bg", "surface", "surface-2"].map((n) => [n, v(n)]);
  for (const [fg, soft] of [["green", "green-soft"], ["yellow", "yellow-soft"], ["red", "red-soft"]]) {
    for (const [gn, g] of [...grounds, [soft, v(soft)]]) {
      const r = ratio(v(fg), g);
      assert.ok(r >= 4.5, `--${fg} auf --${gn}: ${r.toFixed(2)}:1`);
    }
  }
  for (const [gn, g] of grounds) assert.ok(ratio(v("muted"), g) >= 4.5, `--muted auf --${gn}`);
});

test("Datenschutz: keine Drittanbieter-Einbindungen (Skripte, Schriften, Bilder, Frames, Formulare)", () => {
  const files = walk(SITE).filter((f) => /\.(html|css|js)$/.test(f));
  for (const f of files) {
    const s = fs.readFileSync(f, "utf8");
    const rel = path.relative(SITE, f);
    if (rel.endsWith(".html")) {
      for (const m of s.matchAll(/<(script|img|iframe|link|source|video|audio|form)\b[^>]*\b(?:src|href|action)="(https?:)?\/\/([^"]+)"/g)) {
        // Eigene Adresse der Seite (z. B. in der 404-Seite, die unter beliebigen Pfaden ausgeliefert wird) ist keine Einbindung von außen
        if (m[3].startsWith(OWN_HOST)) continue;
        // normale Verweise (<a>) sind keine Einbindungen; <link rel="canonical"> und Open-Graph-Angaben zeigen auf die eigene Seite
        if (m[1] === "link" && /rel="(canonical|alternate)"/.test(m[0])) continue;
        assert.fail(`${rel}: Einbindung von außen: ${m[0].slice(0, 100)}`);
      }
    }
    assert.ok(!/@import\s+url\(["']?https?:/.test(s), `${rel}: @import von außen`);
    assert.ok(!/url\(["']?https?:\/\//.test(s) || rel.endsWith(".js"), `${rel}: url() von außen`);
    if (rel.endsWith(".js")) assert.ok(!/\b(fetch|XMLHttpRequest|sendBeacon)\b[^;\n]*https?:\/\//.test(s), `${rel}: Netzwerkaufruf nach außen`);
  }
});

test("Texte: Knöpfe sagen, was passiert (kein nacktes „Weiter“, „Absenden“, „Speichern“)", () => {
  const vague = /^(weiter|absenden|speichern|submit|ok|senden|details|einlesen|übernehmen)$/i;
  for (const { name, html } of PAGES) {
    for (const m of strip(html).matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)) {
      const text = m[1].replace(/<[^>]+>/g, "").trim();
      assert.ok(!vague.test(text), `${name}: unklarer Knopf „${text}“`);
    }
  }
});

test("Fehler: Formulare zeigen Fehler am Feld (fielderr.js eingebunden, SCField genutzt)", () => {
  for (const page of ["index.html", "tools.html"]) {
    assert.match(fs.readFileSync(path.join(SITE, page), "utf8"), /<script src="fielderr\.js"><\/script>/, `${page}: fielderr.js fehlt`);
  }
  for (const f of ["waitlist.js", "gate.js", "tools.js"]) {
    assert.match(fs.readFileSync(path.join(SITE, f), "utf8"), /SCField\.show\(/, `${f}: Fehler nicht am Feld`);
  }
  const css = fs.readFileSync(path.join(SITE, "style.css"), "utf8");
  assert.match(css, /\.field-error\b/);
  assert.match(css, /\[aria-invalid="true"\]/);
});

test("Tippflächen: Knöpfe, aufklappbare Fragen und Ja/Nein-Auswahl sind mindestens 44 px hoch", () => {
  const css = fs.readFileSync(path.join(SITE, "style.css"), "utf8");
  for (const sel of ["\\.btn", "summary", "\\.quiz-opt"]) {
    assert.match(css, new RegExp(`(^|\\n)${sel} \\{[^}]*min-height: 44px`), `${sel} ohne min-height: 44px`);
  }
  const landing = fs.readFileSync(path.join(SITE, "landing.css"), "utf8");
  assert.match(landing, /\.demo-card input\[type="range"\] \{[^}]*height: 44px/);
});

test("Bewegung: Einblendungen und Übergänge dauern höchstens 300 ms", () => {
  for (const f of ["style.css", "landing.css", "wizard.css", "gate.css", "report.css", "hilfe.css"]) {
    const p = path.join(SITE, f);
    if (!fs.existsSync(p)) continue;
    const css = fs.readFileSync(p, "utf8");
    for (const m of css.matchAll(/(?:animation|transition)(?:-duration)?:[^;}]*/g)) {
      for (const d of m[0].matchAll(/(\d*\.?\d+)(m?s)\b/g)) {
        const ms = d[2] === "ms" ? Number(d[1]) : Number(d[1]) * 1000;
        assert.ok(ms <= 300, `${f}: ${m[0].trim()} (${ms} ms)`);
      }
    }
  }
});
