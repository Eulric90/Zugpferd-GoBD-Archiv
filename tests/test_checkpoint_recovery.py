import pytest

from zugpferd_archiv import storage
from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.journal import Journal
from zugpferd_archiv.snapshots import (
    create_snapshot,
    replicate_snapshot,
    audit_snapshots,
    resume_snapshot,
    MEDIA_FOLDER,
    FOLDER,
)


def setup(tmp_path):
    root, a, b = (tmp_path / n for n in ("root", "A", "B"))
    for folder in (root, a, b):
        folder.mkdir()
    (root / "original.pdf").write_bytes(b"original")
    return root, a, b


def test_media_checkpoint_interruption_resumes_without_false_success(
    tmp_path, monkeypatch
):
    root, a, b = setup(tmp_path)
    snapshot = create_snapshot(root, tmp_path / ".root-Schluessel")
    copy = storage.verified_copy

    def fail(source, destination, digest):
        if destination.is_relative_to(b) and destination.name == "original.pdf":
            raise OSError("USB unplugged")
        return copy(source, destination, digest)

    monkeypatch.setattr(storage, "verified_copy", fail)
    with pytest.raises(OSError):
        replicate_snapshot(snapshot, a, b)
    audit_snapshots(root, a, b, require_equal=False)
    monkeypatch.setattr(storage, "verified_copy", copy)
    replicate_snapshot(snapshot, a, b)
    audit_snapshots(root, a, b)


def test_committed_checkpoint_missing_is_not_repaired(tmp_path):
    root, a, b = setup(tmp_path)
    snapshot = create_snapshot(root, tmp_path / ".root-Schluessel")
    replicate_snapshot(snapshot, a, b)
    Journal(root / "Archivverwaltung/Register/events.jsonl").append(
        "register_backup_verified", {"ids": [], "snapshot": snapshot.name}
    )
    (b / MEDIA_FOLDER / snapshot.name / "Dateien/original.pdf").unlink()
    with pytest.raises(ArchiveError):
        audit_snapshots(root, a, b, require_equal=False)


def test_local_checkpoint_interruption_resumes_signed_intent(tmp_path, monkeypatch):
    root, a, b = setup(tmp_path)
    copy = storage.verified_copy

    def fail(*args):
        raise OSError("Interrupted local copy")

    monkeypatch.setattr(storage, "verified_copy", fail)
    with pytest.raises(OSError):
        create_snapshot(root, tmp_path / ".root-Schluessel")
    snapshot = next((root / FOLDER).iterdir())
    monkeypatch.setattr(storage, "verified_copy", copy)
    resume_snapshot(snapshot, root)
    replicate_snapshot(snapshot, a, b)
    audit_snapshots(root, a, b)
