import pytest

from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.service import Dispatcher


def test_service_rejects_arbitrary_file_access_and_untrusted_actor(tmp_path):
    dispatch = Dispatcher(tmp_path / "archive", tmp_path / "staging")
    with pytest.raises(ArchiveError):
        dispatch.call({"operation": "delete", "path": str(tmp_path)}, "trusted-SID")
    with pytest.raises(ArchiveError):
        dispatch.call(
            {
                "operation": "ingest",
                "filename": "../bad.pdf",
                "content": "YQ==",
                "fields": {},
            },
            "trusted-SID",
        )
    dispatch.call(
        {
            "operation": "start_series",
            "args": [2026, "", 0, "Erstbestand"],
            "actor": "forged-SID",
        },
        "trusted-SID",
    )
    from zugpferd_archiv.register import Register

    assert (
        Register(tmp_path / "archive", actor="read-only").events()[0]["data"]["actor"]
        == "trusted-SID"
    )


def test_service_rejects_unknown_arguments_and_payload_size(tmp_path):
    dispatch = Dispatcher(tmp_path / "archive", tmp_path / "staging")
    with pytest.raises(ArchiveError):
        dispatch.call(
            {
                "operation": "ingest",
                "filename": "CON.pdf",
                "content": "YQ==",
                "fields": {},
            },
            "SID",
        )
    with pytest.raises(ArchiveError):
        dispatch.call({"operation": "records", "args": ["arbitrary"]}, "SID")


def test_operator_cannot_supply_internal_sent_event_argument(tmp_path):
    dispatch = Dispatcher(tmp_path / "archive", tmp_path / "staging")
    with pytest.raises(ArchiveError):
        dispatch.call(
            {
                "operation": "correct",
                "args": ["id", {"status": "versandt"}, "fake", "sent"],
            },
            "SID",
        )
