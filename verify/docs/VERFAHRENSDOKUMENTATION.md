# Verfahrensdokumentation – betriebliche Vorlage

Diese Vorlage ist vom Betreiber auszufüllen, zu versionieren und freizugeben.
Die Anwendung unterstützt Archivierungsabläufe; sie ist keine rechtliche
Zertifizierung und garantiert für sich allein keine GoBD-Konformität.

| Gegenstand | Vom Betreiber festzulegen |
| --- | --- |
| Verantwortliche Person / Vertretung | Name, Zuständigkeiten, Freigaben |
| Version und Änderungsnachweis | Softwareversion, Einführungsdatum, freigegebene Abläufe |
| Eingang und Ausgang | Herkunft, Vollständigkeitskontrolle, Zuordnung, Rechnungsjahre |
| Arbeitsablage | Pfad, Zugriffsrechte, Schutz vor versehentlicher Änderung |
| Archivmedien | Archiv-ID, A/B-Medien-UUIDs, physische Kennzeichnung, sichere Aufbewahrung |
| Sicherungsrhythmus | Häufigkeit, zuständige Person, Kontrolle beider verifizierter Medien |
| Prüfung | Regelmäßige Vollprüfung, Berichtsauswertung, unabhängige externe Journalanker |
| Aufbewahrung | Anwendbare Fristen, organisatorische Aufbewahrungs- und Löschregeln |
| Störung und Wiederanlauf | Dokumentierte Sperr-/Temporärdateiprüfung, keine stille Reparatur |
| Geänderte Quellen | Klärungs- und Freigabeverfahren unter Erhaltung der archivierten Historie |
| Zugriff und Transport | Berechtigungen, Verschlüsselung auf Betriebssystemebene, getrennte Standorte |
| Export und Prüfung | Zuständigkeit, Auswahlkriterien, sichere Weitergabe, Hashprüfung |

## Technischer Ablauf V1.0

Archivierung: Quellmetadaten und SHA-256 erfassen; vorhandene Ziele prüfen;
verifizierte Kopie zunächst temporär auf dem jeweiligen Medium schreiben;
flush/close, SHA-256 vom Medium zurücklesen; ohne Überschreiben veröffentlichen;
Manifest und verkettetes Journal anhängen. Beide Medien werden vor einerErfolgsmeldung geprüft. Alte Archivobjekte werden weder ersetzt noch gelöscht.

Das Manifest enthält Originalnamen, relativen Quellpfad, Zielpfad, Größe,
Quellzeitstempel (mtime/ctime in Nanosekunden; ctime ist plattformabhängig),
UTC-Archivierung
szeitpunkt, Archiv-ID und SHA-256. Journal-Anhänge sind canonical
JSON (sortierte Schlüssel, UTF-8, kompakte Trenner), mit Sequenz, Zeit, Ereignis,
Daten, Vorgängerhash und Eintragshash. Die Eintragshashes schließen den eigenen
Hash aus der Berechnung aus. Das Journal ist manipulationsanzeigend, kein
unveränderlicher Datenträger.

Die Software liest nur Quelldateien; sie konvertiert, verschiebt oder löscht sie
nicht. Dateisysteme können beim Lesen Zugriffszeiten aktualisieren. Quell-mtime
wird erfasst, nicht auf den Archiveintrag kopiert; archivierte Byteinhalte und
Originalzeitstempel in Metadaten sind maßgeblich.

Aufgetretene Fehler, manuelle Eingriffe sowie Ergebnisse von Sicherung, Prüfung
und Export sind betrieblich zu dokumentieren. V1 enthält keine Archivlöschfunktion.

## Ausgefüllte Fassung über den Assistenten erzeugen

Die Anwendung bietet unter `Verfahrensdokumentation erstellen` einen Assistenten
für die Angaben dieser Vorlage. Technische Archivinformationen ergänzt sie
automatisch. Die Eingaben können zunächst als Entwurf gespeichert und nach
betrieblicher Prüfung in einer neuen Fassung freigegeben werden. Der Assistent
speichert jede Fassung mit eindeutiger Dokument-ID lokal und auf beiden
zugeordneten Medien, inklusive SHA-256-Prüfsummen und Journalnachweis.
Details und Wiederanlauf stehen im [Benutzerhandbuch](BENUTZERHANDBUCH.md).
