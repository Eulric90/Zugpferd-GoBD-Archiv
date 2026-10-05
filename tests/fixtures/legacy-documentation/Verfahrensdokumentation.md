# Verfahrensdokumentation

## Fassung und Status

### Fassung

> 1

### Dokument-ID

> 00000000-0000-0000-0000-000000000012

### Erstellt (UTC)

> 2026-10-05T10:00:00+00:00

### Gültig ab

> 2026-10-05

### Status

> Entwurf

### Freigabe durch

> Noch nicht betrieblich freigegeben

## Unternehmen und Zuständigkeiten

### Unternehmen / Organisation

> Betriebsangabe organization

### Anschrift

> Betriebsangabe address

### Geltungsbereich (Bereiche, Standorte, Rechnungsarten)

> Betriebsangabe scope

### Verantwortliche Person und Zuständigkeit

> Betriebsangabe responsible

### Vertretung und Zuständigkeit

> Betriebsangabe deputy

## Belegablage und Aufbewahrung

### Eingang: Herkunft, Erfassung und Zuordnung

> Betriebsangabe receipt_process

### Ausgang: Erstellung, Erfassung und Zuordnung

> Betriebsangabe outgoing_process

### Kontrolle auf Vollständigkeit und richtige Zuordnung

> Betriebsangabe completeness_control

### Zugriffsrechte und Schutz vor Änderungen

> Betriebsangabe access_control

### Aufbewahrungsfristen und deren betriebliche Umsetzung

> Betriebsangabe retention_policy

## Sicherung und Prüfung

### Sicherungsrhythmus, Zuständigkeit und Erfolgskontrolle

> Betriebsangabe backup_schedule

### Prüfrhythmus, Berichtsauswertung und externe Journalanker

> Betriebsangabe integrity_schedule

### Physische Kennzeichnung, Aufbewahrung und Transport von A

> Betriebsangabe location_a

### Physische Kennzeichnung, Aufbewahrung und Transport von B

> Betriebsangabe location_b

## Störungen, Änderungen und Export

### Verhalten bei Fehlern, Unterbrechungen und Wiederanlauf

> Betriebsangabe incident_process

### Klärung geänderter Quellen und Freigabe von Eingriffen

> Betriebsangabe change_process

### Prüfexport: Zuständigkeit, Auswahl und sichere Weitergabe

> Betriebsangabe export_process

### Änderungsgrund gegenüber der vorherigen Fassung

> Betriebsangabe change_note

## Automatisch ergänzte technische Beschreibung

### Softwareversion

> 1.0.0

### Arbeitsablage

> C:\Rechnungen

### Archiv-ID

> archive

### Medium A: UUID

> A

### Medium A: Volume-Kennung

> volume-A

### Medium A: Pfad zum Erstellzeitpunkt

> A:\

### Medium B: UUID

> B

### Medium B: Volume-Kennung

> volume-B

### Medium B: Pfad zum Erstellzeitpunkt

> B:\

### Letzter Sicherungslauf zum Erstellzeitpunkt

> Noch kein Sicherungslauf bekannt

### Arbeitsstruktur

> Eingang/<Jahr>/ und Ausgang/<Jahr>/; Verwaltung unter Archivverwaltung/. Alle regulären Dateien werden unverändert übernommen. Es erfolgt keine Rechnungsvalidierung oder Konvertierung.

### Archivstruktur

> Archive/<Jahr>/Eingang/... bzw. Ausgang/...; Manifest/, Journal/, Pruefberichte/ und Verfahrensdokumentation/. Ursprüngliche relative Pfade verhindern Namenskollisionen.

### Sicherungsablauf

> Quelle und Metadaten erfassen, SHA-256 berechnen; vorhandene Ziele prüfen; temporär auf A und B kopieren; flush/close; jedes Ziel vom jeweiligen Medium zurücklesen und SHA-256 prüfen; ohne Überschreiben veröffentlichen; Metadaten und verkettetes Journal anhängen. Erfolg erst nach Verifikation beider Medien. Identische Archivobjekte werden nicht neu geschrieben.

### Metadaten und Journal

> Originalname, relativer Quellpfad, Zielpfad, Größe, Quell-mtime/ctime in Nanosekunden, UTC-Archivierungszeit und SHA-256. Journal: canonical JSON (UTF-8, sortierte Schlüssel), Sequenz, Zeitpunkt, Ereignis, Daten, Vorgängerhash und Eintragshash.

### Integrität und Konflikte

> Vollprüfung und A/B-Vergleich prüfen Medienkennungen, Objekte, SHA-256, Manifest und Journal. Fehlende, veränderte oder widersprüchliche Originale werden nicht still repariert. Geänderte Quellen werden abgelehnt; die Historie bleibt erhalten. V1 hat keine Archivlöschfunktion.

### Unterbrechung und Wiederanlauf

> Temporäre .partial-<UUID>-Dateien bleiben erkennbare Belege und sind keine Originale. Sperrdateien nach einem Absturz nur nach dokumentierter manueller Prüfung entfernen. Ein Widerspruch zwischen Manifest und Journal blockiert weitere Schreibvorgänge. Originale, Manifest und Journal nicht zur Fehlerbehebung löschen oder bearbeiten.

### Export

> Ein Export kopiert ausgewählte Originale mit Index/Manifest und Prüfbericht in einen neuen Ordner. Jahresfilter beziehen sich auf die Quellablage, Datumsfilter auf UTC-Archivierungszeitpunkte. Quellen und Archivobjekte werden weder verschoben noch gelöscht.

### Dokumentationsfassungen

> Diese Fassung liegt als Markdown, druckbare HTML-Datei und JSON mit SHA-256-Prüfsummen vor. Neue Fassungen ersetzen alte nicht. Kopien auf beiden zugeordneten Medien werden zurückgelesen und geprüft; Speicherung wird im Journal protokolliert.

### Sicherheitsgrenzen

> Eine SHA-256-Hash-Kette ist manipulationsanzeigend, kein WORM-Speicher, keine Codesignatur und kein qualifizierter Zeitstempel. Konsistentes Neuschreiben aller Daten oder Kürzen von Journal und Manifest ist ohne unabhängige externe Anker nicht sicher erkennbar. Sperren koordinieren die Anwendung, nicht beliebige Fremdsoftware. Rechte, Medienaufbewahrung und regelmäßige dokumentierte Prüfungen müssen betrieblich umgesetzt werden.

### Hinweis

> GoBD-unterstützende Archivierung. Die Software allein garantiert keine GoBD-Konformität. Die betrieblichen Angaben stammen vom Betreiber und müssen in der Praxis umgesetzt sowie geprüft werden. Der Status „Betrieblich freigegeben“ dokumentiert dessen Eingabe, keine rechtliche Zertifizierung.

