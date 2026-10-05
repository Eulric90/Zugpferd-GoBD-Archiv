import pytest

from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.register import Register
from zugpferd_archiv.workflow import export_register, retention, restore_snapshot


def test_retention_holds():
    assert retention("2026-01-01", "Rechnung")["keep_until"] == "2034-12-31"
    assert (
        retention("2026-01-01", "Verfahrensdokumentation")["keep_until"] == "2036-12-31"
    )
    assert retention("2026-01-01", "Rechnung", "Laufende Prüfung")["hold"]


def test_export_formula_defense_and_original_integrity(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"original")
    register = Register(tmp_path / "root", actor="SID")
    register.ingest(
        source,
        dict(
            direction="Eingang",
            number="=1+1",
            partner="@vendor",
            invoice_date="2026-10-01",
            currency="EUR",
            net="100.00",
            tax="19.00",
            gross="119.00",
            source="Portal",
            reviewed=False,
        ),
    )
    result = export_register(register, tmp_path / "export", "2026-01-01", "2026-12-31")
    assert result["verified"]
    csv = (tmp_path / "export/register.csv").read_text(encoding="utf-8-sig")
    assert "'=1+1" in csv and "'@vendor" in csv
    with pytest.raises(ArchiveError):
        export_register(register, tmp_path / "export", "2026-01-01", "2026-12-31")


def test_restore_refuses_existing_destination(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(ArchiveError):
        restore_snapshot(tmp_path / "missing", destination)
