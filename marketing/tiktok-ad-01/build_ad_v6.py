#!/usr/bin/env python3
"""SellCheck-Ad V6 "Drei Fragen" im hellen Design (anderes Look-and-feel als die dunklen Ads A/B/V2/V3/V7).

    python3 marketing/tiktok-ad-01/build_ad_v6.py            # Frames + Video ohne Ton (nur zum Beurteilen des Bildes)
    python3 marketing/tiktok-ad-01/build_ad_v6.py poster 1,5  # einzelne Testframes bei 1 s und 5 s

Ausgabe: out/sellcheck_tiktok_ad_V6_visuell.mp4 (1080x1920, 30 fps, stumm).
Design: warmes Papierweiß mit Punktraster, Tinte, Kobaltblau, Marker-Gelb, Futura Condensed, harte Schatten.
"""
import math
import os
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

W, H, FPS, S = 1080, 1920, 30, 2
FRAMES = os.environ.get("AD_FRAMES", "/tmp/sellcheck_ad_frames")
OUT = os.path.join(HERE, "out")
VARIANT = "V6"

# Szenen (Sekunden): Hook, Fragen, Auflösung, Handlung
T1, T2, T3, T4, DUR = 0.0, 3.4, 13.4, 19.6, 23.8
NF = int(round(DUR * FPS))

BG = (245, 241, 232)
GRID = (229, 224, 209)
INK = (20, 23, 28)
BLUE = (43, 80, 255)
SUN = (255, 217, 61)
WHITE = (255, 255, 255)
GREEN = (22, 150, 92)
RED = (229, 72, 59)
AMBER = (240, 168, 30)
MUTED = (106, 108, 116)
TRACK = (226, 222, 208)
DOTC = {"Vinted": (9, 177, 186), "eBay": (54, 101, 243), "Kleinanzeigen": (134, 184, 23)}

FUT = "/System/Library/Fonts/Supplemental/Futura.ttc"
WEIGHT = {"med": 0, "bold": 2, "cond": 3, "xbold": 4}


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


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def col(c, a=255):
    return (c[0], c[1], c[2], int(clamp(a, 0, 255)))


@lru_cache(maxsize=256)
def font(size, weight):
    return ImageFont.truetype(FUT, max(4, int(round(size * S))), index=WEIGHT[weight])


class Layer:
    def __init__(self):
        self.im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

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
        self.d.polygon([(px(a), px(b)) for a, b in pts], fill=fill)

    def line(self, pts, fill, width):
        self.d.line([(px(a), px(b)) for a, b in pts], fill=fill, width=px(width), joint="curve")


@lru_cache(maxsize=1)
def background():
    im = Image.new("RGBA", (W * S, H * S), col(BG))
    d = ImageDraw.Draw(im)
    for gy in range(40, H, 60):
        for gx in range(40, W, 60):
            d.ellipse([px(gx - 2.2), px(gy - 2.2), px(gx + 2.2), px(gy + 2.2)], fill=col(GRID))
    return im


def brand(L):
    h = 64
    w, _ = LOGO.lockup_size(h * S)
    LOGO.draw_lockup(L.d, px(540) - w / 2, px(250 - h / 2), h * S, on_dark=False)


def pop(L, cx, base_y, s, size, weight, color, t, start, anchor="ms", dur=0.35):
    """Text mit Überschwingen (Grundlinie base_y)."""
    p = prog(t, start, dur)
    if p <= 0:
        return
    sc = 0.7 + 0.3 * ease_back(p)
    L.text(cx, base_y, s, size * sc, weight, col(color, 255 * clamp(p * 3)), anchor)


def marker(L, x0, x1, y0, y1, t, start, dur=0.35, color=SUN):
    """Marker-Streifen, der von links nach rechts aufgezogen wird."""
    p = ease_out(prog(t, start, dur))
    if p <= 0:
        return
    xe = x0 + (x1 - x0) * p
    L.poly([(x0 - 4, y0 + 5), (xe + 4, y0), (xe + 4, y1), (x0 - 4, y1 - 5)], col(color))


def card(L, x0, y0, x1, y1, fill=WHITE, shadow=10, r=26):
    """Karte mit Tintenkontur und hartem Schatten."""
    L.rrect(x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow, r, fill=col(INK))
    L.rrect(x0, y0, x1, y1, r, fill=col(fill), outline=col(INK), width=5)


def chip(L, cx, cy, label, dot, t, start):
    p = prog(t, start, 0.3)
    if p <= 0:
        return
    sc = 0.8 + 0.2 * ease_back(p)
    w = (L.width(label, 54, "bold") + 120) * sc
    h = 100 * sc
    ox = (1 - ease_out(p)) * 40
    card(L, cx - w / 2, cy - h / 2 + ox, cx + w / 2, cy + h / 2 + ox, WHITE, 8, r=h / 2)
    L.circle(cx - w / 2 + 48 * sc, cy + ox, 15 * sc, col(dot))
    L.text(cx - w / 2 + 80 * sc, cy + ox + 2, label, 54 * sc, "bold", col(INK), "lm")


# ------------------------------------------------------------------ Szene 1: Hook
def scene_hook(L, t):
    base = 760
    w3 = L.width("3 ", 230, "xbold")
    wf = L.width("Fragen", 230, "xbold")
    x0 = 540 - (w3 + wf) / 2
    marker(L, x0 + w3, x0 + w3 + wf, base - 168, base + 6, t, 0.35)
    p = prog(t, 0.0, 0.4)
    if p > 0:
        sc = 0.7 + 0.3 * ease_back(p)
        a = 255 * clamp(p * 3)
        L.text(x0, base, "3", 230 * sc, "xbold", col(BLUE, a), "ls")
        L.text(x0 + w3, base, "Fragen", 230 * sc, "xbold", col(INK, a), "ls")
    pop(L, 540, 905, "an alle, die auf", 62, "med", INK, t, 0.75)
    chip(L, 345, 1050, "Vinted", DOTC["Vinted"], t, 1.0)
    chip(L, 700, 1050, "eBay", DOTC["eBay"], t, 1.15)
    chip(L, 540, 1185, "Kleinanzeigen", DOTC["Kleinanzeigen"], t, 1.3)
    pop(L, 540, 1345, "verkaufen.", 62, "med", INK, t, 1.8)


# ------------------------------------------------------------------ Szene 2: drei Fragen
CARD_X0, CARD_X1, CARD_H = 100, 980, 290
CARD_TOPS = (430, 770, 1110)
QUESTIONS = (
    ("Wie viele Verkäufe", "hattest du dieses Jahr?"),
    ("Wie viel Umsatz davon", "auf welcher Plattform?"),
    ("Und was davon ist", "wirklich Gewinn?"),
)
Q_START = (0.2, 3.5, 6.8)


def fit(L, lines, maxw, size=56):
    while max(L.width(s, size, "bold") for s in lines) > maxw and size > 30:
        size -= 1
    return size


def question_face(L, i, x0, y0, x1, y1, active_k):
    """Kartenvorderseite: Nummer, Frage, großes Fragezeichen."""
    cy = (y0 + y1) / 2
    L.circle(x0 + 72, cy, 44, col(BLUE))
    L.text(x0 + 72, cy + 4, str(i + 1), 62, "xbold", col(WHITE), "mm")
    lines = QUESTIONS[i]
    size = fit(L, lines, 610, 62)
    ty = cy - size * 0.62
    for j, s in enumerate(lines):
        L.text(x0 + 140, ty + j * size * 1.22, s, size, "bold", col(INK), "lt")
    L.text(x1 - 46, cy + 4, "?", 120, "xbold", col(BLUE), "mm")
    if i == 2 and active_k > 0:
        # "wirklich" bekommt den Marker (hinter dem Text, deshalb nachträglich nicht möglich: Marker daher schmal darunter)
        wx = x0 + 140
        wl = L.width("wirklich", size, "bold")
        L.poly([(wx, ty + size * 1.22 + size * 0.98), (wx + wl * active_k, ty + size * 1.22 + size * 0.98 - 3),
                (wx + wl * active_k, ty + size * 1.22 + size * 1.08), (wx, ty + size * 1.22 + size * 1.08 + 2)], col(BLUE))


def scene_questions(L, t):
    for i in range(3):
        st = Q_START[i]
        p = prog(t, st, 0.5)
        if p <= 0:
            continue
        top = CARD_TOPS[i]
        ox = (1 - ease_back(p)) * 900
        x0, x1 = CARD_X0 + ox, CARD_X1 + ox
        nxt = Q_START[i + 1] if i < 2 else 99
        k = prog(t, nxt, 0.3) if i < 2 else 0.0
        fill = mix(SUN, WHITE, k)
        card(L, x0, top, x1, top + CARD_H, fill)
        question_face(L, i, x0, top, x1, top + CARD_H, ease_out(prog(t, st + 0.9, 0.5)))


# ------------------------------------------------------------------ Szene 3: Antworten
FLIP_T = (2.6, 3.4, 4.2)
ANS_TOPS = (500, 810, 1120)


def answer_face(L, i, x0, y0, x1, y1, t, tstart):
    cy = (y0 + y1) / 2
    L.circle(x0 + 86, cy, 52, col(GREEN))
    L.line([(x0 + 64, cy + 2), (x0 + 82, cy + 22), (x0 + 112, cy - 20)], col(WHITE), 10)
    k = ease_out(prog(t, tstart + 0.3, 0.7))
    if i == 0:
        L.text(x0 + 170, y0 + 62, "Verkäufe dieses Jahr", 38, "med", col(MUTED), "lm")
        L.text(x0 + 170, cy + 42, str(int(round(47 * k))), 150, "xbold", col(INK), "lm")
    elif i == 1:
        rows = [("Vinted", 27, 30, "27 / 30 Verkäufe", DOTC["Vinted"]), ("eBay", 1850, 2000, "1.850 / 2.000 €", DOTC["eBay"])]
        for r, (name, v, lim, label, dot) in enumerate(rows):
            ry = y0 + 82 + r * 102
            L.circle(x0 + 182, ry, 13, col(dot))
            L.text(x0 + 208, ry, name, 40, "bold", col(INK), "lm")
            L.text(x1 - 46, ry, label, 34, "med", col(MUTED), "rm")
            bx0, bx1 = x0 + 170, x1 - 46
            L.rrect(bx0, ry + 30, bx1, ry + 50, 10, fill=col(TRACK))
            L.rrect(bx0, ry + 30, bx0 + (bx1 - bx0) * min(1, v / lim) * k, ry + 50, 10, fill=col(AMBER))
    else:
        L.text(x0 + 170, y0 + 62, "Gewinn nach Einkauf", 38, "med", col(MUTED), "lm")
        val = f"{842.5 * k:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        L.text(x0 + 170, cy + 42, val + " €", 118, "xbold", col(GREEN), "lm")


def scene_answers(L, t):
    # Überschrift: erst "Keine Ahnung?", dann "SellCheck antwortet."
    if t < 2.2:
        w = L.width("Keine Ahnung?", 130, "xbold")
        marker(L, 540 - w / 2, 540 + w / 2, 410 - 96, 410 + 8, t, 0.25)
        pop(L, 540, 410, "Keine Ahnung?", 130, "xbold", INK, t, 0.0)
    else:
        wa = L.width("SellCheck ", 100, "xbold")
        wb = L.width("antwortet.", 100, "xbold")
        x0 = 540 - (wa + wb) / 2
        p = prog(t, 2.2, 0.35)
        sc = 0.75 + 0.25 * ease_back(p)
        a = 255 * clamp(p * 3)
        L.text(x0, 410, "SellCheck", 100 * sc, "xbold", col(BLUE, a), "ls")
        L.text(x0 + wa, 410, "antwortet.", 100 * sc, "xbold", col(INK, a), "ls")
    for i in range(3):
        top = ANS_TOPS[i]
        x0, x1 = CARD_X0, CARD_X1
        fp = prog(t, FLIP_T[i], 0.4)
        sx = abs(math.cos(math.pi * fp)) if 0 < fp < 1 else 1.0
        showing_answer = fp >= 0.5
        cx = (x0 + x1) / 2
        hw = (x1 - x0) / 2 * max(sx, 0.02)
        fill = mix(WHITE, (233, 244, 236), 1.0) if showing_answer else WHITE
        card(L, cx - hw, top, cx + hw, top + CARD_H, fill)
        if sx > 0.6:
            if showing_answer:
                answer_face(L, i, cx - hw, top, cx + hw, top + CARD_H, t, FLIP_T[i])
            else:
                question_face(L, i, cx - hw, top, cx + hw, top + CARD_H, 1.0)
    if t > FLIP_T[2] + 0.5:
        pop(L, 540, 1470, "Beispieldaten", 28, "med", MUTED, t, FLIP_T[2] + 0.5, dur=0.25)


# ------------------------------------------------------------------ Szene 4: Handlung
def scene_cta(L, t):
    p = prog(t, 0.0, 0.45)
    sc = 0.75 + 0.25 * ease_back(p)
    h = 128 * sc
    w, _ = LOGO.lockup_size(h * S)
    tmp = Image.new("RGBA", L.im.size, (0, 0, 0, 0))
    LOGO.draw_lockup(ImageDraw.Draw(tmp), px(540) - w / 2, px(560 - h / 2), h * S, on_dark=False)
    tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * clamp(p * 3))))
    L.im.alpha_composite(tmp)
    wt = L.width("testen.", 160, "xbold")
    marker(L, 540 - wt / 2, 540 + wt / 2, 1040 - 120, 1040 + 6, t, 0.75)
    pop(L, 540, 880, "Jetzt gratis", 160, "xbold", INK, t, 0.4)
    pop(L, 540, 1040, "testen.", 160, "xbold", BLUE, t, 0.55)
    pp = prog(t, 1.1, 0.4)
    if pp > 0:
        pulse = 1 + 0.025 * math.sin(max(0, t - 1.5) * 9)
        sc2 = (0.85 + 0.15 * ease_back(pp)) * pulse
        bw, bh = 800 * sc2, 128 * sc2
        L.rrect(540 - bw / 2 + 10, 1190 - bh / 2 + 10, 540 + bw / 2 + 10, 1190 + bh / 2 + 10, bh / 2, fill=col(INK))
        L.rrect(540 - bw / 2, 1190 - bh / 2, 540 + bw / 2, 1190 + bh / 2, bh / 2, fill=col(BLUE), outline=col(INK), width=5)
        lw = L.width("Einfach unten antippen", 54 * sc2, "bold")
        L.text(540 - 30, 1196, "Einfach unten antippen", 54 * sc2, "bold", col(WHITE, 255 * clamp(pp * 3)), "mm")
        ax = 540 - 30 + lw / 2 + 44
        L.line([(ax, 1176), (ax, 1214)], col(WHITE), 9)
        L.line([(ax - 18, 1198), (ax, 1216), (ax + 18, 1198)], col(WHITE), 9)
    pop(L, 540, 1350, "Unabhängig von den genannten Plattformen.", 28, "med", MUTED, t, 1.7, dur=0.3)
    pop(L, 540, 1392, "Orientierung, keine Steuer- oder Rechtsberatung.", 28, "med", MUTED, t, 1.8, dur=0.3)


SCENES = [(T1, T2, scene_hook), (T2, T3, scene_questions), (T3, T4, scene_answers), (T4, DUR + 1, scene_cta)]


def render_frame(i):
    t = i / FPS
    im = background().copy()
    L0 = Layer()
    brand(L0)
    im.alpha_composite(L0.im)
    for start, end, fn in SCENES:
        if start <= t < end:
            L = Layer()
            fn(L, t - start)
            im.alpha_composite(L.im)
            break
    # Marker-Wischer an den Szenengrenzen (deckt den Szenenwechsel ab)
    for tb in (T2, T3, T4):
        p = prog(t, tb - 0.22, 0.44)
        if 0 < p < 1:
            L = Layer()
            if p < 0.5:
                xe = W * ease_out(p * 2)
                L.d.rectangle([0, 0, px(xe), H * S], fill=col(SUN))
            else:
                xs = W * ease_out((p - 0.5) * 2)
                L.d.rectangle([px(xs), 0, W * S, H * S], fill=col(SUN))
            im.alpha_composite(L.im)
    im = im.convert("RGB").reduce(S)
    path = os.path.join(FRAMES, VARIANT, f"f_{i:05d}.jpg")
    im.save(path, quality=95, subsampling=0)
    return i


def silent_wav(path, seconds):
    n = int(seconds * 44100)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack("<hh", 0, 0) * n)


def encode(wav, mp4):
    enc = os.path.join(FRAMES, "encode")
    src = os.path.join(HERE, "encode.swift")
    if not os.path.exists(enc) or os.path.getmtime(enc) < os.path.getmtime(src):
        print("Swift-Encoder bauen …", flush=True)
        subprocess.run(["swiftc", "-O", "-swift-version", "5", "-suppress-warnings", src, "-o", enc], check=True)
    subprocess.run([enc, os.path.join(FRAMES, VARIANT), str(FPS), str(NF), wav, mp4], check=True)


def main():
    os.makedirs(os.path.join(FRAMES, VARIANT), exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "poster":
        secs = [float(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "0.4,1.5,3.8,7.0,11.0,14.5,16.5,18.5,21.5").split(",")]
        for sec in secs:
            render_frame(int(sec * FPS))
        print("Testframes gerendert")
        return
    print(f"V6: rendere {NF} Frames ({DUR} s) …", flush=True)
    with Pool() as pool:
        for k, _ in enumerate(pool.imap_unordered(render_frame, range(NF), chunksize=8)):
            if k % 150 == 0:
                print(f"  {k}/{NF}", flush=True)
    wav = os.path.join(FRAMES, "audio_V6_stumm.wav")
    silent_wav(wav, DUR + 0.2)
    mp4 = os.path.join(OUT, "sellcheck_tiktok_ad_V6_visuell.mp4")
    encode(wav, mp4)
    print("Fertig:", mp4, flush=True)


if __name__ == "__main__":
    main()
