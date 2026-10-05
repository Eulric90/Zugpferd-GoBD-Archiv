"""Guided business review: input files are never changed by the wizard."""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextBrowser,
    QVBoxLayout,
    QWizard,
    QWizardPage,
    QScrollArea,
    QWidget,
)


class InvoiceWizard(QWizard):
    def __init__(self, source: Path, direction: str, extracted: dict, parent=None):
        super().__init__(parent)
        self.source = source
        self.direction = direction
        self.extracted = extracted
        self.setWindowTitle(f"{direction}: Rechnung übernehmen")
        self.resize(820, 680)
        page = QWizardPage()
        page.setTitle("Original und Rechnungsdaten prüfen")
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.addWidget(
            QLabel(
                f"Original: {source.name}\nFormat: {extracted.get('format', '')}\nProfil: {extracted.get('profile', '')}"
            )
        )
        self.errors = QTextBrowser()
        self.errors.setPlainText(
            "\n".join(extracted.get("critical_errors", []))
            or "Keine kritischen technischen Fehler gemeldet. Inhalt und PDF/XML-Darstellung persönlich gegenprüfen."
        )
        layout.addWidget(self.errors)
        form = QFormLayout()
        self.fields = {}
        labels = dict(
            number="Rechnungsnummer",
            invoice_date="Rechnungsdatum (JJJJ-MM-TT)",
            partner="Lieferant" if direction == "Eingang" else "Kunde",
            currency="Währung",
            net="Netto",
            tax="Steuer gesamt",
            gross="Brutto",
            service_period="Leistungsdatum/-zeitraum",
            source="Herkunft / Portal / Mail",
            received_at="Empfangsdatum (falls bekannt)",
            reference="Geschäftsvorfall / Buchungsreferenz",
            payment_reference="Zahlungsreferenz",
            related_id="Beleg-ID der ursprünglichen Rechnung (Storno/Berichtigung)",
        )
        for key, label in labels.items():
            value = extracted.get(key, "")
            if key == "partner":
                value = extracted.get(
                    "seller" if direction == "Eingang" else "buyer", value
                )
            if key == "currency" and not value:
                value = "EUR"
            field = QLineEdit(str(value))
            self.fields[key] = field
            form.addRow(label, field)
        self.document_type = QComboBox()
        self.document_type.addItems(
            [
                "Rechnung",
                "Storno",
                "Berichtigung",
                "Gutschrift",
                "Buchungsbeleg",
                "Geschäftsbrief",
                "Papier-Scan",
                "Sonstiger Beleg",
            ]
        )
        form.addRow("Dokumentart", self.document_type)
        layout.addLayout(form)
        self.historical = QCheckBox(
            "Bereits versandter Altbeleg / Papierbestand: historischer Import, heutiger Übernahmezeitpunkt"
        )
        self.reviewed = QCheckBox(
            "Inhalt sachlich geprüft; bei PDF/XML beide Darstellungen gegengeprüft"
        )
        layout.addWidget(self.historical)
        layout.addWidget(self.reviewed)
        self.validation = QLabel()
        self.validation.setWordWrap(True)
        layout.addWidget(self.validation)
        self.backup_now = QCheckBox(
            "Nach Übernahme automatisch auf die ausgewählten Medien A und B sichern"
        )
        self.backup_now.setChecked(True)
        layout.addWidget(self.backup_now)
        self.addPage(page)
        summary = QWizardPage()
        summary.setTitle("Übernahme bestätigen")
        sl = QVBoxLayout(summary)
        self.summary = QTextBrowser()
        sl.addWidget(self.summary)
        sl.addWidget(
            QLabel(
                "Mit Fertigstellen wird das Original unverändert lokal übernommen.\nEine gewählte automatische USB-Sicherung gilt erst nach Prüfung von A und B als erfolgreich."
            )
        )
        self.addPage(summary)

    def data(self) -> dict:
        return {key: field.text().strip() for key, field in self.fields.items()} | dict(
            direction=self.direction,
            document_type=self.document_type.currentText(),
            reviewed=self.reviewed.isChecked(),
            historical=self.historical.isChecked(),
            format=self.extracted.get("format"),
            profile=self.extracted.get("profile"),
            validator_version=self.extracted.get("validator_version"),
            critical_errors=self.extracted.get("critical_errors", []),
            tax_breakdown=self.extracted.get("tax_breakdown", []),
        )

    def validateCurrentPage(self) -> bool:
        if self.currentId() == 0:
            from datetime import date
            from .register import amount

            try:
                data = self.data()
                for key in ("number", "invoice_date", "partner", "currency", "source"):
                    if not data[key]:
                        raise ValueError(f"Pflichtangabe fehlt: {key}")
                date.fromisoformat(data["invoice_date"])
                if amount(data["net"]) + amount(data["tax"]) != amount(data["gross"]):
                    raise ValueError("Netto plus Steuer muss Brutto entsprechen")
                if (
                    self.direction == "Ausgang"
                    and not data["historical"]
                    and (not data["reviewed"] or data["critical_errors"])
                ):
                    raise ValueError(
                        "Neue Ausgangsrechnung braucht sachliche Freigabe ohne kritische technische Fehler"
                    )
                self.summary.setHtml(
                    "<h2>Übernahme</h2>"
                    + "".join(
                        f"<p><b>{html.escape(key)}:</b> {html.escape(str(value))}</p>"
                        for key, value in data.items()
                    )
                    + "<p>Original bleibt unverändert. Offene Eingänge müssen später geklärt werden. Kein automatischer Mailversand.</p>"
                )
            except Exception as exc:
                self.validation.setText(str(exc))
                return False
        return super().validateCurrentPage()
