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


def test_export_includes_readable_leading_xml(tmp_path):
    from pathlib import Path
    from zugpferd_archiv.inspection import analyze_bounded
    from zugpferd_archiv import storage

    source = Path(__file__).parent / "fixtures/en16931-cii.xml"
    parsed = analyze_bounded(source)
    register = Register(tmp_path / "root", actor="SID")
    record = register.ingest(
        source,
        dict(direction="Eingang", partner="Lieferant", source="Portal", reviewed=True)
        | {
            k: parsed[k]
            for k in ("number", "invoice_date", "currency", "net", "tax", "gross")
        },
    )
    export_register(register, tmp_path / "export", "0001-01-01", "9999-12-31")
    view = tmp_path / "export/Lesbare-XML" / (record["id"] + ".html")
    assert view.is_file() and "XML" in view.read_text()
    assert "XML-Ansicht" in (tmp_path / "export/index.html").read_text()
    assert storage.sha256(source) == record["sha256"]


def test_latest_recovery_can_continue_backups_with_restored_key(tmp_path):
    from zugpferd_archiv.core import ArchiveService
    from zugpferd_archiv.media import register
    from zugpferd_archiv.snapshots import FOLDER, export_key, restore_key
    import json

    root, a, b = (tmp_path / name for name in ("root", "A", "B"))
    for folder in (root, a, b):
        folder.mkdir()
    archive = ArchiveService(root)
    archive.setup()
    marker = register(a, "A")
    register(b, "B", marker.archive_id)
    archive.configure(a, b)
    Register(root, actor="SID").start_series(2026, "", 0, "Baseline")
    assert archive.backup(a, b).success
    assert archive.backup(a, b).success
    events = Register(root, actor="SID").events()
    identity = [
        e["data"]["snapshot"]
        for e in events
        if e["event"] == "register_backup_verified"
    ][-1]
    snapshot = root / FOLDER / identity
    public = json.loads((snapshot / "manifest.json").read_text())["public_key"]
    recovered = tmp_path / "recovered"
    restore_snapshot(snapshot, recovered, public)
    encrypted = tmp_path / "encrypted.pem"
    export_key(
        tmp_path / ".root-Schluessel", encrypted, "separate-password-for-recovery"
    )
    restore_key(
        tmp_path / ".recovered-Schluessel",
        encrypted,
        "separate-password-for-recovery",
        public,
    )
    assert ArchiveService(recovered).backup(a, b).success


def test_recovery_does_not_repair_missing_reference_object_on_other_medium(tmp_path):
    import json
    from zugpferd_archiv.snapshots import (
        create_snapshot,
        replicate_snapshot,
        audit_snapshots,
        export_key,
        restore_key,
        MEDIA_FOLDER,
    )

    root, a, b = (tmp_path / name for name in ("root", "A", "B"))
    for folder in (root, a, b):
        folder.mkdir()
    (root / "original.pdf").write_bytes(b"original")
    snapshot = create_snapshot(root, tmp_path / ".root-Schluessel")
    replicate_snapshot(snapshot, a, b)
    public = json.loads((snapshot / "manifest.json").read_text())["public_key"]
    recovered = tmp_path / "recovered"
    restore_snapshot(snapshot, recovered, public)
    encrypted = tmp_path / "encrypted.pem"
    export_key(tmp_path / ".root-Schluessel", encrypted, "separate-recovery-password")
    restore_key(
        tmp_path / ".recovered-Schluessel",
        encrypted,
        "separate-recovery-password",
        public,
    )
    (b / MEDIA_FOLDER / snapshot.name / "Dateien/original.pdf").unlink()
    with pytest.raises(ArchiveError):
        audit_snapshots(recovered, a, b, require_equal=False)
