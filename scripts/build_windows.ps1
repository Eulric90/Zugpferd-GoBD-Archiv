$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ([Environment]::OSVersion.Platform -ne 'Win32NT') {
    throw 'Windows-Build muss auf Windows ausgeführt werden (PyInstaller ist kein Cross-Compiler).'
}
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Abhängigkeiten konnten nicht installiert werden' }
python -m pip install --no-deps --no-build-isolation -e .
if ($LASTEXITCODE -ne 0) { throw 'Paket konnte nicht installiert werden' }
python -m ruff check src tests scripts
if ($LASTEXITCODE -ne 0) { throw 'Statische Prüfung fehlgeschlagen' }
python -m pytest -q --junitxml=test-results.xml
if ($LASTEXITCODE -ne 0) { throw 'Tests fehlgeschlagen' }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name ZugpferdArchiv --paths src scripts/windows_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Windows-Packaging fehlgeschlagen' }
Copy-Item -Recurse docs dist/ZugpferdArchiv/docs
Copy-Item README.md dist/ZugpferdArchiv/README.md
python scripts/smoke_windows.py dist/ZugpferdArchiv/ZugpferdArchiv.exe
if ($LASTEXITCODE -ne 0) { throw 'Starttest der Windows-EXE fehlgeschlagen' }
python scripts/package_windows.py
if ($LASTEXITCODE -ne 0) { throw 'ZIP-Erstellung fehlgeschlagen' }
