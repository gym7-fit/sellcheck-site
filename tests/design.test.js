// Design-System Richtung C (Redesign 10/2026): Regeln aus DESIGN.md, die sich maschinell prüfen lassen.
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

test("Schrift: Bricolage Grotesque liegt lokal, mit Lizenz, unter 100 KB, kein Abruf von fremden Servern", () => {
  const woff = path.join(SITE, "fonts", "bricolage-grotesque.woff2");
  assert.ok(fs.existsSync(woff), "Schriftdatei fehlt");
  assert.ok(fs.statSync(woff).size < 100 * 1024, "Schrift über 100 KB");
  assert.match(read(path.join(SITE, "fonts", "LICENSE-bricolage-grotesque.txt")), /SIL Open Font License/);
  const style = read(path.join(SITE, "style.css"));
  assert.match(style, /@font-face\s*\{[^}]*font-family: "Bricolage";[^}]*url\("fonts\/bricolage-grotesque\.woff2"\)/);
  assert.match(style, /--font: "Bricolage"/);
  for (const f of css) assert.ok(!/url\(["']?https?:/.test(read(f)), `${rel(f)}: Schrift oder Bild von außen`);
});

test("Keine Versal-Etiketten und kein Vorspann über Überschriften (eyebrow)", () => {
  for (const f of css) assert.ok(!/text-transform:\s*uppercase/.test(read(f)), `${rel(f)}: text-transform: uppercase`);
  for (const f of html) assert.ok(!/class="[^"]*\beyebrow\b/.test(read(f)), `${rel(f)}: eyebrow-Vorspann`);
});

test("Rhythmus der Startseite: dunkler Block oben, Inhalt auf Papier, dunkler Abschluss", () => {
  const s = read(path.join(SITE, "index.html"));
  const order = [...s.matchAll(/<(?:div|section|footer)\b[^>]*class="([^"]*)"[^>]*>/g)].map((m) => m[1]).filter((c) => c.split(/\s+/).some((t) => ["hero", "platform-strip", "demo", "problem", "film", "tint", "final", "on-dark", "trust"].includes(t)));
  const dark = order.map((c) => /\bon-dark\b/.test(c));
  const firstLight = dark.indexOf(false);
  assert.ok(firstLight > 2, "Hero, Plattformen und Ampel sind ein durchgehender dunkler Block");
  const lastLight = dark.lastIndexOf(false);
  assert.ok(dark.slice(firstLight, lastLight + 1).every((d) => !d), "keine dunklen Inseln zwischen den Papier-Abschnitten");
  assert.ok(dark.slice(lastLight + 1).length >= 2, "Abschluss und Fuß sind dunkel");
});

test("Beträge und Zähler haben Ziffern mit fester Breite", () => {
  const style = read(path.join(SITE, "style.css"));
  assert.match(style, /\.num,[^{]*\{[^}]*font-variant-numeric: tabular-nums/);
});
