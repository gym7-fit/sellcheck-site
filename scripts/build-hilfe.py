#!/usr/bin/env python3
"""Erzeugt die Hilfeseiten site/hilfe/*.html (eine pro Datenquelle plus Übersicht).

Aufruf im Repo-Hauptordner:  python3 scripts/build-hilfe.py

Warum ein Generator: Die acht Seiten haben denselben Aufbau. Texte stehen unten in DATA, das Gerüst
einmal in page(). Es gibt keinen Build-Schritt für die Website selbst; die erzeugten Dateien werden
eingecheckt.

Screenshots: Liegt eine Datei site/hilfe/img/<slug>-<way>-<schritt>.(png|jpg|jpeg|webp) vor, wird sie
im jeweiligen Schritt eingebunden (way = 1 für den ersten Weg, schritt ab 1). Siehe docs/HILFE-SCREENSHOTS.md.
"""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "hilfe"
STAND = "Oktober 2026"
SITE_URL = "https://gym7-fit.github.io/sellcheck-site/"  # wird von scripts/set-site-url.py beim Livegang geändert

CSP = ("default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
       "form-action 'none'; base-uri 'none'; object-src 'none'")

e = html.escape


def S(title, text, path=None, items=None):
    return {"title": title, "text": text, "path": path or [], "items": items or []}


# --------------------------------------------------------------------------------------------
# Inhalte. Quelle der Menüwege steht jeweils unter "sources". Nur Belegtes steht als Anleitung;
# was wir nicht prüfen konnten, steht als ausdrücklicher Hinweis ("Nicht belegt").
# --------------------------------------------------------------------------------------------
DATA = [
    {
        "slug": "ebay", "name": "eBay", "mono": "e", "kind": "export",
        "teaser": "Transaktionsbericht als CSV aus dem Verkäufer-Cockpit Pro.",
        "headline": "eBay: So findest du deinen Transaktionsbericht",
        "lead": "eBay stellt deine Verkäufe, Gebühren und Auszahlungen als CSV-Datei bereit. Sie heißt „Transaktionsbericht“ und liegt im Verkäufer-Cockpit Pro.",
        "facts": [("Datei", "Transaktionsbericht (CSV)"), ("Zeitraum", "Start und Ende frei wählbar"), ("Dauer", "eBay schickt eine E-Mail, wenn er fertig ist")],
        "search": "Transaktionsbericht",
        "ways": [{
            "title": "Transaktionsbericht herunterladen",
            "steps": [
                S("Verkäufer-Cockpit Pro öffnen", "Melde dich bei eBay an und öffne das Verkäufer-Cockpit Pro.", ["eBay-Konto", "Verkäufer-Cockpit Pro"]),
                S("Zu den Berichten wechseln", "Öffne den Tab „Zahlungen“. Wähle im Menü links „Berichte“.", ["Zahlungen", "Berichte"]),
                S("Transaktionsbericht auswählen", "Klicke im Bereich „Download“ auf „Transaktionsbericht“.", ["Berichte", "Download", "Transaktionsbericht"]),
                S("Typ und Zeitraum einstellen", "Wähle den Transaktionstyp und trage bei „Start“ und „Ende“ deinen Zeitraum ein, zum Beispiel den 01.01. bis 31.12. deines Steuerjahres. Klicke dann auf „Bericht erstellen“."),
                S("Datei herunterladen", "Sobald der Bericht bereit ist, bekommst du eine E-Mail von eBay. Lade die CSV-Datei dann herunter."),
            ],
        }],
        "good": [
            "Du kannst die Spalten im Bericht anpassen („Spalteneinstellungen individuell anpassen“). Nimm mindestens Transaktionsdatum, Bestellnummer, Artikel, Beträge und Gebühren mit.",
            "Vor der Kopfzeile stehen oft Zusatzzeilen. Das ist kein Problem, SellCheck findet die Kopfzeile selbst.",
            "Die Zeitangaben können wegen Zeitzonen um ein paar Stunden von deinen eigenen Aufzeichnungen abweichen. Rund um den Jahreswechsel lohnt sich ein Blick.",
            "Einige Berichte gibt es bei eBay erst, wenn du dich für die Zahlungsabwicklung bei eBay angemeldet hast.",
        ],
        "alt": "Für eine reine Bestellliste gibt es bei eBay außerdem die Seite „Alle Bestellungen“ mit „Bericht herunterladen“. Für Gebühren und Auszahlungen ist der Transaktionsbericht die bessere Wahl.",
        "sources": [("eBay-Hilfe: Abgleichen Ihrer eBay-Verkaufstransaktionen", "https://www.ebay.de/help/selling/fees-credits-invoices/reconciling-ebay-sales-transactions?id=4847")],
    },
    {
        "slug": "etsy", "name": "Etsy", "mono": "E", "kind": "export",
        "teaser": "CSV „Daten herunterladen“ im Shop-Manager, nach Monat oder Jahr.",
        "headline": "Etsy: So findest du deine Verkaufsdatei",
        "lead": "Im Shop-Manager kannst du deine Bestellungen als CSV herunterladen, für einen Monat oder für ein ganzes Jahr.",
        "facts": [("Datei", "CSV (Bestellungen oder Bestellpositionen)"), ("Zeitraum", "Monat und Jahr, ohne Monat = ganzes Jahr"), ("Dauer", "direkter Download")],
        "search": "Daten herunterladen",
        "ways": [{
            "title": "Bestellungen als CSV herunterladen",
            "steps": [
                S("Shop-Manager öffnen", "Melde dich auf etsy.com an und öffne den Shop-Manager.", ["Etsy.com", "Shop-Manager"]),
                S("Optionen aufrufen", "Wähle „Einstellungen“ und dann „Optionen“.", ["Einstellungen", "Optionen"]),
                S("Tab „Daten herunterladen“", "Wechsle auf den Tab „Daten herunterladen“.", ["Optionen", "Daten herunterladen"]),
                S("CSV-Typ und Zeitraum wählen", "Wähle bei „Bestellungen“ den CSV-Typ, zum Beispiel „Bestellungen“ (eine Zeile je Bestellung) oder „Bestellpositionen“ (eine Zeile je Artikel). Wähle Jahr und Monat. Für das ganze Jahr lässt du den Monat leer."),
                S("CSV herunterladen", "Klicke auf „CSV herunterladen“."),
            ],
        }],
        "good": [
            "Beträge sind oft englisch formatiert (1,240.00) und das Datum steht als MM/TT/JJJJ. SellCheck erkennt das und zeigt dir die Zuordnung zur Kontrolle.",
            "Welche Gebührenspalten in der Datei stehen, hängt vom gewählten CSV-Typ ab. Prüfe nach dem Import die Spalte „Gebühren“.",
            "Etsy trennt bei Etsy Payments zwischen Verkäufen und Überweisungen. Für SellCheck brauchst du die Verkäufe, nicht die Überweisungen an dein Bankkonto.",
        ],
        "alt": "Alle deine Daten als ZIP (CSV und JSON) bekommst du über die Datenschutz-Einstellungen in den Kontoeinstellungen. Das ist deutlich mehr als nötig.",
        "sources": [
            ("Etsy-Hilfe: Arbeitsblatt mit einer Liste deiner Verkäufe herunterladen", "https://help.etsy.com/hc/de/articles/360000343328-Arbeitsblatt-mit-einer-Liste-deiner-Verk%C3%A4ufe-herunterladen"),
            ("Etsy-Hilfe: Wie kann ich meine Etsy-Daten herunterladen?", "https://help.etsy.com/hc/de/articles/360035753053-Wie-kann-ich-meine-Etsy-Daten-herunterladen"),
        ],
    },
    {
        "slug": "amazon", "name": "Amazon", "mono": "a", "kind": "export",
        "teaser": "Bestellbericht oder Zahlungsbericht aus Seller Central.",
        "headline": "Amazon: So findest du deine Berichte in Seller Central",
        "lead": "Als Verkäufer bei Amazon gibt es zwei brauchbare Berichte: den Bestellbericht (Textdatei) und den Zahlungsbericht (CSV). Du brauchst ein Verkäuferkonto in Seller Central.",
        "facts": [("Datei", "Bestellbericht (.txt mit Tabulatoren) oder Zahlungsbericht (CSV)"), ("Zeitraum", "Bestellbericht: letzte Tage; Zahlungen: Monat oder freier Zeitraum"), ("Dauer", "bis zu 45 Minuten bzw. bis zu 3 Stunden")],
        "search": "Berichts-Repository",
        "ways": [
            {"title": "Weg 1: Bestellbericht", "steps": [
                S("Bestellberichte öffnen", "Öffne in Seller Central im Menü „Bestellungen“ den Punkt „Bestellberichte“.", ["Seller Central", "Bestellungen", "Bestellberichte"]),
                S("Neue Bestellungen wählen", "Wähle die Option „Neue Bestellungen“.", ["Bestellberichte", "Neue Bestellungen"]),
                S("Zeitraum in Tagen festlegen", "Wähle im Bereich „Anfordern eines Bestellberichts“ die Anzahl der Tage, die der Bericht abdecken soll. Klicke dann auf „Bericht anfordern“."),
                S("Bericht herunterladen", "Der Bericht erscheint nach kurzer Zeit im Bereich „Berichtsstatus prüfen und herunterladen“. Das dauert bis zu 45 Minuten. Lade die Textdatei herunter."),
            ]},
            {"title": "Weg 2: Zahlungsbericht (CSV)", "steps": [
                S("Berichts-Repository öffnen", "Wähle im Menü „Zahlungen“ den Punkt „Berichts-Repository“.", ["Seller Central", "Zahlungen", "Berichts-Repository"]),
                S("Berichtstyp wählen", "Wähle bei mehreren Kontotypen ggf. „Alle“. Wähle als Berichtstyp den „Umsatzsteuer-Transaktionsbericht (CSV)“. Er enthält eine detaillierte Transaktionsliste."),
                S("Zeitraum festlegen", "Wähle entweder einen Monat oder einen „Benutzerdefinierten Datumsbereich“ mit Start- und Enddatum. Klicke auf „Bericht anfordern“."),
                S("Bericht herunterladen", "Es kann bis zu drei Stunden dauern, bis der Bericht in der Liste erscheint. Schau später noch einmal nach und lade die Datei herunter."),
            ]},
        ],
        "good": [
            "Der Bestellbericht zeigt nur Bestellungen, die du selbst versendest. Bei „Versand durch Amazon“ (FBA) brauchst du den Bericht „Alle Bestellungen“.",
            "Nach einem älteren Amazon-Tipp gibt es den Bestellbericht nur im professionellen Verkaufsplan. Findest du ihn nicht, nimm Weg 2.",
            "Zahlungsberichte richten sich nach dem Buchungsdatum, nicht nach dem Bestell- oder Versanddatum. Am Jahreswechsel kann ein Verkauf deshalb im anderen Jahr stehen.",
            "Wähle das Enddatum möglichst so, dass es nicht in einen noch offenen Abrechnungszeitraum fällt.",
            "Menünamen können sich je nach Marktplatz und Kontotyp unterscheiden.",
        ],
        "alt": "Unter „Zahlungen“ gibt es außerdem den Tab „Alle Abrechnungen“ mit den täglich erzeugten Abrechnungsberichten zum Herunterladen.",
        "sources": [
            ("Amazon Seller-Forum (Amazon): Quick Tip Berichte nach Zeitraum", "https://sellercentral.amazon.de/seller-forums/discussions/t/298e53f5-be61-4a5e-9900-6f5e34c8e03c"),
            ("Amazon Seller-Forum (Amazon): Quick Tip Bestellberichte", "https://sellercentral.amazon.de/seller-forums/discussions/t/e0afe45c-5f88-4c53-a67f-7875c3325b5f"),
        ],
    },
    {
        "slug": "paypal", "name": "PayPal", "mono": "P", "kind": "export",
        "teaser": "Aktivitätsbericht als CSV, bis zu 12 Monate je Anfrage.",
        "headline": "PayPal: So lädst du deinen Aktivitätsbericht herunter",
        "lead": "Viele Verkäufe auf Vinted und Kleinanzeigen laufen über PayPal. Der Aktivitätsbericht listet sie mit Brutto, Gebühr und Netto auf.",
        "facts": [("Datei", "Aktivitätsbericht (CSV)"), ("Zeitraum", "bis zu 12 Monate je Anfrage, bis zu 7 Jahre zurück"), ("Dauer", "kleine Berichte sofort, große bis zu 5 Werktage")],
        "search": "Berichte herunterladen",
        "ways": [{
            "title": "Aktivitätsbericht als CSV herunterladen",
            "steps": [
                S("Am Computer anmelden", "Melde dich auf paypal.com an. Am Computer geht es am einfachsten."),
                S("Aktivitäten öffnen", "Öffne oben den Bereich „Aktivitäten“.", ["PayPal", "Aktivitäten"]),
                S("Download wählen", "Klicke über der Transaktionsliste auf das Download-Symbol (Pfeil nach unten).", ["Aktivitäten", "Download"]),
                S("Bericht einstellen", "Wähle „Benutzerdefiniert“, den passenden Bericht und das Format „CSV“. Lege den Zeitraum fest (höchstens 12 Monate je Anfrage).", ["Benutzerdefiniert", "Format: CSV"]),
                S("Erstellen und herunterladen", "Klicke auf „Bericht erstellen“. Sobald er fertig ist, erscheint „Herunterladen“. Große Berichte können länger dauern, du bekommst dann eine E-Mail."),
            ],
        }],
        "good": [
            "Ein Steuerjahr passt in eine Anfrage. Wenn du mehrere Jahre brauchst, erstelle je Jahr einen Bericht und importiere sie nacheinander.",
            "Beim Import kannst du ein Stichwort setzen, zum Beispiel „Vinted“ oder „Kleinanzeigen“. Dann zählen nur Zeilen, in denen es vorkommt.",
            "Rückzahlungen und Auszahlungen auf dein Bankkonto werden beim Import übersprungen. SellCheck zeigt dir an, wie viele Zeilen das waren.",
            "Der monatliche Kontoauszug (PDF) ist ein formeller Nachweis, aber kein Import für SellCheck.",
        ],
        "alt": "",
        "sources": [("PayPal-Hilfe: Kontoauszüge und Berichte anzeigen und herunterladen", "https://www.paypal.com/de/cshelp/article/wie-kann-ich-kontoausz%C3%BCge-und-berichte-anzeigen-und-herunterladen-help145")],
    },
    {
        "slug": "bank", "name": "Online-Banking", "mono": "€", "kind": "export",
        "teaser": "Kontoumsätze als CSV, gefiltert nach deinem Stichwort.",
        "headline": "Online-Banking: So exportierst du deine Umsätze als CSV",
        "lead": "Wenn Vinted oder Kleinanzeigen auf dein Girokonto auszahlen, stehen die Beträge in deinen Kontoumsätzen. Fast jede Bank bietet einen CSV-Export.",
        "facts": [("Datei", "Umsätze als CSV"), ("Zeitraum", "wähle das ganze Steuerjahr"), ("Dauer", "sofort")],
        "search": "Umsätze exportieren",
        "ways": [{
            "title": "Umsätze exportieren",
            "steps": [
                S("Online-Banking im Browser öffnen", "Melde dich am Computer in deinem Online-Banking an. In vielen Apps fehlt der Export."),
                S("Kontoumsätze öffnen", "Wähle dein Konto und öffne die Umsatzübersicht.", ["Konto", "Umsätze"]),
                S("Zeitraum einstellen", "Stelle das gesamte Steuerjahr ein, zum Beispiel 01.01. bis 31.12. Manche Banken begrenzen den Zeitraum, dann exportierst du in mehreren Teilen."),
                S("Als CSV exportieren", "Suche die Funktion „Export“, „Exportieren“ oder „Download“ und wähle das Format CSV. Nimm nicht PDF, MT940 oder CAMT.", ["Export", "Format: CSV"]),
                S("Datei speichern", "Speichere die Datei auf deinem Gerät. Beim Import in SellCheck trägst du das Stichwort ein, nach dem gefiltert wird."),
            ],
        }],
        "good": [
            "Die Datei enthält alle deine Umsätze. Sie wird nur in deinem Browser gelesen. Übernommen werden nur Zeilen, in denen dein Stichwort steht, zum Beispiel „Vinted|Kleinanzeigen|PayPal“.",
            "Eine Auszahlung ist nicht der Verkaufspreis. Sie kann mehrere Verkäufe bündeln und Gebühren sind schon abgezogen. Den Einkaufspreis ergänzt du später selbst.",
            "Findest du den Export nicht, suche im Hilfebereich deiner Bank nach „Umsätze exportieren“ oder „CSV“.",
        ],
        "alt": "",
        "sources": [],
    },
    {
        "slug": "tabelle", "name": "Eigene Tabelle", "mono": "⊞", "kind": "export",
        "teaser": "Excel, Google Sheets oder Numbers als CSV speichern.",
        "headline": "Eigene Tabelle: So speicherst du sie als CSV",
        "lead": "Führst du deine Verkäufe schon in Excel oder Google Sheets? Dann brauchst du nur eine Kopfzeile und das Format CSV.",
        "facts": [("Datei", "CSV mit Kopfzeile"), ("Spalten", "Datum, Artikel, Plattform, Einkaufspreis, Verkaufspreis, Gebühren"), ("Größe", "bis 5 MB")],
        "search": "",
        "ways": [{
            "title": "Tabelle vorbereiten und als CSV speichern",
            "steps": [
                S("Kopfzeile prüfen", "Die erste Zeile enthält die Spaltennamen. SellCheck erkennt gängige Namen wie „Datum“, „Artikel“, „Plattform“, „Einkaufspreis“, „Verkaufspreis“, „Gebühren“ und „Status“. Andere Namen kannst du beim Import zuordnen."),
                S("Als CSV speichern", "Speichere die Datei im Format CSV. Je nach Programm so:", items=[
                    "Excel: Datei → Speichern unter → Dateityp „CSV UTF-8 (durch Trennzeichen getrennt)“",
                    "Google Sheets: Datei → Herunterladen → „Kommagetrennte Werte (.csv)“",
                    "LibreOffice Calc: Datei → Speichern unter → Dateityp „Text CSV (.csv)“",
                    "Apple Numbers: Ablage → Exportieren nach → „CSV“",
                ]),
                S("In SellCheck laden", "Ziehe die Datei in das Feld „Datei auswählen“. Du kannst die Tabelle auch markieren, kopieren und unter „Oder Tabelle aus der Zwischenablage einfügen“ einsetzen."),
            ],
        }],
        "good": [
            "Excel-Dateien (.xlsx) liest SellCheck nicht. Speichere sie vorher als CSV.",
            "Datum als TT.MM.JJJJ oder JJJJ-MM-TT, Dezimalkomma oder Dezimalpunkt: beides wird erkannt.",
            "Der CSV-Export aus dem SellCheck-Tracker lässt sich wieder importieren, zum Beispiel als Sicherung oder für ein anderes Gerät.",
        ],
        "alt": "",
        "sources": [],
    },
    {
        "slug": "vinted", "name": "Vinted", "mono": "V", "kind": "noexport",
        "teaser": "Kein Verkaufsexport belegt. Auszahlungsverlauf im Geldbeutel und weitere Wege.",
        "headline": "Vinted: So bekommst du deine Verkaufsdaten",
        "lead": "Eine fertige Verkaufsliste zum Herunterladen haben wir bei Vinted nicht gefunden. Im Vinted-Geldbeutel siehst du aber deine Auszahlungen je Jahr, dazu gibt es weitere Wege.",
        "facts": [("Verkaufsexport", "nicht belegt"), ("Übersicht", "Geldbeutel → Verlauf: Auszahlungen je Jahr"), ("Zusätzlich", "Datenkopie nach Art. 15 DSGVO (ZIP)")],
        "search": "Geldbeutel",
        "ways": [
            {"title": "Weg 1: Auszahlungsverlauf im Vinted-Geldbeutel", "steps": [
                S("Geldbeutel öffnen", "Öffne in der Vinted-App oder im Browser deinen Vinted-Geldbeutel (englisch: Vinted Wallet).", ["Vinted", "Geldbeutel"]),
                S("Verlauf und Jahr wählen", "Wähle „Verlauf“ (englisch: History) und dann das Jahr, das du prüfen willst.", ["Geldbeutel", "Verlauf", "Jahr"]),
                S("Auszahlungen ablesen", "Du siehst deine bisherigen und laufenden Auszahlungen mit Betrag, Startdatum, teilweise verdeckten Bankdaten und Ankunftsdatum."),
                S("In SellCheck übernehmen", "Das sind Auszahlungen, keine einzelnen Verkäufe. Trage deine Verkäufe in SellCheck im Schritt 3 unter „Von Hand eintragen“ ein oder importiere den Kontoauszug (Weg 2)."),
            ]},
            {"title": "Weg 2: Auszahlungen über Bank oder PayPal importieren", "steps": [
                S("Auszahlungen finden", "Vinted zahlt dein Guthaben auf dein Bankkonto aus. Suche im Kontoauszug nach „Vinted“. Der genaue Buchungstext kann je nach Bank und Zahlungsweg anders aussehen. Läuft die Auszahlung über PayPal, steht sie im PayPal-Aktivitätsbericht."),
                S("Export besorgen", "Lade den Kontoauszug oder den PayPal-Bericht als CSV herunter. Die Anleitungen dafür:", items=[
                    "Online-Banking: Anleitung öffnen (bank.html)",
                    "PayPal: Anleitung öffnen (paypal.html)",
                ]),
                S("Mit Stichwort importieren", "Setze beim Import das Stichwort „Vinted“. Den Einkaufspreis ergänzt du danach im Schritt „Angaben vervollständigen“."),
            ]},
            {"title": "Weg 3: Datenkopie bei Vinted anfordern", "steps": [
                S("Daten anfordern", "Tippe auf dein Profilsymbol und öffne „Einstellungen“. Wähle „Datenschutzeinstellungen“, dann „Kontodaten verwalten“ und „Daten anfordern“.", ["Profil", "Einstellungen", "Datenschutzeinstellungen", "Kontodaten verwalten", "Daten anfordern"]),
                S("Per E-Mail bestätigen", "Vinted schickt dir eine E-Mail mit einem Bestätigungslink. Er ist 24 Stunden gültig. Sei dabei in deinem Vinted-Konto angemeldet."),
                S("Warten und herunterladen", "Die Aufbereitung dauert meist wenige Minuten, kann aber bis zu 30 Tage dauern. Danach kommt eine E-Mail mit einem Button. Melde dich an und tippe auf „Download“."),
            ]},
            {"title": "Weg 4: Von Hand eintragen", "steps": [
                S("Verkäufe selbst eintragen", "Bei wenigen Verkäufen ist das am schnellsten. Wechsle in SellCheck im Schritt 3 auf „Von Hand eintragen“."),
            ]},
        ],
        "good": [
            "Der Verlauf zeigt Auszahlungen, nicht jede einzelne Verkaufsbuchung. Guthaben, das du direkt für Käufe auf Vinted ausgibst, taucht dort nicht als Auszahlung auf. Die Summe der Auszahlungen kann also unter deinen Verkäufen liegen.",
            "DAC7: Vinted meldet Verkäufer ab 30 Verkäufen oder mehr als 2.000 € je Kalenderjahr an die Steuerbehörden. Auf vinted.de/dac7 kannst du deinen „DAC7-Status“ prüfen. Was dort genau angezeigt wird, haben wir nicht gesehen, dafür braucht es ein Konto.",
            "Die Datenkopie ist ein ZIP-Archiv mit HTML-Dateien, Fotos und PDFs. Das ist keine CSV-Tabelle, SellCheck kann sie nicht direkt einlesen. Ob deine Verkäufe mit Preisen darin stehen, haben wir nicht geprüft.",
            "In der App können die Bezeichnungen leicht anders heißen. Englisch: „Privacy settings“, „Manage account data“, „Request data“, „Wallet“, „History“.",
        ],
        "alt": "",
        "sources": [
            ("Vinted-Hilfe: Einnahmen auszahlen lassen (englisch)", "https://www.vinted.com/help/68-einnahmen-auszahlen-lassen"),
            ("Vinted: Was ist DAC7?", "https://www.vinted.de/dac7"),
            ("Vinted-Hilfe: Wie du eine Kopie deiner Kontodaten bekommst (englisch)", "https://www.vinted.com/help/1374"),
        ],
    },
    {
        "slug": "kleinanzeigen", "name": "Kleinanzeigen", "mono": "K", "kind": "noexport",
        "teaser": "Verkaufsübersicht in der App. Eine Datei zum Herunterladen ist nicht belegt.",
        "headline": "Kleinanzeigen: So bekommst du deine Verkaufsdaten",
        "lead": "Eine Datei zum Herunterladen haben wir bei Kleinanzeigen nicht gefunden. Dafür zeigt dir die App deine abgeschlossenen Verkäufe über das Bezahlsystem in der „Verkaufsübersicht“.",
        "facts": [("Verkaufsexport", "nicht belegt"), ("Übersicht", "Verkaufsübersicht in der App"), ("Enthält", "Liste der Transaktionen und Jahreszusammenfassung")],
        "search": "Verkaufsübersicht",
        "ways": [
            {"title": "Weg 1: Verkaufsübersicht in der App", "steps": [
                S("Profilbereich öffnen", "Öffne die Kleinanzeigen-App und gehe zu „Meins“. Dort steht dein Profil mit deinen Anzeigen.", ["App", "Meins", "Profil"]),
                S("Verkaufsübersicht antippen", "Tippe auf die Kachel „Verkaufsübersicht“ („Deine Einnahmen über unser Bezahlsystem“).", ["Profil", "Verkaufsübersicht"]),
                S("Liste und Jahreszusammenfassung ansehen", "Du siehst die Liste deiner Transaktionen und die jährliche Zusammenfassung deiner erfolgreichen Verkäufe. Für die Meldegrenze zählt die Zahl und die Summe pro Kalenderjahr."),
                S("In SellCheck übernehmen", "Trage die Verkäufe in SellCheck im Schritt 3 unter „Von Hand eintragen“ ein. Für die Meldegrenze kannst du Anzahl und Summe in Schritt 5 bei Kleinanzeigen direkt eintragen."),
            ]},
            {"title": "Weg 2: Auszahlungen über Bank oder PayPal importieren", "steps": [
                S("Auszahlungen finden", "Bei „Sicher bezahlen“ wird das Geld nach Abschluss der Transaktion in der Regel innerhalb von 1 bis 3 Werktagen auf dein hinterlegtes Konto überwiesen. Du findest diese Buchungen im Kontoauszug. Wer PayPal nutzt, findet sie im PayPal-Bericht."),
                S("Export besorgen", "Lade den Kontoauszug oder den PayPal-Bericht als CSV herunter. Die Anleitungen dafür:", items=[
                    "Online-Banking: Anleitung öffnen (bank.html)",
                    "PayPal: Anleitung öffnen (paypal.html)",
                ]),
                S("Mit Stichwort importieren", "Setze beim Import das Stichwort „Kleinanzeigen“. Den Einkaufspreis ergänzt du danach im Schritt „Angaben vervollständigen“."),
            ]},
            {"title": "Weg 3: Datenauskunft anfordern", "steps": [
                S("Hilfe-Center öffnen", "Melde dich bei Kleinanzeigen an und öffne das Hilfe-Center. Gehe zu „Daten und Datenschutz“.", ["Hilfe-Center", "Nutzerkonto", "Daten und Datenschutz"]),
                S("Anfrage einreichen", "Reiche über „Anfrage einreichen“ ein Auskunftsersuchen nach Art. 15 DSGVO ein. Nenne dein Konto und bitte um eine Kopie der gespeicherten Daten, insbesondere deiner Transaktionen."),
                S("Antwort abwarten", "Nach der Datenschutzerklärung können Dateien passwortgeschützt sein. Das Passwort kommt per SMS an die Nummer in deinem Konto. Halte sie aktuell."),
            ]},
        ],
        "good": [
            "Die Verkaufsübersicht gibt es laut Kleinanzeigen in den Apps im Profilbereich, am Computer nicht. Im Web-Konto zeigt „Transaktionen“ die letzten 50 Vorgänge, getrennt nach Einkäufen und Verkäufen.",
            "Gezählt werden nur erfolgreiche Transaktionen über das Bezahlsystem seit dem 1. Januar 2023, je Kalenderjahr. Das sind dieselben Zahlen, die Kleinanzeigen für die Meldung an das Finanzamt (PStTG/DAC7) nutzt.",
            "Bar bezahlte Verkäufe und Abholungen stehen dort nicht. Trage sie in SellCheck von Hand ein. Für deine eigene Steuererklärung zählen sie trotzdem.",
            "Ob die Übersicht einen Export (Teilen, Download) anbietet, haben wir nicht geprüft. Siehst du eine solche Funktion, nutze sie und importiere die Datei.",
        ],
        "alt": "",
        "sources": [
            ("Kleinanzeigen-Hilfe: Informationen zum PStTG (DAC7) mit Hinweis zur Verkaufsübersicht", "https://hilfe.kleinanzeigen.de/hc/de/articles/17167379828252-Informationen-zum-Plattformen-Steuertransparenzgesetz-PStTG-DAC7"),
            ("Kleinanzeigen-Hilfe: Wie erhalte ich als Verkäufer bei „Sicher bezahlen“ mein Geld?", "https://hilfe.kleinanzeigen.de/hc/de/articles/17229725122460-Wie-erhalte-ich-als-Verk%C3%A4ufer-bei-Sicher-bezahlen-mein-Geld"),
            ("Kleinanzeigen-Hilfe: Daten und Datenschutz", "https://hilfe.kleinanzeigen.de/hc/de/sections/17023680193820-Daten-und-Datenschutz"),
        ],
    },
]

BY_SLUG = {d["slug"]: d for d in DATA}


def brand_block():
    src = (SITE / "tools.html").read_text(encoding="utf-8")
    m = re.search(r'<a class="brand" href="index\.html".*?</a>', src, re.S)
    if not m:
        raise SystemExit("Marken-Block in tools.html nicht gefunden")
    return m.group(0).replace('href="index.html"', 'href="../index.html"')


def shot(slug, way, n, alt):
    for ext in ("png", "jpg", "jpeg", "webp"):
        name = f"{slug}-{way}-{n}.{ext}"
        if (OUT / "img" / name).exists():
            return (f'<figure class="help-shot"><img src="img/{e(name)}" alt="{e(alt)}" loading="lazy">'
                    f'<figcaption>Beispielansicht. Bei dir kann es leicht anders aussehen.</figcaption></figure>')
    return ""


def path_chips(path):
    if not path:
        return ""
    return '<p class="help-path" aria-label="Menüweg">' + '<span class="sep" aria-hidden="true">›</span>'.join(
        f'<span class="chip">{e(p)}</span>' for p in path) + "</p>"


def steps_html(d, way_idx, way):
    out = ['<ol class="help-steps">']
    for i, s in enumerate(way["steps"], 1):
        items = ""
        if s["items"]:
            lis = []
            for it in s["items"]:
                m = re.match(r"^(.*)\((\w+)\.html\)$", it)
                if m:  # Verweis auf eine andere Hilfeseite
                    lis.append(f'<li><a href="{m.group(2)}.html">{e(m.group(1).strip())}</a></li>')
                else:
                    lis.append(f"<li>{e(it)}</li>")
            items = "<ul>" + "".join(lis) + "</ul>"
        out.append(
            f'<li class="help-step"><span class="n" aria-hidden="true">{i}</span><div>'
            f'<h3>{e(s["title"])}</h3><p>{e(s["text"])}</p>{path_chips(s["path"])}{items}'
            f'{shot(d["slug"], way_idx, i, "Beispielansicht: " + s["title"])}</div></li>')
    out.append("</ol>")
    return "".join(out)


def page_shell(title, desc, body, slug="", depth_home="../"):
    url = f"{SITE_URL}hilfe/{slug}"
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="{CSP}">
  <meta name="robots" content="noindex, nofollow">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)} | SellCheck</title>
  <meta name="description" content="{e(desc)}">
  <link rel="canonical" href="{url}">
  <link rel="apple-touch-icon" href="../apple-touch-icon.png">
  <meta property="og:site_name" content="SellCheck">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="de_DE">
  <meta property="og:title" content="{e(title)} | SellCheck">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE_URL}social/og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="SellCheck: Check, was wirklich bleibt.">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#0e1116">
  <link rel="icon" href="../favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../style.css">
  <link rel="stylesheet" href="../hilfe.css">
</head>
<body>
<a class="skip" href="#main">Zum Inhalt springen</a>
<header class="site-header on-dark">
  <div class="wrap">
    {brand_block()}
    <nav class="nav" aria-label="Hauptnavigation">
      <a class="hide-sm" href="../index.html">Startseite</a>
      <a class="hide-sm" href="index.html">Hilfe</a>
      <a class="btn small" href="../tools.html">Zu den Tools</a>
    </nav>
  </div>
</header>
{body}
<footer class="on-dark help-footer">
  <div class="wrap">
    <p>SellCheck gibt Orientierung und ist keine Steuer- oder Rechtsberatung. Alles läuft in deinem Browser.</p>
    <p><a href="../index.html">Startseite</a> · <a href="../tools.html">Tools</a> · <a href="../impressum.html">Impressum</a> · <a href="../datenschutz.html">Datenschutz</a> · <a href="../agb.html">Nutzungsbedingungen</a></p>
  </div>
</footer>
</body>
</html>
"""


def platform_page(d):
    many = len(d["ways"]) > 1
    sec = []
    for wi, way in enumerate(d["ways"], 1):
        head = f'<h2>{e(way["title"])}</h2>' if many else '<h2>So geht es</h2>'
        sec.append(f'<section class="help-way">{head}{steps_html(d, wi, way)}</section>')
    facts = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in d["facts"])
    hint = (f'Findest du einen Menüpunkt nicht, suche im Hilfe-Center von {e(d["name"])} nach „{e(d["search"])}“.'
            if d["search"] else "")
    good = "".join(f"<li>{e(g)}</li>" for g in d["good"])
    alt = f'<section class="help-alt"><h2>Alternative</h2><p>{e(d["alt"])}</p></section>' if d["alt"] else ""
    src = ""
    if d["sources"]:
        src = ('<section class="help-sources"><h2>Quellen</h2><ul>' + "".join(
            f'<li><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{e(t)}</a></li>' for t, u in d["sources"]) + "</ul></section>")
    tag = ('<span class="tag ok">Export vorhanden</span>' if d["kind"] == "export"
           else '<span class="tag no">Kein Verkaufsexport belegt</span>')
    body = f"""<main id="main">
<div class="help-hero on-dark">
  <div class="wrap">
    <a class="help-back" href="index.html">← Alle Datenquellen</a>
    <span class="eyebrow">Hilfe · Datei besorgen</span>
    <h1>{e(d["headline"])}</h1>
    <p>{e(d["lead"])}</p>
  </div>
</div>
<div class="wrap help-main">
  <div class="help-top">
    <dl class="help-facts">{facts}</dl>
    <div class="help-tag">{tag}</div>
  </div>
  <p class="help-note">Stand der Beschreibung: {STAND}. Anbieter ändern ihre Oberfläche gelegentlich, Menünamen können deshalb abweichen. {hint}</p>
  {"".join(sec)}
  <section class="help-next">
    <h2>Danach in SellCheck</h2>
    <ol>
      <li>Zurück zu den Tools und im Schritt 3 auf „Datei importieren“.</li>
      <li>Datei in das Feld ziehen. SellCheck zeigt dir, welche Spalten es erkannt hat.</li>
      <li>Zuordnung prüfen und importieren. Fehlende Einkaufspreise ergänzt du im nächsten Schritt.</li>
    </ol>
    <p><a class="btn" href="../tools.html">Zurück zu den Tools</a></p>
  </section>
  <section class="help-good"><h2>Gut zu wissen</h2><ul>{good}</ul></section>
  {alt}
  {src}
</div>
</main>"""
    return page_shell(d["headline"], d["lead"], body, d["slug"] + ".html")


def hub_page():
    cards = []
    for d in DATA:
        tag = "Export vorhanden" if d["kind"] == "export" else "Kein Verkaufsexport belegt"
        cls = "ok" if d["kind"] == "export" else "no"
        cards.append(
            f'<a class="help-card" href="{d["slug"]}.html"><span class="mono" aria-hidden="true">{e(d["mono"])}</span>'
            f'<span><b>{e(d["name"])}</b><span class="t">{e(d["teaser"])}</span>'
            f'<span class="tag {cls}">{tag}</span></span></a>')
    body = f"""<main id="main">
<div class="help-hero on-dark">
  <div class="wrap">
    <span class="eyebrow">Hilfe · Datei besorgen</span>
    <h1>Wo finde ich meine Exportdatei?</h1>
    <p>Wähle deine Plattform. Du bekommst eine Schritt-für-Schritt-Anleitung, wo die Datei liegt und was du danach in SellCheck tust.</p>
  </div>
</div>
<div class="wrap help-main">
  <p class="help-note">Stand der Beschreibungen: {STAND}. Sie stammen aus den Hilfeseiten der Anbieter. Anbieter ändern ihre Oberfläche gelegentlich, Menünamen können deshalb abweichen.</p>
  <div class="help-cards">{"".join(cards)}</div>
  <section class="help-next">
    <h2>Welche Datei ist die richtige?</h2>
    <ul>
      <li><b>Ich verkaufe auf eBay, Etsy oder Amazon:</b> nimm den Export der Plattform. Er enthält Preise und Gebühren.</li>
      <li><b>Ich verkaufe auf Vinted oder Kleinanzeigen:</b> nimm den PayPal-Bericht oder deine Kontoumsätze und setze das Stichwort. Bei Kleinanzeigen zeigt zusätzlich die „Verkaufsübersicht“ in der App deine Verkäufe über das Bezahlsystem.</li>
      <li><b>Ich führe schon eine Tabelle:</b> speichere sie als CSV.</li>
      <li><b>Nur wenige Verkäufe oder Barverkäufe:</b> trage sie in SellCheck von Hand ein.</li>
    </ul>
    <p><a class="btn" href="../tools.html">Zurück zu den Tools</a></p>
  </section>
</div>
</main>"""
    return page_shell("Wo finde ich meine Exportdatei?", "Anleitungen für den Export deiner Verkaufsdaten bei eBay, Etsy, Amazon, PayPal, Vinted, Kleinanzeigen und deiner Bank.", body, "")


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(hub_page(), encoding="utf-8")
    for d in DATA:
        (OUT / f"{d['slug']}.html").write_text(platform_page(d), encoding="utf-8")
    print(f"{len(DATA) + 1} Seiten nach {OUT.relative_to(ROOT)} geschrieben")


if __name__ == "__main__":
    main()
