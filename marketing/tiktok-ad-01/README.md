# TikTok-Ad 01: „Meldegrenze“ (Stand 11.10.2026, Version 3)

Version 3 nach Feedback: echtes Logo (Variante 6B), keine Überlagerung mehr in der Demo, ohne Computerstimme.

| Datei | Inhalt |
| --- | --- |
| `out/sellcheck_tiktok_ad_A_ohne_Sprecher.mp4` | Hook A „Vinted meldet dich ab 30 Verkäufen“, Musikbett und weiche Effekte |
| `out/sprechertext.md` | Sprechertext mit Einsatzzeiten zum Selbst-Einsprechen |
| `out/untertitel.srt` | Untertitel mit denselben Zeiten (z. B. für CapCut) |

Länge 25,6 s, 1080×1920, 30 fps, H.264 + AAC. Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py A`.
Die Systemstimme lässt sich mit `AD_VO=1` weiterhin erzeugen (`…_mit_Sprecher.mp4`), klingt aber künstlich und ist nicht empfohlen.
Das Logo kommt aus `marketing/logo-final/sellcheck_logo.py`.

## Version 2 („Frist“, V2)

Hook: „Hast du noch den Überblick über all deine Verkäufe?“, dann Kalenderblatt 31. Januar 2027 (Plattformen melden das Vorjahr,
ab 30 Verkäufen oder 2.000 € je Plattform), Demo mit Nutzen („Grenzen im Blick“, „Das bleibt dir“), Handlung „Jetzt gratis testen“.
Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py V2` und danach `… V2 voice` (Clips in `voice_v2/1.mp3 … 6.mp3`).
Ausgabe: `out/sellcheck_tiktok_ad_V2_mit_Stimme.mp4` (ca. 22 s). Bewusst **kein** „ab 2027 ist es Pflicht“: Dafür gibt es keinen Beleg.
Belegt ist: Plattformen melden das Vorjahr bis 31. Januar (PStTG/DAC7, seit 2023), Schwellen 30 Verkäufe oder 2.000 € je Plattform.

## Version 3 („Vinted und Co“, V3)

Einstieg „Du verkaufst viel auf Vinted und Co?“, dann Frist (Plattformen melden bis Ende Januar), Demo, Handlungsaufruf. Ohne Beruhigungs-Szene, Ziel sind Klicks.
Sprechertext mit Betonung (Großbuchstaben = betonte Wörter, `[curious]`/`[warmly]`/`[short pause]` = ElevenLabs-v4-Tags) steht in `vo_lines("V3")` in `build_ad.py`; Clips in `voice_v3/1.mp3 … 4.mp3`.
Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py V3` und danach `… V3 voice`. Ausgabe: `out/sellcheck_tiktok_ad_V3_mit_Stimme.mp4` (ca. 23 s).
Die Zeiten (`TARGET`, `FRIST_T`, `CAP2_T`, `S3_B`) sind auf die gemessenen Clip-Längen abgestimmt; bei neuen Clips das Skript neu messen.

## Mit ElevenLabs-Stimme „Pauli“ (Version A)

`out/sellcheck_tiktok_ad_A_mit_Stimme.mp4` nutzt die deutsche Stimme „Pauli“ (ElevenLabs, jung, warm, natürlich).
Die sieben Clips liegen als `voice/1.mp3 … 7.mp3` (nicht eingecheckt), gemischt mit `build_ad.py A voice`.
Länge 20,1 s (Stille an den Clips entfernt, Sätze direkt aneinander, Szenen an die Sprechzeit angepasst; längste Pause 0,4 s). Hinweis zur Lizenz: Für Werbung braucht es bei ElevenLabs in der Regel einen bezahlten Tarif (kommerzielle Nutzung prüfen).

## Mit lokaler Stimme (Piper, „Thorsten“)

`out/sellcheck_tiktok_ad_A_mit_Stimme.mp4` nutzt die freie deutsche Stimme Thorsten (CC0) über Piper.
Erzeugung und bekanntes Problem der Mac-Version stehen in `make_voice.py`. Die Stimme ist deutlich besser als die
macOS-Systemstimme, bleibt aber hörbar synthetisch. Für Werbung mit höchster Natürlichkeit eigene Aufnahme oder ElevenLabs.

## Mit natürlicher Stimme

Eine natürliche Stimme lässt sich mit den lokalen Werkzeugen nicht erzeugen. Der Mischweg ist aber fertig:
1. Die sieben Zeilen aus `voice/texte.txt` selbst einsprechen oder mit einer Stimme-Software erzeugen (TikTok, CapCut, ElevenLabs …).
2. Als `voice/1.mp3` … `voice/7.mp3` ablegen (auch `.m4a`, `.wav`).
3. `python3 marketing/tiktok-ad-01/build_ad.py A voice` → `out/sellcheck_tiktok_ad_A_mit_Stimme.mp4`.

Das Skript legt jeden Clip zur passenden Szene, senkt die Musik darunter ab und meldet Clips, die zu lang sind.
Alternativ eine bessere Systemstimme installieren (macOS: Systemeinstellungen → Bedienungshilfen → Gesprochene Inhalte → Systemstimme → Stimmen verwalten → Deutsch, Premium oder Siri-Stimme) und mit `AD_VOICE="<Name der Stimme>" AD_VO=1 python3 marketing/tiktok-ad-01/build_ad.py A audio` neu mischen.

Zeitplan: Hook 0–3,5 s · Problem 3,5–8,3 s · Demo 8,3–18,4 s · Nutzen 18,4–21,9 s · Handlung 21,9–25,6 s.
Demo in drei Schritten: Datei ablegen („Datei rein.“), Ampel („Ampel an.“), Report („Report raus.“).

## Was die Recherche ergeben hat (und wie es umgesetzt ist)

Quellen sind überwiegend Agentur- und Tool-Blogs, nicht TikTok selbst. Richtwerte, keine Garantien.

| Erkenntnis | Umsetzung im Video |
| --- | --- |
| Der Hook entscheidet in den ersten 2 bis 3 Sekunden. Problem oder Neugier, nicht Logo-Intro. | Sekunde 0: großer Satz, sofort Bewegung, kein Intro. |
| Aufbau Hook → Problem → Lösung → konkrete Handlung. | Szenen 1 bis 5 genau in dieser Reihenfolge. |
| Ein Nutzen pro Anzeige, Demo statt Behauptung. | Nutzen: Überblick über alle Plattformen. Die Demo zeigt die Ampel. |
| Marke früh zeigen (laut TikTok bei vielen Top-Ads in den ersten 3 s). | Logo und Name von Sekunde 0 oben. |
| 9–15 s laufen im Schnitt am besten, bis 60 s möglich. | 24,8 s: bewusst länger, damit man alles lesen kann. Lesbarkeit war dir wichtiger. |
| Für Ton gestalten, aber Untertitel mitdenken (viele schauen stumm). | Alle Aussagen stehen als große Schrift im Bild. Sprecher, Musik und Effekte unterstützen. |
| Safe Zone: oben ~160 px, unten ~340–440 px und rechts frei, dort sitzen Konto, Beschreibung, Button. | Text liegt zwischen y = 220 und y = 1420, rechts mindestens 140 px Rand. |
| CTA konkret und in den letzten ~5 s. | „Gratis testen. Link unten antippen.“ ab Sekunde 15,4. |
| Mehrere Hooks testen, Hook ist die wichtigste Variable. | Zwei Varianten A/B. |

Technik (TikTok In-Feed, laut Hilfe-Center, Stand Juni 2026): MP4 oder MOV, 9:16, mindestens 540×960, höchstens 500 MB, mindestens 516 kbit/s.
Unsere Dateien: 1080×1920, etwa 6 MB, H.264. Das passt.

## Skript (Bild und Sprecher-Text, Einsatzzeiten stehen in `out/sprechertext.md`)

| Zeit | Bild | Sprecher |
| --- | --- | --- |
| 0,0–3,5 | „Vinted meldet dich ab 30 Verkäufen.“ Zähler 27, 28, 29, 30, rot: „Meldegrenze erreicht“ | „Vinted meldet dich ab dreißig Verkäufen.“ |
| 3,5–8,3 | „Aber du verkaufst nicht nur dort.“ Vinted, Kleinanzeigen, eBay, Etsy mit „?“. „Jede zählt einzeln.“ | „Aber du verkaufst nicht nur dort. Und jede Plattform zählt einzeln.“ |
| 8,3–18,4 | „Datei rein. Ampel an. Report raus.“ Ampel mit vier Plattformen, danach Report mit Gewinn | „Lade deine Verkäufe hoch. Sieh die Ampel pro Plattform. Und druck den Report aus.“ |
| 18,4–21,9 | Drei Haken: Alle Plattformen, Meldegrenzen als Ampel, Steuer-Report zum Drucken | „Alle Plattformen. Ein Überblick.“ |
| 21,9–25,6 | Logo, „Gratis testen.“, „Link unten antippen“ | „SellCheck. Gratis testen. Link unten antippen.“ |

Variante B ersetzt die ersten sechs Sekunden: „POV: Du verkaufst auf 4 Plattformen und hast keine Ahnung, wo du stehst.“, dann „Ab 30 Verkäufen oder 2.000 € im Jahr meldet dich die Plattform an die Steuerbehörde. Jede Plattform zählt einzeln. Meldung heißt nicht automatisch: Steuern zahlen.“

## Beschreibung für die Anzeige (Vorschlag)

> Ab 30 Verkäufen oder 2.000 € melden Plattformen dich. Wo stehst du bei Vinted, Kleinanzeigen, eBay und Etsy? SellCheck zeigt es dir als Ampel. Gratis.

Bei Nicht-Spark-Anzeigen sind in der Beschreibung keine Links, Hashtags oder @-Erwähnungen möglich. Maximal vier Zeilen.

## Zielgruppe zum Testen (Vorschlag, nichts davon ist belegt)

Deutschland, 18–44 Jahre, Interessen Secondhand, Mode, Online-Shopping, Reseller. Erst klein testen (zwei Hooks, je ein eigener Ad Group, gleiches kleines Tagesbudget), nach einigen Tagen den Hook mit der besseren Daumen-Stopp-Rate und Klickrate weiterführen und neue Hooks nachlegen.

## Wichtig vor dem Schalten

1. **Ton:** Musik und Effekte sind selbst erzeugt (kein fremdes Material, keine Lizenzfragen), die Stimme ist eine Computerstimme von macOS. Das klingt hörbar synthetisch. Für die echte Anzeige besser selbst einsprechen (Text unten) oder in TikTok eine Stimme bzw. einen Titel aus der Commercial Music Library wählen.
2. **Aussagen:** „Vinted meldet ab 30 Verkäufen“ stützt sich auf Vinteds eigene DAC7-Seite (30 Verkäufe oder über 2.000 € je Jahr). Die Demo-Zahlen sind Beispiele und im Bild als „Beispieldaten“ gekennzeichnet. Die Anzeige verspricht keine Steuerersparnis.
3. **Zielseite:** Impressum und Datenschutz auf der Seite sind noch Entwürfe mit Platzhaltern. Ohne vollständiges Impressum und Datenschutz darf man in Deutschland nicht werben. Außerdem verlangt die Seite zuerst eine Registrierung, das kostet Klicks. Und die Adresse `gym7-fit.github.io/sellcheck-site` ist keine Marken-Adresse.
4. **Mail-Versand:** Registrierungs-Mails laufen über ein Gmail-Konto (etwa 500 Mails pro Tag, 30 pro Stunde eingestellt). Bei echtem Anzeigenverkehr reicht das nicht.
5. **Name:** SellCheck ist nicht auf Markenrechte geprüft.
6. **Konto:** Du brauchst ein TikTok-Werbekonto (Ads Manager) und musst die Anzeige selbst hochladen. Das habe ich nicht getan und nicht tun können.

## Version 7 („Reseller“, V7)

Hook „Du bist Reseller, oder willst wissen, was du wirklich verdienst?“, dann Gewinn statt Umsatz (Beispielartikel: Verkauf 38 €, Einkauf 12 €, Gewinn 26 €), Meldegrenze (gesprochen ohne Zahlen, „… an der gesetzlichen Grenze, ab der Plattformen dich melden“; „ab 30 Verkäufen oder 2.000 € je Plattform“ steht nur im Bild), CTA. Stimme: ElevenLabs „Mats“ (`HvPMqVH31pBg9ThkOUPw`), Clips in `voice_v7/1.mp3 … 4.mp3`.
Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py V7` und danach `… V7 voice`. Ausgabe: `out/sellcheck_tiktok_ad_V7_mit_Stimme.mp4` (ca. 21,4 s).
Zeiten: `TARGET`, `P7_T`, `CAP2_T`, `S3_B` sind auf die gemessenen Clip-Längen (3,9 / 5,2 / 7,0 / 3,7 s) abgestimmt.

## Version 6 („Drei Fragen“, V6)

Dunkles Design. Hook „Drei Fragen an alle, die auf Vinted, eBay oder Kleinanzeigen verkaufen“, drei Frage-Kacheln, Antwort-Kacheln (47 Verkäufe, Vinted/eBay, Gewinn 842,50 €), CTA. Stimme: ElevenLabs „Mats“, Clips in `voice_v6/1.mp3 … 4.mp3` (Clip 4 = Clip 4 von V7).
Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py V6` und danach `… V6 voice`. Ausgabe: `out/sellcheck_tiktok_ad_V6_mit_Stimme.mp4` (ca. 23 s).
Ein helles Alternativdesign (Futura, Marker-Gelb) liegt in `build_ad_v6.py` (nur Bild, ohne Ton).

## Version 8 (UGC-Stil ohne Gesicht, V8)

Stand 2026-10-12: echte Aufnahmen der Oberfläche (`assets/v8/`, mit Beispieldaten), fünf Szenen (Meldegrenze erklärt, Upload, Ergebnis, Steuer-Übersicht, Endkarte), Clips `voice_v8/1..5.mp3` (Jan). Details unten stammen aus der ersten Fassung.

Bildschirmaufnahme im TikTok-Look: Finger-Taps, Wort-für-Wort-Untertitel (Wortzeiten aus den Clips, `v8_words.json` wird beim Bauen erzeugt), lockere Erklärstimme (ElevenLabs „Jan“, Clips in `voice_v8/1.mp3 … 4.mp3`). Bewusst **keine erfundene Erfahrung** („ich habe …“), sondern Erklärung („ich zeig dir kurz was“).
Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py V8` und danach `… V8 voice`. Ausgabe: `out/sellcheck_tiktok_ad_V8_mit_Stimme.mp4` (ca. 39,7 s).
Hinweis: Die Stimme ist synthetisch, in TikTok als KI-generierte Inhalte kennzeichnen.

## Version 9 (Chat Tim und Anna, V9)

Chat im Messenger-Look (generisch, ohne fremde Marke): Tim erzählt von der Meldegrenze, Anna fragt nach, der Link öffnet die echte Oberfläche (Aufnahmen aus `assets/v8/`), Banner von Tim oben, Dateiauswahl des iPhones (Blatt von unten, Auswahl „Vinted_Verkäufe_2026.csv“), Upload und Ergebnis, zurück in den Chat, Endkarte. Tim = Stimme Mats (wie V7), Anna = Pauli (wie V2/V3). Clips in `voice_v9/1..7.mp3` (1 Tim, 2 Anna, 3 Tim „Mit SellCheck:“, 4 Tim lange Nachricht, 5 Anna, 6 Tim, 7 Endkarte aus V7). Jede Nachricht wird gesprochen, wenn sie erscheint; Annas Tippen läuft so lange wie ihr Satz (`V9_DUR`).
Erzeugen: `python3 marketing/tiktok-ad-01/build_ad.py V9`. Die Zeiten (`V9_DUR`, `v9_schedule`, `V9_T`, `BASE`) folgen den gemessenen Sprechdauern; mit Stimmen: `build_ad.py V9` (Bild), dann `build_ad.py V9 voice`. Länge rund 40 s.
