"""SCM entry point for the separately packaged protected archive writer."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


def configuration_path() -> Path:
    return (
        Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        / "ZugpferdArchiv/service.json"
    )


def run():
    import servicemanager
    import win32service
    import win32serviceutil
    from .service import SERVICE_NAME, serve

    class WriterService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = "Zugpferd Archiv – geschützter Schreibdienst"
        _svc_description_ = "Lokale authentifizierte Erweiterung des Rechnungsarchivs ohne Löschschnittstelle."

        def __init__(self, args):
            super().__init__(args)
            self.stopped = threading.Event()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.stopped.set()
            # Unblock ConnectNamedPipe without accepting another business request.
            try:
                from .service import request

                request({"operation": "configuration"})
            except Exception:
                pass

        def SvcDoRun(self):
            config = json.loads(configuration_path().read_text(encoding="utf-8-sig"))
            serve(config, self.stopped.is_set)

    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(WriterService)
    servicemanager.StartServiceCtrlDispatcher()


def medium_subfolder(path: Path) -> str:
    value = path.relative_to(Path(path.anchor)).as_posix()
    return "" if value == "." else value


def provision(
    root: Path, a: Path | None, b: Path | None, migration: Path | None = None
):
    from . import storage, service
    from .core import ArchiveService
    from .media import register, read_marker, MARKER
    from uuid import uuid4

    service.IN_SERVICE = True
    if root.exists() and any(root.iterdir()):
        raise ValueError(
            "Dienstarchiv muss neuer leerer Ordner sein; keine Überschreibung"
        )
    if migration:
        if not a or not b:
            raise ValueError(
                "Migration braucht beide Medien für vorherige vollständige Prüfung"
            )
        old = ArchiveService(migration)
        report = old.backup(a, b)
        if not report.success:
            raise ValueError(
                "Migration blockiert: bestehende A/B-Sicherung nicht erfolgreich"
            )
        for source in migration.rglob("*"):
            storage.safe_path(source)
            if source.is_file():
                relative = source.relative_to(migration).as_posix()
                if relative == ".protected-service.json":
                    relative = "Archivverwaltung/Migration/alter-dienstmarker.json"
                if ".partial-" in relative or source.name == ".zugpferd-operation.lock":
                    raise ValueError("Migration enthält ungeklärte Dateien")
                storage.verified_copy(
                    source, storage.child(root, relative), storage.sha256(source)
                )
        old_key = (
            migration.parent
            / ("." + migration.name + "-Schluessel")
            / "signing-key.pem"
        )
        if old_key.is_file():
            new_key = (
                root.parent / ("." + root.name + "-Schluessel") / "signing-key.pem"
            )
            storage.verified_copy(old_key, new_key, storage.sha256(old_key))
    archive = ArchiveService(root)
    archive.setup()
    if a and b:
        archive_id = (
            read_marker(a).archive_id if (a / MARKER).exists() else str(uuid4())
        )
        for role, path in (("A", a), ("B", b)):
            if not (path / MARKER).exists():
                register(path, role, archive_id)
        archive.configure(a, b)
        if os.name == "nt":
            storage.write_new(
                root / "Archivverwaltung/Konfiguration/Medienpfade.json",
                storage.canonical(
                    {
                        role: str(path.relative_to(Path(path.anchor)))
                        .replace("\\", "/")
                        .removeprefix(".")
                        for role, path in (("A", a), ("B", b))
                    }
                ),
            )
    storage.write_new(
        root / ".protected-service.json",
        storage.canonical(dict(service=service.SERVICE_NAME, root=str(root))),
    )
