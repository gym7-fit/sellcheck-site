// Prüft den eingebetteten Film auf der Startseite: Markup, Dateien, Untertitel, CSP.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SITE = path.join(__dirname, "..", "site");
const read = (f) => fs.readFileSync(path.join(SITE, f), "utf8");
const html = read("index.html");
const film = html.slice(html.indexOf('<section id="film"'), html.indexOf("</section>", html.indexOf('<section id="film"')));

test("Film: Video hat Bedienelemente, startet nicht von selbst und lädt erst auf Wunsch", () => {
  assert.ok(film.includes("<video"), "video-Element fehlt");
  assert.match(film, /<video[^>]*\bcontrols\b/);
  assert.match(film, /<video[^>]*\bpreload="none"/);
  assert.match(film, /<video[^>]*\bplaysinline\b/);
  assert.ok(!/\bautoplay\b/.test(film), "Autoplay ist nicht erlaubt");
});

test("Film: Untertitel sind verfügbar, aber nicht standardmäßig an (sie würden Bildtexte im unteren Drittel überdecken)", () => {
  assert.match(film, /<track[^>]*kind="subtitles"[^>]*srclang="de"/);
  assert.ok(!/<track[^>]*\bdefault\b/.test(film));
});

test("Film: alle verlinkten Dateien liegen im Ordner site/", () => {
  const refs = [...film.matchAll(/(?:src|poster|href)="(media\/[^"]+)"/g)].map((m) => m[1]);
  assert.ok(refs.length >= 4, "Quelle, Poster, Untertitel und Download-Link erwartet");
  for (const r of refs) assert.ok(fs.existsSync(path.join(SITE, r)), `${r} fehlt`);
});

test("Film: MP4 ist für das Web gedacht (unter 12 MB, Metadaten am Anfang)", () => {
  const f = path.join(SITE, "media/sellcheck-erklaerfilm.mp4");
  const size = fs.statSync(f).size;
  assert.ok(size < 12 * 1024 * 1024, `zu groß: ${(size / 1048576).toFixed(1)} MB`);
  const head = fs.readFileSync(f).subarray(0, 4096);
  assert.ok(head.includes("moov"), "moov-Atom muss am Dateianfang stehen, sonst startet das Video erst nach vollständigem Laden");
});

test("Film: Untertitel sind gültiges WebVTT, geordnet und innerhalb der Laufzeit", () => {
  const vtt = read("media/sellcheck-erklaerfilm.de.vtt");
  assert.ok(vtt.startsWith("WEBVTT"));
  const toSec = (s) => { const [h, m, x] = s.split(":"); return +h * 3600 + +m * 60 + +x; };
  const cues = [...vtt.matchAll(/(\d\d:\d\d:\d\d\.\d{3}) --> (\d\d:\d\d:\d\d\.\d{3})\n([^\n]+(?:\n[^\n]+)?)/g)]
    .map((m) => ({ a: toSec(m[1]), b: toSec(m[2]), t: m[3] }));
  assert.ok(cues.length >= 10);
  cues.forEach((c, i) => {
    assert.ok(c.b > c.a, `Cue ${i + 1}: Ende vor Anfang`);
    assert.ok(c.b <= 51.0, `Cue ${i + 1}: nach dem Ende des Films`);
    if (i) assert.ok(c.a >= cues[i - 1].b - 0.001, `Cue ${i + 1}: überlappt den vorigen`);
    assert.ok(c.t.split("\n").every((l) => l.length <= 42), `Cue ${i + 1}: Zeile länger als 42 Zeichen`);
  });
});

test("Film: Text zum Film steht auf der Seite (Barrierefreiheit) und nennt die KI-Stimme", () => {
  assert.match(film, /<details[^>]*id="film-text"/);
  assert.match(film, /KI-generierte Stimme/);
  assert.match(film, /aria-describedby="film-text"/);
  assert.match(film, /Beispieldaten/);
});

test("Film: CSP erlaubt Medien nur von der eigenen Origin (Seite und _headers)", () => {
  const csp = html.match(/Content-Security-Policy" content="([^"]+)"/)[1];
  assert.match(csp, /media-src 'self'/);
  assert.ok(!/media-src[^;]*https?:/.test(csp));
  assert.match(read("_headers"), /media-src 'self'/);
});

test("Veröffentlichter Ordner: keine Reste von abgebrochenen Schreibvorgängen oder Systemdateien", () => {
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
  const junk = walk(SITE).filter((f) => /\.sb-[0-9a-f]+-|\.tmp$|\.part$|\.orig$|~$|(^|\/)\.DS_Store$/.test(f));
  assert.deepEqual(junk.map((f) => path.relative(SITE, f)), [], "Reste im site-Ordner, die öffentlich ausgeliefert würden");
});
