# Rechtstexte: was fehlt und was geprüft werden muss (Stand 23. Oktober 2026)

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
| Datenschutz 10 | Supabase Inc. (Rechenzentrum Frankfurt): Auftragsverarbeitung mit Standardvertragsklauseln; Absender der Konto-Mails (Dienst, Sitz, Standort) | nach Vertragsabschluss |
| Datenschutz 11 | Stand-Datum | beim Veröffentlichen |
| Impressum | Antwortzeit (z. B. 2 Werktage) | was du einhalten kannst |
| AGB | Anbieter (wie Impressum), Stand-Datum | wie Impressum |
| AGB | Leistungsumfang bei Start, Preis und Lieferweg Starter-Paket | erst ab Verfügbarkeit |
| AGB | Umsatzsteuer im Preis oder Hinweis § 19 UStG | wie Impressum |
| AGB | Zahlungswege im Web, Abo-Verlängerung, Kündigungsfrist, Verwaltung über Apple-ID bzw. Web | bei Start der Bezahlstufen |
| AGB | Widerrufsbelehrung mit Muster-Formular, Erlöschen bei digitalen Inhalten | Rechtstexte-Dienst oder Kanzlei |
| AGB | Haftungsregelung, Änderungen der Bedingungen (Zustimmungsfiktion), Streitbeilegung | Rechtstexte-Dienst oder Kanzlei |

Stand der Zählung 23.10.2026: Impressum 9, Datenschutz 14, AGB 11 Platzhalter (Klasse `ph`).

## 2. Entscheidungen, die du treffen musst

1. **Zweck der E-Mail-Adresse:** Die Freischaltung des Ergebnisses ist die Gegenleistung. Ohne Haken „Tipps und Tricks“ darf die Adresse **nicht** für Werbung verwendet werden (Kopplungsverbot). Soll sie darüber hinaus gespeichert werden (etwa für Support oder Missbrauchsabwehr), muss das benannt werden, sonst nach dem Versand löschen.
2. **E-Mail-Dienst:** EU-Anbieter mit Double-Opt-In und Auftragsverarbeitungsvertrag. Danach erst die Endpunkte in `gate-config.js` eintragen und `connect-src` ergänzen.
3. **Hosting:** GitHub Pages ist nur für die Vorabansicht gedacht (siehe `LIVEGANG.md`, Abschnitt 1: Origin wird mit anderen Seiten des Kontos geteilt, Betreiber sitzt in den USA). Für den Livegang ein EU-Hosting mit eigener Domain wählen. Das bestimmt Datenschutz Abschnitt 3.
4. **Steuer-Aussagen:** „Keine Steuerberatung“, „Eine Meldung ist keine Steuerforderung“ und die Grenzwerte (30 Verkäufe oder 2.000 € je Plattform und Jahr) vom Steuerberater gegenlesen lassen (`LIVEGANG.md`, Abschnitte 1 und 6).

## 3. Faktenblatt für die rechtliche Prüfung (technischer Stand)

- Webseite: statische Seite, kein Server von uns, keine Datenbank, Konten im Browser (Mein SellCheck, Vorschau). Die Datenschutzerklärung wurde dafür in Auftrag 07 angepasst (31.10.2026), bleibt aber Entwurf.
- iPhone-App (in Entwicklung): Basic ohne Konto; Konto ab Essential bei Supabase (Frankfurt) mit Vorname, Nachname, Verkaufsart, Umsatzsteuer-Art; freiwillige Datensicherung von Artikeln, Fotos und Belegen mit Einwilligung; Kontolöschung in der App. `bestaetigt.html` ist die Zielseite des Bestätigungs-Buttons in der Konto-Mail.
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

## 4a. Fragen für die Anwalts- und Steuerprüfung (aus der Prüfung vom 23.10.2026)

Umgesetzt am 23.10.2026 nach Entscheidung von Louis: Punkt 1 (Wortlaut Datenschutz), Punkt 4 (Essential-Karte nur mit echten Zusätzen), Punkt 5 (Hinweissatz Gebühren), Punkt 6 (Hinweis Differenzbesteuerung). Die Formulierungen trotzdem im Rechts- und Steuercheck gegenlesen lassen.

1. **Datenschutz 2 und 10:** Dort steht „Für die iPhone-App legst du ein Konto an“. Die App läuft in Basic ohne Konto. Wortlaut so anpassen: „Ein Konto ist freiwillig und erst für Essential und Premium nötig“?
2. **Supabase Inc.:** Daten liegen in Frankfurt, der Anbieter sitzt in den USA. Reichen Auftragsverarbeitung und Standardvertragsklauseln, und muss der mögliche Drittlandzugriff in Abschnitt 10 genannt werden?
3. **Kontolöschung:** Abschnitt 10 verspricht Löschung „samt Sicherung“. Technisch muss die Lösch-Funktion alle Fotos erfassen (Fund 17 in `PRUEFUNG-2026-10-23.md`, wird in der App-Prüfung behoben). Aufbewahrungspflichten für Konto-Nachweise benennen?
4. **Angebotskarten (UWG, PAngV):** Preise für Stufen, die es noch nicht gibt („Geplant“, „In Vorbereitung“, „Noch nicht erhältlich“). Reicht das als Kennzeichnung? Darf die Essential-Karte Funktionen nennen, die Basic auch hat (Fund 3)?
5. **Meldegrenze:** Die Seite rechnet mit dem Verkaufspreis, das Gesetz mit der Vergütung nach Abzug der Plattform-Gebühren (§ 5 Abs. 2 PStTG). Ist der vorsichtigere Ansatz mit einem Hinweissatz in Ordnung (Fund 4)?
6. **Regelbesteuerung im Steuer-Export:** Volle Umsatzsteuer auf den Verkaufspreis, keine Differenzbesteuerung (§ 25a UStG). Hinweis im Report genug, oder die Option ganz weglassen (Fund 6)?
7. **Abos im Web (falls je angeboten):** Kündigungsbutton nach § 312k BGB, Widerruf digitaler Inhalte, Bestätigungsmail.
8. **Barrierefreiheit (BFSG):** Gilt die Ausnahme für Kleinstunternehmen, sobald Bezahlstufen verkauft werden?
9. **Vorabansicht auf GitHub Pages (USA):** Öffentlich erreichbar, `noindex`, ohne Formular-Versand. Reicht der Entwurfshinweis bis zum Umzug?

## 5. Reihenfolge

1. Hosting und E-Mail-Dienst wählen, Verträge abschließen.
2. Platzhalter in Impressum und Datenschutz füllen (dieses Blatt, Abschnitt 1).
3. Rechtstexte und Freischaltungs-Texte durch Rechtstexte-Dienst oder Kanzlei prüfen lassen.
4. Steuer-Aussagen und Report durch Steuerberater prüfen lassen (`LIVEGANG.md`, Abschnitt 6).
5. Entwurfshinweise und `noindex` entfernen, `robots.txt` öffnen, Adresse setzen (`scripts/set-site-url.py`).

## 6. Änderung für Mein SellCheck im Browser (Auftrag 07, 31.10.2026)

`datenschutz.html` beschreibt jetzt, was die Seite mit Konto und „Mein SellCheck“ tut (Abschnitte 2, 4, 6 und 10). Es wurden **keine Platzhalter ausgefüllt und keine Rechtsgrundlagen festgelegt**. Neu für den Anwalt zu prüfen:

1. **Sitzung im Browser** (localStorage, `sellcheck.session.v1`): Rechtsgrundlage und Einordnung nach § 25 TDDDG (Abschnitt 4, neuer Platzhalter).
2. **Rechtsgrundlage für Mein SellCheck im Browser** (Abschnitt 10, neuer Platzhalter): Die Seite schreibt Artikel direkt ins Konto, ohne den Schalter „Sicherung und Abgleich“ der App.
3. **Gelöschte Artikel:** Löschen markiert nur, die Zeile mit Name, Beträgen und Notizen bleibt im Konto. Die Funktion `purge_deleted_articles()` entfernt Zeilen mit einer Markierung über 90 Tage, ihr automatischer Aufruf ist nicht eingerichtet (Platzhalter in Abschnitt 10). Fristen und Aufbewahrung festlegen und den Aufruf einrichten oder die Beschreibung ändern.
4. **Abgleich statt Sicherung:** Abschnitt 10 spricht jetzt von „Sicherung und Abgleich“ (in beide Richtungen, auch Löschungen) wie in der App.
5. **Konto löschen im Browser** (Eingabe „löschen“): entfernt Konto, Profil, Artikel, Fotos und Belege über die Funktion `delete-account` (Version 2). Aufbewahrungspflichten weiterhin offen (siehe Punkt 3 oben).
6. **Dienstleister:** Es kommt kein neuer Dienst dazu. Der vorhandene Platzhalter zu Supabase gilt auch für den Browser.
