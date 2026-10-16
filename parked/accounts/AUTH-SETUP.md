# Anmeldung einrichten

Die Seite ist statisch, es gibt kein eigenes Backend. Die Anmeldung läuft deshalb entweder über **Supabase Auth** (echte Konten) oder im **Demo-Modus** (Konten nur im Browser). Welcher Modus aktiv ist, entscheidet `site/auth-config.js`.

| | Demo-Modus (Standard) | Supabase |
| --- | --- | --- |
| Aktiv, wenn | `supabaseUrl` und `supabaseAnonKey` leer sind | beide ausgefüllt sind |
| Konten | nur in diesem Browser (localStorage) | echte Konten auf dem Server |
| Passwort | als PBKDF2-Hash (600.000 Runden, Salt) gespeichert | von Supabase gehasht |
| E-Mail-Bestätigung, Passwort zurücksetzen | nein | ja |
| Schutz der Daten | **keiner**. Wer das Gerät hat, kann den Speicher lesen | Konto ist echt, die Tool-Daten liegen aber weiter im Browser |

> **Ehrlich gesagt:** Eine Anmeldung auf einer statischen Seite sperrt nur die Oberfläche. Die Tool-Daten liegen im Browser des Geräts und sind dort für jeden mit Zugriff auf das Gerät lesbar. Echter Schutz und Sicherung über mehrere Geräte entstehen erst, wenn Daten auf einem Server liegen (geplante Pro-Funktion). Bis dahin ist das Konto vor allem Zugangsvoraussetzung und Basis für spätere Funktionen.

## Supabase einrichten

**Wichtig: Lege ein eigenes, neues Supabase-Projekt für SellCheck an. Verwende nicht das Projekt der VITARO-Seiten.** Supabase-Nutzer gelten projektweit: Wer sich bei SellCheck registriert, hätte sonst ein gültiges Konto im VITARO-Projekt und je nach dortigen Richtlinien Zugriff auf Kundendaten.

1. Auf supabase.com ein neues Projekt anlegen (Region in der EU, z. B. Frankfurt).
2. **Authentication → Providers → Email** aktivieren. Empfohlen: „Confirm email“ an, „Minimum password length“ auf 10.
3. **Authentication → URL Configuration:**
   - **Site URL:** die Adresse der Seite, z. B. `https://gym7-fit.github.io/sellcheck-site/`
   - **Redirect URLs:** `https://gym7-fit.github.io/sellcheck-site/login.html` (und `http://localhost:8000/login.html` zum lokalen Testen)
4. **Project Settings → API:** „Project URL“ und den öffentlichen „anon“ bzw. „publishable“ Key kopieren. Der Service-Role-Key gehört **nie** in diese Dateien.
5. In `site/auth-config.js` beides eintragen:

   ```js
   supabaseUrl: "https://abcdefgh.supabase.co",
   supabaseAnonKey: "eyJ…",
   ```
6. **CSP verengen:** In allen `site/*.html` (Meta-Tag) und in `site/_headers` steht `connect-src 'self' https://*.supabase.co`. Ersetze `*.supabase.co` durch den genauen Host deines Projekts.
7. Im Datenschutztext (`site/datenschutz.html`, Abschnitt 5) den Dienstleister, die Region und den Auftragsverarbeitungsvertrag eintragen.
8. Testen: Registrieren → Bestätigungs-Mail → Link öffnen → Anmelden → Weiterleitung auf die Tools-Seite. Dann „Passwort vergessen“.

## Zugang freischalten oder sperren

`required: false` in `site/auth-config.js` macht die Tools wieder ohne Anmeldung nutzbar. Die Anmeldung bleibt optional bestehen.

## Hinweise

- **Zugangshürde:** Eine Pflichtanmeldung senkt erfahrungsgemäß die Nutzung gratis angebotener Werkzeuge deutlich. Wenn die Reichweite über TikTok zählt, miss die Absprungrate an der Registrierung und erwäge `required: false`.
- **Brute-Force:** Im Demo-Modus sperrt die Seite nach 5 Fehlversuchen 60 Sekunden, das ist nur eine Hürde im Browser. Bei Supabase gelten dessen Rate-Limits.
- **Gemeinsame Origin:** Solange die Seite unter `gym7-fit.github.io` liegt, teilt sie den Browser-Speicher mit den anderen Projekten des Kontos, auch die Sitzung. Siehe `docs/LIVEGANG.md`.
- **Mehrere Konten pro Browser** teilen sich dieselben Tool-Daten. Eine getrennte Ablage je Konto gibt es erst mit Server-Daten.

## Aktueller Stand (11.10.2026)

- Eigenes Supabase-Projekt „sellcheck database“, Region Frankfurt (eu-central-1), Referenz `xjogkqttzfsgjeqhkndf`.
- Eingetragen in `site/auth-config.js`: Project-URL und anon-Key. Damit ist der Demo-Modus aus, Registrierung und Anmeldung laufen über Supabase.
- Eingestellt: E-Mail-Anmeldung an, Bestätigungs-Mail Pflicht, Mindestlänge 10, Site-URL `https://gym7-fit.github.io/sellcheck-site/`, Redirect-URLs `login.html` und `tools.html` (plus lokale Testadressen).
- Data API ist aus; die App nutzt nur Auth. Soll später etwas in der Cloud gespeichert werden, Data API einschalten und für jede Tabelle Row Level Security anlegen.
- Mail-Versand: eigener SMTP-Server über Gmail (`smtp.gmail.com`, Port 465, Absender `info.sellcheck@gmail.com`, App-Passwort nur im Supabase-Dashboard). Mail-Limit 30 pro Stunde, Gmail erlaubt etwa 500 pro Tag. Mail-Vorlagen sind auf Deutsch.
- Später: eigene Domain mit Mail-Adresse. Dann nur die SMTP-Felder in Supabase tauschen (Authentication → Emails → SMTP Settings), die App bleibt unverändert.
