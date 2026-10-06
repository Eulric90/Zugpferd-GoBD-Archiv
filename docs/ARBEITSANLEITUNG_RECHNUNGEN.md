# Arbeitsanleitung für Eingangs- und Ausgangsrechnungen

Die beiden Belegassistenten sind implementiert. Dieselben Abläufe stehen in der
Anwendung unter `Arbeitsanleitung` mit Druckfunktion bereit. Vor dem Livebetrieb
das geschützte Dienstprofil einrichten und die Geräteabnahme durchführen.

PDF24 bleibt das Programm zum Erstellen eurer ZUGFeRD-Rechnungen. Die Archiv-App
übernimmt die unveränderten Dateien, führt die technischen Schritte aus und fragt
nur erforderliche betriebliche Angaben und Bestätigungen ab.

## Eingehende Rechnung behandeln

1. **Original holen:** Rechnung aus dem Provider-Portal herunterladen. Nach dem
   Thunderbird-Wechsel eine ausgewählte E-Mail als EML mit Anhängen speichern
   oder die Original-Rechnungsdatei übernehmen. Nicht in ein neues PDF drucken
   und dieses anstelle des elektronischen Originals verwenden.
2. **Assistent starten:** `Eingangsrechnung übernehmen` anklicken oder Datei auf
   die Oberfläche ziehen und die Richtung wählen. Bei einer Mail mit mehreren Rechnungen die einzelnen
   Belege auswählen; relevante Begleitbelege zuordnen.
3. **Automatische Prüfung abwarten:** Die App liest Rechnungsdaten aus, zeigt
   XML-basierte Angaben, prüft das Format und sucht
   bereits übernommene Dateien/Belege. Die Lieferanten-Rechnungsnummer bleibt erhalten.
4. **Inhalt prüfen:** Stimmen Lieferant, Rechnungsempfänger, Leistung, Datum und
   Beträge mit dem tatsächlichen Geschäftsvorfall überein? Fehlende Registerangaben
   ergänzen. Änderungen an diesen Angaben verändern niemals die Originaldatei.
5. **Prüfstatus wählen:** Eine nachvollziehbar geprüfte Rechnung freigeben oder
   bei Fehlern die sachliche Freigabe offenlassen. Kritische Fehler führen zum Status `offen`. Auch eine fehlerhafte Rechnung
   muss mit Original und offenen Punkten erhalten bleiben. Für eine steuerliche
   Frage gegebenenfalls den Steuerberater hinzuziehen.
6. **Übernehmen:** Zusammenfassung bestätigen. Die App vergibt eine interne Beleg-ID,
   legt das Original am richtigen Ort ab und protokolliert die Angaben und Person.
   Ordner oder Dateinamen müssen nicht von Hand gewählt werden.
7. **A/B sichern:** Beide zugeordneten Sticks anschließen und im Assistenten
   die automatische Sicherung wählen oder anschließend `Sichern auf A und B` starten. Nur bei verifizierter Speicherung auf beiden Sticks ist
   die redundante Sicherung vollständig. Fehlt ein Stick, bleibt die Aufgabe offen.
8. **Klärungen nachführen:** Antwort, Berichtigung, Storno oder weitere relevante
   Unterlagen dem Beleg zuordnen. Zahlung/Buchungsreferenz kann separat ergänzt
   werden; die App übernimmt keine ungeprüfte steuerliche Buchung.

Eine grüne Formatprüfung bedeutet nicht, dass die Rechnung sachlich richtig ist.
Ein Ausdruck ist eine Arbeits-/Übergabekopie, kein Ersatz für die erhaltene XML/PDF.

## Ausgehende Rechnung behandeln

1. **Nummer prüfen:** Vor dem Erstellen den nächsten Nummernstand im Register
   prüfen/reservieren. Euer Schema bleibt Jahreszahl plus vier laufende Stellen;
   führende Nullen und ein vorhandenes Trennzeichen bleiben erhalten.
2. **In PDF24 erstellen:** Rechnung mit dieser Nummer und den tatsächlichen
   Angaben als ZUGFeRD-Datei speichern. Korrekte strukturierte Daten mit erzeugen.
3. **Assistent starten:** `Ausgangsrechnung übernehmen` anklicken oder die fertige
   Datei auf die Oberfläche ziehen und `Ausgang` wählen. Die App liest Nummer, Empfänger und Beträge aus,
   prüft ZUGFeRD und vergleicht die Nummer mit dem Register.
4. **Prüfen und freigeben:** PDF-/XML-Angaben und Geschäftsvorfall kontrollieren.
   Kritische Fehler zuerst klären. Der Assistent ersetzt weder Pflichtangaben
   durch erfundene Werte noch korrigiert er die PDF eigenmächtig.
5. **Finale Fassung übernehmen:** Zusammenfassung bestätigen. Die App übernimmt
   die bytegleiche Datei in das geschützte lokale Archiv und den Registervorgang.
6. **Genau diese Datei versenden:** Den im Ergebnis angezeigten Originalpfad im
   Register öffnen und exakt diese Datei über das Provider-Portal oder Thunderbird senden. Danach diese
   Rechnung nicht mehr in PDF24 überschreiben. Die App sendet selbst keine Mail.
7. **Versand zuordnen:** Datum und Empfänger bestätigen oder die gesendete EML
   dem Vorgang geben. Deren Rechnungsanhang wird gegen die archivierte Datei geprüft.
   Ein gesendeter Maildatensatz ist kein garantierter Zustellnachweis.
8. **A/B sichern:** Original und neue Verwaltungsdaten auf beiden Sticks sichern.
   Noch offene Versand- oder Sicherungsschritte bleiben im Aufgabenbereich sichtbar.

Ist eine Rechnung schon versandt, den ausdrücklich vorgesehenen Weg
die Option `Bereits versandter Altbeleg / Papierbestand` im Assistenten nutzen.
Anschließend das tatsächliche Versanddatum im Register bestätigen. Dieser Weg dokumentiert das tatsächliche
Versanddatum und den heutigen Import; er behauptet keine rückwirkende Archivierung.

## Storno und Korrektur

- Ursprüngliche Rechnung behalten. Eine inhaltlich abweichende Datei ist kein
  erlaubtes Überschreiben der alten Rechnung.
- Storno/Berichtigung im betrieblich richtigen Verfahren erstellen, dann als neuen
   Beleg übernehmen und im Assistenten die ursprüngliche Beleg-ID unter `related_id`
   angeben oder anschließend im Register begründet verknüpfen.
- Grund, Datum und zuständige Person dokumentieren. Die App erzeugt keine
  steuerlich ungeprüfte Storno-Rechnung und löscht keine Historie.
- Nummernlücken und verworfene Reservierungen erklären; alte Nummern nicht
  still neu vergeben. Bei 9999 verlangt die App eine Entscheidung zum Schema.

## Tagesabschluss, Steuerberaterordner und Kontrollen

- Vor dem Feierabend offene Aufgaben durchsehen und bei neuen Daten beide Sticks
  verifiziert sichern. Anschließend über Windows sicher auswerfen; getrennt aufbewahren.
- Monatlich Register, Ausgangsnummern und vorhandene Rechnungsquellen abgleichen.
  Die App kann nicht wissen, welche Rechnung ihr aus dem Portal nie heruntergeladen habt.
- Monatsregister und benötigte Rechnungskopien für den bisherigen Papierordner
  ausgeben. Zusätzlich digitale Originale und Register für die Steuerberatung
  oder Prüfung exportieren können.
- Regelmäßig vollständige Integrität und Wiederherstellung prüfen; Ergebnisse und
  tatsächliche Zuständigkeiten in der Verfahrensdokumentation festhalten.
- Aufbewahrungsfristen mit dem Steuerberater festlegen. Die App löscht weder
  Belege noch Papierordner automatisch.

## Abbruch, Fehler oder fehlender Stick

- Vor einer bestätigten Übernahme kann die Auswahl abgebrochen werden; die
  Quelldatei bleibt unverändert.
- Nach bestätigter Übernahme bleiben Original und protokollierter Vorgang erhalten.
  Offene Prüfung, Versandzuordnung oder Sicherung später fortsetzen.
- Lokale Übernahme und vollständige A/B-Sicherung sind verschiedene Zustände.
  `Lokal übernommen – A/B ausstehend` bedeutet nicht, dass die Sicherung erfolgreich war.
- Keine Original-, Manifest- oder Journaldateien manuell ändern/löschen, um einen
  Fehler zu beseitigen. Fehlermeldung/Prüfbericht erhalten und Ursache klären.
- Eine unklare Eingangsrechnung wird nicht weggeworfen; eine nicht erfolgreiche
  Prüfung wird nicht durch eine pauschale Bestätigung zu einer erfolgreichen Sicherung.

Diese Anleitung unterstützt einen nachvollziehbaren Rechnungsprozess. Die
betrieblichen Prüfungen und Freigaben müssen tatsächlich durchgeführt werden;
die Anwendung allein garantiert keine GoBD-Konformität.
