# DESIGN.md: Weiß, Tinte, Archivo (Redesign Oktober 2026, Stand 24.10.)

Ausgangspunkt war Richtung C „Kontrast“ aus drei Prototypen (`design/richtungen/`). Am 24.10.2026 hat Louis nachgeschärft: andere Schrift, entschärfte Farben, weg vom Baukasten. Die Seite soll nicht nach KI aussehen. Lebende Stilseite: `site/brand.html`. Backup des alten Designs und Rückweg: `docs/REDESIGN.md`.

## Idee

Eine ruhige, helle Seite, die das echte Produkt zeigt. Weiß und Tinte tragen alles, Lime ist ein kleines Signal. Statt gebauter Vorschaukarten stehen echte Bildschirmfotos der Tools mit Beispieldaten auf der Startseite. Inhalte stehen als Text und Listen, nicht als Kartenraster. Auffällig ist nur eine Sache: der große Claim.

## Rhythmus

| Bereich | Hell (Standard) | Dunkel (Gerät) |
| --- | --- | --- |
| Kopf, Hero, Inhalt | Weiß | Tinte |
| Ruhige Abschnitte (Ampel, Film) | Grau `section.tint` | Tinte mit Linie oben |
| Fuß | Tinte | Tinte |

- **Dunkle Fläche nur im Fuß.** `.on-dark` ist nur an `<footer>` erlaubt. Test: `tests/design.test.js`.
- Unterseiten (Tools, Hilfe, Rechtliches, Stilseite) haben einen hellen Kopf.

## Tokens (`site/style.css`, `:root`)

**Marke:**
- Tinte `--ink` #0e1116 (Text auf Lime, Fuß), Lime `--lime` #c8f169, `--lime-hover` #d6f784
- Logo: `--logo-tag`, `--logo-tick`, `--logo-word`. Hell: Beleg Tinte, Haken Lime, „Check“ grün #2a7a18. Dunkel: Beleg Lime, Haken Tinte, „Check“ Lime.

**Flächen und Text (hell):**
- `--bg` #ffffff, `--surface` #ffffff, `--surface-2` #f3f4f6
- `--text` #111418, `--muted` #555a63, `--line` #e1e3e7, `--line-strong` #c3c7ce, `--link` #1e6b3a
- Je ein Satz für hell und dunkel. `.on-dark` setzt sie für den Fuß neu.

**Knopf und Fokus:**
- `--btn-bg` Tinte, im dunklen Modus Lime. `--focus` Tinte, im dunklen Modus Lime.

**Status:**
- Textfarben `--green`, `--yellow`, `--red` mit `-soft` als Fläche
- Balkenfarben `--bar-green`, `--bar-yellow`, `--bar-red`
- Nur für die Ampel und Gewinn/Verlust, immer mit Text.

**Radien:**
- `--radius` 20 (Karte), `--radius-sm` 12 (Bedienelement), `--radius-xs` 8 (klein)
- Kreise mit 50 %, kleine Marken bis 6 px. Nichts anderes.

**Schatten:** fast keine. `--shadow` ist eine Haarlinie, Karten haben nur einen Rahmen.

**Abstände:** `--s1` bis `--s9` = 4, 8, 12, 16, 24, 36, 56, 88, 128 px.

**Bewegung:** `--ease` cubic-bezier(.2, .8, .2, 1), höchstens 300 ms. Keine Einblend- oder Scroll-Effekte.

## Schrift

- **Archivo, variabel:** Gewicht 100 bis 900. Lizenz SIL OFL, selbst gehostet in `site/fonts/archivo.woff2` (35 KB), `font-display: swap`. Vorab geladen auf allen Seiten.
- **Claim im Hero:** `clamp(2.9rem, 6.2vw, 5.2rem)`, Gewicht 800, Laufweite −0,03 em.
- **Überschriften:**
  - h1 `clamp(2.5rem, 6vw, 4.2rem)` / 750
  - h2 `clamp(1.9rem, 3.8vw, 2.8rem)` / 720
  - h3 1,25 rem / 680
  - Ohne Schlusspunkt. Nur der Claim endet mit Punkt.
- **Text:** 17 px, Zeilenhöhe 1,6. Fett 650.
- **Ziffern:** Zahlen und Beträge mit fester Ziffernbreite (`.num`, `output`, Tabellen, Kennzahlen, Preise).
- **Etiketten** in normaler Schreibweise. Keine Versalien, kein Vorspann über Überschriften.

## Bauteile

- **Knopf `.btn`:**
  - Tinte mit weißer Schrift, 48 px hoch, Radius 12. Sekundär mit 2-px-Rahmen.
  - `.btn.signal` in Lime: nur der eine Hauptknopf einer Seite (Startseite: „Meldegrenze prüfen“ und der Abschluss).
  - Klein 44 px, groß 56 px. Gesperrt grau, nicht durchscheinend. Nie als Pille, nie mit Pfeil.
- **Feld:** 48 px, 2-px-Rahmen, Fokus mit Tinte-Rahmen und Lime-Schein. Fehler darunter mit Zeichen (`.field-error`, `fielderr.js`).
- **Karte `.card`:** nur wo eine Fläche etwas bedeutet (Ampel-Demo, Schritte im Ablauf). Weiß, 1-px-Linie, Radius 20, kein Schatten.
- **Bildschirmfoto `.shot`:** echtes Foto der Tools mit Beispieldaten, WebP unter 150 KB, helle und dunkle Variante über `<picture>`, Maße im `<img>`, Bildunterschrift nennt Beispieldaten. Aufnahme mit den Skripten aus der Prüfrunde (gstack-Browser, doppelte Auflösung).
- **Liste `.tool-list` / `.prose`:** Werkzeuge und Erklärungen als Text mit feinen Linien statt Karten und Symbolen.
- **Ampel `.ampel`:** Fläche in Status-Soft, Titel in Statusfarbe, Satz darunter. Balken `.meter`, `.demo-meter` mit den Balkenfarben.
- **Schritte im Ablauf:**
  - aktiv mit Textfarbe als Rahmen und Lime-Nummer
  - erledigt mit Tinte-Nummer
  - gesperrt als ruhige gestrichelte Zeile
- **Fortschrittsleiste:** hell, Tinte für erledigt und den Balken, Lime nur für den aktuellen Schritt.
- **Preise:** drei Spalten mit Linie oben statt Kartentürmen. Starter mit kräftiger Linie.
- **Etikett `.tag` / `.label` / `.step-status`:** klein, Radius 8, normale Schreibweise.
- **Hilfsklassen statt `style="…"`:** `.mt-0` bis `.mt-4`, `.mb-0`, `.w-s`, `.w-m`, `.w-l`, `.grow`, `.reserve`, `.ico-lg`.

## Verboten (Qualitäts-Checkliste)

- lila Verlauf, Pillenknöpfe
- Emoji als Symbole, KI-Bilder
- Gedankenstriche
- Pfeile an Knöpfen und Links, Mittelpunkte als Trenner (Menüwege in den Hilfeseiten dürfen die Klickfolge zeigen)
- erfundene Zähler, Bewertungen, Kennzahlen
- Scroll- und Cursor-Animationen, Einblend-Effekte
- Textwände
- Vorspann-Etiketten über Überschriften
- Kartenraster mit Symbol-Kacheln, gebaute Vorschaukarten statt echter Bildschirmfotos
- große dunkle Flächen mitten in der Seite
- einseitig dicke Farbränder an Karten
- einzelne eingefärbte Wörter in Überschriften

## Prüfen

- `npm test`: 169 Tests, darunter `design.test.js` und `landing.test.js`:
  - keine Inline-Styles, nur Radius-Tokens
  - Archivo lokal und unter 100 KB
  - keine Versalien und kein Vorspann
  - weißer Grund, dunkel nur der Fuß, Tinte als normaler Knopf
  - keine Pfeile, keine Mittelpunkte
  - echte Bildschirmfotos mit Maßen, Alternativtext und dunkler Variante
  - Überschriften ohne Schlusspunkt
  - feste Ziffernbreite
- **axe** hell und dunkel, Breiten 320 bis 1440 ohne Überlauf, Tippflächen ab 44 px.
- `impeccable detect site`: 0 Befunde. Begründete Ausnahmen stehen in `.impeccable/config.json`.
