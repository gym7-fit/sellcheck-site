# Corporate-Video

16:9, 1920×1080, 30 fps, 49 s. Erklärfilm für Website und Social, geschnitten auf 120 bpm.

```bash
python3 marketing/corporate-video/build_corporate.py             # Bild und Musik
python3 marketing/corporate-video/build_corporate.py poster 5,20,40   # Einzelbilder
python3 marketing/corporate-video/build_corporate.py voice DIR   # mit Sprecher
```

Ausgabe: `out/sellcheck_corporate_16x9_ohne_Sprecher.mp4` bzw. `_mit_Stimme.mp4`.

- `build_corporate.py`: Renderer (PIL), Musik (reine Synthese), Aufruf des Encoders aus `tiktok-ad-01/encode.swift`
- `assets/`: Aufnahmen der echten Oberfläche (1440×900 @2x), neu aufnehmen mit der aktuellen Seite
- `SPRECHERTEXT.md`: Text mit Zeitfenstern

Szenen: Hook (0 s), Problem (4 s), Lösung (12 s), Produkt (22 s), Vertrauen (38 s), Abbinder (44 s). Übergänge als Lime-Wisch auf dem Takt.

## Mit lizenziertem Track (empfohlen für die Veröffentlichung)

Die synthetisierte Musik (`corporate_music.py`) ist ein Platzhalter. Für ein professionelles Ergebnis einen lizenzierten Track von echten Musikern einsetzen:

```bash
python3 marketing/corporate-video/build_corporate.py analyze track.mp3          # Tempo und Taktanfang bestimmen
python3 marketing/corporate-video/build_corporate.py music track.mp3            # Track einsetzen (Taktanfang automatisch)
python3 marketing/corporate-video/build_corporate.py music track.mp3 1.35       # Taktanfang manuell (Sekunden)
python3 marketing/corporate-video/build_corporate.py music track.mp3 voice DIR  # Track plus Sprecher
```

Auswahl: um 120 bpm (115 bis 127, wird bis ±6 % auf 120 gezogen), klarer Puls, Länge mindestens 50 s, Lizenz für kommerzielle Nutzung auf Website und Social Media (Nachweis aufbewahren). Der Schnitt ist auf einen 120-bpm-Takt gelegt: Szenenstarts bei 0, 4, 12, 22, 38 und 44 s, der Drop kommt bei 12 s.
