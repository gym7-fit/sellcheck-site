#!/usr/bin/env python3
"""Erzeugt sechs Logo-Vorschläge für SellCheck als SVG (Zeichen + Wortmarke) und eine Vergleichsseite.

    python3 marketing/logo-optionen/build_logos.py

Alles ist reine Vektorgrafik. Die Wortmarke ist eine selbst gezeichnete Strich-Schrift (keine Systemschrift),
daher gibt es keine Lizenzfragen und sie braucht keine Schrift auf dem Rechner.
Das ist ein Entwurfsstand für die Auswahl, kein fertiges Corporate Design.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INK, LIME, PAPER = "#0E1116", "#C8F169", "#F6F4EE"
RED, AMBER, GREEN = "#E84E3E", "#F2B22C", "#2EBE6E"
GREY1, GREY2 = "#2C333D", "#56606D"

# ---- Wortmarke: Strichbuchstaben, Strichstärke 7, runde Enden. Grundlinie y=44, Oberlänge y=4, x-Höhe y=16
LETTERS = {
    "S": ("M25 13 C23 8 18 5 13 5 C7 5 3 8.5 3 13.5 C3 19 8 21 14 23.5 C20 26 25 28.5 25 34.5 C25 40.5 20 44 13 44 C7.5 44 3 41.5 1.5 36", 28),
    "e": ("M4 30 H26 C26 21 21 16 15 16 C8 16 4 21.5 4 30 C4 38.5 8.5 44 15 44 C20 44 24 41.5 26 37.5", 30),
    "l": ("M4 4 V44", 8),
    "C": ("M30 12 C27 7.5 22.5 5 17.5 5 C9.5 5 4 11.5 4 24.5 C4 37.5 9.5 44 17.5 44 C22.5 44 27 41.5 30 37", 34),
    "h": ("M4 4 V44 M4 29 C4 21 9 16 16 16 C23 16 26 21 26 29 V44", 30),
    "c": ("M26 22 C24 18.5 20 16 15.5 16 C8 16 4 21.5 4 30 C4 38.5 8 44 15.5 44 C20 44 24 41.5 26 38", 30),
    "k": ("M4 4 V44 M26 17 L5 32.5 M13 27 L27 44", 31),
}


def wordmark(color_sell, color_check, x0=0.0, y0=0.0, scale=1.0, gap=7.0):
    parts = []
    x = 0.0
    word = "SellCheck"
    for i, ch in enumerate(word):
        d, w = LETTERS[ch]
        col = color_sell if i < 4 else color_check
        parts.append(f'<path d="{d}" transform="translate({x:.1f} 0)" stroke="{col}"/>')
        x += w + gap
    width = x - gap
    g = (f'<g transform="translate({x0} {y0}) scale({scale})" fill="none" stroke-width="7" '
         f'stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</g>')
    return g, width * scale


# ---- Zeichen (64x64). Jedes liefert (svg-Inhalt, Name, Beschreibung)
def mark_tag(bg=None):
    return (f'<path fill="{LIME}" fill-rule="evenodd" d="M14 4h24l22 22v28a10 10 0 0 1-10 10H14A10 10 0 0 1 4 54V14A10 10 0 0 1 14 4Zm29 13.8a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4Z"/>'
            f'<path d="M17 36l8 8 15-15" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>')


def mark_ampel():
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{LIME}"/>'
            f'<rect x="20" y="8" width="24" height="48" rx="12" fill="{INK}"/>'
            f'<circle cx="32" cy="20" r="6.2" fill="{RED}"/><circle cx="32" cy="32" r="6.2" fill="{AMBER}"/>'
            f'<circle cx="32" cy="44" r="6.2" fill="{GREEN}"/>'
            f'<path d="M28.6 44.2l2.6 2.7 4.8-5.4" fill="none" stroke="{INK}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')


def mark_gauge():
    import math
    cx, cy, r = 32, 41, 21

    def pt(a):
        return cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a))
    segs = [(180, 122, GREEN), (118, 62, AMBER), (58, 0, RED)]
    out = [f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{INK}" stroke="#3A424D" stroke-width="1.6"/>']
    for a0, a1, c in segs:
        x0, y0 = pt(a0)
        x1, y1 = pt(a1)
        out.append(f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{c}" stroke-width="7.5" stroke-linecap="round"/>')
    out.append(f'<path d="M24 47l5.5 5.5L41 40" fill="none" stroke="{LIME}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
    return "".join(out)


def mark_monogram():
    d, w = LETTERS["S"]
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{INK}" stroke="#3A424D" stroke-width="1.6"/>'
            f'<path d="{d}" transform="translate(17 8) scale(1.0)" fill="none" stroke="{PAPER}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="49" cy="15" r="10" fill="{LIME}"/>'
            f'<path d="M44.2 15.2l3.4 3.4 6-6.8" fill="none" stroke="{INK}" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>')


def mark_stack():
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{INK}" stroke="#3A424D" stroke-width="1.6"/>'
            f'<rect x="10" y="10" width="26" height="26" rx="7" fill="{GREY1}" stroke="{GREY2}" stroke-width="1.5"/>'
            f'<rect x="18" y="18" width="26" height="26" rx="7" fill="{GREY2}"/>'
            f'<rect x="27" y="27" width="27" height="27" rx="7.5" fill="{LIME}"/>'
            f'<path d="M33 41l5 5 10-11" fill="none" stroke="{INK}" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round"/>')


def mark_receipt():
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{INK}" stroke="#3A424D" stroke-width="1.6"/>'
            f'<path d="M17 9H47V55L42.5 51 38 55 33.5 51 29 55 24.5 51 20 55 17 52Z" fill="{LIME}" stroke="{LIME}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M23 31l6.5 6.5L42 23" fill="none" stroke="{INK}" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/>')


OPTIONS = [
    ("1", "Preisschild", "Das bisherige Zeichen, sauber nachgezeichnet. Preisschild (Verkaufen) mit Haken (Check).", mark_tag),
    ("2", "Ampel", "Die Meldegrenzen-Ampel als Zeichen. Zeigt sofort, was das Produkt tut. Mit Haken im grünen Licht.", mark_ampel),
    ("3", "Tacho", "Tacho mit Ampelfarben und Haken. Passt zum Fortschrittsbalken „wie weit bin ich?“.", mark_gauge),
    ("4", "Monogramm S", "Ein S mit Haken-Siegel. Ruhig, markentauglich, wirkt am erwachsensten.", mark_monogram),
    ("5", "Stapel", "Mehrere Plattformen übereinander, vorn der Haken. „Alles an einem Ort“.", mark_stack),
    ("6", "Beleg", "Kassenbon mit Haken. Verweist auf Steuer-Report und Belege.", mark_receipt),
]


def svg_mark(fn, size=64):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" role="img" aria-label="SellCheck Zeichen">{fn()}</svg>'


def svg_lockup(fn, dark=True):
    wm, w = wordmark(PAPER if dark else INK, LIME if dark else "#2A7A18", x0=84, y0=8, scale=1.0)
    total = 84 + w + 4
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total:.0f} 64" role="img" aria-label="SellCheck">'
            f'<g>{fn()}</g>{wm}</svg>')


def main():
    os.makedirs(os.path.join(HERE, "svg"), exist_ok=True)
    cards = []
    for num, name, desc, fn in OPTIONS:
        open(os.path.join(HERE, "svg", f"option-{num}-zeichen.svg"), "w", encoding="utf-8").write(svg_mark(fn))
        open(os.path.join(HERE, "svg", f"option-{num}-logo-dunkel.svg"), "w", encoding="utf-8").write(svg_lockup(fn, True))
        open(os.path.join(HERE, "svg", f"option-{num}-logo-hell.svg"), "w", encoding="utf-8").write(svg_lockup(fn, False))
        small = "".join(f'<span style="display:inline-block;margin-right:14px;vertical-align:middle">{svg_mark(fn, s)}</span>' for s in (56, 36, 24, 16))
        cards.append(f'''<section class="opt">
  <h2><span class="n">{num}</span>{name}</h2>
  <p class="d">{desc}</p>
  <div class="row"><div class="tile dark">{svg_lockup(fn, True)}</div></div>
  <div class="row"><div class="tile light">{svg_lockup(fn, False)}</div></div>
  <div class="row small"><div class="tile dark">{small}</div><div class="tile light">{small}</div></div>
</section>''')
    html = f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><title>SellCheck Logo-Vorschläge</title>
<style>
body{{margin:0;background:#e9e7df;font-family:"Avenir Next",system-ui,sans-serif;color:#0e1116}}
.wrap{{max-width:1500px;margin:0 auto;padding:36px 32px 60px}}
h1{{font-size:32px;margin:0 0 6px}} .lead{{color:#565c68;margin:0 0 28px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}}
.opt{{background:#fff;border-radius:22px;padding:22px 22px 24px}}
.opt h2{{margin:0 0 4px;font-size:22px;display:flex;align-items:center;gap:10px}}
.n{{display:inline-grid;place-items:center;width:34px;height:34px;border-radius:50%;background:#0e1116;color:#c8f169;font-size:17px}}
.d{{margin:0 0 14px;color:#565c68;font-size:15px;line-height:1.4;min-height:42px}}
.tile{{border-radius:14px;padding:18px 20px;display:flex;align-items:center}}
.tile.dark{{background:#0e1116}} .tile.light{{background:#f6f4ee;border:1px solid #e2dfd4}}
.tile svg{{height:56px;width:auto;display:block}}
.row{{margin-bottom:10px}} .row.small{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0}}
.row.small .tile svg{{height:auto}}
</style></head><body><div class="wrap">
<h1>SellCheck: sechs Logo-Vorschläge</h1>
<p class="lead">Je Vorschlag: Zeichen mit Wortmarke auf dunklem und hellem Grund, darunter das Zeichen in vier kleinen Größen (56, 36, 24, 16 px). Die Wortmarke ist bei allen gleich.</p>
<div class="grid">{"".join(cards)}</div></div></body></html>'''
    open(os.path.join(HERE, "logo-optionen.html"), "w", encoding="utf-8").write(html)
    print("Fertig:", os.path.join(HERE, "logo-optionen.html"))


if __name__ == "__main__":
    main()
