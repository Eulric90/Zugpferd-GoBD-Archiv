from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtWidgets import QDialog, QTabWidget, QTextBrowser, QVBoxLayout


class DocumentView(QDialog):
    def __init__(
        self, path: Path, record: dict, parent=None, *, xml: bytes | None = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Original und strukturierte Rechnungsdaten")
        self.resize(950, 750)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        if path.suffix.casefold() == ".pdf":
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView

            self.pdf = QPdfDocument(self)
            self.pdf.load(str(path))
            view = QPdfView(self)
            view.setDocument(self.pdf)
            view.setPageMode(QPdfView.PageMode.MultiPage)
            tabs.addTab(view, "PDF-Original")
        browser = QTextBrowser()
        browser.setHtml(
            "<h2>Rechnungsdaten / Register</h2>"
            + "".join(
                f"<p><b>{html.escape(key)}</b>: {html.escape(str(value))}</p>"
                for key, value in record.items()
            )
            + "<p>XML ist bei E-Rechnungen führend. Registerkorrekturen verändern das Original nicht.</p>"
        )
        tabs.addTab(browser, "Lesbare Daten")
        if xml:
            raw_view = QTextBrowser()
            from .xml_view import render_xml

            try:
                raw_view.setHtml(render_xml(xml))
            except Exception:
                raw_view.setPlainText(xml.decode("utf-8", errors="replace"))
            tabs.addTab(raw_view, "Führende XML (unverändert)")
        root = path.parents[len(Path(record["original_relative"]).parts) - 1]
        for item in record.get("related_files", []):
            if "XML" in item["kind"]:
                raw_view = QTextBrowser()
                from .xml_view import render_xml

                raw_view.setHtml(render_xml((root / item["path"]).read_bytes()))
                tabs.addTab(raw_view, "Führende XML (extrahiert)")
        if path.suffix.casefold() == ".xml":
            raw = QTextBrowser()
            from .xml_view import render_xml

            try:
                raw.setHtml(render_xml(path.read_bytes()))
            except Exception:
                raw.setPlainText(path.read_bytes().decode("utf-8", errors="replace"))
            tabs.addTab(raw, "XML-Original")
