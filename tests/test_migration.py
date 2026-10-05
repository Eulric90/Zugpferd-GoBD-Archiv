import pytest

from zugpferd_archiv import storage, service
from zugpferd_archiv.core import ArchiveService
from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.media import register, read_marker
from zugpferd_archiv.windows_service import provision


def existing(tmp_path):
    old, a, b = (tmp_path / name for name in ("old", "A", "B"))
    for folder in (old, a, b):
        folder.mkdir()
    archive = ArchiveService(old)
    archive.setup()
    marker = register(a, "A")
    register(b, "B", marker.archive_id)
    archive.configure(a, b)
    source = old / "Eingang/2026/invoice.pdf"
    source.parent.mkdir(exist_ok=True)
    source.write_bytes(b"original")
    return old, a, b, marker.archive_id


def test_migration_preserves_originals_and_media_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "IN_SERVICE", False)
    old, a, b, archive_id = existing(tmp_path)
    target = tmp_path / "new"
    provision(target, a, b, old)
    assert (target / "Eingang/2026/invoice.pdf").read_bytes() == b"original"
    assert (old / "Eingang/2026/invoice.pdf").read_bytes() == b"original"
    assert read_marker(a).archive_id == archive_id


def test_migration_blocks_original_changed_after_its_backup(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "IN_SERVICE", False)
    old, a, b, _ = existing(tmp_path)
    copy = storage.verified_copy

    def changed(source, destination, digest):
        if source == old / "Eingang/2026/invoice.pdf":
            source.write_bytes(b"changed after backup")
            digest = storage.sha256(source)
        return copy(source, destination, digest)

    # Alter only the migration copy, after the source has been archived to A/B.
    original_backup = ArchiveService.backup

    def backup(*args, **kwargs):
        result = original_backup(*args, **kwargs)
        monkeypatch.setattr(storage, "verified_copy", changed)
        return result

    monkeypatch.setattr(ArchiveService, "backup", backup)
    with pytest.raises((ArchiveError, ValueError), match="Migration|verändert|Hash"):
        provision(tmp_path / "new", a, b, old)
