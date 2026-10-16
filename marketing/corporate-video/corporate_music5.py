"""Musik für das SellCheck-Corporate-Video, Version 5: modern, elektronisch, ohne Streicher.

Drei Richtungen mit demselben Gerüst (120 bpm, D-Dur, D – A – Bm – G, alle Einsätze auf dem Raster des
Bildes) und unterschiedlichem Charakter:

  keynote  Minimal, luftig: Klavier, weiches Pad, Sub, Snaps und Claps, wenig Perkussion.
  electro  Antreibend: Sidechain-Pad, gerader Zupf-Puls, Claps, Hi-Hats, großer Drop.
  hybrid   Kinoartig-elektronisch: tiefer Sechzehntel-Puls, Pauken und Sub-Einschläge, breites Pad.

Klavier, Pauken, Becken und Tamburin sind echte Aufnahmen (VSCO-2-CE, CC0), alles andere Synthese
(corporate_music2.py) mit Hall, Delay, Chorus und Kompressor von pedalboard.

    .venv/bin/python corporate_music5.py STIL out.wav      # STIL: keynote | electro | hybrid
"""
import sys

import numpy as np
import pedalboard as pb
from scipy import signal

import corporate_music2 as M2
import corporate_music3 as M3
import corporate_music4 as M4
from corporate_music2 import CUES, DUR, SR, TAIL, BEAT, BAR, Stem, mtof, tarr, write_wav, lp, hp
from corporate_music4 import CH, ARP, MOTIF, TIMP, chord

rng = np.random.default_rng(41)

STYLES = {
    "keynote": dict(piano_arp=0.5, pluck="none", pad=0.9, hat="none", shaker=True, kick="half", clap=0.6, snap=True,
                    bass="long", impact=0.7, lead="piano", sub=1.0, timp=False, delay=0.2,
                    gains={"kick": 0.7, "bass": 0.6, "timp": 0.5, "fx": 0.45, "pad": 0.8, "pluck": 1.6, "lead": 1.6, "clap": 1.5, "hat": 2.2, "perc": 1.8, "piano": 1.0}),
    "electro": dict(piano_arp=0.35, pluck="8th", pad=1.1, hat="8th", shaker=False, kick="four", clap=1.0, snap=False,
                    bass="pulse8", impact=1.0, lead="saw", sub=0.9, timp=False, delay=0.3,
                    gains={"kick": 0.6, "bass": 0.5, "timp": 0.5, "fx": 0.45, "pad": 0.85, "pluck": 1.6, "lead": 1.6, "clap": 1.5, "hat": 2.2, "perc": 1.6, "piano": 1.0}),
    "hybrid": dict(piano_arp=0.0, pluck="16th", pad=1.2, hat="none", shaker=False, kick="four", clap=0.8, snap=False,
                   bass="pulse8", impact=1.25, lead="saw", sub=1.1, timp=True, delay=0.25,
                   gains={"kick": 0.5, "bass": 0.4, "timp": 0.5, "fx": 0.45, "pad": 0.9, "pluck": 1.6, "lead": 1.6, "clap": 1.5, "hat": 2.2, "perc": 1.6, "piano": 1.2}),
}


def make_snap():
    n = int(0.12 * SR)
    t = tarr(n)
    x = M2.bp(rng.uniform(-1, 1, n), 1800, 5200) * np.exp(-t / 0.018)
    x += np.sin(2 * np.pi * 1200 * t) * np.exp(-t / 0.006) * 0.4
    return x / np.max(np.abs(x))


def build_stems(style, dur=DUR):
    S = STYLES[style]
    n = int((dur + TAIL) * SR)
    lib = M4.load_library()
    kick_tight = M2.make_kick()
    clap_s, snap_s = M2.make_clap(), make_snap()
    hat_c, hat_o = lp(M2.make_hat(0.03), 12000), lp(M2.make_hat(0.16), 12000)
    impact_s = M2.make_impact()
    st = {k: Stem(n) for k in ("kick", "clap", "hat", "perc", "bass", "pad", "pluck", "lead", "piano", "fx", "timp")}
    kick_times, mute = [], []
    rr = [0]

    def nx():
        rr[0] += 1
        return rr[0]

    def put(stem, t, x, g=1.0, pan=0.0):
        st[stem].add_st(max(0.0, t), x[0] * g * (1 - max(0, pan)), x[1] * g * (1 + min(0, pan)))

    # ---- Schlagzeug
    def kick(t, vel=0.9):
        st["kick"].add(t, kick_tight, 0.8 * vel)
        thump = lib["kick"][nx() % len(lib["kick"])]
        cut = thump[:, : int(0.35 * SR)].copy()
        cut *= np.clip((cut.shape[1] - np.arange(cut.shape[1])) / (0.1 * SR), 0, 1)
        put("kick", t, cut, 0.25 * vel)
        kick_times.append(t)

    def clap(t, vel=0.8):
        st["clap"].add(t, clap_s, 0.7 * vel * S["clap"], pan=0.0)
        if S["snap"]:
            st["clap"].add(t, snap_s, 0.5 * vel, pan=0.2)

    def hat(t, vel=0.5, open_=False, pan=0.25):
        st["hat"].add(t, hat_o if open_ else hat_c, 0.25 * vel, pan)

    def crash(t, vel=0.8, ff=False):
        pool = lib["crash"][2:] if ff else lib["crash"]
        put("perc", t, pool[nx() % len(pool)], 0.6 * vel)

    def tamb(t, vel=0.5):
        put("perc", t, lib["tamb"][nx() % len(lib["tamb"])], 1.0 * vel, pan=0.3)

    def cresc(t_peak, kind="Median", g=1.0):
        x, ci = lib["cresc"][kind]
        seg = x[:, : ci + int(2.0 * SR)].copy()
        seg *= (np.arange(seg.shape[1]) / max(1, ci)).clip(0, 1) ** 1.6
        put("fx", t_peak - ci / SR, seg, 0.7 * g)

    def riser(t_end, dur_, g=1.0):
        l, r = M2.make_riser(dur_, 300, 9000)
        st["fx"].add_st(t_end - dur_, l, r, 0.55 * g)

    def impact(t, g=1.0):
        st["fx"].add(t, impact_s, 0.9 * g * S["impact"])

    def timp(t, midi, vel=0.8):
        put("timp", t, M3.timp_hit(lib, midi, vel, nx()), 0.9 if S["timp"] else 0.45)

    def roll(t0, t1, v0=0.2, v1=0.9):
        """Wirbel aus Claps/Snaps, Achtel dann Sechzehntel."""
        t = t0
        while t < t1 - 1e-6:
            x = (t - t0) / (t1 - t0)
            st["clap"].add(t, clap_s, 0.5 * (v0 + (v1 - v0) * x))
            t += BEAT / 2 if x < 0.4 else BEAT / 4

    # ---- Töne
    def sub(t, midi, d, g=1.0):
        f = mtof(midi)
        nn = int((d + 0.1) * SR)
        tt = tarr(nn)
        y = np.sin(2 * np.pi * f * tt) * np.minimum(1, tt / 0.01)
        y *= np.where(tt < d, 1.0, np.clip(1 - (tt - d) / 0.1, 0, 1))
        st["bass"].add(t, y, 0.5 * g * S["sub"])

    def bassline(t_bar, name, vel=1.0):
        root = CH[name][3]
        f = mtof(root)
        if S["bass"] == "long":
            st["bass"].add(t_bar, M2.bass_note(f, BAR - 0.05, 0.5), 0.55 * vel)
        else:
            for q in range(8):
                oc = 2.0 if q == 7 else 1.0
                st["bass"].add(t_bar + q * BEAT / 2, M2.bass_note(f * oc, BEAT * 0.42, 0.9), (0.5 if q % 2 == 0 else 0.38) * vel)

    def pad(t, name, d=BAR, fc0=1200, fc1=3000, g=1.0):
        notes = [m + 12 for m in CH[name][2]] if False else list(CH[name][2])
        l, r = M2.pad_chord(notes, d, fc0, fc1)
        st["pad"].add_st(t, l, r, g * S["pad"])
        l2, r2 = M2.pad_chord([m - 12 for m in CH[name][0]], d, fc0 * 0.6, fc1 * 0.6)
        st["pad"].add_st(t, l2, r2, 0.8 * g * S["pad"])

    def pluck_pattern(t_bar, name, g=1.0, cutoff=1.0):
        if S["pluck"] == "none":
            return
        steps = 8 if S["pluck"] == "8th" else 16
        sp = BAR / steps
        tones = [m for m in ARP[name]]
        for k in range(steps):
            m = tones[k % 8] + (12 if (steps == 8 and k % 4 == 3) else 0)
            x = M2.pluck(mtof(m), 0.22 if steps == 16 else 0.3, 0.55 * cutoff)
            v = g * (1.0 if k % 2 == 0 else 0.7) * (1.15 if k % 4 == 0 else 1.0)
            st["pluck"].add(t_bar + k * sp, x, 0.4 * v, pan=-0.35 if k % 2 else 0.35)

    def piano(t, midi, vel=0.6, d=0.45, g=1.0, pan=0.0, rr_=0):
        put("piano", t, lib["piano"].note(midi, d, vel, 0.25, 0.0, rr=rr_), g * (0.4 + 0.9 * vel), pan)

    def arp(t_bar, name, vel=0.5, g=1.0):
        if S["piano_arp"] <= 0:
            return
        for q, m in enumerate(ARP[name]):
            piano(t_bar + q * BEAT / 2, m, min(1.0, vel * S["piano_arp"] * 2 * (1.1 if q == 0 else 0.9 if q % 2 else 1.0)), BEAT * 0.5, g, rr_=q)

    def melody(t_bar, name, vel=0.7, g=1.0):
        for pos, m, ln in MOTIF[name]:
            t = t_bar + pos * BEAT / 2
            d = ln * BEAT / 2
            if S["lead"] == "piano":
                piano(t, m - 12, vel, d * 0.95, 1.1 * g, pan=0.1, rr_=pos)
                piano(t, m, vel * 0.55, d * 0.9, 0.7 * g, pan=-0.15, rr_=pos + 1)
            else:
                x = M2.lead_note(mtof(m - 12), d * 0.95)
                st["lead"].add(t, x, 0.5 * g, 0.0)
                st["lead"].add(t + BEAT * 0.75, x, 0.16 * g, 0.5)
                st["lead"].add(t + BEAT * 1.5, x, 0.06 * g, -0.5)
                piano(t, m - 12, vel * 0.5, d * 0.9, 0.6 * g, rr_=pos)

    def piano_chord(t, name, vel=0.7, octave=0, d=1.7, g=1.0, spread=0.0):
        ce, vi, vl, _ = CH[name]
        for k, m in enumerate(sorted(set(vi + vl))):
            piano(t + k * spread, m + 12 * octave, vel, d, g, pan=(k % 3 - 1) * 0.2, rr_=k)

    def groove(t_bar, name, level):
        """Schlagzeug-Teppich je Takt. level 0..1."""
        if S["kick"] == "four":
            for q in range(4):
                kick(t_bar + q * BEAT, (0.95 if q % 2 == 0 else 0.8) * (0.7 + 0.3 * level))
        else:
            kick(t_bar, 0.9 * (0.7 + 0.3 * level))
            kick(t_bar + 2 * BEAT, 0.8 * (0.7 + 0.3 * level))
            kick(t_bar + 3.5 * BEAT, 0.5 * level)
        for q in (1, 3):
            clap(t_bar + q * BEAT, 0.6 + 0.4 * level)
        if S["hat"] != "none":
            for q in range(8):
                hat(t_bar + q * BEAT / 2 + (0 if q % 2 == 0 else 0.0), 0.5 * (0.6 + 0.4 * level) * (1.0 if q % 2 else 0.6),
                    open_=(q == 7), pan=0.3 if q % 2 else -0.2)
        if S["shaker"]:
            for q in range(8):
                tamb(t_bar + q * BEAT / 2, (0.18 + 0.1 * level) * (1.0 if q % 2 else 0.7))

    # ---------------------------------------------------- A: Hook 0 bis 4 s
    for b in (0, 1):
        nm = chord(b)
        pad(b * BAR, nm, BAR, 500 + 250 * b, 1100 + 400 * b, 0.8)
        sub(b * BAR, CH[nm][3], BAR - 0.1, 0.8)
        if S["piano_arp"] > 0:
            arp(b * BAR, nm, 0.45 + 0.1 * b, 0.8)
        pluck_pattern(b * BAR, nm, 0.3 + 0.2 * b, 0.6)
    for k, tt in enumerate(CUES["hook_slams"]):
        kick(tt, (0.8, 0.9, 1.0)[k])
        impact(tt, (0.5, 0.7, 0.95)[k])
        timp(tt, 38 if k < 2 else 45, (0.6, 0.75, 0.95)[k])
        piano(tt, (50, 57, 62)[k], (0.6, 0.7, 0.85)[k], 1.0, 1.0)
    clap(1.0, 0.6)
    clap(2.0, 0.9)
    cresc(4.0, "Short", 0.9)
    roll(3.0, 4.0, 0.2, 0.9)

    # ---------------------------------------------------- B: Problem 4 bis 12 s
    crash(4.0, 0.6)
    impact(4.0, 0.7)
    for b in range(2, 6):
        t_bar = b * BAR
        nm = chord(b)
        lv = (b - 2) / 3
        pad(t_bar, nm, BAR, 800 + 500 * (b - 2), 1500 + 700 * (b - 2), 0.85)
        bassline(t_bar, nm, 0.8)
        groove(t_bar, nm, 0.3 + 0.4 * lv)
        arp(t_bar, nm, 0.45 + 0.1 * lv, 0.9)
        pluck_pattern(t_bar, nm, 0.5 + 0.3 * lv, 0.7 + 0.3 * lv)
    for k, tt in enumerate(CUES["problem_cards"]):
        piano(tt, (62, 66, 69, 74)[k], 0.8, 0.8, 1.2)
    t8 = CUES["problem_banner"][0]
    impact(t8, 0.9)
    clap(t8, 1.0)
    timp(t8, 47, 0.9)
    piano_chord(t8, "D", 0.8, octave=-1, d=1.5)
    piano(CUES["problem_banner"][1], 66, 0.7, 0.6, 1.0)
    cresc(12.0, "Median", 1.0)
    riser(12.0, 3.0, 0.8)
    roll(10.5, 11.75, 0.2, 0.9)
    mute.append((11.75, 12.0))

    # ---------------------------------------------------- C: Lösung 12 bis 22 s
    crash(12.0, 1.0, ff=True)
    impact(12.0, 1.2)
    timp(12.0, 38, 1.0)
    for b in range(6, 11):
        t_bar = b * BAR
        nm = chord(b)
        pad(t_bar, nm, BAR, 2200, 3400, 1.0)
        bassline(t_bar, nm, 1.0)
        groove(t_bar, nm, 1.0)
        arp(t_bar, nm, 0.55, 0.8)
        pluck_pattern(t_bar, nm, 1.0, 1.0)
        if b <= 9:
            melody(t_bar, nm, 0.8, 1.0)
        if b % 2 == 0:
            timp(t_bar, TIMP[nm], 0.7)
    for tt in CUES["loesung_lines"]:
        crash(tt, 0.5)
        impact(tt, 0.5)
        timp(tt, 38 if tt == 13.0 else 45, 0.85)
    crash(CUES["loesung_card"], 0.7)
    for k, tt in enumerate(CUES["loesung_bullets"]):
        piano(tt, (66, 69, 74)[k], 0.85, 0.7, 1.2)
        tamb(tt, 0.8)
    cresc(22.0, "Short", 0.8)
    roll(20.5, 22.0, 0.3, 0.95)

    # ---------------------------------------------------- D: Produkt 22 bis 38 s
    crash(22.0, 0.9)
    timp(22.0, 38, 0.85)
    for b in range(11, 19):
        t_bar = b * BAR
        nm = chord(b)
        pad(t_bar, nm, BAR, 1800 + (600 if b >= 15 else 0), 2800, 0.9)
        bassline(t_bar, nm, 0.9)
        groove(t_bar, nm, 0.8 if b < 15 else 0.95)
        arp(t_bar, nm, 0.5, 0.8)
        pluck_pattern(t_bar, nm, 0.8, 0.9)
        if b >= 15:
            melody(t_bar, nm, 0.75, 1.0)
    for tt in CUES["produkt_cuts"][1:]:
        crash(tt, 0.7)
        impact(tt, 0.5)
    for tt in CUES["produkt_callouts"]:
        piano(tt, 81, 0.75, 0.9, 1.0)
        tamb(tt, 0.7)
    cresc(38.0, "Median", 0.9)
    riser(38.0, 3.0, 0.7)
    roll(36.0, 37.75, 0.2, 0.95)
    mute.append((37.75, 38.0))

    # ---------------------------------------------------- E: Vertrauen 38 bis 44 s
    impact(38.0, 0.8)
    for b in range(19, 22):
        t_bar = b * BAR
        nm = chord(b)
        pad(t_bar, nm, BAR, 900, 1800, 0.85)
        sub(t_bar, CH[nm][3], BAR - 0.1, 0.9)
        piano_chord(t_bar, nm, 0.45, octave=0, d=1.8, g=0.9, spread=0.03)
        for k in range(4):
            piano(t_bar + (k * 2 + 1) * BEAT / 2, CH[nm][2][k % 3] + 12, 0.35, 0.5, 0.7, pan=-0.2 if k % 2 else 0.2, rr_=k)
        kick(t_bar, 0.55)
        if b >= 20:
            pluck_pattern(t_bar, nm, 0.4, 0.6)
    for k, tt in enumerate(CUES["vertrauen_lines"]):
        piano_chord(tt, chord(int(tt // BAR)), 0.8, octave=-1, d=1.5)
        timp(tt, (47, 43, 45)[k], 0.6)
    cresc(44.0, "Short", 0.9)
    riser(44.0, 2.0, 0.7)
    roll(43.0, 43.875, 0.2, 0.9)
    mute.append((43.875, 44.0))

    # ---------------------------------------------------- F: Abbinder 44 bis 49 s
    crash(44.0, 1.0, ff=True)
    impact(44.0, 1.2)
    timp(44.0, 38, 1.0)
    for b, t_bar in ((22, 44.0), (23, 46.0)):
        nm = chord(b)
        pad(t_bar, nm, BAR, 2400, 3500, 1.1)
        bassline(t_bar, nm, 1.0)
        groove(t_bar, nm, 1.0)
        arp(t_bar, nm, 0.55, 0.8)
        pluck_pattern(t_bar, nm, 1.0, 1.0)
        melody(t_bar, nm, 0.85, 1.0)
    for k, tt in enumerate(CUES["abbinder_lines"]):
        crash(tt, 0.6)
        timp(tt, 38 if k == 0 else 45, 0.9)
    piano(CUES["abbinder_pill"], 81, 0.8, 1.2, 1.0)
    piano(CUES["abbinder_pill"], 86, 0.7, 1.2, 0.8)
    # Schluss: D-Dur ausklingend
    pad(48.0, "D", 3.4, 3200, 2000, 1.2)
    sub(48.0, 38, 2.8, 1.0)
    kick(48.0, 1.0)
    impact(48.0, 0.9)
    crash(48.0, 1.0, ff=True)
    timp(48.0, 38, 1.0)
    piano_chord(48.0, "D", 0.85, octave=0, d=2.8, g=1.0, spread=0.05)
    piano(48.0, 74, 0.8, 2.8, 1.0)

    # ---------------------------------------------------- Sidechain und Stopps
    duck = np.ones(n)
    ln = int(0.30 * SR)
    prof = 1 - 0.6 * (1 - np.arange(ln) / ln) ** 2
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
    return {"stems": st, "duck": duck, "gate": gate, "n": n, "style": style}


GAINS = {"kick": 0.9, "clap": 1.0, "hat": 1.0, "perc": 1.0, "bass": 0.7, "pad": 1.0, "pluck": 1.0, "lead": 1.0,
         "piano": 0.8, "fx": 0.7, "timp": 0.7}
SECTION_DB = [(0, -5), (3.9, -4), (4.0, -4.5), (11.7, -2.5), (12.0, 0), (21.9, 0), (22.0, -2), (37.7, -1.5), (38.0, -5.5),
              (43.5, -4.5), (44.0, 0), (47.5, 0), (49.0, -1)]


def mixdown(parts, g=None, reverb=0.28):
    S = STYLES[parts["style"]]
    g = {**GAINS, **S.get("gains", {}), **(g or {})}
    st, duck, gate, n = parts["stems"], parts["duck"], parts["gate"], parts["n"]

    def get(name, ducked=0.0, gated=True):
        d = st[name].d * g[name]
        if ducked:
            d = d * (1 - ducked + ducked * duck)
        return d * gate if gated else d

    f32 = lambda a: a.astype(np.float32)
    pad_b = pb.Pedalboard([pb.Chorus(rate_hz=0.4, depth=0.25, mix=0.3), pb.LowpassFilter(9000)])(f32(get("pad", 1.0)), SR).astype(np.float64)
    pluck_b = pb.Pedalboard([pb.HighpassFilter(180), pb.Delay(delay_seconds=BEAT * 0.75, feedback=0.3, mix=S["delay"])])(f32(get("pluck", 0.5)), SR).astype(np.float64)
    lead_b = pb.Pedalboard([pb.Chorus(rate_hz=0.8, depth=0.2, mix=0.2)])(f32(get("lead", 0.3)), SR).astype(np.float64)

    send = pad_b * 0.35 + pluck_b * 0.4 + lead_b * 0.5 + get("piano") * 0.55 + get("clap") * 0.35 + get("perc") * 0.2 + get("timp") * 0.4
    rev = pb.Pedalboard([pb.HighpassFilter(250), pb.LowpassFilter(9000),
                         pb.Reverb(room_size=0.7, damping=0.5, wet_level=1.0, dry_level=0.0, width=1.0)])(f32(send), SR).astype(np.float64)
    dry = (get("kick") + get("clap") + get("hat") + get("perc") + get("bass", 0.55) + pad_b + pluck_b + lead_b +
           get("piano", 0.1) + get("timp") + get("fx", gated=False))
    out = dry + rev * reverb
    chain = pb.Pedalboard([
        pb.HighpassFilter(30),
        pb.Compressor(threshold_db=-16.0, ratio=2.6, attack_ms=20.0, release_ms=160.0),
        pb.Distortion(drive_db=1.5),
        pb.HighShelfFilter(cutoff_frequency_hz=6000, gain_db=1.5),
    ])
    out = chain(f32(out), SR).astype(np.float64)
    t = np.arange(out.shape[1]) / SR
    out = out * 10 ** (np.interp(t, [p[0] for p in SECTION_DB], [p[1] for p in SECTION_DB]) / 20)
    out = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=100.0)])(f32(out), SR).astype(np.float64)
    out = out[:, :int(DUR * SR)]
    return out / (np.max(np.abs(out)) or 1.0) * 0.89


if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "keynote"
    dest = sys.argv[2] if len(sys.argv) > 2 else f"music5_{style}.wav"
    y = mixdown(build_stems(style))
    write_wav(dest, y)
    print(f"fertig: {dest}  {y.shape[1] / SR:.1f} s  RMS {20 * np.log10(np.sqrt(np.mean(y ** 2))):.1f} dBFS")
