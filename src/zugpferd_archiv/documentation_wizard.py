"""Guided operational documentation: operator inputs, preview and explicit status."""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from .documentation import DocumentationData, FIELD_GROUPS, new_record, render_html


class InputPage(QWizardPage):
    def __init__(self, title: str, fields: list, wizard: DocumentationWizard):
        super().__init__()
        self.setTitle(title)
        self.fields = fields
        self.owner = wizard
        self.setSubTitle(
            "Pflichtangaben sind mit * markiert. Beschreiben Sie die tatsächlich gelebten Abläufe."
        )
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        for key, label, required in fields:
            editor = QPlainTextEdit()
            editor.setMinimumHeight(55)
            editor.setMaximumHeight(85)
            editor.setPlaceholderText(
                "Ihre betriebliche Angabe" + (" (optional)" if not required else "")
            )
            if wizard.initial:
                editor.setPlainText(wizard.initial.values.get(key, ""))
            editor.setReadOnly(wizard.pending)
            editor.textChanged.connect(self.completeChanged.emit)
            wizard.editors[key] = editor
            form.addRow(label + (" *" if required else ""), editor)
        body = QWidget()
        body.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

    def isComplete(self) -> bool:
        return all(
            (not required or self.owner.editors[key].toPlainText().strip())
            and len(self.owner.editors[key].toPlainText()) <= 5000
            for key, _, required in self.fields
        )


class PreviewPage(QWizardPage):
    def __init__(self, wizard: DocumentationWizard):
        super().__init__()
        self.owner = wizard
        self.setTitle("Vorschau und Speichern")
        self.setSubTitle(
            "Neue Fassung speichern; bestehende Fassungen bleiben erhalten."
        )
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Gültig ab:", wizard.valid_from)
        form.addRow(wizard.approved)
        form.addRow("Freigebende Person:", wizard.approved_by)
        layout.addLayout(form)
        layout.addWidget(wizard.preview, 1)
        label = QLabel(
            "Speicherung als druckbare HTML-Datei, Markdown und JSON mit SHA-256-Prüfsummen. "
            "Arbeitsablage: Archivverwaltung/Verfahrensdokumentation/Fassungen/. "
            "Auf A und B: Verfahrensdokumentation/Fassungen/. "
            "HTML im Browser öffnen und bei Bedarf als PDF drucken."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        for signal in (
            wizard.valid_from.dateChanged,
            wizard.approved.toggled,
            wizard.approved_by.textChanged,
        ):
            signal.connect(self.refresh)

    def initializePage(self) -> None:
        self.refresh()

    def refresh(self, *args) -> None:
        self.owner.approved_by.setEnabled(
            self.owner.approved.isChecked() and not self.owner.pending
        )
        if self.isComplete():
            record = self.owner.preview_record or new_record(
                self.owner.documentation_data(),
                self.owner.context,
                self.owner.version,
                document_id="Vorschau – Kennung wird beim Speichern vergeben",
            )
            self.owner.preview.setHtml(render_html(record))
        else:
            self.owner.preview.setPlainText(
                "Für die Freigabe die freigebende Person angeben."
            )
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return not self.owner.approved.isChecked() or bool(
            self.owner.approved_by.text().strip()
        )


class DocumentationWizard(QWizard):
    def __init__(
        self,
        context: dict,
        parent=None,
        initial: DocumentationData | None = None,
        pending: bool = False,
        version: int = 1,
        preview_record: dict | None = None,
    ):
        super().__init__(parent)
        self.context = context
        self.initial = initial
        self.pending = pending
        self.version = version
        self.preview_record = preview_record if pending else None
        self.editors: dict[str, QPlainTextEdit] = {}
        self.setWindowTitle("Assistent für die Verfahrensdokumentation")
        self.resize(860, 760)
        self.setWizardStyle(QWizard.ModernStyle)
        self.setButtonText(QWizard.BackButton, "Zurück")
        self.setButtonText(QWizard.NextButton, "Weiter")
        self.setButtonText(QWizard.CancelButton, "Abbrechen")
        self.setButtonText(QWizard.FinishButton, "Fassung speichern und A/B prüfen")
        for title, fields in FIELD_GROUPS:
            self.addPage(InputPage(title, fields, self))
        self.valid_from = QDateEdit()
        self.valid_from.setCalendarPopup(True)
        self.valid_from.setDisplayFormat("dd.MM.yyyy")
        self.valid_from.setDate(
            QDate.fromString(initial.valid_from, "yyyy-MM-dd")
            if initial
            else QDate.currentDate()
        )
        self.valid_from.setEnabled(not pending)
        self.approved = QCheckBox("Angaben betrieblich geprüft und freigegeben")
        self.approved.setChecked(initial.approved if initial else False)
        self.approved.setEnabled(not pending)
        self.approved_by = QLineEdit(initial.approved_by if initial else "")
        self.approved_by.setMaxLength(500)
        self.approved_by.setReadOnly(pending)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview_page = PreviewPage(self)
        self.addPage(self.preview_page)
        if pending:
            self.setWindowTitle("Ausstehende Dokumentationsfassung abschließen")
            for page_id in self.pageIds():
                self.page(page_id).setSubTitle(
                    "Ausstehende Fassung unverändert erneut auf A/B speichern. "
                    "Danach kann eine neue Fassung erstellt werden."
                )

    def documentation_data(self) -> DocumentationData:
        return DocumentationData(
            {key: editor.toPlainText() for key, editor in self.editors.items()},
            self.valid_from.date().toString("yyyy-MM-dd"),
            self.approved.isChecked(),
            self.approved_by.text(),
        )
