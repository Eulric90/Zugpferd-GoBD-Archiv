"""German Windows UI. All filesystem operations run on a worker thread."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QDate, QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .core import ArchiveService
from .errors import ArchiveError
from . import media
from .media import MARKER, read_marker, register
from .reports import Report


class Worker(QThread):
    progress = Signal(str)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, operation: Callable, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self) -> None:
        try:
            self.result.emit(self.operation(self.progress.emit))
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self, root: Path | None = None, use_settings: bool = True):
        super().__init__()
        self.setWindowTitle("Zugpferd Archiv 1.0 – GoBD-unterstützende Archivierung")
        self.resize(940, 740)
        self.settings = QSettings("ZugpferdArchiv", "Desktop") if use_settings else None
        saved = (
            self.settings.value("root", r"C:\Rechnungen")
            if self.settings
            else r"C:\Rechnungen"
        )
        self.root_edit = QLineEdit(str(root or saved))
        self.worker: Worker | None = None
        self.controls: list[QWidget] = []
        self._reports: list[Path] = []
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        title = QLabel("Rechnungen unverändert auf zwei Archivmedien sichern")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin: 8px 0;")
        layout.addWidget(title)
        note = QLabel(
            "GoBD-unterstützende Archivierung. Die Software allein garantiert keine GoBD-Konformität."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(self.root_edit)
        self.controls.append(self.root_edit)
        self._button(row, "Arbeitsordner wählen", self.choose_root)
        self._button(row, "C:\\Rechnungen anlegen", self.default_root)
        self._button(row, "Struktur anlegen", self.setup)
        layout.addLayout(row)
        self.media_combos: dict[str, QComboBox] = {}
        self.media_labels: dict[str, QLabel] = {}
        for role in ("A", "B"):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Archiv {role}:"))
            combo = QComboBox()
            combo.setMinimumWidth(240)
            combo.currentIndexChanged.connect(self.update_media_status)
            self.media_combos[role] = combo
            self.controls.append(combo)
            row.addWidget(combo, 1)
            self._button(
                row,
                "Medium wählen",
                lambda checked=False, r=role: self.choose_medium(r),
            )
            self._button(
                row,
                "Registrieren",
                lambda checked=False, r=role: self.register_medium(r),
            )
            layout.addLayout(row)
            label = QLabel("Nicht ausgewählt")
            label.setWordWrap(True)
            self.media_labels[role] = label
            layout.addWidget(label)
        row = QHBoxLayout()
        self._button(row, "Medien neu suchen", self.refresh)
        self._button(row, "A/B zuordnen und speichern", self.configure)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.backup_button = self._button(
            row, "Sichern auf A und B", lambda: self.run_operation("backup")
        )
        self.check_button = self._button(
            row, "Vollständige Integritätsprüfung", lambda: self.run_operation("check")
        )
        self.compare_button = self._button(
            row, "A/B vergleichen", lambda: self.run_operation("compare")
        )
        layout.addLayout(row)
        self.last_label = QLabel("Letzte Sicherung: noch nicht geladen")
        layout.addWidget(self.last_label)
        export_form = QFormLayout()
        row = QHBoxLayout()
        self.first_year, self.last_year = QSpinBox(), QSpinBox()
        for field in (self.first_year, self.last_year):
            field.setRange(1, 9999)
            field.setValue(date.today().year)
            self.controls.append(field)
            row.addWidget(field)
        row.addWidget(QLabel("Jahre der Quellablage (von / bis)"))
        export_form.addRow("Export:", row)
        row = QHBoxLayout()
        self.date_filter = QCheckBox("Archivierungsdatum zusätzlich filtern (UTC)")
        self.first_date, self.last_date = QDateEdit(), QDateEdit()
        self.first_date.setDate(QDate(date.today().year, 1, 1))
        self.last_date.setDate(QDate.currentDate())
        for field in (self.first_date, self.last_date):
            field.setCalendarPopup(True)
            field.setDisplayFormat("dd.MM.yyyy")
        for field in (self.date_filter, self.first_date, self.last_date):
            row.addWidget(field)
            self.controls.append(field)
        export_form.addRow("", row)
        layout.addLayout(export_form)
        row = QHBoxLayout()
        self.export_button = self._button(row, "Prüfexport erstellen", self.export)
        self._button(row, "Letzten Bericht öffnen", self.open_report)
        layout.addLayout(row)
        self.status = QLabel(
            "Bereit. Medien vor dem Abziehen nach Ende des Laufs sicher auswerfen."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)
        self.refresh()
        self.root_edit.editingFinished.connect(self.root_changed)

    def _button(self, row: QHBoxLayout, text: str, action: Callable) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(action)
        self.controls.append(button)
        row.addWidget(button)
        return button

    def root(self) -> Path:
        text = self.root_edit.text().strip()
        if not text:
            raise ArchiveError("Arbeitsordner fehlt")
        return Path(text)

    def medium(self, role: str) -> Path:
        value = self.media_combos[role].currentData()
        if not value:
            raise ArchiveError(f"Archiv {role} auswählen")
        return Path(value)

    def launch(self, operation: Callable, on_result: Callable | None = None) -> None:
        if self.worker and self.worker.isRunning():
            return
        for control in self.controls:
            control.setEnabled(False)
        self.status.setText("Vorgang läuft … Medien angeschlossen lassen.")
        self.worker = Worker(operation, self)
        self.worker.progress.connect(self.log.append)
        self.worker.result.connect(on_result or self.completed)
        self.worker.error.connect(self.failed)
        self.worker.finished.connect(self.idle)
        self.worker.start()

    def idle(self) -> None:
        for control in self.controls:
            control.setEnabled(True)
        self.update_media_status()

    def failed(self, message: str) -> None:
        self.status.setText("FEHLER: " + message)
        self.log.append("FEHLER: " + message)
        QMessageBox.critical(self, "Vorgang fehlgeschlagen", message)

    def completed(self, value: object) -> None:
        if isinstance(value, Report):
            self.status.setText(
                (
                    "ERFOLGREICH – Warnungen im Bericht prüfen"
                    if value.warnings
                    else "ERFOLGREICH"
                )
                if value.success
                else "FEHLER / UNVOLLSTÄNDIG – Bericht prüfen"
            )
            self.log.append(value.text())
            if value.report_text:
                self._reports.append(value.report_text)
            if value.operation == "backup":
                self.last_label.setText(
                    f"Letzter Lauf: {value.timestamp} | {'erfolgreich' if value.success else 'fehlgeschlagen'} | "
                    f"Dateien: {value.totals['candidates']} | verifiziert: {value.totals['verified']}"
                )
            if value.success:
                QMessageBox.information(
                    self,
                    "Vorgang abgeschlossen",
                    f"{value.operation}: erfolgreich. Bericht: {value.report_text}",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Vorgang unvollständig",
                    "Keine vollständige Erfolgsmeldung. Details und Ausnahmen stehen im Bericht.",
                )
        else:
            self.status.setText(str(value or "Abgeschlossen"))
            self.log.append(str(value or "Abgeschlossen"))

    def choose_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Arbeitsordner wählen", self.root_edit.text()
        )
        if path:
            self.root_edit.setText(path)
            self.root_changed()

    def root_changed(self) -> None:
        if self.settings:
            self.settings.setValue("root", self.root_edit.text())
        self.refresh()

    def default_root(self) -> None:
        self.root_edit.setText(r"C:\Rechnungen")
        self.root_changed()
        self.setup()

    def setup(self) -> None:
        try:
            root = self.root()

            def operation(progress):
                ArchiveService(root, progress).setup()
                return "Arbeitsstruktur angelegt; vorhandene Inhalte bleiben erhalten."

            self.launch(operation)
        except ArchiveError as exc:
            self.failed(str(exc))

    def _add_medium(self, role: str, path: Path) -> None:
        combo = self.media_combos[role]
        index = combo.findData(str(path))
        if index < 0:
            combo.addItem(str(path), str(path))
            index = combo.count() - 1
        combo.setCurrentIndex(index)

    def choose_medium(self, role: str) -> None:
        path = QFileDialog.getExistingDirectory(
            self, f"Archivmedium {role} wählen (Laufwerkswurzel)"
        )
        if path:
            self._add_medium(role, Path(path))
            self.update_media_status()

    def refresh(self) -> None:
        try:
            root = self.root()
        except ArchiveError as exc:
            self.failed(str(exc))
            return
        previous = {
            role: combo.currentData() for role, combo in self.media_combos.items()
        }

        # Discovery and configuration reads can block on removed network volumes.
        def operation(progress):
            service = ArchiveService(root, progress)
            if root.is_dir():
                service.setup()
            drives = media.discover()
            try:
                config = service.configuration()
            except ArchiveError:
                config = None
            try:
                last = service.last_backup()
            except (ArchiveError, OSError):
                last = None
            matches = []
            for drive in drives:
                try:
                    marker = read_marker(drive.root)
                    if (
                        config
                        and marker.medium_uuid == config[marker.role]["medium_uuid"]
                    ):
                        matches.append((marker.role, drive.root))
                except ArchiveError:
                    continue
            return drives, matches, last

        def loaded(value):
            drives, matches, last = value
            for role, combo in self.media_combos.items():
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("Medium auswählen", None)
                for drive in drives:
                    combo.addItem(drive.label, str(drive.root))
                combo.blockSignals(False)
                if previous[role]:
                    self._add_medium(role, Path(previous[role]))
            for role, path in matches:
                self._add_medium(role, path)
            if last:
                self.last_label.setText(
                    f"Letzter Sicherungslauf: {last['timestamp']} | "
                    f"{'erfolgreich' if last['success'] else 'fehlgeschlagen'} | "
                    f"Dateien: {last['totals']['candidates']} | "
                    f"verifiziert: {last['totals']['verified']}"
                )
            else:
                self.last_label.setText("Keine vollständige letzte Sicherung bekannt")
            self.status.setText("Bereit")

        self.launch(operation, loaded)

    def update_media_status(self) -> None:
        # Display paths only here; marker I/O belongs in workers, avoiding UI freezes.
        for role, label in self.media_labels.items():
            value = self.media_combos[role].currentData()
            label.setText(
                f"{role}: {value or 'Nicht ausgewählt'} – Kennung wird vor jedem Vorgang geprüft"
            )

    def register_medium(self, role: str) -> None:
        try:
            root, path = self.root(), self.medium(role)
            service = ArchiveService(root)
            # Registration writes only the selected medium, after explicit role selection.
            other = self.media_combos["B" if role == "A" else "A"].currentData()

            def operation(progress):
                service._separate(path, path)
                identity = None
                try:
                    config = service.configuration()
                    identity = config["archive_id"]
                except ArchiveError:
                    if other and (Path(other) / MARKER).exists():
                        identity = read_marker(Path(other)).archive_id
                medium = register(path, role, identity)
                return f"Archiv {role} registriert: Archiv-ID {medium.archive_id}, Medien-UUID {medium.medium_uuid}"

            self.launch(operation)
        except (ArchiveError, OSError) as exc:
            self.failed(str(exc))

    def configure(self) -> None:
        try:
            root, a, b = self.root(), self.medium("A"), self.medium("B")

            def operation(progress):
                ArchiveService(root, progress).configure(a, b)
                return "A/B sicher zugeordnet. Medien werden anhand ihrer Kennungen wiedererkannt."

            self.launch(operation)
        except ArchiveError as exc:
            self.failed(str(exc))

    def run_operation(self, name: str) -> None:
        try:
            root, a, b = self.root(), self.medium("A"), self.medium("B")
            self.launch(
                lambda progress: getattr(ArchiveService(root, progress), name)(a, b)
            )
        except ArchiveError as exc:
            self.failed(str(exc))

    def export(self) -> None:
        try:
            root, a, b = self.root(), self.medium("A"), self.medium("B")
            parent = QFileDialog.getExistingDirectory(
                self, "Übergeordneten Exportordner wählen"
            )
            if not parent:
                return
            from uuid import uuid4

            destination = (
                Path(parent) / f"Pruefexport-{date.today()}-{str(uuid4())[:8]}"
            )
            first, last = self.first_year.value(), self.last_year.value()
            first_date = (
                self.first_date.date().toPython()
                if self.date_filter.isChecked()
                else None
            )
            last_date = (
                self.last_date.date().toPython()
                if self.date_filter.isChecked()
                else None
            )
            self.launch(
                lambda progress: ArchiveService(root, progress).export(
                    a, b, destination, first, last, first_date, last_date
                )
            )
        except ArchiveError as exc:
            self.failed(str(exc))

    def open_report(self) -> None:
        if self._reports:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._reports[-1])))

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            event.ignore()
            self.status.setText("Vorgang läuft. Fenster erst nach Abschluss schließen.")
        else:
            event.accept()
