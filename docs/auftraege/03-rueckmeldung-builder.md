# Rückmeldung Builder zu Auftrag 03 (Seite Mein SellCheck)

Stand 30.10.2026. Diese Datei ersetzt den Eintrag „Rückmeldung Builder“ in `sellcheck-app/docs/auftraege/03-mein-sellcheck-seite.md`. Der Verteiler übernimmt sie dorthin und passt `STATUS.md` an. Danach kann diese Datei gelöscht werden, damit es nur eine Quelle gibt.

## Achtung: alter Eintrag ist überholt

In der lokalen Auftragsdatei steht von der ersten Builder-Sitzung: „angefangen, NICHT fertig, nichts committet“. Das stimmt nicht mehr. Auftrag 03 ist fertig gebaut, getestet und gepusht.

## Wo liegt die Arbeit

- **Repo:** `sellcheck-site`
- **Zweig:** `claude/pensive-ramanujan-h1wnlv` (nicht `mein-sellcheck`). Er enthält alles aus `mein-sellcheck` (Auftrag 01 und 02, Commit `782f7f6`) plus den Commit für Auftrag 03.
- **Commit:** `a3783e2` („Mein SellCheck: Seite mit Übersicht, Artikelliste, Formular mit Fotos und Meldegrenze (Auftrag 03)“)
- **Entwurfs-PR #31** (`mein-sellcheck` nach `main`) ist unverändert. Der Commit ist noch nicht darin.
- **Übernehmen nach `mein-sellcheck`** (ein sauberer Vorlauf ohne Merge-Commit), nur nach Louis' Okay:

```bash
git push origin claude/pensive-ramanujan-h1wnlv:mein-sellcheck
```

## Tests

- `npm test`: 210 von 210 grün (vorher 194, neu 16 in `tests/mein.test.js`). `npm run check` ohne Fehler.
- **CI:** Lauf 120 auf dem Zweig `success` ([Lauf](https://github.com/gym7-fit/sellcheck-site/actions/runs/41048895791)). Die CI startet nur bei Push auf `main`, bei PRs und von Hand. Darum wurde sie von Hand gestartet.
- **Im Browser, 320 px:** 50 Artikel und ein Name mit 120 Zeichen ohne Leerzeichen. Alle vier Reiter und das Formular ohne waagerechtes Scrollen. Konsole ohne Fehler.
- **Ablauf im Browser, einmal gegen den JS-Nachbau (`tests/support/fake-supabase.js`) und einmal von Hand gegen `sellcheck-app/Tests/mock_supabase.py`, gleiches Ergebnis:** Anmelden zeigt die Artikel. Anlegen (Betrag „1.500“ wird 150000 Cent), Ändern und Löschen mit Rückfrage kommen im Konto an. Beim Foto ist der Pfad im Artikel gesetzt. Eine Änderung vom zweiten Gerät (`/mock/remote`) erscheint nach Rückkehr in den Tab. Abmelden leert `sellcheck.session.v1`.
- Nicht gemacht: echte Konten, echte Mails (macht Louis). Kein axe-Lauf im Browser (die Tests in `tests/a11y.test.js` laufen für `mein.html` mit und sind grün).

## Fertig-Kriterien aus dem Auftrag

- [x] Gegen den Nachbau: Anmelden zeigt die Artikel, Anlegen, Ändern, Löschen kommen an, Änderung vom zweiten Gerät erscheint nach Rückkehr in den Tab
- [x] Gleiche Zahlen wie in der App: `tests/mein.test.js`, ein Beispiel für Privat, Kleinunternehmer, Regelbesteuerung 19 % und 7 %, Differenzbesteuerung
- [x] Meldegrenze: 1.999,99 € Gelb, 2.000,00 € Rot, 29 Verkäufe Gelb, 30 Rot, Flohmarkt ohne Ampel (Test)
- [x] Foto: Hochladen auf höchstens 1400 px (Test für die Größe, im Browser mit 4000 × 3000 geprüft), Anzeige über `blob:`, altes Foto wird erst nach erfolgreichem Speichern gelöscht (Test prüft die Reihenfolge im Code)
- [x] Abgelaufene Sitzung führt zu `anmelden.html#abgelaufen` (Code und Test auf feste Ziele)
- [x] Kein `innerHTML` in `mein.js`, kein Inline-Skript, kein Inline-Stil (Test)
- [x] Bei 320 px kein waagerechtes Scrollen, mit 50 Artikeln und 120 Zeichen Name (von Hand im Browser)
- [x] `npm test` grün, CI `test` gleich `pass`

## Abweichungen vom Auftrag

1. **Leerer Zustand ohne „Alles bleibt auf deinem iPhone.“** Der Satz stimmt im Browser nicht. Entscheidung von Louis.
2. **„Check, was wirklich bleibt.“ ist ein Absatz (`p.ov-lead`), keine Überschrift.** Der Test in `tests/auth.test.js` verbietet Schlusspunkte in Überschriften. Der Text ist wörtlich wie in der App.
3. **Texte der leeren Artikelliste:** „Tippe auf Plus“ heißt „Klicke auf „Artikel hinzufügen““, weil es im Browser kein Plus gibt. Bei „Kein Artikel im Lager“ dasselbe.
4. **Neuer Text:** „Dieses Foto konnte nicht gelesen werden.“ (Foto lässt sich nicht öffnen). Bitte prüfen.
5. **Umsatzsteuer** steht wie in der App in den Hinweisen unter Umsatz und Gewinn („brutto“, „nach Einkauf, Kosten und … USt“), nicht als eigene Kennzahl. Der Auftrag sagt „Umsatzsteuer (nur wenn nicht 0)“, das ist damit erfüllt.
6. **Balken sind `<progress>`** statt Inline-Stil.
7. **`IntersectionObserver`** für Vorschaubilder: Der Test `tests/checkliste.test.js` verbietet ihn für Scroll-Animationen, erlaubt ihn aber bei „lazy“ im Code. `mein.js` nutzt ihn nur zum späten Laden und sagt das im Kommentar.
8. **Tests zur Seite** (Reiter mit Rollen, Beschriftungen, ein `h1`) stehen in `tests/mein.test.js`, nicht in `tests/a11y.test.js`. Die allgemeinen Prüfungen dort gelten für `mein.html` automatisch.
9. **Die Kennzahl „Im Lager“** ist kein Knopf (in der App führt sie zum Bestand). Der Reiter „Artikel“ mit Filter „Bestand“ ist der Weg dorthin.
10. **`ratioPct` in `site/konto-lib.js`** rechnet jetzt mit ganzen Zahlen, damit 60 % exakt stimmt (Gleitkomma-Fehler vermieden).
11. `tests/mein.test.js` ist in `package.json` und `.github/workflows/pages.yml` eingetragen.

## Was die erste Builder-Sitzung hinterlassen hatte

Die erste Sitzung (Limit erreicht) hatte `konto-lib.js` (Anzeigelogik), `mein.html` und `mein.css` fertig, aber nichts gepusht. Die Dateien sind aus ihrem Protokoll unverändert neu aufgebaut und mit `mein.js` und den Tests ergänzt worden. `initMine` ist aus `auth-ui.js` entfernt, `tests/auth.test.js` erwartet für `mein.html` jetzt `mein.js`.

## Noch offen (nicht Teil von Auftrag 03)

- Import, Übernahme aus den Gratis-Tools, Export: Auftrag 04
- Profil, Passwort, Konto löschen im Browser: Auftrag 05
- Freischaltung, Fußzeile prüfen: Auftrag 06
- Datenschutz für das Konto im Browser: Auftrag 07
- Louis: echte Registrierung ausprobieren, Okay zum Übernehmen nach `mein-sellcheck`

## Vorschlag für `STATUS.md` (Zeile zu Auftrag 03)

„**Auftrag 03, Seite Mein SellCheck:** gebaut, 210 Tests grün, CI grün, Commit `a3783e2` auf `claude/pensive-ramanujan-h1wnlv` (enthält Auftrag 01 und 02). Wartet auf Prüfung durch Validation (Runde 1). Rückmeldung: `03-rueckmeldung-builder.md` im Repo `sellcheck-site`, Ordner `docs/auftraege/`.“
