"""Filesystem tests use logical media, never real USB volumes."""

import pytest
from zugpferd_archiv import media


@pytest.fixture(autouse=True)
def logical_volumes(monkeypatch):
    monkeypatch.setattr(
        media, "volume_id", lambda root: "test-volume:" + str(root.resolve())
    )
