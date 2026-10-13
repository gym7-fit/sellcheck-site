# Corporate-Video

16:9, 1920×1080, 30 fps, ca. 60 s. Erklärfilm für Website und Social.

```bash
python3 marketing/corporate-video/build_corporate.py             # Bild und Musik
python3 marketing/corporate-video/build_corporate.py poster 5,20,40   # Einzelbilder
python3 marketing/corporate-video/build_corporate.py voice DIR   # mit Sprecher
```

Ausgabe: `out/sellcheck_corporate_16x9_ohne_Sprecher.mp4` bzw. `_mit_Stimme.mp4`.

- `build_corporate.py`: Renderer (PIL), Musik (reine Synthese), Aufruf des Encoders aus `tiktok-ad-01/encode.swift`
- `assets/`: Aufnahmen der echten Oberfläche (1440×900 @2x), neu aufnehmen mit der aktuellen Seite
- `SPRECHERTEXT.md`: Text mit Zeitfenstern

Szenen: Hook (0 s), Problem (6,5 s), Lösung (17,5 s), Produkt (28,5 s), Vertrauen (46,5 s), Abbinder (54,5 s).
