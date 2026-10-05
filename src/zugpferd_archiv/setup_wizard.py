from __future__ import annotations

import platform
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
    QScrollArea,
    QWidget,
)

from .register import actor_identity
from .service import protected


def windows_edition() -> str:
    if platform.system() != "Windows":
        return platform.platform()
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    ) as key:
        return (
            str(winreg.QueryValueEx(key, "ProductName")[0])
            + " / "
            + str(winreg.QueryValueEx(key, "DisplayVersion")[0])
        )


class SetupWizard(QWizard):
    def __init__(self, root: Path, initial: dict | None = None, parent=None):
        super().__init__(parent)
        self.root = root
        self.setWindowTitle("Betrieb und digitalen Start einrichten")
        self.resize(780, 600)
        page = QWizardPage()
        page.setTitle("Zuständigkeiten und Beginn festhalten")
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        self.edition = windows_edition()
        self.actor = actor_identity()
        self.service_protected = protected(root)
        layout.addWidget(
            QLabel(
                f"Windows: {self.edition}\nAktuelles Konto: {self.actor}\n"
                + (
                    "Geschütztes Dienstprofil eingerichtet"
                    if self.service_protected
                    else "Dienstschutz fehlt: vor Livebetrieb Admin-Installation und NTFS-Abnahme durchführen"
                )
            )
        )
        form = QFormLayout()
        self.fields = {}
        initial = initial or {}
        for key, label in dict(
            organization="Unternehmen",
            address="Anschrift",
            vat_id="USt-ID / Steuernummer",
            responsible="Bruder: Hauptverantwortlicher / Windows-Konto",
            deputy="Vertretung / Windows-Konto",
            digital_start="Digitaler Stichtag JJJJ-MM-TT",
            accounting_scope="Buchführung, Steuerberatung und weitere Belegarten",
            location_a="USB A: Kennzeichnung und Aufbewahrungsort",
            location_b="USB B: getrennte Aufbewahrung",
            backup_schedule="Sicherungsrhythmus",
            reconciliation="Vollständigkeitsabgleich",
            recovery_schedule="Wiederherstellungsprobe",
            encryption="Verschlüsselung und Aufbewahrung der Wiederherstellungsschlüssel",
        ).items():
            defaults = dict(
                digital_start=date.today().isoformat(),
                backup_schedule="Täglich bei neuen Daten; beide Medien prüfen",
                reconciliation="Monatlich Portal/Mail und Papier-/Belegregister abgleichen",
                recovery_schedule="Vierteljährlich in neuem Ordner testen",
            )
            editor = QLineEdit(initial.get(key, defaults.get(key, "")))
            self.fields[key] = editor
            form.addRow(label, editor)
        layout.addLayout(form)
        self.confirm = QCheckBox(
            "Angaben geprüft; Papieraltbestand bleibt erhalten und elektronische Originale werden nachgeholt"
        )
        layout.addWidget(self.confirm)
        self.error = QLabel()
        layout.addWidget(self.error)
        self.addPage(page)

    def data(self):
        return {
            key: editor.text().strip() for key, editor in self.fields.items()
        } | dict(
            windows_edition=self.edition,
            authenticated_actor=self.actor,
            service_profile_observed=self.service_protected,
            invoice_program="PDF24 ZUGFeRD",
            mail_program="Provider-Portal / Thunderbird",
            tax_adviser="Papierordner plus neutraler digitaler Original-/Registerexport",
        )

    def validateCurrentPage(self):
        try:
            data = self.data()
            for key in (
                "organization",
                "address",
                "vat_id",
                "responsible",
                "deputy",
                "digital_start",
                "location_a",
                "location_b",
            ):
                if not data[key]:
                    raise ValueError(f"Pflichtangabe fehlt: {key}")
            date.fromisoformat(data["digital_start"])
            if not self.confirm.isChecked():
                raise ValueError("Betriebliche Angaben bestätigen")
            return super().validateCurrentPage()
        except ValueError as exc:
            self.error.setText(str(exc))
            return False
