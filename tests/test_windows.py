import os

import pytest
from zugpferd_archiv import media
from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.storage import publish_new


@pytest.mark.skipif(os.name != "nt", reason="real Windows volume APIs")
def test_real_windows_discovery_and_volume_probe(monkeypatch, tmp_path):
    monkeypatch.undo()
    identity = media.volume_id(tmp_path)
    assert identity and ":" in identity
    assert any(drive.root.anchor == tmp_path.anchor for drive in media.discover())
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir()
    b.mkdir()
    ma = media.register(a, "A")
    mb = media.register(b, "B", ma.archive_id)
    # Separate folders on the same physical Windows volume cannot be A and B.
    with pytest.raises(ArchiveError):
        media.validate_pair(a, b, ma, mb)


def test_atomic_publish_does_not_replace_existing_target(tmp_path):
    temp, destination = tmp_path / "object.partial-test", tmp_path / "object.pdf"
    temp.write_bytes(b"new")
    destination.write_bytes(b"old")
    with pytest.raises(FileExistsError):
        publish_new(temp, destination)
    assert destination.read_bytes() == b"old"
    assert temp.read_bytes() == b"new"
