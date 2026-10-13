"""Musik für das SellCheck-Corporate-Video, Version 4: hell und treibend, echte Instrumente.

Gegenüber Version 3 (d-Moll, getragen, zu traurig): D-Dur, Akkorde D – A – Bm – G, Streicher auch kurz
(Spiccato) für den Antrieb, echtes Schlagzeug (Basstrommel, Snare, Becken, Tamburin) statt Synthese.
Aufbauten sind Becken-Crescendi und Snare-Wirbel, Höhepunkte Becken-Crashes und Pauken.

Klangquelle: VSCO-2-CE (CC0), siehe fetch_samples.py. Alle Einsätze liegen auf dem 120-bpm-Raster des
Bildes (CUES aus corporate_music2.py).

    .venv/bin/python corporate_music4.py out.wav
"""
import os
import sys

import numpy as np
import pedalboard as pb
from scipy import signal

import corporate_music2 as M2
import corporate_music3 as M3
from corporate_music2 import CUES, DUR, SR, TAIL, BEAT, BAR, Stem, mtof, tarr, write_wav, lp
from corporate_music3 import Sampler, read_wav, trim_to_onset, _files, SAMPLES

rng = np.random.default_rng(31)

# ------------------------------------------------------------------ Harmonik (D-Dur)
CH = {
    #       Cello,        Bratsche,     Violine,         Bass (MIDI)
    "D": ([50, 57], [54, 57], [62, 66, 69], 38),
    "A": ([45, 52], [52, 57], [57, 61, 64], 33),
    "Bm": ([47, 54], [50, 54], [59, 62, 66], 35),
    "G": ([43, 50], [50, 55], [59, 62, 67], 31),
}
ARP = {   # Klavier-Achtelpuls je Akkord, auf- und absteigend (8 Achtel)
    "D": [50, 57, 62, 66, 69, 66, 62, 57],
    "A": [45, 52, 57, 61, 64, 61, 57, 52],
    "Bm": [47, 54, 59, 62, 66, 62, 59, 54],
    "G": [43, 50, 55, 59, 62, 59, 55, 50],
}
MOTIF = {  # Melodie (Violinen, Klavier doppelt): (Achtel-Position, MIDI, Länge in Achteln)
    "D": [(0, 74, 2), (2, 78, 2), (4, 81, 3), (7, 78, 1)],
    "A": [(0, 76, 2), (2, 73, 2), (4, 76, 2), (6, 81, 2)],
    "Bm": [(0, 74, 2), (2, 78, 2), (4, 83, 3), (7, 81, 1)],
    "G": [(0, 79, 2), (2, 78, 1), (3, 74, 1), (4, 71, 2), (6, 74, 2)],
}
TIMP = {"D": 38, "A": 45, "Bm": 47, "G": 43}


def chord(b):
    if b < 6:
        return ["D", "A", "Bm", "G", "Bm", "A"][b]
    if b < 19:
        return ["D", "A", "Bm", "G"][(b - 6) % 4]
    return {19: "Bm", 20: "G", 21: "A", 22: "D", 23: "G"}.get(b, "D")


# ------------------------------------------------------------------ Bibliothek
def oneshot(path, peak=0.8, trim=True):
    x = read_wav(path)
    if trim:
        x = trim_to_onset(x)
    return x / (np.abs(x).max() or 1.0) * peak


def load_library():
    lib = M3.load_library()
    lib["cello_spic"] = Sampler(_files("Strings/Cello Section/spic/*.wav"), trim_attack=True)
    lib["viola_spic"] = Sampler(_files("Strings/Viola Section/spic/*.wav"), trim_attack=True)
    lib["violin_spic"] = Sampler(_files("Strings/Violin Section/Spic/*.wav"), trim_attack=True)
    lib["cello_pizz"] = Sampler(_files("Strings/Cello Section/pizzT/*.wav"), trim_attack=True)
    lib["kick"] = [oneshot(p) for p in _files("Percussion/BDrumNewhit_v[345]_*.wav")]
    lib["snare"] = [oneshot(p) for p in _files("Percussion/Snare2-HitSN_v[57]_*.wav")]
    lib["crash"] = [oneshot(p, 0.8) for p in _files("Percussion/cymbal-crash1_*.wav")]
    lib["tamb"] = [oneshot(p, 0.7) for p in _files("Percussion/Tamb1-Hit_v2_*.wav")]
    lib["shake"] = [oneshot(p, 0.5, trim=False) for p in _files("Percussion/Tamb1-Shake_*.wav")]
    cr = {}
    for nm in ("Short", "Median", "Long"):
        x = read_wav(os.path.join(SAMPLES, f"Percussion/susCymb1-cresc-{nm}_v1.wav"))
        m = np.abs(x).max(0)
        sm = np.sqrt(np.convolve(m ** 2, np.ones(int(0.05 * SR)) / int(0.05 * SR), "same"))
        cr[nm] = (x / (np.abs(x).max() or 1.0) * 0.8, int(np.argmax(sm)))
    lib["cresc"] = cr
    return lib


# ------------------------------------------------------------------ Aufbau
def build_stems(dur=DUR):
    n = int((dur + TAIL) * SR)
    lib = load_library()
    kick_tight = M2.make_kick()
    clap_s = M2.make_clap()
    st = {k: Stem(n) for k in ("strings", "spic", "piano", "timp", "drums", "perc", "sub", "fx")}
    kick_times, mute = [], []
    rrn = [0]

    def nx():
        rrn[0] += 1
        return rrn[0]

    def put(stem, t, x, g=1.0, pan=0.0):
        t0 = max(0.0, t)
        st[stem].add_st(t0, x[0] * g * (1 - max(0, pan)), x[1] * g * (1 + min(0, pan)))

    # ---- Schlagzeug
    def kick(t, vel=0.9):
        x = lib["kick"][nx() % len(lib["kick"])]
        cut = x[:, : int(0.6 * SR)].copy()
        cut *= np.clip((cut.shape[1] - np.arange(cut.shape[1])) / (0.15 * SR), 0, 1)
        put("drums", t, cut, 0.6 * vel)
        st["drums"].add(t, kick_tight, 0.45 * vel)
        kick_times.append(t)

    def snare(t, vel=0.8):
        x = lib["snare"][nx() % len(lib["snare"])]
        put("drums", t, x, 1.4 * vel)
        st["drums"].add(t, clap_s, 0.22 * vel)

    def crash(t, vel=0.8, ff=False):
        pool = lib["crash"][2:] if ff else lib["crash"]
        put("perc", t, pool[nx() % len(pool)], 0.7 * vel)

    def tamb(t, vel=0.6):
        put("perc", t, lib["tamb"][nx() % len(lib["tamb"])], 1.4 * vel, pan=0.3)

    def tamb_bar(t_bar, vel=0.5, offbeats_only=False):
        for q in range(8):
            if offbeats_only and q % 2 == 0:
                continue
            tamb(t_bar + q * BEAT / 2, vel * (1.0 if q % 2 else 0.7))

    def snare_roll(t0, t1, v0=0.2, v1=0.9):
        t, k = t0, 0
        total = t1 - t0
        while t < t1 - 1e-6:
            x = (t - t0) / total
            snare(t, v0 + (v1 - v0) * x)
            t += BEAT / 2 if x < 0.4 else BEAT / 4
            k += 1

    def cresc(t_peak, kind="Median", g=1.0, length=None):
        x, ci = lib["cresc"][kind]
        L = ci if length is None else min(ci, int(length * SR))
        seg = x[:, ci - L: ci + int(2.0 * SR)].copy()
        fade = (np.arange(seg.shape[1]) / max(1, L)).clip(0, 1) ** 1.6
        seg *= fade
        put("fx", t_peak - L / SR, seg, 0.8 * g)

    def timp(t, midi, vel=0.8):
        put("timp", t, M3.timp_hit(lib, midi, vel, nx()), 1.0)

    def sub(t, midi, d, g=1.0):
        f = mtof(midi)
        nn = int((d + 0.1) * SR)
        tt = tarr(nn)
        y = np.sin(2 * np.pi * f * tt) * np.minimum(1, tt / 0.01)
        y *= np.where(tt < d, 1.0, np.clip(1 - (tt - d) / 0.1, 0, 1))
        st["sub"].add(t, y, 0.5 * g)

    # ---- Streicher, Klavier
    def sus(t, name, d=BAR, g=1.0, vel=0.6, attack=0.1, voices=("cello", "viola", "violin")):
        ce, vi, vl, _ = CH[name]
        for k, m in enumerate(ce if "cello" in voices else []):
            put("strings", t - 0.02, lib["cello"].note(m, d, vel, 0.4, attack, rr=k), 0.9 * g, -0.3)
        for k, m in enumerate(vi if "viola" in voices else []):
            put("strings", t - 0.02, lib["viola"].note(m, d, vel, 0.4, attack, rr=k), 0.8 * g, 0.2)
        for k, m in enumerate(vl if "violin" in voices else []):
            put("strings", t - 0.02, lib["violin"].note(m, d, vel, 0.4, attack, rr=k), 0.75 * g, 0.35 if k % 2 else -0.15)

    def spic8(t_bar, name, vel=0.6, g=1.0, voices=("cello", "viola")):
        """Achtel-Spiccato: Celli auf Grundton/Quinte, Bratschen auf Akkordtönen, betont auf den Schlägen."""
        ce, vi, vl, _ = CH[name]
        for q in range(8):
            v = vel * (1.0 if q % 2 == 0 else 0.75)
            t = t_bar + q * BEAT / 2
            if "cello" in voices:
                put("spic", t, lib["cello_spic"].note(ce[q % 2] + (12 if q in (3, 7) else 0), 0.2, v, 0.12, 0, rr=q), 0.9 * g, -0.25)
            if "viola" in voices:
                put("spic", t, lib["viola_spic"].note(vi[(q // 2) % 2] + 12 * (q % 2), 0.2, v, 0.12, 0, rr=q), 0.8 * g, 0.25)
            if "violin" in voices:
                put("spic", t, lib["violin_spic"].note(vl[q % 3], 0.2, v, 0.12, 0, rr=q), 0.6 * g, 0.4)

    def piano(t, midi, vel=0.6, d=0.45, g=1.0, pan=0.0, rr=0):
        put("piano", t, lib["piano"].note(midi, d, vel, 0.25, 0.0, rr=rr), g * (0.4 + 0.9 * vel), pan)

    def arp(t_bar, name, vel=0.5, g=1.0):
        for q, m in enumerate(ARP[name]):
            piano(t_bar + q * BEAT / 2, m, min(1.0, vel * (1.1 if q == 0 else 0.9 if q % 2 else 1.0)), BEAT * 0.5, g, rr=q)

    def melody(t_bar, name, vel=0.7, g=1.0, violin=True, pianoon=True):
        for pos, m, ln in MOTIF[name]:
            t = t_bar + pos * BEAT / 2
            d = ln * BEAT / 2
            if violin:
                put("strings", t - 0.02, lib["violin"].note(m, d * 0.95, vel, 0.25, 0.03, rr=pos), 0.8 * g, 0.2)
            if pianoon:
                piano(t, m - 12, vel * 0.9, d * 0.95, 0.9 * g, pan=-0.1, rr=pos)

    def piano_chord(t, name, vel=0.7, octave=0, d=1.7, g=1.0, spread=0.0):
        ce, vi, vl, _ = CH[name]
        for k, m in enumerate(sorted(set(vi + vl))):
            piano(t + k * spread, m + 12 * octave, vel, d, g, pan=(k % 3 - 1) * 0.2, rr=k)

    # ---------------------------------------------------- A: Hook 0 bis 4 s
    for b in (0, 1):
        nm = chord(b)
        sus(b * BAR, nm, BAR, 0.8, 0.55 + 0.1 * b, 0.12, ("cello", "viola"))
        spic8(b * BAR, nm, 0.35 + 0.15 * b, 0.9)
        arp(b * BAR, nm, 0.45 + 0.1 * b, 0.8)
        sub(b * BAR, CH[nm][3], BAR - 0.1, 0.8)
    for k, tt in enumerate(CUES["hook_slams"]):
        kick(tt, (0.75, 0.9, 1.0)[k])
        timp(tt, 38 if k < 2 else 45, (0.6, 0.75, 0.95)[k])
        crash(tt, (0.45, 0.6, 0.8)[k])
    cresc(4.0, "Short", 0.8)
    snare_roll(3.0, 4.0, 0.2, 0.95)

    # ---------------------------------------------------- B: Problem 4 bis 12 s
    crash(4.0, 0.7)
    for b in range(2, 6):
        t_bar = b * BAR
        nm = chord(b)
        v = 0.45 + 0.07 * (b - 2)
        sus(t_bar, nm, BAR, 0.85, 0.5 + 0.05 * (b - 2), 0.15, ("cello", "viola") if b < 4 else ("cello", "viola", "violin"))
        spic8(t_bar, nm, v, 0.9, ("cello", "viola") if b < 4 else ("cello", "viola", "violin"))
        arp(t_bar, nm, v, 0.8)
        sub(t_bar, CH[nm][3], BAR - 0.1, 0.9)
        kick(t_bar, 0.75)
        kick(t_bar + 2 * BEAT, 0.7)
        tamb_bar(t_bar, 0.35 + 0.05 * (b - 2), offbeats_only=b < 4)
    timp(4.0, 38, 0.8)
    for k, tt in enumerate(CUES["problem_cards"]):
        piano(tt, (62, 66, 69, 74)[k], 0.8, 0.8, 1.2)
    crash(CUES["problem_banner"][0], 0.8)
    timp(CUES["problem_banner"][0], 47, 0.9)
    piano_chord(CUES["problem_banner"][0], "D", 0.8, octave=-1, d=1.5)
    piano(CUES["problem_banner"][1], 66, 0.7, 0.6, 1.0)
    cresc(12.0, "Median", 1.0)
    snare_roll(10.5, 11.75, 0.2, 0.95)
    mute.append((11.75, 12.0))

    # ---------------------------------------------------- C: Lösung 12 bis 22 s
    crash(12.0, 1.0, ff=True)
    timp(12.0, 38, 1.0)
    for b in range(6, 11):
        t_bar = b * BAR
        nm = chord(b)
        sus(t_bar, nm, BAR, 1.0, 0.75, 0.1)
        spic8(t_bar, nm, 0.65, 0.9, ("cello", "viola", "violin"))
        arp(t_bar, nm, 0.5, 0.7)
        sub(t_bar, CH[nm][3], BAR - 0.1, 1.0)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.9 if q % 2 == 0 else 0.75)
            if q in (1, 3):
                snare(t_bar + q * BEAT, 0.85)
        tamb_bar(t_bar, 0.55)
        if b <= 9:
            melody(t_bar, nm, 0.75, 1.0)
        if b % 2 == 0:
            timp(t_bar, TIMP[nm], 0.7)
    for tt in CUES["loesung_lines"]:
        crash(tt, 0.55)
        timp(tt, 38 if tt == 13.0 else 45, 0.85)
    crash(CUES["loesung_card"], 0.7)
    timp(CUES["loesung_card"], 43, 0.9)
    for k, tt in enumerate(CUES["loesung_bullets"]):
        piano(tt, (66, 69, 74)[k], 0.85, 0.7, 1.2)
        tamb(tt, 0.9)
    cresc(22.0, "Short", 0.8)
    snare_roll(20.5, 22.0, 0.3, 0.95)

    # ---------------------------------------------------- D: Produkt 22 bis 38 s
    crash(22.0, 0.9)
    timp(22.0, 38, 0.85)
    for b in range(11, 19):
        t_bar = b * BAR
        nm = chord(b)
        sus(t_bar, nm, BAR, 0.8 if b < 15 else 1.0, 0.6 if b < 15 else 0.75, 0.1,
            ("cello", "viola") if b < 13 else ("cello", "viola", "violin"))
        spic8(t_bar, nm, 0.55, 0.85, ("cello", "viola") if b < 13 else ("cello", "viola", "violin"))
        arp(t_bar, nm, 0.5, 0.75)
        sub(t_bar, CH[nm][3], BAR - 0.1, 0.9)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.8 if q % 2 == 0 else 0.65)
            if q in (1, 3):
                snare(t_bar + q * BEAT, 0.7)
        tamb_bar(t_bar, 0.5)
        if b >= 15:
            melody(t_bar, nm, 0.75, 1.0)
    for tt in CUES["produkt_cuts"][1:]:
        crash(tt, 0.7)
        timp(tt, 38, 0.7)
    for tt in CUES["produkt_callouts"]:
        piano(tt, 81, 0.75, 0.9, 1.0)
        tamb(tt, 0.9)
    cresc(38.0, "Median", 0.9)
    snare_roll(36.0, 37.75, 0.2, 0.95)
    mute.append((37.75, 38.0))

    # ---------------------------------------------------- E: Vertrauen 38 bis 44 s
    crash(38.0, 0.8)
    timp(38.0, 47, 0.85)
    for b in range(19, 22):
        t_bar = b * BAR
        nm = chord(b)
        sus(t_bar, nm, BAR, 0.9, 0.5 + 0.05 * (b - 19), 0.25)
        arp(t_bar, nm, 0.4 + 0.05 * (b - 19), 0.85)
        sub(t_bar, CH[nm][3], BAR - 0.1, 0.8)
        kick(t_bar, 0.6)
        kick(t_bar + 2 * BEAT, 0.55)
        if b >= 20:
            spic8(t_bar, nm, 0.4 + 0.1 * (b - 20), 0.8)
    for k, tt in enumerate(CUES["vertrauen_lines"]):
        piano_chord(tt, chord(int(tt // BAR)), 0.8, octave=-1, d=1.5, g=1.0)
        timp(tt, (47, 43, 45)[k], 0.65)
    cresc(44.0, "Short", 0.9)
    snare_roll(43.0, 43.875, 0.2, 0.9)
    mute.append((43.875, 44.0))

    # ---------------------------------------------------- F: Abbinder 44 bis 49 s
    crash(44.0, 1.0, ff=True)
    timp(44.0, 38, 1.0)
    for b, t_bar in ((22, 44.0), (23, 46.0)):
        nm = chord(b)
        sus(t_bar, nm, BAR, 1.1, 0.85, 0.08)
        spic8(t_bar, nm, 0.7, 0.9, ("cello", "viola", "violin"))
        arp(t_bar, nm, 0.5, 0.7)
        melody(t_bar, nm, 0.85, 1.0)
        sub(t_bar, CH[nm][3], BAR - 0.1, 1.0)
        for q in range(4):
            kick(t_bar + q * BEAT, 0.95 if q % 2 == 0 else 0.8)
            if q in (1, 3):
                snare(t_bar + q * BEAT, 0.9)
        tamb_bar(t_bar, 0.6)
    for k, tt in enumerate(CUES["abbinder_lines"]):
        crash(tt, 0.6)
        timp(tt, 38 if k == 0 else 45, 0.9)
    piano(CUES["abbinder_pill"], 81, 0.8, 1.2, 1.0)
    piano(CUES["abbinder_pill"], 86, 0.7, 1.2, 0.8)
    # Schluss: D-Dur, lang ausklingend
    sus(48.0, "D", 3.4, 1.15, 0.85, 0.06)
    sub(48.0, 38, 2.8, 1.0)
    kick(48.0, 1.0)
    timp(48.0, 38, 1.0)
    crash(48.0, 1.0, ff=True)
    piano_chord(48.0, "D", 0.85, octave=0, d=2.8, g=1.0, spread=0.05)
    piano(48.0, 74, 0.8, 2.8, 1.0)

    # ---------------------------------------------------- Sidechain (leicht), Stopps
    duck = np.ones(n)
    ln = int(0.25 * SR)
    prof = 1 - 0.22 * (1 - np.arange(ln) / ln) ** 2
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


GAINS = {"strings": 0.85, "spic": 0.95, "piano": 0.7, "timp": 0.75, "drums": 1.2, "perc": 1.2, "sub": 0.65, "fx": 0.6}
# Lautheitsverlauf (Sekunde, dB): ruhiger Einstieg, Drop bei 12 s, zurückgenommen im Vertrauensteil, Finale voll
SECTION_DB = [(0, -5), (3.9, -4), (4.0, -4.5), (11.7, -2.5), (12.0, 0), (21.9, 0), (22.0, -2), (37.7, -1.5), (38.0, -5.5),
              (43.5, -4.5), (44.0, 0), (47.5, 0), (49.0, -1)]


def mixdown(parts, g=None, section_db=None, reverb=0.3):
    g = {**GAINS, **(g or {})}
    st, duck, gate, n = parts["stems"], parts["duck"], parts["gate"], parts["n"]

    def mix(name, ducked=0.0, gated=True):
        d = st[name].d * g[name]
        if ducked:
            d = d * (1 - ducked + ducked * duck)
        return d * gate if gated else d

    send = mix("strings") * 0.6 + mix("spic") * 0.5 + mix("piano") * 0.6 + mix("timp") * 0.4 + mix("perc") * 0.2
    rev_board = pb.Pedalboard([pb.HighpassFilter(220), pb.LowpassFilter(9000),
                               pb.Reverb(room_size=0.75, damping=0.5, wet_level=1.0, dry_level=0.0, width=1.0)])
    rev = rev_board(send.astype(np.float32), SR).astype(np.float64)
    dry = (mix("strings", 0.4) + mix("spic", 0.3) + mix("piano") + mix("timp") + mix("drums") + mix("perc") +
           mix("sub", 0.4) + mix("fx", gated=False))
    out = dry + rev * reverb
    chain = pb.Pedalboard([
        pb.HighpassFilter(30),
        pb.Compressor(threshold_db=-18.0, ratio=2.0, attack_ms=25.0, release_ms=180.0),
        pb.PeakFilter(cutoff_frequency_hz=300, gain_db=-1.0, q=0.8),
        pb.HighShelfFilter(cutoff_frequency_hz=5000, gain_db=2.0),
    ])
    out = chain(out.astype(np.float32), SR).astype(np.float64)
    pts = section_db or SECTION_DB
    t = np.arange(out.shape[1]) / SR
    out = out * 10 ** (np.interp(t, [p[0] for p in pts], [p[1] for p in pts]) / 20)
    out = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=100.0)])(out.astype(np.float32), SR).astype(np.float64)
    out = out[:, :int(DUR * SR)]
    return out / (np.max(np.abs(out)) or 1.0) * 0.89


def render(dur=DUR):
    return mixdown(build_stems(dur))


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "music4.wav"
    y = render()
    write_wav(dest, y)
    rms = np.sqrt(np.mean(y ** 2))
    print(f"fertig: {dest}  {y.shape[1] / SR:.1f} s  RMS {20 * np.log10(rms):.1f} dBFS  Spitze {20 * np.log10(np.max(np.abs(y))):.1f} dBFS")
