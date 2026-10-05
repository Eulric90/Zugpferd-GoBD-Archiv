import pytest
from pathlib import Path

from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.invoice import inspect_xml, mail_attachments


def test_external_entities_rejected():
    with pytest.raises(ArchiveError, match="DTD"):
        inspect_xml(b'<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>')


def test_wrong_schema_does_not_pass():
    result = inspect_xml(
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"/>'
    )
    assert result["critical_errors"]
    assert result["format"] == "UBL"


@pytest.mark.parametrize("name", ["en16931-cii.xml", "xrechnung-cii.xml"])
def test_published_examples_validate_offline(name):
    result = inspect_xml((Path(__file__).parent / "fixtures" / name).read_bytes())
    assert not result["critical_errors"]
    assert result["number"] and result["tax_breakdown"]


def test_bounded_parser_runs_with_memory_and_time_limits():
    from zugpferd_archiv.inspection import analyze_bounded

    result = analyze_bounded(
        (Path(__file__).parent / "fixtures/en16931-cii.xml").resolve()
    )
    assert not result["critical_errors"], result


def test_mail_multiple_attachments_and_unsafe_names():
    raw = (
        b'MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary="abc"\r\n\r\n'
        b'--abc\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename="../bad.pdf"\r\n\r\none\r\n'
        b'--abc\r\nContent-Type: application/xml\r\nContent-Disposition: attachment; filename="invoice.xml"\r\n\r\ntwo\r\n--abc--\r\n'
    )
    items = mail_attachments(raw)
    assert len(items) == 2
    assert items[0]["filename"] == "bad.pdf"
    assert items[1]["content"] == b"two"
