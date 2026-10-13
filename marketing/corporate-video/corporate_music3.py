"""Musik für das SellCheck-Corporate-Video, Version 3: echte Instrumente, reduziert.

Klangquelle sind Aufnahmen aus der freien Bibliothek VSCO-2-CE (CC0, kommerzielle Nutzung ohne
Nachweis erlaubt): Violinen-, Bratschen- und Celloensemble (gehalten, Vibrato), Upright-Klavier,
Pauke. Die Dateien liegen in samples/ (nicht im Repo, Abruf siehe samples/_fetch.py).

Arrangement wie ein Werbefilm-Score statt Club-Track: Streicher als Fundament, Klavier mit
gleichmäßigem Achtel-Puls und kleinem Motiv, Pauken für die Einschläge, darunter ein leiser
Sub-Kick. Keine Snare-Wirbel, keine Risers, keine Glocken. Aufbauten kommen aus echten Streicher-
Crescendi und Paukenwirbeln. Alle Einsätze liegen auf dem 120-bpm-Raster des Bildes (CUES).

    .venv/bin/python corporate_music3.py out.wav
"""
import glob
import os
import re
import sys
from fractions import Fraction

import numpy as np
import pedalboard as pb
from scipy import signal
from scipy.io import wavfile

import corporate_music2 as M2
from corporate_music2 import CUES, DUR, SR, TAIL, BEAT, BAR, Stem, mtof, tarr, write_wav, hp, lp

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")
rng = np.random.default_rng(23)

NOTE_RE = re.compile(r"_([A-G]#?)(\d)_")
SEMI = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def read_wav(path):
    sr, x = wavfile.read(path)
    if x.dtype.kind == "i":
        x = x.astype(np.float64) / np.iinfo(x.dtype).max
    else:
        x = x.astype(np.float64)
    x = x.T if x.ndim == 2 else np.stack([x, x])
    if sr != SR:
        x = signal.resample_poly(x, SR, sr, axis=1)
    return x


class Sampler:
    """Einfacher Sampler: nächstliegende Aufnahme wählen, mit Tonhöhenverschiebung durch Umsampeln."""

    def __init__(self, files, midi_of=None, trim_attack=False):
        self.trim_attack = trim_attack
        self.entries = []   # (midi, layer, path)
        for p in files:
            m = midi_of(p) if midi_of else self._midi(p)
            if m is None:
                continue
            lay = re.search(r"_v(\d)", os.path.basename(p))
            self.entries.append((m, int(lay.group(1)) if lay else 0, p))
        self.cache = {}

    @staticmethod
    def _midi(p):
        m = NOTE_RE.search(os.path.basename(p))
        if not m:
            return None
        sci_oct = int(m.group(2)) + 1          # Dateinamen zählen eine Oktave tiefer als üblich
        return 12 * (sci_oct + 1) + SEMI[m.group(1)]

    def _raw(self, p):
        if p not in self.cache:
            x = read_wav(p)
            if self.trim_attack:
                x = trim_to_onset(x)
            n = min(x.shape[1], int(2.0 * SR))
            rms = np.sqrt(np.mean(x[:, :n] ** 2)) or 1.0
            self.cache[p] = x / rms * 0.1
        return self.cache[p]

    def note(self, midi, dur, layer_pref=0.5, rel=0.35, attack=0.0, rr=0):
        """Stereo-Array (2, n) der Länge dur + rel."""
        layers = sorted({e[1] for e in self.entries})
        want = layers[min(len(layers) - 1, int(round(layer_pref * (len(layers) - 1))))] if layers else 0
        pool = [e for e in self.entries if e[1] == want] or self.entries
        pool = sorted(pool, key=lambda e: (abs(e[0] - midi), e[2]))
        best = [e for e in pool if abs(e[0] - pool[0][0]) == 0][: 2]
        e = best[rr % len(best)]
        src = self._raw(e[2])
        shift = midi - e[0]
        ratio = 2 ** (shift / 12.0)       # > 1: höher, kürzer
        need = int((dur + rel + 0.1) * SR * ratio) + 8
        seg = src[:, :need]
        if abs(shift) > 1e-6:
            fr = Fraction(1.0 / ratio).limit_denominator(64)
            seg = signal.resample_poly(seg, fr.numerator, fr.denominator, axis=1)
        n = int((dur + rel) * SR)
        seg = seg[:, :n]
        if seg.shape[1] < n:
            seg = np.pad(seg, ((0, 0), (0, n - seg.shape[1])))
        env = np.ones(n)
        na = int(max(attack, 0.004) * SR)
        env[:na] = np.linspace(0, 1, na) ** (1.0 if attack > 0.02 else 1.0)
        nd = int(rel * SR)
        i0 = int(dur * SR)
        env[i0:i0 + nd] = np.linspace(1, 0, min(nd, n - i0)) ** 1.5
        env[i0 + nd:] = 0.0
        return seg * env


def trim_to_onset(x, thresh=0.25, keep=0.002):
    """Stille und langsamen Anlauf vor dem Anschlag abschneiden: Anschlag liegt dann auf Sample 0."""
    m = np.abs(x).max(0)
    head = m[: int(0.6 * SR)]
    j = int(np.argmax(head > head.max() * thresh))
    return x[:, max(0, j - int(keep * SR)):]


def _files(pattern):
    return sorted(glob.glob(os.path.join(SAMPLES, pattern)))


def load_library():
    lib = {}
    lib["cello"] = Sampler(_files("Strings/Cello Section/susvib/*.wav"))
    lib["viola"] = Sampler(_files("Strings/Viola Section/susvib/*.wav"))
    lib["violin"] = Sampler(_files("Strings/Violin Section/susVib/*.wav"))
    lib["piano"] = Sampler(_files("Keys/Upright Nr1/*_mf_*.wav"), trim_attack=True)
    # Pauken: fünf Kessel mit unterschiedlicher Stimmung, Tonhöhe aus der Aufnahme bestimmt
    tp = []
    for p in _files("Percussion/Timpani/Timpani*_Hit_v[34]_*.wav"):
        x = read_wav(p)
        mono = x.mean(0)[: int(0.8 * SR)]
        w = mono * np.hanning(len(mono))
        S = np.abs(np.fft.rfft(w, 1 << 18))
        fr = np.fft.rfftfreq(1 << 18, 1 / SR)
        m = (fr > 45) & (fr < 220)
        f0 = fr[m][np.argmax(S[m])]
        tp.append((12 * np.log2(f0 / 440.0) + 69, p))
    lib["timp"] = tp
    return lib


def timp_hit(lib, midi, vel=0.8, rr=0):
    cands = sorted(lib["timp"], key=lambda e: abs(e[0] - midi))
    base = cands[(rr % 2)] if abs(cands[0][0] - cands[1][0]) < 0.2 else cands[0]
    m0, p = base
    x = trim_to_onset(read_wav(p))
    x = x[:, : int(3.0 * SR)]
    pk = np.max(np.abs(x)) or 1.0
    x = x / pk * 0.6
    shift = midi - m0
    if abs(shift) > 1e-6:
        fr = Fraction(1.0 / (2 ** (shift / 12.0))).limit_denominator(64)
        x = signal.resample_poly(x, fr.numerator, fr.denominator, axis=1)
    return x * vel


# ------------------------------------------------------------------ Harmonik
CH = {
    #       Cello,        Bratsche,     Violine,         Bass (Sub, MIDI)
    "Dm": ([50, 57], [53, 57], [62, 65, 69], 38),
    "Bb": ([46, 53], [50, 53], [58, 62, 65], 34),
    "Gm": ([43, 50], [50, 58], [58, 62, 67], 31),
    "A": ([45, 52], [49, 52], [57, 61, 64], 33),
    "D": ([50, 57], [54, 57], [62, 66, 69], 38),
}
OSTI = {   # Klavier-Achtelpuls je Akkord (MIDI, 8 Achtel)
    "Dm": [50, 57, 62, 57, 50, 57, 62, 65],
    "Bb": [46, 53, 58, 53, 46, 53, 58, 62],
    "Gm": [43, 50, 55, 50, 43, 50, 55, 58],
    "A": [45, 52, 57, 52, 45, 52, 57, 61],
    "D": [50, 57, 62, 57, 50, 57, 62, 66],
}
MOTIF = {  # Klavier-Motiv, mittlere Lage: (Achtel-Position, MIDI, Länge in Achteln)
    "Dm": [(0, 69, 2), (2, 72, 2), (4, 74, 3), (7, 72, 1)],
    "Bb": [(0, 74, 2), (2, 70, 1), (3, 74, 1), (4, 77, 3), (7, 74, 1)],
    "Gm": [(0, 74, 2), (2, 70, 2), (4, 67, 2), (6, 70, 2)],
    "A": [(0, 76, 2), (2, 73, 2), (4, 69, 2), (6, 73, 1), (7, 76, 1)],
    "D": [(0, 78, 4), (4, 74, 4)],
}
TIMP_NOTE = {"Dm": 38, "Bb": 41, "Gm": 43, "A": 45, "D": 38}


def chord_name(bar):
    return M2.chord_name(bar)


def build_stems(dur=DUR):
    n = int((dur + TAIL) * SR)
    lib = load_library()
    kick_s = M2.make_kick()
    shaker = M2.make_hat(0.045, 0.2)
    shaker = lp(shaker, 9000)

    st = {k: Stem(n) for k in ("strings", "piano", "timp", "kick", "shk", "sub", "fx")}
    kick_times = []
    mute = []

    def put(stem, t, x, g=1.0, pan=0.0):
        st[stem].add_st(t, x[0] * g * (1 - max(0, pan)), x[1] * g * (1 + min(0, pan)))

    def timp(t, midi, vel=0.8, rr=0):
        put("timp", t, timp_hit(lib, midi, vel, rr))

    def timp_roll(t0, t1, v0=0.25, v1=0.9, midi=38):
        """Wirbel aus Einzelschlägen: Achtel, dann Sechzehntel, dann Zweiunddreißigstel."""
        t, k = t0, 0
        total = t1 - t0
        while t < t1 - 1e-6:
            x = (t - t0) / total
            timp(t, midi, v0 + (v1 - v0) * x, rr=k)
            t += BEAT / 2 if x < 0.4 else (BEAT / 4 if x < 0.8 else BEAT / 8)
            k += 1

    def sub(t, midi, d, g=1.0):
        f = mtof(midi)
        nn = int((d + 0.1) * SR)
        tt = tarr(nn)
        y = np.sin(2 * np.pi * f * tt) * np.minimum(1, tt / 0.01)
        y *= np.where(tt < d, 1.0, np.clip(1 - (tt - d) / 0.1, 0, 1))
        st["sub"].add(t, y, 0.5 * g)

    def kick(t, g=1.0):
        st["kick"].add(t, kick_s, 0.55 * g)
        kick_times.append(t)

    def strings(t, name, d=BAR, g=1.0, vel=0.5, attack=0.18, voices=("cello", "viola", "violin")):
        ce, vi, vl, _ = CH[name]
        rel = 0.45
        if "cello" in voices:
            for k, m in enumerate(ce):
                put("strings", max(0.0, t - 0.02), lib["cello"].note(m, d, vel, rel, attack, rr=k), 0.9 * g, pan=-0.3)
        if "viola" in voices:
            for k, m in enumerate(vi):
                put("strings", max(0.0, t - 0.02), lib["viola"].note(m, d, vel, rel, attack, rr=k), 0.8 * g, pan=0.2)
        if "violin" in voices:
            for k, m in enumerate(vl):
                put("strings", max(0.0, t - 0.02), lib["violin"].note(m, d, vel, rel, attack, rr=k), 0.75 * g, pan=0.35 if k % 2 else -0.15)

    def swell(t, name, d, g=1.0, voices=("violin", "viola")):
        """Crescendo: Streicher setzen leise ein und werden lauter (Fade-in über die ganze Länge)."""
        ce, vi, vl, _ = CH[name]
        buf = Stem(n)
        for m in vl:
            if "violin" in voices:
                x = lib["violin"].note(m + 12, d, 0.7, 0.35, 0.05)
                buf.add_st(t, x[0], x[1], 0.7)
        for m in vi:
            if "viola" in voices:
                x = lib["viola"].note(m + 12, d, 0.7, 0.35, 0.05)
                buf.add_st(t, x[0], x[1], 0.6)
        i0, i1 = int(t * SR), int((t + d) * SR)
        ramp = np.zeros(n)
        ramp[i0:i1] = np.linspace(0, 1, i1 - i0) ** 1.7
        ramp[i1:] = 1.0
        st["strings"].d += buf.d * ramp * g

    def piano_note(t, midi, vel=0.6, d=0.45, g=1.0, pan=0.0, rr=0):
        x = lib["piano"].note(midi, d, vel, 0.25, 0.0, rr=rr)
        put("piano", t, x, g * (0.4 + 0.9 * vel), pan)

    def ostinato(t_bar, name, vel=0.5, g=1.0):
        for q, m in enumerate(OSTI[name]):
            v = vel * (1.0 if q % 2 == 0 else 0.8) * (1.1 if q == 0 else 1.0)
            piano_note(t_bar + q * BEAT / 2, m + 12, min(1.0, v), BEAT * 0.5, g, rr=q)

    def motif(t_bar, name, vel=0.7, g=1.0):
        for pos, m, ln in MOTIF[name]:
            piano_note(t_bar + pos * BEAT / 2, m, vel, ln * BEAT / 2, g * 1.1, pan=0.1, rr=pos)

    def chord_piano(t, name, vel=0.6, octave=0, d=1.8, g=1.0, spread=0.0):
        ce, vi, vl, _ = CH[name]
        for k, m in enumerate(sorted(set(vi + vl))):
            piano_note(t + k * spread, m + 12 * octave, vel, d, g, pan=(k % 3 - 1) * 0.2, rr=k)

    def shake(t_bar, level=1.0):
        for q in range(8):
            st["shk"].add(t_bar + q * BEAT / 2, shaker, (0.06 if q % 2 == 0 else 0.1) * level, pan=0.25 if q % 2 else -0.25)

    # ---------------------------------------------------- A: Hook 0 bis 4 s
    strings(0.0, "Gm", BAR, 0.9, 0.3, attack=0.35, voices=("cello", "viola"))
    strings(2.0, "A", BAR, 1.0, 0.4, attack=0.25, voices=("cello", "viola", "violin"))
    for k, tt in enumerate(CUES["hook_slams"]):
        timp(tt, (43, 43, 45)[k], (0.6, 0.75, 0.95)[k], rr=k)
        sub(tt, (31, 31, 33)[k], 0.9, (0.8, 0.9, 1.1)[k])
    piano_note(1.0, 67, 0.4, 0.9, 0.8)
    piano_note(2.0, 69, 0.5, 1.0, 0.9)
    timp_roll(3.0, 4.0, 0.25, 0.9, 45)

    # ---------------------------------------------------- B: Problem 4 bis 12 s
    for b in range(2, 6):
        t_bar = b * BAR
        name = chord_name(b)
        v = 0.3 + 0.08 * (b - 2)
        strings(t_bar, name, BAR, 0.9, v, attack=0.25, voices=("cello", "viola") if b < 4 else ("cello", "viola", "violin"))
        sub(t_bar, CH[name][3], BAR - 0.1, 0.8)
        piano_note(t_bar, CH[name][1][0] + 12, 0.5, 0.9, 0.9)
        if b >= 4:
            ostinato(t_bar, name, 0.4 + 0.1 * (b - 4), 0.8)
        if b >= 3:
            for q in range(4):
                kick(t_bar + q * BEAT, 0.7)
            shake(t_bar, 0.7)
    timp(4.0, 38, 0.85)
    for k, tt in enumerate(CUES["problem_cards"]):
        piano_note(tt, (57, 60, 62, 65)[k], 0.7, 0.8, 1.1)   # steigende Zählstimme zu den vier Karten
    timp(CUES["problem_banner"][0], 38, 1.0)
    chord_piano(CUES["problem_banner"][0], "Dm", 0.8, octave=-1, d=1.5)
    piano_note(CUES["problem_banner"][1], 62, 0.6, 0.6, 1.0)
    swell(9.0, "A", 3.0, 1.0)
    timp_roll(10.0, 11.75, 0.2, 0.95, 38)
    mute.append((11.75, 12.0))

    # ---------------------------------------------------- C: Lösung 12 bis 22 s
    timp(12.0, 38, 1.0)
    timp(12.0, 50, 0.7, rr=1)
    for b in range(6, 11):
        t_bar = b * BAR
        name = chord_name(b)
        strings(t_bar, name, BAR, 1.0, 0.75, attack=0.2)
        sub(t_bar, CH[name][3], BAR - 0.1, 1.0)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.9)
        shake(t_bar, 1.0)
        ostinato(t_bar, name, 0.6, 0.9)
        if b <= 9:
            motif(t_bar, name, 0.75, 1.0)
        if b % 2 == 0:
            timp(t_bar, TIMP_NOTE[name], 0.7, rr=b)
    for tt in CUES["loesung_lines"]:
        timp(tt, 38 if tt == 13.0 else 45, 0.9, rr=int(tt * 2))
    timp(CUES["loesung_card"], 43, 0.9)
    for k, tt in enumerate(CUES["loesung_bullets"]):
        piano_note(tt, (62, 65, 69)[k], 0.8, 0.7, 1.2)
    swell(19.0, "Dm", 3.0, 0.9)
    timp_roll(20.5, 22.0, 0.3, 0.9, 38)

    # ---------------------------------------------------- D: Produkt 22 bis 38 s
    timp(22.0, 38, 0.8)
    for b in range(11, 19):
        t_bar = b * BAR
        name = chord_name(b)
        strings(t_bar, name, BAR, 0.8 if b < 15 else 1.0, 0.55 if b < 15 else 0.75, attack=0.2,
                voices=("cello", "viola") if b < 13 else ("cello", "viola", "violin"))
        sub(t_bar, CH[name][3], BAR - 0.1, 0.9)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.8)
        shake(t_bar, 0.9)
        ostinato(t_bar, name, 0.5 if b < 15 else 0.6, 0.85)
        if b >= 15:
            motif(t_bar, name, 0.7, 1.0)
    for tt in CUES["produkt_cuts"][1:]:
        timp(tt, 38, 0.75)
    for tt in CUES["produkt_callouts"]:
        piano_note(tt, 81, 0.5, 0.9, 0.9)
        timp(tt, 45, 0.5)
    swell(35.0, "Gm", 3.0, 0.9)
    timp_roll(36.0, 37.75, 0.2, 0.95, 38)
    mute.append((37.75, 38.0))

    # ---------------------------------------------------- E: Vertrauen 38 bis 44 s
    timp(38.0, 41, 0.9)
    for b in range(19, 22):
        t_bar = b * BAR
        name = chord_name(b)
        strings(t_bar, name, BAR, 0.8, 0.35 + 0.05 * (b - 19), attack=0.4, voices=("cello", "viola", "violin"))
        sub(t_bar, CH[name][3], BAR - 0.1, 0.8)
        chord_piano(t_bar, name, 0.45, octave=0, d=1.8, g=0.9, spread=0.03)
        for k in range(4):
            piano_note(t_bar + (k * 2 + 1) * BEAT / 2, CH[name][2][k % 3] + 12, 0.35, 0.5, 0.7, pan=-0.2 if k % 2 else 0.2)
    for tt in CUES["vertrauen_lines"]:
        chord_piano(tt, chord_name(int(tt // BAR)), 0.75, octave=-1, d=1.6, g=1.0)
        timp(tt, 41 if tt < 40 else 43, 0.55)
    for tt in (42.0, 43.0, 43.5):
        timp(tt, 38, 0.35)
    swell(41.5, "Gm", 2.5, 1.0)
    timp_roll(43.0, 43.875, 0.2, 0.9, 38)
    mute.append((43.875, 44.0))

    # ---------------------------------------------------- F: Abbinder 44 bis 49 s
    timp(44.0, 41, 1.0)
    timp(44.0, 53, 0.6, rr=1)
    for b, t_bar in ((22, 44.0), (23, 46.0)):
        name = chord_name(b)
        strings(t_bar, name, BAR, 1.1, 0.85, attack=0.15)
        sub(t_bar, CH[name][3], BAR - 0.1, 1.0)
        if b == 22:
            for q in range(4):
                kick(t_bar + q * BEAT, 0.9)
            shake(t_bar, 1.0)
        ostinato(t_bar, name, 0.6, 0.9) if b == 22 else chord_piano(t_bar, name, 0.7, octave=0, d=1.9)
        motif(t_bar, name, 0.8, 1.0)
    for k, tt in enumerate(CUES["abbinder_lines"]):
        timp(tt, 41 if k == 0 else 45, 0.85)
    piano_note(CUES["abbinder_pill"], 81, 0.7, 1.2, 1.0)
    # Auflösung nach D-Dur
    strings(48.0, "D", 3.4, 1.15, 0.8, attack=0.12)
    sub(48.0, 38, 2.8, 1.0)
    timp(48.0, 38, 1.0)
    chord_piano(48.0, "D", 0.75, octave=0, d=2.8, g=1.0, spread=0.05)
    motif(48.0, "D", 0.8, 1.0)

    # ---------------------------------------------------- Sidechain (leicht) und Stopps
    duck = np.ones(n)
    ln = int(0.28 * SR)
    prof = 1 - 0.28 * (1 - np.arange(ln) / ln) ** 2
    for tk in kick_times:
        i0 = int(round(tk * SR))
        seg = duck[i0:i0 + ln]
        np.minimum(seg, prof[:len(seg)], out=seg)
    gate = np.ones(n)
    for a, b in mute:
        ia, ib = int(a * SR), int(b * SR)
        r = int(0.006 * SR)
        gate[ia:ib] = 0.0
        gate[max(0, ia - r):ia] = np.linspace(1, 0, ia - max(0, ia - r))
        gate[ib:ib + r] = np.linspace(0, 1, min(r, n - ib))
    return {"stems": st, "duck": duck, "gate": gate, "n": n}


GAINS = {"strings": 1.0, "piano": 0.45, "timp": 0.7, "kick": 0.7, "shk": 4.0, "sub": 0.45, "fx": 0.0}
SECTION_DB = [(0, -3), (3.9, -2), (4.0, -4), (11.7, -2), (12.0, 0), (21.9, 0), (22.0, -1), (37.7, -1), (38.0, -5),
              (43.5, -4), (44.0, 0), (47.5, 0), (49.0, -1)]


def mixdown(parts, g=None, section_db=None, reverb=0.35):
    g = {**GAINS, **(g or {})}
    st, duck, gate, n = parts["stems"], parts["duck"], parts["gate"], parts["n"]

    def mix(name, ducked=0.0, gated=True):
        d = st[name].d * g[name]
        if ducked:
            d = d * (1 - ducked + ducked * duck)
        return d * gate if gated else d

    send = mix("strings") * 0.7 + mix("piano") * 0.6 + mix("timp") * 0.5
    rev_board = pb.Pedalboard([pb.HighpassFilter(220), pb.LowpassFilter(8500),
                               pb.Reverb(room_size=0.82, damping=0.55, wet_level=1.0, dry_level=0.0, width=1.0)])
    rev = rev_board(send.astype(np.float32), SR).astype(np.float64)
    dry = (mix("strings", 0.5) + mix("piano") + mix("timp") + mix("kick") + mix("shk") + mix("sub", 0.5))
    out = dry + rev * reverb
    chain = pb.Pedalboard([
        pb.HighpassFilter(30),
        pb.Compressor(threshold_db=-20.0, ratio=1.8, attack_ms=30.0, release_ms=220.0),
        pb.PeakFilter(cutoff_frequency_hz=300, gain_db=-1.5, q=0.8),
        pb.HighShelfFilter(cutoff_frequency_hz=5000, gain_db=2.5),
    ])
    out = chain(out.astype(np.float32), SR).astype(np.float64)
    pts = section_db or SECTION_DB
    t = np.arange(out.shape[1]) / SR
    out = out * 10 ** (np.interp(t, [p[0] for p in pts], [p[1] for p in pts]) / 20)
    out = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=120.0)])(out.astype(np.float32), SR).astype(np.float64)
    out = out[:, :int(DUR * SR)]
    return out / (np.max(np.abs(out)) or 1.0) * 0.89


def render(dur=DUR):
    return mixdown(build_stems(dur))


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "music3.wav"
    y = render()
    write_wav(dest, y)
    rms = np.sqrt(np.mean(y ** 2))
    print(f"fertig: {dest}  {y.shape[1] / SR:.1f} s  RMS {20 * np.log10(rms):.1f} dBFS  Spitze {20 * np.log10(np.max(np.abs(y))):.1f} dBFS")
