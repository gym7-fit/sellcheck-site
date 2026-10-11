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

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo-final"))
import sellcheck_logo as LOGO  # echtes SellCheck-Logo (Variante 6B)

W, H, FPS, S = 1080, 1920, 30, 2          # S = Supersampling-Faktor
# Variante: A und B (Hook-Tests der ersten Ad), V2 = "Frist"-Version (Überblick, Ende Januar, Nutzen, Handlung)
VAR = sys.argv[1].upper() if len(sys.argv) > 1 and sys.argv[1].upper() in ("A", "B", "V2", "V3", "V7") else os.environ.get("AD_VARIANT", "A")
os.environ["AD_VARIANT"] = VAR  # damit Worker-Prozesse dieselbe Variante nutzen
# Dauer je Szene = Basiszeit der Animation x Streckung
V2LIKE = VAR in ("V2", "V3", "V7")
if VAR == "V2":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 2.4, 2: 4.0, 3: 7.9, 4: 3.4}
    TARGET = {1: 2.85, 2: 6.85, 3: 8.05, 4: 4.25}  # Sekunden je Szene, abgestimmt auf die Sprechzeiten
    SLOW = {k: TARGET[k] / BASE[k] for k in KEYS}
elif VAR == "V3":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 2.4, 2: 4.0, 3: 7.9, 4: 3.4}
    TARGET = {1: 2.6, 2: 8.2, 3: 8.1, 4: 4.1}  # nach Messung der Sprechzeiten (Clips 2,4 / 8,0 / 8,0 / 3,9 s)
    SLOW = {k: TARGET[k] / BASE[k] for k in KEYS}
elif VAR == "V7":
    KEYS = (1, 2, 3, 4)
    BASE = {1: 2.4, 2: 4.0, 3: 7.9, 4: 3.4}
    TARGET = {1: 4.1, 2: 5.6, 3: 8.7, 4: 4.1}  # nach Messung der Sprechzeiten (Clips 3,9 / 5,2 / 8,4 / 3,7 s)
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
    S3_B, CAP2_T = 6.0, 1.4
DEMO_SHIFT = 1.4 if VAR == "V3" else 0.0  # Karte/Ampel erst, wenn "und siehst pro Plattform" gesprochen wird


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
        cx, cy = 510, y0 + i * pitch
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
    sz = [100 if len(c) <= 12 else 80 for c in caps]
    if t < CAP2_T:
        pop_text(L, 540, 400, caps[0], sz[0], "heavy", PAPER, t, 0.0)
    elif t < S3_B:
        pop_text(L, 540, 400, caps[1], sz[1], "heavy", LIME, t, CAP2_T)
    else:
        pop_text(L, 540, 400, caps[2], sz[2], "heavy", PAPER, t, S3_B)

    # Beat a1: Ablagefläche, Datei landet darin (nichts überlagert anderen Inhalt)
    zone_a = 1.0 - ease_out(prog(t, 1.45 + DEMO_SHIFT, 0.25))
    if zone_a > 0:
        a = 255 * zone_a
        landed = t >= 0.85
        z0, z1 = 110, 910
        L.rrect(z0, 520, z1, 1080, 44, fill=col(INK2, a), outline=col(LIME if landed else (74, 82, 94), a), width=4)
        # Pfeil nach oben und Hinweis
        L.line([(510, 640), (510, 590)], col(MUTED, a), 8)
        L.line([(486, 612), (510, 588), (534, 612)], col(MUTED, a), 8)
        L.text(510, 700, "CSV hier ablegen", 40, "medium", col(MUTED, a), "mm")
        fp = prog(t, 0.1, 0.7)
        if fp > 0:
            fy = 380 + ease_out(fp) * (860 - 380)
            sc = 1.0 + (0.06 * math.sin(clamp((t - 0.8) / 0.25) * math.pi) if t >= 0.8 else 0.0)
            pill(L, 510, fy, 640 * sc, 104 * sc, col(PAPER, a))
            # kleines Dokument-Symbol
            L.rrect(510 - 290 * sc, fy - 26 * sc, 510 - 252 * sc, fy + 26 * sc, 6, fill=col(INK, a))
            L.text(510 - 230 * sc, fy, "eBay_Transaktionen.csv", 34 * sc, "bold", col(INK, a), "lm")
        if landed:
            lp = prog(t, 0.9, 0.3)
            check_circle(L, 510 - 130, 990, 24 * (0.6 + 0.4 * ease_back(lp)))
            L.text(510 - 90, 990, "Datei gelesen", 40, "heavy", col(PAPER, a * clamp(lp * 3)), "lm")

    # Beat a2: Karte mit Ampel
    slide_out = ease_out(prog(t, S3_B - 0.05, 0.45))
    card_p = ease_out(prog(t, 1.55 + DEMO_SHIFT, 0.55))
    if slide_out < 1.0 and card_p > 0:
        ox = -1100 * slide_out
        oy = (1 - card_p) * 700
        x0, y0, x1, y1 = 80 + ox, 500 + oy, 940 + ox, 1420 + oy
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


def scene_cta(L, t):
    p = prog(t, 0.0, 0.5)
    sc = 0.75 + 0.25 * ease_back(p)
    h = 170 * sc
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
    if VAR in ("V3", "V7"):
        pop_text(L, 540, 1290, "Unabhängig von den genannten Plattformen.", 28, "medium", MUTED, t, 1.6, dur=0.3)
        pop_text(L, 540, 1330, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "medium", MUTED, t, 1.7, dur=0.3)
    else:
        pop_text(L, 540, 1290 if V2LIKE else 1250, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "medium", MUTED, t, 1.6, dur=0.3)


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


SCENES = {
    "A": [(1, scene_hook_a), (2, scene_problem_a)],
    "B": [(1, scene_hook_b), (2, scene_problem_b)],
    "V2": [(1, scene_v2_hook), (2, scene_v2_deadline)],
    "V3": [(1, scene_v3_hook), (2, scene_v2_deadline)],
    "V7": [(1, scene_v7_hook), (2, scene_v7_profit)],
}
COMMON = [(3, scene_demo), (4, scene_cta)] if V2LIKE else [(3, scene_demo), (4, scene_benefits), (5, scene_cta)]


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
    if variant == "V7":
        return [
            (at(1, 0.05), "[curious] Du bist Reseller, oder willst wissen, was du WIRKLICH verdienst?", START[2]),
            (at(2, 0.05), "Dann zählt nicht dein UMSATZ. Sondern, was dir nach dem Einkauf ÜBRIG bleibt.", START[3]),
            (at(3, 0.05), "Und weil du viel umsetzt, bist du schnell an der Grenze: DREIßIG Verkäufe oder ZWEItausend Euro, pro Plattform. SellCheck zeigt dir BEIDES.", START[4]),
            (at(4, -0.10), "SellCheck. Jetzt GRATIS testen. Einfach unten antippen.", DUR - 0.05),
        ]
    if variant == "V3":
        return [
            (at(1, 0.05), "[curious] Du verkaufst viel auf Vinted und Co?", START[2]),
            (at(2, 0.05), "Dann solltest du wissen: Plattformen melden dich bis Ende JANUAR, ab DREIßIG Verkäufen oder ZWEItausend Euro, an die Steuerbehörde.", START[3]),
            (at(3, 0.05), "Mit SellCheck lädst du einfach deine Verkäufe hoch und siehst pro Plattform, wie NAH du an der Grenze bist. Und was dir WIRKLICH bleibt.", START[4]),
            (at(4, -0.10), "SellCheck. Jetzt GRATIS testen. Einfach unten antippen.", DUR - 0.05),
        ]
    if variant == "V2":
        return [
            (at(1, 0.05), "Hast du noch den Überblick über all deine Verkäufe?", START[2]),
            (at(2, 0.05), "Ende Januar melden Plattformen dein Jahr an die Steuerbehörde. Ab dreißig Verkäufen oder zweitausend Euro.", START[3]),
            (at(3, 0.05), "Lade deine Verkäufe hoch.", at(3, 1.5)),
            (at(3, 1.50), "Du siehst sofort, wie nah du pro Plattform an der Grenze bist.", at(3, S3_B)),
            (at(3, S3_B - 0.55), "Und was dir nach Abzug wirklich bleibt.", START[4]),
            (at(4, -0.10), "SellCheck. Jetzt gratis testen. Einfach unten antippen.", DUR - 0.05),
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

    add(sfx, at(3, 0.8), tone(180, 0.18, "sine", 8.0, 60), 0.5)    # Datei landet
    ding(at(3, 0.95), 784.0)                                           # "Datei gelesen"
    for i in range(4):
        tick(at(3, 2.0 + DEMO_SHIFT + i * 0.28 + 0.15), 1100 + i * 120)
    blip_down(at(3, 4.15 + DEMO_SHIFT))
    ding(at(3, S3_B + 1.6), 659.25)                                 # Summe ist oben angekommen
    if variant not in ("V2", "V3", "V7"):
        for i, f in enumerate((523.25, 659.25, 783.99)):
            ding(at(4, 0.35 + i * 0.4), f)
    cta = 4 if variant in ("V2", "V3", "V7") else 5
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


def main():
    variant = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
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
        folder = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("AD_VOICE_DIR", os.path.join(HERE, {"V2": "voice_v2", "V3": "voice_v3", "V7": "voice_v7"}.get(variant, "voice")))
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
