#!/usr/bin/env python3
"""Erzeugt die sieben Sprach-Clips (voice/1.wav ... 7.wav) lokal mit Piper und der deutschen Stimme "Thorsten".

Einmalige Einrichtung (außerhalb des Repos, in einem eigenen venv):
    python3 -m venv ~/piperenv && ~/piperenv/bin/pip install piper-tts==1.3.0
    ~/piperenv/bin/python -m piper.download_voices --download-dir ~/piper_voices de_DE-thorsten-medium
Bekanntes Problem: Das macOS-Wheel von piper-tts hat den Pfad der espeak-Daten fest einkompiliert
(/Users/runner/...). Abhilfe: einen kurzen Symlink auf piper/espeak-ng-data anlegen und die Zeichenkette in
piper/espeakbridge.so durch diesen Pfad ersetzen (gleiche oder kürzere Länge, mit NUL auffüllen), danach
`codesign --force --sign - .../espeakbridge.so`.

Aufruf:
    ~/piperenv/bin/python marketing/tiktok-ad-01/make_voice.py ~/piper_voices
Danach: python3 marketing/tiktok-ad-01/build_ad.py A voice
"""
import os
import sys
import wave

from piper import PiperVoice

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/piper_voices")
OUT = os.path.join(HERE, "voice")

LINES = [
    "Vinted meldet dich ab dreißig Verkäufen.",
    "Aber du verkaufst nicht nur dort. Und jede Plattform zählt einzeln.",
    "Lade deine Verkäufe hoch.",
    "Sieh die Ampel pro Plattform.",
    "Und druck den Report aus.",
    "Alle Plattformen. Ein Überblick.",
    "SellCheck. Gratis testen. Link unten antippen.",
]

voice = PiperVoice.load(os.path.join(VOICES, "de_DE-thorsten-medium.onnx"))
os.makedirs(OUT, exist_ok=True)
for i, text in enumerate(LINES, 1):
    with wave.open(os.path.join(OUT, f"{i}.wav"), "wb") as w:
        voice.synthesize_wav(text, w)
    with wave.open(os.path.join(OUT, f"{i}.wav")) as r:
        print(i, round(r.getnframes() / r.getframerate(), 2), "s")
