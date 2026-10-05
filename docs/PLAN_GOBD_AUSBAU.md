# Gesamtplan: GoBD-unterstützender Rechnungs- und Archivierungsprozess

Planungsstand: 05.10.2026. Dieser Plan beschreibt den nächsten vollständigen
Umsetzungsauftrag; er implementiert noch keine neuen Funktionen. Er ist kein
Nachweis einer gesetzlichen Zertifizierung. Für die praktische GoBD-Konformität
müssen Anwendung, tatsächlich umgesetzte Abläufe und betriebliche Kontrollen
zusammenpassen.

## 1. Feststehender Betriebsablauf

- Ein gemeinsamer Windows-11-PC.
- Getrennte persönliche Windows-Benutzerkonten und die einmalige Einrichtung
  mit Administratorrechten sind vom Betreiber bestätigt.
- Der Bruder erstellt Rechnungen; der zweite Nutzer vertritt ihn bei Krankheit.
- Rechnungsstellung in PDF24 als ZUGFeRD, mit Umsatzsteuer; keine Anwendung der
  Kleinunternehmerregelung nach § 19 UStG.
- Eingang und Versand per E-Mail. Derzeit Nutzung/Download über das Provider-Portal;
  Umstieg auf Thunderbird ist geplant.
- Bisherige Ablage ausschließlich in Papierform mit fortlaufenden Rechnungsnummern.
- Ausgangs-Rechnungsnummer: vierstellige Jahreszahl plus vierstellige laufende
  Nummer; ein gegebenenfalls vorhandenes Trennzeichen wird unverändert übernommen.
- Der Steuerberater erhält Ausdrucke im Ordner.
- Ziel: Originale lokal auf dem PC archivieren und auf zwei unterschiedlichen
  USB-Sticks als A/B redundant sichern. Kein verpflichtendes NAS oder Cloud-Dienst.
- Vorhandene Papierordner und Rechnungsdateien bleiben erhalten.

Die wesentlichen technischen Entscheidungen sind damit festgelegt. Angaben für
die Einrichtung: Windows-Edition, tatsächliche Benutzerkonten, Firmen-/Steuerdaten,
eventuelles Nummern-Trennzeichen und letzter vergebener Nummernstand,
Format/Kapazität der Sticks, Beginn des digitalen Betriebs und Umfang des
Altbestands. Diese Werte fragt der Einrichtungsassistent ab; bestehende
Rechnungsnummern werden nicht verändert. Die Windows-Edition wird auch automatisch
erkannt, insbesondere für die Verfügbarkeit optionaler Verschlüsselungsfunktionen.

## 2. Abgrenzung und geprüfte Grundlagen

Die Anwendung wird ein Rechnungsregister und ein kontrolliertes Belegarchiv,
keine vollständige Buchhaltung, Steuerberechnung oder Kassenführung. Bankbelege,
Zahlungszuordnung und andere steuerlich relevante Unterlagen können aufgenommen
und verknüpft werden; daraus wird keine vollständige Finanzbuchführung behauptet.
Welche Aufzeichnungen darüber hinaus erforderlich sind und wer sie führt,
ist mit der Steuerberatung festzulegen.

Geprüfte amtliche Quellen am 05.10.2026:

- BMF, E-Rechnungs-FAQ, Stand März 2026:
  https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html
- § 14b UStG: https://www.gesetze-im-internet.de/ustg_1980/__14b.html
- § 147 AO: https://www.gesetze-im-internet.de/ao_1977/__147.html
- Die BMF-FAQ verweist auf die GoBD vom 28.11.2019, zuletzt geändert am 14.07.2025.

Wichtige Konsequenzen:

1. Ein gültiges ZUGFeRD-Format/Profil muss festgestellt werden. Die BMF-FAQ nennt
   ZUGFeRD ab 2.0.1, ausgenommen MINIMUM und BASIC-WL. Unbekannte Profile werden
   nicht automatisch als gültige E-Rechnung bezeichnet.
2. Bei hybriden E-Rechnungen sind die strukturierten Daten maßgebend. Wir erhalten
   konservativ die komplette ZUGFeRD-PDF samt eingebetteter XML unverändert.
3. Eine Validierung ist sinnvoll zur Fehlervermeidung, aber kein automatischer
   steuerlicher Anerkennungs- oder GoBD-Nachweis.
4. Rechnungen sind nach § 14b UStG grundsätzlich acht Jahre aufzubewahren, beginnend
   mit dem Schluss des Ausstellungsjahres; Verlängerungen und andere Pflichten
   bleiben relevant. § 147 AO unterscheidet u.a. zehn, acht und sechs Jahre.
   Deshalb keine einheitliche Achtjahresfrist für jede Dokumentart.
5. Die BMF-FAQ stellt klar: Allein die Speicherung einer E-Rechnung außerhalb
   eines GoBD-konformen Systems bedeutet umsatzsteuerlich regelmäßig nicht schon
   einen Verstoß gegen § 14b UStG. Umgekehrt bestätigt die bloße Dateispeicherung
   nicht die Ordnungsmäßigkeit des gesamten betrieblichen Prozesses.
6. Es wird kein bestimmtes WORM-Produkt, keine zusätzliche Rechnungssoftware und
   kein qualifizierter Zeitstempel pauschal als gesetzliche Pflicht behauptet.
   Änderungsschutz und Nachvollziehbarkeit müssen wir technisch und organisatorisch
   wirksam gestalten und für euren konkreten Betrieb prüfen lassen.

## 3. Geplanter täglicher Ablauf

### Eingang

1. Rechnung im Provider-Portal herunterladen oder später ausgewählte Thunderbird-
   E-Mail als EML mit Anhängen importieren.
2. Originalbytes sofort sichern, Eingang und Herkunft erfassen, internen Belegcode
   vergeben; Lieferanten-Rechnungsnummer nicht verändern oder neu vergeben.
3. Format prüfen, XML-Daten auslesen, lesbare Darstellung anbieten.
4. Person prüft sachliche Richtigkeit und Zuordnung zum Geschäftsvorfall.
5. Fehlerhafte oder unklare Rechnungen ebenfalls erhalten; Prüfstatus und
   Rückfrage/Korrektur protokollieren. Nie wegen eines Validierungsfehlers verwerfen.
6. Beleg im Register erfassen und in den lokalen geschützten Archivbestand übernehmen.

Relevante geschäftliche Angaben in einer E-Mail sind zusammen mit der Rechnung
aufzubewahren. Eine reine Transportmail ohne eigene relevante Informationen
wird nicht pauschal als gesetzlich aufbewahrungspflichtig eingestuft. Die Anwendung
kann die komplette ausgewählte Mail freiwillig als nachvollziehbare Zuordnung
mit archivieren. Es wird nicht automatisch das gesamte Postfach eingelesen.

### Ausgang

1. Nummernserie/Reservierung im Register prüfen. PDF24 bleibt das Erstellprogramm.
2. Fertige ZUGFeRD-Datei importieren, Nummer und Beträge mit XML abgleichen.
3. Betriebliche Prüfung/Freigabe; danach unveränderte finale Fassung lokal übernehmen.
4. Genau diese Datei über Portal/Thunderbird versenden. Die App versendet selbst
   keine E-Mails und benötigt dafür keine Zugangsdaten.
5. Versanddatum, Empfänger und optional Original der gesendeten E-Mail zuordnen;
   deren Anhang gegen den Hash der finalen Rechnung prüfen.
6. Versandabweichungen oder Versand vor Übernahme als offene Aufgabe anzeigen.
   Mail-Metadaten oder eine gesendete EML sind kein garantierter Zustellnachweis.

Die App kann einen außerhalb der App erfolgten Versand nicht verhindern. Dieser
Schritt gehört verbindlich in den dokumentierten betrieblichen Ablauf.

### Tagesabschluss und Monatsabschluss

- Vorschlag: an jedem Arbeitstag mit neuen/geänderten Verwaltungsdaten A/B sichern,
  Erfolg prüfen, Sticks sicher auswerfen und getrennt aufbewahren.
- Sicherungserfolg erst, wenn beide Medien dieselben erforderlichen Objekte und
  Metadaten verifiziert enthalten. Bei fehlendem Stick bleibt der Status unvollständig.
- Monatlich Register, offene Eingänge, Ausgangsnummern, Stornos und relevante
  Postfachordner/Portalbelege abgleichen; Kontrolle mit Person/Datum protokollieren.
- Ausdrucke und ein Monatsregister für den bisherigen Steuerberaterordner erzeugen;
  zusätzlich digitale Originale, Register und erforderliche Nachweise exportierbar halten.
- Sicherungs-/Prüfrhythmus ist ein betrieblicher Vorschlag, keine allgemein geltende
  gesetzliche Tages- oder Monatsfrist.

## 4. Funktionspaket A: Rechnungsregister und Zuordnung

### Verbindliche Ergänzung: zwei Belegassistenten und Arbeitsanleitung

Die Oberfläche erhält die Hauptaktionen `Eingangsrechnung übernehmen` und
`Ausgangsrechnung übernehmen`. Eine Datei kann ausgewählt oder auf die jeweilige
Aktion gezogen werden. Der ausgewählte Vorgang bestimmt die Richtung; die App
rät nicht anhand von Dateiname oder Absender, ob ein Beleg ein- oder ausgeht.
Zu beiden Abläufen gibt es eine kurze Anleitung in der App, eine druckbare Fassung
und kontextbezogene Hilfe. Der konkrete Ablauf steht ergänzend in
`ARBEITSANLEITUNG_RECHNUNGEN.md` und fließt in die Verfahrensdokumentation ein.

Gemeinsame Schritte:

1. Originaldatei oder ausdrücklich ausgewählte EML wählen. Bei mehreren Anhängen
   die Rechnungen auswählen und Begleitbelege zuordnen; mehrere Rechnungen nicht
   still zu einem Beleg zusammenfassen.
2. Format erkennen, SHA-256 berechnen, eingebettete XML unverändert auslesen,
   technische Prüfung ausführen und Rechnung lesbar zeigen. Größen-/Sicherheitsgrenzen
   gelten auch im Assistenten; Anhänge werden nicht ausgeführt.
3. Erkannte Daten vorbelegen und fehlende Angaben gezielt abfragen. Tatsächlich
   manuell ergänzte Registerdaten als solche dokumentieren; niemals Original-PDF/XML ändern.
4. Sachliche Kontrolle und Geschäftsvorfall-Zuordnung mit Person/Zeitpunkt erfassen.
   Die technische Prüfung ersetzt diese Bestätigung nicht.
5. Vor der Übernahme Zusammenfassung mit Richtung, Jahr, Nummer, Partner, Betrag,
   Prüfstatus, Herkunft und Ablageziel zeigen. Jahr normalerweise aus dem Rechnungsdatum;
   fehlt ein belastbares Datum, eine explizite Entscheidung verlangen.
6. Nach Bestätigung Original, Begleitbelege und Registerereignisse transaktional
   in den geschützten lokalen Bestand übernehmen. Den Ablauf nicht als vollständig
   abgeschlossen markieren, solange notwendige Commit-/Verifikationsschritte fehlen.
7. Bei angeschlossenen A/B-Sticks die verifizierte Sicherung anbieten und auf
   ausdrücklichen Klick durchführen. Ohne beide Sticks bleibt die lokale Übernahme
   möglich, aber `A/B-Sicherung ausstehend` sichtbar; kein falscher Sicherungserfolg.
8. Ergebnis mit verständlicher Zusammenfassung, Beleg-ID, lokalem Status,
   A/B-Status und konkreten noch offenen Aufgaben anzeigen. Beleg wieder öffnen,
   drucken, exportieren oder einen begonnenen Vorgang fortsetzen können.

Eingangsassistent:

- Lieferantennummer übernehmen; nur internen Belegcode selbst vergeben.
- Empfangsdatum und Quelle, sachliche Prüfung sowie optionale Zahlung/Buchungsreferenz
  zuordnen. Bank-/Buchhaltungsintegration ist kein stiller Bestandteil des Assistenten.
- Ungültige oder unklare Eingangsrechnungen mit ihren Originalen erhalten und als
  `Klärung erforderlich` ablegen. Archivierung von Beweisdaten und fachliche
  Freigabe sind unterschiedliche Zustände.
- Rückfrage, später eingegangene Berichtigung und Storno mit dem Ausgangsbeleg
  verknüpfen. Keine steuerliche Freigabe aus einem grünen Formatcheck ableiten.

Ausgangsassistent:

- Bereits in PDF24 eingetragene Nummer prüfen und übernehmen, niemals die PDF
  umnummerieren. Vor Erstellung separat `Nächste Rechnungsnummer` anzeigen/reservieren.
- Abweichung zwischen Datei, Nummernserie und Reservierung als Klärungsfall behandeln.
- Finale Fassung nach betrieblicher Freigabe lokal übernehmen und anschließend
  ausschließlich diese Fassung als Versanddatei bereitstellen. Keine Konvertierung.
- Der eigentliche Versand erfolgt weiter über Portal/Thunderbird. Keine still
  eingeführte Versandfunktion oder Aufforderung, Zugangsdaten in der App zu speichern.
- Danach Versanddatum/Empfänger bestätigen oder die gesendete EML nachreichen;
  Anhang gegen die archivierte Fassung prüfen. Ein noch nicht bestätigter Versand
  erscheint als offene Aufgabe, nicht als bereits erfolgt.
- Für schon versandte Altbelege einen ausdrücklich bezeichneten Importweg anbieten;
  tatsächliches Versanddatum und heutiger Import werden nicht verwechselt.
- Storno/Berichtigung als neuen verknüpften Beleg importieren, ursprüngliche
  Rechnung unverändert erhalten.

Abbruch und Wiederanlauf:

- Vor bestätigter Übernahme entstehen keine abgeschlossenen Belege; Quell-Dateien
  bleiben unberührt. Bei bestätigter Erhaltung einer unklaren Eingangsrechnung
  bleibt diese ein protokollierter offener Vorgang und wird beim Abbruch nicht gelöscht.
- Nach bestätigter Übernahme führen Abbruch, fehlende Sticks oder Fehler zu einem
  sichtbaren fortsetzbaren Vorgang. Bereits übernommene Originale bleiben erhalten.
- Doppelklick, erneuter Import, Benutzerwechsel und Strom-/Prozessabbruch dürfen
  keine doppelte Rechnung, Nummern-Wiedervergabe oder stille Rückabwicklung erzeugen.
- Offene Aufgaben dürfen ausdrücklich als organisatorisch erledigt gekennzeichnet
  werden, aber notwendige technische A/B-Verifikationen nicht dadurch überspringen.

Automatische Ablage:

- Bediener müssen keine Ordner oder Dateinamen manuell konstruieren.
- Lesbare Zuordnung nach `Eingang/<Jahr>/` bzw. `Ausgang/<Jahr>/`; physische geschützte
  Objekte zusätzlich eindeutig über Beleg-ID/Objekt-ID, damit identische Namen nicht kollidieren.
- Der ursprüngliche Dateiname bleibt in Originalkopie bzw. Metadaten erhalten.
  Eigene Registerkorrekturen oder andere Geschäftspartner führen nie zum Überschreiben.
- Register, Original, Ableitungen und Nachweise sind eindeutig verknüpft; Ablage
  und Verwaltungs-Commit werden nach Unterbrechung gemeinsam überprüft.

Erforderliche Felder:

- Interne unveränderliche Beleg-ID, Richtung und Dokumentart.
- Rechnungsnummer, Datum, Leistungsdatum/-zeitraum soweit vorhanden, Geschäftspartner.
- Währung, Netto-/Steuer-/Bruttobeträge, mehrere Steuersätze, Rundungen, Rabatte
  und steuerliche Sonderfälle ohne pauschale Annahme von 19 Prozent.
- Originaldatei, SHA-256, ursprünglicher Dateiname und Herkunft.
- XML-Format/Profil, Validierungsstatus und Version des Validators.
- Empfang/Versand, tatsächlicher Importzeitpunkt, bearbeitende Person/Windows-SID.
- Geschäftsvorfall/Buchungsreferenz, optionale Zahlungsreferenz.
- Status: offen, geprüft, freigegeben, versandt, korrigiert/storniert; lokale Übernahme
  und A/B-Sicherungsstatus ausdrücklich getrennt.

Nummernregeln für diesen Betrieb:

- Schema `JJJJ` + optionales bestehendes Trennzeichen + `NNNN` mit führenden
  Nullen übernehmen; beispielsweise `20260001` oder, nur falls bisher so benutzt,
  `2026-0001`. Keine stillschweigende Wahl eines neuen Formats.
- Ausgangsserie pro Jahr führen. Bestehende Rechnungen und den letzten tatsächlich
  vergebenen Stand übernehmen; nicht pauschal mitten im Jahr wieder bei 0001 beginnen.
- Neue Jahresserie vorschlagen und betrieblich bestätigen lassen; historische
  Nummern, abweichende Nummernjahre und erklärungsbedürftige Sonderfälle erhalten.
- Bei Ausschöpfung der vier Stellen (9999) eine klare Sperre/Entscheidung verlangen,
  statt Überlauf, doppelter Nummer oder stiller Änderung des Schemas.
- Eindeutige Reservierung auch bei Wechsel zwischen Hauptnutzer und Vertretung.
  Ein abgestürzter Vorgang gibt Nummern nicht still wieder frei.
- Eigene Ausgangsnummer nur einmal vergeben; doppelte Nummer mit anderem Inhalt blockieren.
- Reservierungen/Lücken dürfen erklärt werden und bleiben nachvollziehbar. Keine
  automatische Umnummerierung oder Behauptung, dass jede Nummernlücke rechtswidrig ist.
- Eingangsnummern sind nur zusammen mit Aussteller und weiteren Belegmerkmalen
  sinnvoll vergleichbar; zwei Lieferanten dürfen dieselbe Rechnungsnummer verwenden.
- Identisches Original beim erneuten Import erkennen; nicht still zwei Belege erzeugen.
- Datenkorrekturen als neue Ereignisse mit Begründung und vorherigem Wert erfassen.
  Originaldateien und frühere Registerzustände nie rückwirkend ändern.

## 5. Funktionspaket B: E-Rechnungsprüfung und Anzeige

- ZUGFeRD/Factur-X-PDF mit eingebetteter CII-XML sowie XRechnung CII/UBL unterstützen.
- Normale PDF-Rechnungen, Papier-Scans und weitere Belege ebenfalls erhalten, aber
  klar als andere Belegform kennzeichnen. Keine Umwandlung in angebliche Originale.
- Offline-Validierung anhand versionierter XSD-/Schematron-Regeln und erforderlicher
  Profilregeln; Lizenzen und Windows-Packaging aller Komponenten dokumentieren.
- Pflichtangaben, Summen, Währung, Steuercodes und Referenzen nachvollziehbar prüfen.
  Technische Prüfung, sachliche Prüfung und steuerliche Beurteilung getrennt darstellen.
- XML-basierte lesbare Rechnungsansicht neben der PDF-Ansicht. Unterschiede nicht
  durch stilles Ändern einer der Darstellungen "reparieren"; kritische Abweichungen markieren.
- Kein Anspruch auf lückenlosen automatischen semantischen Vergleich beliebiger
  PDF-Layouts; die lesbare Gegenprüfung durch die Person bleibt Teil der Freigabe.
- XML/PDF sicher parsen: externe Entitäten und Netzabrufe sperren, Größen-/Zeitlimits,
  keine Makro-/Skriptausführung oder Ausführung von Mailanhängen.
- Extrahierte XML und Ansichten sind zusätzliche Ableitungen, keine Ersatzoriginale.
- Ungültige/unerwartete Eingangsdokumente erhalten und zur Klärung markieren. Eigene
  Ausgangsfreigabe bei kritischen Fehlern verhindern; bereits versandte fehlerhafte
  Rechnungen als Vorgang mit Korrekturbezug erhalten.

## 6. Funktionspaket C: Korrekturen, Stornos und Vollständigkeit

- Beziehungen zwischen ursprünglicher Rechnung, Storno, Berichtigung und Ersatz erfassen.
- Keine automatisch erstellten Storno-Rechnungen oder steuerliche Umbuchungen;
  PDF24 und betriebliche Freigabe bleiben verantwortlich für das neue Dokument.
- Begründung, Person und Datum eines Status-/Metadatenwechsels protokollieren.
- Vollständigkeitsansicht mit ungeprüften Eingängen, unbegründeten Nummernlücken,
  nicht zugeordneten Dateien, fehlenden Versandzuordnungen und Sicherungsrückständen.
- Vergleich abgeschlossener Perioden anhand nachvollziehbarer Registerstände.
- Keine Vollständigkeit für nicht zugängliche Portal-/Postfachinhalte behaupten;
  tatsächlicher Abgleich mit den vorhandenen Rechnungsquellen bleibt erforderlich.

## 7. Funktionspaket D: Änderungsschutz und Sicherungsarchitektur

### Zielarchitektur

- Arbeits-/Importbereich bleibt von dem lokal übernommenen Archivbestand getrennt.
- Lokaler primärer Archivbestand auf NTFS, mit kontrolliertem Schreibzugriff und
  zwei persönlichen Standardbenutzerkonten. Hauptverantwortlicher und Vertretung
  erhalten nachvollziehbare Rollen; keine bloße frei wählbare Namensanzeige als Identität.
- Geplantes Schutzprofil: eigener Windows-Dienst/dedizierte Schreibidentität,
  eng begrenzte lokale Schnittstelle und NTFS-Berechtigungen. Die normale Oberfläche
  kann neue Objekte/Protokolle anhängen, aber keine übernommenen Originale ersetzen
  oder löschen. Der Dienst stellt keine beliebige Dateischreib- oder Löschschnittstelle bereit.
- Dienstinstallation/Berechtigungseinrichtung erfordert einmalig Windows-
  Administratorrechte und eine konkrete Prüfung auf eurem PC. Im Betrieb arbeitet
  die Oberfläche als Standardbenutzer. Der Installer verändert keine bestehenden
  Benutzerkonten, Datenträger oder Archivordner ohne sichtbare Einrichtungsschritte.
- Die getrennten Benutzerkonten und einmalige Administrator-Einrichtung sind
  bestätigt; dieses Schutzprofil wird für Windows 11 eingeplant. Administrative
  Einrichtungsschritte auf dem tatsächlichen Gerät bleiben sichtbar und angeleitet.
  Bestehende V1-Sicherheitsinvarianten werden dadurch nicht gelockert.
- Bestehende A/B-Identität, unveränderliche Ziele, Flush, SHA-256-Rückleseprüfung,
  hash-verkettete Journale und fehlersichere Kopiertransaktionen bleiben verbindlich.
- Zwei USB-Sticks sind verifizierte Sicherungskopien, keine WORM-Garantie. NTFS ist
  für Windows-Rechte zu bevorzugen, aber kein WORM-Ersatz. Bei exFAT/FAT werden die
  fehlenden Zugriffskontrollen deutlich erklärt; kein automatisches Formatieren.
- Sticks nicht dauerhaft angeschlossen lassen, B getrennt und möglichst außerhalb
  desselben Schadensbereichs aufbewahren. Kapazität/Medienzustand beim Einrichten prüfen.
- Signierte Abschlussstände mit geschützter Schlüsselhaltung und unabhängigen
  Referenzkopien unterstützen das Erkennen von nachträglicher Änderung/Kettenkürzung.
  Ein Schlüssel auf demselben frei zugänglichen Benutzerkonto oder drei gleichzeitig
  veränderbare Kopien sind kein unabhängiger Vertrauensanker.
- Schlüssel-/Konfigurationssicherung und Wiederherstellung müssen Teil des Betriebs
  sein. Schlüssel nicht neben Rechnungen ungeschützt auf den Sticks ablegen.
- Verschlüsselung für PC/Sticks empfehlen und vorhandene Windows-Funktionen erkennen;
  Verfügbarkeit (z.B. BitLocker) hängt von der Windows-Edition ab. Keine automatische
  Aktivierung ohne Wiederherstellungsschlüssel und dokumentiertes Vorgehen.

### Praktische Grenzen

Administrative Eingriffe und Änderungen auf einem anderen Rechner lassen sich
bei normalen USB-Sticks nicht grundsätzlich verhindern. Der Schutz muss daher
auch organisatorisch umgesetzt und kontrolliert werden. Wenn die geforderte
Sicherheit damit nicht erreichbar ist, ist dies eine offene Schutzentscheidung,
keine Funktion, die durch ein grünes Hash-Prüfergebnis ersetzt werden kann.

## 8. Funktionspaket E: Aufbewahrung, Prüfzugriff und Steuerberaterexport

- Dokumentartenbezogene Aufbewahrung mit Fristbeginn, Begründung und Verlängerung/
  Sperrvermerk (z.B. laufende Prüfung). Fristen als Vorschlag, betrieblich prüfbar.
- Keine automatische Löschung, keine Archivlöschfunktion, auch nach Fristablauf.
- Belege jederzeit nach Nummer, Partner, Zeitraum, Betrag und Referenz finden.
- Lesbarer Prüfzugriff ohne Änderungsrechte; offline und ohne PDF24-Abhängigkeit.
- Export nach Rechnungs-/Belegdatum oder Registerperiode; Archivierungsdatum bleibt
  ein eigener Filter. Bestehende Exportfunktion nicht still umdeuten.
- Digitale Originale einschließlich XML, relevante zugeordnete Mails/Belege,
  Register als dokumentiertes CSV/JSON, Metadaten, Korrekturbezüge, Prüfnachweise
  und zum Zeitraum gehörende Verfahrensdokumentationen kopieren.
- Hashes, Formatbeschreibung und menschenlesbaren Index mitliefern und den Export
  vollständig zurücklesen/verifizieren. Keine Manipulation von Originalen.
- Dokumentierte Feldtypen/Zeichenkodierung und verlustfreie Dezimalbeträge; CSV
  gegen unerwünschte Tabellenkalkulationsformeln absichern.
- Kein behaupteter DATEV-Buchungsstapel ohne mit der Steuerberatung abgestimmte
  Kontierung/Formatvorgaben. Zunächst neutraler Beleg-/Registerexport und Ausdrucke.
- Ein solcher Export allein ersetzt nicht jeden möglichen Datenzugriff nach § 147 AO;
  die tatsächlich benötigten Prüf-/Buchhaltungsdaten sind betrieblich festzulegen.

## 9. Funktionspaket F: Dokumentation, Installation und Altbestand

- Bestehenden Dokumentationsassistenten um Nummernserien, PDF24-Schritt, Portal/
  Thunderbird-Import, Rollen, Änderungsschutz, Abgleich, Fristen und Wiederherstellung ergänzen.
- Neue Fassungen versionieren; betriebliche Freigabe mit nachvollziehbarer Person
  und Zeitpunkt erfassen. Keine Behauptung einer qualifizierten elektronischen Signatur.
- Windows-Installation, erster Start und Prüfstatus müssen klar zeigen, welche
  Schutzmaßnahmen tatsächlich aktiviert und welche noch offen sind.
- Konfiguration und Datenformate versionieren; ältere V1-Archive lesbar halten.
- Migration zunächst rein lesend prüfen, vollständig sichern, dann neue Verwaltungsdaten
  ergänzen. Kein stilles Umbenennen, Reparieren oder Umformatieren alter Originale.
- Altbestand aus gesendeten/empfangenen Portal-Rechnungen bzw. später Thunderbird
  zurückholen und mit Papierordner/Register abgleichen. Nicht mehr verfügbare
  elektronische Originale als offene Lücke dokumentieren und mit Steuerberatung klären.
- Rückwirkender Import dokumentiert den tatsächlichen heutigen Importzeitpunkt,
  nicht eine angeblich frühere digitale Archivierung.
- Papier-Scans als Kopien kennzeichnen. Keine automatische Vernichtung der bisherigen
  Papierordner und kein pauschaler Anspruch auf ersetzendes Scannen.
- Windows-Paket mit Bedienhandbuch, Setup-/Wiederherstellungsanleitung, Formatbeschreibung,
  Abnahmeprotokoll und SHA-256. Codesignierung der Anwendung als getrennte optionale
  Veröffentlichungsentscheidung, kein GoBD-Zertifikat.

## 10. Umsetzung in einem zusammenhängenden Auftrag

Nach Bestätigung der offenen Betriebsentscheidungen werden die Pakete in dieser
Abhängigkeitsreihenfolge umgesetzt, ohne zwischendurch neue Produktentscheidungen
zu erfinden:

1. Datenmodell, Registerereignisse und rückwärtskompatible Migration.
2. Sichere Parser, EML-/Dateiimport, Offline-Validierung und strukturierte Anzeige.
3. Eingangs-/Ausgangsablauf, Nummernkontrolle, Freigabe, Storno-/Korrekturbezüge.
4. Lokaler kontrollierter Archivbestand, Schreibdienst/Berechtigungen gemäß freigegebenem Schutzprofil.
5. A/B-Abgleich für Originale, Register, Journale, Dokumentationen und Konfiguration.
6. Vollständigkeitskontrolle, Fristen, Export und Ausdrucke.
7. Erweiterter Assistent, Wiederherstellung und Altbestandsübernahme.
8. Gesamtprüfung, Windows-Build, Installationstest und bereitgestelltes Paket.

Ein Auftrag umfasst die gesamte Umsetzung, Tests und den Windows-Build. Die
Einrichtung von Benutzerkonten, Schlüsselverwahrung, realen USB-Sticks und
betrieblichen Freigaben auf eurem Gerät kann nicht durch einen Cloud-Build
ersetzt werden und bleibt ein angeleiteter Abnahmeschritt vor dem Livebetrieb.

## 11. Verbindliche Abnahmekriterien und Tests

- Rechnungsoriginale bleiben bytegleich; Quellen werden nicht verändert.
- Unveränderte vorhandene Objekte werden nur geprüft, abweichende Ziele nie ersetzt.
- Zwei verschiedene USB-Medien anhand stabiler Kennungen; Erfolg nur nach A/B-Verifikation.
- Fehlende Medien, voller Datenträger, USB-Abzug, Hash-Abweichung, Sperren und
  Unterbrechungen vor/während/nach Kopier- und Metadatenphasen führen nicht zu falschem Erfolg.
- Reimport, gleicher Name in verschiedenen Ordnern, gleiche Rechnungsnummer bei
  verschiedenen Lieferanten, doppelte eigene Nummer und geänderte Quelle sind korrekt behandelt.
- Nummernlücken, Serien-/Jahreswechsel, Gutschriften/Stornos, mehrere Steuersätze,
  Rundungen und Betragsabweichungen sind nachvollziehbar prüfbar.
- Beschädigte PDFs/XML/Mails, unbekannte Profile, XXE und übergroße Anhänge sind
  begrenzt verarbeitet; Belege werden nicht still vernichtet oder als valide ausgegeben.
- Register-, Journal- und Dokumentationsmanipulation, Kettenkürzung im unterstützten
  Referenzmodell und widersprüchliche A/B-Stände werden erkannt.
- Im Schutzprofil kann ein gewöhnlicher Benutzer außerhalb der App keine übernommenen
  Originale/Verwaltungsnachweise ändern oder löschen; Dienstschnittstelle ist authentisiert.
- Dienst-/Schlüsselzugriff, Prozessabbruch und Wiederanlauf sind auf Windows getestet.
- Vollständiger Wiederherstellungstest in einen neuen isolierten Bereich: Originale,
  Register, Beziehungen, Nachweise und Schlüssel/Schutzkonfiguration stimmen überein.
  Bestehendes Archiv wird dabei nicht überschrieben oder still repariert.
- Export ist vollständig, maschinell lesbar, bytegleich und auch ohne App nachvollziehbar.
- Oberfläche friert bei Import/Prüfung/Sicherung/Export nicht ein; Rollen und reale
  lokale/gesicherte/offene Zustände sind verständlich sichtbar.
- Beide Belegassistenten sind vom Dateiimport bis Ergebnis getestet: fehlende
  Pflichtdaten, falsche Richtung/Nummer, mehrere Mailanhänge, ungültige Eingangsrechnung,
  Ausgangsfreigabe, Versandzuordnung, Wiederaufnahme, Abbruch und A/B-Ausfall.
- Gleiche Dateinamen landen ohne manuelle Umbenennung konfliktfrei bei verschiedenen
  Belegen; Originalbytes bleiben gleich. Eine abweichende Datei für einen vorhandenen
  Beleg wird nicht als harmlose Dublette oder stiller Ersatz behandelt.
- Arbeitsanleitung, Assistenten-Texte und generierte Verfahrensdokumentation
  beschreiben denselben tatsächlich implementierten Ablauf.
- Tests werden vor den zugehörigen Implementierungen ergänzt; Linux-Kerntests,
  Windows-Tests und Starttest der tatsächlich gebauten EXE bestehen.
- Auf eurem PC zusätzlich echte USB-Sicherung, Entfernen eines Sticks, Wiederanlauf,
  Zugriffsschutz und Wiederherstellung prüfen; Ergebnisse dokumentieren.
- Abgleich mit Steuerberatung und betriebliche Freigabe der Dokumentation erfolgen
  vor der Aussage, dass der konkrete Prozess GoBD-konform betrieben wird.

## 12. Festgelegter Auftrag und Angaben zur Einrichtung

| Entscheidung | Aktueller Vorschlag / offener Punkt |
| --- | --- |
| Lokaler PC plus zwei USB-Sticks | Festgelegt; keine Cloud-Abhängigkeit |
| Mailimport | Portal-Dateien jetzt, ausgewählte Thunderbird-EML später; kein automatischer Versand |
| Steuerberater | Papierordner bleibt möglich; digitaler neutraler Export wird zusätzlich bereitgestellt |
| Belegverarbeitung | Zwei geführte Assistenten mit automatischer Ablage, Prüf-/Freigabeschritten, sichtbaren offenen Aufgaben und passender Arbeitsanleitung eingeplant |
| Nummernschema | Jahreszahl plus vier laufende Stellen bestätigt; Trennzeichen und letzter Stand werden beim Einrichten übernommen |
| Windows | Windows 11 und getrennte Benutzerkonten bestätigt; Home/Pro und konkrete Konten werden bei Einrichtung erfasst |
| Änderungsschutz | Windows-Schreibdienst mit NTFS-Rechten eingeplant; einmalige Admin-Einrichtung bestätigt; unabhängige Referenzen/Schlüsselverwahrung werden im Setup festgelegt |
| Stick-Dateisystem/Kapazität | Beim Einrichten prüfen; keine automatische Formatierung |
| Buchführung außerhalb des Archivs | EÜR/Bilanz, Zuständigkeit, weitere Belegarten und nötige Datenzugriffe mit Steuerberatung abgrenzen |
| Digitaler Start/Altbestand | Stichtag und Rückholung verfügbarer Originale aus dem Portal festlegen |
| Betriebsrhythmus | Tägliche Sicherung bei neuen Daten, monatlicher Abgleich, regelmäßige Vollprüfung/Wiederherstellungsprobe als Vorschlag bestätigen |

Alle bestehenden Sicherheitsinvarianten aus AGENTS.md und SPECIFICATION.md bleiben
verbindlich. Eine später erforderliche Änderung daran wird ausdrücklich vorgelegt;
diese Planung genehmigt keine stille Lockerung.

Der Plan ist für den nächsten zusammenhängenden Umsetzungsauftrag vorbereitet.
Die Bestätigung der Planungsangaben wird nicht als bereits erfolgte Einrichtung
auf dem PC, Abnahme realer USB-Medien oder Freigabe durch die Steuerberatung ausgegeben.
