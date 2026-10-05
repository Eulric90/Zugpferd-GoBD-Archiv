# Entwicklung, Tests und Windows-Build

Python 3.12 oder neuer. Der Kern benötigt nur die Python-Standardbibliothek;
PySide6 wird ausschließlich von GUI und Einstiegspunkt verwendet.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
python -m ruff check src tests scripts
python -m zugpferd_archiv
```

`./scripts/build_windows.ps1` führt unter Windows Tests und statische Prüfung
aus, baut mit PyInstaller die portable EXE, startet die gebaute Anwendung zum
automatischen GUI-Starttest und erstellt ZIP und SHA-256-Datei. PyInstaller ist
kein Windows-Cross-Compiler; das Linux-Testergebnis ist kein Windows-Buildnachweis.

Der GitHub-Actions-Workflow `.github/workflows/windows.yml` verwendet Windows
Server 2022 und Python 3.12 x64. Er veröffentlicht das ZIP ausschließlich nach
bestandenen Tests und erfolgreichem Starttest der tatsächlich eingefrorenen EXE.
Das Artefakt ist 90 Tage abrufbar. `test-results.xml` wird ebenfalls bereitgestellt.

## Architektur

- `storage.py`: SHA-256, Pfadprüfung, exklusives Publizieren, Flush und Sperren.
- `media.py`: unveränderte Kennungen, Windows-Volumenprüfung, mockbare Erkennung.
- `journal.py`: canonical JSON und SHA-256-Kette, konkurrierende Anhänge gesperrt.
- `core.py`: Konfiguration, sichere Sicherung, Vollprüfung, A/B-Vergleich, Export.
- `reports.py`: TXT-/JSON-Berichte; keine Erfolgsmeldung bei Fehlern.
- `gui.py`: PySide6-Oberfläche mit QThread für Dateisystemoperationen.

## Fehlerfalltests

Temporäre Ordner ersetzen physische USB-Medien. Windows-Volume-Identitäten werden
für logische A/B-Testordner abstrahiert. Ein zusätzlicher Windows-Test prüft echte
Volume-APIs und die Ablehnung zweier Ordner auf demselben Windows-Volume.
Kein Test braucht ein echtes USB-Gerät oder löscht bestehende Benutzerdaten.

Die Tests decken unveränderte Quellen, Zielkonflikte, geänderte Quellen,
Hash-Abweichungen, Unterbrechungen vor und zwischen Metadaten-Commits, fehlende
Medien/Dateien/Metadaten, Symlinks/Reparse-Pfade, identische Wiederholung,
Medienkennung statt Buchstaben, Journal-/Manifestmanipulation, partielle Replikation,
Prüfberichte, Exportgrenzen und GUI-Arbeiter ab.

Physischer USB-Abzug, FAT/exFAT, Gerätestromausfall und alle unterstützten
Windows-Desktop-Versionen müssen zusätzlich im Betrieb mit den vorgesehenen
Medien erprobt werden. Der automatisierte Buildtest ersetzt diese Hardwareprüfung
nicht. Die Windows-Veröffentlichung erfolgt ohne Codesignatur.
