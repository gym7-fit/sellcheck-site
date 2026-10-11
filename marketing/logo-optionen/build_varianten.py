#!/usr/bin/env python3
"""Zweite Runde: je drei Varianten für Preisschild (1) und Beleg (6) mit verschiedenen Schriftarten.

    python3 marketing/logo-optionen/build_varianten.py

Die Schriften sind hier Systemschriften des Macs, nur zum Vergleichen. Für ein veröffentlichtes Logo
ist eine frei lizenzierte Entsprechung (steht im Kästchen) die sichere Wahl.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INK, LIME, PAPER = "#0E1116", "#C8F169", "#F6F4EE"
DEEP = "#2A7A18"      # Check-Farbe auf hellem Grund
EDGE = "#3A424D"

TAG_D = "M14 4h24l22 22v28a10 10 0 0 1-10 10H14A10 10 0 0 1 4 54V14A10 10 0 0 1 14 4Zm29 13.8a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4Z"
TICK = "M17 36l8 8 15-15"
RECEIPT_D = "M17 9H47V55L42.5 51 38 55 33.5 51 29 55 24.5 51 20 55 17 52Z"


def svg(inner, size=56):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" aria-hidden="true">{inner}</svg>'


# --- Zeichen
def tag_plain(on_dark=True):
    return (f'<path fill="{LIME}" fill-rule="evenodd" d="{TAG_D}"/>'
            f'<path d="{TICK}" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>')


def tag_tilt(on_dark=True):
    return (f'<g transform="rotate(-14 32 32) translate(3 3) scale(0.9)">'
            f'<path fill="{LIME}" fill-rule="evenodd" d="{TAG_D}"/>'
            f'<path d="{TICK}" fill="none" stroke="{INK}" stroke-width="7.5" stroke-linecap="round" stroke-linejoin="round"/></g>')


def tag_in_square(on_dark=True):
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{LIME}"/>'
            f'<g transform="translate(6.4 6.4) scale(0.8)"><path fill="{INK}" fill-rule="evenodd" d="{TAG_D}"/>'
            f'<path d="{TICK}" fill="none" stroke="{LIME}" stroke-width="7.5" stroke-linecap="round" stroke-linejoin="round"/></g>')


def receipt_boxed(on_dark=True):
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{INK}" stroke="{EDGE}" stroke-width="1.6"/>'
            f'<path d="{RECEIPT_D}" fill="{LIME}" stroke="{LIME}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M23 31l6.5 6.5L42 23" fill="none" stroke="{INK}" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/>')


def receipt_naked(on_dark=True):
    fill = LIME if on_dark else INK
    chk = INK if on_dark else LIME
    return (f'<path d="M14 6H50V58L45 53.5 40 58 35 53.5 30 58 25 53.5 20 58 14 53Z" fill="{fill}" stroke="{fill}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M22 30l7.5 7.5L43 22" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/>')


def receipt_lines(on_dark=True):
    return (f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{LIME}"/>'
            f'<path d="{RECEIPT_D}" fill="{INK}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
            f'<rect x="22" y="16" width="20" height="3.6" rx="1.8" fill="{LIME}"/>'
            f'<rect x="22" y="23" width="13" height="3.6" rx="1.8" fill="{LIME}"/>'
            f'<path d="M23 38l5.5 5.5L41 31" fill="none" stroke="{LIME}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')


# --- Varianten: (id, titel, schrift-anzeige, ersatz, css-font, gewicht, tracking, transform, layout, mark, wort-teilung)
VARIANTS = [
    dict(id="1A", group="Preisschild", title="Geometrisch", font_name="Futura Bold", libre="Jost Bold (OFL)",
         css="Futura, 'Avenir Next', sans-serif", weight=700, track="-0.02em", case="none", layout="row", mark=tag_plain, size=52, fs=44,
         note="Klares Preisschild, runde geometrische Schrift. Nüchtern und freundlich."),
    dict(id="1B", group="Preisschild", title="Freundlich", font_name="Arial Rounded MT Bold", libre="Nunito ExtraBold (OFL)",
         css="'Arial Rounded MT Bold', 'Avenir Next', sans-serif", weight=700, track="-0.01em", case="none", layout="row", mark=tag_tilt, size=58, fs=42,
         note="Leicht gekipptes Schild, abgerundete Schrift. Wirkt locker, passt zu TikTok."),
    dict(id="1C", group="Preisschild", title="Kompakt / App-Icon", font_name="DIN Alternate Bold", libre="Barlow Semi Condensed Bold (OFL)",
         css="'DIN Alternate', 'Avenir Next Condensed', sans-serif", weight=700, track="0.01em", case="lowercase", layout="stack", mark=tag_in_square, size=76, fs=46,
         note="Schild im Lime-Quadrat, Schrift klein geschrieben und technisch. Gut als App-Icon und Profilbild."),
    dict(id="6A", group="Beleg", title="Kassenbon", font_name="Courier New Bold", libre="Courier Prime Bold (OFL)",
         css="'Courier New', Courier, monospace", weight=700, track="0.04em", case="uppercase", layout="row", mark=receipt_boxed, size=52, fs=36,
         note="Schreibmaschinen-Schrift wie ein Kassenbon. Eigenständig, sofort Beleg."),
    dict(id="6B", group="Beleg", title="Sachlich", font_name="Helvetica Neue Bold", libre="Inter Bold (OFL)",
         css="'Helvetica Neue', Helvetica, Arial, sans-serif", weight=700, track="-0.035em", case="none", layout="row", mark=receipt_naked, size=56, fs=46,
         note="Beleg ohne Rahmen, neutrale Grotesk. Ruhig und seriös, wie ein Finanzprodukt."),
    dict(id="6C", group="Beleg", title="Klassisch", font_name="Baskerville Bold", libre="Libre Baskerville Bold (OFL)",
         css="Baskerville, 'Baskerville Old Face', Georgia, serif", weight=700, track="-0.01em", case="none", layout="row", mark=receipt_lines, size=52, fs=44,
         note="Serifenschrift, wirkt wie ein Steuerbüro. Am vertrauenswürdigsten, am wenigsten „TikTok“."),
]


def wordmark_html(v, dark):
    word = "SellCheck"
    if v["case"] == "lowercase":
        word = word.lower()
    elif v["case"] == "uppercase":
        word = word.upper()
    a, b = word[:4], word[4:]
    c1 = PAPER if dark else INK
    c2 = LIME if dark else DEEP
    style = (f'font-family:{v["css"]};font-weight:{v["weight"]};font-size:{v["fs"]}px;letter-spacing:{v["track"]};'
             f'line-height:1;white-space:nowrap')
    return f'<span style="{style}"><span style="color:{c1}">{a}</span><span style="color:{c2}">{b}</span></span>'


def lockup(v, dark):
    m = svg(v["mark"](dark), v["size"])
    w = wordmark_html(v, dark)
    if v["layout"] == "stack":
        return f'<div class="lock stack">{m}{w}</div>'
    return f'<div class="lock">{m}{w}</div>'


def small_row(v, dark):
    return "".join(f'<span class="s">{svg(v["mark"](dark), s)}</span>' for s in (56, 36, 24, 16))


def card(v):
    return f'''<section class="opt">
  <h2><span class="n">{v["id"]}</span>{v["title"]}</h2>
  <p class="d">{v["note"]}</p>
  <p class="f"><b>Schrift hier:</b> {v["font_name"]}<br><b>Frei lizenzierte Entsprechung:</b> {v["libre"]}</p>
  <div class="tile dark">{lockup(v, True)}</div>
  <div class="tile light">{lockup(v, False)}</div>
  <div class="two"><div class="tile dark">{small_row(v, True)}</div><div class="tile light">{small_row(v, False)}</div></div>
</section>'''


def main():
    groups = {}
    for v in VARIANTS:
        groups.setdefault(v["group"], []).append(card(v))
    body = ""
    for g, cards in groups.items():
        body += f'<h2 class="grp">{g}</h2><div class="grid">{"".join(cards)}</div>'
    html = f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><title>SellCheck Logo-Varianten</title>
<style>
body{{margin:0;background:#e9e7df;font-family:"Avenir Next",system-ui,sans-serif;color:#0e1116}}
.wrap{{max-width:1500px;margin:0 auto;padding:34px 32px 60px}}
h1{{font-size:32px;margin:0 0 6px}} .lead{{color:#565c68;margin:0 0 20px}}
.grp{{font-size:26px;margin:34px 0 14px;padding-bottom:8px;border-bottom:2px solid #0e1116}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}}
.opt{{background:#fff;border-radius:22px;padding:22px}}
.opt h2{{margin:0 0 4px;font-size:21px;display:flex;align-items:center;gap:10px}}
.n{{display:inline-grid;place-items:center;min-width:40px;height:34px;padding:0 6px;border-radius:17px;background:#0e1116;color:#c8f169;font-size:15px}}
.d{{margin:0 0 8px;color:#565c68;font-size:14.5px;line-height:1.4;min-height:40px}}
.f{{margin:0 0 14px;font-size:13px;line-height:1.5;color:#3a424d;background:#f6f4ee;border-radius:10px;padding:8px 10px}}
.tile{{border-radius:14px;padding:18px 20px;display:flex;align-items:center;min-height:92px;margin-bottom:10px}}
.tile.dark{{background:#0e1116}} .tile.light{{background:#f6f4ee;border:1px solid #e2dfd4}}
.lock{{display:flex;align-items:center;gap:14px}} .lock.stack{{flex-direction:column;gap:10px;margin:0 auto}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .two .tile{{margin:0;min-height:0;gap:12px}}
.s{{display:inline-flex;margin-right:10px}}
</style></head><body><div class="wrap">
<h1>SellCheck: Preisschild und Beleg in je drei Varianten</h1>
<p class="lead">Jede Variante hat eine andere Schrift und eine andere Anordnung. Die Schriften sind Systemschriften zum Vergleichen; für das fertige Logo nehmen wir die frei lizenzierte Entsprechung aus dem Kästchen.</p>
{body}
</div></body></html>'''
    open(os.path.join(HERE, "logo-varianten.html"), "w", encoding="utf-8").write(html)
    print("Fertig")


if __name__ == "__main__":
    main()
