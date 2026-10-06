"""Inert, complete readable XML invoice fields."""

import html

from lxml import etree

from .errors import ArchiveError
from .invoice import MAX_XML


def render_xml(raw: bytes) -> str:
    if len(raw) > MAX_XML:
        raise ArchiveError("XML überschreitet Größenlimit")
    root = etree.fromstring(
        raw, etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    )
    if root.getroottree().docinfo.doctype:
        raise ArchiveError("DTD gesperrt")
    labels = {
        "ID": "Kennung / Nummer",
        "Name": "Name",
        "IssueDate": "Rechnungsdatum",
        "DateTimeString": "Datum",
        "Description": "Beschreibung",
        "BilledQuantity": "Menge",
        "InvoicedQuantity": "Menge",
        "ChargeAmount": "Einzelpreis",
        "LineTotalAmount": "Positionssumme",
        "TaxAmount": "Steuerbetrag",
        "CalculatedAmount": "Steuerbetrag",
        "BasisAmount": "Steuerbasis",
        "RateApplicablePercent": "Steuersatz (%)",
        "Percent": "Steuersatz (%)",
        "GrandTotalAmount": "Brutto gesamt",
        "TaxInclusiveAmount": "Brutto gesamt",
        "TaxBasisTotalAmount": "Netto gesamt",
        "TaxExclusiveAmount": "Netto gesamt",
        "DuePayableAmount": "Zahlbetrag",
        "PayableAmount": "Zahlbetrag",
        "InvoiceCurrencyCode": "Währung",
        "DocumentCurrencyCode": "Währung",
    }
    rows = []
    for node in root.iter():
        if (
            isinstance(node.tag, str)
            and node.text
            and node.text.strip()
            and not len(node)
        ):
            name = etree.QName(node).localname
            parent = (
                etree.QName(node.getparent()).localname
                if node.getparent() is not None
                else "Rechnung"
            )
            attrs = " ".join(f"{key}={value}" for key, value in node.attrib.items())
            rows.append(
                f"<tr><td>{html.escape(parent)}</td><td>{html.escape(labels.get(name, name))}</td>"
                f"<td>{html.escape(node.text.strip())} {html.escape(attrs)}</td></tr>"
            )
    return (
        "<h2>Strukturierte Rechnung – vollständige lesbare Felder</h2><table>"
        + "".join(rows)
        + "</table>"
    )
