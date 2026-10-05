from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from zugpferd_archiv import storage
from zugpferd_archiv.core import ArchiveService
from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.journal import Journal
from zugpferd_archiv.media import register, validate_pair


@pytest.fixture
def archive(tmp_path):
    root, a, b = (tmp_path / name for name in ("work", "a", "b"))
    for p in (root, a, b):
        p.mkdir()
    service = ArchiveService(root)
    service.setup(2026)
    ma = register(a, "A")
    mb = register(b, "B", ma.archive_id)
    service.configure(a, b)
    source = root / "Eingang/2026/vendor/invoice.pdf"
    source.parent.mkdir()
    source.write_bytes(b"%PDF-1.7\nInvoice\n")
    return service, source, a, b, ma, mb


def test_hash_and_non_destructive_setup(tmp_path):
    service = ArchiveService(tmp_path)
    service.setup(2026)
    source = tmp_path / "Eingang/2026/existing.xml"
    source.write_bytes(b"original")
    service.setup(2026)
    assert source.read_bytes() == b"original"
    assert storage.sha256(source) == hashlib.sha256(b"original").hexdigest()
    for name in ("Protokolle", "Pruefberichte", "Konfiguration"):
        assert (tmp_path / "Archivverwaltung" / name).is_dir()


def test_registration_identity_and_duplicate_rejection(archive):
    service, source, a, b, ma, mb = archive
    assert ma.archive_id == mb.archive_id
    assert ma.medium_uuid != mb.medium_uuid
    assert validate_pair(a, b, ma, mb) == (ma, mb)
    with pytest.raises(ArchiveError):
        register(a, "A")
    with pytest.raises(ArchiveError):
        validate_pair(a, a, ma, mb)
    marker = b / ".zugpferd-medium.json"
    data = json.loads(marker.read_text())
    data["role"] = "A"
    marker.write_text(json.dumps(data))
    with pytest.raises(ArchiveError):
        validate_pair(a, b, ma, mb)


def test_backup_roundtrip_and_idempotence(archive):
    service, source, a, b, _, _ = archive
    original = source.read_bytes()
    stat = source.stat()
    result = service.backup(a, b)
    assert result.success
    assert result.totals["verified"] == 2
    dest = Path("Archive/2026/Eingang/vendor/invoice.pdf")
    assert (a / dest).read_bytes() == original == (b / dest).read_bytes()
    timestamp = (a / dest).stat().st_mtime_ns
    assert service.backup(a, b).success
    assert (a / dest).stat().st_mtime_ns == timestamp
    assert source.read_bytes() == original
    assert source.stat().st_mtime_ns == stat.st_mtime_ns
    assert service.check(a, b).success
    assert service.compare(a, b).success
    records = service.records(a)
    assert len(records) == 1
    record = records[0]
    assert record["filename"] == source.name
    assert record["source_relative"] == "Eingang/2026/vendor/invoice.pdf"
    assert record["size"] == len(original)
    assert record["source_mtime_ns"] == stat.st_mtime_ns
    assert record["archived_at"]
    assert result.report_json.is_file() and result.report_text.is_file()


def test_changed_source_preserves_history(archive):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    source.write_bytes(b"changed")
    result = service.backup(a, b)
    assert not result.success
    assert any("changed_source" in item["kind"] for item in result.exceptions)
    assert (
        a / "Archive/2026/Eingang/vendor/invoice.pdf"
    ).read_bytes() != source.read_bytes()
    assert len(service.records(a)) == 1
    assert service.compare(a, b).success


def test_conflict_never_overwritten(archive):
    service, source, a, b, _, _ = archive
    dest = a / "Archive/2026/Eingang/vendor/invoice.pdf"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"conflicting")
    result = service.backup(a, b)
    assert not result.success
    assert dest.read_bytes() == b"conflicting"
    assert not (b / "Archive/2026/Eingang/vendor/invoice.pdf").exists()


def test_missing_medium_and_unexpected_identity(archive):
    service, source, a, b, ma, mb = archive
    assert not service.backup(a, b.parent / "missing").success
    marker = b / ".zugpferd-medium.json"
    data = json.loads(marker.read_text())
    data["medium_uuid"] = "11111111-1111-4111-8111-111111111111"
    marker.write_text(json.dumps(data))
    assert not service.backup(a, b).success
    assert not (a / "Archive/2026/Eingang/vendor/invoice.pdf").exists()


def test_readback_hash_mismatch_never_published(tmp_path, monkeypatch):
    source, dest = tmp_path / "source.pdf", tmp_path / "dest.pdf"
    source.write_bytes(b"good")
    actual = storage.sha256
    monkeypatch.setattr(
        storage, "sha256", lambda p: actual(p) if p == source else "0" * 64
    )
    with pytest.raises(ArchiveError):
        storage.verified_copy(source, dest, actual(source))
    assert not dest.exists()
    assert list(tmp_path.glob("*.partial-*"))
    assert source.read_bytes() == b"good"


def test_interrupted_copy_is_reported_and_not_accepted(archive, monkeypatch):
    service, source, a, b, _, _ = archive
    original = storage.copy_stream

    def interrupt(src, target):
        target.write(b"partial")
        raise OSError("medium disconnected")

    monkeypatch.setattr(storage, "copy_stream", interrupt)
    result = service.backup(a, b)
    assert not result.success
    assert not (a / "Archive/2026/Eingang/vendor/invoice.pdf").exists()
    monkeypatch.setattr(storage, "copy_stream", original)
    assert not service.check(a, b).success
    assert service.backup(a, b).success
    # Recovery leaves interrupted evidence intact and uses a fresh temporary file.
    report = service.check(a, b)
    assert not report.success
    assert any(e["kind"] == "interrupted" for e in report.exceptions)


def test_partial_replication_retry(archive, monkeypatch):
    service, source, a, b, _, _ = archive
    original = storage.verified_copy

    def fail_b(src, dest, expected):
        if dest.is_relative_to(b):
            raise ArchiveError("B failed")
        return original(src, dest, expected)

    monkeypatch.setattr(storage, "verified_copy", fail_b)
    assert not service.backup(a, b).success
    assert len(service.records(a)) == 1
    assert not service.last_backup_success()
    monkeypatch.setattr(storage, "verified_copy", original)
    assert service.backup(a, b).success
    assert len(service.records(a)) == len(service.records(b)) == 1


def test_integrity_missing_changed_unexpected(archive):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    (a / "Archive/2026/Eingang/vendor/invoice.pdf").unlink()
    (b / "Archive/2026/Eingang/vendor/invoice.pdf").write_bytes(b"corrupt")
    (b / "Archive/extra.xml").write_bytes(b"unexpected")
    report = service.check(a, b)
    assert not report.success
    assert {"missing", "changed", "unexpected"} <= {
        e["kind"] for e in report.exceptions
    }
    assert not service.compare(a, b).success
    assert not service.backup(a, b).success  # Never silently repair.


def test_journal_chain_detects_tampering(tmp_path):
    journal = Journal(tmp_path / "events.jsonl")
    journal.append("test", {"sha256": "a" * 64})
    journal.append("test", {"sha256": "b" * 64})
    assert len(journal.verify()) == 2
    data = journal.path.read_text()
    journal.path.write_text(data.replace("a" * 64, "c" * 64))
    with pytest.raises(ArchiveError):
        journal.verify()
    with pytest.raises(ArchiveError):
        journal.append("test", {})


def test_manifest_tampering_blocks_writes(archive):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    manifest = a / "Manifest/records.jsonl"
    manifest.write_text(manifest.read_text().replace("invoice.pdf", "other.pdf"))
    assert not service.check(a, b).success
    new = source.with_name("new.xml")
    new.write_bytes(b"new")
    assert not service.backup(a, b).success
    assert not (a / "Archive/2026/Eingang/vendor/new.xml").exists()


def test_export_range_is_copy_and_verified(archive, tmp_path):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    export = tmp_path / "export"
    result = service.export(a, b, export, 2026, 2026)
    assert result.success
    assert (
        export / "Originale/Eingang/2026/vendor/invoice.pdf"
    ).read_bytes() == source.read_bytes()
    assert (export / "index.json").is_file()
    assert source.is_file()
    assert not service.export(a, b, export, 2026, 2026).success
    assert not service.export(a, b, a / "export", 2026, 2026).success
    assert not service.export(a, b, tmp_path / "bad", 2027, 2026).success


def test_symlinks_rejected(archive, tmp_path):
    service, source, a, b, _, _ = archive
    other = tmp_path / "secret.pdf"
    other.write_bytes(b"secret")
    source.unlink()
    source.symlink_to(other)
    assert not service.backup(a, b).success


def test_lock_and_truncated_journal_fail_closed(archive):
    service, source, a, b, _, _ = archive
    lock = a / ".zugpferd-operation.lock"
    lock.write_text("interrupted")
    assert not service.backup(a, b).success
    lock.unlink()
    assert service.backup(a, b).success
    journal = a / "Journal/events.jsonl"
    with journal.open("ab") as stream:
        stream.write(b'{"sequence":')
    assert not service.check(a, b).success
    assert not service.backup(a, b).success


def test_source_changed_while_copying_never_publishes(tmp_path, monkeypatch):
    source, dest = tmp_path / "source.pdf", tmp_path / "dest.pdf"
    source.write_bytes(b"old")
    expected = storage.sha256(source)
    original = storage.copy_stream

    def change(src, target):
        original(src, target)
        src.write_bytes(b"new")

    monkeypatch.setattr(storage, "copy_stream", change)
    with pytest.raises(ArchiveError):
        storage.verified_copy(source, dest, expected)
    assert not dest.exists()
    assert source.read_bytes() == b"new"


def test_zero_byte_and_same_filename_different_folders(archive):
    service, source, a, b, _, _ = archive
    second = source.parents[1] / "another/invoice.pdf"
    second.parent.mkdir()
    second.write_bytes(b"")
    assert service.backup(a, b).success
    assert len(service.records(a)) == 2
    assert (a / "Archive/2026/Eingang/another/invoice.pdf").read_bytes() == b""


def test_untracked_identical_orphan_is_explicitly_recorded(archive):
    service, source, a, b, _, _ = archive
    dest = a / "Archive/2026/Eingang/vendor/invoice.pdf"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(source.read_bytes())
    assert not service.check(a, b).success
    assert service.backup(a, b).success
    assert len(service.records(a)) == 1
    assert service.check(a, b).success


def test_export_date_filter_and_corrupt_media(archive, tmp_path):
    from datetime import date

    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    export = tmp_path / "filtered"
    assert service.export(
        a, b, export, 2026, 2026, date(2000, 1, 1), date(2000, 12, 31)
    ).success
    assert json.loads((export / "index.json").read_text())["records"] == []
    (b / "Archive/2026/Eingang/vendor/invoice.pdf").write_bytes(b"corrupt")
    target = tmp_path / "corrupt-export"
    assert not service.export(a, b, target, 2026, 2026).success
    assert not target.exists()


def test_journal_and_manifest_commit_interruption_fails_closed(archive, monkeypatch):
    service, source, a, b, _, _ = archive
    original = Journal.append

    def interrupted(self, event, data):
        if event == "archived":
            raise OSError("Power loss between manifest and journal commit")
        return original(self, event, data)

    monkeypatch.setattr(Journal, "append", interrupted)
    assert not service.backup(a, b).success
    monkeypatch.setattr(Journal, "append", original)
    assert not service.backup(a, b).success
    assert not service.check(a, b).success
    assert source.exists()


def test_moved_media_path_recognized_by_marker(archive, monkeypatch):
    from zugpferd_archiv import media

    service, source, a, b, ma, mb = archive
    new_a = a.with_name("new-letter-a")
    a.rename(new_a)
    probe = media.volume_id
    monkeypatch.setattr(
        media, "volume_id", lambda root: ma.volume_id if root == new_a else probe(root)
    )
    assert service.backup(new_a, b).success


def test_wrong_archive_and_duplicate_physical_volume(archive, monkeypatch):
    from zugpferd_archiv import media
    from dataclasses import replace

    service, source, a, b, ma, mb = archive
    with pytest.raises(ArchiveError):
        validate_pair(
            a, b, ma, replace(mb, archive_id="11111111-1111-4111-8111-111111111111")
        )
    data = json.loads((b / media.MARKER).read_text())
    data["volume_id"] = ma.volume_id
    (b / media.MARKER).write_text(json.dumps(data))
    monkeypatch.setattr(media, "volume_id", lambda root: ma.volume_id)
    with pytest.raises(ArchiveError):
        validate_pair(a, b, ma, replace(mb, volume_id=ma.volume_id))


def test_missing_metadata_never_recreated(archive):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    (a / "Manifest/records.jsonl").unlink()
    assert not service.backup(a, b).success
    assert not (a / "Manifest/records.jsonl").exists()


def test_archive_symlink_directory_rejected(archive, tmp_path):
    service, source, a, b, _, _ = archive
    external = tmp_path / "external"
    external.mkdir()
    (a / "Archive/2026").symlink_to(external, target_is_directory=True)
    assert not service.backup(a, b).success
    assert list(external.iterdir()) == []


def test_portable_path_validation(tmp_path):
    for relative in (
        "../invoice.pdf",
        "/invoice.pdf",
        "Archive/C:invoice.pdf",
        "Archive/CON.pdf",
        "Archive/file.pdf.",
        "Archive/vendor /invoice.pdf",
        "Archive/name\\invoice.pdf",
    ):
        with pytest.raises(ArchiveError):
            storage.child(tmp_path, relative)


def test_tampered_local_log_prevents_archive_writes(archive):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    log = service.root / "Archivverwaltung/Protokolle/operations.jsonl"
    log.write_bytes(b"{}\n")
    new = source.with_name("new.pdf")
    new.write_bytes(b"new")
    with pytest.raises(ArchiveError):
        service.backup(a, b)
    assert not (a / "Archive/2026/Eingang/vendor/new.pdf").exists()


def test_backup_reports_interrupted_evidence_as_warning(archive):
    service, source, a, b, _, _ = archive
    partial = a / "Archive/interrupted.pdf.partial-old"
    partial.write_bytes(b"partial")
    result = service.backup(a, b)
    assert result.success
    assert any(w["kind"] == "interrupted" for w in result.warnings)
    assert partial.read_bytes() == b"partial"


def test_source_removed_after_partial_replication_is_not_success(archive, monkeypatch):
    service, source, a, b, _, _ = archive
    original = storage.verified_copy

    def fail_b(src, dest, expected):
        if dest.is_relative_to(b):
            raise OSError("B unplugged")
        return original(src, dest, expected)

    monkeypatch.setattr(storage, "verified_copy", fail_b)
    assert not service.backup(a, b).success
    source.unlink()
    monkeypatch.setattr(storage, "verified_copy", original)
    assert not service.backup(a, b).success


def test_report_write_failure_does_not_mark_success(archive, monkeypatch):
    service, source, a, b, _, _ = archive
    original = storage.write_new

    def fail_report(path, data):
        if path.is_relative_to(b / "Pruefberichte"):
            raise OSError("report storage full")
        return original(path, data)

    monkeypatch.setattr(storage, "write_new", fail_report)
    assert not service.backup(a, b).success
    assert not service.last_backup_success()


def test_journal_append_lock_rejects_concurrent_writer(tmp_path):
    folder = tmp_path / "Journal"
    folder.mkdir()
    journal = Journal(folder / "events.jsonl")
    with storage.exclusive_lock(folder):
        with pytest.raises(ArchiveError):
            journal.append("test", {})
    assert not journal.path.exists()


def test_case_only_source_rename_fails_without_history_rewrite(archive):
    service, source, a, b, _, _ = archive
    assert service.backup(a, b).success
    source.rename(source.with_name("INVOICE.pdf"))
    result = service.backup(a, b)
    assert not result.success
    assert len(service.records(a)) == 1


def test_conflicting_destination_has_distinct_report_category(archive):
    service, source, a, b, _, _ = archive
    dest = a / "Archive/2026/Eingang/vendor/invoice.pdf"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"conflicting")
    report = service.backup(a, b)
    assert any(item["kind"] == "conflicting" for item in report.exceptions)


def test_relative_media_paths_supported(archive, monkeypatch):
    service, source, a, b, _, _ = archive
    monkeypatch.chdir(a.parent)
    assert service.backup(Path("a"), Path("b")).success
