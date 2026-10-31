# SellCheck (Arbeitstitel)

Überblick, Meldegrenze und Steuer-Export für Verkäufer auf Vinted, Kleinanzeigen, eBay, Etsy, Amazon und mehr. Eine statische Website: Alles läuft im Browser, es gibt kein eigenes Backend. Anmeldung über Supabase Auth (sobald konfiguriert) oder Demo-Modus. Eingaben bleiben im lokalen Speicher des Geräts.

> **Status: Entwurf vor dem Livegang.** Name ist ein Platzhalter, Impressum und Datenschutz sind Entwürfe, das Wartelisten-Formular ist im Demo-Modus, die Seiten sind per `noindex` und `robots.txt` für Suchmaschinen gesperrt. Keine Steuer- oder Rechtsberatung.

## Ansehen

Lokal (Python 3 reicht, keine Installation):

```bash
npm start            # oder: python3 -m http.server 8000 --directory site
# dann http://localhost:8000 öffnen
```

Online: nach dem ersten Push über GitHub Pages (siehe unten).

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `site/` | Die Website (wird 1:1 veröffentlicht): `index.html`, `tools.html`, `report.html`, Rechtstexte, Skripte, Styles |
| `site/tax-lib.js`, `site/parse-lib.js`, `site/wizard-lib.js` | Reine Logik (Steuerberechnung, Datei-Import, Freischalt-Regeln des Ablaufs), ohne DOM und getestet |
| `site/hilfe/`, `site/hilfe.css`, `scripts/build-hilfe.py` | Hilfeseiten „Wo finde ich meine Exportdatei?“ je Datenquelle. Texte stehen im Skript, `python3 scripts/build-hilfe.py` erzeugt die Seiten neu |
| `site/wizard.js`, `site/wizard.css` | Oberfläche des geführten Ablaufs auf `tools.html` (sechs Schritte, dann Überprüfungsseite) |
| `tests/` | Automatische Tests (`node --test`) |
| `docs/STEUER-EXPORT.md` | Recherche und Entscheidungen zum Steuer-Export |
| `docs/LIVEGANG.md` | Checkliste vor dem Livegang |
| `docs/EMAIL-ZUGANG.md` | Freischaltung per E-Mail-Adresse, Endpunkte, Livegang-Punkte |
| `docs/ACCOUNTS.md` | Konto im Browser (Anmelden, Registrieren, Mein SellCheck): Dateien, Verhalten, Einrichtung |
| `.github/workflows/pages.yml` | Tests und Veröffentlichung über GitHub Pages |

## Tests

```bash
npm test      # Import-Parser, Steuerlogik, Anmeldung, Schritt-Regeln, Hilfeseiten
npm run check # Syntaxprüfung aller Skripte
```

## Veröffentlichen mit GitHub Pages

1. Repository auf GitHub anlegen und `main` pushen.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions** wählen.
3. Der Workflow testet und veröffentlicht `site/`. Die Adresse steht danach unter Settings → Pages und lautet `https://<konto>.github.io/<repo>/`.

Hinweise:

- **Gemeinsame Origin:** Unter `<konto>.github.io` teilen sich alle Projekte eines Kontos denselben Browser-Speicher. Das ist für die Vorab-Ansicht in Ordnung, für den Livegang sollte SellCheck auf eine eigene Domain oder in ein eigenes Konto (siehe docs/LIVEGANG.md).
- GitHub Pages ist für **öffentliche** Repositories kostenlos. Private Repositories brauchen einen bezahlten Tarif.
- GitHub Pages kann keine eigenen HTTP-Header setzen. Die Content-Security-Policy steht deshalb zusätzlich als Meta-Tag in jeder Seite. Der Schutz gegen Einbettung in fremde Seiten (`frame-ancestors`) funktioniert so nicht. Dafür bräuchte es einen Host mit Header-Support (siehe `site/_headers`, z. B. Cloudflare Pages oder Netlify).
- Alle Links sind relativ, die Seiten laufen deshalb auch unter dem Unterpfad `/<repo>/`.

## Vor dem Livegang

Siehe [docs/LIVEGANG.md](docs/LIVEGANG.md). Kurzfassung: Marke und Domain prüfen, Impressum und Datenschutz ausfüllen und prüfen lassen, E-Mail-Dienst für die Warteliste anschließen, `noindex`-Tags und `site/robots.txt` entfernen, Steuer-Export von einem Steuerberater prüfen lassen.

## Datenschutz im Repository

Das Repository enthält **keine** Geschäftsunterlagen und keine personenbezogenen Daten. Beispieldaten in den Tests (`SCParse.SAMPLES` in `site/parse-lib.js`) sind frei erfunden und in der Oberfläche nicht sichtbar. Es gibt keine Abhängigkeiten von Fremdservern (keine CDNs, keine Schriften, kein Tracking).

## Lizenz

Noch nicht festgelegt. Ohne Lizenz gilt „alle Rechte vorbehalten“. Wähle vor einer Veröffentlichung bewusst eine Lizenz (z. B. MIT, wenn der Code offen sein soll).
