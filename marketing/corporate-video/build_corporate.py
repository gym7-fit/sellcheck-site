#!/usr/bin/env python3
"""SellCheck Corporate-Video, 16:9 (1920x1080, 30 fps), ca. 49 s.

Zweck: Erklärfilm für Website und Social. Läuft auch ohne Ton (die Botschaft steht im Bild).
Schnitt auf einem 120-bpm-Raster: Schrift schlägt im Beat ein, Wisch-Übergänge auf den Takt, treibender Beat.

    python3 marketing/corporate-video/build_corporate.py              # Bild und Musik (ohne Sprecher)
    python3 marketing/corporate-video/build_corporate.py voice DIR    # mit Sprachclips aus DIR (1.mp3 ... 6.mp3)
    python3 marketing/corporate-video/build_corporate.py poster 3,12  # Einzelbilder zum Prüfen
    python3 marketing/corporate-video/build_corporate.py audio        # nur Ton neu, Bilder bleiben

Ausgabe: marketing/corporate-video/out/
Es werden keine Plattform-Logos und keine fremden Markenzeichen verwendet. Alle Zahlen im Video sind
Beispieldaten und im Bild so gekennzeichnet.
"""
import math
import os
import random
import struct
import subprocess
import sys
import wave
from functools import lru_cache
from multiprocessing import Pool

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "logo-final"))
import sellcheck_logo as LOGO  # noqa: E402

W, H, FPS, S = 1920, 1080, 30, 2
FRAMES = os.environ.get("CORP_FRAMES", "/tmp/sellcheck_corporate_frames")
OUT = os.path.join(HERE, "out")
ASSETS = os.path.join(HERE, "assets")

INK = (14, 17, 22)
INK2 = (27, 32, 40)
LIME = (200, 241, 105)
PAPER = (246, 244, 238)
WHITE = (255, 255, 255)
MUTED = (154, 161, 173)
DARKMUTED = (96, 103, 115)
LINE = (226, 223, 212)
GREEN = (52, 196, 116)
AMBER = (229, 169, 58)
RED = (214, 72, 58)
DEEPGREEN = (23, 112, 63)

BPM = 120
BEAT = 60.0 / BPM  # 0,5 s
# Szenen: (Name, Start, Länge). Alle Starts liegen auf dem Beat-Raster.
SCENES = [("hook", 0.0, 4.0), ("problem", 4.0, 8.0), ("loesung", 12.0, 10.0), ("produkt", 22.0, 16.0),
          ("vertrauen", 38.0, 6.0), ("abbinder", 44.0, 5.0)]
DUR = 49.0
NF = int(DUR * FPS)
WIPE = 0.36  # Dauer des Wisch-Übergangs, Mitte = Schnitt

FONT = "/System/Library/Fonts/Avenir Next.ttc"
WEIGHT = {"bold": 0, "demi": 2, "medium": 5, "regular": 7, "heavy": 8}


@lru_cache(maxsize=None)
def font(size, weight):
    return ImageFont.truetype(FONT, int(round(size)), index=WEIGHT[weight])


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else (1.0 if t >= t0 else 0.0)


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_io(p):
    return p * p * (3 - 2 * p)


def ease_back(p, k=1.7):
    p = clamp(p)
    return 1 + (k + 1) * (p - 1) ** 3 + k * (p - 1) ** 2


class Canvas:
    def __init__(self, bg):
        # RGB-Fläche: Zeichnen mit Alpha mischt dann korrekt (auf RGBA würde Pillow den Alpha-Wert überschreiben)
        self.im = Image.new("RGB", (W * S, H * S), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def over(self, layer, pos=(0, 0)):
        """RGBA-Ebene mit Transparenz über die Fläche legen."""
        self.im.paste(layer.convert("RGB"), pos, layer.getchannel("A"))

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, width=0):
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], r * S, fill=fill, outline=outline, width=int(width * S))

    def rect(self, x0, y0, x1, y1, fill):
        self.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill)

    def circle(self, cx, cy, r, fill=None, outline=None, width=0):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill, outline=outline, width=int(width * S))

    def line(self, pts, fill, width):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S), joint="curve")

    def text(self, x, y, s, size, weight, fill, anchor="la"):
        """Text mit Transparenz: Pillow ignoriert den Alpha-Wert bei Text, deshalb über eine Maske mischen."""
        f = font(size * S, weight)
        al = fill[3] if len(fill) > 3 else 255
        if al >= 255:
            self.d.text((x * S, y * S), s, font=f, fill=tuple(fill[:3]), anchor=anchor)
            return
        if al <= 0:
            return
        l, t, r, b = self.d.textbbox((x * S, y * S), s, font=f, anchor=anchor)
        pad = 6
        box = (int(l) - pad, int(t) - pad, int(r) + pad, int(b) + pad)
        mask = Image.new("L", (box[2] - box[0], box[3] - box[1]), 0)
        ImageDraw.Draw(mask).text((x * S - box[0], y * S - box[1]), s, font=f, fill=255, anchor=anchor)
        mask = mask.point(lambda v: v * al // 255)
        self.im.paste(tuple(fill[:3]), box, mask)

    def tw(self, s, size, weight):
        return font(size * S, weight).getlength(s) / S

    def wrap(self, s, size, weight, maxw):
        lines, cur = [], ""
        for word in s.split():
            test = (cur + " " + word).strip()
            if self.tw(test, size, weight) <= maxw or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def logo(self, cx, cy, h, alpha=1.0, on_dark=True):
        w, _ = LOGO.lockup_size(h * S)
        tmp = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        LOGO.draw_lockup(ImageDraw.Draw(tmp), cx * S - w / 2, (cy - h / 2) * S, h * S, on_dark=on_dark)
        if alpha < 1:
            tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * alpha)))
        self.over(tmp)
        return w / S


def slam(c, x, y, s, size, weight, fill, t, t0, anchor="lm", pop=0.5):
    """Schrift schlägt groß ein und setzt sich: Start größer, schnell auf Sollgröße."""
    p = prog(t, t0, 0.26)
    if p <= 0:
        return
    k = 1 + pop * (1 - ease_out(p))
    base = fill[3] if len(fill) > 3 else 255
    a = int(base * clamp(p * 5))
    c.text(x, y, s, size * k, weight, tuple(fill[:3]) + (a,), anchor)


def pill(c, cx, cy, w, h, fill=None, outline=None, width=0):
    c.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, h / 2, fill=fill, outline=outline, width=width)


def check(c, cx, cy, r, bg=LIME, fg=INK, a=255):
    c.circle(cx, cy, r, fill=bg + (a,))
    c.line([(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.46, cy - r * 0.32)], fg + (a,), max(2, r * 0.22))


def money(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"


def flash(c, t, t0, color=WHITE, peak=70, dur=0.22):
    p = prog(t, t0, dur)
    if 0 < p < 1:
        c.d.rectangle([0, 0, W * S, H * S], fill=color + (int(peak * (1 - p)),))


def glow(c, box, alpha):
    g = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([box[0] * S, box[1] * S, box[2] * S, box[3] * S], fill=LIME + (int(alpha),))
    g = g.filter(ImageFilter.GaussianBlur(170 * S))
    c.over(g)


def bug(c, on_dark):
    c.logo(60 + 105, 74, 50, 0.9, on_dark=on_dark)


def color_dark(col):
    return {GREEN: DEEPGREEN, AMBER: (150, 96, 0), RED: (176, 40, 30)}.get(col, DARKMUTED)


# ------------------------------------------------------------------ Szenen
def scene_hook(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    glow(c, (1100, 100, 2000, 900), 46)
    bug(c, True)
    # Drei Schläge im Beat: 0,0 / 1,0 / 2,0 s
    slam(c, 140, 330, "Vier Plattformen.", 150, "heavy", PAPER, t, 0.0)
    slam(c, 140, 505, "Vier Zähler.", 150, "heavy", PAPER, t, 1.0)
    slam(c, 140, 680, "Kein Überblick.", 150, "heavy", LIME, t, 2.0)
    p = ease_out(prog(t, 2.25, 0.5))
    if p > 0:
        wline = c.tw("Kein Überblick.", 150, "heavy")
        c.rrect(140, 770, 140 + wline * p, 784, 7, fill=LIME + (255,))
    names = ["Vinted", "Kleinanzeigen", "eBay", "Etsy"]
    x = 140
    for k, nm in enumerate(names):
        p = ease_back(prog(t, 0.5 + k * 0.5, 0.3))
        w = c.tw(nm, 40, "demi") + 70
        if p > 0:
            sc = 0.7 + 0.3 * min(p, 1.1)
            pill(c, x + w / 2, 930, w * sc, 76 * sc, fill=INK2 + (255,), outline=(70, 78, 92, 255), width=2)
            c.text(x + w / 2, 931, nm, 40, "demi", PAPER + (int(255 * clamp(p * 3)),), "mm")
        x += w + 22


def platform_card(c, x, y, w, name, n, color, status, t, t0):
    p = ease_back(prog(t, t0, 0.35))
    if p <= 0:
        return
    a = int(255 * clamp(p * 4))
    cy = y + (1 - clamp(p)) * 40
    sc = 0.9 + 0.1 * min(p, 1.0)
    cw, ch = w * sc, 300 * sc
    x0 = x + (w - cw) / 2
    c.rrect(x0, cy, x0 + cw, cy + ch, 30, fill=WHITE + (a,), outline=LINE + (a,), width=2)
    c.text(x + 34, cy + 54, name, 36, "heavy", INK + (a,), "lm")
    v = int(round(n * ease_out(prog(t, t0 + 0.1, 0.9))))
    c.text(x + 34, cy + 142, str(v), 82, "heavy", INK + (a,), "lm")
    c.text(x + 34 + c.tw(str(v), 82, "heavy") + 14, cy + 156, "von 30", 34, "medium", DARKMUTED + (a,), "lm")
    bx0, bx1, by = x + 34, x + w - 34, cy + 214
    c.rrect(bx0, by, bx1, by + 18, 9, fill=(236, 233, 223, a))
    fill = ease_out(prog(t, t0 + 0.1, 0.9)) * min(1.0, n / 30)
    if fill > 0.01:
        c.rrect(bx0, by, bx0 + (bx1 - bx0) * fill, by + 18, 9, fill=color + (a,))
    c.text(x + 34, cy + 262, status, 28, "medium", color_dark(color) + (a,), "lm")
    if color == RED and t > t0 + 1.0:
        pulse = 0.5 + 0.5 * math.sin((t - t0) * 9)
        c.rrect(x, cy, x + w, cy + 300, 30, outline=RED + (int(120 + 100 * pulse),), width=5)


def scene_problem(c, t):
    c.rect(0, 0, W, H, PAPER + (255,))
    bug(c, False)
    slam(c, 140, 250, "Jede Plattform zählt getrennt.", 92, "heavy", INK, t, 0.0)
    cards = [("Vinted", 21, AMBER, "Nähert sich der Grenze"), ("Kleinanzeigen", 8, GREEN, "Weit entfernt"),
             ("eBay", 2, GREEN, "Weit entfernt"), ("Etsy", 31, RED, "Grenze erreicht")]
    cw, gap = 395, 28
    for k, (nm, n, col, st) in enumerate(cards):
        platform_card(c, 140 + k * (cw + gap), 380, cw, nm, n, col, st, t, 1.0 + k * 0.5)
    c.text(1780, 712, "Beispieldaten", 24, "medium", DARKMUTED, "ra")
    p = ease_back(prog(t, 4.0, 0.4), 1.2)
    if p > 0:
        a = int(255 * clamp(p * 4))
        off = (1 - clamp(p)) * 120
        c.rrect(140, 760 + off, 1780, 1010 + off, 34, fill=INK + (a,))
        slam(c, 200, 850 + off, "30 Verkäufe oder 2.000 € im Jahr.", 72, "heavy", PAPER, t, 4.1)
        slam(c, 200, 935 + off, "Je Plattform. Dann meldet sie an die Steuerbehörden.", 38, "medium", LIME, t, 4.5, pop=0.2)
        p2 = ease_out(prog(t, 5.5, 0.4))
        c.text(200, 985 + off, "Eine Meldung ist keine Steuerforderung.", 28, "medium", MUTED + (int(255 * p2),), "lm")


def overview_card(c, x, y, t, t0):
    p = ease_back(prog(t, t0, 0.5), 1.3)
    if p <= 0:
        return
    a = int(255 * clamp(p * 4))
    yy = y + (1 - clamp(p)) * 80
    w, h = 720, 800
    sh = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x * S, (yy + 18) * S, (x + w) * S, (yy + h + 18) * S], 40 * S, fill=(0, 0, 0, int(90 * clamp(p))))
    c.over(sh)
    c.rrect(x, yy, x + w, yy + h, 40, fill=PAPER + (a,))
    c.text(x + 44, yy + 62, "Gewinn 2026 · alle Plattformen", 28, "demi", DARKMUTED + (a,), "lm")
    pill(c, x + w - 44 - 110, yy + 62, 220, 42, fill=(255, 243, 199, a))
    c.text(x + w - 44 - 110, yy + 63, "Beispieldaten", 22, "demi", (122, 82, 0, a), "mm")
    val = 842.5 * ease_out(prog(t, t0 + 0.2, 1.0))
    pulse = 1 + 0.08 * max(0.0, 1 - abs(t - (t0 + 1.4)) / 0.25)
    c.text(x + 44, yy + 150, money(val), 84 * pulse, "heavy", INK + (a,), "lm")
    c.text(x + 44 + c.tw(money(842.5), 84, "heavy") + 20, yy + 166, "nach Kosten", 28, "demi", DEEPGREEN + (a,), "lm")
    c.rrect(x + 36, yy + 214, x + w - 36, yy + 470, 26, fill=WHITE + (a,), outline=LINE + (a,), width=2)
    rows = [("Vinted", 21, AMBER), ("Kleinanzeigen", 8, GREEN), ("eBay", 2, GREEN)]
    for k, (nm, n, col) in enumerate(rows):
        ry = yy + 252 + k * 74
        c.text(x + 70, ry, nm, 28, "demi", INK + (a,), "lm")
        c.text(x + w - 70, ry, f"{n} von 30", 28, "demi", INK + (a,), "rm")
        c.rrect(x + 70, ry + 24, x + w - 70, ry + 38, 7, fill=(236, 233, 223, a))
        f = ease_out(prog(t, t0 + 0.3 + k * 0.12, 0.7)) * n / 30
        if f > 0.01:
            c.rrect(x + 70, ry + 24, x + 70 + (w - 140) * f, ry + 38, 7, fill=col + (a,))
    items = [("Nike Air Max 90", "+ 33,50 €", DEEPGREEN), ("Retro-Konsole", "+ 38,10 €", DEEPGREEN), ("Zara Mantel M", "− 2,00 €", RED)]
    for k, (nm, v, col) in enumerate(items):
        ry = yy + 540 + k * 84
        pa = int(a * ease_out(prog(t, t0 + 0.8 + k * 0.25, 0.3)))
        c.line([(x + 44, ry - 42), (x + w - 44, ry - 42)], LINE + (pa,), 2)
        c.text(x + 44, ry, nm, 30, "demi", INK + (pa,), "lm")
        c.text(x + w - 44, ry, v, 30, "heavy", col + (pa,), "rm")


def scene_loesung(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    glow(c, (300, 100, 1500, 1000), 30)
    p = ease_back(prog(t, 0.0, 0.5), 2.0)
    shift = ease_io(prog(t, 3.0, 0.7))
    cx = 960 + (600 - 960) * shift
    c.logo(cx, 330, 190 * (1 - 0.2 * shift) * (0.55 + 0.45 * clamp(p, 0, 1.15)), clamp(prog(t, 0.0, 0.15) * 4))
    slam(c, cx, 515, "Alles an", 104, "heavy", PAPER, t, 1.0, anchor="mm")
    slam(c, cx, 630, "einem Ort.", 104, "heavy", LIME, t, 1.5, anchor="mm")
    overview_card(c, 1030, 140, t, 3.0)
    for k, b in enumerate(["Gewinn pro Artikel", "Meldegrenze je Plattform", "Bestand im Blick"]):
        pp = ease_back(prog(t, 4.0 + k * 0.5, 0.3))
        if pp <= 0:
            continue
        a = int(255 * clamp(pp * 4))
        y = 790 + k * 76
        check(c, 240, y, 22 * min(pp, 1.0), a=a)
        c.text(284 + (1 - clamp(pp)) * 40, y, b, 40, "demi", PAPER + (a,), "lm")
    flash(c, t, 0.0, LIME, 90, 0.3)


def window(c, x, y, w, img, t, zoom_from, zoom_to, focus, alpha=1.0):
    if alpha <= 0:
        return None
    iw, ih = img.size
    ch = w * ih / iw
    bar = 44
    a = int(255 * alpha)
    sh = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x * S, (y + 22) * S, (x + w) * S, (y + bar + ch + 22) * S], 24 * S, fill=(14, 17, 22, int(70 * alpha)))
    sh = sh.filter(ImageFilter.GaussianBlur(26 * S))
    c.over(sh)
    c.rrect(x, y, x + w, y + bar + ch, 22, fill=(255, 255, 255, a))
    c.rrect(x, y, x + w, y + bar + 22, 22, fill=(236, 234, 228, a))
    c.rect(x, y + bar - 2, x + w, y + bar + 20, (255, 255, 255, a))
    for k, col in enumerate(((255, 96, 87), (254, 188, 46), (40, 200, 64))):
        c.circle(x + 28 + k * 26, y + bar / 2, 8, fill=col + (a,))
    z = zoom_from + (zoom_to - zoom_from) * clamp(t)
    cw_src, ch_src = iw / z, ih / z
    fx = clamp(focus[0]) * (iw - cw_src)
    fy = clamp(focus[1]) * (ih - ch_src)
    crop = img.crop((int(fx), int(fy), int(fx + cw_src), int(fy + ch_src))).resize((int(w * S), int(ch * S)), Image.LANCZOS)
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, crop.width, crop.height], 22 * S, fill=255)
    ImageDraw.Draw(mask).rectangle([0, 0, crop.width, 24 * S], fill=255)
    tile = crop.convert("RGBA")
    tile.putalpha(mask.point(lambda v: int(v * alpha)))
    c.over(tile, (int(x * S), int((y + bar) * S)))

    def to_stage(px, py):
        return x + (px - fx) / cw_src * w, y + bar + (py - fy) / ch_src * ch
    return to_stage


_IMGS = {}


def shot(name):
    if name not in _IMGS:
        _IMGS[name] = Image.open(os.path.join(ASSETS, name)).convert("RGB")
    return _IMGS[name]


# Titel, Beschreibung, Aufnahme, Fokus, Zoom, Länge, Hervorhebung (Rechteck in Aufnahme-Pixeln, Text, Farbe)
BEATS = [
    ("Import in Sekunden.", "CSV aus Plattform, PayPal oder Online-Banking. Gelesen wird nur im Browser.", "ui_import.png", (0.5, 0.5), 1.5, 6.0,
     ((420, 560, 2460, 1520), "85 von 85 Zeilen erkannt", GREEN)),
    ("Die Meldegrenze als Ampel.", "Je Plattform sofort sichtbar: Grün, Gelb oder Rot, dazu der Gewinn.", "ui_limits.png", (0.5, 0.82), 1.5, 5.0,
     ((620, 1125, 2215, 1395), "Gelb: nähert sich der Grenze", AMBER)),
    ("Der Report zum Abtippen.", "Ausfüllhilfe für die Anlage EÜR, dazu CSV für den Steuerberater.", "ui_report.png", (0.5, 0.88), 1.45, 5.0,
     ((420, 1560, 2460, 1740), "Gewinn: 1.924,78 € (Beispiel)", GREEN)),
]


def scene_produkt(c, t):
    c.rect(0, 0, W, H, PAPER + (255,))
    bug(c, False)
    starts, acc = [], 0.0
    for b in BEATS:
        starts.append(acc)
        acc += b[5]
    k = max(j for j, s0 in enumerate(starts) if t >= s0)
    lt = t - starts[k]
    to_stage = None
    for j in range(len(BEATS)):
        if j > k:
            continue
        jt = t - starts[j]
        slide = (1 - ease_out(prog(jt, 0.0, 0.35))) * 220 if j == k else 0
        a = clamp(prog(jt, 0.0, 0.2)) if j == k else 1.0
        b = BEATS[j]
        ts = window(c, 800 + slide, 190, 1020, shot(b[2]), clamp(jt / b[5]), b[4], b[4] + 0.1, b[3], alpha=a)
        if j == k:
            to_stage = ts
    title, desc = BEATS[k][0], BEATS[k][1]
    lines = c.wrap(title, 68, "heavy", 620)
    y = 400
    for i, ln in enumerate(lines):
        slam(c, 140, y, ln, 68, "heavy", INK, lt, 0.05 + i * 0.12, pop=0.25)
        y += 80
    dp = ease_out(prog(lt, 0.45, 0.4))
    for ln in c.wrap(desc, 32, "medium", 600):
        c.text(140, y + 28, ln, 32, "medium", DARKMUTED + (int(255 * dp),), "lm")
        y += 48
    rect, label, colr = BEATS[k][6]
    hp = ease_back(prog(lt, 1.5, 0.4), 1.2)
    if to_stage and hp > 0:
        x0, y0 = to_stage(rect[0], rect[1])
        x1, y1 = to_stage(rect[2], rect[3])
        x0, x1 = max(x0, 806), min(x1, 1814)
        y0, y1 = max(y0, 244), min(y1, 806)
        if x1 > x0 and y1 > y0:
            a = int(255 * clamp(hp * 3))
            c.rrect(x0 - 6, y0 - 6, x1 + 6, y1 + 6, 18, outline=colr + (a,), width=6)
            lw = c.tw(label, 32, "heavy") + 60
            lx = min(x1 + 6, 1814) - lw
            ly = y1 + 44 if y1 + 70 < 1040 else y0 - 44
            pill(c, lx + lw / 2, ly, lw * (0.8 + 0.2 * min(hp, 1.0)), 64, fill=colr + (a,))
            c.text(lx + lw / 2, ly + 1, label, 32, "heavy", INK + (a,), "mm")
    for j in range(3):
        cur = j == k
        c.rrect(140 + j * 54, 880, 140 + j * 54 + (40 if cur else 14), 894, 7, fill=(INK if cur else (200, 196, 184)) + (255,))
    c.text(1780, 1030, "Beispieldaten", 24, "medium", DARKMUTED, "ra")


def lock_icon(c, cx, cy, s, a=255, col=LIME):
    w = s * 0.07
    c.rrect(cx - s * 0.5, cy, cx + s * 0.5, cy + s * 0.62, s * 0.12, outline=col + (a,), width=w)
    r = s * 0.3
    c.d.arc([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], 180, 360, fill=col + (a,), width=int(w * S))
    c.circle(cx, cy + s * 0.3, s * 0.065, fill=col + (a,))


def scene_vertrauen(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    glow(c, (1100, 100, 2000, 900), 36)
    bug(c, True)
    lines = ["Kein Zugriff auf Konten.", "Daten bleiben im Browser.", "Orientierung statt Beratung."]
    for k, ln in enumerate(lines):
        t0 = k * 1.5
        pp = ease_back(prog(t, t0, 0.3))
        if pp > 0:
            check(c, 190, 380 + k * 160, 34 * min(pp, 1.0), a=int(255 * clamp(pp * 4)))
        slam(c, 260, 380 + k * 160, ln, 78, "heavy", PAPER, t, t0 + 0.05, pop=0.35)
    pulse = 1 + 0.05 * max(0.0, 1 - ((t % 1.5) / 0.25))
    p = ease_back(prog(t, 0.0, 0.5))
    lock_icon(c, 1640, 450, 300 * pulse * clamp(p, 0.01, 1.0), int(255 * clamp(p * 3)))
    c.text(140, 1010, "Unabhängig von den genannten Plattformen.", 28, "medium", MUTED + (int(255 * ease_out(prog(t, 3.5, 0.4))),), "lm")
    flash(c, t, 3.0, LIME, 40, 0.2)


def scene_abbinder(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    glow(c, (560, 150, 1360, 950), 56)
    p = ease_back(prog(t, 0.0, 0.5), 2.0)
    c.logo(960, 240, 190 * (0.55 + 0.45 * clamp(p, 0, 1.15)), clamp(prog(t, 0.0, 0.15) * 4))
    slam(c, 960, 470, "Check, was", 120, "heavy", PAPER, t, 1.0, anchor="mm")
    slam(c, 960, 605, "wirklich bleibt.", 120, "heavy", LIME, t, 1.5, anchor="mm")
    pp = ease_back(prog(t, 2.5, 0.4))
    if pp > 0:
        w = c.tw("Kostenlos, ohne Anmeldung", 44, "heavy") + 120
        pill(c, 960, 790, w * (0.8 + 0.2 * min(pp, 1.0)), 104, fill=LIME + (int(255 * clamp(pp * 4)),))
        c.text(960, 792, "Kostenlos, ohne Anmeldung", 44, "heavy", INK + (int(255 * clamp(pp * 4)),), "mm")
    fa = int(255 * ease_out(prog(t, 3.0, 0.5)))
    c.text(960, 955, "SellCheck ist ein unabhängiges Projekt und mit keiner der genannten Plattformen verbunden.", 24, "medium", MUTED + (fa,), "mm")
    c.text(960, 993, "Keine Steuer- oder Rechtsberatung. Alle Angaben ohne Gewähr.", 24, "medium", MUTED + (fa,), "mm")
    flash(c, t, 0.0, WHITE, 110, 0.3)


FUNCS = {"hook": scene_hook, "problem": scene_problem, "loesung": scene_loesung, "produkt": scene_produkt,
         "vertrauen": scene_vertrauen, "abbinder": scene_abbinder}
BG = {"hook": INK, "problem": PAPER, "loesung": INK, "produkt": PAPER, "vertrauen": INK, "abbinder": INK}
PUSH = {"hook": 0.06, "problem": 0.0, "loesung": 0.05, "produkt": 0.0, "vertrauen": 0.06, "abbinder": 0.04}


def render_scene(idx, t):
    name, start, length = SCENES[idx]
    c = Canvas(BG[name])
    lt = max(0.0, t - start)
    FUNCS[name](c, lt)
    im = c.im
    z = 1 + PUSH[name] * clamp(lt / length)  # langsames Heranfahren
    if z > 1.0005:
        cw, ch = W * S / z, H * S / z
        x0, y0 = (W * S - cw) / 2, (H * S - ch) / 2
        im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W * S, H * S), Image.BILINEAR)
    return im


def render_frame(args):
    i, path_dir = args
    t = i / FPS
    idx = 0
    for k, (_, st, ln) in enumerate(SCENES):
        if t >= st:
            idx = k
    cut = None
    for k in range(1, len(SCENES)):
        st = SCENES[k][1]
        if abs(t - st) < WIPE / 2:
            cut = (k, st)
    if cut:
        k, st = cut
        p = (t - st + WIPE / 2) / WIPE
        im = render_scene(k - 1, t) if p < 0.5 else render_scene(k, t)
        x0 = -W + 2 * W * p  # Lime-Band läuft von links nach rechts, bei p = 0,5 deckt es alles
        ImageDraw.Draw(im, "RGBA").rectangle([x0 * S, 0, (x0 + W) * S, H * S], fill=LIME + (255,))
    else:
        im = render_scene(idx, t)
    im = im.convert("RGB").reduce(S)
    im.save(os.path.join(path_dir, f"f_{i:05d}.jpg"), quality=94, subsampling=0)
    return i


# ------------------------------------------------------------------ Ton
SR = 44100


def build_audio(path, voice_dir=None):
    n = int(SR * DUR)
    buf = [0.0] * n
    rnd = random.Random(21)

    def add(t0, samples, gain=1.0):
        s0 = int(t0 * SR)
        for k, v in enumerate(samples):
            j = s0 + k
            if j >= n:
                break
            if j >= 0:
                buf[j] += v * gain

    def sine(f, dur, decay=5.0, attack=0.003, f_end=None, harm=()):
        m = int(dur * SR)
        out, ph = [], 0.0
        for i in range(m):
            x = i / m
            ff = f if f_end is None else f + (f_end - f) * x
            ph += 2 * math.pi * ff / SR
            env = math.exp(-decay * x) * min(1.0, i / (attack * SR + 1))
            v = math.sin(ph)
            for hm, g in harm:
                v += g * math.sin(ph * hm)
            out.append(v * env)
        return out

    def noise(dur, decay=8.0, hp=0.0, lp=1.0):
        m = int(dur * SR)
        out, prev_x, prev_y, lpv = [], 0.0, 0.0, 0.0
        for i in range(m):
            x = rnd.uniform(-1, 1)
            y = x - prev_x + hp * prev_y if hp else x
            prev_x, prev_y = x, y
            lpv += lp * (y - lpv)
            out.append(lpv * math.exp(-decay * i / m))
        return out

    def kick(t0, g=0.9):
        m = int(0.26 * SR)
        out, ph = [], 0.0
        for i in range(m):
            tt = i / SR
            f = 46 + 110 * math.exp(-tt / 0.028)
            ph += 2 * math.pi * f / SR
            out.append(math.sin(ph) * math.exp(-tt / 0.085) * min(1.0, i / 60))
        add(t0, out, g)
        add(t0, noise(0.008, 3.0, 0.5), 0.12)

    def clap(t0, g=0.5):
        for d in (0.0, 0.011, 0.024):
            add(t0 + d, noise(0.11, 9.0, 0.6, 0.55), g * 0.6)

    def hat(t0, g=0.14, open_=False):
        add(t0, noise(0.12 if open_ else 0.04, 6.0 if open_ else 10.0, 0.93), g)

    def bass(t0, f, dur=0.22, g=0.34):
        add(t0, sine(f, dur, 5.5, 0.004, harm=((2, 0.35), (3, 0.12))), g)

    def pluck(t0, f, g=0.09):
        add(t0, sine(f, 0.32, 7.0, 0.002, harm=((2, 0.3), (3, 0.1))), g)

    def stab(t0, notes, g=0.07, dur=0.42):
        for f in notes:
            add(t0, sine(f, dur, 6.0, 0.004, harm=((2, 0.25),)), g)

    def impact(t0, g=0.75):
        add(t0, sine(70, 1.1, 3.5, 0.002, 34), g)
        add(t0, noise(0.9, 4.0, 0.0, 0.18), 0.35)

    def riser(t0, dur, g=0.26):
        m = int(dur * SR)
        low = band = 0.0
        q = 0.4
        out = []
        for i in range(m):
            x = i / m
            f = 300 + 5200 * x * x
            a = 2 * math.sin(math.pi * f / SR)
            v = rnd.uniform(-1, 1)
            low += a * band
            high = v - low - q * band
            band += a * high
            out.append(band * (x ** 1.5))
        pk = max(abs(v) for v in out) or 1.0
        add(t0, [v / pk for v in out], g)
        add(t0, sine(180, dur, 0.0, 0.01, 1800), g * 0.18)

    # Akkorde Am - F - C - G, je Takt (4 Schläge = 2 s)
    chords = [
        ((110.0, 130.81, 164.81, 220.0), 55.0),
        ((87.31, 110.0, 130.81, 174.61), 43.65),
        ((130.81, 164.81, 196.0, 261.63), 65.41),
        ((98.0, 123.47, 146.83, 196.0), 49.0),
    ]
    sec = {name: (st, st + ln) for name, st, ln in SCENES}

    def level(t0):
        """Dichte je Szene: 0 = nur Puls, 1 = voller Beat."""
        if t0 < sec["problem"][0]:
            return 0.35
        if t0 < sec["loesung"][0]:
            return 0.5
        if t0 < sec["vertrauen"][0]:
            return 1.0
        if t0 < sec["abbinder"][0]:
            return 0.55
        return 0.9

    for b in range(int(DUR / BEAT)):
        t0 = b * BEAT
        lv = level(t0)
        chord, root = chords[(b // 4) % 4]
        bib = b % 4
        kick(t0, 0.85 if lv < 0.9 else 0.95)
        hat(t0 + BEAT / 2, 0.13 * (0.6 + 0.4 * lv), open_=True)
        if lv >= 0.5:
            hat(t0 + BEAT / 4, 0.07)
            hat(t0 + BEAT * 3 / 4, 0.07)
        if lv >= 0.9 and bib in (1, 3):
            clap(t0, 0.5)
        if lv >= 0.5:
            bass(t0 + BEAT / 2, root * (2 if bib == 3 else 1), 0.2, 0.3 * lv)
            if bib in (0, 2):
                bass(t0 + BEAT * 0.75, root, 0.14, 0.2 * lv)
        elif bib in (0, 2):
            bass(t0 + BEAT / 2, root, 0.2, 0.22)
        if lv >= 0.9:
            notes = [chord[0] * 2, chord[1] * 2, chord[2] * 2, chord[3] * 2]
            for q in range(4):
                pluck(t0 + q * BEAT / 4, notes[(q + bib) % 4], 0.075)
        if lv >= 0.9 and bib == 0:
            stab(t0, chord[:3], 0.06)
        if lv >= 0.9 and bib == 2:
            stab(t0 + BEAT * 0.75, chord[:3], 0.045, 0.3)

    for name, st, ln in SCENES[1:]:
        riser(st - 2.0, 2.0, 0.24)
        impact(st, 0.6 if name != "abbinder" else 0.8)
    for tt in (0.0, 1.0, 2.0):
        impact(tt, 0.5 if tt == 0.0 else 0.35)

    def ding(t0, f, gain=0.2):
        add(t0, sine(f, 0.7, 4.0, 0.002, harm=((2, 0.3),)), gain)

    for j, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        ding(sec["abbinder"][0] + 0.1 + j * 0.12, f, 0.17)
    ding(sec["loesung"][0] + 0.05, 659.25, 0.22)

    duck = [1.0] * n
    vo = [0.0] * n
    if voice_dir:
        starts = [0.3, 4.3, 12.8, 22.4, 38.3, 44.8]
        prev_end = 0.0
        for k, st in enumerate(starts, 1):
            src = None
            for ext in (".mp3", ".m4a", ".wav"):
                p = os.path.join(voice_dir, f"{k}{ext}")
                if os.path.exists(p):
                    src = p
                    break
            if not src:
                continue
            wav = os.path.join(FRAMES, f"vo_{k}.wav")
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", src, wav], check=True)
            with wave.open(wav) as w:
                raw = w.readframes(w.getnframes())
            vals = struct.unpack("<" + "h" * (len(raw) // 2), raw)
            pk = max(abs(v) for v in vals) or 1
            samples = [v / pk * 0.9 for v in vals]
            t0 = max(st, prev_end + 0.15)
            end = t0 + len(samples) / SR
            prev_end = end
            print(f"  Sprecher {k}: {t0:5.2f}s bis {end:5.2f}s", flush=True)
            for i2, v in enumerate(samples):
                j = int(t0 * SR) + i2
                if 0 <= j < n:
                    vo[j] += v
            a, b = int((t0 - 0.1) * SR), int((end + 0.25) * SR)
            for j in range(max(0, a), min(n, b)):
                ramp = min(1.0, (j - a) / (0.1 * SR), (b - j) / (0.25 * SR))
                duck[j] = min(duck[j], 1.0 - 0.5 * max(0.0, ramp))
    mix = [buf[k] * duck[k] + vo[k] for k in range(n)]
    rms = math.sqrt(sum(v * v for v in mix) / n) or 1.0
    scale = 0.125 / rms
    fade_in, fade_out = int(0.05 * SR), int(0.9 * SR)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        out = bytearray()
        for k, v in enumerate(mix):
            y = v * scale
            m = abs(y)
            if m > 0.7:
                y = math.copysign(0.7 + 0.28 * math.tanh((m - 0.7) / 0.28), y)
            if k < fade_in:
                y *= k / fade_in
            if k > n - fade_out:
                y *= (n - k) / fade_out
            sv = int(max(-1.0, min(1.0, y)) * 32767)
            out += struct.pack("<hh", sv, sv)
        w.writeframes(bytes(out))


def encode(wav, mp4):
    enc = os.path.join(FRAMES, "encode")
    src = os.path.join(HERE, "..", "tiktok-ad-01", "encode.swift")
    if not os.path.exists(enc) or os.path.getmtime(enc) < os.path.getmtime(src):
        print("Swift-Encoder bauen …", flush=True)
        subprocess.run(["swiftc", "-O", "-swift-version", "5", "-suppress-warnings", src, "-o", enc], check=True)
    subprocess.run([enc, FRAMES, str(FPS), str(NF), wav, mp4, str(W), str(H)], check=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    os.makedirs(FRAMES, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    if mode == "poster":
        secs = [float(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1,5,10,16,26,32,40,46").split(",")]
        for s in secs:
            render_frame((int(s * FPS), FRAMES))
        print("Testbilder in", FRAMES)
        return
    voice_dir = sys.argv[2] if mode == "voice" and len(sys.argv) > 2 else None
    if mode != "audio":
        print(f"Rendere {NF} Bilder …", flush=True)
        with Pool() as pool:
            for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, FRAMES) for i in range(NF)], chunksize=6)):
                if k % 200 == 0:
                    print(f"  {k}/{NF}", flush=True)
    tag = "mit_Stimme" if voice_dir else "ohne_Sprecher"
    wav = os.path.join(FRAMES, f"audio_{tag}.wav")
    print("Ton …", flush=True)
    build_audio(wav, voice_dir)
    mp4 = os.path.join(OUT, f"sellcheck_corporate_16x9_{tag}.mp4")
    encode(wav, mp4)
    print("Fertig:", mp4)


if __name__ == "__main__":
    main()
