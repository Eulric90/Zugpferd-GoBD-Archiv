"""Desktop entry point and packaged start-up smoke test."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description='GoBD-unterstützende Archivierung')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--smoke-test', action='store_true', help='GUI starten und automatisch beenden')
    args = parser.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .gui import MainWindow
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow(args.root, use_settings=not args.smoke_test)
    window.show()
    if args.smoke_test:
        def finish():
            if window.worker and window.worker.isRunning():
                QTimer.singleShot(100, finish)
            else:
                window.close()
                app.quit()
        QTimer.singleShot(500, finish)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
