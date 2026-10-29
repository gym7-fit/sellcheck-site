# Redesign der Webseite (ab 24.10.2026)

Plan: `~/.claude/plans/prancy-painting-curry.md`. Arbeit nur auf dem Zweig `redesign`. Die Vorabansicht zeigt bis zum Livegang weiter das alte Design.

## Backup des alten Designs

| Was | Wo |
| --- | --- |
| Git-Tag (unveränderbar, auch auf GitHub) | `design-alt-2026-10-23` auf Commit `b173627` |
| ZIP des ganzen Repos an diesem Stand | `VintCheck/Backups/sellcheck-site-design-alt-2026-10-23.zip` (28 MB, lokal) |
| Vorher-Galerie: 21 Ansichten × 3 Breiten (375, 768, 1280) × hell/dunkel | `VintCheck/Backups/design-alt-2026-10-23-bilder/` (126 Bilder, lokal) |

Die Galerie zeigt auch die Tools mit Beispieldaten, den Ergebnis-Bildschirm und den Report. Ganze Seiten sind auf höchstens 2.000 Pixel Höhe verkleinert.

## Zurück zum alten Design

**Vor dem Livegang:** nichts zu tun. `main` und die Vorabansicht haben das alte Design.

**Nach dem Livegang:** Das Redesign kommt als **ein** Squash-Commit auf `main`. Rückgängig machen in einem PR:

```bash
git checkout main && git pull
git checkout -b zurueck-zum-alten-design
git revert --no-edit <commit-des-redesign-merges>
git push -u origin zurueck-zum-alten-design
gh pr create --fill
```

Nach grünem Test mergen. Etwa 2 Minuten später zeigt die Vorabansicht wieder das alte Design.

**Notfall ohne Revert:** Den Ordner `site/` aus dem Tag zurückholen. Das nimmt aber auch spätere Text- und Fehlerkorrekturen zurück:

```bash
git checkout design-alt-2026-10-23 -- site/
```

**Alte Fassung nur ansehen, ohne etwas zu ändern:**

```bash
git worktree add ../sellcheck-site-alt design-alt-2026-10-23
python3 -m http.server 8000 --directory ../sellcheck-site-alt/site
```

## Befunde vor dem Redesign (Phase 0)

Geprüft mit:
- `impeccable` (detect, audit)
- `redesign-existing-projects` (Audit-Liste)
- gstack-Browser: Galerie, axe, Überlauf und Tippflächen
- Messung im Code

**Audit-Wert (impeccable): 13 von 20, „Acceptable“.** Die Technik ist solide, das Erscheinungsbild ist uneinheitlich.

| Bereich | Wert | Wichtigster Befund |
| --- | --- | --- |
| Barrierefreiheit | 3 | axe 0 Verstöße. Viele Versal-Etiketten mit Sperrung schwer lesbar. Tool-Etiketten waren bis 10,9 px klein (behoben am 23.10.). |
| Leistung | 3 | Statisch und klein. Video (8,5 MB) lädt erst beim Start. |
| Farben und Modi | 2 | Tokens vorhanden, aber 54 feste Farbwerte in `style.css` und 23 in `style="…"`. Dunkelmodus funktioniert. |
| Responsiv | 3 | Kein waagerechtes Scrollen, Tippflächen seit 23.10. bei 44 px. Hilfeseiten: Beschriftung überlappt den Wert. |
| Einheitlichkeit | 2 | 59 Schriftgrößen, 53 Abstandswerte, 8 Eckradien, 57 Inline-Styles. Systemschrift sieht je Gerät anders aus. Keine Ziffern mit fester Breite (`tabular-nums`). |

**Weitere Muster:**
- **Unruhiger Wechsel von hell und dunkel:** Die Startseite hat 7 dunkle Flächen auf Papier.
- **Kopf der Tools:** sagt „sechs Schritte“, die Leiste zeigt 7.
- **Gesperrte Schritte:** als große graue Blöcke.
- **Gesperrter Knopf:** trüb olivgrün.
- **Überschriften der Hilfeseiten:** zu flache Stufen (Prüfer: `flat-type-hierarchy` auf 8 Seiten).

**Was bleibt, weil es gut ist:**
- klare, geprüfte Texte
- Fehler direkt am Feld
- Sprunglink, Landmarken, Fokus
- keine Fremdanbieter
- Rechenkern mit Tests

## Phase 1: drei Richtungen (Checkpoint 1)

Prototypen in `design/richtungen/`: `index.html` vergleicht alle drei, dazu je eine Seite. Ansehen lokal:

```bash
python3 -m http.server 8771 --directory design/richtungen
```

| Richtung | Idee | Schrift (OFL, selbst gehostet) |
| --- | --- | --- |
| A: Beleg | Kassenbon rechnet im Hero vor, was bleibt. Zackenkante, Lime als Textmarker. | IBM Plex Sans und Plex Mono (Beträge), etwa 74 KB |
| B: Ruhig und präzise | Weißraum, feine Linien, Messskalen mit Marken bei 60 und 100 %. | Hanken Grotesk, etwa 35 KB |
| C: Kontrast | Dunkel zuerst, sehr große Schrift, Plattform-Karten mit großer Zahl. | Bricolage Grotesque, etwa 77 KB |

**Nicht genommen:**
- **Geist:** Der Prüfer stuft Geist als zu oft benutzte KI-Standardschrift ein.
- **Farbvorschläge aus `ui-ux-pro-max`** (Gold, Lila): passen nicht zur Marke. Lila steht auf der Kreuzliste.

Entscheidung von Louis am 24.10.2026: **C „Kontrast“**, dazu Texte und die komplette Aufmachung überarbeiten.

## Phase 2 bis 4: Umsetzung (Zweig `redesign`)

- **Design-System:**
  - `site/style.css`, Regeln in `DESIGN.md`, Produktwahrheit in `PRODUCT.md`
  - Schrift zuerst Bricolage Grotesque, seit 24.10. Archivo (siehe unten)
- **Seiten:** Startseite neu, Tools, 9 Hilfeseiten (Vorlage in `scripts/build-hilfe.py`), Rechtsseiten, Danke, Bestätigt, 404, Markenseite (lebende Stilseite), Report.
- **Texte:**
  - Startseite und Tools-Einleitung überarbeitet.
  - Preise, Stufen, Meldegrenzen-Fakten, Rechtstexte und geprüfte Aussagen sind unverändert.
  - Korrigiert: „Gewinn, Marge und Rendite“ zu „Gewinn und Marge“, denn eine Rendite zeigt das Werkzeug nicht. Die Einleitung der Tools passt jetzt zur Leiste mit 6 Schritten plus „Prüfen“.
- **Prüfungen:**
  - 166 Tests grün, davon neu `tests/design.test.js`
  - axe 0 Verstöße auf allen Seiten, hell und dunkel
  - kein waagerechtes Scrollen bei 320 bis 1440 px und quer
  - Tippflächen ab 44 px (außer Links im Fließtext)
  - `impeccable detect`: 0 Befunde
  - Konsole ohne Fehler
  - Funktionsprobe: Ablauf mit eBay-Datei, Freischaltung, Journal und Report, Ampel bei 1.999,99 € Gelb und bei 2.000 € Rot
- **Gewicht:** Beim ersten Besuch etwa 70 bis 77 KB mehr je Seite, das ist die Schrift. Danach liegt sie im Zwischenspeicher.

### Abschlussprüfung durch den Prüf-Agenten (impeccable-finish-reviewer)

Grundlage: vollständige Fotos in `.impeccable/review/` (lokal, nicht im Repo). Umgesetzt:

1. **Prüf-Ampel wie im Prototyp:** zwei große Anzeigen mit je eigenem Balken, Regler darunter, Warnsymbol am Ampel-Titel.
2. **Dunkelmodus:**
   - keine graublauen Streifen mehr, Abschnitte nur durch eine Linie getrennt
   - Auswahlfelder passend zum Modus (`color-scheme`)
   - Starter-Karte mit Lime-Rahmen
3. **Hilfeseiten:** Schrittnummer auch am Handy neben der Überschrift.
4. **Preiskarten:** gleich hoch, Aktion unten. Der Satz „Was Nichtstun kostet“ steht als Text unter den Karten statt als Kasten in der Karte.
5. **Ausrichtung:**
   - Tools und Hilfe haben eine gemeinsame Kante für Kopf und Inhalt.
   - Film und FAQ der Startseite stehen linksbündig wie alle anderen Abschnitte.
6. **Ergebnis-Bildschirm:**
   - Kennzahlen ohne Kästen
   - Abgabewege mit gezeichneten Symbolen statt Buchstaben, 3 + 2 statt einer verwaisten Kachel
   - Abgabe-Details ohne Karte in der Karte
7. **Überall gleich:**
   - eine Fußzeile auf allen Seiten außer der 404
   - Fortschrittsleiste mit gezeichneten Haken, „Prüfen“ als Ziel mit Fahne statt Nummer 7, größere Beschriftung
8. **Detector-Ausnahmen:** veraltete Ausnahmen entfernt. `impeccable detect` meldet weiterhin 0.

Nicht umgesetzt (Vorschläge für später):
- eigene Video-Bedienleiste (die native ist barrierefrei)
- Zackenkante des Logos als Schmuck auf weiteren Karten
- große Zahlen auch im Kopf der Tools und Hilfeseiten

## Nachschärfung am 24.10.2026: „nicht vibecodet, nicht nach KI“

Louis' Rückmeldung zur Version C: Die Schrift gefällt nicht, und die Seite soll nicht nach KI aussehen. Seine Entscheidungen:

- **Schrift:** Archivo statt Bricolage Grotesque (35 statt 77 KB, OFL). Schriftprobe mit fünf Kandidaten in `design/schriften/`.
- **Farben entschärft:** Weiß statt Creme, Tinte für Text und normale Knöpfe, dunkel nur noch der Fuß. Lime bleibt im Logo, am Hauptknopf (`.btn.signal`) und beim aktuellen Schritt.
- **Weg vom Baukasten:**
  - echte Bildschirmfotos der Tools mit Beispieldaten statt gebauter Vorschaukarten (`site/media/shot-*.webp`, hell und dunkel)
  - Text und Listen statt Kartenraster mit Symbolen
  - „In drei Schritten“ und die Vertrauens-Karten entfallen, ihre Aussagen stehen jetzt im Text (kein Kontozugriff, Grün ist auch ein Ergebnis)
  - Überschriften ohne Schlusspunkt, keine Pfeile an Knöpfen, keine Mittelpunkte als Trenner
  - keine Einblend-Animation im Hero, kaum Schatten

Umgesetzt in `site/style.css`, `site/landing.css`, `site/wizard.css`, `site/hilfe.css`, `site/index.html` (neu geschrieben), den Kopfzeilen aller Seiten, `tools.js`, `wizard.js`, `import.js` und der Hilfe-Vorlage. Fakten, Preise und Rechtstexte sind unverändert. Tests angepasst und ergänzt (169 grün).

**Bewusst gelassen:**
- Menüwege in den Hilfeseiten und im Abgabe-Teil („Datei → Speichern unter“) zeigen die Klickfolge und behalten ihren Pfeil.
- Das Vorschaubild für geteilte Links (`site/social/og-image.*`) bleibt dunkel, es ist ein eigenes Markenbild.

**Bildschirmfotos neu aufnehmen** (zum Beispiel nach Änderungen an den Tools): lokalen Server auf Port 8772 starten, dann die Aufnahme-Skripte aus der Prüfrunde nutzen (Schritt 5 „Meldegrenzen prüfen“ mit Beispieldaten, Schritt 3 mit der eBay-Beispieldatei, je hell und dunkel, doppelte Auflösung, danach als WebP mit Breite 1280 speichern und `width`/`height` in `index.html` anpassen).
