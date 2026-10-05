# Offline-Prüfung und Lizenzen

Die Anwendung verändert keine Rechnung. Strukturprüfungen verwenden lxml,
Schematron-Regeln werden mit SaxonC-HE offline ausgeführt. Die sachliche und
steuerliche Prüfung bleibt ein eigener Arbeitsschritt.

Gebündelte Regeln:

- ConnectingEurope/eInvoicing-EN16931, Tag `validation-1.3.15`, CII/UBL
  XSLT und CII D16B XSD. EUPL 1.2, Lizenz im Regelverzeichnis.
- KoSIT XRechnung 3.0.2, Konfiguration `v2026-08-31`: Profil-XSLT und
  UBL 2.1 XSD. Apache 2.0 für KoSIT-Regeln; UBL/OASIS- und UN/CEFACT-Hinweise
  stehen auch in den jeweiligen Schemadateien und sind unverändert enthalten.

Quellen: https://github.com/ConnectingEurope/eInvoicing-EN16931 und
https://github.com/itplr-kosit/validator-configuration-xrechnung.
Regeldateien werden zur Laufzeit nicht aus dem Netz geladen.
Die EN16931-Prüfung deckt keine beliebigen zusätzlichen Empfänger-CIUS ab.
MINIMUM/BASIC-WL werden nicht als vollständige E-Rechnung freigegeben.

Python-Komponenten: PySide6/Qt (LGPL 3/GPL, dynamische Bibliotheken),
lxml (BSD und mitgelieferte libxml2/libxslt-Lizenzen), pypdf (BSD 3),
SaxonC-HE (MPL 2), cryptography (Apache 2/BSD), pywin32 (PSF-Lizenz),
PyInstaller (GPL mit Bootloader-Ausnahme). Das Windows-Paket enthält die
Lizenzdateien der installierten Distributionen und die Quell-/Versionshinweise.
Quellen zur Anwendung und Änderungen an der Integration bleiben im Repository
verfügbar; Drittanbieter-Bibliotheken werden nicht verändert.

Sicherheitsgrenzen: XML ohne DTD, externe Entitäten oder Netzabrufe; Dateilimit
64 MiB, XML 8 MiB. Anhänge werden nicht ausgeführt. Die Prüfung enthält keine
automatische vollständige semantische Gleichheitsprüfung beliebiger PDF-Layouts.
