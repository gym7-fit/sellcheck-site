#!/usr/bin/env python3
"""SellCheck Corporate-Video, 16:9 (1920x1080, 30 fps), ca. 49 s.

Zweck: Erklärfilm für Website und Social. Läuft auch ohne Ton (die Botschaft steht im Bild).
Schnitt auf einem 120-bpm-Raster: Schrift schlägt im Beat ein, Wisch-Übergänge auf den Takt, treibender Beat.

    python3 marketing/corporate-video/build_corporate.py              # Bild und Musik (ohne Sprecher)
    python3 marketing/corporate-video/build_corporate.py voice DIR    # mit Sprachclips aus DIR (1.mp3 ... 6.mp3)
    python3 marketing/corporate-video/build_corporate.py poster 3,12  # Einzelbilder zum Prüfen
    python3 marketing/corporate-video/build_corporate.py audio        # nur Ton neu, Bilder bleiben
    python3 marketing/corporate-video/build_corporate.py analyze TRACK            # Tempo und Taktanfang eines Tracks bestimmen
    python3 marketing/corporate-video/build_corporate.py music TRACK [OFFSET]    # mit lizenziertem Track statt Synthese
    python3 marketing/corporate-video/build_corporate.py music TRACK [OFFSET] voice DIR   # Track plus Sprecher
    python3 marketing/corporate-video/build_corporate.py grid WAV [voice DIR]     # eigene Musik auf dem Raster (corporate_music2.py)

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
        slam(c, 200, 850 + off, "30 Verkäufe oder 2.000 € im Jahr.", 72, "heavy", PAPER, t, 4.0)
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


def load_track(path):
    """Beliebige Audiodatei als Stereo-Listen (44,1 kHz) laden (macOS afconvert)."""
    wav = os.path.join(FRAMES, "track_in.wav")
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "2", path, wav], check=True)
    with wave.open(wav) as w:
        raw = w.readframes(w.getnframes())
    v = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    return [x / 32768 for x in v[0::2]], [x / 32768 for x in v[1::2]]


def analyze_tempo(left, right):
    """Grobe Tempo- und Taktanfang-Bestimmung: Onset-Hüllkurve, Kamm über Tempo und Phase.
    Liefert (bpm, erster_Schlag_s, Taktanfang_s). Für Tracks mit klarem Puls ausreichend, immer gegenprüfen."""
    sr = SR
    mono = [(a + b) * 0.5 for a, b in zip(left, right)]
    hop = 441  # 10 ms
    env = []
    low = []
    y = 0.0
    a_lp = 1 - math.exp(-2 * math.pi * 150 / sr)
    for i in range(0, len(mono) - hop, hop):
        seg = mono[i:i + hop]
        env.append(sum(v * v for v in seg) / hop)
        e = 0.0
        for v in seg:
            y += a_lp * (v - y)
            e += y * y
        low.append(e / hop)
    env = [math.sqrt(v) for v in env]
    low = [math.sqrt(v) for v in low]
    on = [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]
    onl = [max(0.0, low[i] - low[i - 1]) for i in range(1, len(low))]
    N = len(on)

    def ac(lag):
        if lag >= N - 1:
            return 0.0
        return sum(on[i] * on[i + lag] for i in range(0, N - lag)) / (N - lag)

    # Autokorrelation mit Vorliebe für übliche Tempi (um 120 bpm), Vielfache stützen den Kandidaten
    cache = {}

    def acc(lag):
        if lag not in cache:
            cache[lag] = ac(lag)
        return cache[lag]

    best = (-1.0, 120.0)
    for lag in range(30, 101):           # 60 bis 200 bpm
        bpm_c = 6000.0 / lag
        prior = math.exp(-0.5 * (math.log2(bpm_c / 120.0) / 0.55) ** 2)
        sc = (acc(lag) + 0.5 * acc(2 * lag) + 0.25 * acc(4 * lag)) * prior
        if sc > best[0]:
            best = (sc, bpm_c)
    bpm = best[1]
    # Verfeinern: Kamm über Tempo ±3 % in 0,1-%-Schritten
    ref = (-1.0, bpm)
    f = 0.97
    while f <= 1.03:
        period = 6000.0 / (bpm * f)
        sc, pos = 0.0, 0.0
        while pos < N - 1:
            sc += on[int(pos)]
            pos += period
        sc *= 1.0
        if sc / max(1.0, (N / period)) > ref[0]:
            ref = (sc / max(1.0, (N / period)), bpm * f)
        f += 0.001
    bpm = ref[1]
    period = 6000.0 / bpm
    best_ph, best_sc = 0.0, -1.0
    ph = 0.0
    while ph < period:
        sc, pos = 0.0, ph
        while pos < N - 1:
            sc += on[int(pos)]
            pos += period
        if sc > best_sc:
            best_ph, best_sc = ph, sc
        ph += 1.0
    # Taktanfang: Schlag (1 von 4) mit der stärksten tiefen Energie
    sums = [0.0] * 4
    k, pos = 0, best_ph
    while pos < len(onl) - 1:
        sums[k % 4] += onl[int(pos)]
        pos += period
        k += 1
    down = max(range(4), key=lambda i: sums[i])
    beat0 = best_ph / 100.0
    return bpm, beat0, beat0 + down * 60.0 / bpm


DROP_AT = 12.0  # Sekunde im Video, an der die volle Energie einsetzen soll


def find_drop(left, right, bpm, down):
    """Stärkster Energiesprung auf der Taktgrenze (Sekunden im Original) oder None."""
    sr = SR
    bar = 60.0 / bpm * 4
    mono = [(a + b) * 0.5 for a, b in zip(left, right)]
    g0 = down % bar
    nb = int((len(mono) / sr - g0) / bar)
    e = []
    for k in range(nb):
        a, z = int((g0 + k * bar) * sr), int((g0 + (k + 1) * bar) * sr)
        seg = mono[a:z:8]
        e.append(10 * math.log10(sum(v * v for v in seg) / max(1, len(seg)) + 1e-12))
    best, kb = 0.0, None
    need = int(math.ceil(DROP_AT / bar)) + 1  # davor genug Takte, damit der Start nicht negativ wird
    for k in range(max(4, need), nb - 4):
        gain = sum(e[k:k + 4]) / 4 - sum(e[k - 4:k]) / 4
        if gain > best:
            best, kb = gain, k
    if kb is None or best < 3.0:
        return None
    return g0 + kb * bar


def stretch(x, factor):
    """Einfaches Umsampeln (verändert Tempo und Tonhöhe leicht), factor > 1 = schneller."""
    n = int(len(x) / factor)
    out = []
    for i in range(n):
        p = i * factor
        j = int(p)
        f = p - j
        a = x[j]
        b = x[j + 1] if j + 1 < len(x) else a
        out.append(a + (b - a) * f)
    return out


def build_audio(path, voice_dir=None, track=None, offset=None, grid=False):
    n = int(SR * DUR)
    if track and grid:
        # Musik wurde auf das Raster des Videos gerechnet (corporate_music2.py): kein Analysieren, kein Strecken
        tl, tr = load_track(track)
        ml = [0.0] * n
        mr = [0.0] * n
        m = min(n, len(tl))
        ml[:m], mr[:m] = tl[:m], tr[:m]
        print("  Musik auf dem Raster, unverändert übernommen", flush=True)
    elif track:
        tl, tr = load_track(track)
        bpm, beat0, down = analyze_tempo(tl, tr)
        print(f"  Track: ca. {bpm:.1f} bpm, erster Schlag bei {beat0:.2f} s, Taktanfang bei {down:.2f} s", flush=True)
        factor = 1.0  # Zeit im Video = Zeit im Original / factor
        if 0.94 <= bpm / BPM <= 1.06 and abs(bpm - BPM) > 0.3:
            factor = BPM / bpm  # auf 120 bpm ziehen: bei 122 bpm etwas langsamer abspielen
        # Startpunkt: Taktanfang aus der Analyse; ohne Angabe wird der stärkste Energiesprung (Drop) auf 12 s gelegt
        if offset is not None:
            start = offset
        else:
            start = down
            drop = find_drop(tl, tr, bpm, down)
            if drop is not None:
                start = drop - DROP_AT * factor
                print(f"  Drop im Original bei {drop:.2f} s, Start bei {start:.2f} s (Drop landet bei {DROP_AT:.0f} s im Video)", flush=True)
        if factor != 1.0:
            tl, tr = stretch(tl, factor), stretch(tr, factor)
            start = start / factor
            print(f"  Tempo angepasst (Faktor {factor:.3f}), etwa {abs(1 - factor) * 100:.1f} % neben dem Original", flush=True)
        elif abs(bpm / BPM - 1) > 0.06:
            print(f"  Hinweis: Tempo weicht stark von 120 bpm ab, Schnitt und Takt passen nicht. Besser einen Track um 120 bpm wählen.", flush=True)
        i0 = int(start * SR)
        ml = [0.0] * n
        mr = [0.0] * n
        for k in range(n):
            j = i0 + k
            if 0 <= j < len(tl):
                ml[k], mr[k] = tl[j], tr[j]
    else:
        sys.path.insert(0, HERE)
        import corporate_music as M
        print("  Musik wird synthetisiert …", flush=True)
        ml, mr = M.build_music(DUR, SCENES)
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
    # Master: Musik auf feste mittlere Lautstärke, Sprache oben drauf, weiche Begrenzung
    rms = math.sqrt(sum(v * v for v in ml) / n) or 1.0
    g = (0.09 if grid else 0.14) / rms
    fade_in, fade_out = int(0.02 * SR), int((0.5 if grid else 2.4 if track else 0.9) * SR)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        out = bytearray()
        for k in range(n):
            l = ml[k] * g * duck[k] + vo[k] * 0.9
            r = mr[k] * g * duck[k] + vo[k] * 0.9
            for ch in (l, r):
                pass
            fl = 1.0
            if k < fade_in:
                fl = k / fade_in
            elif k > n - fade_out:
                fl = (n - k) / fade_out
            vals = []
            for y in (l * fl, r * fl):
                m = abs(y)
                if m > 0.72:
                    y = math.copysign(0.72 + 0.26 * math.tanh((m - 0.72) / 0.26), y)
                vals.append(int(max(-1.0, min(1.0, y)) * 32767))
            out += struct.pack("<hh", vals[0], vals[1])
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
    if mode == "analyze":
        l, r = load_track(sys.argv[2])
        bpm, b0, down = analyze_tempo(l, r)
        print(f"Länge {len(l) / SR:.1f} s, Tempo ca. {bpm:.1f} bpm, erster Schlag {b0:.2f} s, Taktanfang {down:.2f} s")
        print("Hinweis: Wert gegenprüfen (Track im Player anhören, ob der Taktanfang stimmt).")
        return
    if mode == "frames":
        print(f"Rendere {NF} Bilder …", flush=True)
        with Pool() as pool:
            for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, FRAMES) for i in range(NF)], chunksize=6)):
                if k % 200 == 0:
                    print(f"  {k}/{NF}", flush=True)
        print("Bilder fertig in", FRAMES)
        return
    track, offset, voice_dir = None, None, None
    args = sys.argv[2:]
    grid = False
    if mode == "grid" and args:
        grid = True
        track = args.pop(0)
    if mode == "music" and args:
        track = args.pop(0)
        if args and args[0] not in ("voice",):
            offset = float(args.pop(0).replace(",", "."))
    if args and args[0] == "voice" and len(args) > 1:
        voice_dir = args[1]
    elif mode == "voice" and args:
        voice_dir = args[0]
    if mode not in ("audio", "music", "grid"):
        print(f"Rendere {NF} Bilder …", flush=True)
        with Pool() as pool:
            for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, FRAMES) for i in range(NF)], chunksize=6)):
                if k % 200 == 0:
                    print(f"  {k}/{NF}", flush=True)
    tag = "mit_Stimme" if voice_dir else "ohne_Sprecher"
    if track:
        tag += "_Raster" if grid else "_Track"
    wav = os.path.join(FRAMES, f"audio_{tag}.wav")
    print("Ton …", flush=True)
    build_audio(wav, voice_dir, track, offset, grid)
    mp4 = os.path.join(OUT, f"sellcheck_corporate_16x9_{tag}.mp4")
    encode(wav, mp4)
    print("Fertig:", mp4)


if __name__ == "__main__":
    main()
