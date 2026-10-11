# Sprachaufnahmen für die Ad

1. Die sieben Zeilen aus `texte.txt` einsprechen oder mit einer Stimme-Software erzeugen (z. B. in TikTok, CapCut, ElevenLabs).
2. Jede Zeile als eigene Datei hier ablegen: `1.mp3`, `2.mp3`, … `7.mp3` (auch `.m4a` oder `.wav`).
3. `python3 marketing/tiktok-ad-01/build_ad.py A voice` ausführen. Das Video mit Stimme liegt danach in `out/`.

Das Skript legt jeden Clip zur passenden Szene, senkt die Musik darunter ab und meldet, wenn ein Clip zu lang ist.
Die Dateien in diesem Ordner werden nicht eingecheckt (`.gitignore`).
