"""Bereitet die Sprecher-Clips (voice_judith/1..6.mp3) für das Video vor.

- Alle Clips auf gleiche Lautheit (RMS) bringen
- Clips mit mehreren Sätzen an den Sprechpausen teilen, damit jeder Satz zu seinem Bild passt
- plan.json schreiben: Liste [Datei, Startsekunde]; build_corporate.py grid ... voice DIR liest sie

    .venv/bin/python split_voice.py voice_judith
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 44100
TARGET_RMS = 0.085

# Clip: (Anzahl Teile, Startzeiten im Video). Ein Teil: einfach platzieren.
PLAN = {
    1: [0.3],
    2: [4.3, 6.7],              # "Jede Plattform zählt getrennt." / "Ab dreißig Verkäufen ... Steuerbehörden."
    3: [12.8],
    4: [22.5, 28.45, 33.45],    # Import / Ampel / Report, je zur eigenen Bildschirmaufnahme
    5: [38.3],
    6: [44.25, 45.15, 46.75],     # "SellCheck." / "Check, was wirklich bleibt." / "Kostenlos, ohne Anmeldung."
}


def load(path):
    out = os.path.join(tempfile.gettempdir(), os.path.basename(path) + ".wav")
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", path, out], check=True)
    with wave.open(out) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
    return x


def split_at_gaps(x, parts, min_gap=0.14):
    """Teilt x in `parts` Stücke an den längsten Sprechpausen."""
    if parts == 1:
        return [x]
    hop = int(0.01 * SR)
    env = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    thr = env.max() * 0.04
    quiet = env < thr
    gaps, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_gap and i > 15 and j < len(quiet) - 15:
                gaps.append((j - i, i, j))
            i = j
        else:
            i += 1
    gaps = sorted(sorted(gaps, reverse=True)[:parts - 1], key=lambda g: g[1])
    if len(gaps) < parts - 1:
        raise SystemExit(f"nur {len(gaps)} Pausen gefunden, {parts - 1} nötig")
    cuts = [0] + [(g[1] + g[2]) // 2 * hop for g in gaps] + [len(x)]
    return [x[a:b] for a, b in zip(cuts[:-1], cuts[1:])]


def trim(x, pad=0.03):
    idx = np.where(np.abs(x) > 0.01)[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] - int(pad * SR)), min(len(x), idx[-1] + int(pad * SR))
    return x[a:b]


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def main(folder):
    plan = []
    for k, starts in PLAN.items():
        x = load(os.path.join(folder, f"{k}.mp3"))
        act = x[np.abs(x) > np.abs(x).max() * 0.05]
        x = x * (TARGET_RMS / (np.sqrt(np.mean(act ** 2)) or 1.0))
        x = x / max(1.0, np.abs(x).max() / 0.95)
        pieces = [trim(p) for p in split_at_gaps(x, len(starts))]
        for n, (p, st) in enumerate(zip(pieces, starts)):
            name = f"{k}.wav" if len(starts) == 1 else f"{k}{'abc'[n]}.wav"
            fade = int(0.012 * SR)
            p = p.copy()
            p[:fade] *= np.linspace(0, 1, fade)
            p[-fade:] *= np.linspace(1, 0, fade)
            write(os.path.join(folder, "plan_" + name), p)
            plan.append(["plan_" + name, st])
            print(f"  Clip {k}{'abc'[n] if len(starts) > 1 else ''}: {len(p) / SR:4.2f} s  Start {st:5.2f} s  Ende {st + len(p) / SR:5.2f} s")
    json.dump(sorted(plan, key=lambda e: e[1]), open(os.path.join(folder, "plan.json"), "w"), indent=1)
    print("plan.json geschrieben")


if __name__ == "__main__":
    main(sys.argv[1])
