# Konto im Browser (Mein SellCheck)

Stand 30.10.2026. Dasselbe Konto wie in der iPhone-App (Supabase, Frankfurt, Projekt `xjogkqttzfsgjeqhkndf`). Phase 2, Schritt 1 des Konzepts `sellcheck-app/docs/KONZEPT-LAPTOP-UND-WEB.md`. Die Seiten sind nicht indexiert und stehen nur im Fuß („Mein SellCheck“), nicht in der Kopfzeile.

## Dateien

| Datei | Zweck |
| --- | --- |
| `site/anmelden.html` | Anmelden, „Passwort vergessen“ in drei Schritten (Code anfordern, Code prüfen, neues Passwort) |
| `site/registrieren.html` | Konto erstellen (Vorname, Nachname, E-Mail, Passwort zweimal, Verkaufsart, Datenschutz-Häkchen, freiwillig Tipps) |
| `site/mein.html`, `site/mein.js`, `site/mein.css` | „Mein SellCheck“: Reiter Übersicht, Artikel, Meldegrenze, Konto. Ohne Sitzung geht es zu `anmelden.html`. Artikel anlegen, ändern, löschen, Fotos und Belege (Auftrag 03). Import, Export und Übernahme aus den Gratis-Tools folgen in Auftrag 04 |
| `site/auth-lib.js` | Passwort-Regeln und Fehlertexte wie die App, Zugang zum Dienst, Sitzung (`localStorage`, Schlüssel `sellcheck.session.v1`) |
| `site/auth-ui.js` | Bedienung von Anmelden und Registrieren (nur feste Weiterleitungsziele, nur `textContent`) |
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

## Import, Übernahme und Export (Auftrag 04)

Im Reiter Artikel, Bereich „Importieren und exportieren“ (`mein.js`, Logik in `konto-lib.js` und `parse-lib.js`).

- **Übernahme aus den Gratis-Tools:** liest `sellcheck.sales.v1` (oder `vintcheck.sales.v1`) nur, schreibt nie dorthin. Doppelte erkennt `planTakeover` gegen die Artikel im Konto.
- **Datei-Import:** `SCParse.analyze` und `entriesFrom` (gleiche Erkennung und `buildEntries` wie `import.js`), höchstens 5000 Zeilen und 5 MB je Datei. Die Datei wird nur im Browser gelesen, ins Konto gehen nur die übernommenen Artikel. Spalten lassen sich nicht von Hand zuordnen (nur Datumsformat, Plattform, Stichwort, „nur positive Beträge“).
- **Export:** `SCKonto.exportCsv`, Spalten wie `CSVExport.journal` der App, Dateiname `sellcheck-artikel-JJJJ-MM-TT.csv`.
- **Fotos ersetzen:** Das alte Foto wird erst gelöscht, wenn `loadByIds` zeigt, dass die Zeile im Konto den neuen Pfad trägt.

## Konto-Reiter (Auftrag 05)

- **Profil:** Vorname, Nachname, Verkaufsart, Umsatzsteuer und Satz wie bei der Registrierung, `PATCH rest/v1/profiles` über `store.saveProfile`. Übersicht, Artikel und Meldegrenze rechnen danach sofort mit den neuen Werten.
- **Passwort:** Regeln live und vor dem Senden (`passwordError` mit Name und E-Mail), danach `PUT auth/v1/user` über `store.changePassword`. Man bleibt angemeldet, das Passwort wird nirgends gespeichert.
- **Abmelden:** mit Rückfrage, dann `anmelden.html`.
- **Konto löschen:** Rückfrage und Eingabe von „löschen“, dann `POST functions/v1/delete-account` über `store.deleteAccount`. Erst nach Erfolg wird die Sitzung geleert und `anmelden.html#geloescht` zeigt „Dein Konto und alle Daten sind gelöscht.“ Scheitert die Funktion, bleibt alles wie es war, mit Meldung.
- **Duplikate beim Import:** `dupKey` vergleicht Namen nur bis 80 Zeichen, damit der Re-Import des eigenen Exports bei langen Namen nichts doppelt anlegt.

## Zugang und Vorschau (Auftrag 06)

- **Eine Stelle:** `SCKonto.access(session, plan)` in `konto-lib.js` entscheidet, wer „Mein SellCheck“ nutzen darf. Heute `allowed: true` für jede gültige Sitzung. Mit dem Kauf im Browser (Phase 3) kommt die Stufe aus `current_plan()` als `plan` dazu; ein Plan `{ locked: true, reason }` zeigt in `mein.js` eine ruhige Sperrseite („Nicht freigeschaltet“) statt der Reiter, es wird nichts geladen. Kein zweiter Weg, nichts in `localStorage`.
- **Vorschau:** Unter der Überschrift steht „Vorschau. Umfang und Zugang können sich noch ändern.“ (ohne Preise, Stufen, Daten oder Zusagen).
- **Auffindbarkeit:** Kein Link in einer Kopfzeile, nur im Fuß („Mein SellCheck“ führt zu `anmelden.html`). `anmelden.html`, `registrieren.html` und `mein.html` haben `noindex` und stehen nicht in `sitemap.xml` (Test in `tests/seo.test.js`).

## Bekannt und offen

- Echte Registrierung und Mails: macht Louis selbst, die Tests laufen nur gegen den Nachbau.
- Profil ändern, Passwort ändern, Konto löschen im Browser: Auftrag 05.
- Kauf im Browser und Freischaltung nach Stufe: Phase 3.
- Datenschutzerklärung für das Konto im Browser: Auftrag 07 (Rechtstext).
- Auf einer statischen Seite schützt die Anmeldung nur die Oberfläche. Echter Schutz der Daten kommt aus den Zugriffsregeln der Datenbank (Zeilensicherheit je Nutzer).

## Seite „Mein SellCheck“ (`site/mein.js`)

- **Laden:** `loadProfile` und `loadAll` beim Öffnen. Bei Rückkehr in den Tab (`visibilitychange`), höchstens alle 60 Sekunden, `loadChanges` und `SCKonto.mergeChanges`. Bei einem Fehler steht die Meldung oben, die zuletzt geladenen Daten bleiben sichtbar. Abgelaufene Sitzung: `anmelden.html#abgelaufen`.
- **Reiter:** `role="tablist"`, Pfeiltasten, Anker `#uebersicht`, `#artikel`, `#meldegrenze`, `#konto`. Jeder andere Anker öffnet die Übersicht (`SCKonto.tabFromHash`).
- **Zahlen:** `SCKonto.yearStats` und `rowProfit` (wie die App), Ampel aus `SCTax.meldeStatus`. Texte wie `OverviewView`, `InventoryView`, `LimitView` und `ArticleFormView` der App.
- **Formular:** `SCKonto.formToRow` (Beträge über `parseNum`, „1.500“ ist 1500), Speichern über `store.save`, Löschen über `store.remove` mit Rückfrage.
- **Fotos:** im Browser über Canvas auf höchstens 1400 px und JPEG mit Qualität 0,75. Neue Fotos werden vor der Zeile hochgeladen, alte erst nach dem Speichern gelöscht. Beim Löschen eines Artikels werden die Fotos erst entfernt, wenn die Zeile im Konto nachgelesen (`loadByIds`) wirklich `deleted_at` hat, wie in `BackupService.swift`. Hat ein anderes Gerät den Artikel neuer geändert, verwirft der Server die Löschung, die Fotos bleiben und die Seite holt den aktuellen Stand. Vorschaubilder laden per `IntersectionObserver` erst, wenn sie sichtbar werden. Blob-Adressen werden beim Schließen freigegeben.
- **Sicherheit:** Nutzerdaten nur über `textContent`, kein `innerHTML`, kein Inline-Skript, kein Inline-Stil (Balken sind `<progress>`). Tests: `tests/mein.test.js`.
- **Im Browser geprüft (320 px):** 50 Artikel, ein Name mit 120 Zeichen ohne Leerzeichen, alle vier Reiter und das Formular ohne waagerechtes Scrollen. Ablauf gegen den Nachbau: Anlegen, Ändern, Löschen, Foto, Änderung vom zweiten Gerät nach Rückkehr in den Tab, Abmelden.
