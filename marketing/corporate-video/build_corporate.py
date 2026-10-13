#!/usr/bin/env python3
"""SellCheck Corporate-Video, 16:9 (1920x1080, 30 fps), ca. 60 s.

Zweck: Erklärfilm für Website und Social. Läuft auch ohne Ton (die Botschaft steht im Bild).
Aufbau: Hook, Problem, Lösung, Produkt (echte Oberfläche), Vertrauen, Abbinder.

    python3 marketing/corporate-video/build_corporate.py            # Bild und Musik (ohne Sprecher)
    python3 marketing/corporate-video/build_corporate.py voice DIR  # mit Sprachclips aus DIR (1.mp3 ... 6.mp3)
    python3 marketing/corporate-video/build_corporate.py poster 3,12,25   # Einzelbilder zum Prüfen

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

from PIL import Image, ImageDraw, ImageFont

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

# Szenen: (Name, Start, Länge)
SCENES = [("hook", 0.0, 6.5), ("problem", 6.5, 11.0), ("loesung", 17.5, 11.0), ("produkt", 28.5, 18.0),
          ("vertrauen", 46.5, 8.0), ("abbinder", 54.5, 5.5)]
DUR = 60.0
NF = int(DUR * FPS)
FADE = 0.4  # Ausblenden vor jedem Szenenstart

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


def ease_back(p, k=1.4):
    p = clamp(p)
    return 1 + (k + 1) * (p - 1) ** 3 + k * (p - 1) ** 2


class Canvas:
    def __init__(self, bg):
        self.im = Image.new("RGBA", (W * S, H * S), bg + (255,))
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, width=0):
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], r * S, fill=fill, outline=outline, width=int(width * S))

    def rect(self, x0, y0, x1, y1, fill):
        self.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill)

    def circle(self, cx, cy, r, fill=None, outline=None, width=0):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill, outline=outline, width=int(width * S))

    def line(self, pts, fill, width):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S), joint="curve")

    def text(self, x, y, s, size, weight, fill, anchor="la"):
        self.d.text((x * S, y * S), s, font=font(size * S, weight), fill=fill, anchor=anchor)

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
        self.im.alpha_composite(tmp)
        return w / S

    def paste(self, img, x, y, alpha=1.0):
        if alpha < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        self.im.alpha_composite(img, (int(x * S), int(y * S)))


def rise(c, x, y, s, size, weight, fill, t, t0, anchor="la", dist=22, dur=0.55):
    """Text gleitet leicht von unten ein und blendet auf."""
    p = ease_out(prog(t, t0, dur))
    if p <= 0:
        return
    col = tuple(fill[:3]) + (int((fill[3] if len(fill) > 3 else 255) * p),)
    c.text(x, y + (1 - p) * dist, s, size, weight, col, anchor)


def pill(c, cx, cy, w, h, fill=None, outline=None, width=0):
    c.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, h / 2, fill=fill, outline=outline, width=width)


def check(c, cx, cy, r, bg=LIME, fg=INK, a=255):
    c.circle(cx, cy, r, fill=bg + (a,))
    c.line([(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.46, cy - r * 0.32)], fg + (a,), max(2, r * 0.22))


def money(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"


def glow(c, box, alpha):
    """Weicher Lichtfleck (Lime) hinter dem Inhalt."""
    from PIL import ImageFilter
    g = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([box[0] * S, box[1] * S, box[2] * S, box[3] * S], fill=LIME + (int(alpha),))
    g = g.filter(ImageFilter.GaussianBlur(170 * S))
    c.im.alpha_composite(g)


def bug(c, on_dark):
    """Kleines Logo oben links als durchgehende Marke."""
    c.logo(60 + 105, 74, 50, 0.9, on_dark=on_dark)


# ------------------------------------------------------------------ Szenen
def scene_hook(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    glow(c, (1200, 150, 2000, 950), 40)
    bug(c, True)
    rise(c, 140, 360, "Wer auf mehreren Plattformen verkauft,", 62, "medium", PAPER + (200,), t, 0.4)
    rise(c, 140, 450, "verliert schnell", 124, "heavy", PAPER, t, 1.3)
    rise(c, 140, 585, "den Überblick.", 124, "heavy", LIME, t, 1.6)
    names = [("Vinted", 1230, 250), ("Kleinanzeigen", 1450, 380), ("eBay", 1330, 540), ("Etsy", 1560, 690), ("Amazon", 1250, 820)]
    for k, (nm, x, y) in enumerate(names):
        p = ease_out(prog(t, 0.8 + k * 0.22, 0.7))
        if p <= 0:
            continue
        w = c.tw(nm, 40, "demi") + 70
        dx = (1 - p) * 120
        dy = 8 * math.sin(t * 1.2 + k * 1.3)
        a = int(255 * p)
        pill(c, x + dx + w / 2, y + dy, w, 78, fill=INK2 + (a,), outline=(70, 78, 92, a), width=2)
        c.text(x + dx + w / 2, y + dy + 1, nm, 40, "demi", PAPER + (a,), "mm")


def platform_card(c, x, y, w, name, n, color, status, t, t0):
    p = ease_out(prog(t, t0, 0.7))
    if p <= 0:
        return
    a = int(255 * p)
    yy = y + (1 - p) * 30
    c.rrect(x, yy, x + w, yy + 300, 30, fill=WHITE + (a,), outline=LINE + (a,), width=2)
    c.text(x + 34, yy + 54, name, 36, "heavy", INK + (a,), "lm")
    v = int(round(n * ease_out(prog(t, t0 + 0.2, 1.3))))
    c.text(x + 34, yy + 142, str(v), 82, "heavy", INK + (a,), "lm")
    c.text(x + 34 + c.tw(str(v), 82, "heavy") + 14, yy + 156, "von 30", 34, "medium", DARKMUTED + (a,), "lm")
    bx0, bx1, by = x + 34, x + w - 34, yy + 214
    c.rrect(bx0, by, bx1, by + 18, 9, fill=(236, 233, 223, a))
    fill = ease_out(prog(t, t0 + 0.2, 1.3)) * min(1.0, n / 30)
    if fill > 0.01:
        c.rrect(bx0, by, bx0 + (bx1 - bx0) * fill, by + 18, 9, fill=color + (a,))
    c.text(x + 34, yy + 262, status, 28, "medium", color_dark(color) + (a,), "lm")


def color_dark(col):
    return {GREEN: DEEPGREEN, AMBER: (150, 96, 0), RED: (176, 40, 30)}.get(col, DARKMUTED)


def scene_problem(c, t):
    c.rect(0, 0, W, H, PAPER + (255,))
    bug(c, False)
    rise(c, 140, 260, "Jede Plattform zählt für sich.", 84, "heavy", INK, t, 0.3)
    rise(c, 140, 372, "Eigene Zähler, eigene Grenzen, kein Gesamtbild.", 38, "medium", DARKMUTED, t, 0.9)
    cards = [("Vinted", 21, AMBER, "Nähert sich der Grenze"), ("Kleinanzeigen", 8, GREEN, "Weit entfernt"),
             ("eBay", 2, GREEN, "Weit entfernt"), ("Etsy", 31, RED, "Grenze erreicht")]
    cw, gap = 395, 28
    for k, (nm, n, col, st) in enumerate(cards):
        platform_card(c, 140 + k * (cw + gap), 450, cw, nm, n, col, st, t, 1.5 + k * 0.28)
    c.text(1780, 782, "Beispieldaten", 24, "medium", DARKMUTED, "ra")
    p = ease_out(prog(t, 6.6, 0.8))
    if p > 0:
        a = int(255 * p)
        c.rrect(140, 830 + (1 - p) * 30, 1780, 1000 + (1 - p) * 30, 34, fill=INK + (a,))
        c.text(200, 884 + (1 - p) * 30, "Ab 30 Verkäufen oder 2.000 € im Jahr melden Plattformen", 44, "heavy", PAPER + (a,), "lm")
        c.text(200, 944 + (1 - p) * 30, "an die Steuerbehörden. Je Plattform, nicht insgesamt. Eine Meldung ist keine Steuerforderung.", 30, "medium", MUTED + (a,), "lm")


def overview_card(c, x, y, t, t0):
    """Gesamtübersicht (Beispieldaten), wie in der Produktvorschau auf der Website."""
    p = ease_out(prog(t, t0, 0.8))
    if p <= 0:
        return
    a = int(255 * p)
    yy = y + (1 - p) * 40
    w, h = 720, 800
    sh = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x * S, (yy + 18) * S, (x + w) * S, (yy + h + 18) * S], 40 * S, fill=(0, 0, 0, int(90 * p)))
    c.im.alpha_composite(sh)
    c.rrect(x, yy, x + w, yy + h, 40, fill=PAPER + (a,))
    c.text(x + 44, yy + 62, "Gewinn 2026 · alle Plattformen", 28, "demi", DARKMUTED + (a,), "lm")
    pill(c, x + w - 44 - 110, yy + 62, 220, 42, fill=(255, 243, 199, a))
    c.text(x + w - 44 - 110, yy + 63, "Beispieldaten", 22, "demi", (122, 82, 0, a), "mm")
    val = 842.5 * ease_out(prog(t, t0 + 0.4, 1.5))
    c.text(x + 44, yy + 150, money(val), 84, "heavy", INK + (a,), "lm")
    c.text(x + 44 + c.tw(money(842.5), 84, "heavy") + 16, yy + 166, "nach Kosten", 28, "demi", DEEPGREEN + (a,), "lm")
    c.rrect(x + 36, yy + 214, x + w - 36, yy + 470, 26, fill=WHITE + (a,), outline=LINE + (a,), width=2)
    rows = [("Vinted", 21, AMBER), ("Kleinanzeigen", 8, GREEN), ("eBay", 2, GREEN)]
    for k, (nm, n, col) in enumerate(rows):
        ry = yy + 252 + k * 74
        c.text(x + 70, ry, nm, 28, "demi", INK + (a,), "lm")
        c.text(x + w - 70, ry, f"{n} von 30", 28, "demi", INK + (a,), "rm")
        c.rrect(x + 70, ry + 24, x + w - 70, ry + 38, 7, fill=(236, 233, 223, a))
        f = ease_out(prog(t, t0 + 0.6 + k * 0.15, 1.1)) * n / 30
        if f > 0.01:
            c.rrect(x + 70, ry + 24, x + 70 + (w - 140) * f, ry + 38, 7, fill=col + (a,))
    items = [("Nike Air Max 90", "+ 33,50 €", DEEPGREEN), ("Retro-Konsole", "+ 38,10 €", DEEPGREEN), ("Zara Mantel M", "− 2,00 €", RED)]
    for k, (nm, v, col) in enumerate(items):
        ry = yy + 540 + k * 84
        pa = int(a * ease_out(prog(t, t0 + 1.2 + k * 0.25, 0.5)))
        c.line([(x + 44, ry - 42), (x + w - 44, ry - 42)], LINE + (pa,), 2)
        c.text(x + 44, ry, nm, 30, "demi", INK + (pa,), "lm")
        c.text(x + w - 44, ry, v, 30, "heavy", col + (pa,), "rm")


def scene_loesung(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    shift = ease_io(prog(t, 3.2, 0.9))
    cx = 960 + (520 - 960) * shift
    pl = ease_back(prog(t, 0.2, 0.7))
    h = 150 * (0.8 + 0.2 * pl)
    c.logo(cx, 330 + (0 if shift == 0 else -10 * shift), h, clamp(prog(t, 0.2, 0.35)))
    rise(c, cx, 480, "bringt alles", 84, "heavy", PAPER, t, 1.0, "mm")
    rise(c, cx, 580, "zusammen.", 84, "heavy", LIME, t, 1.2, "mm")
    overview_card(c, 1030, 140, t, 3.6)
    bullets = ["Gewinn pro Artikel", "Meldegrenze je Plattform", "Bestand an einem Ort"]
    for k, b in enumerate(bullets):
        p = ease_out(prog(t, 5.6 + k * 0.45, 0.5))
        if p <= 0:
            continue
        a = int(255 * p)
        y = 730 + k * 80 + (1 - p) * 16
        check(c, 240, y, 22, a=a)
        c.text(284, y, b, 40, "demi", PAPER + (a,), "lm")


def window(c, x, y, w, img, t, zoom_from=1.0, zoom_to=1.07, focus=(0.5, 0.35), alpha=1.0):
    """Browserfenster mit Aufnahme. Der Bildausschnitt zoomt langsam (Ken Burns)."""
    if alpha <= 0:
        return
    iw, ih = img.size
    ch = w * ih / iw
    bar = 44
    a = int(255 * alpha)
    sh = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x * S, (y + 22) * S, (x + w) * S, (y + bar + ch + 22) * S], 24 * S, fill=(14, 17, 22, int(70 * alpha)))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(26 * S))
    c.im.alpha_composite(sh)
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
    # obere Ecken gerade (unter der Leiste), untere rund
    ImageDraw.Draw(mask).rectangle([0, 0, crop.width, 24 * S], fill=255)
    tile = crop.convert("RGBA")
    tile.putalpha(mask.point(lambda v: int(v * alpha)))
    c.im.alpha_composite(tile, (int(x * S), int((y + bar) * S)))


_IMGS = {}


def shot(name):
    if name not in _IMGS:
        _IMGS[name] = Image.open(os.path.join(ASSETS, name)).convert("RGB")
    return _IMGS[name]


BEATS = [
    ("Import in Sekunden.", "CSV aus Plattform, PayPal oder Online-Banking. Die Datei wird nur im Browser gelesen.", "ui_import.png", (0.5, 0.55), 1.55),
    ("Die Meldegrenze als Ampel.", "Je Plattform sofort sichtbar: Grün, Gelb oder Rot, dazu der Gewinn.", "ui_limits.png", (0.5, 0.85), 1.5),
    ("Ein Report für die Steuererklärung.", "Ausfüllhilfe für die Anlage EÜR und CSV-Dateien für den Steuerberater.", "ui_report.png", (0.5, 0.0), 1.45),
]


def scene_produkt(c, t):
    c.rect(0, 0, W, H, PAPER + (255,))
    bug(c, False)
    beat_len = 6.0
    k = min(2, int(t // beat_len))
    lt = t - k * beat_len
    # Fenster: Aufnahmen überblenden jeweils in den ersten 0.5 s
    for j in range(3):
        if j > k:
            continue
        jt = t - j * beat_len
        a = ease_out(prog(jt, 0.0, 0.5)) if j == k else (1.0 - ease_out(prog(t - (j + 1) * beat_len, 0.0, 0.5)))
        if j < k and a <= 0:
            continue
        name = BEATS[j][2]
        window(c, 800, 190, 1020, shot(name), clamp(jt / beat_len), BEATS[j][4], BEATS[j][4] + 0.1, BEATS[j][3], alpha=a)
    title, desc = BEATS[k][0], BEATS[k][1]
    # Textblock links
    p = ease_out(prog(lt, 0.15, 0.55))
    a = int(255 * p)
    lines = c.wrap(title, 66, "heavy", 620)
    y = 400 + (1 - p) * 24
    for ln in lines:
        c.text(140, y, ln, 66, "heavy", INK + (a,), "lm")
        y += 78
    dp = ease_out(prog(lt, 0.55, 0.55))
    for ln in c.wrap(desc, 32, "medium", 600):
        c.text(140, y + 28 + (1 - dp) * 16, ln, 34, "medium", DARKMUTED + (int(255 * dp),), "lm")
        y += 48
    # Fortschrittspunkte
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
    bug(c, True)
    lines = ["Kein Zugriff auf Plattform-Konten.", "Daten bleiben im Browser.", "Orientierung statt Steuerberatung."]
    for k, ln in enumerate(lines):
        p = ease_out(prog(t, 0.4 + k * 0.9, 0.6))
        if p <= 0:
            continue
        a = int(255 * p)
        y = 380 + k * 150 + (1 - p) * 24
        check(c, 190, y, 32, a=a)
        c.text(260, y, ln, 62, "heavy", PAPER + (a,), "lm")
    p = ease_out(prog(t, 0.3, 1.0))
    lock_icon(c, 1640, 470, 280, int(255 * p))
    c.text(140, 1000, "Unabhängig von den genannten Plattformen.", 28, "medium", MUTED + (int(255 * ease_out(prog(t, 3.6, 0.5))),), "lm")


def scene_abbinder(c, t):
    c.rect(0, 0, W, H, INK + (255,))
    glow(c, (560, 250, 1360, 1050), 46 * ease_out(prog(t, 0, 1.2)))
    pl = ease_back(prog(t, 0.0, 0.6))
    c.logo(960, 255, 170 * (0.85 + 0.15 * pl), clamp(prog(t, 0.0, 0.3)))
    rise(c, 960, 480, "Check, was", 112, "heavy", PAPER, t, 0.5, "mm")
    rise(c, 960, 610, "wirklich bleibt.", 112, "heavy", LIME, t, 0.7, "mm")
    p = ease_back(prog(t, 1.6, 0.5))
    if p > 0:
        w = c.tw("Kostenlos, ohne Anmeldung", 42, "heavy") + 110
        pill(c, 960, 790, w * (0.9 + 0.1 * p), 100, fill=LIME + (int(255 * clamp(p * 3)),))
        c.text(960, 792, "Kostenlos, ohne Anmeldung", 42, "heavy", INK + (int(255 * clamp(p * 3)),), "mm")
    fa = int(255 * ease_out(prog(t, 2.2, 0.5)))
    c.text(960, 960, "SellCheck ist ein unabhängiges Projekt und mit keiner der genannten Plattformen verbunden.", 24, "medium", MUTED + (fa,), "mm")
    c.text(960, 998, "Keine Steuer- oder Rechtsberatung. Alle Angaben ohne Gewähr.", 24, "medium", MUTED + (fa,), "mm")


FUNCS = {"hook": scene_hook, "problem": scene_problem, "loesung": scene_loesung, "produkt": scene_produkt,
         "vertrauen": scene_vertrauen, "abbinder": scene_abbinder}
BG = {"hook": INK, "problem": PAPER, "loesung": INK, "produkt": PAPER, "vertrauen": INK, "abbinder": INK}


def render_scene(idx, t):
    name, start, length = SCENES[idx]
    c = Canvas(BG[name])
    FUNCS[name](c, max(0.0, t - start))
    return c.im


def render_frame(args):
    i, path_dir = args
    t = i / FPS
    idx = 0
    for k, (_, st, ln) in enumerate(SCENES):
        if t >= st:
            idx = k
    im = render_scene(idx, t)
    # Übergang: Der Inhalt blendet in die Hintergrundfarbe der nächsten Szene aus (kein Text über Text)
    if idx + 1 < len(SCENES):
        nxt = SCENES[idx + 1][1]
        if t > nxt - FADE:
            a = ease_io(clamp((t - (nxt - FADE)) / FADE))
            flat = Image.new("RGBA", im.size, BG[SCENES[idx + 1][0]] + (255,))
            im = Image.blend(im, flat, a)
    im = im.convert("RGB").reduce(S)
    im.save(os.path.join(path_dir, f"f_{i:05d}.jpg"), quality=94, subsampling=0)
    return i


# ------------------------------------------------------------------ Ton
SR = 44100


def build_audio(path, voice_dir=None):
    n = int(SR * DUR)
    buf = [0.0] * n
    rnd = random.Random(11)

    def add(t0, samples, gain=1.0):
        s0 = int(t0 * SR)
        for k, v in enumerate(samples):
            j = s0 + k
            if 0 <= j < n:
                buf[j] += v * gain

    def tone(f, dur, decay=4.0, attack=0.02, detune=0.0, harm=()):
        m = int(dur * SR)
        out = []
        for i in range(m):
            x = i / m
            tt = i / SR
            env = math.exp(-decay * x) * min(1.0, tt / attack)
            v = math.sin(2 * math.pi * f * tt)
            if detune:
                v += math.sin(2 * math.pi * f * (1 + detune) * tt)
                v *= 0.5
            for hm, g in harm:
                v += g * math.sin(2 * math.pi * f * hm * tt)
            out.append(v * env)
        return out

    def pad(f, dur):
        m = int(dur * SR)
        out = []
        for i in range(m):
            tt = i / SR
            env = min(1.0, tt / 1.1) * min(1.0, (dur - tt) / 1.4)
            v = (math.sin(2 * math.pi * f * tt) + math.sin(2 * math.pi * f * 1.004 * tt) + 0.5 * math.sin(2 * math.pi * f * 2 * tt)) / 2.5
            out.append(v * env)
        return out

    bpm = 84
    beat = 60.0 / bpm
    bar = 4 * beat
    # Am7 - Fmaj7 - Cmaj7 - G6 (je ein Takt)
    prog_chords = [((110.0, 164.81, 196.0, 261.63), 55.0), ((87.31, 130.81, 164.81, 220.0), 43.65),
                   ((130.81, 196.0, 246.94, 329.63), 65.41), ((98.0, 146.83, 196.0, 246.94), 49.0)]
    nbars = int(DUR / bar) + 1
    for b in range(nbars):
        chord, root = prog_chords[b % 4]
        t0 = b * bar
        # Lautstärke-Verlauf: leise Einleitung, Aufbau zur Lösung, volle Mitte, ruhiger Ausklang
        lvl = 0.55 + 0.45 * clamp((t0 - 4) / 14)
        if t0 > 50:
            lvl *= max(0.35, 1 - (t0 - 50) / 14)
        for f in chord[:3]:
            add(t0, pad(f, bar + 0.6), 0.045 * lvl)
        add(t0, tone(root, bar * 0.95, 1.6, 0.04), 0.16 * lvl)
        # Arpeggio in Achteln (ab der Lösung deutlicher)
        arp_gain = 0.0 if t0 < 6 else (0.05 + 0.04 * clamp((t0 - 17) / 10))
        if arp_gain > 0:
            notes = [chord[0] * 2, chord[1] * 2, chord[2] * 2, chord[3] * 2, chord[2] * 2, chord[1] * 2, chord[3] * 2, chord[1] * 2]
            for q in range(8):
                add(t0 + q * beat / 2, tone(notes[q], 0.55, 6.5, 0.004, harm=((2, 0.18),)), arp_gain * lvl)
        # leiser Puls auf der Eins und der Drei
        for q in (0, 2):
            add(t0 + q * beat, tone(58.0, 0.28, 9.0, 0.004), 0.12 * lvl)

    def ding(t0, f, gain=0.16):
        add(t0, tone(f, 0.6, 4.0, 0.003), gain)
        add(t0, tone(f * 2, 0.4, 6.0, 0.003), gain * 0.3)

    ding(SCENES[2][1] + 0.35, 659.25)                        # Logo erscheint
    for j, f in enumerate((523.25, 659.25, 783.99, 1046.5)):  # Abbinder
        ding(SCENES[5][1] + 0.9 + j * 0.1, f, 0.14)

    duck = [1.0] * n
    vo = [0.0] * n
    if voice_dir:
        starts = [0.4, 6.9, 17.9, 28.9, 46.9, 54.7]
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
            t0 = max(st, prev_end + 0.2)
            end = t0 + len(samples) / SR
            prev_end = end
            print(f"  Sprecher {k}: {t0:5.2f}s bis {end:5.2f}s", flush=True)
            for i2, v in enumerate(samples):
                j = int(t0 * SR) + i2
                if 0 <= j < n:
                    vo[j] += v
            a, b = int((t0 - 0.2) * SR), int((end + 0.4) * SR)
            for j in range(max(0, a), min(n, b)):
                ramp = min(1.0, (j - a) / (0.2 * SR), (b - j) / (0.4 * SR))
                duck[j] = min(duck[j], 1.0 - 0.55 * max(0.0, ramp))
    mix = [buf[k] * duck[k] + vo[k] for k in range(n)]
    peak = max(abs(v) for v in mix) or 1.0
    scale = 0.85 / peak
    fade_in, fade_out = int(0.8 * SR), int(1.2 * SR)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        out = bytearray()
        for k, v in enumerate(mix):
            if k < fade_in:
                v *= k / fade_in
            if k > n - fade_out:
                v *= (n - k) / fade_out
            sv = int(max(-1.0, min(1.0, v * scale)) * 32767)
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
    if mode == "transitions":
        idxs = []
        for _, st, _ in SCENES[1:]:
            idxs += [i for i in range(NF) if st - FADE <= i / FPS < st]
        with Pool() as pool:
            list(pool.imap_unordered(render_frame, [(i, FRAMES) for i in idxs]))
        print(len(idxs), "Übergangsbilder neu gerendert")
        mode = "audio"
    if mode == "poster":
        secs = [float(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "2,10,22,32,40,50,57").split(",")]
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
