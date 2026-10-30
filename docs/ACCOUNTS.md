# Konto im Browser (Mein SellCheck)

Stand 30.10.2026. Dasselbe Konto wie in der iPhone-App (Supabase, Frankfurt, Projekt `xjogkqttzfsgjeqhkndf`). Phase 2, Schritt 1 des Konzepts `sellcheck-app/docs/KONZEPT-LAPTOP-UND-WEB.md`. Die Seiten sind nicht indexiert und stehen nur im Fuß („Mein SellCheck“), nicht in der Kopfzeile.

## Dateien

| Datei | Zweck |
| --- | --- |
| `site/anmelden.html` | Anmelden, „Passwort vergessen“ in drei Schritten (Code anfordern, Code prüfen, neues Passwort) |
| `site/registrieren.html` | Konto erstellen (Vorname, Nachname, E-Mail, Passwort zweimal, Verkaufsart, Datenschutz-Häkchen, freiwillig Tipps) |
| `site/mein.html` | Platzhalter: „Angemeldet als …“ und Abmelden. Ohne Sitzung geht es zu `anmelden.html`. Inhalt kommt in Auftrag 03 |
| `site/auth-lib.js` | Passwort-Regeln und Fehlertexte wie die App, Zugang zum Dienst, Sitzung (`localStorage`, Schlüssel `sellcheck.session.v1`) |
| `site/auth-ui.js` | Bedienung der drei Seiten (nur feste Weiterleitungsziele, nur `textContent`) |
| `site/auth-config.js` | Adresse des Projekts und öffentlicher „anon“-Schlüssel (kein Geheimnis) |
| `site/auth.css` | Aussehen der Seiten |
| `tests/auth.test.js`, `tests/support/fake-supabase.js` | Tests: Regeln mit denselben Beispielen wie die App, Ablauf gegen einen Nachbau der Schnittstelle, Seiten, Sicherheitsrichtlinie |

## Verhalten

- **Nur echte Konten.** Es gibt keinen Demo-Modus und keine Umschaltung über die Adresszeile.
- **Passwort:** mindestens 10 Zeichen, ein Großbuchstabe, ein Sonderzeichen, dazu die Verbote der App (häufige Passwörter, Folgen, Wiederholungen, Name oder E-Mail im Passwort). Die Regeln stehen live unter dem Feld. Die Liste der Wörter stammt maschinell aus `sellcheck-app/SellCheck/Logic/PasswordPolicy.swift`: Ändert sich die App-Liste, `auth-lib.js` angleichen (die Beispiele in `tests/auth.test.js` entsprechen `Tests/main.swift`).
- **Kein Verrat von Konten:** Bei falschem Passwort und bei unbekannter Adresse dieselbe Meldung, „Passwort vergessen“ antwortet immer gleich.
- **Sitzung:** Zugangs- und Erneuerungs-Token in `localStorage`, 60 Sekunden vor Ablauf erneuert. Ist die Erneuerung abgelaufen, wird abgemeldet und `anmelden.html#abgelaufen` zeigt „Deine Anmeldung ist abgelaufen. Melde dich noch einmal an.“ Abmelden löscht den Eintrag immer, auch ohne Antwort des Servers.
- **Bestätigung der E-Mail:** `redirect_to` zeigt auf `bestaetigt.html`. Dort öffnet „SellCheck öffnen“ die App, „Im Browser anmelden“ führt zu `anmelden.html`.
- **Sicherheitsrichtlinie:** Nur die drei Konto-Seiten dürfen `https://xjogkqttzfsgjeqhkndf.supabase.co` erreichen (Meta-Tag in jeder Seite, zusätzlich Hinweis in `site/_headers`). `mein.html` darf zusätzlich `blob:`-Bilder. Alle anderen Seiten bleiben unverändert streng. Ein Test prüft das.

## Einrichtung im Supabase-Projekt

Ist erledigt: Redirect-URL `https://gym7-fit.github.io/sellcheck-site/bestaetigt.html`, Mail-Vorlagen, Mindestlänge 10. Weitere Schritte stehen in `sellcheck-app/docs/SUPABASE-EINRICHTEN.md`. Beim Wechsel auf eine eigene Domain: `scripts/set-site-url.py`, in Supabase die neue Redirect-URL eintragen, in `auth-config.js` bleibt die Projekt-Adresse.

## Bekannt und offen

- Echte Registrierung und Mails: macht Louis selbst, die Tests laufen nur gegen den Nachbau.
- Profil ändern, Passwort ändern, Konto löschen im Browser: Auftrag 05.
- Kauf im Browser und Freischaltung nach Stufe: Phase 3.
- Datenschutzerklärung für das Konto im Browser: Auftrag 07 (Rechtstext).
- Auf einer statischen Seite schützt die Anmeldung nur die Oberfläche. Echter Schutz der Daten kommt aus den Zugriffsregeln der Datenbank (Zeilensicherheit je Nutzer).
