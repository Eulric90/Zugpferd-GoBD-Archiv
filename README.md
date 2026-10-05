# Zugpferd GoBD Archiv

Windows-Anwendung zur GoBD-unterstützenden Archivierung elektronischer Ein- und Ausgangsrechnungen (PDF, ZUGFeRD/PDF-A-3 und XML) auf zwei redundanten USB-Medien.

> **Hinweis:** Die Software allein garantiert keine GoBD-Konformität. Entscheidend sind auch Verfahrensdokumentation, Berechtigungen und die tatsächliche betriebliche Nutzung.

## Ziel V1.0

- GUI für Windows
- Basisstruktur auf `C:\Rechnungen` automatisch erzeugen
- `Eingang\<Jahr>` und `Ausgang\<Jahr>` automatisch verwalten
- alternativ frei wählbarer Grundordner
- zwei USB-Medien als Archiv A und B registrieren
- Medien über UUID/Kennung statt Laufwerksbuchstaben wiedererkennen
- Originaldateien bytegenau archivieren
- SHA-256 vor und nach dem Kopieren verifizieren
- archivierte Objekte niemals still überschreiben
- Veränderungen bereits archivierter Quelldateien erkennen und dokumentieren
- append-orientiertes, hash-verkettetes Journal
- Archive A/B vergleichen
- vollständige Integritätsprüfung
- Sicherungs- und Prüfberichte
- Export für Betriebsprüfung/Steuerberatung
- Verfahrensdokumentation

## Sicherheitsprinzipien

1. **Original erhalten:** Keine Konvertierung der archivierten Rechnungsdatei.
2. **Fail closed:** Bei Hash-Abweichung, falschem Medium oder widersprüchlichem Archivstatus wird nicht weitergeschrieben.
3. **Kein stilles Überschreiben:** Existiert ein Zielobjekt mit anderem Hash, ist das ein Integritätsfehler.
4. **Verifikation:** Jede geschriebene Datei wird vom Zielmedium zurückgelesen und erneut gehasht.
5. **Redundanz:** Eine Sicherung gilt nur dann als vollständig, wenn A und B erfolgreich verifiziert wurden.
6. **Nachvollziehbarkeit:** Sicherungsläufe und relevante Ereignisse werden protokolliert.
7. **Trennung:** Arbeitsablage auf C: und Archivmedien sind getrennte Rollen.

Siehe `docs/SPECIFICATION.md` und `AGENTS.md` für die verbindlichen Anforderungen.


## V1.0 starten

Das portable Windows-x64-Paket wird im [Windows-Build](https://github.com/Eulric90/Zugpferd-GoBD-Archiv/actions/workflows/windows.yml)
als Artefakt `ZugpferdArchiv-1.0.0-Windows-x64` bereitgestellt. Das enthaltene ZIP
vollständig entpacken und `ZugpferdArchiv.exe` neben dem `_internal`-Ordner starten.
Python muss auf dem Zielrechner nicht installiert sein.

Die V1 umfasst die Desktop-Oberfläche, registrierte A/B-Medien, verifizierte
Originalkopien, Konflikterkennung, verkettete Journale, Integritätsprüfung,
A/B-Vergleich, TXT-/JSON-Berichte und einen nichtdestruktiven Jahres-/Datums-Export.
Veränderte Quellen werden sicher abgelehnt; bestehende Archivhistorie wird erhalten.

- [Bedienung und Fehlerbehandlung](docs/BENUTZERHANDBUCH.md)
- [Betriebliche Verfahrensdokumentation](docs/VERFAHRENSDOKUMENTATION.md)
- [Entwicklung, Tests und Windows-Packaging](docs/ENTWICKLUNG.md)

Für den Start aus dem Quellcode: Python 3.12+, `python -m pip install -e .`,
anschließend `python -m zugpferd_archiv`. Der Windows-Build verwendet
`scripts/build_windows.ps1`; er prüft die Tests und startet auch die gebaute EXE.

## Verfahrensdokumentation erstellen

Der integrierte Assistent fragt Unternehmensdaten und betriebliche Abläufe ab,
ergänzt Archivkennungen und technische Angaben automatisch und zeigt eine Vorschau.
Er speichert versionierte Fassungen als druckbare HTML-Datei, Markdown und JSON
lokal sowie verifiziert auf A/B. Frühere Fassungen bleiben erhalten. Entwürfe und
betriebliche Freigaben werden ausdrücklich unterschieden; die Angaben müssen
vom Betreiber geprüft und in der Praxis umgesetzt werden.
