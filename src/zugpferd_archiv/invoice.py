"""Offline XML validation and inert PDF/mail extraction; never rewrite input."""

from __future__ import annotations

import email.policy
import hashlib
import io
from email.parser import BytesParser
from pathlib import Path

from lxml import etree
from pypdf import PdfReader
from saxonche import PySaxonProcessor

from .errors import ArchiveError

RULES = Path(__file__).parent / "validation"
VERSION = "EN16931-1.3.15; XRechnung-3.0.2/2026-08-31"
MAX_FILE = 64 * 1024 * 1024
MAX_XML = 8 * 1024 * 1024


def mail_attachments(raw: bytes) -> list[dict]:
    if len(raw) > MAX_FILE:
        raise ArchiveError("Mail überschreitet Größenlimit")
    message = BytesParser(policy=email.policy.default).parsebytes(raw)
    result = []
    for part in message.walk():
        filename = part.get_filename()
        if filename:
            name = filename.replace("\\", "/").split("/")[-1]
            data = part.get_payload(decode=True)
            if not data or len(data) > MAX_FILE or len(result) >= 100:
                raise ArchiveError("Unzulässige Anzahl/Größe von Mailanhängen")
            result.append(
                dict(
                    filename=name,
                    content=data,
                    sha256=hashlib.sha256(data).hexdigest(),
                    sender=str(message.get("From", "")),
                    date=str(message.get("Date", "")),
                    message_id=str(message.get("Message-ID", "")),
                )
            )
    return result


def inspect_xml(raw: bytes) -> dict:
    if len(raw) > MAX_XML:
        raise ArchiveError("XML überschreitet Größenlimit")
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
    )
    try:
        root = etree.fromstring(raw, parser)
    except etree.XMLSyntaxError as exc:
        raise ArchiveError(f"XML nicht lesbar: {exc}") from exc
    if root.getroottree().docinfo.doctype:
        raise ArchiveError("DTD/externe Entitäten sind gesperrt")
    tag = etree.QName(root)
    syntax = (
        "CII"
        if tag.localname == "CrossIndustryInvoice"
        else "UBL"
        if tag.localname in ("Invoice", "CreditNote")
        else "unbekannt"
    )
    errors = []
    if syntax == "unbekannt":
        errors.append("Unbekanntes Rechnungsformat")
    else:
        schema = (
            RULES
            / syntax.lower()
            / "schema"
            / (
                "uncefact/data/standard/CrossIndustryInvoice_100pD16B.xsd"
                if syntax == "CII"
                else f"maindoc/UBL-{tag.localname}-2.1.xsd"
            )
        )
        if not schema.is_file():
            errors.append("Passendes Offline-XSD fehlt; keine erfolgreiche Validierung")
        else:
            validator = etree.XMLSchema(etree.parse(str(schema), parser))
            if not validator.validate(root):
                errors.extend(str(e) for e in validator.error_log)
        with PySaxonProcessor(license=False) as processor:
            xslt = processor.new_xslt30_processor()
            sheet = (
                RULES / syntax.lower() / "xslt" / f"EN16931-{syntax}-validation.xslt"
            )
            executable = xslt.compile_stylesheet(stylesheet_file=str(sheet))
            report = executable.transform_to_string(
                xdm_node=processor.parse_xml(
                    xml_text=etree.tostring(root, encoding="unicode")
                )
            )
            svrl = etree.fromstring(report.encode(), parser)
            errors.extend(
                " ".join(e.itertext()).strip()
                for e in svrl.findall(
                    ".//{http://purl.oclc.org/dsdl/svrl}failed-assert"
                )
            )

    def text(expression):
        return str(root.xpath(f"string({expression})")).strip()

    if syntax == "CII":
        prefix = "//*[local-name()='ApplicableHeaderTradeSettlement']"
        totals = (
            prefix
            + "/*[local-name()='SpecifiedTradeSettlementHeaderMonetarySummation']"
        )
        profile = text(
            "//*[local-name()='GuidelineSpecifiedDocumentContextParameter']/*[local-name()='ID']"
        )
        fields = dict(
            number=text("//*[local-name()='ExchangedDocument']/*[local-name()='ID']"),
            invoice_date=text(
                "//*[local-name()='ExchangedDocument']/*[local-name()='IssueDateTime']/*"
            ),
            seller=text("//*[local-name()='SellerTradeParty']/*[local-name()='Name']"),
            buyer=text("//*[local-name()='BuyerTradeParty']/*[local-name()='Name']"),
            currency=text(prefix + "/*[local-name()='InvoiceCurrencyCode']"),
            net=text(totals + "/*[local-name()='TaxBasisTotalAmount']"),
            tax=text(totals + "/*[local-name()='TaxTotalAmount']"),
            gross=text(totals + "/*[local-name()='GrandTotalAmount']"),
        )
        fields["tax_breakdown"] = [
            dict(
                rate=str(node.xpath("string(*[local-name()='RateApplicablePercent'])")),
                category=str(node.xpath("string(*[local-name()='CategoryCode'])")),
                net=str(node.xpath("string(*[local-name()='BasisAmount'])")),
                tax=str(node.xpath("string(*[local-name()='CalculatedAmount'])")),
            )
            for node in root.xpath(prefix + "/*[local-name()='ApplicableTradeTax']")
        ]
        if len(fields["invoice_date"]) == 8:
            value = fields["invoice_date"]
            fields["invoice_date"] = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    else:
        profile = text("/*/*[local-name()='CustomizationID']")
        totals = "/*/*[local-name()='LegalMonetaryTotal']"
        fields = dict(
            number=text("/*/*[local-name()='ID']"),
            invoice_date=text("/*/*[local-name()='IssueDate']"),
            seller=text(
                "//*[local-name()='AccountingSupplierParty']//*[local-name()='RegistrationName']"
            ),
            buyer=text(
                "//*[local-name()='AccountingCustomerParty']//*[local-name()='RegistrationName']"
            ),
            currency=text("/*/*[local-name()='DocumentCurrencyCode']"),
            net=text(totals + "/*[local-name()='TaxExclusiveAmount']"),
            tax=text("/*/*[local-name()='TaxTotal']/*[local-name()='TaxAmount']"),
            gross=text(totals + "/*[local-name()='TaxInclusiveAmount']"),
        )
    if syntax == "UBL":
        fields["tax_breakdown"] = [
            dict(
                rate=str(
                    node.xpath(
                        "string(*[local-name()='TaxCategory']/*[local-name()='Percent'])"
                    )
                ),
                category=str(
                    node.xpath(
                        "string(*[local-name()='TaxCategory']/*[local-name()='ID'])"
                    )
                ),
                net=str(node.xpath("string(*[local-name()='TaxableAmount'])")),
                tax=str(node.xpath("string(*[local-name()='TaxAmount'])")),
            )
            for node in root.xpath(
                "/*/*[local-name()='TaxTotal']/*[local-name()='TaxSubtotal']"
            )
        ]
    if (
        "minimum" in profile.casefold()
        or "basicwl" in profile.casefold()
        or "basic-wl" in profile.casefold()
    ):
        errors.append("MINIMUM/BASIC-WL ist keine vollständige EN16931-E-Rechnung")
    if "xrechnung" in profile.casefold():
        profile_sheet = RULES / syntax.lower() / "xslt" / "XRechnung-validation.xsl"
        if not profile_sheet.exists():
            errors.append("XRechnung-Profilregeln fehlen; Freigabe gesperrt")
        else:
            with PySaxonProcessor(license=False) as processor:
                executable = processor.new_xslt30_processor().compile_stylesheet(
                    stylesheet_file=str(profile_sheet)
                )
                report = executable.transform_to_string(
                    xdm_node=processor.parse_xml(
                        xml_text=etree.tostring(root, encoding="unicode")
                    )
                )
                svrl = etree.fromstring(report.encode(), parser)
                errors.extend(
                    " ".join(e.itertext()).strip()
                    for e in svrl.findall(
                        ".//{http://purl.oclc.org/dsdl/svrl}failed-assert"
                    )
                )
    return fields | dict(
        format=syntax,
        profile=profile,
        validator_version=VERSION,
        critical_errors=errors,
        xml_sha256=hashlib.sha256(raw).hexdigest(),
    )


def inspect_file(path: Path) -> dict:
    if path.stat().st_size > MAX_FILE:
        raise ArchiveError("Datei überschreitet Größenlimit (64 MiB)")
    raw = path.read_bytes()
    if path.suffix.casefold() == ".xml":
        return inspect_xml(raw) | {"xml": raw}
    if raw.startswith(b"%PDF"):
        reader = PdfReader(io.BytesIO(raw), strict=True)
        xmls = []
        for name, contents in reader.attachments.items():
            if name.casefold().endswith(".xml"):
                xmls.extend(contents)
        if len(xmls) > 1:
            raise ArchiveError("Mehrere XML-Anhänge: eindeutige Rechnung erforderlich")
        if xmls:
            return inspect_xml(xmls[0]) | {
                "xml": xmls[0],
                "container": "ZUGFeRD/Factur-X PDF",
            }
        return dict(
            format="PDF",
            profile="Kein strukturiertes E-Rechnungsoriginal",
            validator_version=VERSION,
            critical_errors=[],
            xml=None,
        )
    return dict(
        format="Sonstiger Beleg",
        profile="Keine E-Rechnung erkannt",
        validator_version=VERSION,
        critical_errors=[],
        xml=None,
    )


def analyze_file(path: Path) -> dict:
    """Preserve malformed evidence with explicit validation errors."""
    try:
        return inspect_file(path)
    except Exception as exc:
        return dict(
            format="Ungeprüft/beschädigt",
            profile="Klärung erforderlich",
            validator_version=VERSION,
            critical_errors=[str(exc)],
            xml=None,
        )
