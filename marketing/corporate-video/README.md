# Corporate-Video

16:9, 1920×1080, 30 fps, 51 s (49 s Bild und Sprache, 2 s Ausklingen). Erklärfilm für Website und Social, geschnitten auf 120 bpm (Szenenstarts bei 0, 4, 12, 22, 38 und 44 s, Lime-Wisch auf dem Takt).

**Freigegebene Fassung (16. Oktober 2026):** Musik `corporate_music7.py` („Herzklopfen und Erleichterung“), Sprecherin Judith Maas (ElevenLabs, KI-Stimme), Datei `out/sellcheck_corporate_16x9_v13_mit_Judith.mp4`.

## Neu bauen

Einmalig: `python3 -m venv .venv && .venv/bin/pip install numpy scipy pedalboard mido` (im Ordner `marketing/corporate-video/`) und die Instrumenten-Aufnahmen holen: `python3 fetch_samples.py` und `python3 fetch_samples.py samples_list_extra.txt` (VSCO-2-CE, CC0, ca. 340 MB, nicht im Repo). Für die freigegebene Fassung braucht nur das Klavier aus dem ersten Paket (`Keys/Upright Nr1`).

```bash
python3 build_corporate.py frames                       # alle Bilder nach /tmp/sellcheck_corporate_frames (ca. 3 min, vorhandene werden übersprungen)
.venv/bin/python corporate_music7.py musik.wav          # Musik, auf das Raster des Bildes gerechnet
.venv/bin/python split_voice.py voice_judith            # Sprecher-Clips angleichen, Sätze teilen, plan.json schreiben
VIDEO_BITRATE=4000000 python3 build_corporate.py grid musik.wav voice voice_judith   # Ton + Video
```

Ausgabe in `out/`. `VIDEO_BITRATE=4000000` hält die Datei unter 30 MB (Versand per Chat); ohne Angabe ca. 10 Mbit/s.

## Web-Fassung und Untertitel (Startseite)

```bash
F=/tmp/sellcheck_corporate_frames
VIDEO_BITRATE=1300000 $F/encode $F 30 1530 $F/audio_mit_Stimme_Raster.wav ../../site/media/sellcheck-erklaerfilm.mp4 1280 720
sips -Z 1280 --setProperty format jpeg --setProperty formatOptions 78 $F/f_00375.jpg --out ../../site/media/sellcheck-erklaerfilm-poster.jpg
.venv/bin/python make_captions.py voice_judith ../../site/media/sellcheck-erklaerfilm.de.vtt
```

`encode` stammt aus `../tiktok-ad-01/encode.swift` (setzt die Metadaten ans Dateiende nach vorn, damit das Video im Browser sofort startet).

## Dateien

- `build_corporate.py`: Bildrenderer (PIL), Mischung, Encoder-Aufruf. Modi: `frames`, `poster`, `audio`, `grid`, `music`, `analyze`
- `corporate_music2.py`: Grundbausteine der Klangerzeugung und die Zeitpunkte aller Bildereignisse (`CUES`)
- `corporate_music7.py`: Musik der freigegebenen Fassung. `corporate_music3` bis `6` sind frühere Richtungen (Orchester, hell, elektronisch, Atem) und bleiben zum Nachsehen im Repo; `corporate_music.py` ist die erste Synthese
- `split_voice.py`: bringt die Sprecher-Clips auf gleiche Lautheit, teilt mehrsätzige Clips an den Pausen und legt sie auf die Bildszenen (`plan.json`)
- `make_captions.py`: Untertitel (WebVTT) aus `plan.json`
- `SPRECHERTEXT.md`: Text mit Zeitfenstern; `assets/`: Aufnahmen der echten Oberfläche (1440×900 @2x), neu aufnehmen, wenn sich die Seite ändert
- `music/LIZENZ.md`: Lizenznotizen (eigene Musik, CC0-Aufnahmen)

## Hinweise

- Alle Zahlen im Bild sind Beispieldaten und so gekennzeichnet; Plattformnamen nur als Text, keine Logos.
- Die Stimme ist KI-generiert: in TikTok und YouTube als KI-Inhalt kennzeichnen. Tarif von ElevenLabs für die kommerzielle Nutzung der Bibliotheksstimme prüfen.
- Ältere Variante mit lizenziertem Track (`music`, `analyze`): Der getestete Track hatte keinen festen Puls, deshalb passten die Schläge nicht. Für Tracks gilt: klarer Puls um 120 bpm, Lizenz für Web und Social.
