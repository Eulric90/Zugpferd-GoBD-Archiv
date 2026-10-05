from pathlib import Path

from PySide6.QtWidgets import QApplication

from zugpferd_archiv.invoice_wizard import InvoiceWizard


def test_outgoing_review_and_critical_errors_block_progress():
    app = QApplication.instance() or QApplication([])
    wizard = InvoiceWizard(
        Path("invoice.xml"), "Ausgang", {"critical_errors": ["BR-01"]}
    )
    wizard.show()
    app.processEvents()
    for key, value in dict(
        number="20260001",
        invoice_date="2026-10-01",
        partner="Kunde",
        net="100",
        tax="19",
        gross="119",
        source="PDF24",
    ).items():
        wizard.fields[key].setText(value)
    wizard.reviewed.setChecked(True)
    assert not wizard.validateCurrentPage()
    wizard.historical.setChecked(True)
    assert wizard.validateCurrentPage()
    wizard.close()


def test_wizard_exposes_original_and_complete_xml_preview(monkeypatch):
    from zugpferd_archiv.document_view import DocumentView

    app = QApplication.instance() or QApplication([])
    raw = b"<Invoice><ID>20260001</ID></Invoice>"
    captured = []
    monkeypatch.setattr(
        DocumentView, "exec", lambda self: captured.append(self.windowTitle())
    )
    wizard = InvoiceWizard(
        Path("invoice.pdf"), "Eingang", {"xml": raw, "format": "CII"}
    )
    wizard.preview_button.click()
    assert captured == ["Original und strukturierte Rechnungsdaten"]
    wizard.close()
    app.processEvents()
