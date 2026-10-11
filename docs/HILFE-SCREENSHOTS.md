# Screenshots für die Hilfeseiten

Die Hilfeseiten (`site/hilfe/*.html`) zeigen den Menüweg als Kette („Zahlungen › Berichte › Transaktionsbericht“).
Echte Screenshots der Anbieter-Oberflächen fehlen bewusst: Sie müssen aus einem eingeloggten Konto stammen
und ändern sich bei den Anbietern oft. Wer sie ergänzen will, geht so vor.

## So ergänzt du einen Screenshot

1. Im eigenen Konto den Schritt aufrufen und einen Screenshot machen.
2. **Persönliche Daten unkenntlich machen** (Name, Adresse, Bestellnummern, Beträge, E-Mail, Shop-Name). Auch Browser-Tabs und Lesezeichen prüfen.
3. Als `.png`, `.jpg` oder `.webp` in `site/hilfe/img/` ablegen, **maximal etwa 150 KB**, Breite höchstens 1000 px.
4. Dateiname: `<seite>-<weg>-<schritt>.png`. Beispiel: `ebay-1-3.png` ist Seite eBay, erster Weg, dritter Schritt.
5. `python3 scripts/build-hilfe.py` ausführen. Der Screenshot erscheint automatisch im passenden Schritt, mit Hinweis „Beispielansicht“.
6. `npm test`, committen, pushen.

Hinweis: Ein Screenshot einer fremden Oberfläche ist urheber- und markenrechtlich nicht ohne Weiteres frei. Für eine
öffentliche Seite lieber eigene, stark zugeschnittene Ausschnitte nehmen oder die Anbieter-Erlaubnis prüfen.

## Welche Dateinamen sinnvoll sind

| Datei | Zeigt |
| --- | --- |
| `ebay-1-2.png` | Verkäufer-Cockpit Pro, Tab „Zahlungen“, Menü „Berichte“ |
| `ebay-1-3.png` | Bereich „Download“ mit „Transaktionsbericht“ |
| `etsy-1-3.png` | Shop-Manager, Einstellungen → Optionen, Tab „Daten herunterladen“ |
| `amazon-1-1.png` | Seller Central, Menü „Bestellungen“ → „Bestellberichte“ |
| `amazon-2-1.png` | Seller Central, „Zahlungen“ → „Berichts-Repository“ |
| `paypal-1-3.png` | Aktivitäten mit dem Download-Symbol |
| `vinted-2-1.png` | Einstellungen → Datenschutzeinstellungen → Daten anfordern |
| `kleinanzeigen-3-1.png` | Hilfe-Center, Bereich „Daten und Datenschutz“ |
