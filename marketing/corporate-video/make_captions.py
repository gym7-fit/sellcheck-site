"""Erzeugt die Untertitel (WebVTT) für die Web-Fassung des Corporate-Videos.

Zeiten stammen aus voice_judith/plan.json (Startzeit je Clip) und den Satzpausen in den vorbereiteten Clips.
Text: dieselben Sätze wie in SPRECHERTEXT.md, Zahlen als Ziffern.

    .venv/bin/python make_captions.py voice_judith ../../site/media/sellcheck-erklaerfilm.de.vtt
"""
import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_voice import split_at_gaps, SR  # noqa: E402

# Clip-Datei -> Untertitel je Satz (mehrere Sätze: an den Pausen im Clip geteilt)
TEXT = {
    "plan_1.wav": ["Vier Plattformen.", "Vier Zähler.", "Kein Überblick."],
    "plan_2a.wav": ["Jede Plattform zählt getrennt."],
    "plan_2b.wav": ["Ab 30 Verkäufen oder 2.000 Euro im Jahr\nmeldet sie an die Steuerbehörden."],
    "plan_3.wav": ["SellCheck bringt alles an einem\nOrt zusammen:", "Gewinn pro Artikel, Meldegrenze\nje Plattform und Bestand."],
    "plan_4a.wav": ["Der CSV-Import dauert Sekunden."],
    "plan_4b.wav": ["Die Meldegrenze erscheint als Ampel,\nfür jede Plattform."],
    "plan_4c.wav": ["Und der Report liefert die Ausfüllhilfe\nfür die Steuererklärung."],
    "plan_5.wav": ["Kein Zugriff auf Konten.", "Daten bleiben im Browser.", "Orientierung statt Beratung."],
    "plan_6a.wav": ["SellCheck."],
    "plan_6b.wav": ["Check, was wirklich bleibt."],
    "plan_6c.wav": ["Kostenlos, ohne Anmeldung."],
}


PROPORTIONAL = {"plan_3.wav"}  # keine hörbare Pause im Satz: Aufteilung nach Zeichenzahl


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def main(folder, out):
    plan = json.load(open(os.path.join(folder, "plan.json")))
    cues = []
    for name, start in plan:
        with wave.open(os.path.join(folder, name)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
        lines = TEXT[name]
        if len(lines) == 1:
            cues.append((start, start + len(x) / SR + 0.1, lines[0]))
            continue
        if name in PROPORTIONAL:
            total = sum(len(l) for l in lines)
            cuts, acc = [0], 0
            for l in lines:
                acc += len(l)
                cuts.append(int(len(x) * acc / total))
            pieces = [x[a:b] for a, b in zip(cuts[:-1], cuts[1:])]
        else:
            pieces = split_at_gaps(x, len(lines))
        pos = 0
        for line, piece in zip(lines, pieces):
            a = start + pos / SR
            pos += len(piece)
            cues.append((a, start + pos / SR, line))
    # Lücken zwischen Sätzen derselben Szene schließen: Untertitel bleibt bis kurz vor dem nächsten stehen
    cues.sort()
    fixed = []
    for i, (a, b, t) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else b + 0.3
        fixed.append((a, min(max(b + 0.15, a + 0.9), max(b, nxt - 0.05)), t))
    with open(out, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, (a, b, t) in enumerate(fixed, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n")
    print(f"{len(fixed)} Untertitel nach {out}")
    for a, b, t in fixed:
        print(f"  {a:6.2f} - {b:6.2f}  {t.replace(chr(10), ' / ')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
