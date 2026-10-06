from __future__ import annotations

from pathlib import Path

import pytest

from zugpferd_archiv import storage
from zugpferd_archiv.core import ArchiveService
from zugpferd_archiv.documentation import DocumentationData, FIELD_GROUPS, load_latest
from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.journal import Journal
from zugpferd_archiv.media import register


@pytest.fixture
def doc_archive(tmp_path):
    root, a, b = [tmp_path / name for name in ("work", "a", "b")]
    for p in (root, a, b):
        p.mkdir()
    service = ArchiveService(root)
    service.setup()
    ma = register(a, "A")
    register(b, "B", ma.archive_id)
    service.configure(a, b)
    values = {
        key: f"Betriebliche Angabe: {label}"
        for _, fields in FIELD_GROUPS
        for key, label, required in fields
        if required
    }
    values["organization"] = "Muster & Partner <GmbH>"
    return service, a, b, DocumentationData(values=values)


def test_document_generation_versioned_and_verified(doc_archive):
    service, a, b, data = doc_archive
    report = service.create_documentation(a, b, data)
    assert report.success
    assert len(report.outputs) == 3
    html = next(Path(p) for p in report.outputs if p.endswith(".html"))
    assert "Muster &amp; Partner &lt;GmbH&gt;" in html.read_text(encoding="utf-8")
    assert "Entwurf" in html.read_text(encoding="utf-8")
    assert "Die Software allein garantiert keine GoBD-Konformität" in html.read_text(
        encoding="utf-8"
    )
    assert "SHA-256" in html.read_text(encoding="utf-8")
    latest = load_latest(service.root)
    assert latest["answers"]["organization"] == data.values["organization"]
    assert latest["context"]["archive_id"] == service.configuration()["archive_id"]
    assert (
        latest["context"]["media"]["A"]["medium_uuid"]
        == service.configuration()["A"]["medium_uuid"]
    )
    for medium in (a, b):
        event = next(
            e
            for e in Journal(medium / "Journal/events.jsonl").verify()
            if e["event"] == "documentation_saved"
        )
        for entry in event["data"]["files"]:
            assert storage.sha256(medium / entry["path"]) == entry["sha256"]
    old = html.read_bytes()
    second = service.create_documentation(a, b, data)
    assert second.success
    assert html.read_bytes() == old
    assert next(p for p in second.outputs if p.endswith(".html")) != str(html)
    assert load_latest(service.root)["version"] == 2
    assert service.check(a, b).success


def test_missing_medium_does_not_create_document(doc_archive):
    service, a, b, data = doc_archive
    assert not service.create_documentation(a, b.parent / "missing", data).success
    assert load_latest(service.root) is None


def test_required_fields_and_release_validation(doc_archive):
    service, a, b, data = doc_archive
    incomplete = DocumentationData(values={})
    assert not service.create_documentation(a, b, incomplete).success
    assert load_latest(service.root) is None
    released = DocumentationData(values=data.values, approved=True, approved_by="")
    assert not service.create_documentation(a, b, released).success
    released = DocumentationData(
        values=data.values, approved=True, approved_by="Erika Muster"
    )
    assert service.create_documentation(a, b, released).success
    record = load_latest(service.root)
    assert record["status"] == "Betrieblich freigegeben"
    assert record["approved_by"] == "Erika Muster"


def test_partial_documentation_copy_can_resume_without_overwrite(
    doc_archive, monkeypatch
):
    service, a, b, data = doc_archive
    original = storage.verified_copy

    def fail_b(src, dest, expected):
        if dest.is_relative_to(b / "Verfahrensdokumentation"):
            raise OSError("B disconnected")
        return original(src, dest, expected)

    monkeypatch.setattr(storage, "verified_copy", fail_b)
    first = service.create_documentation(a, b, data)
    assert not first.success
    pending = load_latest(service.root, include_pending=True)
    assert pending and not pending["completed"]
    assert load_latest(service.root) is None
    assert not service.check(a, b).success
    monkeypatch.setattr(storage, "verified_copy", original)
    second = service.create_documentation(a, b, data)
    assert second.success
    assert load_latest(service.root)["document_id"] == pending["document_id"]
    assert service.check(a, b).success
    assert (
        len(
            [
                e
                for e in Journal(a / "Journal/events.jsonl").verify()
                if e["event"] == "documentation_saved"
            ]
        )
        == 1
    )


def test_conflicting_document_target_never_overwritten(doc_archive, monkeypatch):
    service, a, b, data = doc_archive
    original = storage.verified_copy
    conflicts = []

    def conflict(src, dest, expected):
        if dest.is_relative_to(b / "Verfahrensdokumentation") and not conflicts:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"conflict")
            conflicts.append(dest)
        return original(src, dest, expected)

    monkeypatch.setattr(storage, "verified_copy", conflict)
    assert not service.create_documentation(a, b, data).success
    assert conflicts[0].read_bytes() == b"conflict"
    assert load_latest(service.root) is None


def test_tampered_documentation_detected_and_not_repaired(doc_archive):
    service, a, b, data = doc_archive
    assert service.create_documentation(a, b, data).success
    event = next(
        e
        for e in Journal(a / "Journal/events.jsonl").verify()
        if e["event"] == "documentation_saved"
    )
    doc = a / event["data"]["files"][0]["path"]
    doc.write_bytes(b"tampered")
    assert not service.check(a, b).success
    assert not service.create_documentation(a, b, data).success
    assert not service.backup(a, b).success
    assert doc.read_bytes() == b"tampered"


def test_pending_changes_rejected_and_local_document_tampering_detected(
    doc_archive, monkeypatch
):
    service, a, b, data = doc_archive
    original = storage.verified_copy
    monkeypatch.setattr(
        storage,
        "verified_copy",
        lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    assert not service.create_documentation(a, b, data).success
    monkeypatch.setattr(storage, "verified_copy", original)
    different = DocumentationData(
        values={**data.values, "organization": "Changed business"}
    )
    assert not service.create_documentation(a, b, different).success
    assert service.create_documentation(a, b, data).success
    html = next(
        Path(p)
        for p in service.create_documentation(a, b, data).outputs
        if p.endswith(".html")
    )
    html.write_text("tampered")
    with pytest.raises(ArchiveError):
        load_latest(service.root)


def test_documentation_never_changes_invoice_history(doc_archive):
    service, a, b, data = doc_archive
    invoice = service.root / "Eingang/2026/invoice.pdf"
    invoice.parent.mkdir(exist_ok=True)
    invoice.write_bytes(b"original")
    assert service.backup(a, b).success
    before = (a / "Manifest/records.jsonl").read_bytes()
    assert service.create_documentation(a, b, data).success
    assert (a / "Manifest/records.jsonl").read_bytes() == before
    assert invoice.read_bytes() == b"original"


def test_failure_before_first_medium_commit_remains_visible(doc_archive, monkeypatch):
    service, a, b, data = doc_archive
    monkeypatch.setattr(
        storage,
        "verified_copy",
        lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    assert not service.create_documentation(a, b, data).success
    assert not service.check(a, b).success
    assert not service.backup(a, b).success


def test_unexpected_documentation_file_detected(doc_archive):
    service, a, b, data = doc_archive
    assert service.create_documentation(a, b, data).success
    extra = a / "Verfahrensdokumentation/Fassungen/untracked.txt"
    extra.write_bytes(b"untracked")
    report = service.check(a, b)
    assert not report.success
    assert any(e["kind"] == "unexpected" for e in report.exceptions)


def test_doc_readback_mismatch_preserves_temporary_evidence(doc_archive, monkeypatch):
    service, a, b, data = doc_archive
    original = storage.sha256
    monkeypatch.setattr(
        storage, "sha256", lambda p: "0" * 64 if ".partial-" in p.name else original(p)
    )
    report = service.create_documentation(a, b, data)
    assert not report.success
    partials = list((a / "Verfahrensdokumentation/Fassungen").rglob("*.partial-*"))
    assert partials
    monkeypatch.setattr(storage, "sha256", original)
    result = service.create_documentation(a, b, data)
    assert result.success
    assert result.warnings
    assert partials[0].exists()
    assert not service.check(a, b).success
