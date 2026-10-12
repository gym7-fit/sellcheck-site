#!/usr/bin/env python3
"""TikTok-Ad 01 für SellCheck: rendert Frames (PIL), erzeugt den Ton (reine Python-Synthese)
und ruft den Swift-Encoder (AVFoundation) für das fertige MP4 auf.

    python3 marketing/tiktok-ad-01/build_ad.py A      # Hook A: Fakt "Vinted meldet dich ab 30 Verkäufen"
    python3 marketing/tiktok-ad-01/build_ad.py B      # Hook B: POV "4 Plattformen und keine Ahnung"

Ausgabe: marketing/tiktok-ad-01/out/sellcheck_tiktok_ad_<variante>.mp4 (1080x1920, 30 fps, H.264 + AAC)

Aufbau nach TikTok-Praxis: Hook in den ersten 3 s, Marke früh, ein Nutzen (Überblick über alle
Plattformen), Demo statt Behauptung, konkrete Handlung am Ende, wichtige Inhalte innerhalb der
Safe Zone (oben ~160 px, unten ~440 px, rechts ~140 px frei).
Es werden keine Plattform-Logos und keine fremden Marken-Assets verwendet.
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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo-final"))
import sellcheck_logo as LOGO  # echtes SellCheck-Logo (Variante 6B)

W, H, FPS, S = 1080, 1920, 30, 2          # S = Supersampling-Faktor
# Variante: A und B (Hook-Tests der ersten Ad), V2 = "Frist"-Version (Überblick, Ende Januar, Nutzen, Handlung)
VAR = sys.argv[1].upper() if len(sys.argv) > 1 and sys.argv[1].upper() in ("A", "B", "V2", "V3", "V6", "V7", "V8", "V9") else os.environ.get("AD_VARIANT", "A")
os.environ["AD_VARIANT"] = VAR  # damit Worker-Prozesse dieselbe Variante nutzen
# Dauer je Szene = Basiszeit der Animation x Streckung
V2LIKE = VAR in ("V2", "V3", "V6", "V7", "V8", "V9")
if VAR == "V2":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 2.4, 2: 4.0, 3: 7.9, 4: 5.1}
    TARGET = {1: 2.85, 2: 6.85, 3: 8.05, 4: 5.1}  # Sekunden je Szene, abgestimmt auf die Sprechzeiten
    SLOW = {k: TARGET[k] / BASE[k] for k in KEYS}
elif VAR == "V3":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 2.4, 2: 4.0, 3: 7.9, 4: 5.1}
    TARGET = {1: 2.6, 2: 8.2, 3: 8.1, 4: 5.1}  # nach Messung der Sprechzeiten (Clips 2,4 / 8,0 / 8,0 / 3,9 s)
    SLOW = {k: TARGET[k] / BASE[k] for k in KEYS}
elif VAR == "V9":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 5.3, 2: 10.2, 3: 10.4, 4: 5.8}  # Chat 1, Webseite, Chat 2, Endkarte (Sekunden, SLOW = 1; Zeiten nach geschätzter Sprechdauer)
    TARGET = dict(BASE)
    SLOW = {k: 1.0 for k in KEYS}
elif VAR == "V8":
    KEYS = (1, 2, 3, 4, 5)
    BASE = {1: 9.05, 2: 5.9, 3: 10.3, 4: 8.7, 5: 5.8}  # Meldegrenze, Upload und Anleitungen, Ergebnis, Steuer-Übersicht, Endkarte (Sekunden, SLOW = 1; Clips 8,9 / 5,7 / 10,0 / 8,6 / 5,3 s)
    TARGET = dict(BASE)
    SLOW = {k: 1.0 for k in KEYS}
elif VAR == "V6":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 4.75, 2: 9.1, 3: 5.0, 4: 5.1}
    TARGET = dict(BASE)  # Szenenzeiten in Sekunden, abgestimmt auf die Sprachclips (4,55 / 8,9 / 4,4 / 3,7 s)
    SLOW = {k: 1.0 for k in KEYS}
elif VAR == "V7":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 2.4, 2: 4.0, 3: 7.9, 4: 5.1}
    TARGET = {1: 4.1, 2: 5.6, 3: 7.6, 4: 5.1}  # nach Messung der Sprechzeiten (Clips 3,9 / 5,2 / 7,0 / 3,7 s)
    SLOW = {k: TARGET[k] / BASE[k] for k in KEYS}
else:
    KEYS = (1, 2, 3, 4, 5)
    BASE = {1: 2.6, 2: 3.2, 3: 7.9, 4: 2.8, 5: 3.4}
    SLOW = {1: 1.1, 2: 1.45, 3: 0.8, 4: 0.95, 5: 1.05}
LAST = max(KEYS)
START = {}
_t = 0.0
for _k in KEYS:
    START[_k] = _t
    _t += BASE[_k] * SLOW[_k]
DUR = round(_t, 2)
NF = int(round(DUR * FPS))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FRAMES = os.environ.get("AD_FRAMES", "/tmp/sellcheck_ad_frames")

INK = (14, 17, 22)
INK2 = (27, 32, 40)
LIME = (200, 241, 105)
PAPER = (246, 244, 238)
WHITE = (255, 255, 255)
MUTED = (154, 161, 173)
DARKMUTED = (96, 103, 115)
RED = (232, 78, 62)
AMBER = (242, 178, 44)
GREEN = (52, 196, 116)
DEEPGREEN = (23, 112, 63)
TRACK = (226, 223, 212)
DOT = {"Vinted": (9, 177, 186), "Kleinanzeigen": (134, 184, 23), "eBay": (54, 101, 243), "Etsy": (241, 100, 30)}

FONT = "/System/Library/Fonts/Avenir Next.ttc"
WEIGHT = {"bold": 0, "demi": 2, "medium": 5, "regular": 7, "heavy": 8}

# Szenen (Sekunden)
T_S1, T_S2, T_S3, T_S4, T_S5 = (START.get(k, 0.0) for k in (1, 2, 3, 4, 5))
S3_B = 5.4  # Beat b (Report) beginnt in Basiszeit 5,4 s nach Szenenstart (Szene 3)
CAP2_T = 1.5  # Basiszeit, ab der in der Demo die zweite Überschrift steht
FRIST_T = (2.1, 2.6, 3.1, 3.2)  # Einblendzeiten (Basiszeit) in der Fristszene: Zeile 1, Zeile 2, Hinweis 1, Hinweis 2
if VAR == "V3":
    S3_B, CAP2_T, FRIST_T = 5.95, 2.95, (1.95, 2.6, 1.3, 1.4)  # Schwellen beim Sprechen von "ab dreißig" / "zweitausend", Hinweis schon bei "melden dich"
P7_T = (0.5, 2.07, 0.79, 1.07, 2.71, 3.04)  # Reseller-Gewinnszene (Basiszeit): Überschrift 1, Überschrift 2, Karte, Verkauf, Einkauf, Gewinn
if VAR == "V7":
    S3_B, CAP2_T = 5.5, 1.55
CTA_T = (0.75, 1.4) if VAR in ("V8", "V9") else (0.75, 2.6)
V8_T = {"s1_end": 9.0, "hl": 5.7, "tap_up": 2.0, "guide_scroll": 2.8, "tap_guide": 4.8,
        "r_scroll1": 0.4, "tap_gelb": 3.4, "r_scroll2": 4.4, "tap_rot": 6.9, "hl_gewinn": 8.9,
        "rep_hl1": 1.6, "rep_scroll": 3.5, "rep_hl2": 4.9}  # V8 (UGC-Stil): Ereigniszeiten je Szene
if VAR == "V8":
    S3_B, CAP2_T = 5.7, 0.0  # Claim erscheint, "Für mehr Infos" und Klick-Hinweis (Sekunden ab Szenenstart)
DEMO_SHIFT = 1.4 if VAR == "V3" else (-1.4 if VAR == "V8" else 0.0)  # Karte/Ampel erst, wenn "und siehst pro Plattform" gesprochen wird


def at(scene, base_t):
    """Absolute Zeit eines Ereignisses, das in der Szene bei Basiszeit base_t passiert."""
    return START[scene] + base_t * SLOW[scene]


# ------------------------------------------------------------------ Helfer
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def prog(t, start, dur):
    return clamp((t - start) / dur)


def px(v):
    return int(round(v * S))


@lru_cache(maxsize=256)
def font(size, weight):
    return ImageFont.truetype(FONT, max(4, int(round(size * S))), index=WEIGHT[weight])


class Layer:
    def __init__(self):
        self.im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.dx = 0
        self.dy = 0

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, width=0):
        self.d.rounded_rectangle([px(x0), px(y0), px(x1), px(y1)], radius=px(r), fill=fill,
                                 outline=outline, width=px(width) if width else 0)

    def circle(self, cx, cy, r, fill):
        self.d.ellipse([px(cx - r), px(cy - r), px(cx + r), px(cy + r)], fill=fill)

    def text(self, x, y, s, size, weight, fill, anchor="la"):
        self.d.text((px(x), px(y)), s, font=font(size, weight), fill=fill, anchor=anchor)

    def width(self, s, size, weight):
        return self.d.textlength(s, font=font(size, weight)) / S

    def poly(self, pts, fill):
        self.d.polygon([(px(a_), px(b_)) for a_, b_ in pts], fill=fill)

    def line(self, pts, fill, width):
        self.d.line([(px(x), px(y)) for x, y in pts], fill=fill, width=px(width), joint="curve")


def col(c, a=255):
    return (c[0], c[1], c[2], int(a))


def pop_text(L, cx, cy, s, size, weight, color, t, start, anchor="mm", dur=0.35):
    """Text, der mit leichtem Überschwingen einpoppt."""
    p = prog(t, start, dur)
    if p <= 0:
        return
    sc = 0.7 + 0.3 * ease_back(p)
    L.text(cx, cy, s, size * sc, weight, col(color, 255 * clamp(p * 3)), anchor)


def pop_segments(L, cx, base_y, segs, t, start, dur=0.35):
    """Eine Zeile aus mehreren Farben/Größen, mittig, gemeinsame Grundlinie."""
    p = prog(t, start, dur)
    if p <= 0:
        return
    sc = 0.75 + 0.25 * ease_back(p)
    a = 255 * clamp(p * 3)
    widths = [L.width(s, size * sc, w) for s, size, w, _ in segs]
    x = cx - sum(widths) / 2
    for (s, size, w, c), wd in zip(segs, widths):
        L.text(x, base_y, s, size * sc, w, col(c, a), "ls")
        x += wd


def brand(L, t):
    """Marke von Sekunde 0 an (echtes Logo, klein), mittig oben in der Safe Zone."""
    h = 66
    w, _ = LOGO.lockup_size(h * S)
    LOGO.draw_lockup(L.d, 540 * S - w / 2, (250 - h / 2) * S, h * S, on_dark=True)


def pill(L, cx, cy, w, h, fill, outline=None):
    L.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, h / 2, fill=fill, outline=outline, width=3 if outline else 0)


def check_circle(L, cx, cy, r, bg=LIME, fg=INK):
    L.circle(cx, cy, r, col(bg))
    L.line([(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.34), (cx + r * 0.46, cy - r * 0.3)], col(fg), max(5, r * 0.22))


# ------------------------------------------------------------------ Szenen
def platform_list(L, t, y0, start, step=0.2, pitch=122):
    """Vier Plattformen untereinander, jede mit '?' (Zähler unbekannt)."""
    for i, n in enumerate(["Vinted", "Kleinanzeigen", "eBay", "Etsy"]):
        p = prog(t, start + i * step, 0.3)
        if p <= 0:
            continue
        cx, cy = 540, y0 + i * pitch
        sc = 0.85 + 0.15 * ease_back(p)
        a = 255 * clamp(p * 3)
        pill(L, cx, cy, 700 * sc, 104 * sc, col(INK2, a), col((60, 68, 80), a))
        L.circle(cx - 280 * sc, cy, 18, col(DOT[n], a))
        L.text(cx - 235 * sc, cy, n, 46 * sc, "bold", col(PAPER, a), "lm")
        L.text(cx + 300 * sc, cy, "?", 58 * sc, "heavy", col(LIME, a), "mm")


def scene_hook_a(L, t):
    # Zeilen (Fakt), danach tickender Zähler 27 -> 30
    pop_text(L, 540, 520, "Vinted meldet", 118, "heavy", PAPER, t, 0.00)
    pop_text(L, 540, 650, "dich ab", 118, "heavy", PAPER, t, 0.14)
    pop_segments(L, 540, 860, [("30", 190, "heavy", LIME), (" Verkäufen.", 100, "heavy", PAPER)], t, 0.28, 0.4)
    # Zähler
    p = prog(t, 0.45, 0.4)
    if p > 0:
        top = 1010 + (1 - ease_out(p)) * 60
        L.rrect(190, top, 890, top + 400, 44, fill=col(INK2, 255 * clamp(p * 2)), outline=col(RED if t >= 1.6 else (60, 68, 80)), width=4)
        L.text(540, top + 62, "Deine Verkäufe 2026", 40, "medium", col(MUTED), "mm")
        n = 27 + int(t >= 0.9) + int(t >= 1.25) + int(t >= 1.6)
        n = min(n, 30)
        hit = t >= 1.6
        shake = math.sin((t - 1.6) * 70) * 8 * clamp(1 - (t - 1.6) / 0.5) if hit else 0
        L.text(540 + shake, top + 205, str(n), 200, "heavy", col(RED if hit else PAPER), "mm")
        if hit:
            pp = prog(t, 1.65, 0.3)
            pill(L, 540, top + 340, 560 * (0.8 + 0.2 * ease_back(pp)), 66, col(RED, 255 * clamp(pp * 3)))
            L.text(540, top + 340, "MELDEGRENZE ERREICHT", 32, "heavy", col(WHITE, 255 * clamp(pp * 3)), "mm")


def scene_hook_b(L, t):
    pop_text(L, 540, 470, "POV:", 130, "heavy", LIME, t, 0.00)
    pop_text(L, 540, 620, "Du verkaufst auf", 92, "heavy", PAPER, t, 0.12)
    pop_text(L, 540, 730, "4 Plattformen", 118, "heavy", PAPER, t, 0.24)
    pop_text(L, 540, 880, "und hast keine Ahnung,", 70, "heavy", PAPER, t, 0.5)
    pop_text(L, 540, 965, "wo du stehst.", 70, "heavy", LIME, t, 0.62)
    platform_list(L, t, 1120, 0.9, 0.22, 118)


def scene_problem_a(L, t):
    pop_text(L, 540, 470, "Aber du verkaufst", 92, "heavy", PAPER, t, 0.00)
    pop_text(L, 540, 580, "nicht nur dort.", 92, "heavy", PAPER, t, 0.14)
    platform_list(L, t, 760, 0.55, 0.2, 122)
    pop_text(L, 540, 1290, "Jede zählt einzeln.", 76, "heavy", LIME, t, 1.55)
    pop_text(L, 540, 1385, "Weißt du, wo du stehst?", 50, "medium", PAPER, t, 2.05)


def scene_problem_b(L, t):
    pop_text(L, 540, 480, "Ab 30 Verkäufen", 100, "heavy", PAPER, t, 0.00)
    pop_text(L, 540, 600, "oder 2.000 € im Jahr", 74, "heavy", LIME, t, 0.18)
    pop_text(L, 540, 760, "meldet dich die Plattform", 60, "heavy", PAPER, t, 0.7)
    pop_text(L, 540, 840, "an die Steuerbehörde.", 60, "heavy", PAPER, t, 0.8)
    pop_text(L, 540, 1010, "Jede Plattform zählt einzeln.", 56, "heavy", LIME, t, 1.5)
    p = prog(t, 2.0, 0.35)
    if p > 0:
        a = 255 * clamp(p * 3)
        L.rrect(110, 1110, 830 + 110 - 0, 1260, 30, fill=col(INK2, a), outline=col((60, 68, 80), a), width=3)
        L.text(540, 1160, "Meldung heißt nicht automatisch:", 40, "medium", col(PAPER, a), "mm")
        L.text(540, 1214, "Steuern zahlen.", 46, "heavy", col(LIME, a), "mm")


ROWS = [("Vinted", 27, 30, "27 / 30 Verkäufe", False), ("Kleinanzeigen", 12, 30, "12 / 30 Verkäufe", False),
        ("eBay", 1850, 2000, "1.850 / 2.000 €", True), ("Etsy", 31, 30, "31 / 30 Verkäufe", False)]


def money(v):
    return f"{v:,.0f}".replace(",", ".")


def scene_demo(L, t):
    # Titelzeile je nach Beat (Basiszeit)
    caps = ("Datei rein.", "Grenzen im Blick.", "Das bleibt dir.") if V2LIKE else ("Datei rein.", "Ampel an.", "Report raus.")
    sz = [88] * 3 if V2LIKE else [100 if len(c) <= 12 else 80 for c in caps]
    if VAR == "V8":
        pass
    elif t < CAP2_T:
        pop_text(L, 540, 400, caps[0], sz[0], "heavy", PAPER, t, 0.0)
    elif t < S3_B:
        pop_text(L, 540, 400, caps[1], sz[1], "heavy", LIME, t, CAP2_T)
    else:
        pop_text(L, 540, 400, caps[2], sz[2], "heavy", PAPER, t, S3_B)

    if VAR == "V7" and CAP2_T <= t < S3_B - 0.05:
        # Zahlen stehen nur im Bild, gesprochen wird die Grenze ohne Zahlen
        pop_text(L, 540, 1488, "Meldung ab 30 Verkäufen", 40, "heavy", PAPER, t, CAP2_T + 0.2)
        pop_text(L, 540, 1542, "oder 2.000 € je Plattform", 40, "heavy", LIME, t, CAP2_T + 0.35)

    # Beat a1: Ablagefläche, Datei landet darin (nichts überlagert anderen Inhalt)
    zone_a = 1.0 - ease_out(prog(t, 1.45 + DEMO_SHIFT, 0.25))
    if VAR == "V8":
        zone_a = 0.0
    if zone_a > 0:
        a = 255 * zone_a
        landed = t >= 0.85
        s_ = 45 if V2LIKE else 0  # Ablagefläche höher, Inhalt mittig darin
        z0, z1 = 130, 950
        L.rrect(z0, 520, z1, 1080 + 2 * s_, 44, fill=col(INK2, a), outline=col(LIME if landed else (74, 82, 94), a), width=4)
        # Pfeil nach oben und Hinweis
        L.line([(540, 640 + s_), (540, 590 + s_)], col(MUTED, a), 8)
        L.line([(516, 612 + s_), (540, 588 + s_), (564, 612 + s_)], col(MUTED, a), 8)
        L.text(540, 700 + s_, "CSV hier ablegen", 40, "medium", col(MUTED, a), "mm")
        fp = prog(t, 0.1, 0.7)
        if fp > 0:
            fy = 380 + ease_out(fp) * (860 + 3 * s_ // 2 - 380)
            sc = 1.0 + (0.06 * math.sin(clamp((t - 0.8) / 0.25) * math.pi) if t >= 0.8 else 0.0)
            pill(L, 540, fy, 640 * sc, 104 * sc, col(PAPER, a))
            # kleines Dokument-Symbol
            L.rrect(540 - 290 * sc, fy - 26 * sc, 540 - 252 * sc, fy + 26 * sc, 6, fill=col(INK, a))
            L.text(540 - 230 * sc, fy, "eBay_Transaktionen.csv", 34 * sc, "bold", col(INK, a), "lm")
        if landed:
            lp = prog(t, 0.9, 0.3)
            check_circle(L, 540 - 130, 990 + 2 * s_, 24 * (0.6 + 0.4 * ease_back(lp)))
            L.text(540 - 90, 990 + 2 * s_, "Datei gelesen", 40, "heavy", col(PAPER, a * clamp(lp * 3)), "lm")

    # Beat a2: Karte mit Ampel
    slide_out = ease_out(prog(t, S3_B - 0.05, 0.45))
    card_p = ease_out(prog(t, 1.55 + DEMO_SHIFT, 0.55))
    if slide_out < 1.0 and card_p > 0:
        ox = -1100 * slide_out
        oy = (1 - card_p) * 700
        x0, y0, x1, y1 = 130 + ox, 500 + oy, 950 + ox, 1420 + oy
        red_t = 4.15 + DEMO_SHIFT
        flash = t >= red_t and t < red_t + 0.8 and (t % 0.5) < 0.3
        L.rrect(x0, y0, x1, y1, 44, fill=col(PAPER), outline=col(RED) if flash else None, width=6)
        L.text(x0 + 50, y0 + 62, "Meldegrenzen 2026", 46, "heavy", col(INK), "lm")
        pill(L, x1 - 130, y0 + 62, 190, 50, col(LIME))
        L.text(x1 - 130, y0 + 62, "Übersicht" if V2LIKE else "Ampel", 28, "heavy", col(INK), "mm")
        L.text(x1 - 50, y1 - 34, "Beispieldaten", 24, "medium", col(DARKMUTED), "rm")
        for i, (name, v, lim, label, money_mode) in enumerate(ROWS):
            st = 2.0 + DEMO_SHIFT + i * 0.28
            rp = prog(t, st, 0.35)
            if rp <= 0:
                continue
            ry = y0 + 150 + i * 182 + (1 - ease_out(rp)) * 30
            k = clamp(rp * 3)

            def fc(c, k=k):  # auf dem Karton überblenden statt Transparenz (sonst entsteht ein Loch)
                return tuple(int(PAPER[j] + (c[j] - PAPER[j]) * k) for j in range(3)) + (255,)
            L.circle(x0 + 62, ry + 20, 14, fc(DOT[name]))
            L.text(x0 + 90, ry + 20, name, 42, "bold", fc(INK), "lm")
            fillp = ease_out(prog(t, st + 0.15, 0.8))
            val = v * fillp
            vt = f"{money(val)} / {money(lim)} €" if money_mode else f"{int(round(val))} / {lim} Verkäufe"
            L.text(x1 - 50, ry + 20, vt, 36, "medium", fc(DARKMUTED), "rm")
            bx0, bx1, by = x0 + 50, x1 - 50, ry + 62
            L.rrect(bx0, by, bx1, by + 30, 15, fill=fc(TRACK))
            ratio = min(1.0, v / lim) * fillp
            if ratio > 0.01:
                final = min(1.0, v / lim)
                colr = RED if final >= 1 else (AMBER if final >= 0.8 else GREEN)
                L.rrect(bx0, by, bx0 + (bx1 - bx0) * ratio, by + 30, 15, fill=fc(colr))
            if fillp > 0.95:
                final = min(1.0, v / lim)
                if final >= 1:
                    txt, c2 = "Meldegrenze erreicht", RED
                elif final >= 0.8:
                    txt, c2 = "Fast erreicht", (176, 112, 0)
                else:
                    txt, c2 = "Alles im grünen Bereich", DEEPGREEN
                L.text(bx0, by + 64, txt, 31, "bold", fc(c2), "lm")

    # Beat b: Report-Blatt
    sp = ease_out(prog(t, S3_B + 0.1, 0.6))
    if sp > 0:
        ox = (1 - sp) * 1100
        x0, y0, x1, y1 = 170 + ox, 500, 910 + ox, 1420
        L.rrect(x0, y0, x1, y1, 30, fill=col(PAPER))
        L.text(x0 + 46, y0 + 70, "Steuer-Report 2026", 46, "heavy", col(INK), "lm")
        L.text(x0 + 46, y0 + 128, "Ausfüllhilfe Anlage EÜR", 32, "medium", col(DARKMUTED), "lm")
        pill(L, x1 - 46 - 125, y0 + 128, 250, 50, col(LIME))
        L.text(x1 - 46 - 125, y0 + 128, "Als PDF" if V2LIKE else "Druckfertig", 28, "heavy", col(INK), "mm")
        L.text(x1 - 46, y1 - 34, "Beispieldaten", 24, "medium", col(DARKMUTED), "rm")
        rnd = random.Random(7)
        for i in range(6):
            yy = y0 + 220 + i * 66
            L.rrect(x0 + 46, yy, x0 + 46 + 250 + rnd.randint(0, 150), yy + 22, 11, fill=col(TRACK))
            L.rrect(x1 - 46 - 110, yy, x1 - 46, yy + 22, 11, fill=col(TRACK))
        gp = prog(t, S3_B + 0.7, 0.9)
        L.rrect(x0 + 40, y0 + 640, x1 - 40, y0 + 810, 26, fill=col((228, 246, 214)))
        L.text(x0 + 76, y0 + 696, "Gewinn nach Einkauf", 32, "medium", col(DEEPGREEN), "lm")
        L.text(x0 + 76, y0 + 764, f"{842.5 * ease_out(gp):,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."), 64, "heavy", col(DEEPGREEN), "lm")


    if VAR == "V8":
        draw_tap(L, t, V8_T["tap_vinted"], 800, 705)
        draw_tap(L, t, V8_T["tap_gewinn"], 540, 1225)


def scene_benefits(L, t):
    pop_text(L, 540, 430, "Dein Überblick:", 76, "heavy", PAPER, t, 0.0)
    items = ["Alle Plattformen", "Meldegrenzen als Ampel", "Steuer-Report zum Drucken"]
    for i, it in enumerate(items):
        p = prog(t, 0.35 + i * 0.4, 0.35)
        if p <= 0:
            continue
        cy = 650 + i * 190
        sc = 0.85 + 0.15 * ease_back(p)
        a = 255 * clamp(p * 3)
        L.rrect(100, cy - 74, 940, cy + 74, 40, fill=col(INK2, a), outline=col((60, 68, 80), a), width=3)
        check_circle(L, 100 + 78, cy, 40 * sc)
        L.text(100 + 150, cy, it, 44 * sc, "heavy", col(PAPER, a), "lm")
    pop_text(L, 540, 1290, "Läuft im Browser.", 50, "medium", MUTED, t, 1.7)
    pop_text(L, 540, 1352, "Deine Daten bleiben bei dir.", 50, "medium", MUTED, t, 1.8)


def scene_cta_v2like(L, t):
    """Endkarte der neueren Ads: Logo, Claim, Hinweis 'Hier unten klicken' mit Pfeil über der TikTok-Klickfläche."""
    p = prog(t, 0.0, 0.45)
    sc = 0.75 + 0.25 * ease_back(p)
    h = 145 * sc
    w, _ = LOGO.lockup_size(h * S)
    tmp = Image.new("RGBA", L.im.size, (0, 0, 0, 0))
    LOGO.draw_lockup(ImageDraw.Draw(tmp), 540 * S - w / 2, (600 - h / 2) * S, h * S, on_dark=True)
    tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * clamp(p * 3))))
    L.im.alpha_composite(tmp)
    if VAR in ("V8", "V9"):
        pop_text(L, 540, 760, "Check, was", 92, "heavy", PAPER, t, CTA_T[0])
        pop_text(L, 540, 860, "wirklich bleibt.", 92, "heavy", LIME, t, CTA_T[0] + 0.12)
        for k, label in enumerate(("Kostenlos mit Konto", "Daten bleiben im Browser", "Übersicht für die Steuererklärung")):
            pp0 = prog(t, CTA_T[1] + k * 0.35, 0.3)
            if pp0 <= 0:
                continue
            a0 = 255 * clamp(pp0 * 3)
            cy0 = 985 + k * 92
            pill(L, 540, cy0, 800 * (0.9 + 0.1 * ease_back(pp0)), 76, col(INK2, a0), col((60, 68, 80), a0))
            check_circle(L, 540 - 340, cy0, 22, bg=LIME, fg=INK)
            L.text(540 - 296, cy0 + 1, label, 40, "bold", col(PAPER, a0), "lm")
        pop_text(L, 540, 1285, "Unabhängig von den genannten Plattformen.", 26, "medium", MUTED, t, CTA_T[1] + 1.2, dur=0.3)
        pop_text(L, 540, 1322, "Orientierung, keine Steuer- oder Rechtsberatung.", 26, "medium", MUTED, t, CTA_T[1] + 1.3, dur=0.3)
        pp = prog(t, CTA_T[1] + 1.6, 0.4)
        if pp > 0:
            a = 255 * clamp(pp * 3)
            bob = 14 * math.sin(max(0, t - CTA_T[1] - 2.0) * 7)
            pill_w = L.width("Hier unten klicken", 62, "heavy") + 130
            pill(L, 540, 1405, pill_w * (0.85 + 0.15 * ease_back(pp)), 118, col(LIME, a))
            L.text(540, 1408, "Hier unten klicken", 62, "heavy", col(INK, a), "mm")
            ax, ay = 540, 1520 + bob
            L.line([(ax, ay - 36), (ax, ay + 20)], col(LIME, a), 12)
            L.line([(ax - 28, ay - 4), (ax, ay + 28), (ax + 28, ay - 4)], col(LIME, a), 12)
        return
    pop_text(L, 540, 840, "Check, was", 108, "heavy", PAPER, t, CTA_T[0])
    pop_text(L, 540, 965, "wirklich bleibt.", 108, "heavy", LIME, t, CTA_T[0] + 0.12)
    pop_text(L, 540, 1090, "Für mehr Infos", 52, "medium", MUTED, t, CTA_T[1])
    pop_text(L, 540, 1215, "Unabhängig von den genannten Plattformen.", 28, "medium", MUTED, t, CTA_T[1] + 0.2, dur=0.3)
    pop_text(L, 540, 1255, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "medium", MUTED, t, CTA_T[1] + 0.3, dur=0.3)
    # Hinweis direkt über der Klickfläche von TikTok (unten), Pfeil wippt nach unten
    pp = prog(t, CTA_T[1] + 0.5, 0.4)
    if pp > 0:
        a = 255 * clamp(pp * 3)
        bob = 14 * math.sin(max(0, t - CTA_T[1] - 0.9) * 7)
        pill_w = L.width("Hier unten klicken", 62, "heavy") + 130
        pill(L, 540, 1385, pill_w * (0.85 + 0.15 * ease_back(pp)), 118, col(LIME, a))
        L.text(540, 1388, "Hier unten klicken", 62, "heavy", col(INK, a), "mm")
        ax, ay = 540, 1500 + bob
        L.line([(ax, ay - 40), (ax, ay + 24)], col(LIME, a), 12)
        L.line([(ax - 30, ay), (ax, ay + 32), (ax + 30, ay)], col(LIME, a), 12)


def scene_cta(L, t):
    if V2LIKE:
        return scene_cta_v2like(L, t)
    p = prog(t, 0.0, 0.5)
    sc = 0.75 + 0.25 * ease_back(p)
    h = (145 if V2LIKE else 170) * sc
    w, _ = LOGO.lockup_size(h * S)
    # Logo wird mit Alpha eingeblendet: auf eigener Ebene zeichnen und zusammenführen
    tmp = Image.new("RGBA", L.im.size, (0, 0, 0, 0))
    LOGO.draw_lockup(ImageDraw.Draw(tmp), 540 * S - w / 2, (640 - h / 2) * S, h * S, on_dark=True)
    a = tmp.getchannel("A").point(lambda v: int(v * clamp(p * 3)))
    tmp.putalpha(a)
    L.im.alpha_composite(tmp)
    if V2LIKE:
        pop_text(L, 540, 850, "Jetzt gratis", 100, "heavy", PAPER, t, 0.45)
        pop_text(L, 540, 965, "testen.", 100, "heavy", LIME, t, 0.6)
        label, pw, ax_off, ly = "Einfach unten antippen", 740, 300, 1150
    else:
        pop_text(L, 540, 860, "Gratis testen.", 100, "heavy", PAPER, t, 0.5)
        label, pw, ax_off, ly = "Link unten antippen", 640, 255, 1060
    pp = prog(t, 1.0, 0.4)
    if pp > 0:
        pulse = 1 + 0.03 * math.sin(max(0, t - 1.4) * 9)
        pill(L, 540, ly, pw * pulse * (0.85 + 0.15 * ease_back(pp)), 120 * pulse, col(LIME, 255 * clamp(pp * 3)))
        L.text(540 - 30, ly, label, 46, "heavy", col(INK, 255 * clamp(pp * 3)), "mm")
        ax, ay = 540 + ax_off, ly
        L.line([(ax, ay - 14), (ax, ay + 16)], col(INK, 255 * clamp(pp * 3)), 8)
        L.line([(ax - 14, ay + 3), (ax, ay + 18), (ax + 14, ay + 3)], col(INK, 255 * clamp(pp * 3)), 8)
    if V2LIKE:
        pop_text(L, 540, 1275, "Check, was wirklich bleibt.", 44, "heavy", LIME, t, 1.5, dur=0.35)
    if VAR in ("V3", "V6", "V7"):
        pop_text(L, 540, 1355, "Unabhängig von den genannten Plattformen.", 28, "medium", MUTED, t, 1.6, dur=0.3)
        pop_text(L, 540, 1395, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "medium", MUTED, t, 1.7, dur=0.3)
    else:
        pop_text(L, 540, 1355 if V2LIKE else 1250, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "medium", MUTED, t, 1.6, dur=0.3)


def scene_v3_hook(L, t):
    """Du verkaufst viel auf Vinted und Co? mit hochlaufendem Zähler (Beispieldaten)."""
    pop_text(L, 540, 480, "Du verkaufst", 100, "heavy", PAPER, t, 0.0)
    pop_text(L, 540, 600, "viel auf Vinted", 100, "heavy", LIME, t, 0.14)
    pop_text(L, 540, 720, "und Co?", 100, "heavy", PAPER, t, 0.28)
    p = prog(t, 0.6, 0.4)
    if p > 0:
        top = 930 + (1 - ease_out(p)) * 60
        a = 255 * clamp(p * 2)
        L.rrect(190, top, 890, top + 400, 44, fill=col(INK2, a), outline=col((60, 68, 80), a), width=4)
        L.text(540, top + 62, "Deine Verkäufe 2026", 40, "medium", col(MUTED, a), "mm")
        n = int(12 + 35 * ease_out(prog(t, 0.9, 1.3)))
        L.text(540, top + 205, str(n), 200, "heavy", col(PAPER, a), "mm")
        L.text(540, top + 345, "Beispieldaten", 26, "medium", col(MUTED, a), "mm")


def scene_v7_hook(L, t):
    """Du bist Reseller, oder willst wissen, was du wirklich verdienst?"""
    pop_text(L, 540, 450, "Du bist", 88, "heavy", PAPER, t, 0.0)
    pop_text(L, 540, 580, "Reseller,", 130, "heavy", LIME, t, 0.29)
    pop_text(L, 540, 720, "oder willst wissen,", 70, "heavy", PAPER, t, 0.82)
    pop_segments(L, 540, 835, [("was du ", 66, "heavy", PAPER), ("wirklich", 66, "heavy", LIME), (" verdienst?", 66, "heavy", PAPER)], t, 1.43, 0.4)
    platform_list(L, t, 1040, 1.55, 0.1, 112)


def scene_v7_profit(L, t):
    """Nicht der Umsatz zählt, sondern was nach dem Einkauf bleibt (Beispielartikel)."""
    pop_text(L, 540, 420, "Nicht dein Umsatz.", 78, "heavy", PAPER, t, P7_T[0])
    pop_text(L, 540, 530, "Dein Gewinn zählt.", 78, "heavy", LIME, t, P7_T[1])
    cp = ease_out(prog(t, P7_T[2], 0.55))
    if cp <= 0:
        return
    x0, y0, x1, y1 = 110, 650 + (1 - cp) * 600, 970, 1340 + (1 - cp) * 600
    L.rrect(x0, y0, x1, y1, 40, fill=col(PAPER))
    L.text(x0 + 50, y0 + 62, "Sneaker, Gr. 42", 44, "heavy", col(INK), "lm")
    pill(L, x1 - 140, y0 + 62, 200, 50, col(LIME))
    L.text(x1 - 140, y0 + 62, "Artikel", 28, "heavy", col(INK), "mm")
    L.text(x1 - 50, y1 - 34, "Beispieldaten", 24, "medium", col(DARKMUTED), "rm")

    def fc(c, k):  # auf dem Karton überblenden statt Transparenz
        return tuple(int(PAPER[j] + (c[j] - PAPER[j]) * k) for j in range(3)) + (255,)

    def eur(v):
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    k1 = clamp(prog(t, P7_T[3], 0.3) * 3)
    k2 = clamp(prog(t, P7_T[4], 0.3) * 3)
    if k1 > 0:
        L.text(x0 + 50, y0 + 170, "Verkauf", 42, "medium", fc(DARKMUTED, k1), "lm")
        L.text(x1 - 50, y0 + 170, eur(38) + " €", 48, "bold", fc(INK, k1), "rm")
    if k2 > 0:
        L.text(x0 + 50, y0 + 270, "Einkauf", 42, "medium", fc(DARKMUTED, k2), "lm")
        L.text(x1 - 50, y0 + 270, "– " + eur(12) + " €", 48, "bold", fc(RED, k2), "rm")
        L.line([(x0 + 50, y0 + 345), (x1 - 50, y0 + 345)], col(TRACK), 4)
    gp = prog(t, P7_T[5], 0.7)
    if gp > 0:
        L.rrect(x0 + 40, y0 + 390, x1 - 40, y0 + 600, 28, fill=col((228, 246, 214)))
        L.text(x0 + 76, y0 + 450, "Gewinn nach Einkauf", 34, "medium", col(DEEPGREEN), "lm")
        L.text(x0 + 76, y0 + 535, eur(26 * ease_out(gp)) + " €", 84, "heavy", col(DEEPGREEN), "lm")


def scene_v2_hook(L, t):
    """Frage als Einstieg: Hast du noch den Überblick über all deine Verkäufe?"""
    pop_text(L, 540, 470, "Hast du noch den", 88, "heavy", PAPER, t, 0.0)
    pop_text(L, 540, 580, "Überblick über", 88, "heavy", PAPER, t, 0.12)
    pop_text(L, 540, 690, "all deine", 88, "heavy", PAPER, t, 0.24)
    pop_text(L, 540, 820, "Verkäufe?", 124, "heavy", LIME, t, 0.36)
    platform_list(L, t, 1010, 1.0, 0.18, 112)


def scene_v2_deadline(L, t):
    """Ende Januar melden Plattformen das Vorjahr; Schwellen 30 Verkäufe oder 2.000 €."""
    p = prog(t, 0.0, 0.5)
    if p > 0:
        sc = 0.8 + 0.2 * ease_back(p)
        a = 255 * clamp(p * 3)
        cx, cy, w0, h0 = 540, 730, 560, 520
        w, h = w0 * sc, h0 * sc
        top = cy - h / 2
        L.rrect(cx - w / 2, top, cx + w / 2, cy + h / 2, 44 * sc, fill=col(PAPER, a))
        L.rrect(cx - w / 2, top, cx + w / 2, top + 140 * sc, 44 * sc, fill=col(LIME, a))
        L.rrect(cx - w / 2, top + 90 * sc, cx + w / 2, top + 140 * sc, 0, fill=col(LIME, a))
        L.text(cx, top + 70 * sc, "JANUAR 2027", 52 * sc, "heavy", col(INK, a), "mm")
        L.text(cx, cy + 20 * sc, "31", 290 * sc, "heavy", col(INK, a), "mm")
        L.text(cx, cy + h / 2 - 52 * sc, "Meldung deines Jahres 2026", 32 * sc, "medium", col(DARKMUTED, a), "mm")
    pop_text(L, 540, 1075, "ab 30 Verkäufen", 70, "heavy", LIME, t, FRIST_T[0])
    pop_text(L, 540, 1160, "oder 2.000 € je Plattform", 50, "heavy", PAPER, t, FRIST_T[1])
    pop_text(L, 540, 1290, "Meldung heißt nicht automatisch:", 34, "medium", MUTED, t, FRIST_T[2])
    pop_text(L, 540, 1342, "Steuern zahlen.", 42, "heavy", PAPER, t, FRIST_T[3])


# ---- V6 "Drei Fragen" (dunkles Design wie V2/V3/V7)
V6_TOPS_Q = (400, 730, 1060)
V6_TOPS_A = (520, 830, 1140)
V6_QSTART = (0.1, 2.9, 6.1)
V6_FLIP = (2.7, 3.25, 3.8)
V6_QUESTIONS = (("Wie viele Verkäufe", "hattest du dieses Jahr?"),
                ("Wie viel Umsatz davon", "auf welcher Plattform?"),
                ("Und was davon ist", "wirklich Gewinn?"))
V6_CHIPS = (("Vinted", (9, 177, 186), 335, 1020), ("eBay", (54, 101, 243), 715, 1020), ("Kleinanzeigen", (134, 184, 23), 540, 1160))


def v6_mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def v6_question_face(L, i, x0, y0, x1, y1, k_active):
    """Frage-Karte: Nummer links, Text mittig, Fragezeichen rechts (spiegelbildlich, gleiche Ränder).
    k_active 1 = Karte aktiv (Lime), 0 = ruhig (dunkel)."""
    cy = (y0 + y1) / 2
    r = 38
    cxl, cxr = x0 + 70, x1 - 70
    tile = v6_mix(INK2, LIME, k_active)
    fg = v6_mix(PAPER, INK, k_active)
    acc = v6_mix(LIME, INK, k_active)
    L.circle(cxl, cy, r, col(acc))
    L.text(cxl, cy + 1, str(i + 1), 50, "heavy", col(tile), "mm")
    L.circle(cxr, cy, r, col(acc))
    L.circle(cxr, cy, r - 6, col(tile))
    L.text(cxr, cy + 1, "?", 52, "heavy", col(acc), "mm")
    lines = V6_QUESTIONS[i]
    maxw = (cxr - r - 26) - (cxl + r + 26)
    size = 56
    while max(L.width(s, size, "heavy") for s in lines) > maxw and size > 30:
        size -= 1
    lh = size * 1.2
    for j, s in enumerate(lines):
        L.text(cxl + r + 26, cy + (j - 0.5) * lh, s, size, "heavy", col(fg), "lm")


def scene_v6_hook(L, t):
    base = 720
    p = prog(t, 0.0, 0.45)
    if p > 0:
        sc = 0.7 + 0.3 * ease_back(p)
        a = 255 * clamp(p * 3)
        w3 = L.width("3", 250 * sc, "heavy") + 26
        wf = L.width("Fragen", 190 * sc, "heavy")
        x = 540 - (w3 + wf) / 2
        L.text(x, base, "3", 250 * sc, "heavy", col(LIME, a), "ls")
        L.text(x + w3, base, "Fragen", 190 * sc, "heavy", col(PAPER, a), "ls")
    pop_text(L, 540, 860, "an alle, die auf", 62, "medium", MUTED, t, 0.95)
    for k, (name, dot, cx, cy) in enumerate(V6_CHIPS):
        p = prog(t, (2.3, 2.95, 3.5)[k], 0.3)
        if p <= 0:
            continue
        sc = 0.8 + 0.2 * ease_back(p)
        a = 255 * clamp(p * 3)
        w = (L.width(name, 54, "bold") + 124) * sc
        pill(L, cx, cy, w, 108 * sc, col(INK2, a), col((60, 68, 80), a))
        L.circle(cx - w / 2 + 50 * sc, cy, 17 * sc, col(dot, a))
        L.text(cx - w / 2 + 86 * sc, cy, name, 54 * sc, "bold", col(PAPER, a), "lm")
    pop_text(L, 540, 1320, "verkaufen.", 62, "medium", MUTED, t, 4.0)


def scene_v6_questions(L, t):
    for i in range(3):
        st = V6_QSTART[i]
        p = prog(t, st, 0.5)
        if p <= 0:
            continue
        top = V6_TOPS_Q[i]
        ox = (1 - ease_back(p)) * 900
        x0, x1 = 100 + ox, 980 + ox
        nxt = V6_QSTART[i + 1] if i < 2 else 99
        k = 1.0 - prog(t, nxt, 0.3) if i < 2 else 1.0
        fill = v6_mix(INK2, LIME, k)
        L.rrect(x0, top, x1, top + 290, 44, fill=col(fill), outline=col(v6_mix((60, 68, 80), LIME, k)), width=4)
        v6_question_face(L, i, x0, top, x1, top + 290, k)


def v6_answer_face(L, i, x0, y0, x1, y1, t, tstart):
    cy = (y0 + y1) / 2
    r = 38
    cxl = x0 + 70
    check_circle(L, cxl, cy, r, bg=GREEN, fg=WHITE)
    tx = cxl + r + 26
    k = ease_out(prog(t, tstart + 0.3, 0.55))
    if i == 0:
        L.text(tx, y0 + 70, "Verkäufe dieses Jahr", 36, "medium", col(DARKMUTED), "lm")
        num = str(int(round(47 * k)))
        L.text(tx, y0 + 232, num, 150, "heavy", col(INK), "ls")
        L.text(tx + L.width("47", 150, "heavy") + 24, y0 + 232, "Verkäufe", 46, "medium", col(DARKMUTED), "ls")
    elif i == 1:
        rows = [("Vinted", 27, 30, "27 / 30 Verkäufe", DOT["Vinted"]), ("eBay", 1850, 2000, "1.850 / 2.000 €", DOT["eBay"])]
        for r_, (name, v, lim, label, dot) in enumerate(rows):
            ry = y0 + 92 + r_ * 100
            L.circle(tx + 12, ry, 12, col(dot))
            L.text(tx + 36, ry, name, 38, "bold", col(INK), "lm")
            L.text(x1 - 40, ry, label, 32, "medium", col(DARKMUTED), "rm")
            bx0, bx1 = tx, x1 - 40
            L.rrect(bx0, ry + 30, bx1, ry + 48, 9, fill=col(TRACK))
            L.rrect(bx0, ry + 30, bx0 + (bx1 - bx0) * min(1, v / lim) * k, ry + 48, 9, fill=col(AMBER))
    else:
        L.text(tx, y0 + 70, "Gewinn nach Einkauf", 36, "medium", col(DARKMUTED), "lm")
        val = f"{842.5 * k:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        L.text(tx, y0 + 226, val + " €", 112, "heavy", col(DEEPGREEN), "ls")


def scene_v6_answers(L, t):
    if t < 2.25:
        pop_text(L, 540, 410, "Keine Ahnung?", 104, "heavy", PAPER, t, 0.0)
    else:
        wa = L.width("SellCheck ", 70, "heavy")
        wb = L.width("beantwortet", 70, "heavy")
        x0 = 540 - (wa + wb) / 2
        p = prog(t, 2.25, 0.35)
        sc = 0.75 + 0.25 * ease_back(p)
        a = 255 * clamp(p * 3)
        L.text(x0, 380, "SellCheck", 70 * sc, "heavy", col(LIME, a), "ls")
        L.text(x0 + wa, 380, "beantwortet", 70 * sc, "heavy", col(PAPER, a), "ls")
        pop_text(L, 540, 462, "alle drei.", 70, "heavy", PAPER, t, 2.4)
    for i in range(3):
        top = V6_TOPS_A[i]
        fp = prog(t, V6_FLIP[i], 0.4)
        sx = abs(math.cos(math.pi * fp)) if 0 < fp < 1 else 1.0
        ans = fp >= 0.5
        cx = 540
        hw = 440 * max(sx, 0.02)
        if ans:
            L.rrect(cx - hw, top, cx + hw, top + 290, 44, fill=col(PAPER))
        else:
            L.rrect(cx - hw, top, cx + hw, top + 290, 44, fill=col(INK2), outline=col((60, 68, 80)), width=4)
        if sx > 0.97:
            if ans:
                v6_answer_face(L, i, cx - hw, top, cx + hw, top + 290, t, V6_FLIP[i])
            else:
                v6_question_face(L, i, cx - hw, top, cx + hw, top + 290, 0.0)
    if t > V6_FLIP[2] + 0.5:
        pop_text(L, 540, 1490, "Beispieldaten", 26, "medium", MUTED, t, V6_FLIP[2] + 0.5, dur=0.25)


# ---- V8 "UGC-Stil": Bildschirmaufnahme mit Finger-Taps und Wort-für-Wort-Untertiteln
def draw_tap(L, t, start, x, y):
    p = prog(t, start, 0.6)
    if p <= 0 or p >= 1:
        return
    r = 28 + 56 * ease_out(p)
    a = int(220 * (1 - p))
    L.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], outline=(255, 255, 255, a), width=int(7 * S))
    pd = clamp(1 - prog(t, start, 0.3))
    L.circle(x, y, 30 * (0.6 + 0.4 * pd), col((255, 255, 255), 200 * pd))


def scene_v8_hook(L, t):
    """UGC-Hook: 'Stopp.' plus die drei Plattformen, passend zum Sprechertext."""
    p = prog(t, 0.0, 0.3)
    if p > 0:
        sc = 0.7 + 0.3 * ease_back(p)
        a = 255 * clamp(p * 3)
        w, h = 330 * sc, 120 * sc
        pill(L, 540, 620, w, h, col(RED, a))
        L.text(540, 622, "STOPP", 76 * sc, "heavy", col(WHITE, a), "mm")
    names = (("Vinted", DOT["Vinted"], 1.05), ("eBay", DOT["eBay"], 1.7), ("Kleinanzeigen", DOT["Kleinanzeigen"], 2.3))
    for k, (name, dot, st) in enumerate(names):
        pp = prog(t, st, 0.3)
        if pp <= 0:
            continue
        sc = 0.8 + 0.2 * ease_back(pp)
        a = 255 * clamp(pp * 3)
        cy = 860 + k * 135
        wd = 640 * sc
        pill(L, 540, cy, wd, 110 * sc, col(INK2, a), col((60, 68, 80), a))
        L.circle(540 - wd / 2 + 56 * sc, cy, 18 * sc, col(dot, a))
        L.text(540 - wd / 2 + 96 * sc, cy, name, 54 * sc, "bold", col(PAPER, a), "lm")


def scene_v8_upload(L, t):
    """Bildschirmaufnahme: Verkaufsdatei hochladen, Finger tippt auf die Ablagefläche."""
    x0, y0, x1, y1 = 100, 520, 980, 1260
    L.rrect(x0, y0, x1, y1, 44, fill=col(INK2), outline=col((60, 68, 80)), width=4)
    L.rrect(x0 + 40, y0 + 36, x1 - 40, y0 + 104, 34, fill=col((38, 44, 54)))
    L.text(540, y0 + 70, "sellcheck.app / tools", 30, "medium", col(MUTED), "mm")
    L.text(540, y0 + 190, "Verkaufsdatei hochladen", 46, "heavy", col(PAPER), "mm")
    landed = t >= V8_T["landed"]
    zx0, zy0, zx1, zy1 = x0 + 60, y0 + 250, x1 - 60, y1 - 70
    L.rrect(zx0, zy0, zx1, zy1, 36, fill=col((24, 28, 36)), outline=col(LIME if landed else (74, 82, 94)), width=4)
    L.line([(540, zy0 + 150), (540, zy0 + 100)], col(MUTED), 8)
    L.line([(516, zy0 + 122), (540, zy0 + 98), (564, zy0 + 122)], col(MUTED), 8)
    L.text(540, zy0 + 210, "CSV hier ablegen", 40, "medium", col(MUTED), "mm")
    fp = prog(t, V8_T["tap_up"] + 0.2, 0.7)
    if fp > 0:
        fy = y0 - 30 + ease_out(fp) * ((zy0 + zy1) / 2 + 40 - (y0 - 30))
        sc = 1.0 + (0.06 * math.sin(clamp((t - V8_T["landed"]) / 0.25) * math.pi) if landed else 0.0)
        pill(L, 540, fy, 600 * sc, 100 * sc, col(PAPER))
        L.rrect(540 - 270 * sc, fy - 25 * sc, 540 - 234 * sc, fy + 25 * sc, 6, fill=col(INK))
        L.text(540 - 214 * sc, fy, "eBay_Transaktionen.csv", 32 * sc, "bold", col(INK), "lm")
    if landed:
        lp = prog(t, V8_T["landed"], 0.3)
        check_circle(L, 540 - 130, zy1 - 70, 24 * (0.6 + 0.4 * ease_back(lp)))
        L.text(540 - 90, zy1 - 70, "Datei gelesen", 40, "heavy", col(PAPER, 255 * clamp(lp * 3)), "lm")
    draw_tap(L, t, V8_T["tap_up"], 700, (zy0 + zy1) / 2 + 110)


def v8_words():
    """Wörter mit Zeitmarken (Sekunden) aus der Datei v8_words.json, wird beim Bauen aus den Sprachclips erzeugt."""
    global _V8_WORDS
    if _V8_WORDS is None:
        import json
        path = os.path.join(FRAMES, "v8_words.json")
        _V8_WORDS = json.load(open(path)) if os.path.exists(path) else []
    return _V8_WORDS


_V8_WORDS = None


def draw_captions_v8(L, t):
    """TikTok-Untertitel: bis zu 3 Wörter gleichzeitig, das gesprochene Wort in Lime."""
    words = v8_words()
    if not words:
        return
    cur = None
    for k, (w, a, b) in enumerate(words):
        if a - 0.05 <= t < b + 0.12:
            cur = k
            break
    if cur is None:
        return
    # Chunk: Wörter derselben Dreiergruppe (ohne Satzgrenze)
    g0 = cur - (cur % 3)
    chunk = words[g0:g0 + 3]
    for j in range(len(chunk) - 1):
        if chunk[j][0].endswith((".", "?", "!")):
            chunk = chunk[:j + 1]
            break
    size = 76
    texts = [c[0] for c in chunk]
    while sum(L.width(x + " ", size, "heavy") for x in texts) > 940 and size > 40:
        size -= 2
    total = sum(L.width(x + " ", size, "heavy") for x in texts)
    x = 540 - total / 2
    for j, (w, a, b) in enumerate(chunk):
        active = g0 + j == cur
        L.d.text((px(x), px(1400)), w, font=font(size, "heavy"), fill=col(LIME if active else PAPER), anchor="lm",
                 stroke_width=px(6), stroke_fill=col(INK))
        x += L.width(w + " ", size, "heavy")


# ---- V8 (UGC-Stil, echte Bildschirmaufnahme der Oberfläche statt Nachbau)
@lru_cache(maxsize=8)
def v8_img(name):
    return Image.open(os.path.join(HERE, "assets", "v8", name)).convert("RGB")


def ui_window(L, img_name, header_name, y, alpha=255, hdr_h=350):
    """Zeichnet die Aufnahme (Inhalt ab Zeile y) unter der festen Kopfleiste, wie ein Scroll in der Seite."""
    img = v8_img(img_name)
    ch = 1535 if hdr_h == 350 else 1920 - hdr_h
    y = int(max(0, min(img.height - ch, y)))
    part = img.crop((0, y, 1080, y + ch)).resize((1080 * S, ch * S), Image.BICUBIC)
    hdr = v8_img(header_name).resize((1080 * S, hdr_h * S), Image.BICUBIC)
    L.d.rectangle([0, 0, W * S, H * S], fill=(245, 243, 238, alpha))
    L.im.paste(part, (0, hdr_h * S))
    L.im.paste(hdr, (0, 0))


def v8_ease(a, b, t, t0, t1):
    """Weiches Scrollen von a nach b zwischen t0 und t1."""
    p = ease_out(prog(t, t0, t1 - t0)) if t1 > t0 else 1.0
    return a + (b - a) * p


def v8_blend(L, patch, X0, Y0):
    """Legt einen RGBA-Ausschnitt mit echter Transparenz über die Aufnahme (Position in Pixeln der Ebene)."""
    X0, Y0 = int(X0), int(Y0)
    X1, Y1 = X0 + patch.width, Y0 + patch.height
    cx0, cy0, cx1, cy1 = max(0, X0), max(0, Y0), min(L.im.width, X1), min(L.im.height, Y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    patch = patch.crop((cx0 - X0, cy0 - Y0, cx1 - X0, cy1 - Y0))
    reg = L.im.crop((cx0, cy0, cx1, cy1))
    L.im.paste(Image.alpha_composite(reg, patch), (cx0, cy0))


def v8_highlight(L, x0, y0, x1, y1, t, start, dur=0.4):
    """Marker-Streifen, der über den Text gezogen wird (Text bleibt lesbar)."""
    p = ease_out(prog(t, start, dur))
    if p <= 0:
        return
    w, h = int((x1 - x0) * p * S), int((y1 - y0) * S)
    if w > 0 and h > 0:
        v8_blend(L, Image.new("RGBA", (w, h), (255, 214, 0, 110)), x0 * S, y0 * S)


def v8_tap(L, t, start, x, y):
    """Finger-Tap: dunkler Punkt mit sich öffnendem Ring (auf heller Oberfläche sichtbar)."""
    p = prog(t, start, 0.6)
    if p <= 0 or p >= 1:
        return
    r = (30 + 60 * ease_out(p)) * S
    size = int(2 * r + 20)
    patch = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    c = size / 2
    d.ellipse([c - r, c - r, c + r, c + r], outline=(30, 34, 42, int(210 * (1 - p))), width=int(8 * S))
    pd = clamp(1 - prog(t, start, 0.35))
    if pd > 0:
        rr = 34 * (0.6 + 0.4 * pd) * S
        d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=(30, 34, 42, int(150 * pd)))
    v8_blend(L, patch, x * S - c, y * S - c)


# Zeilen in den Aufnahmen (aus den Messungen der echten Seite)
V8_S5 = {"para": 323, "hl1": (355, 479, 642, 545), "hl2": (768, 479, 952, 545), "hl3": (112, 556, 372, 622),
         "tiles": 1082, "vinted": 2185, "klein": 2798, "ebay": 3411, "etsy": 4014}
V8_S3 = {"drop": 6789, "drop_h": 694, "msg": 7785, "go": 9703}


def scene_v8_s1(L, t):
    """Die Seite 'Meldegrenzen prüfen': Erklärtext mit Marker auf '30 Verkäufe oder 2.000 € Einnahmen'."""
    y = 40  # ruhiger Bildausschnitt, kein Scrollen
    ui_window(L, "v8_step5.jpg", "header_step5.jpg", y)
    off = 350 - y
    for key, st in (("hl1", V8_T["hl"]), ("hl2", V8_T["hl"] + 0.25), ("hl3", V8_T["hl"] + 0.4)):
        x0, y0, x1, y1 = V8_S5[key]
        v8_highlight(L, x0 - 6, y0 + off, x1 + 6, y1 + off, t, st)


def scene_v8_s2(L, t):
    """Datei hochladen (Tap auf die Ablagefläche), danach die Anleitungen: 'Wo du die findest, zeigt dir SellCheck'."""
    tap_t = V8_T["tap_up"]
    after = t >= tap_t + 0.35
    img = "v8_step3_geladen.jpg" if after else "v8_step3_leer.jpg"
    y0, y1 = 6300.0, 5350.0
    y = v8_ease(y0, y1, t, V8_T["guide_scroll"], V8_T["guide_scroll"] + 1.0)
    ui_window(L, img, "header_step3.jpg", y)
    v8_tap(L, t, tap_t, 540, V8_S3["drop"] + V8_S3["drop_h"] / 2 + (350 - y0))
    # Anleitung öffnen unter dem Vinted-Eintrag (Zeile 5934 in der Aufnahme)
    v8_tap(L, t, V8_T["tap_guide"], 540, 5934 + (350 - y1))


def scene_v8_s3(L, t):
    """Ergebnis: Karten pro Plattform scrollen durch, Tap auf Gelb und Rot, Gewinn markiert."""
    y = 960.0
    y = v8_ease(y, V8_S5["vinted"] - 40, t, V8_T["r_scroll1"], V8_T["r_scroll1"] + 1.2)
    y = v8_ease(y, V8_S5["etsy"] - 120, t, V8_T["r_scroll2"], V8_T["r_scroll2"] + 1.6)
    ui_window(L, "v8_step5.jpg", "header_step5.jpg", y)
    off = 350 - y
    v8_tap(L, t, V8_T["tap_gelb"], 560, V8_S5["vinted"] + 492 + (350 - (V8_S5["vinted"] - 40)))
    v8_tap(L, t, V8_T["tap_rot"], 540, V8_S5["etsy"] + 492 + off)
    # Gewinnzahl und Beschriftung der Etsy-Karte (gemessen: Zahl 322 bis 362, Label 397 bis 425, Karte ab 4014)
    v8_highlight(L, 156, V8_S5["etsy"] + 312 + off, 384, V8_S5["etsy"] + 436 + off, t, V8_T["hl_gewinn"])


V8_R = {"sub": (612, 742), "gewinn": (3050, 3235)}  # Zeilen in der Report-Aufnahme (gemessen)


def scene_v8_s4(L, t):
    """Steuer-Report: Ausfüllhilfe für die Anlage EÜR, Marker auf der Überschrift, dann auf dem Gewinn."""
    y = v8_ease(268, 2250, t, V8_T["rep_scroll"], V8_T["rep_scroll"] + 1.2)  # Aufnahme beginnt selbst mit der Leiste (268 px), daher erst darunter
    ui_window(L, "v8_report.jpg", "header_report.jpg", y, hdr_h=268)
    off = 268 - y
    a0, a1 = V8_R["sub"]
    v8_highlight(L, 30, a0 + off, 1040, a1 + off, t, V8_T["rep_hl1"])
    g0, g1 = V8_R["gewinn"]
    v8_highlight(L, 30, g0 + off, 700, g1 + off, t, V8_T["rep_hl2"])


# ---- V9: Chat zwischen Tim und Anna (generisches Messenger-Design, keine fremde Marke), dazwischen die echte Oberfläche
@lru_cache(maxsize=64)
def hn(size, bold=False):
    return ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", int(round(size * S)), index=1 if bold else 0)


def hn_wrap(L, text, size, maxw, bold=False):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if L.d.textlength(trial, font=hn(size, bold)) / S <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def hn_text(L, x, y, s, size, fill, bold=False, anchor="la"):
    L.d.text((int(x * S), int(y * S)), s, font=hn(size, bold), fill=fill, anchor=anchor)


CH_BG = (239, 234, 226)       # Hintergrund des Chats (helles Beige)
CH_DOODLE = (222, 214, 203)   # Muster im Hintergrund
CH_IN = (255, 255, 255)
CH_OUT = (217, 253, 211)
CH_INK = (17, 27, 33)
CH_GREY = (102, 119, 129)
CH_HEAD = (247, 247, 247)
CH_GREEN = (0, 168, 132)
CH_TICK = (83, 189, 235)
V9_LAYOUT = {"top": 470, "bottom": 1340, "gap": 10}

# Nachrichten: (Absender, Text, Erscheinen, Typ). Zeiten je Szene, werden nach den Sprachclips angepasst.
V9_CHAT1 = [
    ("tim", "Hey Anna, wusstest du, dass Plattformen deine Verkäufe an die Steuerbehörde melden?", 0.6, "text"),
    ("anna", "Warte, was? Woher weiß ich, ob ich über der Grenze bin?", 2.4, "text"),
    ("tim", "Mit SellCheck:", 3.5, "link"),
]
V9_CHAT2_PREV = [m[:3] + ("text",) for m in V9_CHAT1[:2]] + [V9_CHAT1[2][:3] + ("link",)]
V9_CHAT2 = [
    ("anna", "Ahh cool, so eine praktische Website kannte ich gar nicht.", 0.8, "text"),
    ("tim", "Jap! Und das Beste: kostenlos, mit Konto, und deine Daten bleiben im Browser.", 5.2, "text"),
]
V9_T = {"tim_type0": 0.1, "anna_type0": 1.5, "tim_type1": 3.0, "tap_link": 4.7, "link_y": 1160,
        "c2_anna_type0": 0.1, "c2_tim_type": 4.7,
        "up_tap": 1.0, "banner_in": 1.6, "banner_out": 8.0, "go_scroll": 2.4, "go_tap": 4.2, "res_switch": 4.7,
        "res_scroll1": 5.5, "res_scroll2": 7.5, "res_hl": 8.8}
V9_BANNER = "Du lädst einfach deine Verkäufe als CSV hoch, und SellCheck zeigt dir pro Plattform, wo du stehst."


def v9_bubble_layout(L, msgs):
    """Berechnet Position und Größe aller Blasen (unabhängig von der Zeit)."""
    out, y, prev = [], V9_LAYOUT["top"], None
    for who, text, t0, kind in msgs:
        maxw = 700
        lines = hn_wrap(L, text, 44, maxw)
        w = max(L.d.textlength(l, font=hn(44)) / S for l in lines) + 60
        h = len(lines) * 58 + 32 + 40
        if kind == "link":
            w = max(w, 700)
            h += 250
        x0 = 30 if who == "tim" else 1050 - w
        gap = V9_LAYOUT["gap"] if prev == who else 26
        y += gap if out else 0
        out.append(dict(who=who, text=text, lines=lines, t0=t0, kind=kind, x0=x0, y0=y, w=w, h=h, tail=(prev != who)))
        y += h
        prev = who
    return out


def v9_draw_link_card(L, x, y, w):
    L.rrect(x + 14, y + 14, x + w - 14, y + 234, 22, fill=(238, 241, 243))
    # Logo-Fläche
    L.rrect(x + 14, y + 14, x + 214, y + 234, 22, fill=col(INK))
    wlo, _ = LOGO.lockup_size(64 * S)
    mark = Image.new("RGBA", (200 * S, 220 * S), (0, 0, 0, 0))
    LOGO.draw_mark(ImageDraw.Draw(mark), 70 * S, 72 * S, 76 * S, on_dark=True)
    L.im.alpha_composite(mark, (int((x + 14) * S), int((y + 14) * S)))
    hn_text(L, x + 236, y + 52, "SellCheck", 36, CH_INK, True)
    hn_text(L, x + 236, y + 100, "Alle Plattformen.", 30, CH_GREY)
    hn_text(L, x + 236, y + 138, "Ein Überblick.", 30, CH_GREY)
    hn_text(L, x + 236, y + 190, "gym7-fit.github.io", 26, (47, 111, 142))


def v9_doodles(L):
    """Dezentes Muster wie das Standard-Hintergrundbild eines Messengers (Kreise, Sterne, Wellen, Herzen)."""
    rnd = random.Random(21)
    for gy in range(240, 1900, 150):
        for gx in range(30, 1080, 150):
            x, y = gx + rnd.randint(-30, 30), gy + rnd.randint(-30, 30)
            kind = rnd.randint(0, 4)
            c = CH_DOODLE + (255,)
            if kind == 0:
                L.d.ellipse([(x - 14) * S, (y - 14) * S, (x + 14) * S, (y + 14) * S], outline=c, width=int(3 * S))
            elif kind == 1:
                L.line([(x - 16, y), (x + 16, y)], c, 3)
                L.line([(x, y - 16), (x, y + 16)], c, 3)
            elif kind == 2:
                pts = [(x - 20 + i * 8, y + (8 if i % 2 else -8)) for i in range(6)]
                L.line(pts, c, 3)
            elif kind == 3:
                L.d.polygon([((x) * S, (y - 16) * S), ((x + 16) * S, y * S), (x * S, (y + 16) * S), ((x - 16) * S, y * S)], outline=c, width=int(3 * S))
            else:
                L.d.arc([(x - 14) * S, (y - 14) * S, (x + 14) * S, (y + 14) * S], 200, 340, fill=c, width=int(3 * S))


def v9_keyboard(L):
    L.d.rectangle([0, 1510 * S, W * S, H * S], fill=(209, 212, 217, 255))
    rows = ["QWERTZUIOP", "ASDFGHJKL", "YXCVBNM"]
    kw, kh, gx = 92, 84, 10
    for r_, letters in enumerate(rows):
        n = len(letters)
        total = n * kw + (n - 1) * gx
        x0 = (W - total) / 2
        yk = 1526 + r_ * (kh + 16)
        for c_, ch in enumerate(letters):
            L.rrect(x0 + c_ * (kw + gx), yk, x0 + c_ * (kw + gx) + kw, yk + kh, 14, fill=(255, 255, 255, 255))
            hn_text(L, x0 + c_ * (kw + gx) + kw / 2, yk + kh / 2, ch, 44, (30, 30, 30), anchor="mm")
        if r_ == 2:
            L.rrect(x0 - 124, yk, x0 - 124 + 108, yk + kh, 14, fill=(172, 178, 187, 255))
            L.rrect(x0 + total + 16, yk, x0 + total + 124, yk + kh, 14, fill=(172, 178, 187, 255))
    yb = 1526 + 3 * (kh + 16)
    L.rrect(24, yb, 24 + 150, yb + kh, 14, fill=(172, 178, 187, 255))
    hn_text(L, 24 + 75, yb + kh / 2, "123", 42, (30, 30, 30), anchor="mm")
    L.rrect(190, yb, 190 + 100, yb + kh, 14, fill=(172, 178, 187, 255))
    L.rrect(306, yb, 306 + 470, yb + kh, 14, fill=(255, 255, 255, 255))
    hn_text(L, 306 + 235, yb + kh / 2, "Leerzeichen", 38, (30, 30, 30), anchor="mm")
    L.rrect(792, yb, 1056, yb + kh, 14, fill=(172, 178, 187, 255))
    hn_text(L, 792 + 132, yb + kh / 2, "Senden", 40, (30, 30, 30), anchor="mm")


@lru_cache(maxsize=1)
def v9_memoji_img():
    return Image.open(os.path.join(HERE, "assets", "v9", "tim_memoji.png")).convert("RGBA")


def v9_memoji(L, cx, cy, r, bg=(206, 228, 247)):
    """Tims Profilbild: Memoji-Grafik (vom Nutzer geliefert, zwinkernd) freigestellt auf Pastellkreis."""
    n = int(2 * r * S)
    base = Image.new("RGBA", (n, n), bg + (255,))
    mm = v9_memoji_img()
    sc = (1.62 * r * S) / mm.width
    mm = mm.resize((max(1, int(mm.width * sc)), max(1, int(mm.height * sc))), Image.LANCZOS)
    base.alpha_composite(mm, ((n - mm.width) // 2, int(n * 0.50 - mm.height * 0.50)))
    m = Image.new("L", (n, n), 0)
    ImageDraw.Draw(m).ellipse([0, 0, n - 1, n - 1], fill=255)
    base.putalpha(Image.composite(base.getchannel("A"), Image.new("L", (n, n), 0), m))
    v8_blend(L, base, cx * S - n / 2, cy * S - n / 2)


def v9_glass(L, x0, y0, x1, y1, radius, tint=(250, 250, 252), alpha=150):
    """Milchglas wie bei iOS: Hintergrund wird weichgezeichnet und leicht aufgehellt, mit weichem Schatten."""
    X0, Y0, X1, Y1 = int(x0 * S), int(y0 * S), int(x1 * S), int(y1 * S)
    pad = int(40 * S)
    # Schatten
    sh = Image.new("RGBA", (X1 - X0 + 2 * pad, Y1 - Y0 + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad + int(10 * S), pad + X1 - X0, pad + Y1 - Y0 + int(10 * S)], radius=int(radius * S), fill=(0, 0, 0, 70))
    v8_blend(L, sh.filter(ImageFilter.GaussianBlur(int(16 * S))), X0 - pad, Y0 - pad)
    cx0, cy0, cx1, cy1 = max(0, X0), max(0, Y0), min(L.im.width, X1), min(L.im.height, Y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return  # Banner liegt gerade außerhalb des Bildes
    reg = L.im.crop((cx0, cy0, cx1, cy1)).filter(ImageFilter.GaussianBlur(int(22 * S)))
    glass = Image.new("RGBA", reg.size, tint + (alpha,))
    reg = Image.alpha_composite(reg, glass)
    m = Image.new("L", (X1 - X0, Y1 - Y0), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, X1 - X0 - 1, Y1 - Y0 - 1], radius=int(radius * S), fill=255)
    m = m.crop((cx0 - X0, cy0 - Y0, cx1 - X0, cy1 - Y0))
    L.im.paste(reg, (cx0, cy0), m)


def v9_header(L, status):
    L.d.rectangle([0, 0, W * S, 360 * S], fill=CH_HEAD + (255,))
    L.d.rectangle([0, 359 * S, W * S, 361 * S], fill=(218, 218, 218, 255))
    hn_text(L, 90, 70, "9:41", 40, (0, 0, 0), True, anchor="lm")
    L.rrect(930, 52, 1010, 88, 10, outline=(0, 0, 0, 255), width=3)
    L.rrect(936, 58, 990, 82, 5, fill=(0, 0, 0, 255))
    L.line([(900, 84), (900, 66)], (0, 0, 0, 255), 6)
    L.line([(880, 84), (880, 72)], (0, 0, 0, 255), 6)
    L.line([(860, 84), (860, 78)], (0, 0, 0, 255), 6)
    # Navigationsleiste
    L.line([(62, 215), (36, 245), (62, 275)], CH_GREEN + (255,), 8)
    v9_memoji(L, 150, 245, 54)
    hn_text(L, 230, 222, "Tim", 48, (0, 0, 0), True, anchor="lm")
    green = status == "schreibt …"
    hn_text(L, 230, 272, status, 33, CH_GREEN if green else CH_GREY, anchor="lm")
    # Symbole rechts: Video und Anruf
    L.rrect(842, 225, 900, 265, 8, outline=CH_GREEN + (255,), width=5)
    L.poly([(900, 238), (922, 226), (922, 264), (900, 252)], CH_GREEN + (255,))
    L.d.arc([(962) * S, (222) * S, (1018) * S, (278) * S], 20, 160, fill=CH_GREEN + (255,), width=int(7 * S))


def v9_draw_chat(L, t, msgs, prev_msgs=(), typing=None, anna_typing=None, tap=None, status_typing=None):
    """Chatbildschirm im Messenger-Look. typing: Liste von Zeitfenstern, in denen Tim 'schreibt …' (nur in der Kopfzeile)."""
    L.d.rectangle([0, 0, W * S, H * S], fill=CH_BG + (255,))
    v9_doodles(L)
    allm = list(prev_msgs) + list(msgs)
    lay = v9_bubble_layout(L, allm)
    npv = len(prev_msgs)
    shown = [b for i, b in enumerate(lay) if i < npv or t >= b["t0"]]
    bottom = max((b["y0"] + b["h"] for b in shown), default=0)
    off = max(0, bottom - V9_LAYOUT["bottom"])
    # Datum und Hinweis zu Beginn des Chats
    if off < 260:
        dy = 380 - off
        pw = hn(30).getlength("HEUTE") / S + 56
        L.rrect(540 - pw / 2, dy, 540 + pw / 2, dy + 52, 14, fill=(255, 255, 255, 235))
        hn_text(L, 540, dy + 27, "HEUTE", 28, CH_GREY, anchor="mm")
    for i, b in enumerate(lay):
        if i >= npv and t < b["t0"]:
            continue
        p = 1.0 if i < npv else ease_out(prog(t, b["t0"], 0.18))
        yy = b["y0"] - off + (1 - p) * 24
        if yy + b["h"] < 380 or yy > 1390:
            continue
        fill = (CH_IN if b["who"] == "tim" else CH_OUT) + (255,)
        L.rrect(b["x0"], yy, b["x0"] + b["w"], yy + b["h"], 30, fill=fill)
        if b["tail"]:
            if b["who"] == "tim":
                L.poly([(b["x0"] - 14, yy), (b["x0"] + 30, yy), (b["x0"] + 30, yy + 36)], fill)
            else:
                L.poly([(b["x0"] + b["w"] + 14, yy), (b["x0"] + b["w"] - 30, yy), (b["x0"] + b["w"] - 30, yy + 36)], fill)
        ty = yy + 18
        for ln in b["lines"]:
            hn_text(L, b["x0"] + 30, ty, ln, 44, CH_INK)
            ty += 58
        if b["kind"] == "link":
            v9_draw_link_card(L, b["x0"], ty + 4, b["w"])
        hn_text(L, b["x0"] + b["w"] - (66 if b["who"] == "anna" else 22), yy + b["h"] - 14, "9:41", 28, CH_GREY, anchor="rb")
        if b["who"] == "anna":
            cx0, cy0 = b["x0"] + b["w"] - 40, yy + b["h"] - 30
            for dx in (0, 12):
                L.line([(cx0 + dx - 10, cy0), (cx0 + dx - 3, cy0 + 9), (cx0 + dx + 11, cy0 - 9)], CH_TICK + (255,), 3)
    # Kopfzeile
    tw_active = next((w for w in (typing or []) if w[0] <= t < w[1]), None)
    v9_header(L, "schreibt …" if (tw_active or status_typing) else "online")
    # Eingabeleiste
    L.d.rectangle([0, 1380 * S, W * S, 1510 * S], fill=(247, 247, 247, 255))
    L.line([(54, 1445), (90, 1445)], CH_GREEN + (255,), 6)
    L.line([(72, 1427), (72, 1463)], CH_GREEN + (255,), 6)
    L.rrect(120, 1397, 880, 1493, 48, fill=(255, 255, 255, 255), outline=(218, 218, 218, 255), width=2)
    txt = ""
    if anna_typing:
        a0, a1, full, tsend = anna_typing
        if a0 <= t < tsend:
            k = int(len(full) * clamp((t - a0) / max(0.1, a1 - a0)))
            txt = full[:k]
    if txt:
        shown_txt = txt if L.d.textlength(txt, font=hn(42)) / S < 700 else "…" + txt[-28:]
        hn_text(L, 150, 1445, shown_txt, 42, CH_INK, anchor="lm")
    else:
        hn_text(L, 150, 1445, "Nachricht", 42, (150, 160, 168), anchor="lm")
    L.rrect(930, 1425, 986, 1465, 8, outline=(110, 120, 128, 255), width=4)
    L.circle(958, 1445, 12, col((110, 120, 128)))
    L.rrect(1000, 1424, 1052, 1466, 10, outline=(110, 120, 128, 255), width=4)
    v9_keyboard(L)
    if tap:
        v8_tap(L, t, tap[0], tap[1], tap[2])


def scene_v9_chat1(L, t):
    anna_txt = V9_CHAT1[1][1]
    v9_draw_chat(L, t, V9_CHAT1,
                 typing=[(V9_T["tim_type0"], V9_CHAT1[0][2]), (V9_T["tim_type1"], V9_CHAT1[2][2])],
                 anna_typing=(V9_T["anna_type0"], V9_CHAT1[1][2] - 0.1, anna_txt, V9_CHAT1[1][2]))
    v8_tap(L, t, V9_T["tap_link"], 420, V9_T["link_y"])  # Tap auf die Link-Vorschau


def scene_v9_site(L, t):
    """Die echte Oberfläche öffnet sich (von unten), Banner von Tim oben, Upload und Ergebnis."""
    tw = V9_T
    tmp = Layer()
    if t < tw["res_switch"]:
        after = t >= tw["up_tap"] + 0.35
        img = "v8_step3_geladen.jpg" if after else "v8_step3_leer.jpg"
        y = 6300.0
        y = v8_ease(y, 9330, t, tw["go_scroll"], tw["go_scroll"] + 1.2)
        ui_window(tmp, img, "header_step3.jpg", y)
        v8_tap(tmp, t, tw["up_tap"], 540, V8_S3["drop"] + V8_S3["drop_h"] / 2 + (350 - 6300))
        v8_tap(tmp, t, tw["go_tap"], 310, V8_S3["go"] + 80 + (350 - 9330))
    else:
        y = 960.0
        y = v8_ease(y, V8_S5["vinted"] - 40, t, tw["res_scroll1"], tw["res_scroll1"] + 1.2)
        y = v8_ease(y, V8_S5["etsy"] - 120, t, tw["res_scroll2"], tw["res_scroll2"] + 1.4)
        ui_window(tmp, "v8_step5.jpg", "header_step5.jpg", y)
        off = 350 - y
        v8_highlight(tmp, 150, V8_S5["etsy"] + 470 + off, 705, V8_S5["etsy"] + 535 + off, t, tw["res_hl"])
    p = ease_out(prog(t, 0.0, 0.45))
    L.d.rectangle([0, 0, W * S, H * S], fill=CH_BG + (255,))
    L.im.paste(tmp.im, (0, int((1 - p) * H * S)))
    # Mitteilungsbanner wie auf dem iPhone (iOS 17): Milchglas, große Rundung, Kontaktfoto mit App-Symbol, Name, Text
    b0, b1 = tw["banner_in"], tw["banner_out"]
    if b0 <= t < b1 + 0.5:
        lines = hn_wrap(L, V9_BANNER, 41, 760)[:3]
        h = 36 + 52 + len(lines) * 52 + 28
        pin = ease_back(prog(t, b0, 0.5))
        pout = ease_out(prog(t, b1, 0.35))
        by = 16 + (-h - 200) * (1 - pin) + (-h - 200) * pout
        v9_glass(L, 22, by, 1058, by + h, 66)
        v9_memoji(L, 112, by + h / 2 - 4, 50)
        # kleines App-Symbol an der Ecke des Fotos
        L.rrect(128, by + h / 2 + 22, 176, by + h / 2 + 70, 12, fill=(37, 211, 102, 255), outline=(255, 255, 255, 255), width=3)
        L.circle(152, by + h / 2 + 46, 11, col((255, 255, 255)))
        hn_text(L, 200, by + 34, "Tim", 44, (0, 0, 0), True)
        hn_text(L, 1030, by + 38, "jetzt", 34, (120, 120, 128), anchor="ra")
        ty = by + 34 + 54
        for ln in lines:
            hn_text(L, 200, ty, ln, 41, (20, 20, 22))
            ty += 52


def scene_v9_chat2(L, t):
    anna_txt = V9_CHAT2[0][1]
    v9_draw_chat(L, t, V9_CHAT2, prev_msgs=V9_CHAT2_PREV,
                 anna_typing=(V9_T["c2_anna_type0"], V9_CHAT2[0][2] - 0.1, anna_txt, V9_CHAT2[0][2]),
                 typing=[(V9_T["c2_tim_type"], V9_CHAT2[1][2])])


SCENES = {
    "V9": [(1, scene_v9_chat1), (2, scene_v9_site), (3, scene_v9_chat2)],
    "V8": [(1, scene_v8_s1), (2, scene_v8_s2), (3, scene_v8_s3), (4, scene_v8_s4)],
    "V6": [(1, scene_v6_hook), (2, scene_v6_questions), (3, scene_v6_answers)],
    "A": [(1, scene_hook_a), (2, scene_problem_a)],
    "B": [(1, scene_hook_b), (2, scene_problem_b)],
    "V2": [(1, scene_v2_hook), (2, scene_v2_deadline)],
    "V3": [(1, scene_v3_hook), (2, scene_v2_deadline)],
    "V7": [(1, scene_v7_hook), (2, scene_v7_profit)],
}
COMMON = [(5, scene_cta)] if VAR == "V8" else [(4, scene_cta)] if VAR == "V9" else [(4, scene_cta)] if VAR == "V6" else [(3, scene_demo), (4, scene_cta)] if V2LIKE else [(3, scene_demo), (4, scene_benefits), (5, scene_cta)]


# ------------------------------------------------------------------ Hintergrund & Frame
@lru_cache(maxsize=1)
def background():
    base = Image.new("RGB", (W * S, H * S), INK)
    small = (W * S // 4, H * S // 4)
    rg = Image.radial_gradient("L").resize(small, Image.BICUBIC)
    inv = Image.eval(rg, lambda v: 255 - v)
    glow = Image.new("RGB", small, LIME)
    mask = inv.point(lambda v: int(v * 0.16))
    layer = Image.new("RGB", small, INK)
    layer = Image.composite(glow, layer, mask).resize((W * S, H * S), Image.BICUBIC)
    # Glow unten links und zart oben rechts
    out = base.copy()
    big = Image.new("L", (W * S, H * S), 0)
    out.paste(layer.crop((0, 0, W * S, H * S)), (0, 0))
    return out


def render_frame(args):
    i, variant = args
    t = i / FPS
    im = background().copy()
    L0 = Layer()
    if not (variant == "V8" and t < START[5]) and not (variant == "V9" and t < START[4]):
        brand(L0, t)
    im.paste(L0.im, (0, 0), L0.im)
    scenes = SCENES[variant] + COMMON
    for k, fn in scenes:
        start = START[k]
        end = start + BASE[k] * SLOW[k] if k != LAST else DUR + 1
        if start <= t < end:
            L = Layer()
            lt = (t - start) / SLOW[k]
            fn(L, lt)
            f = min(clamp((t - start) / 0.08), clamp((end - t) / 0.08))
            if f < 1:
                a = L.im.getchannel("A").point(lambda v: int(v * f))
                L.im.putalpha(a)
            im.paste(L.im, (0, 0), L.im)
            break
    if variant == "V8" and t < START[5]:
        Lc = Layer()
        draw_captions_v8(Lc, t)
        im.paste(Lc.im, (0, 0), Lc.im)
    im = im.reduce(S)
    path = os.path.join(FRAMES, variant, f"f_{i:05d}.jpg")
    im.save(path, quality=95, subsampling=0)
    return i


# ------------------------------------------------------------------ Ton (reine Synthese)
SR = 44100
VOICE = os.environ.get("AD_VOICE", "Anna")          # macOS-Systemstimme (say -v '?' zeigt die Liste)
VO_RATE = os.environ.get("AD_VOICE_RATE", "165")    # Wörter pro Minute

# Sprechertext je Variante: (absolute Startzeit, Text, spätestes Ende)
def vo_lines(variant):
    if variant == "V8":
        return [
            (at(1, 0.05), "Wusstest du, dass Vinted, eBay und Kleinanzeigen deine Verkäufe an die Steuerbehörde melden, sobald du eine bestimmte Grenze erreichst? Ich zeig dir kurz, wo du stehst.", START[2]),
            (at(2, 0.05), "Dafür lädst du einfach die Datei mit deinen Verkäufen hoch. Wo du die bei deiner Plattform findest, zeigt dir SellCheck.", START[3]),
            (at(3, 0.05), "Dann siehst du pro Plattform, wie nah du an der Grenze bist. Gelb heißt: fast erreicht. Rot heißt: erreicht, so wie hier bei Etsy. Und in jeder Karte siehst du auch deinen Gewinn.", START[4]),
            (at(4, 0.05), "Und daraus macht SellCheck dir die Übersicht für deine Steuererklärung, oder für deinen Steuerberater. Kostenlos mit Konto, und deine Daten bleiben in deinem Browser.", START[5]),
            (at(5, -0.10), "SellCheck. Check, was wirklich bleibt. Unten klicken, Datei hochladen, fertig.", DUR - 0.05),
        ]
    if variant == "V6":
        return [
            (at(1, 0.05), "Drei Fragen an alle, die auf Vinted, eBay oder Kleinanzeigen verkaufen.", START[2]),
            (at(2, 0.05), "Eins: Wie viele Verkäufe hattest du dieses Jahr? Zwei: Wie viel Umsatz davon auf welcher Plattform? Drei: Und was davon ist WIRKLICH Gewinn?", START[3]),
            (at(3, 0.05), "Keine Ahnung? Dann bist du nicht allein. SellCheck beantwortet dir alle drei.", START[4]),
            (at(4, -0.10), "SellCheck. Check, was WIRKLICH bleibt. Für mehr Infos unten klicken.", DUR - 0.05),
        ]
    if variant == "V7":
        return [
            (at(1, 0.05), "[curious] Du bist Reseller, oder willst wissen, was du WIRKLICH verdienst?", START[2]),
            (at(2, 0.05), "Dann zählt nicht dein UMSATZ. Sondern, was dir nach dem Einkauf ÜBRIG bleibt.", START[3]),
            (at(3, 0.05), "Und weil du viel umsetzt, bist du schnell an der gesetzlichen Grenze, ab der Plattformen dich melden. SellCheck zeigt dir BEIDES.", START[4]),
            (at(4, -0.10), "SellCheck. Check, was WIRKLICH bleibt. Für mehr Infos unten klicken.", DUR - 0.05),
        ]
    if variant == "V3":
        return [
            (at(1, 0.05), "[curious] Du verkaufst viel auf Vinted und Co?", START[2]),
            (at(2, 0.05), "Dann solltest du wissen: Plattformen melden dich bis Ende JANUAR, ab DREIßIG Verkäufen oder ZWEItausend Euro, an die Steuerbehörde.", START[3]),
            (at(3, 0.05), "Mit SellCheck lädst du einfach deine Verkäufe hoch und siehst pro Plattform, wie NAH du an der Grenze bist. Und was dir WIRKLICH bleibt.", START[4]),
            (at(4, -0.10), "SellCheck. Check, was WIRKLICH bleibt. Für mehr Infos unten klicken.", DUR - 0.05),
        ]
    if variant == "V2":
        return [
            (at(1, 0.05), "Hast du noch den Überblick über all deine Verkäufe?", START[2]),
            (at(2, 0.05), "Ende Januar melden Plattformen dein Jahr an die Steuerbehörde. Ab dreißig Verkäufen oder zweitausend Euro.", START[3]),
            (at(3, 0.05), "Lade deine Verkäufe hoch.", at(3, 1.5)),
            (at(3, 1.50), "Du siehst sofort, wie nah du pro Plattform an der Grenze bist.", at(3, S3_B)),
            (at(3, S3_B - 0.55), "Und was dir nach Abzug wirklich bleibt.", START[4]),
            (at(4, -0.10), "SellCheck. Check, was WIRKLICH bleibt. Für mehr Infos unten klicken.", DUR - 0.05),
        ]
    if variant != "A":
        return []
    return [
        (at(1, 0.05), "Vinted meldet dich ab dreißig Verkäufen.", START[2]),
        (at(2, 0.05), "Aber du verkaufst nicht nur dort. Und jede Plattform zählt einzeln.", START[3] + 0.2),
        (at(3, 0.05), "Lade deine Verkäufe hoch.", at(3, 2.4)),
        (at(3, 1.50), "Sieh die Ampel pro Plattform.", at(3, S3_B + 0.1)),
        (at(3, S3_B - 0.55), "Und druck den Report aus.", START[4] + 0.1),
        (at(4, -0.30), "Alle Plattformen. Ein Überblick.", START[5] + 0.1),
        (at(5, -0.35), "SellCheck. Gratis testen. Link unten antippen.", DUR - 0.05),
    ]


def fmt_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_script_files():
    """Sprechertext mit Zeitmarken (zum Selbst-Einsprechen) und Untertitel-Datei (.srt, z. B. für CapCut)."""
    lines = vo_lines("A")
    rows, srt = [], []
    for i, (t0, text, limit) in enumerate(lines, 1):
        words = len(text.split())
        end = min(t0 + max(1.8, words / 2.6), limit)
        rows.append(f"| {t0:5.1f} s | {end:5.1f} s | {text} |")
        srt.append(f"{i}\n{fmt_srt(t0)} --> {fmt_srt(end)}\n{text}\n")
    md = ("# Sprechertext zur Ad (Variante A)\n\n"
          f"Länge des Videos: {DUR:.1f} s. Die Zeiten sind Einsatzpunkte: Beginne den Satz zu diesem Zeitpunkt und "
          "sprich so, dass er vor dem nächsten Eintrag endet. Locker und freundlich, nicht werblich.\n\n"
          "| Start | spätestens Ende | Text |\n| --- | --- | --- |\n" + "\n".join(rows) + "\n")
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "sprechertext.md"), "w", encoding="utf-8").write(md)
    open(os.path.join(OUT, "untertitel.srt"), "w", encoding="utf-8").write("\n".join(srt))
    return md


def squeeze_gaps(x, sr=44100, thr=0.02, min_gap=0.28, keep=0.18):
    """Pausen innerhalb eines Clips, die länger als min_gap sind, auf keep Sekunden kürzen (straffer, ohne Tempoänderung)."""
    blk = int(0.01 * sr)
    out = []
    i, n = 0, len(x)
    quiet = []
    while i < n:
        seg = x[i:i + blk]
        if max(abs(v) for v in seg) < thr:
            quiet.append(seg)
        else:
            if quiet:
                total = len(quiet) * 0.01
                if total > min_gap:
                    nkeep = max(1, int(keep / 0.01))
                    quiet = quiet[:nkeep // 2] + quiet[-(nkeep - nkeep // 2):]
                for q in quiet:
                    out.extend(q)
                quiet = []
            out.extend(seg)
        i += blk
    for q in quiet:
        out.extend(q)
    return out


def load_clip(path, name):
    """Beliebiges Audio (mp3, m4a, wav, aiff) als Mono-Samples mit 44,1 kHz laden (nutzt macOS afconvert)."""
    wav = os.path.join(FRAMES, f"clip_{name}.wav")
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", path, wav], check=True)
    with wave.open(wav) as w:
        raw = w.readframes(w.getnframes())
    vals = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    pk = max(abs(v) for v in vals) or 1
    out = [v / pk * 0.9 for v in vals]
    # Stille am Anfang und Ende entfernen (30 ms Puffer), damit die Sätze direkt aneinander anschließen
    thr = 0.02
    first = next((i for i, v in enumerate(out) if abs(v) > thr), 0)
    last = next((i for i in range(len(out) - 1, -1, -1) if abs(out[i]) > thr), len(out) - 1)
    pad = int(0.03 * 44100)
    out = out[max(0, first - pad): min(len(out), last + pad)]
    return squeeze_gaps(out)


def find_voice_files(folder):
    """Erwartet Dateien 1.*, 2.*, ... in der Reihenfolge der Sprechertext-Zeilen (siehe voice/texte.txt)."""
    exts = (".mp3", ".m4a", ".wav", ".aiff", ".aif", ".caf", ".mp4")
    files = []
    for i in range(1, len(vo_lines(VAR)) + 1):
        hit = None
        for ext in exts:
            p = os.path.join(folder, f"{i}{ext}")
            if os.path.exists(p):
                hit = p
                break
        files.append(hit)
    return files


def tts(text, name):
    aiff = os.path.join(FRAMES, f"vo_{name}.aiff")
    wav = os.path.join(FRAMES, f"vo_{name}.wav")
    subprocess.run(["say", "-v", VOICE, "-r", VO_RATE, "-o", aiff, text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", aiff, wav], check=True)
    with wave.open(wav) as w:
        raw = w.readframes(w.getnframes())
    vals = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    pk = max(abs(v) for v in vals) or 1
    return [v / pk * 0.9 for v in vals]


def build_audio(variant, path, with_voice=False, voice_files=None):
    n = int(SR * DUR)
    music = [0.0] * n
    sfx = [0.0] * n
    rnd = random.Random(3)

    def add(buf, t0, samples, gain=1.0):
        s0 = int(t0 * SR)
        for k, v in enumerate(samples):
            j = s0 + k
            if 0 <= j < n:
                buf[j] += v * gain

    def tone(freq, dur, kind="sine", decay=6.0, freq_end=None, attack=60.0):
        out = []
        ph = 0.0
        m = int(dur * SR)
        for k in range(m):
            x = k / m
            f = freq if freq_end is None else freq + (freq_end - freq) * x
            ph += 2 * math.pi * f / SR
            v = math.sin(ph) if kind == "sine" else (2 * ((ph / (2 * math.pi)) % 1) - 1)
            out.append(v * math.exp(-decay * x) * min(1.0, k / attack))
        return out

    def hat(dur=0.03):
        out = []
        prev = 0.0
        for k in range(int(dur * SR)):
            x = k / (dur * SR)
            v = rnd.uniform(-1, 1)
            v, prev = v - prev * 0.9, v
            out.append(v * math.exp(-12 * x))
        return out

    beat = 0.5  # 120 bpm
    bass_notes = [55.0, 55.0, 43.65, 49.0]
    t = 0.0
    bar = 0
    while t < DUR:
        for b in range(4):
            tb = t + b * beat
            if tb >= DUR:
                break
            vol = 0.5 if tb < START[2] else 0.7
            add(music, tb, tone(120, 0.22, "sine", 9.0, 45), 0.8 * vol)   # Kick
            add(music, tb + beat / 2, hat(), 0.10 * vol)                  # Hi-Hat, sehr leise
            if tb >= START[3]:
                add(music, tb + beat / 2, tone(bass_notes[bar % 4] * 2, 0.2, "sine", 6.0), 0.14)
        add(music, t, tone(bass_notes[bar % 4], 1.9, "sine", 2.2), 0.45)
        if t >= START[3]:
            arp = [220.0, 261.63, 329.63, 392.0] if bar % 2 == 0 else [196.0, 246.94, 293.66, 392.0]
            for q in range(8):
                add(music, t + q * beat / 2, tone(arp[q % 4] * 2, 0.22, "sine", 7.0), 0.06)
        t += 4 * beat
        bar += 1

    if variant == "V9":
        music = [0.0] * n  # Chat-Ad ohne Musikbett

    # Effekte: nur weiche Töne, kein Rauschen
    def tick(t0, f=1500):
        add(sfx, t0, tone(f, 0.05, "sine", 10.0), 0.28)

    def pop(t0, f=520):
        add(sfx, t0, tone(f, 0.11, "sine", 7.0, f * 1.5), 0.32)

    def ding(t0, f):
        add(sfx, t0, tone(f, 0.5, "sine", 4.0), 0.3)
        add(sfx, t0, tone(f * 2, 0.35, "sine", 6.0), 0.08)

    def blip_down(t0):
        add(sfx, t0, tone(440, 0.14, "sine", 5.0, 360), 0.3)
        add(sfx, t0 + 0.13, tone(330, 0.2, "sine", 5.0, 250), 0.3)

    def swipe(t0):
        add(sfx, t0, tone(260, 0.28, "sine", 3.5, 520, attack=2000.0), 0.12)

    for k in KEYS[1:]:
        swipe(START[k] - 0.12)
    if variant != "V6":
        swipe(at(3, S3_B) - 0.1)

    if variant == "A":
        for base in (0.9, 1.25, 1.6):
            tick(at(1, base))
        blip_down(at(1, 1.65))
        for i in range(4):
            pop(at(2, 0.55 + i * 0.2), 480 + i * 60)
    elif variant == "V7":
        pop(at(1, 0.0), 520)
        pop(at(1, 0.29), 600)
        pop(at(1, 0.82), 560)
        pop(at(1, 1.43), 640)
        pop(at(2, P7_T[2]), 480)
        pop(at(2, P7_T[3]), 620)
        pop(at(2, P7_T[4]), 560)
        ding(at(2, P7_T[5] + 0.7), 659.25)  # Gewinn steht
    elif variant == "V3":
        for i, base in enumerate((0.9, 1.15, 1.4, 1.65)):
            tick(at(1, base), 1300 + i * 150)
        ding(at(2, 0.25), 659.25)           # Kalenderblatt
        pop(at(2, FRIST_T[0]), 700)
        pop(at(2, FRIST_T[1]), 780)
    elif variant == "V2":
        for i in range(4):
            pop(at(1, 1.0 + i * 0.18), 480 + i * 60)
        ding(at(2, 0.25), 659.25)           # Kalenderblatt
        pop(at(2, 2.1), 700)
        pop(at(2, 2.6), 780)
    else:
        for i in range(4):
            pop(at(1, 0.9 + i * 0.22), 480 + i * 60)
        pop(at(2, 0.0), 640)
        pop(at(2, 0.18), 720)

    if variant == "V9":
        def ping(t0):
            # heller, glasiger Hinweiston: zwei schnell aufeinanderfolgende hohe Töne mit lang nachklingendem Funkeln
            for dt, f, g in ((0.0, 1760.0, 0.30), (0.085, 2349.3, 0.26)):
                add(sfx, t0 + dt, tone(f, 1.1, "sine", 4.2), g)
                add(sfx, t0 + dt, tone(f * 2.76, 0.7, "sine", 6.0), g * 0.42)
                add(sfx, t0 + dt, tone(f * 5.4, 0.5, "sine", 9.0), g * 0.2)
                add(sfx, t0 + dt, tone(f * 8.93, 0.35, "sine", 12.0), g * 0.08)
        ping(at(1, V9_CHAT1[0][2]))
        pop(at(1, V9_CHAT1[1][2]), 480)
        ping(at(1, V9_CHAT1[2][2]))
        tick(at(1, V9_T["tap_link"]), 1500)
        tick(at(2, V9_T["up_tap"]), 1500)
        tick(at(2, V9_T["go_tap"]), 1500)
        ding(at(2, V9_T["res_hl"] + 0.2), 659.25)
        ping(at(2, V9_T["banner_in"]))
        pop(at(3, V9_CHAT2[0][2]), 480)
        ping(at(3, V9_CHAT2[1][2]))
    elif variant == "V8":
        for key, sc_ in (("tap_up", 2), ("tap_guide", 2), ("tap_gelb", 3), ("tap_rot", 3)):
            tick(at(sc_, V8_T[key]), 1500)
        ding(at(2, V8_T["tap_up"] + 0.5), 784.0)
        ding(at(3, V8_T["hl_gewinn"] + 0.2), 659.25)
        ding(at(4, V8_T["rep_hl2"] + 0.2), 784.0)
    elif variant == "V6":
        for i, qs in enumerate(V6_QSTART):
            pop(at(2, qs + 0.05), 480 + i * 90)
        for i, ft in enumerate(V6_FLIP):
            ding(at(3, ft + 0.4), (523.25, 659.25, 783.99)[i])
    else:
        add(sfx, at(3, 0.8), tone(180, 0.18, "sine", 8.0, 60), 0.5)    # Datei landet
        ding(at(3, 0.95), 784.0)                                           # "Datei gelesen"
        for i in range(4):
            tick(at(3, 2.0 + DEMO_SHIFT + i * 0.28 + 0.15), 1100 + i * 120)
        blip_down(at(3, 4.15 + DEMO_SHIFT))
        ding(at(3, S3_B + 1.6), 659.25)                                 # Summe ist oben angekommen
    if variant not in ("V2", "V3", "V6", "V7", "V8", "V9"):
        for i, f in enumerate((523.25, 659.25, 783.99)):
            ding(at(4, 0.35 + i * 0.4), f)
    cta = 4 if variant in ("V2", "V3", "V6", "V7", "V9") else 5
    for j, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        ding(at(cta, 0.9) + j * 0.1, f)

    # Sprecher (optional) und Absenkung der Musik darunter
    duck = [1.0] * n
    vo = [0.0] * n
    if with_voice:
        prev_end = 0.0
        for idx, (t0, text, limit) in enumerate(vo_lines(variant)):
            t0 = max(t0, prev_end + 0.04)
            if voice_files:
                if idx >= len(voice_files) or not voice_files[idx]:
                    continue
                samples = load_clip(voice_files[idx], f"{variant}{idx}")
            else:
                samples = tts(text, f"{variant}{idx}")
            end = t0 + len(samples) / SR
            prev_end = end
            flag = "" if end <= limit else "  <-- ZU LANG"
            print(f"  Sprecher {idx + 1}: {t0:5.2f}s bis {end:5.2f}s (Fenster bis {limit:5.2f}s){flag}", flush=True)
            add(vo, t0, samples, 1.0)
            a, b = int((t0 - 0.15) * SR), int((end + 0.3) * SR)
            for j in range(max(0, a), min(n, b)):
                ramp = min(1.0, (j - a) / (0.15 * SR), (b - j) / (0.3 * SR))
                duck[j] = min(duck[j], 1.0 - 0.6 * max(0.0, ramp))

    mix = [music[k] * duck[k] + sfx[k] * (0.7 if with_voice else 1.0) + vo[k] * 1.0 for k in range(n)]
    peak = max(abs(v) for v in mix) or 1.0
    scale = 0.85 / peak
    fade = int(0.35 * SR)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        buf = bytearray()
        for k, v in enumerate(mix):
            if k > n - fade:
                v *= (n - k) / fade
            sv = int(max(-1.0, min(1.0, v * scale)) * 32767)
            buf += struct.pack("<hh", sv, sv)
        w.writeframes(bytes(buf))


# ------------------------------------------------------------------ Main
def encode(variant, wav, mp4):
    enc = os.path.join(FRAMES, "encode")
    if not os.path.exists(enc) or os.path.getmtime(enc) < os.path.getmtime(os.path.join(HERE, "encode.swift")):
        print("Swift-Encoder bauen …", flush=True)
        subprocess.run(["swiftc", "-O", "-swift-version", "5", "-suppress-warnings", os.path.join(HERE, "encode.swift"), "-o", enc], check=True)
    subprocess.run([enc, os.path.join(FRAMES, variant), str(FPS), str(NF), wav, mp4], check=True)


def build_v8_words():
    """Wortzeiten für die Untertitel von V8 aus den gemessenen Sprachclips (Verteilung nach Wortlänge)."""
    import json
    files = find_voice_files(os.path.join(HERE, "voice_v8"))
    if not all(files):
        return
    words, prev_end = [], 0.0
    for (t0, text, limit), f in zip(vo_lines("V8"), files):
        t0 = max(t0, prev_end + 0.04)
        dur = len(load_clip(f, "v8w")) / SR
        prev_end = t0 + dur
        toks = text.split()
        # Satzzeichen bringen kurze Sprechpausen mit, das verbessert den Gleichlauf der Untertitel
        weights = [len(w.strip(".,?!:")) + 1.5 + (8.0 if w[-1] in ".?!:" else 3.5 if w.endswith(",") else 0.0) for w in toks]
        tot, tcur = sum(weights), t0
        for w, wt in zip(toks, weights):
            d = dur * wt / tot
            core = w.strip(".,?!:")
            shown = w.replace(core, core.lower()) if core.isupper() and len(core) > 3 else w
            words.append([shown, tcur, tcur + d])
            tcur += d
    os.makedirs(FRAMES, exist_ok=True)
    json.dump(words, open(os.path.join(FRAMES, "v8_words.json"), "w"))


def main():
    variant = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
    if variant == "V8":
        build_v8_words()
    only = sys.argv[2] if len(sys.argv) > 2 else ""
    if variant not in SCENES:
        raise SystemExit("Variante A oder B")
    os.makedirs(os.path.join(FRAMES, variant), exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    if only == "poster":
        secs = [float(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "0.5,2.0,4.0,7.5,10.5,13.5,16.8").split(",")]
        for sec in secs:
            render_frame((int(sec * FPS), variant))
        print("Testframes gerendert")
        return
    if only == "voice":
        folder = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("AD_VOICE_DIR", os.path.join(HERE, {"V2": "voice_v2", "V3": "voice_v3", "V6": "voice_v6", "V7": "voice_v7", "V8": "voice_v8"}.get(variant, "voice")))
        files = find_voice_files(folder)
        missing = [i + 1 for i, f in enumerate(files) if not f]
        if len(missing) == len(files):
            raise SystemExit(f"Keine Sprachdateien in {folder} gefunden (erwartet 1.mp3 … {len(files)}.mp3)")
        if missing:
            print("Hinweis: es fehlen die Clips", missing, flush=True)
        frames_dir = os.path.join(FRAMES, variant)
        if len([f for f in os.listdir(frames_dir) if f.endswith(".jpg")]) < NF:
            print("Frames fehlen, rendere zuerst …", flush=True)
            with Pool() as pool:
                list(pool.imap_unordered(render_frame, [(i, variant) for i in range(NF)], chunksize=8))
        wav = os.path.join(FRAMES, f"audio_{variant}_mit_Stimme.wav")
        print("Ton mit Stimme …", flush=True)
        build_audio(variant, wav, True, files)
        mp4 = os.path.join(OUT, f"sellcheck_tiktok_ad_{variant}_mit_Stimme.mp4")
        encode(variant, wav, mp4)
        print("Fertig:", mp4, flush=True)
        return
    if only != "audio":
        print(f"Variante {variant}: rendere {NF} Frames ({DUR} s) …", flush=True)
        with Pool() as pool:
            for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, variant) for i in range(NF)], chunksize=8)):
                if k % 150 == 0:
                    print(f"  {k}/{NF}", flush=True)
    for with_voice in ([False, True] if (variant == "A" and os.environ.get("AD_VO") == "1") else [False]):
        tag = "mit_Sprecher" if with_voice else "ohne_Sprecher"
        print(f"Ton ({tag}) …", flush=True)
        wav = os.path.join(FRAMES, f"audio_{variant}_{tag}.wav")
        build_audio(variant, wav, with_voice)
        mp4 = os.path.join(OUT, f"sellcheck_tiktok_ad_{variant}_{tag}.mp4")
        print("Encoding …", flush=True)
        encode(variant, wav, mp4)
        print("Fertig:", mp4, flush=True)
    if variant == "A":
        write_script_files()


if __name__ == "__main__":
    main()
