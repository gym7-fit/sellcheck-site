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

W, H, FPS, S = 1080, 1920, 30, 2          # S = Supersampling-Faktor
DUR = 18.5
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
T_S1, T_S2, T_S3, T_S4, T_S5 = 0.0, 2.6, 5.6, 12.6, 15.4
S3_B = 4.0  # Beat b (Report) beginnt 4,0 s nach Szenenstart


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
    """Marke von Sekunde 0 an (kleines Logo + Wortmarke), mittig oben in der Safe Zone."""
    y = 250
    wm_w = L.width("SellCheck", 46, "heavy")
    total = 56 + 16 + wm_w
    x0 = 540 - total / 2
    L.rrect(x0, y - 28, x0 + 56, y + 28, 15, fill=col(LIME))
    L.line([(x0 + 15, y + 2), (x0 + 25, y + 13), (x0 + 42, y - 11)], col(INK), 7)
    L.text(x0 + 56 + 16, y + 16, "Sell", 46, "heavy", col(PAPER), "ls")
    sell_w = L.width("Sell", 46, "heavy")
    L.text(x0 + 56 + 16 + sell_w, y + 16, "Check", 46, "heavy", col(LIME), "ls")


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
    # Titelzeile je nach Beat
    if t < 1.9:
        pop_text(L, 540, 400, "Datei rein.", 100, "heavy", PAPER, t, 0.0)
    elif t < S3_B:
        pop_text(L, 540, 400, "Ampel an.", 100, "heavy", LIME, t, 1.9)
    else:
        pop_text(L, 540, 400, "Report raus.", 100, "heavy", PAPER, t, S3_B)

    # Beat a: Karte mit Ampel
    slide_out = ease_out(prog(t, S3_B - 0.05, 0.45))
    if slide_out < 1.0:
        ox = -1100 * slide_out
        cp = ease_out(prog(t, 0.15, 0.55))
        oy = (1 - cp) * 700
        x0, y0, x1, y1 = 80 + ox, 500 + oy, 940 + ox, 1420 + oy
        red_hit = t >= 3.05
        L.rrect(x0, y0, x1, y1, 44, fill=col(PAPER), outline=col(RED) if red_hit and (t % 0.5) < 0.3 and t < 3.9 else None, width=6)
        L.text(x0 + 50, y0 + 62, "Meldegrenzen 2026", 46, "heavy", col(INK), "lm")
        pill(L, x1 - 130, y0 + 62, 190, 50, col(LIME))
        L.text(x1 - 130, y0 + 62, "Ampel", 28, "heavy", col(INK), "mm")
        L.text(x1 - 50, y1 - 34, "Beispieldaten", 24, "medium", col(DARKMUTED), "rm")
        # Datei-Chip fällt ein
        fp = prog(t, 0.25, 0.5)
        if 0 < fp < 1:
            fy = y0 - 260 + ease_out(fp) * 330
            pill(L, 540 + ox, fy, 560, 78, col(INK2))
            L.text(540 + ox, fy, "eBay_Transaktionen.csv", 32, "bold", col(PAPER), "mm")
        for i, (name, v, lim, label, money_mode) in enumerate(ROWS):
            st = 0.9 + i * 0.28
            rp = prog(t, st, 0.35)
            if rp <= 0:
                continue
            ry = y0 + 150 + i * 182 + (1 - ease_out(rp)) * 30
            a = 255 * clamp(rp * 3)
            L.circle(x0 + 62, ry + 20, 14, col(DOT[name], a))
            L.text(x0 + 90, ry + 20, name, 42, "bold", col(INK, a), "lm")
            fillp = ease_out(prog(t, st + 0.15, 0.8))
            val = v * fillp
            vt = f"{money(val)} / {money(lim)} €" if money_mode else f"{int(round(val))} / {lim} Verkäufe"
            L.text(x1 - 50, ry + 20, vt, 36, "medium", col(DARKMUTED, a), "rm")
            bx0, bx1, by = x0 + 50, x1 - 50, ry + 62
            L.rrect(bx0, by, bx1, by + 30, 15, fill=col(TRACK, a))
            ratio = min(1.0, v / lim) * fillp
            if ratio > 0.01:
                final = min(1.0, v / lim)
                colr = RED if final >= 1 else (AMBER if final >= 0.8 else GREEN)
                L.rrect(bx0, by, bx0 + (bx1 - bx0) * ratio, by + 30, 15, fill=col(colr, a))
            if fillp > 0.95:
                final = min(1.0, v / lim)
                if final >= 1:
                    txt, c2 = "Meldegrenze erreicht", RED
                elif final >= 0.8:
                    txt, c2 = "Fast erreicht", (176, 112, 0)
                else:
                    txt, c2 = "Alles im grünen Bereich", DEEPGREEN
                L.text(bx0, by + 64, txt, 31, "bold", col(c2, a), "lm")

    # Beat b: Report-Blatt
    sp = ease_out(prog(t, S3_B + 0.1, 0.6))
    if sp > 0:
        ox = (1 - sp) * 1100
        x0, y0, x1, y1 = 170 + ox, 500, 910 + ox, 1420
        L.rrect(x0, y0, x1, y1, 30, fill=col(PAPER))
        L.text(x0 + 46, y0 + 70, "Steuer-Report 2026", 46, "heavy", col(INK), "lm")
        L.text(x0 + 46, y0 + 128, "Ausfüllhilfe Anlage EÜR", 32, "medium", col(DARKMUTED), "lm")
        pill(L, x1 - 46 - 125, y0 + 128, 250, 50, col(LIME))
        L.text(x1 - 46 - 125, y0 + 128, "Druckfertig", 28, "heavy", col(INK), "mm")
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
    sc = 0.6 + 0.4 * ease_back(p)
    size = 190 * sc
    L.rrect(540 - size / 2, 520 - size / 2, 540 + size / 2, 520 + size / 2, size * 0.27, fill=col(LIME, 255 * clamp(p * 3)))
    cx, cy = 540, 520
    k = size / 190
    L.line([(cx - 44 * k, cy + 4 * k), (cx - 14 * k, cy + 36 * k), (cx + 48 * k, cy - 34 * k)], col(INK), 22 * k)
    pop_segments(L, 540, 860, [("Sell", 128, "heavy", PAPER), ("Check", 128, "heavy", LIME)], t, 0.25)
    pop_text(L, 540, 1000, "Gratis testen.", 96, "heavy", PAPER, t, 0.6)
    pp = prog(t, 1.0, 0.4)
    if pp > 0:
        pulse = 1 + 0.03 * math.sin(max(0, t - 1.4) * 9)
        pill(L, 540, 1160, 640 * pulse * (0.85 + 0.15 * ease_back(pp)), 120 * pulse, col(LIME, 255 * clamp(pp * 3)))
        L.text(540 - 30, 1160, "Link unten antippen", 46, "heavy", col(INK, 255 * clamp(pp * 3)), "mm")
        ax, ay = 540 + 255, 1160
        L.line([(ax, ay - 14), (ax, ay + 16)], col(INK, 255 * clamp(pp * 3)), 8)
        L.line([(ax - 14, ay + 3), (ax, ay + 18), (ax + 14, ay + 3)], col(INK, 255 * clamp(pp * 3)), 8)
    pop_text(L, 540, 1330, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "medium", MUTED, t, 1.6, dur=0.3)


SCENES = {
    "A": [(T_S1, T_S2, scene_hook_a), (T_S2, T_S3, scene_problem_a)],
    "B": [(T_S1, T_S2, scene_hook_b), (T_S2, T_S3, scene_problem_b)],
}
COMMON = [(T_S3, T_S4, scene_demo), (T_S4, T_S5, scene_benefits), (T_S5, DUR + 1, scene_cta)]


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
    for start, end, fn in scenes:
        if start <= t < end:
            L = Layer()
            lt = t - start
            fn(L, lt)
            f = min(clamp(lt / 0.08), clamp((end - t) / 0.08))
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


def build_audio(variant, path):
    n = int(SR * DUR)
    mix = [0.0] * n
    rnd = random.Random(3)

    def add(t0, samples, gain=1.0):
        s0 = int(t0 * SR)
        for k, v in enumerate(samples):
            j = s0 + k
            if 0 <= j < n:
                mix[j] += v * gain

    def tone(freq, dur, kind="sine", decay=6.0, freq_end=None):
        out = []
        ph = 0.0
        m = int(dur * SR)
        for k in range(m):
            x = k / m
            f = freq if freq_end is None else freq + (freq_end - freq) * x
            ph += 2 * math.pi * f / SR
            if kind == "sine":
                v = math.sin(ph)
            elif kind == "saw":
                v = 2 * ((ph / (2 * math.pi)) % 1) - 1
            else:
                v = 1.0 if math.sin(ph) > 0 else -1.0
            out.append(v * math.exp(-decay * x) * min(1.0, k / 60.0))
        return out

    def noise(dur, decay=8.0, hp=0.0):
        out = []
        prev = 0.0
        for k in range(int(dur * SR)):
            x = k / (dur * SR)
            v = rnd.uniform(-1, 1)
            if hp:
                v, prev = v - prev * hp, v
            out.append(v * math.exp(-decay * x))
        return out

    def whoosh(dur=0.35):
        out = []
        lp = 0.0
        m = int(dur * SR)
        for k in range(m):
            x = k / m
            c = 0.02 + 0.5 * x
            lp += c * (rnd.uniform(-1, 1) - lp)
            env = math.sin(math.pi * x) ** 1.5
            out.append(lp * env * 2.2)
        return out

    beat = 0.5  # 120 bpm
    # Musikbett
    bass_notes = [55.0, 55.0, 43.65, 49.0]
    t = 0.0
    bar = 0
    while t < DUR:
        for b in range(4):
            tb = t + b * beat
            if tb >= DUR:
                break
            vol = 0.55 if tb < T_S2 else 0.8
            add(tb, tone(120, 0.22, "sine", 9.0, 45), 0.9 * vol)       # Kick
            add(tb + beat / 2, noise(0.05, 14.0, 0.9), 0.22 * vol)    # Hi-Hat
            if tb >= T_S3:
                add(tb + beat / 2, tone(bass_notes[bar % 4] * 2, 0.2, "sine", 6.0), 0.18)
        # Bass je Takt
        add(t, tone(bass_notes[bar % 4], 1.9, "sine", 2.2), 0.5)
        if t >= T_S3:  # Arpeggio ab der Demo
            arp = [220.0, 261.63, 329.63, 392.0] if bar % 2 == 0 else [196.0, 246.94, 293.66, 392.0]
            for q in range(8):
                add(t + q * beat / 2, tone(arp[q % 4] * 2, 0.22, "sine", 7.0), 0.07)
        t += 4 * beat
        bar += 1

    def tick(t0, f=1500):
        add(t0, tone(f, 0.05, "sine", 10.0), 0.35)

    def pop(t0, f=520):
        add(t0, tone(f, 0.11, "sine", 7.0, f * 1.6), 0.45)

    def ding(t0, f):
        add(t0, tone(f, 0.5, "sine", 4.0), 0.4)
        add(t0, tone(f * 2, 0.35, "sine", 6.0), 0.12)

    def alarm(t0):
        add(t0, tone(95, 0.28, "saw", 5.0), 0.5)

    # Übergänge
    for ts in (T_S2, T_S3, T_S4, T_S5):
        add(ts - 0.15, whoosh(0.3), 0.5)
    add(T_S3 + S3_B - 0.1, whoosh(0.35), 0.5)

    if variant == "A":
        add(0.0, whoosh(0.25), 0.5)
        for tt in (0.9, 1.25, 1.6):
            tick(T_S1 + tt)
        alarm(T_S1 + 1.65)
        for i in range(4):
            pop(T_S2 + 0.55 + i * 0.2, 480 + i * 60)
    else:
        add(0.0, whoosh(0.25), 0.5)
        for i in range(4):
            pop(T_S1 + 0.9 + i * 0.22, 480 + i * 60)
        pop(T_S2 + 0.0, 640)
        pop(T_S2 + 0.18, 720)

    add(T_S3 + 0.3, tone(180, 0.18, "sine", 8.0, 60), 0.7)         # Datei landet
    for i in range(4):
        tick(T_S3 + 0.9 + i * 0.28 + 0.15, 1100 + i * 120)
    alarm(T_S3 + 3.05)
    for i, f in enumerate((523.25, 659.25, 783.99)):
        ding(T_S4 + 0.35 + i * 0.4, f)
    add(T_S3 + S3_B + 0.7, whoosh(0.9), 0.35)
    ding(T_S5 + 0.9, 523.25)
    ding(T_S5 + 1.0, 659.25)
    ding(T_S5 + 1.1, 783.99)
    ding(T_S5 + 1.2, 1046.5)

    peak = max(abs(v) for v in mix) or 1.0
    scale = 0.8 / peak
    fade = int(0.35 * SR)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        buf = bytearray()
        for k, v in enumerate(mix):
            if k > n - fade:
                v *= (n - k) / fade
            s = int(max(-1.0, min(1.0, v * scale)) * 32767)
            buf += struct.pack("<hh", s, s)
        w.writeframes(bytes(buf))


# ------------------------------------------------------------------ Main
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
    print(f"Variante {variant}: rendere {NF} Frames …", flush=True)
    with Pool() as pool:
        for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, variant) for i in range(NF)], chunksize=8)):
            if k % 100 == 0:
                print(f"  {k}/{NF}", flush=True)
    wav = os.path.join(FRAMES, f"audio_{variant}.wav")
    print("Ton …", flush=True)
    build_audio(variant, wav)
    mp4 = os.path.join(OUT, f"sellcheck_tiktok_ad_{variant}.mp4")
    enc = os.path.join(FRAMES, "encode")
    if not os.path.exists(enc) or os.path.getmtime(enc) < os.path.getmtime(os.path.join(HERE, "encode.swift")):
        print("Swift-Encoder bauen …", flush=True)
        subprocess.run(["swiftc", "-O", "-swift-version", "5", "-suppress-warnings", os.path.join(HERE, "encode.swift"), "-o", enc], check=True)
    print("Encoding …", flush=True)
    subprocess.run([enc, os.path.join(FRAMES, variant), str(FPS), str(NF), wav, mp4], check=True)
    print("Fertig:", mp4)


if __name__ == "__main__":
    main()
