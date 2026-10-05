"""German Windows UI. All filesystem operations run on a worker thread."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QDate, QSettings, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
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
    QInputDialog,
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
        self.setAcceptDrops(True)
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
        self.protection_label = QLabel("Schutzprofil wird geprüft …")
        self.protection_label.setWordWrap(True)
        layout.addWidget(self.protection_label)
        row = QHBoxLayout()
        row.addWidget(self.root_edit)
        self.controls.append(self.root_edit)
        self._button(row, "Arbeitsordner wählen", self.choose_root)
        self._button(row, "C:\\Rechnungen anlegen", self.default_root)
        self._button(row, "Struktur anlegen", self.setup)
        layout.addLayout(row)
        row = QHBoxLayout()
        self._button(
            row, "Eingangsrechnung übernehmen", lambda: self.import_invoice("Eingang")
        )
        self._button(
            row, "Ausgangsrechnung übernehmen", lambda: self.import_invoice("Ausgang")
        )
        self._button(row, "Belegregister / offene Aufgaben", self.show_register)
        layout.addLayout(row)
        row = QHBoxLayout()
        self._button(row, "Jahresserie einrichten", self.configure_series)
        self._button(row, "Nächste Nummer reservieren", self.reserve_number)
        self._button(row, "Arbeitsanleitung", self.open_instructions)
        self._button(row, "Betrieb einrichten", self.business_setup)
        self._button(row, "Schlüssel geschützt sichern", self.backup_key)
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
        row = QHBoxLayout()
        self.documentation_button = self._button(
            row, "Verfahrensdokumentation erstellen", self.documentation
        )
        self._button(row, "Gespeicherte Dokumentation öffnen", self.open_documentation)
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

    def import_invoice(self, direction: str, selected_file: str | None = None) -> None:
        from .invoice import mail_attachments
        from .inspection import analyze_bounded
        from .invoice_wizard import InvoiceWizard
        from .register import Register
        from . import storage
        import tempfile

        selected = selected_file
        if selected is None:
            selected, _ = QFileDialog.getOpenFileName(
                self,
                "Originalrechnung oder Mail auswählen",
                "",
                "Rechnungen und Mails (*.pdf *.xml *.eml);;Alle Dateien (*)",
            )
        if not selected:
            return
        original = Path(selected)
        temporary = tempfile.TemporaryDirectory(prefix="zugpferd-import-")
        staging = Path(temporary.name)
        root = self.root()

        def prepare(progress):
            source = original
            items = None
            if original.suffix.casefold() == ".eml":
                items = mail_attachments(original.read_bytes())
                return dict(items=items)
            return dict(source=source, extracted=analyze_bounded(source))

        def show(value):
            if "items" in value:
                items = value["items"]
                if not items:
                    self.failed("Keine Mailanhänge gefunden")
                    temporary.cleanup()
                    return
                labels = [
                    f"{index + 1}: {item['filename']} ({len(item['content'])} Bytes)"
                    for index, item in enumerate(items)
                ]
                selection, accepted = QInputDialog.getItem(
                    self,
                    "Mailanhang auswählen",
                    "Jeden Beleg einzeln übernehmen. Mail wird zugeordnet gespeichert.",
                    labels,
                    0,
                    False,
                )
                if not accepted:
                    temporary.cleanup()
                    return
                item = items[labels.index(selection)]
                source = storage.child(staging, item["filename"])
                storage.write_new(source, item["content"])
                self.launch(
                    lambda progress: dict(
                        source=source, extracted=analyze_bounded(source)
                    ),
                    show,
                )
                return
            source = value["source"]
            extracted = value["extracted"]
            wizard = InvoiceWizard(source, direction, extracted, self)
            if wizard.exec() != QDialog.DialogCode.Accepted:
                temporary.cleanup()
                return
            fields = wizard.data()
            automatic_backup = wizard.backup_now.isChecked()
            try:
                media_pair = (self.medium("A"), self.medium("B"))
            except ArchiveError:
                media_pair = None

            def commit(progress):
                register = Register(root)
                record = register.ingest(source, fields)
                if original.suffix.casefold() == ".eml":
                    register.add_related(
                        record["id"], original, "Transportmail mit ausgewähltem Beleg"
                    )
                if extracted.get("xml"):
                    xml = staging / "strukturierte-rechnung.xml"
                    storage.write_new(xml, extracted["xml"])
                    register.add_related(
                        record["id"], xml, "Extrahierte XML; Original unverändert"
                    )
                temporary.cleanup()
                report = (
                    ArchiveService(root, progress).backup(*media_pair)
                    if automatic_backup and media_pair
                    else None
                )
                return record, report

            def committed(value):
                record, report = value
                secured = bool(report and report.success)
                if report:
                    self.completed(report)
                self.status.setText(
                    f"Lokal übernommen: {record['number']} – "
                    + (
                        "A und B verifiziert"
                        if secured
                        else "A/B-Sicherung ausstehend; Bericht prüfen"
                    )
                )
                self.log.append(
                    f"Beleg-ID {record['id']} / {record['original_relative']}"
                )
                QMessageBox.information(
                    self,
                    "Übernommen",
                    "Original unverändert lokal abgelegt.\n"
                    + (
                        "Automatisch auf A und B gesichert und rückgelesen.\n"
                        if secured
                        else "Sicherung offen: beide USB-Medien anschließen und ‚Sichern auf A und B‘ ausführen.\n"
                    )
                    + "Ausgänge: exakt diese abgelegte Originaldatei versenden, danach Versand im Register bestätigen.",
                )

            self.launch(commit, committed)

        self.launch(prepare, show)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(
            url.isLocalFile() for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) != 1 or (self.worker and self.worker.isRunning()):
            return
        direction, accepted = QInputDialog.getItem(
            self, "Beleg übernehmen", "Richtung", ["Eingang", "Ausgang"], 0, False
        )
        if accepted:
            self.import_invoice(direction, urls[0].toLocalFile())
            event.acceptProposedAction()

    def configure_series(self):
        from .register import Register

        year, accepted = QInputDialog.getInt(
            self, "Jahresserie", "Jahr", date.today().year, 1, 9999
        )
        if not accepted:
            return
        separator, accepted = QInputDialog.getItem(
            self,
            "Bestehendes Nummernformat",
            "Bisheriges Trennzeichen beibehalten",
            ["Keines (20260001)", "- (2026-0001)", "/ (2026/0001)", ". (2026.0001)"],
            0,
            False,
        )
        if not accepted:
            return
        last, accepted = QInputDialog.getInt(
            self,
            "Bisheriger Nummernstand",
            "Letzte tatsächlich vergebene laufende Nummer; NICHT neu bei 0001 beginnen",
            0,
            0,
            9999,
        )
        if not accepted:
            return
        reason, accepted = QInputDialog.getText(
            self, "Bestätigung", "Grundlage des geprüften Nummernstands"
        )
        if accepted:
            root = self.root()
            sep = {"K": "", "-": "-", "/": "/", ".": "."}[separator[0]]
            self.launch(
                lambda progress: Register(root).start_series(year, sep, last, reason),
                lambda result: self.status.setText("Jahresserie bestätigt"),
            )

    def reserve_number(self):
        from .register import Register

        year, accepted = QInputDialog.getInt(
            self, "Nummer reservieren", "Jahr", date.today().year, 1, 9999
        )
        if accepted:
            root = self.root()
            self.launch(
                lambda progress: Register(root).reserve(year),
                lambda number: QMessageBox.information(
                    self,
                    "Dauerhaft reserviert",
                    f"In PDF24 verwenden: {number}\nDiese Nummer wird auch nach Abbruch nicht wieder vergeben.",
                ),
            )

    def show_register(self):
        from .register import Register
        from .register_view import RegisterView

        root = self.root()
        self.launch(
            lambda progress: dict(
                records=Register(root).records(), tasks=Register(root).tasks()
            ),
            lambda result: RegisterView(
                root, result["records"], self, result["tasks"]
            ).exec(),
        )

    def open_instructions(self):
        from .register_view import InstructionsDialog

        InstructionsDialog(self).exec()

    def business_setup(self):
        from .register import Register
        from .setup_wizard import SetupWizard

        root = self.root()

        def show(initial):
            wizard = SetupWizard(root, initial["values"] if initial else None, self)
            if wizard.exec() == QDialog.DialogCode.Accepted:
                values = wizard.data()
                self.launch(
                    lambda progress: Register(root).save_setup(values),
                    lambda result: self.status.setText(
                        "Betriebsangaben unverändert versioniert; Jahresserie separat bestätigen"
                    ),
                )

        self.launch(lambda progress: Register(root).business_setup(), show)

    def backup_key(self):
        from .service import protected, request
        from .snapshots import export_key
        import base64
        from . import storage

        root = self.root()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Neue verschlüsselte Schlüsselsicherung", "Archivschluessel.pem"
        )
        if not filename:
            return
        password, accepted = QInputDialog.getText(
            self,
            "Schlüsselsicherung",
            "Mindestens 12 Zeichen; Passwort getrennt sicher verwahren",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return

        def save(progress):
            if protected(root):
                content = base64.b64decode(
                    request(dict(operation="export_key", password=password))
                )
                storage.write_new(Path(filename), content)
                from cryptography.hazmat.primitives import serialization

                key = serialization.load_pem_private_key(
                    content, password=password.encode()
                )
                public = base64.b64encode(
                    key.public_key().public_bytes(
                        serialization.Encoding.Raw, serialization.PublicFormat.Raw
                    )
                )
                storage.write_new(Path(filename + ".public-key.txt"), public + b"\n")
                return storage.sha256(Path(filename))
            digest = export_key(
                root.parent / ("." + root.name + "-Schluessel"),
                Path(filename),
                password,
            )
            from cryptography.hazmat.primitives import serialization

            content = Path(filename).read_bytes()
            key = serialization.load_pem_private_key(
                content, password=password.encode()
            )
            public = base64.b64encode(
                key.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
            )
            storage.write_new(Path(filename + ".public-key.txt"), public + b"\n")
            return digest

        self.launch(
            save,
            lambda digest: QMessageBox.information(
                self,
                "Schlüssel verschlüsselt gesichert",
                f"SHA-256: {digest}\nPasswort und Referenzschlüssel getrennt von den drei Archivkopien verwahren.",
            ),
        )

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

        def deliver(value, worker=self.worker):
            if worker.isRunning():
                QTimer.singleShot(10, lambda: deliver(value, worker))
                return
            (on_result or self.completed)(value)

        self.worker.result.connect(deliver)
        self.worker.error.connect(self.failed)
        self.worker.finished.connect(lambda worker=self.worker: self.idle(worker))
        self.worker.start()

    def idle(self, worker: Worker | None = None) -> None:
        if worker is not None and worker is not self.worker:
            return
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
            for output in value.outputs:
                self.log.append(f"Dokumentation: {output}")
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
                    (
                        "Dokumentationsfassung lokal sowie auf A/B gespeichert und verifiziert.\n"
                        + next((p for p in value.outputs if p.endswith(".html")), "")
                        if value.operation == "documentation"
                        else f"{value.operation}: erfolgreich. Bericht: {value.report_text}"
                    ),
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
            import json
            from .service import protected

            hints = {}
            hints_path = root / "Archivverwaltung/Konfiguration/Medienpfade.json"
            if hints_path.is_file():
                hints = json.loads(hints_path.read_text(encoding="utf-8"))
            for drive in drives:
                for role, relative in hints.items():
                    try:
                        from .storage import child

                        candidate = (
                            child(drive.root, relative) if relative else drive.root
                        )
                        marker = read_marker(candidate)
                        if config and marker.medium_uuid == config[role]["medium_uuid"]:
                            matches.append((role, candidate))
                    except ArchiveError:
                        continue
                try:
                    marker = read_marker(drive.root)
                    if (
                        config
                        and marker.medium_uuid == config[marker.role]["medium_uuid"]
                    ):
                        matches.append((marker.role, drive.root))
                except ArchiveError:
                    continue
            return drives, matches, last, protected(root)

        def loaded(value):
            drives, matches, last, is_protected = value
            self.protection_label.setText(
                "Geschütztes Windows-Dienstprofil: Bediener erhalten nur Leserechte auf übernommene Belege."
                if is_protected
                else "Portabler Modus ohne NTFS-Dienstschutz. Vor dem Livebetrieb geschützte Admin-Installation und Abnahme durchführen."
            )
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

    def documentation(self) -> None:
        try:
            root, a, b = self.root(), self.medium("A"), self.medium("B")

            def prepare(progress):
                from .documentation import context, load_latest

                service = ArchiveService(root, progress)
                service.setup()
                service._pair(a, b, Report("documentation_prepare"))
                return context(service, a, b), load_latest(root, include_pending=True)

            def show(value):
                from .documentation import DocumentationData, answers_from
                from .documentation_wizard import DocumentationWizard

                ctx, latest = value
                pending = bool(latest and not latest["completed"])
                initial = answers_from(latest) if latest else None
                if initial is None:
                    from .register import Register

                    setup = Register(root).business_setup()
                    if setup:
                        values = setup["values"]
                        initial = DocumentationData(
                            {
                                key: str(values.get(key, ""))
                                for key in (
                                    "organization",
                                    "address",
                                    "responsible",
                                    "deputy",
                                    "vat_id",
                                    "digital_start",
                                    "location_a",
                                    "location_b",
                                    "backup_schedule",
                                )
                            }
                            | dict(
                                scope=str(values.get("accounting_scope", "")),
                                receipt_process="Originale aus Provider-Portal/Thunderbird; Eingangsassistent, sachliche Prüfung, lokale Übernahme, A/B-Rücklesesicherung; Unklarheiten offen klären.",
                                outgoing_process="PDF24-ZUGFeRD; reservierte Nummer, XML/PDF gegenprüfen, Ausgangsassistent und Freigabe; exaktes Original manuell mailen und Versand mit Hashvergleich bestätigen.",
                                numbering="Jahr und vier Stellen; bestehendes Trennzeichen/letzten Stand bestätigen. Reservierungen werden nicht wieder vergeben; Lücken begründen.",
                                mail_process="Einzelne Rechnung/EML auswählen. Mehrere Rechnungsanhänge getrennt übernehmen; relevante Mail zuordnen. Kein automatischer Versand.",
                                completeness_control=str(
                                    values.get("reconciliation", "")
                                ),
                                access_control="Persönliche Standardkonten; authentifizierter Windows-Schreibdienst und NTFS-Leserechte. Admin-Abnahme und Schutz der getrennten Signaturschlüssel erforderlich.",
                                retention_policy="Fristvorschläge je Dokumentart ab Jahresende prüfen, offene Prüfungen/Sperrvermerke beachten; keine Archivlöschfunktion.",
                                integrity_schedule="Vollprüfung von A/B und signierten Abschlüssen regelmäßig; Berichte prüfen, Referenzschlüssel getrennt verwahren.",
                                incident_process="Fehler nicht als Erfolg behandeln; Originale erhalten, Vorgang mit gleichen Daten fortsetzen; Medien sicher auswerfen.",
                                change_process="Originale nie ersetzen. Neue Storno-/Berichtigungsbelege verknüpfen; Metadaten begründet als Ereignis korrigieren.",
                                export_process="Neutraler Register-/Originalexport nach Rechnungsdatum; index.html und Rechnungen für Steuerberater-Papierordner drucken. Archivdatum ist separater Filter.",
                                recovery_process=str(
                                    values.get("recovery_schedule", "")
                                )
                                + "; isolierter neuer Ordner; Schlüssel verschlüsselt sichern, Dienst/NTFS vor Livebetrieb neu einrichten.",
                            )
                        )
                if initial and not pending:
                    initial = DocumentationData(initial.values, approved=False)
                wizard = DocumentationWizard(
                    ctx,
                    self,
                    initial=initial,
                    pending=pending,
                    version=latest["version"] + (0 if pending else 1) if latest else 1,
                    preview_record=latest,
                )
                if wizard.exec() == QDialog.DialogCode.Accepted:
                    data = wizard.documentation_data()
                    self.launch(
                        lambda progress: ArchiveService(
                            root, progress
                        ).create_documentation(a, b, data)
                    )
                else:
                    self.status.setText(
                        "Dokumentationsassistent abgebrochen; keine Fassung gespeichert."
                    )

            self.launch(prepare, show)
        except ArchiveError as exc:
            self.failed(str(exc))

    def open_documentation(self) -> None:
        try:
            root = self.root()

            def operation(progress):
                from .documentation import LOCAL_BASE, load_latest

                latest = load_latest(root)
                if not latest:
                    raise ArchiveError(
                        "Noch keine vollständig gespeicherte Dokumentationsfassung vorhanden"
                    )
                return (
                    root
                    / LOCAL_BASE
                    / latest["document_id"]
                    / "Verfahrensdokumentation.html"
                )

            def opened(path):
                from PySide6.QtCore import QUrl
                from PySide6.QtGui import QDesktopServices

                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                self.status.setText(f"Dokumentation geöffnet: {path}")

            self.launch(operation, opened)
        except ArchiveError as exc:
            self.failed(str(exc))

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            event.ignore()
            self.status.setText("Vorgang läuft. Fenster erst nach Abschluss schließen.")
        else:
            event.accept()
