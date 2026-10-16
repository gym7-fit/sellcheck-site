"""Musik für das SellCheck-Corporate-Video, Version 6: der Atem. Sounddesign statt Melodie.

Idee: Die Fakten fliegen ins Bild, die Person erschrickt. Der Ton ist ein Körper, der darauf reagiert.

  Hook         drei Einblendungen = drei kurze Atemzüge (überrascht, nicht unheimlich), danach ein Herzschlag
  Problem      vier Karten = vier leise Atemstöße; die Meldegrenze kommt als Einatmen mit kurzer Stille;
               danach wird der Herzschlag dichter, das Pad öffnet sich, dann Luft anhalten vor dem Drop
  Lösung       Ausatmen bei 12,0 s (Erleichterung), das Pad blüht zu offenem D-Dur auf; Herzschlag auf jedem
               Schlag, dazu leise Hi-Hats
  Produkt      ruhiger: Herzschlag nur auf 1 und 3, Pad bleibt stehen, nur ein leises Ausatmen je Schnitt
  Vertrauen    ruhiger Herzschlag, ein Seufzer je Aussage
  Abbinder     Ausatmen mit vollem Klang und Herzschlag-Groove, am Ende ein langes Ausatmen

Alle Töne sind synthetisiert: Atem als weicher, vokalartiger Hauch (rosa Rauschen durch Formanten, etwas
Stimmanteil, nichts über ca. 4 kHz), Herzschlag (Lub-Dub) als rhythmisches Rückgrat, Pad. Kaum Tonhöhen:
nur Grundton D und ein offener Dur-Akkord für die Erleichterung. Alle Einsätze liegen auf CUES.

    .venv/bin/python corporate_music6.py out.wav
"""
import sys

import numpy as np
import pedalboard as pb

import corporate_music2 as M2
from corporate_music2 import CUES, DUR, SR, TAIL, BEAT, BAR, Stem, mtof, tarr, write_wav, lp, hp

rng = np.random.default_rng(53)


# ------------------------------------------------------------------ Atem-Bausteine
PINK_B = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
PINK_A = [1, -2.494956002, 2.017265875, -0.522189400]
VOWEL = {            # (F1, F2, F3) in Hz
    "a": (730, 1250, 2600),
    "o": (450, 850, 2450),
    "i": (320, 2100, 2900),
    "u": (330, 700, 2400),
}


def _pink(n):
    from scipy.signal import lfilter
    return lfilter(PINK_B, PINK_A, rng.uniform(-1, 1, n + 2000))[2000:]


def _formants(x, vowel, q=5.0):
    out = np.zeros_like(x)
    for f, gain in zip(VOWEL[vowel], (1.0, 0.7, 0.35)):
        lo, hi = f * (1 - 0.5 / q * 2), f * (1 + 0.5 / q * 2)
        out += gain * M2.bp(x, lo, hi, 2)
    return out


def _breath(dur, v0, v1, voiced, f_voice, env, tail):
    """Atemzug als weicher, vokalartiger Hauch: rosa Rauschen durch Formanten, dazu ein Stimmanteil.
    Der Vokal wandert von v0 nach v1 (Überblendung), alles unter ca. 4 kHz."""
    n = int((dur + tail) * SR)
    t = tarr(n)
    out = []
    for ch in range(2):
        src = _pink(n)
        a = _formants(src, v0)
        b = _formants(src, v1)
        x = np.linspace(0, 1, n) ** 0.8
        mixed = a * (1 - x) + b * x
        if voiced > 0:
            f = f_voice * (1 + 0.01 * np.sin(2 * np.pi * (4.5 + 0.5 * ch) * t))
            gl = M2.saw(f, 2, rng.random())
            gv = _formants(gl, v0) * (1 - x) + _formants(gl, v1) * x
            mixed = mixed + voiced * gv * 0.6
        y = lp(mixed, 3800, 2) * env(t, dur)
        out.append(y)
    pk = max(np.abs(out[0]).max(), np.abs(out[1]).max()) or 1.0
    return out[0] / pk, out[1] / pk


def breath_in(dur=0.3, f0=700.0, f1=3400.0, rasp=0.35):
    """Einatmen ("haa", Vokal wandert o -> a), weicher Anstieg, kurzes Abklingen."""
    def env(t, d):
        e = np.clip(t / (0.45 * d), 0, 1) ** 1.6
        e *= np.where(t < d, 1.0, np.exp(-(t - d) / 0.05))
        return e
    return _breath(dur, "a", "i", 0.0, 120.0, env, 0.2)


def breath_out(dur=1.3, f0=4200.0, f1=650.0, soft=1.0):
    """Ausatmen ("haaah", Vokal wandert a -> u), weicher Anstieg, langes Ausklingen."""
    def env(t, d):
        return np.clip(t / (0.08 * soft + 0.03), 0, 1) ** 1.3 * np.exp(-t / (d * 0.42))
    return _breath(dur, "a", "o", 0.04, 105.0, env, 0.1)


def soft_riser(dur):
    """Anstieg aus weichem Rauschen, oben bei ca. 3 kHz abgeschnitten (nichts Schneidendes)."""
    l, r = M2.make_riser(dur, 200, 3200)
    return lp(l, 3500, 2), lp(r, 3500, 2)


def thump(f=52.0, dur=0.3, soft=1.0):
    """Herzschlag-Schlag: tiefer Sinus mit leichtem Tonhöhenabfall, weicher Anschlag, kein Klick."""
    n = int(dur * SR)
    t = tarr(n)
    fr = f * (1 + 0.9 * np.exp(-t / 0.03))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / (0.085 * soft)) * np.clip(t / 0.006, 0, 1)
    y += lp(rng.uniform(-1, 1, n), 260) * np.exp(-t / 0.03) * 0.12
    return np.tanh(1.3 * y) * np.clip((n - np.arange(n)) / (0.02 * SR), 0, 1)


def pff(dur=0.14):
    """Kurzer Luftstoß als Snare: Rauschen mit Körper."""
    n = int(dur * SR)
    t = tarr(n)
    x = M2.bp(_pink(n), 500, 3200) * np.exp(-t / 0.04)
    x += np.sin(2 * np.pi * 170 * t) * np.exp(-t / 0.05) * 0.5
    return np.tanh(1.3 * x) / 1.0


def tss(dur=0.07):
    n = int(dur * SR)
    t = tarr(n)
    x = M2.bp(_pink(n), 2500, 5200) * np.exp(-t / 0.03)
    return x / (np.abs(x).max() or 1.0)


def ring(dur=1.0, f=4300.0):
    n = int(dur * SR)
    t = tarr(n)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.51 * t)) * np.exp(-t / (dur * 0.45)) * np.clip(t / 0.01, 0, 1)


# ------------------------------------------------------------------ Aufbau
def build_stems(dur=DUR):
    n = int((dur + TAIL) * SR)
    st = {k: Stem(n) for k in ("air", "body", "perc", "pad", "sub", "fx")}
    mute = []          # (t0, t1): alles außer "air" stumm (Luft anhalten, Schock)
    kick_times = []
    thump_s, pff_s, tss_s = thump(), pff(), tss()

    def gasp(t, g=1.0, f0=700.0, f1=3400.0, d=0.28):
        l, r = breath_in(d, f0, f1)
        st["air"].add_st(t, l, r, 0.8 * g)

    def exhale(t, g=1.0, d=1.3, f0=4200.0, f1=650.0):
        l, r = breath_out(d, f0, f1)
        st["air"].add_st(t, l, r, 0.7 * g)

    def beat_thump(t, g=1.0, f=52.0):
        st["body"].add(t, thump_s if f == 52.0 else thump(f), 0.9 * g)
        kick_times.append(t)

    def heart(t, g=1.0, gap=0.17):
        beat_thump(t, g)
        beat_thump(t + gap, 0.6 * g, 46.0)

    def sub(t, midi, d, g=1.0, a=0.05):
        f = mtof(midi)
        nn = int((d + 0.2) * SR)
        tt = tarr(nn)
        y = np.sin(2 * np.pi * f * tt) * np.clip(tt / a, 0, 1)
        y *= np.where(tt < d, 1.0, np.clip(1 - (tt - d) / 0.2, 0, 1))
        st["sub"].add(t, y, 0.5 * g)

    def pad(t, notes, d, fc0, fc1, g=1.0):
        l, r = M2.pad_chord(notes, d, fc0, fc1)
        st["pad"].add_st(t, l, r, g)

    def puff(t, g=1.0):
        st["perc"].add(t, pff_s, 0.7 * g)

    def hat(t, g=0.5, pan=0.3):
        st["perc"].add(t, tss_s, 0.4 * g, pan)

    def groove(t_bar, level=1.0, hats=True, full=True, hat_every=1):
        """Der Rhythmus ist ein Herzschlag bei 120 bpm (Lub-Dub). full: auf jedem Schlag, sonst nur auf 1 und 3."""
        for q in range(4):
            if full or q % 2 == 0:
                heart(t_bar + q * BEAT, (1.0 if q % 2 == 0 else 0.8) * level, 0.16)
        if hats:
            for q in range(1, 8, 2):
                hat(t_bar + q * BEAT / 2, 0.4 * level, pan=0.3 if q % 4 == 1 else -0.3)

    # ---------------------------------------------------- A: Hook 0 bis 4 s
    # Drei Einblendungen = drei Atemzüge (kurz, hell, überrascht statt unheimlich), dann ein Herzschlag.
    pad(0.0, [38, 45, 50, 54, 57], 4.0, 350, 1100, 0.7)
    sub(0.0, 38, 3.9, 0.5, 1.2)
    for k, tt in enumerate(CUES["hook_slams"]):
        gasp(tt, (0.5, 0.65, 0.85)[k], 900 + 300 * k, 3000 + 500 * k, 0.1)
        beat_thump(tt, (0.6, 0.8, 1.0)[k])
    for tt in (2.5, 3.0, 3.5):
        heart(tt, 0.55 + 0.2 * (tt - 2.5))
    st["fx"].add_st(2.0, *soft_riser(2.0), 0.2)

    # ---------------------------------------------------- B: Problem 4 bis 12 s
    pad(4.0, [38, 45, 50, 54, 57], 8.0, 500, 1800, 0.65)
    sub(4.0, 38, 7.7, 0.5, 1.5)
    for b in range(2, 6):
        for q in (0, 2):
            heart(b * BAR + q * BEAT, 0.6 + 0.08 * (b - 2))
    for k, tt in enumerate(CUES["problem_cards"]):
        gasp(tt, 0.4 + 0.05 * k, 1000 + 200 * k, 3200, 0.08)
    t8 = CUES["problem_banner"][0]
    gasp(t8 - 0.22, 0.9, 700, 3400, 0.22)          # Einatmen direkt vor der Meldegrenze
    beat_thump(t8, 1.1, 42.0)
    mute.append((t8 + 0.02, t8 + 0.3))             # kurzer Moment Stille
    gasp(CUES["problem_banner"][1], 0.35, 1100, 3000, 0.08)
    # Anstieg: Herzschlag wird dichter, das Pad öffnet sich
    for tt in (9.0, 9.5, 10.0, 10.5, 10.75, 11.0, 11.25, 11.5):
        heart(tt, 0.65 + 0.3 * (tt - 9.0) / 2.5, 0.14)
    st["fx"].add_st(9.0, *soft_riser(3.0), 0.3)
    mute.append((11.72, 12.0))

    # ---------------------------------------------------- C: Lösung 12 bis 22 s
    exhale(12.0, 0.9, 1.4, 4000, 700)
    beat_thump(12.0, 1.3, 42.0)
    sub(12.0, 38, 9.8, 0.9, 0.02)
    pad(12.0, [50, 57, 62, 66, 69], 10.0, 1400, 3000, 0.75)
    for b in range(6, 11):
        groove(b * BAR, 1.0, hats=True, full=True)
    for tt in CUES["loesung_lines"]:
        exhale(tt, 0.35, 0.4, 3200, 900)
    exhale(CUES["loesung_card"], 0.45, 0.7, 3600, 800)
    for k, tt in enumerate(CUES["loesung_bullets"]):
        hat(tt, 1.0 + 0.1 * k, pan=-0.3 + 0.3 * k)
    st["fx"].add_st(20.0, *soft_riser(2.0), 0.25)

    # ---------------------------------------------------- D: Produkt 22 bis 38 s (ruhig)
    pad(22.0, [50, 57, 62, 66, 69], 16.0, 1500, 2600, 0.7)
    sub(22.0, 38, 15.8, 0.6, 0.5)
    for b in range(11, 19):
        groove(b * BAR, 0.75 if b < 15 else 0.85, hats=(b % 2 == 1), full=False)
    for tt in CUES["produkt_cuts"]:
        exhale(tt, 0.3, 0.5, 3000, 800)
    for tt in CUES["produkt_callouts"]:
        hat(tt, 1.2, pan=0.2)
    st["fx"].add_st(35.0, *soft_riser(3.0), 0.25)
    mute.append((37.78, 38.0))

    # ---------------------------------------------------- E: Vertrauen 38 bis 44 s
    exhale(38.0, 0.5, 1.2, 3200, 700)
    pad(38.0, [38, 45, 50, 54, 57], 6.0, 800, 1500, 0.7)
    sub(38.0, 38, 5.8, 0.5, 0.5)
    for tt in (38.0, 40.0, 42.0):
        heart(tt, 0.5, 0.2)
    for tt in CUES["vertrauen_lines"][1:]:
        exhale(tt, 0.35, 0.9, 3000, 700)
    st["fx"].add_st(42.0, *soft_riser(2.0), 0.2)
    mute.append((43.9, 44.0))

    # ---------------------------------------------------- F: Abbinder 44 bis 49 s
    exhale(44.0, 0.9, 1.3, 4000, 700)
    beat_thump(44.0, 1.2, 42.0)
    sub(44.0, 38, 2.0, 1.0, 0.02)
    pad(44.0, [50, 57, 62, 66, 69, 74], 5.0, 1800, 3200, 0.8)
    groove(44.0, 1.0, hats=True, full=True)
    groove(46.0, 0.7, hats=False, full=False)
    for tt in CUES["abbinder_lines"]:
        exhale(tt, 0.3, 0.45, 3200, 900)
    hat(CUES["abbinder_pill"], 1.0, pan=0.0)
    sub(46.0, 43, 1.9, 0.7)
    sub(48.0, 38, 2.9, 1.0, 0.02)
    exhale(48.0, 0.7, 2.4, 4000, 600)
    beat_thump(48.0, 0.9, 44.0)

    # ---------------------------------------------------- Sidechain, Stopps, Atemmodulation des Pads
    duck = np.ones(n)
    ln = int(0.28 * SR)
    prof = 1 - 0.5 * (1 - np.arange(ln) / ln) ** 2
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
    t = np.arange(n) / SR
    breath = np.ones(n)
    for a, b, cyc in ((12.0, 38.0, 4.0), (38.0, 44.0, 4.0), (44.0, 48.0, 4.0)):
        m = (t >= a) & (t < b)
        ph = ((t[m] - a) % cyc) / cyc
        breath[m] = 0.8 + 0.2 * np.sin(np.pi * ph) ** 1.4      # Einatmen (Anstieg) und Ausatmen (Abfall)
    return {"stems": st, "duck": duck, "gate": gate, "breath": breath, "n": n}


GAINS = {"air": 3.6, "body": 0.5, "perc": 1.5, "pad": 1.8, "sub": 0.25, "fx": 0.6}
SECTION_DB = [(0, -2), (3.9, -2), (4.0, -2.5), (11.7, -1.5), (12.0, 0), (21.9, 0), (22.0, 0.5), (37.7, 0.5),
              (38.0, -3), (43.5, -3), (44.0, 0), (47.5, 0), (49.0, -1)]


def mixdown(parts, g=None, reverb=0.3):
    g = {**GAINS, **(g or {})}
    st, duck, gate, breath, n = parts["stems"], parts["duck"], parts["gate"], parts["breath"], parts["n"]
    f32 = lambda a: a.astype(np.float32)

    def get(name, ducked=0.0, gated=True):
        d = st[name].d * g[name]
        if ducked:
            d = d * (1 - ducked + ducked * duck)
        return d * gate if gated else d

    pad = pb.Pedalboard([pb.Chorus(rate_hz=0.3, depth=0.25, mix=0.3), pb.LowpassFilter(9000)])(f32(get("pad", 0.6) * breath), SR).astype(np.float64)
    air = get("air", gated=False)
    send = pad * 0.4 + air * 0.5 + get("perc") * 0.3
    rev = pb.Pedalboard([pb.HighpassFilter(250), pb.LowpassFilter(9500),
                         pb.Reverb(room_size=0.85, damping=0.5, wet_level=1.0, dry_level=0.0, width=1.0)])(f32(send), SR).astype(np.float64)
    dry = get("body") + get("perc") + get("sub", 0.5) + pad + air + get("fx", gated=False)
    out = dry + rev * reverb
    chain = pb.Pedalboard([
        pb.HighpassFilter(28),
        pb.Compressor(threshold_db=-18.0, ratio=2.2, attack_ms=15.0, release_ms=140.0),
        pb.HighShelfFilter(cutoff_frequency_hz=6000, gain_db=1.0),
    ])
    out = chain(f32(out), SR).astype(np.float64)
    t = np.arange(out.shape[1]) / SR
    out = out * 10 ** (np.interp(t, [p[0] for p in SECTION_DB], [p[1] for p in SECTION_DB]) / 20)
    out = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=100.0)])(f32(out), SR).astype(np.float64)
    out = out[:, :int(DUR * SR)]
    return out / (np.max(np.abs(out)) or 1.0) * 0.89


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "music6.wav"
    y = mixdown(build_stems())
    write_wav(dest, y)
    print(f"fertig: {dest}  {y.shape[1] / SR:.1f} s  RMS {20 * np.log10(np.sqrt(np.mean(y ** 2))):.1f} dBFS")
