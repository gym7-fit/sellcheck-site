#!/usr/bin/env python3
"""Dritte Runde: drei weitere Varianten der Richtung 6B (Beleg, sachlich, neutrale Grotesk).

    python3 marketing/logo-optionen/build_6b.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INK, LIME, PAPER = "#0E1116", "#C8F169", "#F6F4EE"
DEEP = "#2A7A18"
MUTED_D, MUTED_L = "#9AA1AD", "#565C68"
FOLD_D, FOLD_L = "#8FB63A", "#8FB63A"


def svg(inner, size=56):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" aria-hidden="true">{inner}</svg>'


def recv_wide(dark):          # Ausgangspunkt 6B: breit, fünf Zacken
    fill, chk = (LIME, INK) if dark else (INK, LIME)
    return (f'<path d="M14 6H50V58L45 53.5 40 58 35 53.5 30 58 25 53.5 20 58 14 53Z" fill="{fill}" stroke="{fill}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M22 30l7.5 7.5L43 22" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/>')


def recv_slim(dark):          # schmal, vier Zacken, größerer Haken
    fill, chk = (LIME, INK) if dark else (INK, LIME)
    return (f'<path d="M18 5H46V59L42 55 38 59 34 55 30 59 26 55 22 59 18 55Z" fill="{fill}" stroke="{fill}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M23.5 29l6.5 7 11-14" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/>')


def recv_fold(dark):          # Blatt mit abgeknickter Ecke
    fill, chk = (LIME, INK) if dark else (INK, LIME)
    fold = FOLD_D if dark else "#4A525E"
    return (f'<path d="M14 6H40L50 16V58L45 53.5 40 58 35 53.5 30 58 25 53.5 20 58 14 53Z" fill="{fill}" stroke="{fill}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M40 6V16H50Z" fill="{fold}" stroke="{fold}" stroke-width="2" stroke-linejoin="round"/>'
            f'<path d="M22 33l7 7 13-14" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/>')


HF = "'Helvetica Neue', Helvetica, Arial, sans-serif"

VARIANTS = [
    dict(id="6B-1", title="Gewichtskontrast", mark=recv_wide, layout="row", size=60,
         note="Gleiches Zeichen wie 6B, größer. „Sell“ dünn und grau, „Check“ fett: die Betonung liegt auf dem Check. Lime steckt nur im Zeichen.",
         word=lambda d: (f'<span style="font:400 46px/1 {HF};letter-spacing:-0.03em;color:{MUTED_D if d else MUTED_L}">Sell</span>'
                         f'<span style="font:700 46px/1 {HF};letter-spacing:-0.03em;color:{PAPER if d else INK}">Check</span>')),
    dict(id="6B-2", title="Klein und schmal", mark=recv_slim, layout="row", size=60,
         note="Schmaleres Blatt mit vier Zacken und größerem Haken, alles klein geschrieben. Moderner, stärker „App“.",
         word=lambda d: (f'<span style="font:700 48px/1 {HF};letter-spacing:-0.045em;color:{PAPER if d else INK}">sell</span>'
                         f'<span style="font:700 48px/1 {HF};letter-spacing:-0.045em;color:{LIME if d else DEEP}">check</span>')),
    dict(id="6B-3", title="Gestapelt mit Knickecke", mark=recv_fold, layout="stack", size=76,
         note="Blatt mit abgeknickter Ecke über einer weit gesetzten Wortmarke in Großbuchstaben. Wirkt am ehesten wie ein Finanz- oder Steuerprodukt.",
         word=lambda d: (f'<span style="font:700 26px/1 {HF};letter-spacing:0.22em;color:{PAPER if d else INK}">SELL</span>'
                         f'<span style="font:700 26px/1 {HF};letter-spacing:0.22em;color:{LIME if d else DEEP}">CHECK</span>')),
]


def lockup(v, dark):
    m = svg(v["mark"](dark), v["size"])
    w = v["word"](dark)
    if v["layout"] == "stack":
        return f'<div class="lock stack">{m}<span class="w">{w}</span></div>'
    return f'<div class="lock">{m}<span class="w">{w}</span></div>'


def small_row(v, dark):
    return "".join(f'<span class="s">{svg(v["mark"](dark), s)}</span>' for s in (56, 36, 24, 16))


def profile(v):
    # TikTok-Profilbild ist rund: Zeichen auf Lime und auf Tinte
    on_lime = f'<span class="pf" style="background:{LIME}">{svg(v["mark"](False), 54)}</span>'
    on_ink = f'<span class="pf" style="background:{INK}">{svg(v["mark"](True), 54)}</span>'
    return on_lime + on_ink


def card(v):
    return f'''<section class="opt">
  <h2><span class="n">{v["id"]}</span>{v["title"]}</h2>
  <p class="d">{v["note"]}</p>
  <div class="tile dark">{lockup(v, True)}</div>
  <div class="tile light">{lockup(v, False)}</div>
  <div class="two"><div class="tile dark">{small_row(v, True)}</div><div class="tile light">{small_row(v, False)}</div></div>
  <div class="prof"><span class="lab">Profilbild (rund):</span>{profile(v)}</div>
</section>'''


def main():
    html = f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><title>SellCheck 6B-Varianten</title>
<style>
body{{margin:0;background:#e9e7df;font-family:"Avenir Next",system-ui,sans-serif;color:#0e1116}}
.wrap{{max-width:1500px;margin:0 auto;padding:34px 32px 50px}}
h1{{font-size:30px;margin:0 0 6px}} .lead{{color:#565c68;margin:0 0 22px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}}
.opt{{background:#fff;border-radius:22px;padding:22px}}
.opt h2{{margin:0 0 6px;font-size:21px;display:flex;align-items:center;gap:10px}}
.n{{display:inline-grid;place-items:center;min-width:54px;height:34px;padding:0 8px;border-radius:17px;background:#0e1116;color:#c8f169;font-size:15px}}
.d{{margin:0 0 14px;color:#565c68;font-size:14.5px;line-height:1.4;min-height:62px}}
.tile{{border-radius:14px;padding:18px 20px;display:flex;align-items:center;min-height:104px;margin-bottom:10px}}
.tile.dark{{background:#0e1116}} .tile.light{{background:#f6f4ee;border:1px solid #e2dfd4}}
.lock{{display:flex;align-items:center;gap:14px}} .lock.stack{{flex-direction:column;gap:12px;margin:0 auto}}
.w{{display:inline-flex;align-items:baseline}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .two .tile{{margin:0;min-height:0}}
.s{{display:inline-flex;margin-right:10px}}
.prof{{display:flex;align-items:center;gap:12px;margin-top:12px;font-size:13px;color:#565c68}}
.pf{{display:inline-grid;place-items:center;width:88px;height:88px;border-radius:50%;border:1px solid #d9d6cb}}
</style></head><body><div class="wrap">
<h1>SellCheck: drei weitere Varianten von 6B</h1>
<p class="lead">Gleiche Richtung (Beleg, neutrale Grotesk), anders gewichtet, geformt und angeordnet. Schrift in allen drei: Helvetica Neue Bold/Regular als Vorlage, frei lizenzierte Entsprechung Inter.</p>
<div class="grid">{"".join(card(v) for v in VARIANTS)}</div>
</div></body></html>'''
    open(os.path.join(HERE, "logo-6b-varianten.html"), "w", encoding="utf-8").write(html)
    print("Fertig")


if __name__ == "__main__":
    main()
