"""Read-only register browsing with explicit append-only business actions."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QGridLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
)

from .register import Register
from .workflow import export_register, restore_snapshot, retention


class RegisterView(QDialog):
    def __init__(self, root: Path, records: list[dict], parent=None, tasks=None):
        super().__init__(parent)
        self.root, self.records, self.host = root, records, parent
        self.setWindowTitle("Belegregister und offene Aufgaben")
        self.resize(1100, 740)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Nummer, Geschäftspartner, Betrag oder Referenz suchen"
        )
        self.search.textChanged.connect(self.populate)
        layout.addWidget(self.search)
        period = QHBoxLayout()
        self.first, self.last = QLineEdit("0001-01-01"), QLineEdit("9999-12-31")
        for editor in (self.first, self.last):
            editor.setMaxLength(10)
            editor.textChanged.connect(self.populate)
            period.addWidget(editor)
        period.addWidget(QLabel("Rechnungsdatum von / bis (JJJJ-MM-TT)"))
        layout.addLayout(period)
        self.read_only = QCheckBox("Nur lesender Prüfzugriff")
        self.read_only.setChecked(True)
        layout.addWidget(self.read_only)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Nummer",
                "Datum",
                "Partner",
                "Brutto",
                "Status",
                "Sicherung",
                "Aufbewahrung bis",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.details = QTextBrowser()
        layout.addWidget(self.details)
        self.tasks_text = QTextBrowser()
        self.tasks_text.setMaximumHeight(110)
        self.tasks_text.setPlainText(
            "\n".join(str(task) for task in (tasks or []))
            or "Keine technischen Registeraufgaben offen; Portal-/Papierabgleich bleibt erforderlich."
        )
        layout.addWidget(self.tasks_text)
        self.table.itemSelectionChanged.connect(self.describe)
        row = QGridLayout()
        layout.addLayout(row)
        for index, (text, action) in enumerate(
            [
                ("Original / XML anzeigen", self.open_original),
                ("Metadaten korrigieren / Status", self.correct),
                ("Versand bestätigen", self.sent),
                ("Nachweis zuordnen", self.add_related),
                ("Nummernlücke erklären", self.explain_number),
                ("Periodenabgleich protokollieren", self.close_period),
                ("Registerexport / Ausdruck", self.export),
                ("Wiederherstellung in neuen Ordner", self.restore),
            ]
        ):
            button = QPushButton(text)
            button.clicked.connect(action)
            row.addWidget(button, index // 3, index % 3)
        layout.addWidget(
            QLabel(
                "Offene Aufgaben: ungeprüfte Eingänge, nicht bestätigte Ausgänge, A/B-Rückstände und Nummernreservierungen mit dem Portal/Papierregister abgleichen."
            )
        )
        self.populate()

    def populate(self):
        text = self.search.text().casefold()
        self.visible = [
            r
            for r in self.records
            if self.first.text() <= r["invoice_date"] <= self.last.text()
            and text
            in " ".join(
                str(r.get(k, ""))
                for k in (
                    "number",
                    "partner",
                    "gross",
                    "reference",
                    "payment_reference",
                )
            ).casefold()
        ]
        self.table.setRowCount(len(self.visible))
        for index, record in enumerate(self.visible):
            proposal = retention(
                record["invoice_date"],
                record.get("document_type", "Rechnung"),
                record.get("hold", ""),
            )
            for column, value in enumerate(
                [
                    record["number"],
                    record["invoice_date"],
                    record["partner"],
                    record["gross"],
                    record["status"],
                    record["backup_status"],
                    proposal["keep_until"] or "Betrieblich festlegen",
                ]
            ):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def selected(self):
        row = self.table.currentRow()
        return self.visible[row] if 0 <= row < len(self.visible) else None

    def describe(self):
        record = self.selected()
        if record:
            self.details.setHtml(
                "".join(
                    f"<p><b>{html.escape(key)}</b>: {html.escape(str(value))}</p>"
                    for key, value in record.items()
                )
            )

    def mutation(self, action, message):
        if self.read_only.isChecked():
            QMessageBox.information(
                self,
                "Prüfzugriff",
                "Für Bearbeitung ‚Nur lesender Prüfzugriff‘ deaktivieren.",
            )
            return

        def refreshed(result):
            self.records = result["records"]
            self.tasks_text.setPlainText(
                "\n".join(str(task) for task in result["tasks"])
                or "Keine technischen Registeraufgaben offen"
            )
            self.populate()
            QMessageBox.information(self, "Protokolliert", message)

        self.host.launch(
            lambda progress: (
                action(),
                dict(
                    records=Register(self.root).records(),
                    tasks=Register(self.root).tasks(),
                ),
            )[1],
            refreshed,
        )

    def correct(self):
        record = self.selected()
        if not record:
            return
        key, accepted = QInputDialog.getItem(
            self,
            "Korrektur / Beziehung",
            "Feld",
            [
                "partner",
                "number",
                "invoice_date",
                "service_period",
                "reference",
                "payment_reference",
                "hold",
                "related_id",
                "status",
            ],
            0,
            False,
        )
        if not accepted:
            return
        value, accepted = QInputDialog.getText(
            self, "Neuer Wert", key, text=str(record.get(key, ""))
        )
        if not accepted:
            return
        reason, accepted = QInputDialog.getText(
            self, "Begründung", "Korrektur bleibt mit bisherigem Wert erhalten"
        )
        if accepted:
            self.mutation(
                lambda: Register(self.root).correct(record["id"], {key: value}, reason),
                "Änderung angehängt; Original unverändert",
            )

    def sent(self):
        record = self.selected()
        if not record:
            return
        sent_date, accepted = QInputDialog.getText(
            self,
            "Versand",
            "Tatsächliches Versanddatum JJJJ-MM-TT",
            text=date.today().isoformat(),
        )
        if not accepted:
            return
        recipient, accepted = QInputDialog.getText(self, "Versand", "Empfänger")
        if not accepted:
            return
        source, _ = QFileDialog.getOpenFileName(
            self, "Tatsächlich versandten Anhang auswählen (Hash wird verglichen)"
        )
        if source:
            self.mutation(
                lambda: Register(self.root).mark_sent(
                    record["id"], sent_date, recipient, Path(source)
                ),
                "Versand mit identischem Anhang bestätigt; kein Zustellnachweis behauptet",
            )

    def open_original(self):
        record = self.selected()
        if not record:
            return
        from .document_view import DocumentView

        DocumentView(self.root / record["original_relative"], record, self).exec()

    def add_related(self):
        record = self.selected()
        if not record:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Relevanten Beleg oder Mail zuordnen"
        )
        if not filename:
            return
        kind, accepted = QInputDialog.getText(
            self, "Zuordnung", "Begründung / Art des Nachweises"
        )
        if accepted and kind.strip():
            self.mutation(
                lambda: Register(self.root).add_related(
                    record["id"], Path(filename), kind
                ),
                "Nachweis unverändert zugeordnet; A/B-Sicherung erneut ausführen",
            )

    def explain_number(self):
        number, accepted = QInputDialog.getText(
            self, "Nummernlücke", "Reservierte oder fehlende Nummer"
        )
        if not accepted:
            return
        reason, accepted = QInputDialog.getText(
            self, "Begründung", "Was ist mit dieser Nummer geschehen?"
        )
        if accepted:
            self.mutation(
                lambda: Register(self.root).explain_number(number, reason),
                "Lücke begründet; Nummer bleibt gesperrt",
            )

    def close_period(self):
        reason, accepted = QInputDialog.getText(
            self,
            "Tatsächlicher Periodenabgleich",
            "Welche Portal-/Mail-/Papierquellen wurden mit dem Register abgeglichen? Offene Lücken nennen.",
        )
        if accepted:
            self.mutation(
                lambda: Register(self.root).close_period(
                    self.first.text(), self.last.text(), reason
                ),
                "Periodenstand und Abgleichgrundlage protokolliert",
            )

    def export(self):
        first, accepted = QInputDialog.getText(
            self,
            "Belegexport",
            "Rechnungsdatum ab (JJJJ-MM-TT)",
            text=f"{date.today().year}-01-01",
        )
        if not accepted:
            return
        last, accepted = QInputDialog.getText(
            self, "Belegexport", "Rechnungsdatum bis", text=date.today().isoformat()
        )
        if not accepted:
            return
        parent = QFileDialog.getExistingDirectory(
            self, "Übergeordneten Exportordner wählen"
        )
        if parent:
            from uuid import uuid4

            destination = Path(parent) / f"Belegexport-{uuid4()}"
            self.host.launch(
                lambda progress: export_register(
                    Register(self.root), destination, first, last
                ),
                lambda result: QMessageBox.information(
                    self,
                    "Export geprüft",
                    f"{result['count']} Belege: {destination}\nindex.html öffnen und für den Papierordner drucken.",
                ),
            )

    def restore(self):
        source = QFileDialog.getExistingDirectory(
            self, "Signierten Sicherungsstand auswählen (UUID-Ordner)"
        )
        if not source:
            return
        reference, _ = QFileDialog.getOpenFileName(
            self,
            "Unabhängig verwahrten öffentlichen Referenzschlüssel auswählen",
            "",
            "Referenzschlüssel (*.public-key.txt *.txt)",
        )
        if not reference:
            return
        public_key = Path(reference).read_text(encoding="ascii").strip()
        parent = QFileDialog.getExistingDirectory(
            self, "Übergeordneten Wiederherstellungsordner auswählen"
        )
        if parent:
            from uuid import uuid4

            destination = Path(parent) / f"Wiederherstellung-{uuid4()}"
            self.host.launch(
                lambda progress: restore_snapshot(
                    Path(source), destination, public_key
                ),
                lambda result: QMessageBox.information(
                    self,
                    "Wiederherstellung geprüft",
                    f"{destination}\nPrüfkopie: vor Livebetrieb Admin-Rechte und Schlüssel wieder einrichten.",
                ),
            )


class InstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Arbeitsanleitung Rechnungen")
        self.resize(800, 650)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml("""<h1>Rechnungen behandeln</h1>
        <h2>Eingang</h2><ol><li>Originalanhang aus Portal/Thunderbird speichern; PDF oder XML niemals neu drucken oder konvertieren.</li>
        <li>‚Eingangsrechnung übernehmen‘ öffnen, Datei oder EML wählen. Bei mehreren Anhängen jeden Beleg einzeln auswählen.</li>
        <li>Rechnungsdaten und Lieferung/Leistung prüfen. Unklare Belege offen erhalten und beim Lieferanten klären.</li>
        <li>Übernahme bestätigen. Beide USB-Sticks anschließen und ‚Sichern auf A und B‘ starten. Bericht prüfen.</li></ol>
        <h2>Ausgang mit PDF24</h2><ol><li>Jahresserie mit bisherigem Nummernstand bestätigen. Nächste Nummer reservieren und exakt in PDF24 verwenden.</li>
        <li>ZUGFeRD-Original erzeugen. ‚Ausgangsrechnung übernehmen‘ starten; XML/PDF und Leistung persönlich prüfen.</li>
        <li>Freigeben und übernehmen. Exakt die abgelegte Originaldatei über Portal/Thunderbird senden.</li>
        <li>Im Register Versanddatum/Empfänger bestätigen; versandten Anhang zum Hashvergleich auswählen.</li>
        <li>Auf A und B sichern und Bericht prüfen. Bei Fehler bleibt der Vorgang offen.</li></ol>
        <h2>Täglich und monatlich</h2><p>Portal/Mail und Papierregister mit Belegregister abgleichen. Ungeprüfte Eingänge, Versand, Nummernlücken und Sicherungsrückstände klären.
        USB A/B sicher auswerfen; B getrennt lagern. Monatlich Rechnungsdatum-Export mit Originalen erstellen, index.html drucken und Ausdrucke samt Register an Steuerberatung geben.</p>
        <h2>Korrektur und Altbestand</h2><p>Original niemals ersetzen. Berichtigung/Storno als neuen Beleg übernehmen und mit related_id verknüpfen. Metadaten nur begründet korrigieren.
        Elektronische Altoriginale aus Portal nachholen; Scans als Papier-Scan kennzeichnen und Papier aufbewahren. Heutiger Importzeitpunkt bleibt erhalten.</p>
        <h2>Betrieb und Notfall</h2><p>Jeder nutzt sein persönliches Windows-Konto. Geschützten Dienst durch Admin einrichten. Verfahrensdokumentation freigeben und bei Änderungen versionieren.
        Regelmäßig vollständige Integritätsprüfung und Wiederherstellung in neuem Ordner durchführen. Fristvorschläge und Sperrvermerke betrieblich prüfen; die App löscht keine Belege.</p>""")
        layout.addWidget(browser)
        button = QPushButton("Anleitung drucken")

        def print_document():
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter

            printer = QPrinter()
            if QPrintDialog(printer, self).exec() == QDialog.DialogCode.Accepted:
                browser.document().print_(printer)

        button.clicked.connect(print_document)
        layout.addWidget(button)
