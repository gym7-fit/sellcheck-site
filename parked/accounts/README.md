# Konten (geparkt)

Stand 13. Oktober 2026. Die Tools laufen ohne Anmeldung, Ergebnis, Report und Downloads werden per E-Mail-Adresse freigeschaltet (siehe `docs/EMAIL-ZUGANG.md`). Anmeldung und Registrierung sind deshalb **aus der Auslieferung (`site/`) herausgenommen**, aber vollständig erhalten und getestet. Sie kommen zurück, wenn es Pro-Abos gibt.

## Inhalt

| Datei | Zweck |
| --- | --- |
| `auth-lib.js` | Logik (Passwort-Regeln, Sitzung, Supabase-Anbindung), Tests in `tests/auth.test.js` |
| `auth.js` | Seitenübergreifend: schützt Seiten, steuert Menü (Anmelden/Abmelden) |
| `auth-ui.js` | Formulare in `login.html` und `register.html` |
| `auth-config.js` | Einstellungen, Supabase-URL und öffentlicher Anon-Key |
| `login.html`, `register.html` | Seiten |
| `AUTH-SETUP.md` | Einrichtung des Supabase-Projekts (Redirect-URLs, Bestätigungs-Mail, Passwortlänge) |

## Wieder einschalten (Pro)

1. Dateien zurück nach `site/` verschieben (`git mv parked/accounts/* site/`, `README.md` und `AUTH-SETUP.md` nach `docs/`).
2. In den Seiten, die Menü oder Schutz brauchen (`index.html`, `tools.html`, `report.html`, `brand.html`, `datenschutz.html`, `impressum.html`, `404.html`), vor den anderen Skripten einbinden:
   `auth-config.js`, `auth-lib.js`, `auth.js`.
3. Menü: „Anmelden“ und „Registrieren“ (`class="auth-guest"`) sowie „Zu den Tools“ und „Abmelden“ (`class="auth-user"`, `id="logout-btn"`) wieder in die Navigation setzen. Vorlage: `login.html`.
4. CSP: in den Meta-Tags aller Seiten und in `site/_headers` bei `connect-src` den Host des eigenen Supabase-Projekts ergänzen (nicht `*.supabase.co`, sondern den genauen Host).
5. Entscheiden, was hinter dem Login liegt (z. B. Sicherung über mehrere Geräte, Pro-Funktionen). Für geschützte Seiten `data-auth="required"` am `<html>`-Element setzen und in `auth-config.js` `required: true`. Die Freischaltung per E-Mail bleibt für Gratis-Nutzer bestehen.
6. Datenschutz-Entwurf: Abschnitt „Konto und Anmeldung“ wieder aufnehmen (Text steht in der Git-Historie vor dem Park-Commit).
7. Tests: `npm test`.

## Hinweise

- **Passwortlos wäre sinnvoller.** Wenn Pro startet, ist ein Login per E-Mail-Link (Magic Link) einfacher und sicherer als Passwörter, und er passt zu den bereits gesammelten und bestätigten Adressen.
- Die Stile für die Anmelde-Seiten (`.auth-*`) liegen weiter in `site/style.css`.
- Ehrlicher Hinweis aus `AUTH-SETUP.md`: Auf einer statischen Seite sperrt eine Anmeldung nur die Oberfläche. Echter Schutz entsteht erst mit serverseitigen Daten.
- Der öffentliche Anon-Key in `auth-config.js` ist kein Geheimnis, gehört aber zu einem **eigenen** Supabase-Projekt für SellCheck.
