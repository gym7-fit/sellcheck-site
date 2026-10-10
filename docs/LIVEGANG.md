# Livegang-Checkliste SellCheck (Stand 9. Oktober 2026)

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

## 3a. GitHub Pages (Vorabansicht)

Der Workflow `.github/workflows/pages.yml` testet und veröffentlicht `site/`. Unter Settings → Pages muss „GitHub Actions“ als Quelle gewählt sein. Vor dem echten Livegang entfernen: `<meta name="robots" content="noindex, nofollow">` in allen Seiten (bei Rechtstexten und Marken-Seite je nach Wunsch) und `site/robots.txt`. GitHub Pages setzt keine eigenen Header: Die CSP steht als Meta-Tag in den Seiten, `frame-ancestors` und die übrigen Header aus `_headers` greifen nur bei Hosts mit Header-Unterstützung.

## 3. Hosting

Geeignet sind statische Hoster mit EU-Standort (z. B. Cloudflare Pages, Netlify, Vercel, eigener Webspace). Die Datei `_headers` wird von Netlify und Cloudflare Pages automatisch gelesen; bei Vercel die Werte in `vercel.json` übernehmen, bei Webspace in `.htaccess` oder Servereinstellungen.

Nach dem Deployment prüfen: Header kommen an (z. B. `curl -I https://deine-domain.de`), alle fünf Seiten laden ohne Konsolenfehler, die CSP blockiert nichts.

Optional: `brand.html` nicht mitveröffentlichen (interne Markenseite, ist auf `noindex` gesetzt).

## 4. Social Media

In `social/`: `og-image.png` (1200×630, Link-Vorschau), `profilbild.png` (800×800, TikTok/Instagram). Für die Link-Vorschau muss im `<head>` ein `og:image`-Tag mit **absoluter** Adresse ergänzt werden, sobald die Domain feststeht, zum Beispiel:

```html
<meta property="og:image" content="https://DEINE-DOMAIN/social/og-image.png">
<meta property="og:title" content="SellCheck – Alle Plattformen. Ein Überblick.">
<meta property="og:type" content="website">
```

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
- Spaltennamen der Anbieter ändern sich; der Import rät und lässt korrigieren. Die mitgelieferten Beispieldateien sind frei erfunden, keine Originalexporte. Gegen echte Exporte testen, sobald welche vorliegen.
- Keine Währungsumrechnung (Fremdwährungen werden gewarnt, nicht umgerechnet).
- Daten liegen nur im Browser. Regelmäßig als CSV exportieren.
- Keine Nutzungsmessung eingebaut (bewusst, Datenschutz). Entscheidung dazu offen.
- Nicht geprüft: Verhalten in Safari und Firefox (nur Chromium getestet), Darstellung der Word-Datei in Word.
