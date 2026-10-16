# Rechtstexte: was fehlt und was geprüft werden muss (Stand 16. Oktober 2026)

`impressum.html` und `datenschutz.html` sind **Entwürfe** (gelbe Platzhalter, Hinweisbox, `noindex`). Ich kann Angaben, die nur du kennst, nicht erfinden, und keine Rechtsberatung geben. Diese Datei sammelt alles, was vor dem Livegang ausgefüllt, entschieden und geprüft werden muss.

## 1. Angaben, die du liefern musst

| Wo | Platzhalter | Was du angibst |
| --- | --- | --- |
| Impressum | Vor- und Nachname, Straße, PLZ Ort | ladungsfähige Anschrift (Postfach genügt nicht) |
| Impressum | E-Mail, Telefon oder zweiter schneller Kontaktweg | schnelle elektronische Kontaktaufnahme und unmittelbare Kommunikation |
| Impressum | Umsatzsteuer | USt-IdNr. **oder** Hinweis Kleinunternehmerregelung (§ 19 UStG) |
| Impressum | Verantwortlicher für Inhalte | Name und Anschrift |
| Impressum | Streitbeilegung | Teilnahme oder Nichtteilnahme (Formulierung vom Rechtstexte-Dienst) |
| Datenschutz 1 | Verantwortlicher | wie Impressum |
| Datenschutz 3 | Hosting-Anbieter, Sitz, Serverstandort, Speicherdauer, Auftragsverarbeitung | siehe Abschnitt 3 unten (Hosting) |
| Datenschutz 5 | Zweck der Speicherung der Adresse nach der Freischaltung | Entscheidung, siehe unten |
| Datenschutz 5 und 7 | E-Mail-Dienst: Anbieter, Sitz, Standort in der EU, Vertrag, Speicherdauer, Löschung nach Versand, Frist für Einwilligungsnachweis | nach Wahl des Dienstes |
| Datenschutz 9 | zuständige Landesdatenschutzbehörde | nach deinem Wohnsitz |
| Datenschutz 10 | Stand-Datum | beim Veröffentlichen |

## 2. Entscheidungen, die du treffen musst

1. **Zweck der E-Mail-Adresse:** Die Freischaltung des Ergebnisses ist die Gegenleistung. Ohne Haken „Tipps und Tricks“ darf die Adresse **nicht** für Werbung verwendet werden (Kopplungsverbot). Soll sie darüber hinaus gespeichert werden (etwa für Support oder Missbrauchsabwehr), muss das benannt werden, sonst nach dem Versand löschen.
2. **E-Mail-Dienst:** EU-Anbieter mit Double-Opt-In und Auftragsverarbeitungsvertrag. Danach erst die Endpunkte in `gate-config.js` eintragen und `connect-src` ergänzen.
3. **Hosting:** GitHub Pages ist nur für die Vorabansicht gedacht (siehe `LIVEGANG.md`, Abschnitt 1: Origin wird mit anderen Seiten des Kontos geteilt, Betreiber sitzt in den USA). Für den Livegang ein EU-Hosting mit eigener Domain wählen. Das bestimmt Datenschutz Abschnitt 3.
4. **Steuer-Aussagen:** „Keine Steuerberatung“, „Eine Meldung ist keine Steuerforderung“ und die Grenzwerte (30 Verkäufe oder 2.000 € je Plattform und Jahr) vom Steuerberater gegenlesen lassen (`LIVEGANG.md`, Abschnitte 1 und 6).

## 3. Faktenblatt für die rechtliche Prüfung (technischer Stand)

- Statische Seite, kein Server von uns, keine Datenbank, keine Konten (geparkt in `parked/accounts/`).
- **Keine** Cookies, kein Tracking, keine Analyse, keine Werbung, keine Einbettung von Dritten; Schriften, Skripte, Bilder und Video liegen auf der eigenen Origin (strenge CSP: `default-src 'none'`).
- Browser-Speicher (localStorage): `sellcheck.sales.v1` (Verkäufe), `sellcheck.wizard.v1` (Ablauf), `sellcheck.settings.v1` (Einstellungen), `sellcheck.lead.v1` (Freischaltung mit E-Mail-Adresse). Nichts davon wird gesendet, solange keine Endpunkte eingetragen sind.
- Datenfluss nach außen nur bei eingetragenen Endpunkten: `leadEndpoint` (E-Mail-Adresse, Einwilligungen mit Wortlaut und Zeitpunkt) und `reportEndpoint` (E-Mail-Adresse plus Report: Verkaufsdaten verlassen das Gerät, einmalig, nur nach Haken oder Klick).
- Datei-Import: lokal im Browser, kein Upload.
- Film: selbst gehostet, lädt erst beim Start, Sprecherstimme KI-generiert (ElevenLabs), Musik eigene Synthese plus CC0-Aufnahmen.
- Texte der Einwilligungen stehen in `site/gate-lib.js` (`TEXTS`) und gelten zugleich als Nachweis.

## 4. Zusätzlich prüfen lassen

- **Newsletter („Tipps und Tricks“):** Double-Opt-In, Abmeldelink in jeder Mail, Widerruf jederzeit, Absender und Impressum korrekt, Einwilligung dokumentieren (Wortlaut, Zeitpunkt).
- **Kennzeichnung KI-Stimme:** Auf TikTok und YouTube als KI-generiert markieren (Plattformvorgabe). Einordnung nach EU-KI-Verordnung (Transparenzpflichten) im Rechtscheck mitnehmen. Nutzungsrechte der ElevenLabs-Stimme „Judith Maas“ im Werbeeinsatz prüfen (hängt vom Tarif ab).
- **Marke:** „SellCheck“ bei DPMA und EUIPO recherchieren, bevor Domain und Werbung hängen (`LIVEGANG.md`, Abschnitt 1).
- **Plattformnamen:** Nur als Text genannt, keine Logos; Hinweis „unabhängig von den genannten Plattformen“ steht im Film und auf der Seite. Im Rechtscheck bestätigen lassen.
- **Hinweise zur Einordnung privat/gewerblich:** neutral formuliert, keine Beratung; ebenfalls vom Steuerberater prüfen lassen.

## 5. Reihenfolge

1. Hosting und E-Mail-Dienst wählen, Verträge abschließen.
2. Platzhalter in Impressum und Datenschutz füllen (dieses Blatt, Abschnitt 1).
3. Rechtstexte und Freischaltungs-Texte durch Rechtstexte-Dienst oder Kanzlei prüfen lassen.
4. Steuer-Aussagen und Report durch Steuerberater prüfen lassen (`LIVEGANG.md`, Abschnitt 6).
5. Entwurfshinweise und `noindex` entfernen, `robots.txt` öffnen, Adresse setzen (`scripts/set-site-url.py`).
