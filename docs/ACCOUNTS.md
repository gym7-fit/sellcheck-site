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

## Netzschicht (`site/konto-net.js`)

Lädt Artikel, Profil und Fotos aus dem Konto und schreibt Änderungen zurück, ohne Oberfläche (die kommt in Auftrag 03). `SCKontoNet.createStore({ url, anonKey, client, fetch })` mit dem Client aus `auth-lib.js`. Browser: `window.SCKontoNet`, noch auf keiner Seite eingebunden.

- **Laden:** `loadAll()` seitenweise (1000 je Anfrage, `pageSize` einstellbar), ohne gelöschte, mit Merker. `loadChanges(merker)` holt alles seit dem Merker mit 120 s Überlappung, auch Löschungen; zusammenführen mit `SCKonto.mergeChanges`.
- **Schreiben:** `save(zeilen)` als Upsert (`on_conflict=user_id,id`, `resolution=merge-duplicates`), höchstens 500 je Anfrage, jede Zeile mit `user_id` aus der Sitzung. Die ältere Änderung verliert gegen die neuere, das entscheidet der Trigger `articles_sync_guard` im Konto. `remove(id, now)` setzt nur `deleted_at` und `changed_at`.
- **Profil:** `loadProfile()` mit `first_name,last_name,seller_mode,vat_mode,vat_rate`.
- **Fotos:** `uploadPhoto` (nur JPEG bis 5 MB, sonst Meldung ohne Anfrage), `photoBlob`, `deletePhotos`. Pfade wie in der App (`SCKonto.storagePath`). Pfade, die nicht mit der eigenen Nutzerkennung beginnen oder Umwege enthalten, werden weder geladen noch gelöscht.
- **Sitzung:** Bei 401 wird genau einmal erneuert (`getSession({ force: true })`) und die Anfrage wiederholt. Klappt das nicht, kommt `{ ok: false, expired: true }`, die Seite geht dann auf `anmelden.html#abgelaufen`.
- **Meldungen:** „Keine Verbindung“ aus `auth-lib.js`, sonst allgemeine Texte ohne Einzelheiten aus dem Konto.
- **Tests:** `tests/konto-net.test.js` gegen `tests/support/fake-supabase.js`. Der Nachbau kennt jetzt Artikel (mit Trigger-Regel), Profile, Foto-Ablage, `/mock/remote` und `/mock/state` wie `sellcheck-app/Tests/mock_supabase.py`. Ändert sich der Python-Nachbau, den JS-Nachbau mitziehen.

## Bekannt und offen

- Echte Registrierung und Mails: macht Louis selbst, die Tests laufen nur gegen den Nachbau.
- Profil ändern, Passwort ändern, Konto löschen im Browser: Auftrag 05.
- Kauf im Browser und Freischaltung nach Stufe: Phase 3.
- Datenschutzerklärung für das Konto im Browser: Auftrag 07 (Rechtstext).
- Auf einer statischen Seite schützt die Anmeldung nur die Oberfläche. Echter Schutz der Daten kommt aus den Zugriffsregeln der Datenbank (Zeilensicherheit je Nutzer).
