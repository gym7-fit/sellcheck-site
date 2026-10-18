#!/usr/bin/env python3
"""Setzt die Adresse der Seite in Link-Vorschau (og:url, og:image, canonical) und schreibt sitemap.xml.

Aufruf im Repo-Hauptordner:
    python3 scripts/set-site-url.py https://sellcheck.de/

Ohne Argument wird die aktuelle Adresse angezeigt. Die Adresse muss mit https:// beginnen und auf / enden.
Die Hilfeseiten bekommen ihre Adresse im Generator (scripts/build-hilfe.py, Konstante SITE_URL); dieses Skript
ändert sie dort mit und erzeugt die Seiten neu.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
GEN = ROOT / "scripts" / "build-hilfe.py"
PAGES = ["index.html", "tools.html", "404.html", "agb.html", "datenschutz.html", "impressum.html", "danke.html", "bestaetigt.html"]


def current():
    m = re.search(r'^SITE_URL = "([^"]+)"', GEN.read_text(encoding="utf-8"), re.M)
    return m.group(1)


def main():
    old = current()
    if len(sys.argv) < 2:
        print("Aktuelle Adresse:", old)
        return
    new = sys.argv[1]
    if not re.fullmatch(r"https://[a-z0-9.-]+(/[a-zA-Z0-9._~/-]*)?/", new):
        sys.exit("Adresse muss mit https:// beginnen und mit / enden, zum Beispiel https://sellcheck.de/")
    for name in PAGES:
        p = SITE / name
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    GEN.write_text(GEN.read_text(encoding="utf-8").replace(f'SITE_URL = "{old}"', f'SITE_URL = "{new}"'), encoding="utf-8")
    subprocess.run([sys.executable, str(GEN)], check=True, cwd=ROOT)
    urls = [new] + [new + n for n in ("tools.html", "agb.html", "datenschutz.html", "impressum.html", "hilfe/")] + [f"{new}hilfe/{p.name}" for p in sorted((SITE / "hilfe").glob("*.html")) if p.name != "index.html"]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{u}</loc></url>" for u in urls]
    sm.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    print(f"Adresse {old} -> {new}; sitemap.xml mit {len(urls)} Seiten geschrieben")
    print("Vor dem Livegang außerdem: noindex-Tags und site/robots.txt anpassen (docs/LIVEGANG.md, Abschnitt 3a).")


if __name__ == "__main__":
    main()
