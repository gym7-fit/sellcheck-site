"""Musik für das SellCheck-Corporate-Video, Version 6: der Atem. Sounddesign statt Melodie.

Idee: Die Fakten fliegen ins Bild, die Person erschrickt. Der Ton ist ein Körper, der darauf reagiert.

  Hook         drei Einblendungen = drei Atemzüge (scharfes Einatmen, jedes höher und lauter), danach Herzschlag
  Problem      vier Karten = vier hastige Atemstöße, Herzschlag beschleunigt; die Meldegrenze trifft als
               Schock: großes Einatmen, alles wird abgesaugt, nur ein hohes Klingeln (Tinnitus) bleibt
               kurz stehen; dann Hecheln, Anstieg, Luft anhalten (kurze Stille vor dem Drop)
  Lösung       Ausatmen bei 12,0 s (Erleichterung), das Pad blüht auf; Rhythmus aus Atem-Percussion
               (Herzschlag-Kick, "pff"-Snare, "tss"-Hi-Hat); das Pad atmet im Takt
  Produkt      gleichmäßiger Atem-Groove, kleine "Aha"-Atemzüge bei den Markierungen
  Vertrauen    ruhiges, langsames Atmen (4 s je Zug), ein Seufzer je Aussage
  Abbinder     tiefes Einatmen, dann kräftiges Ausatmen mit vollem Klang; zum Schluss ein letzter, langer Atem

Alle Töne sind synthetisiert: gefiltertes Rauschen mit Formanten, Sinus-Herzschlag, Pad. Kaum Tonhöhen:
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
def _noise2(n):
    return rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)


def breath_in(dur=0.3, f0=700.0, f1=3400.0, rasp=0.35):
    """Einatmen: Rauschen, dessen Helligkeit nach oben fährt; schneller Anstieg, abruptes Ende (Schreck)."""
    n = int((dur + 0.06) * SR)
    t = tarr(n)
    fc = np.geomspace(f0, f1, n)
    env = np.clip(t / (0.35 * dur), 0, 1) ** 1.3
    env *= np.where(t < dur, 1.0, np.clip(1 - (t - dur) / 0.05, 0, 1))
    out = []
    for x in _noise2(n):
        y = hp(M2.lp_sweep(x, fc), 300)
        y += 0.5 * M2.bp(x, 900, 1700) * env
        flutter = 1 + rasp * lp(rng.uniform(-1, 1, n), 70) * 3
        out.append(y * env * flutter)
    pk = max(np.abs(out[0]).max(), np.abs(out[1]).max()) or 1.0
    return out[0] / pk, out[1] / pk


def breath_out(dur=1.3, f0=4200.0, f1=650.0, soft=1.0):
    """Ausatmen: Rauschen, dessen Helligkeit nach unten fällt; weicher Anstieg, langes Ausklingen."""
    n = int((dur + 0.1) * SR)
    t = tarr(n)
    fc = np.geomspace(f0, f1, n)
    env = np.clip(t / (0.06 * soft + 0.02), 0, 1) * np.exp(-t / (dur * 0.38))
    out = []
    for x in _noise2(n):
        y = M2.lp_sweep(x, fc)
        y += 0.6 * M2.bp(x, 350, 800) * env
        out.append(y * env)
    pk = max(np.abs(out[0]).max(), np.abs(out[1]).max()) or 1.0
    return out[0] / pk, out[1] / pk


def thump(f=52.0, dur=0.22):
    n = int(dur * SR)
    t = tarr(n)
    fr = f * (1 + 1.2 * np.exp(-t / 0.02))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.07)
    y += hp(rng.uniform(-1, 1, n), 1500) * np.exp(-t / 0.004) * 0.12
    return np.tanh(1.5 * y) * np.clip((n - np.arange(n)) / (0.01 * SR), 0, 1)


def pff(dur=0.14):
    """Kurzer Luftstoß als Snare: Rauschen mit Körper."""
    n = int(dur * SR)
    t = tarr(n)
    x = M2.bp(rng.uniform(-1, 1, n), 900, 6000) * np.exp(-t / 0.035)
    x += np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04) * 0.35
    return np.tanh(1.3 * x) / 1.0


def tss(dur=0.07):
    n = int(dur * SR)
    t = tarr(n)
    x = M2.bp(rng.uniform(-1, 1, n), 4000, 11000) * np.exp(-t / 0.018)
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

    def heart(t, g=1.0):
        beat_thump(t, g)
        beat_thump(t + 0.17, 0.6 * g, 46.0)

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

    def groove(t_bar, level=1.0, hats=True):
        for q in range(4):
            beat_thump(t_bar + q * BEAT, (0.95 if q % 2 == 0 else 0.7) * level)
            if q in (1, 3):
                puff(t_bar + q * BEAT, 0.9 * level)
        if hats:
            for q in range(8):
                hat(t_bar + q * BEAT / 2, 0.45 * level * (1.0 if q % 2 else 0.6), pan=0.3 if q % 2 else -0.3)

    # ---------------------------------------------------- A: Hook 0 bis 4 s
    sub(0.0, 26, 2.5, 0.6, 1.5)
    for k, tt in enumerate(CUES["hook_slams"]):
        gasp(tt, (0.5, 0.75, 1.05)[k], 700 + 350 * k, 3000 + 900 * k, 0.12 + 0.01 * k)
        beat_thump(tt, (0.6, 0.8, 1.1)[k])
    mute.append((2.0, 2.3))
    st["fx"].add(2.0, ring(1.0, 4300.0), 0.05)
    for tt in (2.5, 3.0, 3.25, 3.5, 3.625, 3.75, 3.875):
        heart(tt, 0.6 + 0.25 * (tt - 2.5))
    st["fx"].add_st(2.0, *M2.make_riser(2.0, 250, 6500), 0.35)

    # ---------------------------------------------------- B: Problem 4 bis 12 s
    sub(4.0, 38, 7.7, 0.7, 2.0)
    pad(4.0, [38, 45, 50], 8.0, 400, 1600, 0.5)      # offene Quinte, ohne Terz: Spannung
    for b in range(2, 6):
        for q in range(4):
            heart(b * BAR + q * BEAT, 0.55 + 0.1 * (b - 2))
    for k, tt in enumerate(CUES["problem_cards"]):
        gasp(tt - 0.05, 0.7 + 0.08 * k, 900 + 250 * k, 3600 + 500 * k, 0.1)
    t8 = CUES["problem_banner"][0]
    gasp(t8 - 0.28, 1.25, 500, 4200, 0.28)         # das große Einatmen vor dem Schock
    beat_thump(t8, 1.3, 40.0)
    st["fx"].add(t8, ring(1.4, 4300.0), 0.10)
    mute.append((t8 + 0.02, t8 + 0.42))
    gasp(CUES["problem_banner"][1] - 0.08, 0.6, 900, 3000, 0.1)
    # Hecheln und Anstieg
    for b in (4, 5):
        for q in range(8):
            tt = 8.9 + (b - 4) * 1.5 + q * BEAT * 0.75
    t = 8.9
    k = 0
    while t < 11.7:
        x = (t - 8.9) / 2.8
        if k % 2 == 0:
            gasp(t, 0.45 + 0.4 * x, 800 + 700 * x, 3000 + 1500 * x, 0.12)
        else:
            exhale(t, 0.35 + 0.3 * x, 0.18, 3500, 1200)
        t += 0.34 - 0.14 * x
        k += 1
    st["fx"].add_st(9.0, *M2.make_riser(3.0, 300, 9000), 0.5)
    mute.append((11.72, 12.0))

    # ---------------------------------------------------- C: Lösung 12 bis 22 s
    exhale(12.0, 1.4, 1.8, 5200, 500)
    beat_thump(12.0, 1.4, 42.0)
    sub(12.0, 38, 1.9, 1.2, 0.01)
    pad(12.0, [50, 57, 62, 66, 69], 10.0, 1200, 3300, 0.7)
    sub(14.0, 33, 1.9, 0.9)
    sub(16.0, 35, 1.9, 0.9)
    sub(18.0, 31, 1.9, 0.9)
    sub(20.0, 38, 1.9, 0.9)
    sub(12.0, 38, 1.9, 1.0)
    for b in range(6, 11):
        groove(b * BAR, 1.0)
    for tt in CUES["loesung_lines"]:
        exhale(tt, 0.55, 0.45, 3500, 800)
    exhale(CUES["loesung_card"], 0.8, 0.9, 4200, 700)
    for k, tt in enumerate(CUES["loesung_bullets"]):
        hat(tt, 1.4 + 0.1 * k, pan=-0.3 + 0.3 * k)
        gasp(tt - 0.04, 0.35, 1500 + 300 * k, 4500, 0.07)
    # Atem vor dem nächsten Teil
    gasp(20.4, 0.8, 600, 3800, 1.5)

    # ---------------------------------------------------- D: Produkt 22 bis 38 s
    exhale(22.0, 0.9, 0.9, 4200, 800)
    for b in range(11, 19):
        groove(b * BAR, 0.8 if b < 15 else 0.95, hats=True)
    pad(22.0, [50, 57, 62, 66, 69], 16.0, 1500, 3000, 0.55)
    for k, tt in enumerate((22.0, 24.0, 26.0, 28.0, 30.0, 32.0, 34.0, 36.0)):
        sub(tt, (38, 33, 35, 31, 38, 33, 35, 31)[k], 1.9, 0.8)
    for tt in CUES["produkt_cuts"][1:]:
        exhale(tt, 0.6, 0.6, 5200, 900)
    for tt in CUES["produkt_callouts"]:
        gasp(tt - 0.14, 0.6, 600, 2600, 0.14)
        st["perc"].add(tt, tss_s, 0.7, 0.2)
    gasp(34.2, 0.9, 600, 4200, 3.5)              # langes Einatmen vor der Pause
    st["fx"].add_st(34.0, *M2.make_riser(3.7, 300, 9500), 0.45)
    t = 36.0
    while t < 37.7:
        heart(t, 0.7 + 0.4 * (t - 36.0) / 1.7)
        t += 0.5 if t < 37.0 else 0.25
    mute.append((37.72, 38.0))

    # ---------------------------------------------------- E: Vertrauen 38 bis 44 s
    exhale(38.0, 0.9, 1.4, 3600, 600, )
    pad(38.0, [38, 45, 50, 54, 57], 6.0, 700, 1500, 0.7)
    sub(38.0, 31, 2.8, 0.8)
    sub(40.0, 33, 2.8, 0.8)
    sub(42.0, 35, 1.9, 0.8)
    for tt in (38.0, 40.0, 42.0):
        heart(tt, 0.5)
    for tt in CUES["vertrauen_lines"][1:]:
        exhale(tt, 0.7, 1.1, 3200, 600)
    gasp(42.0, 0.7, 500, 3200, 1.85)
    mute.append((43.875, 44.0))

    # ---------------------------------------------------- F: Abbinder 44 bis 49 s
    exhale(44.0, 1.5, 1.6, 6000, 500)
    beat_thump(44.0, 1.4, 42.0)
    sub(44.0, 38, 2.0, 1.3, 0.01)
    pad(44.0, [50, 57, 62, 66, 69, 74], 5.0, 2000, 3600, 0.85)
    for b in (22, 23):
        groove(b * BAR if False else 44.0 + (b - 22) * BAR, 1.0 if b == 22 else 0.7, hats=(b == 22))
    for k, tt in enumerate(CUES["abbinder_lines"]):
        exhale(tt, 0.7, 0.7, 4200, 700)
    st["perc"].add(CUES["abbinder_pill"], tss_s, 0.9, 0.0)
    sub(46.0, 43, 1.9, 0.9)
    sub(48.0, 38, 2.9, 1.2, 0.02)
    exhale(48.0, 1.2, 2.8, 4800, 450)
    beat_thump(48.0, 1.0, 44.0)

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
    for a, b, cyc in ((12.0, 38.0, 2.0), (38.0, 44.0, 4.0), (44.0, 48.0, 2.0)):
        m = (t >= a) & (t < b)
        ph = ((t[m] - a) % cyc) / cyc
        breath[m] = 0.55 + 0.45 * np.sin(np.pi * ph) ** 1.4      # Einatmen (Anstieg) und Ausatmen (Abfall)
    return {"stems": st, "duck": duck, "gate": gate, "breath": breath, "n": n}


GAINS = {"air": 3.0, "body": 0.6, "perc": 2.5, "pad": 1.4, "sub": 0.3, "fx": 1.3}
SECTION_DB = [(0, -3), (3.9, -3), (4.0, -4), (11.7, -2), (12.0, 0), (21.9, 0), (22.0, -1.5), (37.7, -1),
              (38.0, -4), (43.5, -4), (44.0, 0), (47.5, 0), (49.0, -1)]


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
