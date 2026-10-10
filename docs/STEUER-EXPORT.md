# Steuer-Export: Recherche und Entscheidungen (Stand 9. Oktober 2026)

Keine Steuer- oder Rechtsberatung. Diese Datei hält fest, **welche Ziele recherchiert wurden, was sie verlangen, was SellCheck liefert und was bewusst fehlt**. Alles, was nur aus einer Quelle stammt oder unsicher ist, ist so markiert.

## 1. Ziele und was dort gebraucht wird

| Ziel | Was verlangt/akzeptiert wird (Recherche) | Was SellCheck liefert | Status |
| --- | --- | --- | --- |
| **Mein ELSTER, Anlage EÜR** | Die Anlage EÜR ist grundsätzlich **elektronisch** zu übermitteln (§ 60 Abs. 4 EStDV). Eingabe direkt im Formular. Einen **CSV-Import für die EÜR habe ich nicht belegt gefunden** (nur ein unbestätigter Forenhinweis). Software überträgt über die **ERiC-Schnittstelle**, die nur zertifizierte Programme nutzen. Papier nur im Härtefall auf Antrag (§ 150 Abs. 8 AO). | Druckbare **Ausfüllhilfe** mit den Beträgen in Reihenfolge und mit den Bezeichnungen der Anlage EÜR, Summen-CSV. | Umgesetzt. Keine Übermittlung (nicht möglich ohne Zertifizierung) |
| **Formlose Gewinnermittlung** (unter 17.500 € Einnahmen) | Ältere Quellen (bis 2014) und manche Ratgeber nennen sie noch. Laut BMF-Schreiben vom 9.10.2017 (nach Recherchequelle) **entfällt sie seit 2017**. | Wird nicht als Ersatz angeboten. Der Report taugt als Anlage/Nachweis. | Unsicher, im Report nicht behauptet |
| **Anlage G** | Der Gewinn aus der Anlage EÜR wird übernommen (Gewerbebetrieb). | Hinweis im Report. | Umgesetzt |
| **Anlage SO** (private Veräußerungsgeschäfte) | § 23 EStG: Frist 1 Jahr, Gegenstände des täglichen Gebrauchs ausgenommen, Freigrenze 1.000 € (Gesetzestext geprüft). | Modus „privat“: Aufstellung mit den Spalten der Anlage SO, Einordnung je Verkauf, CSV. | Umgesetzt |
| **Steuersoftware** (WISO Steuer, smartsteuer, Taxfix) | WISO Steuer: Einnahmen und Ausgaben werden in Felder eingetragen, Übermittlung über die ELSTER-Schnittstelle (Herstellerseite). **Kein CSV-Import für Einnahmen/Ausgaben belegt.** smartsteuer: Anlage S/SO unterstützt (Tabellen 2021/2023), EÜR-Import nicht belegt. Taxfix: nichts gefunden. | Summen zum Abtippen. | Importmöglichkeit unbelegt, nicht behauptet |
| **Steuerberater / DATEV** | DATEV-Buchungsstapel: CSV mit Kopfzeile `EXTF`, Semikolon, Spaltenbeschreibung nach DATEV-Entwicklerportal; benötigt Konten (Kontenrahmen) und Beraternummer. | **Journal-CSV** (eine Zeile je Buchung mit Kategorie, Beleg, USt) und PDF-Report. **DATEV-Format bewusst nicht erzeugt** (siehe 3). | Bewusst ausgelassen |
| **Buchhaltungs-Apps** (Norman, Accountable, Lexware Office, sevDesk) | Importformate habe ich **nicht** belegt gefunden. Üblich: Datum, Beschreibung, Betrag. | Journal-CSV im gängigen Muster (Datum, Beleg, Beschreibung, Betrag brutto/netto, USt). | Nicht gegen konkrete Programme getestet |

## 2. Fachliche Regeln, auf denen die Berechnung beruht

| Regel | Quelle | Prüfstand |
| --- | --- | --- |
| EÜR: Einnahmen im Jahr des **Zuflusses**, Ausgaben im Jahr der **Zahlung** (§ 11 EStG); Wareneinkauf ist im Zahlungsjahr abzugsfähig, auch wenn die Ware unverkauft ist | Fachbeiträge (IWW, Haufe) | Fachliteratur, Gesetz nicht selbst gelesen |
| Kleinunternehmer: Vorjahr bis **25.000 €**, laufendes Jahr bis **100.000 €** | § 19 UStG | Gesetzestext gelesen |
| Private Veräußerungsgeschäfte: Frist **1 Jahr**, Ausnahme Gegenstände des täglichen Gebrauchs, Freigrenze **1.000 €** Gesamtgewinn | § 23 Abs. 1 Satz 1 Nr. 2, Abs. 3 Satz 5 EStG | Gesetzestext gelesen. **Anwendungszeitpunkt der 1.000 € (ab 2024, früher 600 €) ist aus Allgemeinwissen, nicht aus dem Text belegt** |
| Plattformmeldung: befreit nur bei **weniger als 30 Fällen und weniger als 2.000 €** | § 4 Abs. 5 Satz 1 Nr. 4 PStTG | Gesetzestext gelesen |
| Gewerbesteuer-Freibetrag 24.500 € (Einzelunternehmen) | Taxfix (Anbieterangabe) | Nicht geprüft, im Report als Hinweis |
| Zeilennummern der Anlage EÜR | Quellen widersprechen sich (z. B. Kleinunternehmer-Zeile 11 oder 12; „Waren, Roh- und Hilfsstoffe“ Zeile 27 laut Haufe) | **Nicht verwendet.** Das amtliche Formular konnte ich nicht lesen (das gefundene PDF war nur das BMF-Anschreiben) |

## 3. Entscheidungen

- **Keine Zeilennummern.** Ein falscher Wert im Report ist schlimmer als keiner. Der Report nennt die Positionen mit den Bezeichnungen der Anlage EÜR, die du in Mein ELSTER suchen kannst.
- **Kein DATEV-Export.** Das Format verlangt je nach Kontenrahmen die richtigen Konten und eine Beraternummer. Ein Import mit falschen Konten wäre für den Steuerberater mehr Arbeit als das Journal. Wenn ein Steuerberater das Format ausdrücklich wünscht, lässt es sich ergänzen (Spezifikation: DATEV-Entwicklerportal, Format DTVF).
- **Keine Übermittlung an ELSTER.** Das geht nur mit zertifizierter Software über ERiC. Ein Einzelprojekt ohne Zertifizierung darf das nicht anbieten. Der Weg ist Ausfüllhilfe plus manuelle Eingabe oder Steuerberater.
- **Cent-genaue Rechnung** (ganze Zahlen), Umsatzsteuer **je Beleg** gerundet, damit Netto plus USt immer exakt Brutto ergibt.
- **Einkaufsdatum ist ein eigenes Feld**, weil die EÜR nach Zahlung rechnet. Fehlt es, wird der Einkauf im Verkaufsjahr angesetzt und der Report **warnt deutlich**.
- **Zwei Modi:** gewerblich (Anlage EÜR) und privat (Anlage SO). Ob du gewerblich handelst, entscheidet SellCheck nicht.

## 4. Was der Report enthält

1. Kopf: Name und Steuernummer (nur wenn eingegeben), Steuerjahr, Besteuerungsart, Datum.
2. Beträge für die Anlage EÜR (Einnahmen, Waren, sonstige Ausgaben, Gewinn).
3. Datenqualität und Hinweise (fehlende Einkaufsdaten, Bestand, Kleinunternehmergrenze, Gewerbesteuer, Vorsteuer).
4. Aufstellung nach Plattform (mit Meldegrenze) und nach Monat.
5. Journal aller Buchungen mit Belegnummer.
6. Hinweise zur Abgabe, Unterschriftsfelder.

## 5. Bewusst nicht enthalten (mit Steuerberater klären)

- Umsatzsteuer-Voranmeldung und -Erklärung, Vorsteuerabzug aus Einkäufen.
- Anlagevermögen und Abschreibungen (z. B. Kamera, Regale), Arbeitszimmer, Fahrtkosten.
- Entnahmen (private Mitnahme von Ware), Warenverluste, Rücksendungen (bitte den Eintrag bearbeiten oder löschen).
- Zuflussdatum bei Plattform-Guthaben: Als Datum gilt das Verkaufsdatum.
- Gewerbesteuererklärung, Anlage AVEÜR, Anlage S.
- Fremdwährungen (keine Umrechnung).

## 6. Prüfliste für den Steuerberater

- [ ] Ist die Tätigkeit gewerblich? Gewerbeanmeldung vorhanden?
- [ ] Kleinunternehmerregelung oder Regelbesteuerung, Grenzen im Blick?
- [ ] Einkaufsdaten und Belege vollständig? Zuflussdatum bei Jahreswechsel?
- [ ] Anschaffungen über Geringwertigkeitsgrenze? Entnahmen?
- [ ] Krankenversicherung, Gewerbesteuer.

## 7. Quellen

- Anlage EÜR 2025, Waren-Zeile: [Haufe](https://www.haufe.de/id/beitrag/anlage-euer-einnahmen-ueberschuss-rechnung-2025-43-waren-roh-und-hilfsstoffe-zeile27-HI16887129.html)
- Elektronische Übermittlung, Härtefall: [BMF-Anschreiben 29.08.2025 (PDF)](https://www.steuerschroeder.de/blog/wp-content/uploads/2025/09/2025-08-29-anlage-EUER-2025.pdf), [IHK-Anleitung zum Vordruck](https://www.ihk.de/blueprint/servlet/resource/blob/1826006/7476fa5f17ce9ceb321ff10edadae621/anleitungvordruck-data.pdf)
- ELSTER, CSV-Import und ERiC: [ELSTER-Forum](https://forum.elster.de/anwenderforum/forum/elster-webanwendungen/mein-elster/471340-eür-mit-excel), [Norman: ELSTER/ERiC](https://norman.finance/de/hilfe-center/elster-eric)
- Abfluss-/Zuflussprinzip, Wareneinkauf: [IWW](https://www.iww.de/astw/archiv/--4-estg--keine-nachholung-des-betriebsausgabenabzugs-bei-der-euer-f50388), [Haufe](https://www.haufe.de/id/beitrag/anlage-euer-einnahmen-ueberschuss-rechnung-2025-43-waren-roh-und-hilfsstoffe-zeile27-HI16887129.html)
- Gesetze: [§ 23 EStG](https://www.gesetze-im-internet.de/estg/__23.html), [§ 19 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html), [§ 4 PStTG](https://www.gesetze-im-internet.de/psttg/__4.html)
- DATEV-Format: [DATEV Entwicklerportal](https://developer.datev.de/datev/platform/en/dtvf)
- WISO Steuer, EÜR-Ablauf: [Buhl](https://www.buhl.de/steuer/kaufen/euer/)
- Private Verkäufe, Freigrenze (Anbieter): [Taxfix](https://taxfix.de/steuererklaerung-fuer-vinted-verkaeufer/)
