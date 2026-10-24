# DESIGN.md: Richtung C „Kontrast“ (Redesign Oktober 2026)

Gewählt von Louis am 24.10.2026 aus drei Prototypen (`design/richtungen/`). Lebende Stilseite: `site/brand.html`. Backup des alten Designs und Rückweg: `docs/REDESIGN.md`.

## Idee

Dunkel zuerst, sehr große Schrift, Lime als einziges Signal. Die Seite wirkt wie eine Marke, nicht wie ein Baukasten. Der dunkle Rahmen trägt die Aufmerksamkeit: Hero, Plattform-Karten, Prüf-Ampel. Lesen und Entscheiden passiert auf Papier.

## Rhythmus

| Bereich | Hell (Standard) | Dunkel (Gerät) |
| --- | --- | --- |
| Kopf, Hero, Plattformen, Ampel | Tinte | Tinte |
| Inhalt (Problem, Film, Werkzeuge, Schritte, Angebot, Vertrauen, FAQ) | Papier, im Wechsel mit `section.tint` | Tinte |
| Abschluss, Fuß | Tinte | Tinte |

- **Keine dunklen Inseln mitten im Papierteil.** Ausnahmen sind einzelne Karten mit eigener Rolle:
  - Starter-Karte (Hervorhebung)
  - Werkzeug-Vorschauen (Produkt)
  - „Danach in SellCheck“ (nächster Schritt)
  - Abschluss des Ablaufs
- Test: `tests/design.test.js`.

## Tokens (`site/style.css`, `:root`)

**Marke:**
- `--ink` #0e1116, `--ink-2` #171b22, `--ink-3` #222832
- `--lime` #c8f169, `--lime-hover` #d6f784
- `--paper` #f6f4ee

**Flächen und Text:**
- `--bg`, `--surface`, `--surface-2`, `--text`, `--muted`, `--line`, `--line-strong`, `--link`
- Je ein Satz für hell und dunkel.
- `.on-dark` setzt sie für immer dunkle Bereiche neu, auch im hellen Modus.

**Status:**
- Textfarben `--green`, `--yellow`, `--red` mit `-soft` als Fläche
- Balkenfarben `--bar-green`, `--bar-yellow`, `--bar-red`
- Nur für die Ampel und Gewinn/Verlust, immer mit Text.

**Radien:**
- `--radius` 20 (Karte), `--radius-sm` 12 (Bedienelement), `--radius-xs` 8 (klein)
- Kreise mit 50 %, kleine Marken bis 6 px. Nichts anderes.

**Abstände:** `--s1` bis `--s9` = 4, 8, 12, 16, 24, 36, 56, 88, 128 px.

**Bewegung:** `--ease` cubic-bezier(.2, .8, .2, 1), höchstens 300 ms.

## Schrift

- **Bricolage Grotesque, variabel:** Gewicht 200 bis 800 und optische Größe. Lizenz SIL OFL, selbst gehostet in `site/fonts/` (77 KB), `font-display: swap`. Vorab geladen auf Startseite, Tools, Hilfe und Rechtsseiten.
- **Display:** Hero `clamp(3rem, 9vw, 6rem)`, Gewicht 800, Laufweite −0,03 em, Zeilenhöhe 0,96.
- **Überschriften:**
  - h1 `clamp(2.5rem, 6vw, 4.4rem)`
  - h2 `clamp(2rem, 4.4vw, 3.3rem)`, Gewicht 780
  - h3 1,3 rem / 720
- **Text:** 17 px, Zeilenhöhe 1,6. Fett 680.
- **Ziffern:** Zahlen und Beträge mit fester Ziffernbreite (`.num`, `output`, Tabellen, Kennzahlen, Preise).
- **Etiketten** in normaler Schreibweise. Keine Versalien, kein Vorspann über Überschriften.

## Bauteile

- **Knopf `.btn`:**
  - Lime, 48 px hoch, Radius 12. Sekundär mit 2-px-Rahmen.
  - Klein 44 px, groß 56 px.
  - Gesperrt grau, nicht durchscheinend. Nie als Pille.
- **Feld:** 48 px, 2-px-Rahmen, Fokus mit Lime-Ring. Fehler darunter mit Zeichen (`.field-error`, `fielderr.js`).
- **Karte `.card`:** Fläche, 1-px-Linie, Radius 20, weicher Schatten. Symbole stehen neben der Überschrift (`.card-head`), nie als Kachel darüber.
- **Ampel `.ampel`:** Fläche in Status-Soft, Titel in Statusfarbe, Satz darunter. Balken `.meter`, `.bar`, `.demo-meter` mit den Balkenfarben.
- **Schritte im Ablauf:**
  - aktiv mit Textfarbe als Rahmen
  - erledigt mit Lime-Nummer
  - gesperrt als ruhige gestrichelte Zeile
- **Fortschrittsleiste:** dunkel, Lime für aktuell und erledigt.
- **Etikett `.tag` / `.label` / `.step-status`:** klein, Radius 8, normale Schreibweise.
- **Hilfsklassen statt `style="…"`:** `.mt-0` bis `.mt-4`, `.mb-0`, `.w-s`, `.w-m`, `.w-l`, `.grow`, `.reserve`, `.ico-lg`.

## Verboten (Qualitäts-Checkliste)

- lila Verlauf, Pillenknöpfe
- Emoji als Symbole, KI-Bilder
- Gedankenstriche
- erfundene Zähler, Bewertungen, Kennzahlen
- Scroll- und Cursor-Animationen
- Textwände
- Vorspann-Etiketten über Überschriften
- Symbol-Kacheln über Überschriften
- einseitig dicke Farbränder an Karten
- einzelne eingefärbte Wörter in Überschriften

## Prüfen

- `npm test`: 166 Tests, darunter `design.test.js`:
  - keine Inline-Styles
  - nur Radius-Tokens
  - Schrift lokal und unter 100 KB
  - keine Versalien und kein Vorspann
  - Rhythmus der Startseite
  - feste Ziffernbreite
- **axe** hell und dunkel, Breiten 320 bis 1440 ohne Überlauf, Tippflächen ab 44 px.
- `impeccable detect site`: 0 Befunde. Begründete Ausnahmen stehen in `.impeccable/config.json`.
