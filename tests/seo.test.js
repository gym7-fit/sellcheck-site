// Prüft Link-Vorschau (Open Graph), canonical und Touch-Icon der öffentlichen Seiten.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..");
const SITE = path.join(ROOT, "site");
const BASE = fs.readFileSync(path.join(ROOT, "scripts/build-hilfe.py"), "utf8").match(/^SITE_URL = "([^"]+)"/m)[1];
const PAGES = ["index.html", "tools.html", ...fs.readdirSync(path.join(SITE, "hilfe")).filter((f) => f.endsWith(".html")).map((f) => "hilfe/" + f)];
const meta = (html, key) => {
  const m = html.match(new RegExp(`<meta (?:property|name)="${key}" content="([^"]*)"`));
  return m && m[1];
};
const pngSize = (f) => { const b = fs.readFileSync(f); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };

test("Adresse der Seite: https, endet auf /", () => {
  assert.match(BASE, /^https:\/\/[a-z0-9.-]+(\/[a-zA-Z0-9._~/-]*)?\/$/);
});

for (const page of PAGES) {
  test(`Link-Vorschau: ${page}`, () => {
    const html = fs.readFileSync(path.join(SITE, page), "utf8");
    const canonical = html.match(/<link rel="canonical" href="([^"]+)"/);
    assert.ok(canonical, "canonical fehlt");
    const rel = page === "index.html" ? "" : page === "hilfe/index.html" ? "hilfe/" : page;
    assert.equal(canonical[1], BASE + rel, "canonical passt nicht zur Seite");
    assert.equal(meta(html, "og:url"), canonical[1]);
    const title = meta(html, "og:title");
    const desc = meta(html, "og:description");
    assert.ok(title && title.length <= 70, `og:title fehlt oder zu lang (${title && title.length})`);
    assert.ok(desc && desc.length >= 40 && desc.length <= 200, `og:description fehlt oder Länge unpassend (${desc && desc.length})`);
    assert.equal(meta(html, "og:locale"), "de_DE");
    assert.equal(meta(html, "twitter:card"), "summary_large_image");
    const img = meta(html, "og:image");
    assert.ok(img.startsWith(BASE), "og:image muss absolut sein und zur Seitenadresse passen");
    const file = path.join(SITE, img.slice(BASE.length));
    assert.ok(fs.existsSync(file), `${img} liegt nicht in site/`);
    assert.deepEqual(pngSize(file), [+meta(html, "og:image:width"), +meta(html, "og:image:height")]);
    assert.ok(meta(html, "og:image:alt"));
    assert.ok(html.includes('rel="apple-touch-icon"'));
  });
}

test("Touch-Icon ist 180 x 180 und Titel sind eindeutig", () => {
  assert.deepEqual(pngSize(path.join(SITE, "apple-touch-icon.png")), [180, 180]);
  const titles = PAGES.map((p) => fs.readFileSync(path.join(SITE, p), "utf8").match(/<title>([^<]+)<\/title>/)[1]);
  assert.equal(new Set(titles).size, titles.length, "doppelte Seitentitel");
});

test("Mein SellCheck: in keiner Kopfzeile, nur im Fuß; Konto-Seiten mit noindex und nicht in der Sitemap", () => {
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
  const ACCOUNT = ["anmelden.html", "registrieren.html", "mein.html"];
  for (const f of walk(SITE).filter((x) => x.endsWith(".html"))) {
    const rel = path.relative(SITE, f), h = fs.readFileSync(f, "utf8");
    for (const head of h.match(/<header[\s\S]*?<\/header>/g) || []) {
      assert.ok(!/anmelden\.html|mein\.html|registrieren\.html|Mein SellCheck/.test(head), rel + ": Konto-Link in der Kopfzeile");
    }
    if (/<footer/.test(h) && h.includes("Gratis-Tools")) assert.match(h, /<footer[\s\S]*href="(\.\.\/)?anmelden\.html">Mein SellCheck</, rel + ": Link im Fuß");
  }
  for (const f of ACCOUNT) assert.match(fs.readFileSync(path.join(SITE, f), "utf8"), /<meta name="robots" content="noindex">/, f);
  const sm = path.join(SITE, "sitemap.xml");
  const sitemap = (fs.existsSync(sm) ? fs.readFileSync(sm, "utf8") : "") + fs.readFileSync(path.join(ROOT, "scripts/set-site-url.py"), "utf8").match(/urls = \[[^\n]*\n/)[0];
  for (const f of ACCOUNT) assert.ok(!sitemap.includes(f), f + " steht in der Sitemap");
});
