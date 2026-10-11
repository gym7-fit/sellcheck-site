# TikTok-Ad 01: „Meldegrenze“ (Stand 11.10.2026)

Zwei Hook-Varianten desselben Videos, 18,5 s, 1080×1920, 30 fps, H.264 + AAC.

| Datei | Hook | Idee |
| --- | --- | --- |
| `out/sellcheck_tiktok_ad_A.mp4` | „Vinted meldet dich ab 30 Verkäufen.“ + tickender Zähler 27 → 30 | Fakt, Neugier, kleine Dramaturgie |
| `out/sellcheck_tiktok_ad_B.mp4` | „POV: Du verkaufst auf 4 Plattformen und hast keine Ahnung, wo du stehst.“ | Wiedererkennung, Problem zuerst |

Beide laufen danach identisch: Demo (Datei rein → Ampel an → Report raus), drei Nutzen, Handlung.
Die Videos entstehen mit `python3 marketing/tiktok-ad-01/build_ad.py A` (oder `B`). Texte und Zeiten stehen im Skript.

## Was die Recherche ergeben hat (und wie es umgesetzt ist)

Quellen sind überwiegend Agentur- und Tool-Blogs, nicht TikTok selbst. Richtwerte, keine Garantien.

| Erkenntnis | Umsetzung im Video |
| --- | --- |
| Der Hook entscheidet in den ersten 2 bis 3 Sekunden. Problem oder Neugier, nicht Logo-Intro. | Sekunde 0: großer Satz, sofort Bewegung, kein Intro. |
| Aufbau Hook → Problem → Lösung → konkrete Handlung. | Szenen 1 bis 5 genau in dieser Reihenfolge. |
| Ein Nutzen pro Anzeige, Demo statt Behauptung. | Nutzen: Überblick über alle Plattformen. Die Demo zeigt die Ampel. |
| Marke früh zeigen (laut TikTok bei vielen Top-Ads in den ersten 3 s). | Logo und Name von Sekunde 0 oben. |
| 9–15 s laufen im Schnitt am besten, bis 60 s möglich. | 18,5 s, bewusst knapp über dem Richtwert wegen der Demo. Für 15 s kann Szene 4 gekürzt werden. |
| Für Ton gestalten, aber Untertitel mitdenken (viele schauen stumm). | Alle Aussagen stehen als große Schrift im Bild. Musik und Effekte unterstützen. |
| Safe Zone: oben ~160 px, unten ~340–440 px und rechts frei, dort sitzen Konto, Beschreibung, Button. | Text liegt zwischen y = 220 und y = 1420, rechts mindestens 140 px Rand. |
| CTA konkret und in den letzten ~5 s. | „Gratis testen. Link unten antippen.“ ab Sekunde 15,4. |
| Mehrere Hooks testen, Hook ist die wichtigste Variable. | Zwei Varianten A/B. |

Technik (TikTok In-Feed, laut Hilfe-Center, Stand Juni 2026): MP4 oder MOV, 9:16, mindestens 540×960, höchstens 500 MB, mindestens 516 kbit/s.
Unsere Dateien: 1080×1920, 4 MB, H.264. Das passt.

## Skript (Bild und Sprecher-Text, falls du es einsprechen willst)

| Zeit | Bild | Sprecher |
| --- | --- | --- |
| 0,0–2,6 | „Vinted meldet dich ab 30 Verkäufen.“ Zähler 27, 28, 29, 30, rot: „Meldegrenze erreicht“ | „Vinted meldet dich ab dreißig Verkäufen.“ |
| 2,6–5,6 | „Aber du verkaufst nicht nur dort.“ Vinted, Kleinanzeigen, eBay, Etsy mit „?“. „Jede zählt einzeln.“ | „Aber du verkaufst ja nicht nur dort. Und jede Plattform zählt einzeln.“ |
| 5,6–12,6 | „Datei rein. Ampel an. Report raus.“ Ampel mit vier Plattformen, danach Report mit Gewinn | „Lade deine Verkäufe hoch, sieh die Ampel pro Plattform und druck den Report aus.“ |
| 12,6–15,4 | Drei Haken: Alle Plattformen, Meldegrenzen als Ampel, Steuer-Report zum Drucken | „Alle Plattformen. Ein Überblick.“ |
| 15,4–18,5 | Logo, „Gratis testen.“, „Link unten antippen“ | „SellCheck. Gratis testen. Link unten.“ |

Variante B ersetzt die ersten sechs Sekunden: „POV: Du verkaufst auf 4 Plattformen und hast keine Ahnung, wo du stehst.“, dann „Ab 30 Verkäufen oder 2.000 € im Jahr meldet dich die Plattform an die Steuerbehörde. Jede Plattform zählt einzeln. Meldung heißt nicht automatisch: Steuern zahlen.“

## Beschreibung für die Anzeige (Vorschlag)

> Ab 30 Verkäufen oder 2.000 € melden Plattformen dich. Wo stehst du bei Vinted, Kleinanzeigen, eBay und Etsy? SellCheck zeigt es dir als Ampel. Gratis.

Bei Nicht-Spark-Anzeigen sind in der Beschreibung keine Links, Hashtags oder @-Erwähnungen möglich. Maximal vier Zeilen.

## Zielgruppe zum Testen (Vorschlag, nichts davon ist belegt)

Deutschland, 18–44 Jahre, Interessen Secondhand, Mode, Online-Shopping, Reseller. Erst klein testen (zwei Hooks, je ein eigener Ad Group, gleiches kleines Tagesbudget), nach einigen Tagen den Hook mit der besseren Daumen-Stopp-Rate und Klickrate weiterführen und neue Hooks nachlegen.

## Wichtig vor dem Schalten

1. **Ton:** Die Musik und Effekte im Video sind selbst erzeugte Platzhalter (kein fremdes Material, keine Lizenzfragen). Für die echte Anzeige besser in TikTok einen Titel aus der Commercial Music Library wählen oder einen Sprecher einsprechen.
2. **Aussagen:** „Vinted meldet ab 30 Verkäufen“ stützt sich auf Vinteds eigene DAC7-Seite (30 Verkäufe oder über 2.000 € je Jahr). Die Demo-Zahlen sind Beispiele und im Bild als „Beispieldaten“ gekennzeichnet. Die Anzeige verspricht keine Steuerersparnis.
3. **Zielseite:** Impressum und Datenschutz auf der Seite sind noch Entwürfe mit Platzhaltern. Ohne vollständiges Impressum und Datenschutz darf man in Deutschland nicht werben. Außerdem verlangt die Seite zuerst eine Registrierung, das kostet Klicks. Und die Adresse `gym7-fit.github.io/sellcheck-site` ist keine Marken-Adresse.
4. **Mail-Versand:** Registrierungs-Mails laufen über ein Gmail-Konto (etwa 500 Mails pro Tag, 30 pro Stunde eingestellt). Bei echtem Anzeigenverkehr reicht das nicht.
5. **Name:** SellCheck ist nicht auf Markenrechte geprüft.
6. **Konto:** Du brauchst ein TikTok-Werbekonto (Ads Manager) und musst die Anzeige selbst hochladen. Das habe ich nicht getan und nicht tun können.
