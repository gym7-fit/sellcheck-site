"""Musik für das SellCheck-Corporate-Video, Version 7: Herzklopfen und Erleichterung, mit Platz für die Stimme.

Dramaturgie als Körpergefühl in zwei Hälften:

  Angst (0 bis 12 s)   Die Fakten. Herzklopfen, das mit jeder Einblendung schneller und dichter wird, kurze
                       Atemstöße beim Erschrecken, ein Schock-Moment bei der Meldegrenze (8 s), dann Luft
                       anhalten: 0,28 s völlige Stille vor SellCheck.
  Erleichterung (12 s+) Kein Herzschlag mehr. Ein langes Ausatmen, ein warmer Dur-Klang, der langsam
                       aufblüht, wenige weiche Klavierakkorde, ein tiefer, ruhiger Grundton. Nichts treibt.

Gesprochener Text kommt später darüber (Sprecherfenster siehe SPRECHERTEXT.md): Die Musik ist deshalb
ein dünnes Bett. Die Mitten (300 Hz bis 3 kHz) sind im Erleichterungsteil nur vom Pad und von leisen
Klavierakkorden besetzt, es gibt keine Hi-Hats, Claps oder Atem-Zischer mehr, und der Pegel ist niedrig.

    .venv/bin/python corporate_music7.py out.wav
"""
import sys
import warnings

import numpy as np
import pedalboard as pb

import corporate_music2 as M2
import corporate_music3 as M3
import corporate_music6 as M6
from corporate_music2 import CUES, DUR, SR, TAIL, BEAT, BAR, Stem, mtof, tarr, write_wav, lp, hp

warnings.filterwarnings("ignore")
rng = np.random.default_rng(67)

NOTES = {"D": [50, 57, 62, 66, 69], "A": [45, 52, 57, 61, 64], "Bm": [47, 54, 59, 62, 66], "G": [43, 50, 55, 59, 62]}
LOOP = ["D", "A", "Bm", "G"]


def knock(kind="lub", dur=0.24):
    """Herzklopfen: rund und warm, mit hörbarem Brustkorb-Klopfen in den Mitten, trocken, kurzes Ausklingen."""
    n = int(dur * SR)
    t = tarr(n)
    f = 74.0 if kind == "lub" else 92.0
    fr = f * (1 + 0.55 * np.exp(-t / 0.022))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    body = np.sin(ph) * np.exp(-t / 0.065)
    h2 = 0.45 * np.sin(2 * ph) * np.exp(-t / 0.045)
    thud = lp(rng.uniform(-1, 1, n), 700) * np.exp(-t / 0.014) * 0.5
    y = np.tanh(1.2 * (body + h2 + thud)) * np.clip(t / 0.004, 0, 1)
    y *= np.clip((n - np.arange(n)) / (0.03 * SR), 0, 1)
    return y / (np.abs(y).max() or 1.0)


def build_stems(dur=DUR):
    n = int((dur + TAIL) * SR)
    lib = M3.load_library()
    st = {k: Stem(n) for k in ("air", "heart", "pad", "piano", "sub", "fx")}
    mute = []
    lub, dub = knock("lub"), knock("dub")

    def heart(t, g=1.0, gap=0.15):
        st["heart"].add(t, lub, 0.9 * g)
        st["heart"].add(t + gap, dub, 0.62 * g)

    def gasp(t, g=1.0, d=0.12):
        l, r = M6.breath_in(d)
        st["air"].add_st(t, l, r, 0.8 * g)

    def exhale(t, g=1.0, d=1.6):
        l, r = M6.breath_out(d)
        st["air"].add_st(t, l, r, 0.7 * g)

    def sub(t, midi, d, g=1.0, a=0.6):
        f = mtof(midi)
        nn = int((d + 0.4) * SR)
        tt = tarr(nn)
        y = np.sin(2 * np.pi * f * tt) * np.clip(tt / a, 0, 1)
        y *= np.where(tt < d, 1.0, np.clip(1 - (tt - d) / 0.4, 0, 1))
        st["sub"].add(t, y, 0.5 * g)

    def pad(t, notes, d, fc0, fc1, g=1.0, fade_in=0.6):
        l, r = M2.pad_chord(notes, d, fc0, fc1)
        ramp = np.clip(tarr(len(l)) / max(fade_in, 0.01), 0, 1) ** 1.5
        st["pad"].add_st(t, l * ramp, r * ramp, g)

    def piano_chord(t, name, vel=0.4, d=2.2, g=1.0, spread=0.045):
        for k, m in enumerate(NOTES[name][:4]):
            x = lib["piano"].note(m, d, vel, 0.5, 0.0, rr=k)
            st["piano"].add_st(t + k * spread, x[0], x[1], g * (0.4 + 0.9 * vel) * (0.9 if k == 0 else 1.0))

    # ---------------------------------------------------- Angst: Hook 0 bis 4 s
    # Bewusst wenig: drei einzelne Schläge zu den drei Einblendungen, sonst nur ein leiser Boden.
    pad(0.0, NOTES["D"], 12.0, 300, 700, 0.35, fade_in=2.0)
    for k, tt in enumerate(CUES["hook_slams"]):
        heart(tt, (0.6, 0.8, 1.0)[k], 0.15)

    # ---------------------------------------------------- Angst: Problem 4 bis 12 s
    # erst ein Schlag pro Sekunde, ab 6 s auf jedem Schlag; die Karten bekommen keine eigenen Geräusche mehr
    t = 4.0
    while t < 6.0 - 1e-6:
        heart(t, 0.7 + 0.1 * (t - 4.0) / 2.0, 0.15)
        t += 1.0
    while t < 8.0 - 1e-6:
        heart(t, 0.85, 0.14)
        t += 0.5
    t8 = CUES["problem_banner"][0]
    gasp(t8 - 0.24, 0.8, 0.24)                    # Einatmen vor dem Schock
    heart(t8, 1.2, 0.13)                          # ein harter Doppelschlag
    mute.append((t8 + 0.34, t8 + 0.56))          # kurzer Aussetzer
    # danach wird das Herzklopfen schneller, aber nie hektisch (Abstand 0,5 s bis 0,3 s)
    t, step = 8.6, 0.5
    while t < 11.72:
        heart(t, 0.85 + 0.12 * (t - 8.6) / 3.0, 0.14)
        t += step
        step = max(0.3, step - 0.04)
    mute.append((11.72, 12.0))                    # Luft anhalten

    # ---------------------------------------------------- Aha: 12 bis 22 s
    # Aufklaren: Ausatmen, das Pad geht gleich hell auf, ein hoher weicher Akkord wie ein Lichtblick
    exhale(12.0, 0.8, 1.9)
    pad(12.0, NOTES["D"], 10.0, 1800, 2500, 1.0, fade_in=0.5)
    pad(12.0, [62, 69, 74, 78], 6.0, 2600, 2200, 0.35, fade_in=0.4)
    sub(12.0, 38, 9.6, 0.8, 0.8)
    for k, m in enumerate((74, 78, 81, 86)):
        x = lib["piano"].note(m, 3.2, 0.5, 0.8, 0.0, rr=k)
        st["piano"].add_st(12.0 + k * 0.04, x[0], x[1], 0.9 if k < 3 else 0.6)
    for b in range(7, 11):
        piano_chord(b * BAR, LOOP[(b - 6) % 4], 0.36, 2.4, 0.85)

    # ---------------------------------------------------- 22 bis 38 s (Produkt, ruhig)
    pad(22.0, NOTES["D"], 16.0, 900, 2000, 0.85, fade_in=1.0)
    sub(22.0, 38, 15.6, 0.7, 1.0)
    for b in range(11, 19, 2):
        piano_chord(b * BAR, LOOP[(b - 6) % 4], 0.33, 3.8, 0.85)
    for tt in CUES["produkt_callouts"]:            # kleines, helles "Aha" bei jeder Markierung
        x = lib["piano"].note(86, 2.0, 0.3, 0.6, 0.0, rr=int(tt))
        st["piano"].add_st(tt, x[0], x[1], 0.5)

    # ---------------------------------------------------- 38 bis 44 s (Vertrauen)
    pad(38.0, [38, 45, 50, 54, 57], 6.0, 700, 1400, 0.8, fade_in=1.0)
    sub(38.0, 38, 5.8, 0.6, 1.0)
    for b in (19, 21):
        piano_chord(b * BAR, LOOP[(b - 6) % 4], 0.3, 3.0, 0.8)

    # ---------------------------------------------------- Abbinder 44 bis 51 s (abrunden und ausklingen)
    exhale(44.0, 0.7, 1.6)
    pad(44.0, NOTES["D"] + [74], 4.0, 1400, 2800, 1.0, fade_in=0.3)
    sub(44.0, 38, 3.9, 0.9, 0.2)
    piano_chord(44.0, "G", 0.5, 2.0, 1.0)
    piano_chord(46.0, "A", 0.5, 2.0, 1.0)
    # Auflösung: D-Dur als gebrochener Akkord, der aufsteigt und lange im Hall ausklingt
    pad(48.0, NOTES["D"] + [74], 4.5, 2000, 1500, 1.1, fade_in=0.25)
    sub(48.0, 38, 3.6, 0.9, 0.3)
    for k, m in enumerate((50, 57, 62, 66, 69, 74)):
        x = lib["piano"].note(m, 3.4, 0.5, 1.2, 0.0, rr=k)
        st["piano"].add_st(48.0 + k * 0.11, x[0], x[1], 0.95 if k < 5 else 0.75)
    exhale(48.0, 0.5, 2.6)
    for k, m in enumerate((81, 86)):
        x = lib["piano"].note(m, 2.0, 0.28, 1.2, 0.0, rr=k)
        st["piano"].add_st(48.9 + k * 0.5, x[0], x[1], 0.45)

    gate = np.ones(n)
    for a, b in mute:
        ia, ib = int(a * SR), int(b * SR)
        r = int(0.006 * SR)
        gate[ia:ib] = 0.0
        gate[max(0, ia - r):ia] = np.linspace(1, 0, ia - max(0, ia - r))
        gate[ib:ib + r] = np.linspace(0, 1, min(r, n - ib))
    return {"stems": st, "gate": gate, "n": n}


GAINS = {"air": 3.0, "heart": 1.3, "pad": 1.5, "piano": 1.0, "sub": 0.28, "fx": 0.5}
SECTION_DB = [(0, -1.5), (11.7, -0.5), (12.0, -2), (43.9, -2), (44.0, 0), (48.0, 0), (51.0, -3)]


def mixdown(parts, g=None, reverb=0.25):
    g = {**GAINS, **(g or {})}
    st, gate, n = parts["stems"], parts["gate"], parts["n"]
    f32 = lambda a: a.astype(np.float32)

    def get(name, gated=True):
        d = st[name].d * g[name]
        return d * gate if gated else d

    pad = pb.Pedalboard([pb.Chorus(rate_hz=0.3, depth=0.25, mix=0.3), pb.LowpassFilter(5000)])(f32(get("pad")), SR).astype(np.float64)
    send = pad * 0.5 + get("air") * 0.3 + get("piano") * 0.6
    rev = pb.Pedalboard([pb.HighpassFilter(250), pb.LowpassFilter(7500),
                         pb.Reverb(room_size=0.8, damping=0.6, wet_level=1.0, dry_level=0.0, width=1.0)])(f32(send), SR).astype(np.float64)
    dry = get("heart") + get("air", gated=False) + pad + get("piano") + get("sub") + get("fx", gated=False)
    out = dry + rev * reverb
    out = pb.Pedalboard([pb.HighpassFilter(30), pb.Compressor(threshold_db=-20.0, ratio=1.8, attack_ms=25.0, release_ms=200.0)])(f32(out), SR).astype(np.float64)
    t = np.arange(out.shape[1]) / SR
    out = out * 10 ** (np.interp(t, [p[0] for p in SECTION_DB], [p[1] for p in SECTION_DB]) / 20)
    out = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=100.0)])(f32(out), SR).astype(np.float64)
    out = out[:, :int(DUR * SR)]
    return out / (np.max(np.abs(out)) or 1.0) * 0.89


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "music7.wav"
    y = mixdown(build_stems())
    write_wav(dest, y)
    print(f"fertig: {dest}  {y.shape[1] / SR:.1f} s  RMS {20 * np.log10(np.sqrt(np.mean(y ** 2))):.1f} dBFS")
