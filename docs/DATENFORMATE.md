# Portable Datenformate

Alle Formate sind UTF-8 JSON/JSONL mit expliziten Versionen. Dezimalbeträge stehen
als Strings, Datumsangaben ISO 8601, Zeitstempel mit UTC-Offset, SHA-256 kleinhexadezimal.
Es gibt keine Archivlöschschnittstelle und keine rückwirkliche Änderung alter Ereignisse.

## Register 1

`Archivverwaltung/Register/events.jsonl`: SHA-256-verkettete Ereignisse mit
Sequenz, UTC-Zeit, Vorgängerhash, Nutzdaten und Ereignishash. Ereignisse enthalten
authentifizierte Bediener-SID, Jahresserie, dauerhafte Reservierung, Übernahme,
begründete Korrektur mit vorherigem Wert, Zuordnung, Versand, Nummernerklärung,
Periodenabgleich und verifizierten Sicherungsabschluss.

Beleg: UUID, Richtung, Dokumentart, Nummer, Rechnungsdatum, Partner, Währung,
Netto/Steuer/Brutto, Steueraufschlüsselung, Leistungszeitraum, Geschäftsvorfall,
Zahlungsreferenz, Quellen-/Importdaten, Originalname/relative Ablage, Größe,
mtime/ctime in Nanosekunden, SHA-256, XML-Felder/Profil/Validatorversion,
Prüffehler, Status, Beziehungen und zugeordnete Dateien mit Hash.
Die Registerkorrektur verändert niemals PDF/XML. XML-Felder bleiben separat erhalten.

Originale liegen eindeutig unter `Eingang|Ausgang/<Rechnungsjahr>/<Beleg-ID>/`;
gleiche Dateinamen bei verschiedenen Belegen kollidieren nicht. `Vorgaenge/<UUID>.json`
ist die unveränderliche Übernahmeabsicht. Ein offener Commit wird mit denselben
Daten/Originalbytes fortgesetzt; keine zweite ID und keine erneute Nummernvergabe.

## Sicherungsstände 1

Lokal `Archivverwaltung/Sicherungsstaende/<UUID>`, auf A/B `Sicherungsstaende/<UUID>`.
`manifest.json` enthält Dateiliste, Größen, Hashes, Zeitpunkt, öffentlichen Ed25519-
Schlüssel und Signatur über canonical JSON. `Dateien/` enthält den vollständigen
Stand einschließlich Register, Originalen, Konfiguration und Nachweisen. Private
Schlüssel und eigene rekursive Datenkopien der Sicherungsstände werden nicht mitkopiert.
Die signierten Manifestreferenzen früherer Stände sind enthalten; die Wiederherstellung
legt zusätzlich die ausgewählte Manifestreferenz ab. Damit bleibt die unabhängige
Prüfhistorie bei späterer Fortsetzung vorhanden.

Eine signierte Absicht wird vor dem Kopieren veröffentlicht; erst vollständige
Rückleseprüfung beider Medien führt zum Abschluss. Offene Absichten sind fortsetzbar.
Fehlende/veränderte Objekte abgeschlossener Stände sind harte Fehler. Journalpräfixe
werden gegen unabhängige Referenzkopien geprüft; diese unterstützen die Erkennung
von Kettenkürzung. Schutz der Schlüssel und unabhängige Referenzverwahrung sind erforderlich.

## Exporte

Der bisherige Prüfexport filtert Quellablagejahr und optional UTC-Archivierungsdatum.
Der Registerexport filtert `invoice_date`, ergänzt verknüpfte Belege, enthält
unveränderte Originale/zugeordnete Mails/XML, vollständige Registerereignisse,
CSV/JSON, Formatbeschreibung, Prüfnachweise/Dokumentationen und `index.html`.
CSV: UTF-8 mit BOM, Semikolon, gequotete Felder; führendes Apostroph bei Formeln.
JSON bewahrt Werte verlustfrei. Dateien und Prüfsummen werden zurückgelesen.
Neutraler Belegexport, kein ungeprüfter DATEV-Buchungsstapel.

Dokumentationsschema 1 verwendet Renderer 2 für neue Fassungen. Ältere Fassungen
ohne Rendererangabe behalten Renderer 1 und ihre ursprünglichen Hashes/Dateien.
