import pytest

from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.register import Register


def fields(direction="Eingang", number="4711"):
    return dict(
        direction=direction,
        number=number,
        invoice_date="2026-10-01",
        partner="Lieferant",
        currency="EUR",
        net="100.00",
        tax="19.00",
        gross="119.00",
        source="Portal",
        reviewed=True,
    )


def test_number_reservations_persist_and_exhaust(tmp_path):
    register = Register(tmp_path, actor="test-SID")
    register.start_series(2026, "-", 9998, "Bestehender Nummernstand geprüft")
    assert register.reserve(2026) == "2026-9999"
    with pytest.raises(ArchiveError, match="9999"):
        Register(tmp_path, actor="other-SID").reserve(2026)


def test_import_duplicate_conflict_and_source_unchanged(tmp_path):
    source = tmp_path / "input.pdf"
    source.write_bytes(b"%PDF original")
    register = Register(tmp_path / "archive", actor="test-SID")
    register.start_series(2026, "", 0, "Erstbestand")
    first = register.ingest(source, fields("Ausgang", "20260001"))
    assert register.ingest(source, fields("Ausgang", "20260001"))["id"] == first["id"]
    source.write_bytes(b"%PDF different")
    with pytest.raises(ArchiveError, match="nummer"):
        register.ingest(source, fields("Ausgang", "20260001"))
    assert source.read_bytes() == b"%PDF different"
    assert len(register.records()) == 1


def test_incoming_same_number_different_supplier_and_correction(tmp_path):
    register = Register(tmp_path / "archive", actor="test-SID")
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"first")
    record = register.ingest(source, fields())
    source.write_bytes(b"second")
    register.ingest(source, fields() | {"partner": "Zweiter Lieferant"})
    register.correct(record["id"], {"partner": "Korrigierter Lieferant"}, "Tippfehler")
    assert register.records()[0]["partner"] == "Korrigierter Lieferant"
    assert register.events()[0]["data"]["record"]["partner"] == "Lieferant"
    with pytest.raises(ArchiveError):
        register.correct(record["id"], {"sha256": "wrong"}, "Manipulation")


def test_invalid_totals_and_wrong_send_attachment_are_blocked(tmp_path):
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"first")
    register = Register(tmp_path / "archive", actor="test-SID")
    with pytest.raises(ArchiveError, match="Summen"):
        register.ingest(source, fields() | {"gross": "120.00"})
    register.start_series(2026, "", 0, "Erstbestand")
    record = register.ingest(source, fields("Ausgang", "20260001"))
    source.write_bytes(b"wrong attachment")
    with pytest.raises(ArchiveError, match="Anhang"):
        register.mark_sent(record["id"], "2026-10-02", "kunde@example.com", source)


def test_original_tampering_is_detected(tmp_path):
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"first")
    register = Register(tmp_path / "archive", actor="test-SID")
    record = register.ingest(source, fields())
    (register.root / record["original_relative"]).write_bytes(b"tampered")
    with pytest.raises(ArchiveError, match="Original"):
        register.records()
