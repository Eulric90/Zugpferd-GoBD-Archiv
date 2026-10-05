# V1.0 unter Windows verwenden

## Portable Anwendung starten

Voraussetzung: Windows 10/11 (64 Bit). Das Windows-Build-Artefakt enthält
`ZugpferdArchiv-1.0.0-Windows-x64.zip` und die zugehörige `.zip.sha256`.
Das ZIP vollständig in einen beschreibbaren Ordner entpacken und
`ZugpferdArchiv/ZugpferdArchiv.exe` starten. Der mitgelieferte `_internal`-Ordner
muss neben der EXE bleiben. Python muss auf dem Zielrechner nicht installiert sein.
Die Anwendung benötigt im Betrieb keine Cloud-Verbindung. Es wird keine
Codesignatur oder rechtliche Zertifizierung behauptet.

Den Download-Hash kann PowerShell mit
`Get-FileHash .\ZugpferdArchiv-1.0.0-Windows-x64.zip -Algorithm SHA256` prüfen.

## Einrichten

1. Arbeitsordner auswählen oder `C:\Rechnungen anlegen` drücken. Vorhandene
   Inhalte bleiben erhalten. `Struktur anlegen` erstellt auch bei einem frei
   gewählten Arbeitsordner die Unterordner.
2. Rechnungen unverändert nach `Eingang/<Jahr>/...` bzw. `Ausgang/<Jahr>/...`
   ablegen. Unterordner sind erlaubt. Alle regulären Dateien werden archiviert,
   auch Begleitdateien; es erfolgt keine Konvertierung oder Rechnungsvalidierung.
3. Zwei verschiedene physische USB-Medien anschließen. Beide müssen genügend
   freien Speicher haben. USB-Festplatten können in Windows als feste Laufwerke
   erscheinen und sind deshalb ebenfalls auswählbar.
4. Medium A auswählen und als A registrieren. Medium B auswählen und als B
   registrieren, während A ausgewählt ist. B übernimmt die Archiv-ID von A.
5. `A/B zuordnen und speichern` drücken. Die Konfiguration speichert die
   Kennungen, nicht die Laufwerksbuchstaben. Nach einem Wechsel der Buchstaben
   `Medien neu suchen` drücken; registrierte Medien werden anhand der Kennungen
   wieder zugeordnet. Ein fehlendes oder unerwartetes Medium blockiert den Lauf.

Arbeitsablage und Archivmedien müssen getrennt sein. Unter Windows dürfen
A und B nicht zwei Ordner desselben Volumes sein; die Arbeitsablage darf nicht
auf einem der Archivvolumes liegen. Volume-Serienkennung/Dateisystem ergänzt
Archiv-ID, Rolle und Medien-UUID. Bitweise geklonte Kennungen sind kein Beweis
für unabhängige Hardware; zwei separat registrierte physische Medien verwenden.

## Sichern und prüfen

`Sichern auf A und B` prüft zuerst die vorhandene Archivhistorie. Neue Dateien
werden auf beiden Medien kopiert, geflusht und vom jeweiligen Ziel zurückgelesen.
Identische bereits archivierte Dateien werden geprüft und nicht neu geschrieben.
Ein Lauf wird erst nach der A/B-Verifikation als erfolgreich angezeigt. Auch eine
Sicherung ohne neue Dateien prüft die gesamte bestehende Historie.

Geänderte Quellen, widersprüchliche Ziele, fehlende archivierte Objekte,
ungültige Journal-Ketten und falsche Medien blockieren neue Archivschreibvorgänge.
Quellen und bestehende Archivobjekte bleiben erhalten. Geänderte Quellen werden
in V1 **nicht** automatisch als neue Version archiviert. Der Konflikt muss unter
erhaltener Historie organisatorisch geklärt werden.

`Vollständige Integritätsprüfung` und `A/B vergleichen` lesen alle erwarteten
Originale, prüfen SHA-256, Metadaten, Medienkennungen, Journal-Ketten und A/B-Gleichheit.
Fehlende, veränderte, unerwartete und widersprüchliche Objekte werden separat
gezählt. Keine der Prüfungen repariert Dateien automatisch.

Die Oberfläche bleibt während längerer Vorgänge bedienbar; Änderungen an der
Konfiguration und parallele Archivoperationen sind dabei gesperrt. Fenster erst
nach Abschluss schließen, anschließend Medien über Windows sicher auswerfen.

## Berichte und Export

Jeder Lauf schreibt einen deutschen Textbericht und JSON unter
`Archivverwaltung/Pruefberichte`. Auf korrekt zugeordneten Medien werden ebenfalls
Berichte abgelegt. Das lokale Laufjournal liegt unter
`Archivverwaltung/Protokolle/operations.jsonl`. Ein fehlgeschlagener Lauf erscheint
nicht als vollständige letzte Sicherung. Die Oberfläche zeigt Zeit und Dateizahlen.

Für einen Prüfexport den Bereich der **Jahre in der Quellablage** einstellen.
Optional zusätzlich nach **Archivierungsdatum in UTC** filtern; dieses Datum ist
nicht das Rechnungsdatum. Der ausgewählte Bereich ist einschließlich beider
Grenzen. V1 interpretiert keine Rechnungsinhalte oder PDF/XML-Datumsfelder.

`Prüfexport erstellen` kopiert nach einer vollständigen A/B-Prüfung in einen neuen
Ordner unter dem gewählten Exportziel. Er enthält `Originale/`, `index.json` mit
Originalpfaden und SHA-256 sowie einen Prüfbericht. Bestehende Exportordner werden
nicht überschrieben. Der Export verschiebt oder löscht weder Quellen noch Archive.
Bei einem Kopierfehler kann ein unvollständiger Exportordner mit erkennbaren
Temporärdateien zurückbleiben; maßgeblich ist der fehlgeschlagene lokale Bericht.

## Unterbrechungen und Fehlerbehandlung

- Dateien mit `.partial-<UUID>` sind unterbrochene temporäre Kopien, keine
  archivierten Originale. Ein neuer Lauf verwendet einen frischen temporären Namen.
  Alte temporäre Dateien bleiben als Belege erhalten, die Sicherung weist darauf
  mit einer Warnung hin und die vollständige Prüfung meldet sie als Unterbrechung.
- Eine nach einem Abbruch vollständig veröffentlichte, aber noch nicht im Manifest
  verzeichnete Datei kann nur dann übernommen werden, wenn die noch vorhandene
  Quelle identisch ist und beide Medien sonst konsistent sind. Diese Übernahme
  schreibt einen neuen Manifest- und Journal-Eintrag, ohne das Original zu ersetzen.
- Ein bereits auf A vollständig verzeichnetes Objekt kann nach Ausfall von B beim
  nächsten Lauf auf B ergänzt werden, solange die Quelle identisch und A unverletzt
  ist. Fehlt die Quelle, bleibt die Replikation unvollständig und der Lauf schlägt fehl.
- Ein Abbruch zwischen Manifest- und Journal-Anhang erzeugt einen Widerspruch.
  V1 blockiert dann weitere Schreibvorgänge und verlangt eine manuelle Prüfung.
  Es gibt keine automatische Rekonstruktion oder stille Reparatur.
- `.zugpferd-operation.lock` verhindert konkurrierende Lauf-/Journalschreibvorgänge.
  Nach einem harten Prozessabbruch kann die Sperrdatei verbleiben. Erst nach
  Sicherstellung, dass kein Prozess mehr arbeitet, und nach dokumentierter Prüfung
  darf ein Verantwortlicher ausschließlich diese Sperrdatei manuell entfernen.
  Keine Rechnung, Manifest- oder Journaldatei dafür löschen oder bearbeiten.

## Sicherheitsgrenzen

SHA-256 und verkettete Journale unterstützen das Erkennen von Veränderungen.
Eine Hash-Kette ist weder WORM-Speicher noch ein qualifizierter Zeitstempel.
Wer Originale und alle Metadaten einschließlich der Ketten konsistent neu schreibt
oder das Kettenende samt zugehörigem Manifest kürzt, kann durch diese Anwendung
allein nicht sicher erkannt werden. Externe Anker, Zugriffsrechte, getrennte
Aufbewahrung und regelmäßige dokumentierte Prüfungen gehören zum Betrieb.

Die Datenträger dürfen während eines Laufs nicht von anderen Prozessen verändert
werden. Die Sperren koordinieren diese Anwendung, nicht beliebige Fremdsoftware.
Symlinks und Windows-Reparse-Punkte werden abgelehnt. Ein adversarialer
Administrator oder ein defekter Controller wird nicht durch Anwendungscode
kontrolliert. Flush und Rückleseprüfung ersetzen keine Hardware-/Stromausfallsicherheit.

Die Software allein garantiert keine GoBD-Konformität; siehe die betriebliche
Vorlage in `VERFAHRENSDOKUMENTATION.md`.

## Assistent für die Verfahrensdokumentation

`Verfahrensdokumentation erstellen` startet den Assistenten. Voraussetzung sind
registrierte, zugeordnete und angeschlossene Medien A und B sowie eine intakte
Archivhistorie. Der Assistent fragt die tatsächlichen betrieblichen Angaben ab:

1. Unternehmen, Anschrift, Geltungsbereich, Verantwortliche und Vertretung.
2. Rechnungseingang/-ausgang, Vollständigkeitskontrolle, Zugriffsrechte und Aufbewahrung.
3. Sicherungs- und Prüfrhythmus sowie physische Kennzeichnung und Aufbewahrung beider Medien.
4. Fehlerbehandlung, geänderte Quellen, Export und optional der Änderungsgrund.
5. Vorschau, Gültigkeitsdatum und optional die betriebliche Freigabe mit freigebender Person.

Die technischen Angaben – Softwareversion, Arbeitsordner, Archiv-ID, Medien-UUIDs,
Volume-Kennungen und der letzte Sicherungslauf – sowie die Beschreibung der
Archivierung und ihrer Grenzen ergänzt die Anwendung automatisch. Pfade und
Sicherungsstatus sind eine Momentaufnahme zum Erstellzeitpunkt. Betriebliche
Abläufe und Aufbewahrungsfristen werden vom Betreiber eingegeben und nicht von
der Software rechtlich beurteilt. Der Inhalt muss der tatsächlichen Nutzung entsprechen.

Standardmäßig wird ein **Entwurf** erstellt. `Angaben betrieblich geprüft und
freigegeben` kennzeichnet eine vom Betreiber freigegebene Fassung; diese Eingabe
ist keine digitale Signatur, rechtliche Zertifizierung oder Garantie der GoBD-Konformität.

`Fassung speichern und A/B prüfen` speichert eine neue, unveränderliche Fassung:

- Arbeitsablage: `Archivverwaltung/Verfahrensdokumentation/Fassungen/<Dokument-ID>/`
- Beide Archivmedien: `Verfahrensdokumentation/Fassungen/<Dokument-ID>/`

Enthalten sind `Verfahrensdokumentation.html` (druckbar),
`Verfahrensdokumentation.md`, `document.json` (Angaben und technische Momentaufnahme)
und `checksums.json` (SHA-256-Prüfsummen). Jede Kopie wird vom Ziel zurückgelesen.
Die Archivjournale verzeichnen die gespeicherte Fassung und die Dateihashes.
Die lokale `completion.json` wird erst nach vollständiger Speicherung und
Prüfung auf beiden Medien erstellt. Erst dann gibt die Oberfläche Erfolg aus.
Berichte zeigen die lokalen Dateipfade. Die Dokumentation enthält betriebliche
und personenbezogene Angaben; die festgelegten Zugriffsrechte gelten auch hierfür.

`Gespeicherte Dokumentation öffnen` öffnet die letzte abgeschlossene Fassung im
Browser. Mit **Drucken → Als PDF speichern** lässt sich daraus bei Bedarf eine PDF
erstellen. Die Anwendung erzeugt selbst HTML, Markdown und JSON, keine PDF-Datei.

Bei einer späteren Änderung den Assistenten erneut starten. Die bisherigen
Angaben sind vorbelegt; eine neue Fassung beginnt wieder als Entwurf und ersetzt
keine ältere Datei. Eine laufende Fassung wird bei `Abbrechen` nicht gespeichert.

Falls A/B-Speicherung unterbrochen wurde, bietet der Assistent die ausstehende
Fassung unverändert zur erneuten Speicherung an. Erst diese abschließen, dann
eine geänderte Fassung erzeugen. Identische bereits kopierte Dateien bleiben
unverändert, widersprüchliche Ziele werden nicht überschrieben. Beschädigte oder
fehlende bereits im Journal verzeichnete Dokumentationsdateien werden nicht
still repariert. Temporäre Kopien bleiben als erkennbare Belege erhalten; eine
erfolgreiche Wiederaufnahme kann darauf mit einer Warnung hinweisen. Die Vollprüfung
meldet ausstehende Fassungen, fehlende/veränderte Dokumentationsdateien,
unbekannte Dateien und verbliebene temporäre Kopien. Eine unvollständige
Dokumentationsfassung blockiert auch neue Sicherungen, bis sie abgeschlossen ist.

## Rechnungsbetrieb unter Windows 11

Vor dem Livebetrieb das geschützte Profil nach [WINDOWS_EINRICHTUNG.md](WINDOWS_EINRICHTUNG.md)
einrichten und mit beiden persönlichen Konten abnehmen. `Betrieb einrichten` erfasst
Firmendaten, Zuständigkeiten, Umstellung und den vereinbarten Sicherungsrhythmus.
Bestehenden Nummernstand bestätigen; Nummernreservierungen bleiben nach Abbruch verbraucht.

`Eingangsrechnung übernehmen` und `Ausgangsrechnung übernehmen` prüfen eine ausgewählte
Datei oder einen EML-Anhang, zeigen erkannte Daten und verlangen die sachliche Kontrolle.
`Belegregister / Aufgaben` zeigt offene Prüfungen, Versand, A/B-Sicherungen und Nummernlücken.
Begründete Metadatenkorrekturen erhalten den bisherigen Wert. Eine Berichtigung/Storno ist
eine neue Originaldatei mit Beziehung zum ursprünglichen Beleg. Betragskorrekturen sind
nur für manuell erfasste Angaben zulässig; führende XML-Daten dürfen nicht abweichen.

PDF24 erstellt die Rechnung. Den freigegebenen unveränderten Anhang persönlich versenden;
anschließend Datum, Empfänger und identischen Anhang/gesendete EML bestätigen.
Die vollständigen Schritte stehen in [ARBEITSANLEITUNG_RECHNUNGEN.md](ARBEITSANLEITUNG_RECHNUNGEN.md)
und in der druckbaren Anleitung der Anwendung.

Der Registerexport filtert nach Rechnungsdatum und enthält unveränderte Originale,
lesbare XML-HTML-Ansichten, CSV/JSON, Historie und Prüf-/Dokumentationsnachweise.
`index.html` und Rechnungen können für den Steuerberaterordner gedruckt werden.
Elektronische Originale bleiben daneben erhalten. Der bestehende Quellenjahr-/Archivdatumexport
ist eine separate Funktion. Exporte überschreiben keine vorhandenen Zielordner.
