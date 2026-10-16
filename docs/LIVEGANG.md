# Livegang-Checkliste SellCheck (Stand 16. Oktober 2026)

Zu den Rechtstexten (Impressum, Datenschutz) gibt es eine eigene Liste mit allen Platzhaltern, Entscheidungen und dem Faktenblatt für die Prüfung: [`RECHTSTEXTE.md`](RECHTSTEXTE.md).

Die Seiten sind statisch (HTML, CSS, JS, kein Build-Schritt) und liegen im Ordner `site/`. Zum Testen mit Server: `npm start` (oder `python3 -m http.server 8000 --directory site`).

## 1. Vor dem Veröffentlichen (Pflicht)

- [ ] **Hosting vom VITARO-Backoffice trennen.** Solange SellCheck unter `gym7-fit.github.io` liegt, teilt es sich die Origin mit den anderen Seiten dieses Kontos, unter anderem dem Backoffice mit Kundendaten und Supabase-Sitzungen. Der Browser-Speicher (localStorage) gilt pro Origin: Ein Skriptfehler (XSS) in einer der Seiten könnte die Daten der anderen lesen. Für die Vorab-Ansicht ist das vertretbar (SellCheck hat keine Kundendaten und eine strenge CSP), **vor dem Livegang** gehört SellCheck auf eine eigene Domain oder in ein eigenes Konto.

- [ ] **Name und Marke:** „SellCheck“ ist ein Platzhalter. Marke bei DPMA und EUIPO prüfen, erst dann Domain sichern. `sellcheck.de` war am 9. Okt 2026 laut DENIC frei, `.com`, `.app`, `.io` waren vergeben (Stichtagsangabe, keine Reservierung).
- [ ] **Impressum:** `impressum.html` ausfüllen (gelbe Platzhalter), Hinweisbox und `noindex` entfernen.
- [ ] **Datenschutz:** `datenschutz.html` ausfüllen (Hosting-Anbieter, E-Mail-Dienst, Aufsichtsbehörde, Fristen) und von einem Rechtstexte-Dienst oder einer Kanzlei prüfen lassen.
- [ ] **Gewerbe anmelden** und Kleinunternehmerregelung klären (siehe Businessplan).
- [ ] **Steuerhinweise** und Formulierungen („keine Steuerberatung“) vom Steuerberater prüfen lassen.
- [ ] **Meldegrenze** nochmals gegen den Gesetzestext prüfen (§ 4 Abs. 5 Satz 1 Nr. 4 PStTG: befreit nur, wer weniger als 30 Fälle **und** weniger als 2.000 € hat; gemeldet wird also, sobald **eine** Grenze erreicht ist). Letzte bekannte Gesetzesänderung laut Recherche: 22.12.2025.

## 2. Wartelisten-Formular anschließen

1. EU-E-Mail-Dienst mit Double-Opt-In wählen (z. B. Brevo, CleverReach). Datenverarbeitungsvertrag abschließen.
2. In `waitlist.js` den Endpunkt bei `FORM_ENDPOINT` eintragen (muss mit `https://` beginnen).
3. In `_headers` bei `connect-src` den Host des Dienstes ergänzen.
4. Im Datenschutztext den Dienst eintragen.
5. Testen: Eintragen, Bestätigungsmail erhalten, Abmelden.

Bis dahin läuft das Formular im Demo-Modus und speichert nichts.

## 2b. Freischaltung per E-Mail-Adresse

Die Tools laufen ohne Anmeldung, Ergebnis, Report und Downloads werden nach Eingabe einer E-Mail-Adresse freigeschaltet (optional: Report per E-Mail, Tipps und Tricks). Einrichtung und rechtliche Punkte: [`EMAIL-ZUGANG.md`](EMAIL-ZUGANG.md).

## 3a. GitHub Pages (Vorabansicht)

Der Workflow `.github/workflows/pages.yml` testet und veröffentlicht `site/`. Unter Settings → Pages muss „GitHub Actions“ als Quelle gewählt sein. Vor dem echten Livegang entfernen: `<meta name="robots" content="noindex, nofollow">` in allen Seiten (bei Rechtstexten und Marken-Seite je nach Wunsch; bei den Hilfeseiten unter `site/hilfe/` steht er im Generator `scripts/build-hilfe.py`, danach `python3 scripts/build-hilfe.py` ausführen) und `site/robots.txt`. GitHub Pages setzt keine eigenen Header: Die CSP steht als Meta-Tag in den Seiten, `frame-ancestors` und die übrigen Header aus `_headers` greifen nur bei Hosts mit Header-Unterstützung.

## 3. Hosting

Geeignet sind statische Hoster mit EU-Standort (z. B. Cloudflare Pages, Netlify, Vercel, eigener Webspace). Die Datei `_headers` wird von Netlify und Cloudflare Pages automatisch gelesen; bei Vercel die Werte in `vercel.json` übernehmen, bei Webspace in `.htaccess` oder Servereinstellungen.

Nach dem Deployment prüfen: Header kommen an (z. B. `curl -I https://deine-domain.de`), alle fünf Seiten laden ohne Konsolenfehler, die CSP blockiert nichts.

Optional: `brand.html` nicht mitveröffentlichen (interne Markenseite, ist auf `noindex` gesetzt).

## 4. Social Media und Link-Vorschau

In `social/`: `og-image.png` (1200×630, Link-Vorschau), `profilbild.png` (800×800, TikTok/Instagram). `apple-touch-icon.png` (180×180) liegt direkt in `site/`.

Open Graph, canonical und Twitter-Karte stehen bereits auf Startseite, Tools und allen Hilfeseiten, derzeit mit der Adresse der GitHub-Pages-Vorabansicht. **Beim Livegang die echte Adresse setzen:**

```bash
python3 scripts/set-site-url.py https://deine-domain.de/
```

Das Skript ersetzt die Adresse in den Seiten und im Hilfe-Generator, erzeugt die Hilfeseiten neu und schreibt `site/sitemap.xml`. `npm test` prüft Link-Vorschau, Bildgrößen und canonical.

## 4b. Erklärfilm (Startseite, Abschnitt „Der Überblick in 50 Sekunden“)

Dateien in `site/media/`: `sellcheck-erklaerfilm.mp4` (1280×720, ca. 9 MB, Metadaten am Anfang), `…-poster.jpg`, `….de.vtt` (Untertitel). Das Video lädt erst auf Klick (`preload="none"`), startet nie von selbst und hat Untertitel und einen Text zum Film.

- [ ] Stimme ist **KI-generiert** (ElevenLabs, „Judith Maas“): Hinweis steht unter dem Video; bei TikTok/YouTube als KI-Inhalt kennzeichnen.
- [ ] ElevenLabs-Tarif prüfen: Darf die Bibliotheksstimme in der Werbung genutzt werden (kommerzielle Nutzung)?
- [ ] Musik: eigene Synthese plus CC0-Aufnahmen (VSCO-2-CE), kein Nachweis nötig. Lizenznotiz: `marketing/corporate-video/music/LIZENZ.md`.
- Neu rendern: Quellcode und Ablauf in `marketing/corporate-video/README.md`; Untertitel mit `make_captions.py`.

## 5. Tests

Import-Logik, Steuerberechnung, Anmeldung und Freischalt-Regeln des Ablaufs, im Repo-Hauptordner:

```bash
npm test
```

## 6. Steuer-Export vor dem Livegang

- [ ] Einen Steuerberater den Report (PDF) und das Journal (CSV) mit Beispieldaten prüfen lassen: Bezeichnungen der Positionen, Hinweise, Aufteilung der sonstigen Betriebsausgaben.
- [ ] Mit dem Steuerberater klären, ob er ein bestimmtes Importformat (z. B. DATEV) wünscht. Recherche und Entscheidungen: `STEUER-EXPORT.md`.
- [ ] Den Report im Druckdialog (A4) in mindestens Chrome und Safari ansehen. Die Druckdarstellung wurde nur im Browser geprüft, nicht auf Papier.
- [ ] Zeilennummern der Anlage EÜR bewusst nicht enthalten: nur ergänzen, wenn sie am amtlichen Formular des Jahres geprüft sind.

## 7. Bekannte Grenzen

- Kein offizieller Verkaufsexport für Vinted und Kleinanzeigen belegt: Import dort über Bank-/PayPal-Auszüge oder manuell.
- Spaltennamen der Anbieter ändern sich; der Import rät und lässt korrigieren. Die Beispieldaten in `parse-lib.js` (nur für Tests, nicht in der Oberfläche) sind frei erfunden, keine Originalexporte. Gegen echte Exporte testen, sobald welche vorliegen.
- Keine Währungsumrechnung (Fremdwährungen werden gewarnt, nicht umgerechnet).
- Daten liegen nur im Browser. Regelmäßig als CSV exportieren.
- Keine Nutzungsmessung eingebaut (bewusst, Datenschutz). Entscheidung dazu offen.
- Nicht geprüft: Verhalten in Safari und Firefox (nur Chromium getestet), Darstellung der Word-Datei in Word.
