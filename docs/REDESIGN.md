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

Entscheidung von Louis: _offen_
