from email.message import EmailMessage

from zugpferd_archiv.register import Register


def test_sent_mail_keeps_original_and_matches_attachment(tmp_path):
    source = tmp_path / "original.pdf"
    source.write_bytes(b"invoice original")
    register = Register(tmp_path / "archive", actor="SID")
    register.start_series(2026, "", 0, "Start")
    record = register.ingest(
        source,
        dict(
            direction="Ausgang",
            number="20260001",
            invoice_date="2026-10-01",
            partner="Kunde",
            currency="EUR",
            net="100",
            tax="19",
            gross="119",
            source="PDF24",
            reviewed=True,
        ),
    )
    message = EmailMessage()
    message["To"] = "kunde@example.com"
    message.set_content("Ihre Rechnung")
    message.add_attachment(
        b"invoice original",
        maintype="application",
        subtype="pdf",
        filename="invoice.pdf",
    )
    eml = tmp_path / "sent.eml"
    eml.write_bytes(message.as_bytes())
    register.mark_sent(record["id"], "2026-10-02", "kunde@example.com", eml)
    result = register.records()[0]
    assert result["status"] == "versandt"
    assert len(result["related_files"]) == 1


def test_reserved_gap_remains_until_explained(tmp_path):
    register = Register(tmp_path, actor="SID")
    register.start_series(2026, "-", 100, "Papierregister geprüft")
    number = register.reserve(2026)
    assert any(t["kind"] == "number_gap" for t in register.tasks())
    register.explain_number(number, "Entwurf verworfen; nie versandt")
    assert not any(t["kind"] == "number_gap" for t in register.tasks())
    assert register.reserve(2026) == "2026-0102"
