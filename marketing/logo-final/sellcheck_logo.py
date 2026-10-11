#!/usr/bin/env python3
"""SellCheck-Logo (Variante 6B: Beleg + Helvetica Neue Bold, Schrift näher am Zeichen).

Zeichnet das Zeichen und die Wortmarke mit PIL. Wird vom Video-Skript und vom Export unten benutzt.
    python3 marketing/logo-final/sellcheck_logo.py     # erzeugt PNG- und SVG-Dateien in diesem Ordner

Hinweis Schrift: Helvetica Neue ist hier nur die Vorlage (Systemschrift des Macs). Für die Veröffentlichung
als Logo bitte die frei lizenzierte Entsprechung Inter verwenden und die Wortmarke aus Inter in Pfade umwandeln.
"""
import os
from PIL import Image, ImageDraw, ImageFont

INK, LIME, PAPER, DEEP = (14, 17, 22), (200, 241, 105), (246, 244, 238), (42, 122, 24)
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_INDEX = 1                                   # Helvetica Neue Bold
TRACK = -0.035                                   # Laufweite in em
GAP = 0.20                                       # Abstand Zeichen zu Schrift in Zeichenhöhen (vorher ca. 0,54)
FS = 0.96                                        # Schriftgröße im Verhältnis zur Zeichenhöhe
CAP = 0.71                                       # Versalhöhe in em (Helvetica Neue)

RECEIPT = [(14, 6), (50, 6), (50, 58), (45, 52.5), (40, 58), (35, 52.5), (30, 58), (25, 52.5), (20, 58), (14, 52.5)]
STROKE = 2.4                                      # Konturstärke der Beleg-Form (rundet Ecken, hält Zacken scharf)
CHECK = [(22, 30), (29.5, 37.5), (43, 22)]
BOX = (12.8, 4.8, 51.2, 59.2)                    # Zeichen inklusive Konturstärke, in 64er-Einheiten
BOX_W, BOX_H = BOX[2] - BOX[0], BOX[3] - BOX[1]  # 39 x 55


def draw_mark(d, x, y, h, on_dark=True, fill=None, check=None):
    """Zeichen mit oberer linker Ecke (x, y) und Höhe h in Pixeln."""
    s = h / BOX_H
    ox, oy = x - BOX[0] * s, y - BOX[1] * s
    fill = fill or (LIME if on_dark else INK)
    check = check or (INK if on_dark else LIME)
    pts = [(ox + a * s, oy + b * s) for a, b in RECEIPT]
    d.polygon(pts, fill=fill)
    d.line(pts + [pts[0]], fill=fill, width=max(1, int(round(STROKE * s))), joint="curve")
    r = STROKE / 2 * s
    for px, py in pts:
        d.ellipse([px - r, py - r, px + r, py + r], fill=fill)
    cp = [(ox + a * s, oy + b * s) for a, b in CHECK]
    w = 6.4 * s
    d.line(cp, fill=check, width=max(1, int(round(w))), joint="curve")
    for cx, cy in (cp[0], cp[2]):
        d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=check)


def mark_width(h):
    return h * BOX_W / BOX_H


def _font(size):
    return ImageFont.truetype(FONT, max(4, int(round(size))), index=FONT_INDEX)


def word_width(size):
    f = _font(size)
    return sum(f.getlength(c) for c in "SellCheck") + TRACK * size * (len("SellCheck") - 1)


def draw_word(d, x, baseline, size, on_dark=True):
    f = _font(size)
    cx = x
    for i, c in enumerate("SellCheck"):
        col = (PAPER if on_dark else INK) if i < 4 else (LIME if on_dark else DEEP)
        d.text((cx, baseline), c, font=f, fill=col, anchor="ls")
        cx += f.getlength(c) + TRACK * size


def lockup_size(h):
    fs = h * FS
    return mark_width(h) + GAP * h + word_width(fs), h


def draw_lockup(d, x, y, h, on_dark=True):
    """Zeichen + Wortmarke; (x, y) ist die obere linke Ecke des Zeichens, h die Zeichenhöhe."""
    draw_mark(d, x, y, h, on_dark)
    fs = h * FS
    tx = x + mark_width(h) + GAP * h
    baseline = y + h / 2 + CAP * fs / 2
    draw_word(d, tx, baseline, fs, on_dark)


def export(here):
    # PNG mit transparentem Grund
    for tag, dark in (("dunkel", True), ("hell", False)):
        h = 400
        w, _ = lockup_size(h)
        pad = int(h * 0.25)
        im = Image.new("RGBA", (int(w) + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        draw_lockup(ImageDraw.Draw(im), pad, pad, h, dark)
        im.save(os.path.join(here, f"sellcheck-logo-{tag}.png"))
    # Zeichen allein
    for tag, dark in (("lime", True), ("tinte", False)):
        h = 800
        pad = 120
        im = Image.new("RGBA", (int(mark_width(h)) + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        draw_mark(ImageDraw.Draw(im), pad, pad, h, dark)
        im.save(os.path.join(here, f"sellcheck-zeichen-{tag}.png"))
    # Profilbild 1024x1024 (TikTok schneidet rund zu): Zeichen tinte auf Lime
    pic = Image.new("RGB", (1024, 1024), LIME)
    h = 560
    draw_mark(ImageDraw.Draw(pic), (1024 - mark_width(h)) / 2, (1024 - h) / 2, h, False)
    pic.save(os.path.join(here, "sellcheck-profilbild-1024.png"))
    # SVG des Zeichens (exakt, Vektor)
    for tag, fill, chk in (("lime", "#C8F169", "#0E1116"), ("tinte", "#0E1116", "#C8F169")):
        pts = " ".join(f"{a},{b}" for a, b in RECEIPT)
        cp = " ".join(f"{a},{b}" for a, b in CHECK)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{BOX[0]} {BOX[1]} {BOX_W} {BOX_H}" role="img" aria-label="SellCheck">'
               f'<polygon points="{pts}" fill="{fill}" stroke="{fill}" stroke-width="{STROKE}" stroke-linejoin="round"/>'
               f'<polyline points="{cp}" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')
        open(os.path.join(here, f"sellcheck-zeichen-{tag}.svg"), "w", encoding="utf-8").write(svg)
    # SVG-Logo mit Text (Schrift NICHT in Pfade umgewandelt, siehe Hinweis oben)
    for tag, dark in (("dunkel", True), ("hell", False)):
        h = 55.0
        fs = h * FS
        mw = BOX_W
        gap = GAP * h
        tw = word_width(fs)
        total = mw + gap + tw
        c1, c2 = ("#F6F4EE", "#C8F169") if dark else ("#0E1116", "#2A7A18")
        fill, chk = ("#C8F169", "#0E1116") if dark else ("#0E1116", "#C8F169")
        pts = " ".join(f"{a - BOX[0]},{b - BOX[1]}" for a, b in RECEIPT)
        cp = " ".join(f"{a - BOX[0]},{b - BOX[1]}" for a, b in CHECK)
        base = h / 2 + CAP * fs / 2
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total:.1f} {h:.0f}" role="img" aria-label="SellCheck">'
               f'<polygon points="{pts}" fill="{fill}" stroke="{fill}" stroke-width="{STROKE}" stroke-linejoin="round"/>'
               f'<polyline points="{cp}" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/>'
               f'<text x="{mw + gap:.1f}" y="{base:.1f}" font-family="Inter, \'Helvetica Neue\', Helvetica, Arial, sans-serif" '
               f'font-weight="700" font-size="{fs:.1f}" letter-spacing="{TRACK * fs:.2f}">'
               f'<tspan fill="{c1}">Sell</tspan><tspan fill="{c2}">Check</tspan></text></svg>')
        open(os.path.join(here, f"sellcheck-logo-{tag}.svg"), "w", encoding="utf-8").write(svg)
    # Vergleichsbild
    sheet = Image.new("RGB", (1500, 560), (233, 231, 223))
    d = ImageDraw.Draw(sheet)
    for i, (dark, bg) in enumerate(((True, INK), (False, PAPER))):
        x0 = 30 + i * 735
        d.rounded_rectangle([x0, 30, x0 + 705, 330], 24, fill=bg)
        h = 120
        w, _ = lockup_size(h)
        draw_lockup(d, x0 + (705 - w) / 2, 30 + (300 - h) / 2, h, dark)
        for k, hh in enumerate((64, 40, 28, 18)):
            draw_mark(d, x0 + 40 + k * 110, 360 + (64 - hh) / 2, hh, dark)
    d.ellipse([1180, 330, 1420, 570], fill=LIME)
    draw_mark(d, 1180 + (240 - 140 * BOX_W / BOX_H) / 2, 330 + 50, 140, False)
    sheet.save(os.path.join(here, "vorschau.png"))


if __name__ == "__main__":
    export(os.path.dirname(os.path.abspath(__file__)))
    print("Logo-Dateien geschrieben")
