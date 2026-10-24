# PRODUCT.md: SellCheck (Webseite und Gratis-Tools)

## Was es ist

SellCheck zeigt Menschen, die auf Online-Plattformen verkaufen (Vinted, Kleinanzeigen, eBay, Etsy, Amazon, Flohmarkt), zwei Dinge:

1. **Wie nah sie an der Meldegrenze sind:** 30 Verkäufe oder 2.000 € Einnahmen je Plattform und Jahr (§ 4 Abs. 5 PStTG). Bei genau 2.000,00 € meldet die Plattform schon.
2. **Was nach Einkauf, Versand und Umsatzsteuer wirklich bleibt.** Claim: „Check, was wirklich bleibt.“

Die Webseite ist eine statische Seite mit Gratis-Tools im Browser:
- Ablauf in sechs Schritten mit Import der Exportdateien
- Meldegrenzen-Ampel
- Tracker mit Bestand
- Steuer-Export für Anlage EÜR und Anlage SO

Ergebnis und Downloads schaltet man mit der E-Mail-Adresse frei. Die iPhone-App (Basic, Essential, Premium) ist in Vorbereitung.

## Für wen

- **Gelegentliche Verkäufer**, die ausmisten und wissen wollen, ob eine Meldung droht. Meist privat, oft am Handy.
- **Wiederverkäufer** mit Einkauf und mehreren Plattformen. Sie brauchen Gewinn je Artikel, Bestand und eine Ausfüllhilfe für die Steuer.
- **Lage:** abends, zu Hause, am Handy oder Laptop. Beim Thema Steuern oft unsicher, manchmal besorgt.

## Was die Seite leisten muss

| Fläche | Modus | Erfolg heißt |
| --- | --- | --- |
| Startseite `index.html` | Überzeugen | In unter einer Minute verstanden, Ampel ausprobiert, Tools geöffnet |
| Tools `tools.html` | Bedienen | Verkäufe erfasst oder importiert, Ampel je Plattform gesehen, Report erzeugt |
| Hilfe `hilfe/*.html` | Lesen | Exportdatei gefunden, zurück in die Tools |
| Rechtsseiten | Lesen | Pflichtangaben auffindbar und lesbar |

## Wahrheiten, die nicht verhandelbar sind

- **Keine Steuer- oder Rechtsberatung.** Orientierung und Ausfüllhilfe, sonst nichts. Keine Zusagen wie „steuerfrei“ oder „rechtssicher“.
- **Daten bleiben im Browser.** Keine Fremdanbieter, keine Tracker, keine Cookies. Strenge Sicherheitsrichtlinie (`default-src 'none'`).
- **Preise und Stufen** (Stand 18.10.2026):
  - Starter 9,99 € einmalig, in Vorbereitung
  - Essential 4,99 € im Monat oder 39 € im Jahr
  - Premium 6,99 € im Monat oder 49 € im Jahr
  - Basic kostenlos, ohne Konto
  - Geplantes bleibt als „Geplant“ gekennzeichnet.
- **Keine erfundenen Zahlen,** Bewertungen oder Nutzerzähler. Beispieldaten sind immer als solche gekennzeichnet.

## Stimme

- Du-Ansprache, kurze Sätze, konkrete Zahlen, menschliche Sprache.
- Sachlich und ohne Alarm: Auch „kein Handlungsbedarf“ ist ein Ergebnis.
- Knöpfe sagen, was passiert. Fehler stehen direkt am Feld und nennen die Lösung.
- Keine Gedankenstriche, keine KI-Floskeln, keine Textwände.

## Plattform

Web, statisches HTML/CSS/JS ohne Build und ohne Framework, ausgeliefert über GitHub Pages (Vorabansicht). Gestaltung siehe `DESIGN.md`.
