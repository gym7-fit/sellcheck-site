# Freischaltung per E-Mail-Adresse (Stand 13. Oktober 2026)

Die Tools sind ohne Anmeldung nutzbar. **Ergebnis, Report und Downloads** zeigt die Seite erst, nachdem eine E-Mail-Adresse eingegeben wurde. Das Formular hat zwei freiwillige Haken (beide standardmäßig aus):

1. **Report zusätzlich per E-Mail an mich senden**
2. **Tipps und Tricks per E-Mail erhalten** (Newsletter, Einwilligung)

## Was gesperrt ist

| Bereich | Verhalten ohne Freischaltung |
| --- | --- |
| „Ergebnis ansehen“ (Überprüfung mit Ergebnis, Meldegrenzen, Report-Link) | Formular erscheint, danach geht es weiter |
| Downloads (Report als HTML-Datei, CSV: Journal, Summen, Anlage SO, Sicherung) | Formular erscheint, danach startet der Download |
| `report.html` (druckbarer Report) | Weiterleitung auf `tools.html#review`, dort erscheint das Formular |
| Schritte 1 bis 6 (Eingabe, Import, Zwischensummen, Meldegrenzen-Check) | frei zugänglich |

Die Freischaltung steht im Browser unter `sellcheck.lead.v1` (localStorage). „Adresse ändern“ im Ergebnis hebt sie auf. **Das ist eine weiche Sperre**: Wer den Speicher manipuliert, sieht das Ergebnis. Das ist bei einer rein clientseitigen Seite nicht vermeidbar und für den Zweck (Adresse einsammeln) in Ordnung.

## Dateien

- `site/gate-lib.js`: Prüfung der Adresse, Bereinigung, Nutzlast, Texte der Haken (getestet in `tests/gate.test.js`)
- `site/gate.js`: Formular, Speicherung, optionaler Versand
- `site/gate-config.js`: **Endpunkte eintragen**
- `site/gate-guard.js`: Schutz der Report-Seite
- `site/gate.css`: Darstellung

## Was gesendet wird, wenn Endpunkte eingetragen sind

- `leadEndpoint` (POST, JSON): `{ email, source: "tools-gate", consents: { tips: {given, text, at}, report: {given, text, at} } }`. Keine Verkaufsdaten.
- `reportEndpoint` (POST, JSON), nur bei Haken oder Klick auf „Report per E-Mail senden“: `{ email, type: "report", year, mode, summary, files: [{ name, type, content }] }` (Report als HTML-Datei plus CSV-Dateien). Hier verlassen Verkaufsdaten das Gerät. Das ist im Formular offengelegt und im Datenschutz-Entwurf beschrieben.

Solange beide Endpunkte leer sind (Vorabversion), wird **nichts gesendet**. Die Adresse schaltet nur lokal frei, und der Report lässt sich per `mailto:`-Link an die eigene Adresse vorbereiten.

## Vor dem Livegang (Pflicht)

- [ ] E-Mail-Dienst mit **Double-Opt-In** für „Tipps und Tricks“ wählen (EU-Anbieter, Vertrag zur Auftragsverarbeitung).
- [ ] Endpunkte in `gate-config.js` eintragen (nur `https://`) und die Hosts in der CSP (`connect-src`, Meta-Tag in den Seiten und `_headers`) freigeben.
- [ ] Versand des Reports: Dienst, der aus der Nutzlast eine E-Mail erzeugt (z. B. Supabase Edge Function plus transaktionaler Mailversand). Nach dem Versand nichts speichern.
- [ ] **Datenschutzerklärung** Abschnitt 5 ausfüllen und von einem Rechtstexte-Dienst oder einer Kanzlei prüfen lassen. Offen: Zweck der Speicherung der Adresse nach der Freischaltung (ohne Haken darf sie nicht für Werbung genutzt werden).
- [ ] **Kopplungsverbot** beachten: Die Freischaltung darf nicht von der Einwilligung in „Tipps und Tricks“ abhängen. Der Haken bleibt freiwillig und standardmäßig aus.
- [ ] Newsletter-Mails: Abmeldelink in jeder Mail, Widerruf jederzeit, Impressum und Absender korrekt.
- [ ] Beschreibung in der Werbung (TikTok-Ads sagen teils „kostenlos, mit Konto“) auf „kostenlos, ohne Anmeldung“ anpassen.
- [x] Konten im Browser gibt es seit 30.10.2026 (Anmelden, Registrieren, Mein SellCheck), siehe `docs/ACCOUNTS.md`.
