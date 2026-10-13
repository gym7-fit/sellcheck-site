"""Musik für das SellCheck-Corporate-Video, Version 2: auf das Bild gerechnet.

Anders als ein fertiger Track ist diese Musik Ton für Ton auf dem Raster des Videos gebaut
(120 bpm, Schlag = 0,5 s, Takt = 2 s). Jede Texteinblendung im Bild bekommt ihren Schlag auf die
Millisekunde, weil beide aus denselben Zeitpunkten kommen (siehe CUES).

Werkzeuge: numpy/scipy für die Klangerzeugung (Sägezähne mit Überabtastung, Filterhüllkurven,
additives Klavier, Schlagzeug aus Sinus und Rauschen), Spotifys pedalboard für Hall, Kompressor und
Begrenzer. Tonart d-Moll, Akkorde Dm – B – F – C, Finale B – C – F (Auflösung nach Dur).

    .venv/bin/python corporate_music2.py out.wav      # rendert 49 s Stereo, 44,1 kHz, 16 Bit
"""
import sys
import wave

import numpy as np
import pedalboard as pb
from scipy import signal

SR = 44100
BPM = 120
BEAT = 60.0 / BPM
BAR = BEAT * 4
DUR = 49.0
TAIL = 3.0
rng = np.random.default_rng(11)

# ------------------------------------------------------------------ Zeitpunkte aus dem Bild
# Alle Werte sind Sekunden im Video. Sie entsprechen den Einsatzzeiten in build_corporate.py.
CUES = {
    "hook_slams": [0.0, 1.0, 2.0],            # "Vier Plattformen." / "Vier Zähler." / "Kein Überblick."
    "problem_title": 4.0,                      # "Jede Plattform zählt getrennt."
    "problem_cards": [5.0, 5.5, 6.0, 6.5],     # vier Plattform-Karten
    "problem_banner": [8.0, 8.5],              # "30 Verkäufe oder 2.000 € im Jahr." / Zusatzzeile
    "loesung_logo": 12.0,
    "loesung_lines": [13.0, 13.5],             # "Alles an" / "einem Ort."
    "loesung_card": 15.0,                      # Übersichtskarte
    "loesung_bullets": [16.0, 16.5, 17.0],
    "produkt_cuts": [22.0, 28.0, 33.0],        # drei Bildschirmaufnahmen
    "produkt_callouts": [23.5, 29.5, 34.5],    # farbige Markierung im Bild
    "vertrauen_lines": [38.0, 39.5, 41.0],
    "abbinder_logo": 44.0,
    "abbinder_lines": [45.0, 45.5],            # "Check, was" / "wirklich bleibt."
    "abbinder_pill": 46.5,                     # "Kostenlos, ohne Anmeldung"
}

# ------------------------------------------------------------------ Grundbausteine
MIDI = {"D2": 38, "Bb1": 34, "F2": 41, "C2": 36}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tarr(n):
    return np.arange(n) / SR


def sos(kind, fc, order=2):
    return signal.butter(order, fc, btype=kind, fs=SR, output="sos")


def lp(x, fc, order=2):
    return signal.sosfilt(sos("low", min(fc, SR * 0.45), order), x)


def hp(x, fc, order=2):
    return signal.sosfilt(sos("high", fc, order), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


_LEVELS = np.geomspace(150.0, 14000.0, 9)
_SOS = [sos("low", f, 2) for f in _LEVELS]


def lp_sweep(x, fc):
    """Tiefpass mit zeitlich veränderlicher Grenzfrequenz (Überblendung zwischen festen Filterstufen)."""
    n = len(x)
    Y = np.stack([signal.sosfilt(s, x) for s in _SOS])
    pos = (np.log(np.clip(fc, _LEVELS[0], _LEVELS[-1])) - np.log(_LEVELS[0])) / (np.log(_LEVELS[-1]) - np.log(_LEVELS[0])) * (len(_LEVELS) - 1)
    pos = np.clip(pos, 0, len(_LEVELS) - 1 - 1e-6)
    i = pos.astype(int)
    f = pos - i
    idx = np.arange(n)
    return Y[i, idx] * (1 - f) + Y[i + 1, idx] * f


def saw(fvec, os_=4, ph0=0.0):
    """Bandbegrenzter Sägezahn: überabgetastet, danach mit Filter heruntergerechnet."""
    f = np.asarray(fvec, dtype=float)
    n = len(f)
    fo = np.repeat(f, os_)
    ph = (ph0 + np.cumsum(fo) / (SR * os_)) % 1.0
    s = 2 * ph - 1
    return signal.resample_poly(s, 1, os_)[:n]


def sine(fvec, ph0=0.0):
    f = np.asarray(fvec, dtype=float)
    return np.sin(2 * np.pi * (ph0 + np.cumsum(f) / SR))


def fade_env(n, a, r, hold=None):
    """Hüllkurve: Anstieg a s, danach konstant, letzte r s Abfall."""
    e = np.ones(n)
    na = max(1, int(a * SR))
    nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na) ** 1.0
    e[-nr:] = np.minimum(e[-nr:], np.linspace(1, 0, nr))
    return e


class Stem:
    def __init__(self, n):
        self.d = np.zeros((2, n), dtype=np.float64)
        self.n = n

    def add(self, t, x, g=1.0, pan=0.0):
        """Mono-Signal x bei t Sekunden einfügen; pan -1 links bis +1 rechts (Konstantleistung)."""
        i0 = int(round(t * SR))
        if i0 >= self.n or i0 + len(x) <= 0:
            return
        lo = max(0, -i0)
        hi = min(len(x), self.n - i0)
        a = (pan + 1) * np.pi / 4
        self.d[0, i0 + lo:i0 + hi] += x[lo:hi] * g * np.cos(a)
        self.d[1, i0 + lo:i0 + hi] += x[lo:hi] * g * np.sin(a)

    def add_st(self, t, xl, xr, g=1.0):
        i0 = int(round(t * SR))
        if i0 >= self.n:
            return
        hi = min(len(xl), self.n - i0)
        self.d[0, i0:i0 + hi] += xl[:hi] * g
        self.d[1, i0:i0 + hi] += xr[:hi] * g


# ------------------------------------------------------------------ Schlagzeug und Effekte
def make_kick():
    n = int(0.5 * SR)
    t = tarr(n)
    f = 47 + 120 * np.exp(-t / 0.022)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.17)
    click = hp(rng.uniform(-1, 1, n), 1800) * np.exp(-t / 0.0035) * 0.4
    x = np.tanh(2.1 * (body + click))
    x *= np.clip((n - np.arange(n)) / (0.03 * SR), 0, 1)
    return x / np.max(np.abs(x))


def make_clap():
    n = int(0.5 * SR)
    base = bp(rng.uniform(-1, 1, n), 900, 4200)
    out = np.zeros(n)
    for off, g in ((0.0, 0.7), (0.011, 0.8), (0.023, 0.9), (0.039, 1.0)):
        o = int(off * SR)
        tt = tarr(n - o)
        out[o:] += base[:n - o] * g * np.exp(-tt / (0.011 if off < 0.039 else 0.10))
    return out / np.max(np.abs(out))


def make_snare():
    n = int(0.4 * SR)
    t = tarr(n)
    noise = hp(rng.uniform(-1, 1, n), 1400) * np.exp(-t / 0.085)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.6
    x = np.tanh(1.5 * (noise + tone))
    return x / np.max(np.abs(x))


def make_hat(decay, n_s=0.25):
    n = int(n_s * SR)
    x = hp(rng.uniform(-1, 1, n), 7500) * np.exp(-tarr(n) / decay)
    return x / np.max(np.abs(x))


def make_crash(dur=2.6):
    n = int(dur * SR)
    t = tarr(n)
    x = hp(rng.uniform(-1, 1, n), 3200) * np.exp(-t / 0.75)
    x *= np.minimum(1, t / 0.002)
    return x / np.max(np.abs(x))


def make_impact():
    n = int(2.6 * SR)
    t = tarr(n)
    f = 30 + 55 * np.exp(-t / 0.35)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.75)
    rum = lp(rng.uniform(-1, 1, n), 420) * np.exp(-t / 0.5) * 2.2
    top = hp(rng.uniform(-1, 1, n), 2500) * np.exp(-t / 0.18) * 0.35
    x = np.tanh(1.2 * (sub * 1.0 + rum + top))
    return x / np.max(np.abs(x))


def make_riser(dur, f0=350.0, f1=9500.0):
    n = int(dur * SR)
    fc = np.geomspace(f0, f1, n)
    amp = (np.arange(n) / n) ** 1.7
    ch = []
    for _ in range(2):
        x = rng.uniform(-1, 1, n)
        ch.append(hp(lp_sweep(x, fc), 250) * amp)
    return ch[0] / np.max(np.abs(ch[0])), ch[1] / np.max(np.abs(ch[1]))


def make_downlift(dur):
    l, r = make_riser(dur, 6000.0, 400.0)
    n = len(l)
    env = (1 - np.arange(n) / n) ** 1.3 * np.minimum(1, np.arange(n) / (0.01 * SR))
    return l * env / np.max(np.abs(l * env)), r * env / np.max(np.abs(r * env))


# ------------------------------------------------------------------ Stimmen
def pad_chord(notes, dur, fc0, fc1, os_=2):
    """Breiter Akkord aus verstimmten Sägezähnen, Tiefpass fährt von fc0 nach fc1."""
    n = int((dur + 0.5) * SR)
    t = tarr(n)
    L = np.zeros(n)
    R = np.zeros(n)
    det = [-0.012, -0.006, 0.0, 0.006, 0.012]
    for m in notes:
        f0 = mtof(m)
        for k, d in enumerate(det):
            s = saw(np.full(n, f0 * (1 + d)), os_, ph0=rng.random())
            w = k / (len(det) - 1)
            L += s * (1 - w) * 0.5 + s * 0.15
            R += s * w * 0.5 + s * 0.15
    fc = fc0 + (fc1 - fc0) * np.clip(t / dur, 0, 1)
    L = lp_sweep(L, fc)
    R = lp_sweep(R, fc)
    env = np.clip(t / 0.08, 0, 1) * np.where(t < dur, 1.0, np.clip(1 - (t - dur) / 0.5, 0, 1))
    g = 0.11 / max(1, len(notes) / 3)
    return L * env * g, R * env * g


def bass_note(f, dur, bright=1.0):
    n = int((dur + 0.05) * SR)
    t = tarr(n)
    s = saw(np.full(n, f), 4) * 0.7 + np.sign(np.sin(2 * np.pi * f * t)) * 0.2
    fc = (160 + 1400 * np.exp(-t / 0.09)) * bright
    y = lp_sweep(s, fc)
    sub = np.sin(2 * np.pi * f * t)
    env = np.clip(t / 0.004, 0, 1) * np.where(t < dur, 1.0, np.clip(1 - (t - dur) / 0.05, 0, 1))
    return np.tanh(1.4 * (y * 0.9 + sub * 0.85)) * env


def pluck(f, dur=0.3, bright=1.0):
    n = int((dur + 0.08) * SR)
    t = tarr(n)
    s = saw(np.full(n, f * 1.004), 4, 0.3) + saw(np.full(n, f * 0.996), 4, 0.7)
    fc = (700 + 5200 * np.exp(-t / 0.06)) * bright
    y = lp_sweep(s, fc)
    return y * np.exp(-t / 0.15) * np.clip(t / 0.002, 0, 1) * 0.45


def lead_note(f, dur, vib=True):
    n = int((dur + 0.25) * SR)
    t = tarr(n)
    vf = 1 + (0.005 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - 0.15) / 0.4, 0, 1) if vib else 0)
    ft = f * vf
    s = (saw(ft * 0.997, 4, 0.1) + saw(ft * 1.003, 4, 0.6) + saw(ft, 4, 0.35)) * 0.4
    s += np.sign(np.sin(2 * np.pi * np.cumsum(ft) / SR)) * 0.12
    fc = 1500 + 3200 * np.exp(-t / 0.25)
    y = lp_sweep(s, fc)
    env = np.clip(t / 0.006, 0, 1) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.07))
    return y * env * 0.32


def piano_note(f, dur, vel=0.8):
    n = int((dur + 0.7) * SR)
    t = tarr(n)
    y = np.zeros(n)
    for k in range(1, 12):
        fk = f * k * np.sqrt(1 + 0.00035 * k * k)
        if fk > 8500:
            break
        y += (vel / k ** 1.25) * np.sin(2 * np.pi * fk * t + 0.7 * k) * np.exp(-t / (2.2 / (1 + 0.55 * k)))
    hammer = lp(rng.uniform(-1, 1, n), 3500) * np.exp(-t / 0.012) * 0.12
    y += hammer
    env = np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.18)) * np.clip(t / 0.003, 0, 1)
    return y * env * 0.5


def bell(f, dur=1.4):
    n = int(dur * SR)
    t = tarr(n)
    y = np.zeros(n)
    for ratio, a, dec in ((1.0, 1.0, 0.55), (2.76, 0.5, 0.3), (5.4, 0.25, 0.14), (8.9, 0.1, 0.07)):
        y += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / dec)
    return y * np.clip(t / 0.002, 0, 1) * 0.5


# ------------------------------------------------------------------ Aufbau
PROG = {
    # Name: (Pad/Stab-Töne, Basston, Töne für Plucks, Töne für Leadlinie bleibt in LEAD)
    "Dm": ((62, 65, 69), 38, (62, 65, 69, 74)),
    "Bb": ((58, 62, 65), 34, (58, 62, 65, 70)),
    "F": ((60, 65, 69), 41, (60, 65, 69, 72)),
    "C": ((60, 64, 67), 36, (60, 64, 67, 72)),
}
LOOP = ["Dm", "Bb", "F", "C"]

# Lead-Motiv je Akkord: (Achtel-Position, MIDI-Note, Länge in Achteln)
LEAD = {
    "Dm": [(0, 74, 2), (2, 77, 2), (4, 81, 3), (7, 79, 1)],
    "Bb": [(0, 77, 2), (2, 74, 1), (3, 77, 1), (4, 79, 3), (7, 77, 1)],
    "F": [(0, 81, 2), (2, 77, 2), (4, 72, 2), (6, 77, 2)],
    "C": [(0, 79, 2), (2, 76, 2), (4, 72, 2), (6, 76, 1), (7, 79, 1)],
}


def chord_name(bar):
    if bar == 22:
        return "Bb"
    if bar == 23:
        return "C"
    if bar >= 24:
        return "F"
    return LOOP[(bar - 6) % 4]


def build_stems(dur=DUR):
    n = int((dur + TAIL) * SR)
    kick_s, clap_s, snare_s = make_kick(), make_clap(), make_snare()
    hat_c, hat_o, hat_s = make_hat(0.025), make_hat(0.16), make_hat(0.012, 0.1)
    crash_s, impact_s = make_crash(), make_impact()

    kicks_st, claps_st, hats_st = Stem(n), Stem(n), Stem(n)
    bass_st, pad_st, pluck_st, lead_st = Stem(n), Stem(n), Stem(n), Stem(n)
    piano_st, fx_st, spark_st = Stem(n), Stem(n), Stem(n)
    kick_times = []
    mute = []  # (t0, t1): alles außer Effekten stumm (Stopp vor dem Drop)

    def kick(t, g=1.0):
        kicks_st.add(t, kick_s, 0.95 * g)
        kick_times.append(t)

    def clap(t, g=1.0, pan=0.0):
        claps_st.add(t, clap_s, 0.8 * g, pan)

    def snare(t, g=1.0):
        claps_st.add(t, snare_s, 0.7 * g)

    def crash(t, g=1.0):
        fx_st.add(t, crash_s, 0.55 * g, 0.1)

    def impact(t, g=1.0):
        fx_st.add(t, impact_s, 0.95 * g)

    def snare_roll(t0, t1, g0=0.25, g1=1.0, step=BEAT / 2):
        """Wirbel: Achtel, in der zweiten Hälfte Sechzehntel."""
        k, tt = 0, t0
        total = t1 - t0
        while tt < t1 - 1e-6:
            x = (tt - t0) / total
            st = step if x < 0.5 else step / 2
            snare(tt, g0 + (g1 - g0) * x)
            tt += st
            k += 1

    def bell_hit(t, midi, g=1.0):
        spark_st.add(t, bell(mtof(midi)), 0.22 * g, pan=0.25 if int(t * 2) % 2 else -0.25)

    def pluck_hit(t, midi, g=1.0, pan=0.0):
        pluck_st.add(t, pluck(mtof(midi), 0.32, 1.2), 0.5 * g, pan)

    def pad(t, name, d=BAR, fc0=900, fc1=2800, g=1.0, octave=0):
        notes = [m + 12 * octave for m in PROG[name][0]]
        l, r = pad_chord(notes, d, fc0, fc1)
        pad_st.add_st(t, l, r, g)

    def bassline(t_bar, name, mode):
        root = PROG[name][1]
        f = mtof(root)
        if mode == "long":
            bass_st.add(t_bar, bass_note(f, BAR - 0.05, 0.6), 0.9)
        elif mode == "tense":  # Achtel auf "und" von 1 und 3
            for q in (0.5, 2.5):
                bass_st.add(t_bar + q * BEAT, bass_note(f, BEAT * 0.8, 0.8), 0.9)
        else:  # treibend: Achtel auf allen "und", Oktave auf Schlag 4
            for q in range(4):
                oc = 2.0 if q == 3 else 1.0
                bass_st.add(t_bar + (q + 0.5) * BEAT, bass_note(f * oc, BEAT * 0.42), 0.85)
            bass_st.add(t_bar, bass_note(f, BEAT * 0.45), 0.8)
            bass_st.add(t_bar + 2 * BEAT, bass_note(f, BEAT * 0.45), 0.7)

    def arp(t_bar, name, density=2, g=0.5, up=0):
        tones = PROG[name][2]
        steps = 8 if density == 2 else 16
        sp = BAR / steps
        order = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 1, 3, 2]
        for k in range(steps):
            m = tones[order[k % 16] % 4] + 12 * up + 12
            pluck_hit(t_bar + k * sp, m, g * (1.0 if k % 2 == 0 else 0.7), pan=-0.4 if k % 2 else 0.4)

    def lead(t_bar, name, g=1.0, octave=0):
        for pos, m, ln in LEAD[name]:
            t = t_bar + pos * BEAT / 2
            d = ln * BEAT / 2
            f = mtof(m + 12 * octave)
            x = lead_note(f, d * 0.95)
            lead_st.add(t, x, 0.55 * g, 0.0)
            # Echo (punktierte Achtel)
            lead_st.add(t + BEAT * 0.75, x, 0.17 * g, 0.5)
            lead_st.add(t + BEAT * 1.5, x, 0.07 * g, -0.5)

    def piano_chord(t, name, g=1.0, octave=0, d=1.6, arpeggio=0.0):
        notes = PROG[name][0]
        for k, m in enumerate(notes):
            piano_st.add(t + k * arpeggio, piano_note(mtof(m + 12 * octave), d), 0.5 * g, pan=(k - 1) * 0.25)
        piano_st.add(t, piano_note(mtof(PROG[name][1] + 24), d), 0.35 * g)

    def hats(t_bar, level, open_on=3):
        for q in range(4):
            tb = t_bar + q * BEAT
            hats_st.add(tb + BEAT / 2, hat_o if q == open_on else hat_c, 0.22 * level, pan=0.3)
            if level >= 0.9:
                hats_st.add(tb + BEAT / 4, hat_s, 0.10, pan=-0.3)
                hats_st.add(tb + BEAT * 3 / 4, hat_s, 0.12, pan=0.3)

    # ---------------------------------------------------- A: Hook 0 bis 4 s (Takt 0, 1)
    pad(0.0, "F", BAR * 2, 380, 900, 0.8)
    for tt, gg in zip(CUES["hook_slams"], (0.8, 0.95, 1.1)):
        kick(tt, gg)
        impact(tt, 0.55 + 0.25 * CUES["hook_slams"].index(tt))
    clap(1.0, 0.7)
    clap(2.0, 1.0)
    bass_st.add(2.0, bass_note(mtof(PROG["F"][1]), 1.0, 0.7), 1.0)
    bass_st.add(0.0, bass_note(mtof(PROG["F"][1]), 0.9, 0.6), 0.9)
    for tt in (0.5, 1.5, 2.5, 3.0, 3.5):
        hats_st.add(tt, hat_c, 0.14 + 0.03 * tt, pan=0.3)
    fx_st.add_st(1.0, *make_riser(3.0, 300, 7500), 0.5)
    snare_roll(3.0, 4.0, 0.3, 1.0, BEAT / 2)

    # ---------------------------------------------------- B: Problem 4 bis 12 s (Takte 2 bis 5)
    for b in range(2, 6):
        t_bar = b * BAR
        name = chord_name(b)
        pad(t_bar, name, BAR, 700 + 250 * (b - 2), 1500 + 600 * (b - 2), 0.8)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.85)
        hats(t_bar, 0.6)
        bassline(t_bar, name, "tense")
        arp(t_bar, name, 2, 0.14 + 0.05 * (b - 2))
    impact(4.0, 0.8)
    crash(4.0, 0.5)
    for k, tt in enumerate(CUES["problem_cards"]):
        bell_hit(tt, (69, 72, 74, 77)[k], 1.0)       # steigende Zählstimme zu den vier Karten
    impact(CUES["problem_banner"][0], 0.9)
    claps_st.add(CUES["problem_banner"][0], clap_s, 0.9)
    bell_hit(CUES["problem_banner"][1], 74, 0.8)
    fx_st.add_st(9.0, *make_riser(3.0, 400, 10000), 0.7)
    snare_roll(10.0, 11.5, 0.3, 1.0, BEAT / 2)
    for k in range(6):   # Sechzehntel-Wirbel direkt vor dem Stopp
        snare(11.0 + k * BEAT / 4 + 0.5 * 0, 0.0)
    mute.append((11.75, 12.0))

    # ---------------------------------------------------- C: Lösung 12 bis 22 s (Takte 6 bis 10)
    impact(12.0, 1.1)
    crash(12.0, 1.0)
    for b in range(6, 11):
        t_bar = b * BAR
        name = chord_name(b)
        pad(t_bar, name, BAR, 2600, 3600, 1.0)
        pad(t_bar, name, BAR, 3000, 3400, 0.35, octave=1)
        for q in range(4):
            kick(t_bar + q * BEAT)
            if q in (1, 3):
                clap(t_bar + q * BEAT, 0.9)
        hats(t_bar, 1.0)
        bassline(t_bar, name, "drive")
        arp(t_bar, name, 2, 0.30, up=0)
        if b <= 9:
            lead(t_bar, name, 1.0)
    for tt in CUES["loesung_lines"]:
        crash(tt, 0.55)
        bell_hit(tt, 81 if tt == 13.0 else 86, 1.1)
    bell_hit(CUES["loesung_card"], 79, 1.0)
    crash(CUES["loesung_card"], 0.6)
    for k, tt in enumerate(CUES["loesung_bullets"]):
        pluck_hit(tt, (74, 77, 81)[k], 1.4)
        bell_hit(tt, (86, 89, 93)[k], 0.7)
    # Übergang in die Produktszene
    snare_roll(20.5, 22.0, 0.3, 0.9)
    fx_st.add_st(20.0, *make_riser(2.0, 500, 9000), 0.45)

    # ---------------------------------------------------- D: Produkt 22 bis 38 s (Takte 11 bis 18)
    crash(22.0, 0.9)
    impact(22.0, 0.55)
    for b in range(11, 19):
        t_bar = b * BAR
        name = chord_name(b)
        pad(t_bar, name, BAR, 1800, 2600, 0.8)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.95)
            if q in (1, 3):
                clap(t_bar + q * BEAT, 0.8)
        hats(t_bar, 0.9 if b >= 15 else 0.75)
        bassline(t_bar, name, "drive")
        arp(t_bar, name, 2, 0.26, up=0 if b < 15 else 1)
        if b >= 15 and b <= 17:
            lead(t_bar, name, 0.9, octave=0)
    for tt in CUES["produkt_cuts"][1:]:
        crash(tt, 0.75)
        impact(tt, 0.45)
    for tt in CUES["produkt_callouts"]:
        bell_hit(tt, 86, 1.1)
        bell_hit(tt + 0.5, 89, 0.7)
    # Vorbereitung auf die Pause
    snare_roll(35.5, 37.75, 0.25, 1.0)
    fx_st.add_st(34.0, *make_riser(4.0, 400, 10000), 0.6)
    mute.append((37.75, 38.0))

    # ---------------------------------------------------- E: Vertrauen 38 bis 44 s (Takte 19 bis 21)
    impact(38.0, 1.0)
    for b in range(19, 22):
        t_bar = b * BAR
        name = chord_name(b)
        pad(t_bar, name, BAR, 1200, 1800, 0.9)
        bassline(t_bar, name, "long")
        piano_chord(t_bar, name, 0.8, d=BAR, arpeggio=0.0)
        for k in range(4):
            piano_st.add(t_bar + (k * 2 + 1) * BEAT / 2 * 1.0, piano_note(mtof(PROG[name][2][(k + 1) % 4] + 12), 0.5, 0.45), 0.3, pan=0.3 if k % 2 else -0.3)
    for tt in CUES["vertrauen_lines"]:
        piano_chord(tt, chord_name(int(tt // BAR)), 1.0, octave=1, d=1.4)
        kicks_st.add(tt, kick_s, 0.8)
        kick_times.append(tt)
    # Herzschlag im letzten Takt
    for tt in (42.0, 43.0, 43.5):
        kick(tt, 0.6)
    fx_st.add_st(42.0, *make_riser(2.0, 500, 11000), 0.7)
    snare_roll(43.0, 44.0, 0.25, 1.0, BEAT / 2)
    mute.append((43.875, 44.0))

    # ---------------------------------------------------- F: Abbinder 44 bis 49 s (Takte 22 bis 24)
    impact(44.0, 1.2)
    crash(44.0, 1.0)
    for b, t_bar in ((22, 44.0), (23, 46.0)):
        name = chord_name(b)
        pad(t_bar, name, BAR, 3000, 3500, 1.0)
        pad(t_bar, name, BAR, 3000, 3400, 0.3, octave=1)
        for q in range(4):
            if b == 22 or q in (0, 2):
                kick(t_bar + q * BEAT, 0.95)
            if b == 22 and q in (1, 3):
                clap(t_bar + q * BEAT, 0.9)
        if b == 22:
            hats(t_bar, 0.9)
        bassline(t_bar, name, "drive" if b == 22 else "long")
        lead(t_bar, name, 1.0)
    for tt in CUES["abbinder_lines"]:
        crash(tt, 0.5)
    bell_hit(CUES["abbinder_pill"], 91, 1.2)
    # Auflösung: F-Dur lang ausklingen
    pad(48.0, "F", 3.8, 3200, 2400, 1.1)
    pad(48.0, "F", 3.8, 3200, 2400, 0.4, octave=1)
    kick(48.0, 1.0)
    impact(48.0, 0.9)
    bass_st.add(48.0, bass_note(mtof(PROG["F"][1]), 2.8, 0.7), 1.0)
    piano_chord(48.0, "F", 1.1, octave=1, d=2.6, arpeggio=0.04)
    lead_st.add(48.0, lead_note(mtof(81), 2.4), 0.5)
    bell_hit(48.0, 93, 1.0)

    # ---------------------------------------------------- Sidechain, Mischung, Hall
    duck = np.ones(n)
    ln = int(0.30 * SR)
    prof = 1 - 0.62 * (1 - np.arange(ln) / ln) ** 2
    for tk in kick_times:
        i0 = int(round(tk * SR))
        seg = duck[i0:i0 + ln]
        np.minimum(seg, prof[:len(seg)], out=seg)

    gate = np.ones(n)
    for a, b in mute:
        ia, ib = int(a * SR), int(b * SR)
        gate[ia:ib] = 0.0
        # kurze Rampen, damit nichts knackt
        r = int(0.006 * SR)
        gate[max(0, ia - r):ia] = np.linspace(1, 0, ia - max(0, ia - r))
        gate[ib:ib + r] = np.linspace(0, 1, min(r, n - ib))

    stems = {"kick": kicks_st, "clap": claps_st, "hat": hats_st, "bass": bass_st, "pad": pad_st,
             "pluck": pluck_st, "lead": lead_st, "piano": piano_st, "spark": spark_st, "fx": fx_st}
    return {"stems": stems, "duck": duck, "gate": gate, "n": n}


# Pegel der Bausteine (Verhältnis tief zu mittel zu hoch bestimmt, ob die Musik dumpf oder klar klingt)
GAINS = {"kick": 0.55, "clap": 0.75, "hat": 0.75, "bass": 0.42, "pad": 1.5, "pluck": 0.95, "lead": 1.25,
         "piano": 1.25, "spark": 0.9, "fx": 0.55}
# Lautheitsverlauf: (Sekunde, dB). Zwischenwerte werden linear verbunden. Sorgt für Dynamik trotz Begrenzer.
SECTION_DB = [(0, -4), (3.9, -4), (4.0, -3), (11.7, -1), (12.0, 0), (21.9, 0), (22.0, -1), (37.7, -0.5), (38.0, -6),
              (43.5, -5), (44.0, 0), (47.5, 0), (49.0, -1)]


def mixdown(parts, g=None, section_db=None, reverb=0.5):
    g = {**GAINS, **(g or {})}
    st, duck, gate, n = parts["stems"], parts["duck"], parts["gate"], parts["n"]

    def mix(name, ducked=0.0, gated=True):
        d = st[name].d * g[name]
        if ducked:
            d = d * (1 - ducked + ducked * duck)
        if gated:
            d = d * gate
        return d

    send = (mix("pad", 0.8) * 0.45 + mix("lead") * 0.5 + mix("piano") * 0.6 + mix("clap") * 0.35 +
            mix("spark") * 0.8 + mix("fx", gated=False) * 0.4 + mix("pluck", 0.5) * 0.4 + mix("hat") * 0.05)
    rev_board = pb.Pedalboard([pb.HighpassFilter(280), pb.LowpassFilter(9500),
                               pb.Reverb(room_size=0.72, damping=0.45, wet_level=1.0, dry_level=0.0, width=1.0)])
    rev = rev_board(send.astype(np.float32), SR).astype(np.float64)
    dry = (mix("kick") + mix("clap") + mix("hat") + mix("bass", 0.85) + mix("pad", 0.7) + mix("pluck", 0.5) +
           mix("lead", 0.35) + mix("piano") + mix("spark") + mix("fx", gated=False))
    out = dry + rev * reverb
    chain = pb.Pedalboard([
        pb.HighpassFilter(32),
        pb.Compressor(threshold_db=-16.0, ratio=2.2, attack_ms=22.0, release_ms=140.0),
        pb.Distortion(drive_db=1.5),
        pb.HighShelfFilter(cutoff_frequency_hz=7000, gain_db=1.5),
    ])
    out = chain(out.astype(np.float32), SR).astype(np.float64)
    pts = section_db or SECTION_DB
    t = np.arange(out.shape[1]) / SR
    curve = 10 ** (np.interp(t, [p[0] for p in pts], [p[1] for p in pts]) / 20)
    out = out * curve
    out = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=80.0)])(out.astype(np.float32), SR).astype(np.float64)
    out = out[:, :int(DUR * SR)]
    return out / (np.max(np.abs(out)) or 1.0) * 0.89


def render(dur=DUR):
    return mixdown(build_stems(dur))


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").T.copy()
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "music2.wav"
    y = render()
    write_wav(dest, y)
    rms = np.sqrt(np.mean(y ** 2))
    print(f"fertig: {dest}  {y.shape[1] / SR:.1f} s  RMS {20 * np.log10(rms):.1f} dBFS  Spitze {20 * np.log10(np.max(np.abs(y))):.1f} dBFS")
