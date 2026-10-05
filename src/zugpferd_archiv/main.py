"""Desktop entry point and packaged start-up smoke test."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="GoBD-unterstützende Archivierung")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--service", action="store_true")
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--medium-a", type=Path)
    parser.add_argument("--medium-b", type=Path)
    parser.add_argument("--migrate-from", type=Path)
    parser.add_argument(
        "--smoke-test", action="store_true", help="GUI starten und automatisch beenden"
    )
    args = parser.parse_args()
    if args.service:
        from .windows_service import run

        run()
        return 0
    if args.provision:
        if args.root is None:
            parser.error("--root erforderlich")
        from .windows_service import provision

        provision(args.root, args.medium_a, args.medium_b, args.migrate_from)
        return 0
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .gui import MainWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow(args.root, use_settings=not args.smoke_test)
    window.show()
    if args.smoke_test:
        # Also exercise the packaged wizard and its generated preview. No
        # documentation is saved: the supplied IDs are synthetic test values.
        from . import __version__
        from .documentation import FIELD_GROUPS
        from .documentation_wizard import DocumentationWizard

        ctx = {
            "software_version": __version__,
            "root": str(args.root or Path.cwd()),
            "archive_id": "00000000-0000-0000-0000-000000000001",
            "media": {
                role: {
                    "medium_uuid": role,
                    "volume_id": "test",
                    "path_at_creation": "Starttest",
                }
                for role in ("A", "B")
            },
            "last_backup": None,
        }
        wizard = DocumentationWizard(ctx, window)
        for _, fields in FIELD_GROUPS:
            for key, label, required in fields:
                if required:
                    wizard.editors[key].setPlainText("Starttest: " + label)
        wizard.setStartId(wizard.pageIds()[-1])
        wizard.restart()
        wizard.show()
        from .invoice import RULES, inspect_file
        from .invoice_wizard import InvoiceWizard

        sample = RULES / "sample-cii.xml"
        inspected = inspect_file(sample)
        if inspected["critical_errors"]:
            raise RuntimeError("Gebündelte Offline-Validierung fehlgeschlagen")
        invoice_wizard = InvoiceWizard(sample, "Eingang", inspected, window)
        invoice_wizard.show()

        def finish():
            if window.worker and window.worker.isRunning():
                QTimer.singleShot(100, finish)
            else:
                wizard.close()
                invoice_wizard.close()
                window.close()
                app.quit()

        QTimer.singleShot(500, finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
