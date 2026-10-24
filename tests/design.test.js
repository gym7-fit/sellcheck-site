// Design-System (Redesign 10/2026, Stand 24.10.): Regeln aus DESIGN.md, die sich maschinell prüfen lassen.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SITE = path.join(__dirname, "..", "site");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk(SITE);
const html = files.filter((f) => f.endsWith(".html"));
const css = files.filter((f) => f.endsWith(".css"));
const read = (f) => fs.readFileSync(f, "utf8");
const rel = (f) => path.relative(SITE, f);

test("Keine Inline-Styles in den Seiten (alles über Klassen und Tokens)", () => {
  for (const f of html) assert.ok(!/\sstyle="/.test(read(f)), `${rel(f)}: style="…" gefunden`);
});

test("Eckradien nur aus den Tokens (20, 12, 8), Kreise oder kleine Marken bis 6 px", () => {
  const ok = /^(var\(--radius(-sm|-xs)?(, ?\d+px)?\)|50%|0|[2-6]px)$/;
  for (const f of css) {
    for (const m of read(f).matchAll(/border-radius:\s*([^;}]+)/g)) {
      for (const part of m[1].trim().split(/\s+(?![^(]*\))/)) assert.match(part, ok, `${rel(f)}: border-radius ${m[1].trim()}`);
    }
  }
  const root = read(path.join(SITE, "style.css"));
  assert.match(root, /--radius: 20px/);
  assert.match(root, /--radius-sm: 12px/);
  assert.match(root, /--radius-xs: 8px/);
});

test("Schrift: Archivo liegt lokal, mit Lizenz, unter 100 KB, kein Abruf von fremden Servern", () => {
  const woff = path.join(SITE, "fonts", "archivo.woff2");
  assert.ok(fs.existsSync(woff), "Schriftdatei fehlt");
  assert.ok(fs.statSync(woff).size < 100 * 1024, "Schrift über 100 KB");
  assert.match(read(path.join(SITE, "fonts", "LICENSE-archivo.txt")), /SIL Open Font License/);
  const style = read(path.join(SITE, "style.css"));
  assert.match(style, /@font-face\s*\{[^}]*font-family: "Archivo";[^}]*url\("fonts\/archivo\.woff2"\)/);
  assert.match(style, /--font: "Archivo"/);
  for (const f of html) {
    const pre = read(f).match(/<link rel="preload" href="([^"]+)" as="font"/);
    if (pre) assert.match(pre[1], /archivo\.woff2$/, `${rel(f)}: lädt eine andere Schrift vor`);
  }
  for (const f of css) assert.ok(!/url\(["']?https?:/.test(read(f)), `${rel(f)}: Schrift oder Bild von außen`);
});

test("Keine Versal-Etiketten und kein Vorspann über Überschriften (eyebrow)", () => {
  for (const f of css) assert.ok(!/text-transform:\s*uppercase/.test(read(f)), `${rel(f)}: text-transform: uppercase`);
  for (const f of html) assert.ok(!/class="[^"]*\beyebrow\b/.test(read(f)), `${rel(f)}: eyebrow-Vorspann`);
});

test("Farben entschärft (Entscheidung Louis 24.10.2026): weißer Grund, dunkel ist nur der Fuß", () => {
  const style = read(path.join(SITE, "style.css"));
  const root = style.slice(style.indexOf(":root {"), style.indexOf("}", style.indexOf(":root {")));
  assert.match(root, /--bg: #ffffff;/, "heller Grund ist Weiß, kein Creme");
  for (const f of html) {
    const s = read(f);
    for (const m of s.matchAll(/<(\w+)\b[^>]*class="([^"]*\bon-dark\b[^"]*)"/g)) assert.equal(m[1], "footer", `${rel(f)}: dunkle Fläche außerhalb des Fußes (${m[1]}.${m[2]})`);
    assert.ok(!/<body[^>]*class="[^"]*on-dark/.test(s), `${rel(f)}: ganze Seite dunkel`);
  }
  // Lime ist Signal, keine Fläche: der normale Knopf ist Tinte, Lime nur über .btn.signal und im dunklen Modus
  assert.match(style, /\.btn \{[^}]*background: var\(--btn-bg\)/);
  assert.match(style, /--btn-bg: #111418;/);
});

test("Seitenüberschriften ohne Schlusspunkt, nur der Claim behält ihn", () => {
  for (const f of html) {
    for (const m of read(f).matchAll(/<h([1-3])[^>]*>([^<]+)<\/h\1>/g)) {
      if (m[2].trim() !== "Check, was wirklich bleibt.") assert.ok(!/\.$/.test(m[2].trim()), `${rel(f)}: Überschrift mit Punkt: ${m[2].trim()}`);
    }
  }
});

test("Keine Pfeile an Knöpfen und Links, keine Mittelpunkte als Trenner", () => {
  for (const f of files.filter((x) => /\.(html|js)$/.test(x))) {
    const s = read(f);
    assert.ok(!/←/.test(s), `${rel(f)}: Pfeil ←`);
    assert.ok(!/ · /.test(s), `${rel(f)}: Mittelpunkt als Trenner`);
    assert.ok(!/M5 12h14M13 6l6 6-6 6/.test(s), `${rel(f)}: Pfeil-Symbol`);
    for (const m of s.matchAll(/<(a|button)\b[^>]*class="[^"]*\bbtn\b[^"]*"[^>]*>([^<]*)</g)) assert.ok(!/→/.test(m[2]), `${rel(f)}: Pfeil im Knopf ${m[2].trim()}`);
  }
});

test("Beträge und Zähler haben Ziffern mit fester Breite", () => {
  const style = read(path.join(SITE, "style.css"));
  assert.match(style, /\.num,[^{]*\{[^}]*font-variant-numeric: tabular-nums/);
});
