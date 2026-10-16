"""Musik für das SellCheck-Corporate-Video: reine Python-Synthese, aber mit echter Klangbearbeitung.

Bausteine (statt Sinus-Spielzeug):
- Kick aus Sub, Körper und Klick, leicht angesättigt
- Clap und Hi-Hat aus gefiltertem Rauschen, Clap mit Hall
- Bass: zwei verstimmte Sägezähne mit Filterhüllkurve plus Sub
- Pad: verstimmte Sägezähne, Tiefpass mit Verlauf, breit (Haas), per Sidechain vom Kick gedrückt
- E-Piano (FM) für die emotionalen Stellen, Pluck-Arpeggio mit Echo
- Hall (Freeverb-Art) auf Pad, Keys, Clap und Effekten
- Aufbau: Riser und Snare-Wirbel, Einschläge nur an den Szenengrenzen, kein Piepen
- Master: Sättigung und weiche Begrenzung

Tonart a-Moll, Akkorde Am – G – F – E (spanische Kadenz), Schluss in F – C (Auflösung nach oben).
"""
import math
import random

SR = 44100
TWO_PI = 2 * math.pi

# Pegelverhältnisse der Bausteine (Klangbild: tief nur als Fundament, Mitten und Präsenz tragen)
MIXG = {"kick": 0.55, "hats": 1.9, "clap": 1.5, "bass": 0.7, "fx": 0.55, "pad": 2.0, "keys": 2.2, "rev": 1.1}


class Bus:
    def __init__(self, n):
        self.n = n
        self.d = [0.0] * n

    def add(self, t0, s, g=1.0):
        i0 = int(round(t0 * SR))
        d = self.d
        lo = max(0, -i0)
        hi = min(len(s), self.n - i0)
        for k in range(lo, hi):
            d[i0 + k] += s[k] * g


def _noise(rnd, n):
    return [rnd.uniform(-1.0, 1.0) for _ in range(n)]


def _onepole_lp(x, fc):
    a = 1 - math.exp(-TWO_PI * fc / SR)
    y, out = 0.0, []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def _onepole_hp(x, fc):
    lp = _onepole_lp(x, fc)
    return [v - l for v, l in zip(x, lp)]


def _bandpass(x, lo, hi):
    return [a - b for a, b in zip(_onepole_lp(x, hi), _onepole_lp(x, lo))]


def make_kick(rnd):
    n = int(0.34 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        f = 47 + 125 * math.exp(-t / 0.021)
        ph += TWO_PI * f / SR
        body = math.sin(ph) * math.exp(-t / 0.12)
        click = rnd.uniform(-1, 1) * math.exp(-t / 0.0035) * 0.28 if t < 0.015 else 0.0
        out.append(math.tanh(1.8 * (body + click)) / 0.95)
    return out


def make_clap(rnd):
    n = int(0.38 * SR)
    base = _bandpass(_noise(rnd, n), 900, 4200)
    out = [0.0] * n
    for off, g in ((0.0, 0.8), (0.012, 0.7), (0.026, 0.6), (0.040, 1.0)):
        o = int(off * SR)
        for i in range(n - o):
            out[o + i] += base[i] * g * math.exp(-i / SR / (0.02 if off < 0.04 else 0.11))
    pk = max(abs(v) for v in out) or 1.0
    return [v / pk for v in out]


def make_hat(rnd, dur, decay):
    n = int(dur * SR)
    x = _onepole_hp(_noise(rnd, n), 7000)
    return [v * math.exp(-i / SR / decay) for i, v in enumerate(x)]


def make_boom(rnd):
    n = int(1.7 * SR)
    out, ph = [], 0.0
    rumble = _onepole_lp(_noise(rnd, n), 140)
    for i in range(n):
        t = i / SR
        f = 30 + 40 * math.exp(-t / 0.12)
        ph += TWO_PI * f / SR
        out.append(math.sin(ph) * math.exp(-t / 0.55) * 0.9 + rumble[i] * 2.4 * math.exp(-t / 0.4))
    pk = max(abs(v) for v in out) or 1.0
    return [v / pk for v in out]


def make_thud(rnd):
    n = int(0.42 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        f = 46 + 50 * math.exp(-t / 0.035)
        ph += TWO_PI * f / SR
        out.append(math.sin(ph) * math.exp(-t / 0.15))
    return out


def make_riser(rnd, dur):
    m = int(dur * SR)
    low = band = 0.0
    q = 0.38
    out = []
    for i in range(m):
        x = i / m
        f = 350 + 6200 * x * x
        a = 2 * math.sin(math.pi * f / SR)
        v = rnd.uniform(-1, 1)
        low += a * band
        high = v - low - q * band
        band += a * high
        out.append(band * (x ** 2.0))
    pk = max(abs(v) for v in out) or 1.0
    return [v / pk for v in out]


def bass_note(f, dur, rnd, cut_hi=1500.0, cut_lo=180.0):
    n = int(dur * SR)
    out = []
    p1 = p2 = ps = 0.0
    y = 0.0
    for i in range(n):
        t = i / SR
        p1 += f * 1.003 / SR
        p2 += f * 0.997 / SR
        ps += f / SR
        s = (2 * (p1 % 1.0) - 1) * 0.5 + (2 * (p2 % 1.0) - 1) * 0.5
        fc = cut_lo + (cut_hi - cut_lo) * math.exp(-t / 0.07)
        a = 1 - math.exp(-TWO_PI * fc / SR)
        y += a * (s - y)
        env = min(1.0, i / (0.004 * SR)) * (1.0 if t < dur - 0.04 else max(0.0, (dur - t) / 0.04))
        sub = math.sin(TWO_PI * ps)
        out.append((y * 1.1 + sub * 0.35) * env)
    return out


def pluck_note(f, dur=0.34):
    n = int(dur * SR)
    out, ph, y = [], 0.0, 0.0
    for i in range(n):
        t = i / SR
        ph += f / SR
        s = 2 * (ph % 1.0) - 1
        fc = 650 + 5200 * math.exp(-t / 0.05)
        a = 1 - math.exp(-TWO_PI * fc / SR)
        y += a * (s - y)
        out.append(y * math.exp(-t / 0.13) * min(1.0, i / (0.002 * SR)))
    return out


def epiano_note(f, dur=1.5):
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        idx = 0.15 + 2.4 * math.exp(-t / 0.18)
        mod = math.sin(TWO_PI * f * t) * idx
        v = math.sin(TWO_PI * f * t + mod) * math.exp(-t / 0.9)
        v += 0.18 * math.sin(TWO_PI * f * 7 * t + mod * 0.5) * math.exp(-t / 0.09)
        out.append(v * min(1.0, i / (0.003 * SR)) * 0.8)
    return out


def pad_note(f, dur, detune=0.004, attack=0.3, release=0.45):
    n = int((dur + release) * SR)
    out = []
    p1 = p2 = p3 = 0.0
    for i in range(n):
        t = i / SR
        p1 += f * (1 - detune) / SR
        p2 += f / SR
        p3 += f * (1 + detune) / SR
        s = ((p1 % 1.0) + (p2 % 1.0) + (p3 % 1.0)) * 2 / 3 - 1
        env = min(1.0, t / attack) * (1.0 if t < dur else max(0.0, 1 - (t - dur) / release))
        out.append(s * env)
    return out


class Reverb:
    """Schroeder/Freeverb-ähnlich, läuft mit halber Abtastrate (der Nachhall ist ohnehin dunkel)."""

    def __init__(self, room=0.84, damp=0.35):
        self.comb_l = [558, 594, 638, 678]
        self.comb_r = [c + 11 for c in self.comb_l]
        self.ap = [112, 170, 220]
        self.room = room
        self.damp = damp

    def _chan(self, x, combs):
        n = len(x)
        outs = [0.0] * n
        for d in combs:
            buf = [0.0] * d
            idx = 0
            store = 0.0
            fb, dm = self.room, self.damp
            for i in range(n):
                v = buf[idx]
                store = v * (1 - dm) + store * dm
                buf[idx] = x[i] + store * fb
                outs[i] += v
                idx += 1
                if idx >= d:
                    idx = 0
        y = [v * 0.25 for v in outs]
        for d in self.ap:
            buf = [0.0] * d
            idx = 0
            res = [0.0] * n
            for i in range(n):
                b = buf[idx]
                v = y[i]
                res[i] = -v + b
                buf[idx] = v + b * 0.5
                idx += 1
                if idx >= d:
                    idx = 0
            y = res
        return y

    def process(self, mono):
        half = [(mono[i] + mono[i + 1]) * 0.5 for i in range(0, len(mono) - 1, 2)]
        l = self._chan(half, self.comb_l)
        r = self._chan(half, self.comb_r)

        def up(y):
            out = [0.0] * (len(y) * 2)
            for i, v in enumerate(y):
                out[2 * i] = v
                out[2 * i + 1] = (v + (y[i + 1] if i + 1 < len(y) else v)) * 0.5
            return out
        return up(l), up(r)


def build_music(dur, scenes, seed=5):
    """Liefert (links, rechts), beide Listen mit Werten im Bereich ca. -1..1, Länge dur * SR."""
    n = int(dur * SR)
    rnd = random.Random(seed)
    beat = 0.5  # 120 bpm
    bar = 2.0
    sec = {name: (st, st + ln) for name, st, ln in scenes}

    kick_s, clap_s = make_kick(rnd), make_clap(rnd)
    hat_c, hat_o = make_hat(rnd, 0.07, 0.016), make_hat(rnd, 0.22, 0.07)
    boom_s, thud_s = make_boom(rnd), make_thud(rnd)

    drums = Bus(n)     # Kick (trocken)
    hats = Bus(n)
    claps = Bus(n)     # Clap (trocken, geht auch in den Hall)
    bass = Bus(n)
    pad = Bus(n)
    keys = Bus(n)
    fx = Bus(n)
    kicks = []

    # Akkorde je Takt: (Pad-Töne, Bass-Grundton, Arpeggio-Töne in 330 bis 800 Hz)
    chords = [
        ((220.0, 523.25, 659.25), 55.0, (440.0, 523.25, 659.25, 880.0)),          # Am(add9)
        ((392.0, 493.88, 587.33), 49.0, (392.0, 493.88, 587.33, 783.99)),         # G
        ((349.23, 440.0, 523.25), 43.65, (349.23, 440.0, 523.25, 698.46)),        # Fmaj7
        ((329.63, 415.30, 493.88), 41.2, (329.63, 415.30, 493.88, 659.25)),       # E (Terz gis)
    ]
    final = {22: chords[0], 23: chords[2], 24: ((261.63, 329.63, 392.0), 65.41, (523.25, 659.25, 783.99, 587.33))}

    def chord_at(bar_idx):
        if bar_idx in final:
            return final[bar_idx]
        return chords[bar_idx % 4]

    # Dichte je Abschnitt
    def lvl(t):
        if t < sec["problem"][0]:
            return "hook"
        if t < sec["loesung"][0]:
            return "tension"
        if t < sec["produkt"][0]:
            return "drop"
        if t < sec["vertrauen"][0]:
            return "groove"
        if t < sec["abbinder"][0]:
            return "break"
        return "finale"

    nbars = int(math.ceil(dur / bar))
    pad_events = []  # (t0, dauer, Frequenzen, Abschnitt)
    for b in range(nbars):
        t_bar = b * bar
        mode = lvl(t_bar)
        pad_notes, root, arp = chord_at(b)
        # Pad
        if mode in ("hook", "tension", "drop", "break", "finale") or (mode == "groove" and (b - 11) >= 4):
            pad_events.append((t_bar, bar, pad_notes, mode))
        for q in range(4):
            tb = t_bar + q * beat
            if tb >= dur:
                break
            # Kick
            do_kick = mode in ("hook", "tension", "drop", "groove", "finale")
            if mode == "break" and q in (0, 2) and t_bar >= sec["vertrauen"][1] - 2.0:
                do_kick = True
            if mode == "finale" and b == 24:
                do_kick = q == 0
            if do_kick:
                drums.add(tb, kick_s, 0.92)
                kicks.append(tb)
            # Hats
            if mode in ("tension", "drop", "groove", "finale") and not (mode == "finale" and b == 24):
                hats.add(tb + beat / 2, hat_o if (mode != "tension" and q == 3) else hat_c, 0.22 if mode == "tension" else 0.3)
                if mode in ("drop", "groove", "finale"):
                    hats.add(tb + beat / 4, hat_c, 0.11)
                    hats.add(tb + beat * 3 / 4, hat_c, 0.13)
            # Clap auf 2 und 4
            if mode in ("drop", "groove", "finale") and q in (1, 3) and not (mode == "finale" and b == 24):
                claps.add(tb, clap_s, 0.7)
            # Bass
            if mode in ("tension", "drop", "groove", "finale") and not (mode == "finale" and b == 24):
                if mode == "tension":
                    if q in (0, 2):
                        bass.add(tb + beat / 2, bass_note(root, 0.34, rnd, 900, 160), 0.5)
                else:
                    oct_ = 2.0 if q == 3 else 1.0
                    bass.add(tb + beat / 2, bass_note(root * oct_, 0.24, rnd, 1700, 200), 0.55)
                    if q in (0, 2):
                        bass.add(tb + beat * 0.75, bass_note(root, 0.16, rnd, 1400, 190), 0.4)
            elif mode == "hook" and q == 0:
                bass.add(tb, bass_note(root, 1.6, rnd, 500, 120), 0.5)
            # Arpeggio (Pluck mit Echo)
            if mode in ("drop", "groove", "finale") and not (mode == "finale" and b == 24):
                for h in range(2):
                    k = q * 2 + h
                    f = arp[(k + (b % 2)) % 4] * (2 if (mode == "groove" and (b - 11) >= 4 and h == 1) else 1)
                    tt = tb + h * beat / 2
                    note = pluck_note(f)
                    keys.add(tt, note, 0.1)
                    keys.add(tt + beat * 0.75, note, 0.045)
                    keys.add(tt + beat * 1.5, note, 0.02)
            # E-Piano: Spannung (sparsam), Breakdown (Achtel), Finale (Akkord)
            if mode == "tension" and q in (0, 2):
                keys.add(tb, epiano_note(arp[q % 4]), 0.16)
            if mode == "break":
                for h in range(2):
                    keys.add(tb + h * beat / 2, epiano_note(arp[(q * 2 + h) % 4], 1.1), 0.2)
            if mode == "finale" and q == 0 and b in (22, 23):
                for f in arp[:3]:
                    keys.add(tb, epiano_note(f, 1.8), 0.16)
            if mode == "finale" and b == 24 and q == 0:
                for f in (261.63, 329.63, 392.0, 587.33, 523.25):
                    keys.add(tb, epiano_note(f, 2.4), 0.16)

    # Pad rendern (Dreiklang, je Akkord), danach gefiltert mit Verlauf
    pad_dry = Bus(n)
    for t0, d, notes, mode in pad_events:
        for f in notes:
            pad_dry.add(t0, pad_note(f, d), 0.12 if mode != "tension" else 0.09)
    cutoff_for = {"hook": 900.0, "tension": 1300.0, "drop": 3400.0, "groove": 3000.0, "break": 1600.0, "finale": 3600.0}
    y1 = y2 = 0.0
    padx = pad_dry.d
    blk = 256
    for i0 in range(0, n, blk):
        t = i0 / SR
        fc = cutoff_for[lvl(t)]
        # Spannung öffnet sich vor dem Drop (Filter fährt auf)
        if sec["problem"][0] <= t < sec["problem"][1]:
            x = (t - sec["problem"][0]) / (sec["problem"][1] - sec["problem"][0])
            fc = 900 + 3200 * x * x
        a = 1 - math.exp(-TWO_PI * fc / SR)
        for i in range(i0, min(n, i0 + blk)):
            y1 += a * (padx[i] - y1)
            y2 += a * (y1 - y2)
            padx[i] = y2
    for i in range(n):
        pad.d[i] = padx[i]

    # Effekte: Aufbau und Einschläge nur an den Grenzen
    for name, st, ln in scenes[1:]:
        # Riser vor dem Drop und vor dem Finale, kurze Wischer sonst
        if name in ("loesung",):
            fx.add(st - 4.0, make_riser(rnd, 4.0), 0.55)
            for k in range(8):  # Snare-Wirbel in den letzten zwei Schlägen... Achtel bis Sechzehntel
                t_s = st - 2.0 + k * 0.25
                claps.add(t_s, clap_s, 0.18 + 0.07 * k)
            for k in range(4):
                claps.add(st - 0.5 + k * 0.125, clap_s, 0.5 + 0.1 * k)
        elif name in ("vertrauen",):
            fx.add(st - 2.0, make_riser(rnd, 2.0), 0.4)
        elif name == "abbinder":
            fx.add(st - 2.0, make_riser(rnd, 2.0), 0.5)
        else:
            fx.add(st - 0.6, make_riser(rnd, 0.6), 0.25)
        fx.add(st, boom_s, 0.9 if name in ("loesung", "abbinder") else 0.55)
    # Hook: tiefe Schläge zu den drei Textschlägen (ohne Rauschen, kein Piepen)
    for tt in (0.0, 1.0, 2.0):
        fx.add(tt, thud_s, 0.7)

    # Sidechain: Kick drückt Pad, Keys und Bass
    sc = [1.0] * n
    dl = int(0.26 * SR)
    for tk in kicks:
        i0 = int(tk * SR)
        for k in range(min(dl, n - i0)):
            g = 0.28 + 0.72 * ((k / dl) ** 1.4)
            if g < sc[i0 + k]:
                sc[i0 + k] = g

    # Hall-Sendung
    g = MIXG
    send = [0.0] * n
    for i in range(n):
        send[i] = (pad.d[i] * g["pad"] * 0.35 * sc[i] + keys.d[i] * g["keys"] * 0.55 + claps.d[i] * g["clap"] * 0.45
                   + fx.d[i] * g["fx"] * 0.5 + hats.d[i] * g["hats"] * 0.08)
    rev_l, rev_r = Reverb(0.86, 0.3).process(send)

    # Breite: Pad und Keys leicht versetzt (Haas)
    hd = int(0.012 * SR)
    L = [0.0] * n
    R = [0.0] * n
    for i in range(n):
        p = pad.d[i] * g["pad"] * sc[i]
        kz = keys.d[i] * g["keys"] * (0.55 + 0.45 * sc[i])
        mono = (drums.d[i] * g["kick"] + hats.d[i] * g["hats"] + claps.d[i] * g["clap"]
                + bass.d[i] * g["bass"] * (0.4 + 0.6 * sc[i]) + fx.d[i] * g["fx"])
        j = i - hd
        pd = pad.d[j] * g["pad"] * sc[j] if j >= 0 else 0.0
        kd = keys.d[j] * g["keys"] * (0.55 + 0.45 * sc[j]) if j >= 0 else 0.0
        L[i] = mono + p + kz + rev_l[i] * g["rev"]
        R[i] = mono + pd * 0.9 + kd * 0.9 + rev_r[i] * g["rev"]
    return L, R
