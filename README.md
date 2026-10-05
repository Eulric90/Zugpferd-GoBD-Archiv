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

