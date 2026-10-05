import json

import pytest

from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.journal import Journal
from zugpferd_archiv.snapshots import (
    create_snapshot,
    replicate_snapshot,
    audit_snapshots,
)
from zugpferd_archiv.workflow import restore_snapshot


def test_signed_snapshot_restore_and_tail_cut_detection(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "original.pdf").write_bytes(b"immutable")
    journal = Journal(root / "Archivverwaltung/Register/events.jsonl")
    journal.append("series_started", {"year": 2026})
    snapshot = create_snapshot(root, tmp_path / ".root-Schluessel")
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir()
    b.mkdir()
    replicate_snapshot(snapshot, a, b)
    audit_snapshots(root, a, b)
    assert restore_snapshot(snapshot, tmp_path / "restored")["verified"]
    assert (tmp_path / "restored/original.pdf").read_bytes() == b"immutable"
    journal.path.write_bytes(b"")
    with pytest.raises(ArchiveError, match="gekürzt"):
        audit_snapshots(root, a, b)


def test_snapshot_manifest_tamper_and_pinned_key(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "file").write_bytes(b"immutable")
    snapshot = create_snapshot(root, tmp_path / "keys")
    with pytest.raises(ArchiveError, match="schlüssel"):
        restore_snapshot(snapshot, tmp_path / "bad", "wrong")
    path = snapshot / "manifest.json"
    value = json.loads(path.read_text())
    value["timestamp"] = "forged"
    path.write_text(json.dumps(value))
    with pytest.raises(ArchiveError, match="signatur"):
        restore_snapshot(snapshot, tmp_path / "bad2")
