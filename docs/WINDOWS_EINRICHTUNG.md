# Geschütztes Windows-Archiv einrichten

Voraussetzungen: Windows 11, lokaler NTFS-Datenträger, zwei verschiedene USB-Sticks,
persönliche Standardkonten für Hauptverantwortlichen und Vertretung, ein separates
Administratorkonto für die Einrichtung. Die Anwendung erzeugt keine Rechnungen;
PDF24 bleibt dafür zuständig. Das portable Programm benötigt kein installiertes Python.

## Einmalige Installation

1. Windows-ZIP vollständig entpacken. SHA-256 mit der mitgelieferten `.sha256`
   vergleichen (`Get-FileHash <ZIP> -Algorithm SHA256`).
2. Die beiden bestehenden persönlichen Windows-Konten bereitstellen. Keine gemeinsame
   Benutzerkennung nutzen. Konten werden vom Installer nicht neu angelegt.
3. Auf jedem Stick einen eigenen Archivordner vorsehen, z.B. `E:\GoBD-A` und
   `F:\GoBD-B`. Kennzeichnung A/B am Stick anbringen. NTFS erlaubt lokale Zugriffsrechte;
   exFAT/FAT bietet diesen Schutz nicht. Der Installer formatiert nicht.
4. PowerShell als Administrator öffnen, zum entpackten ZIP wechseln und ausführen:

```powershell
.\Install-ProtectedArchive.ps1 -ArchiveRoot 'C:\GoBD\Archiv' `
  -MediumA 'E:\GoBD-A' -MediumB 'F:\GoBD-B' `
  -Operators @('KontoBruder','KontoVertretung')
```

Der Installer prüft NTFS, kopiert das Programm nach `Program Files\ZugpferdArchiv`,
registriert/bindet A/B, richtet `ZugpferdArchivWriter` mit virtueller Dienstidentität
ein und schützt Archiv, Konfiguration und getrennten Schlüsselordner mit ACLs.
Bediener erhalten nur Leserechte auf übernommene Archivdaten. Bei NTFS-Unterordnern
der Sticks werden die Archivordner ebenfalls geschützt. Dateien/Eigentümerrechte
werden sichtbar auf Administrator/Dienst umgestellt; Belegbytes bleiben unverändert.
A/B müssen verschiedene physische Datenträger sein; zwei Partitionen desselben
Sticks werden abgelehnt. Gerätekennungen bleiben unabhängig vom Laufwerksbuchstaben.
Andere Rechner/Administratoren können normale USB-Sticks weiterhin verändern.

Der Container (z.B. `C:\GoBD`) muss ausschließlich das Archiv und dessen Schlüsselordner
enthalten. Der Installer schützt auch diesen Container gegen Umbenennen/Löschen
durch Bediener und lehnt gemeinsame Ordner mit fremden Daten ab.

Der Schlüssel liegt separat in `C:\GoBD\.Archiv-Schluessel`; Bediener erhalten dort
keinen Zugriff. Dienstkonfiguration/Staging liegen unter `ProgramData\ZugpferdArchiv`.
Keinen Schlüssel ungeschützt auf A/B oder in den Rechnungsbestand legen.

5. Persönlichen Benutzer neu anmelden, Oberfläche als Standardbenutzer starten,
   `C:\GoBD\Archiv` als Grundordner wählen. `Betrieb einrichten` ausfüllen, digitale
   Umstellung und Altbestand festlegen. `Jahresserie einrichten`: bisherigen
   Trennzeichen- und Nummernstand bestätigen, nicht mitten im Jahr bei 0001 beginnen.
6. `Schlüssel geschützt sichern`: Windows-Adminabfrage bestätigen. Das Passwort wird
   verdeckt im Admin-Konsolenfenster eingegeben; Bediener dürfen den privaten
   Signaturschlüssel auch über den Dienst nicht exportieren. Starkes separates Passwort verwenden. Verschlüsselte
   PEM-Datei und zugehörige `.public-key.txt` getrennt sicher verwahren; Referenzschlüssel
   zusätzlich unabhängig ausdrucken/verwahren. Passwort nicht im Rechnungsordner speichern.
7. Verfahrensdokumentation prüfen, betrieblich freigeben und auf A/B sichern.

Windows zeigt Edition und Version im Einrichtungsassistenten. BitLocker/
Geräteverschlüsselung und Wiederherstellungsschlüssel gesondert prüfen; Home/Pro
bieten unterschiedliche Funktionen. Verschlüsselung wird nicht automatisch aktiviert.

## Bestehende V1 übernehmen

Neuen leeren Zielordner wählen und beim obigen Aufruf
`-MigrateFrom 'C:\Rechnungen'` ergänzen. Vor der Übernahme prüft die Anwendung den
Altbestand und führt eine vollständige A/B-Sicherung aus. Originale, Metadaten,
Dokumentationsfassungen und Journale werden bytegleich zurückgelesen übernommen.
Der alte Bestand bleibt erhalten. Konflikte, fehlende Originale oder ungeklärte
Sperr-/Partialdateien verhindern die Migration; keine automatische Reparatur.
Elektronische Altoriginale aus dem Portal über den historischen Assistenten ergänzen.
Papier/Scans als Altbestand kennzeichnen; Papierordner nicht vernichten.

## Geräteabnahme vor dem Livebetrieb

- Mit beiden persönlichen Konten: Original lesen, Änderung/Löschung außerhalb der
  Anwendung versuchen – beides muss im geschützten Bestand verweigert werden.
- Je eine echte Ein- und Ausgangsrechnung übernehmen; XML/PDF persönlich vergleichen.
- Gleichen Beleg erneut importieren: kein zweiter Registerbeleg. Neue Datei mit
  bereits belegter Ausgangsnummer: Konflikt. Reservierung bleibt nach Abbruch erhalten.
- Mit beiden Sticks sichern, TXT-/JSON-Berichte und Registerstatus prüfen.
- Einen Stick entfernen: kein A/B-Erfolg. Wieder anschließen und fortsetzen.
- Vollständige Integritätsprüfung; wiederhergestellten Bestand öffnen und Stichproben
  samt Originalhash/Nummer/Beziehungen und lesbarer Anzeige vergleichen.
- Neutralen Monats-/Rechnungsdatumexport testen; Register und Originalkopien drucken.
- Abnahme, Konten, Aufbewahrungsorte, Rhythmus und Schlüsselverwahrung dokumentieren;
  Buchführungsumfang und Übergabe mit Steuerberatung abstimmen.

## Wiederherstellung

Im Register `Wiederherstellung in neuen Ordner` wählen. Den UUID-Ordner unter
`Sicherungsstaende` auf A oder B auswählen, unabhängig verwahrten öffentlichen
Referenzschlüssel angeben und einen neuen Zielordner erstellen lassen.
Alle im signierten Stand enthaltenen Originale, Register, Beziehungen, Konfiguration,
Nachweise und Dokumentationen werden geprüft kopiert. Vorhandene Ordner bleiben unberührt.
Zuerst als Prüfkopie verwenden. Für die Fortsetzung den jüngsten vollständigen Stand wählen,
passenden Schlüssel wiederherstellen und beide Medien prüfen. Frühere Manifestreferenzen
bleiben erhalten; fehlende Referenzobjekte auf A/B werden nicht still repariert.
Vor Livebetrieb Admin-Installation/NTFS-Rechte neu einrichten.

Ein privater Signaturschlüssel gehört nicht in den allgemeinen Sicherungsstand.
Falls der geschützte Schlüssel fehlt, Dienst stoppen und als Administrator ausführen:

```powershell
& 'C:\Program Files\ZugpferdArchiv\ZugpferdArchivService.exe' `
  --restore-key 'G:\GetrennteSicherung\Archivschluessel.pem' `
  --reference-key 'G:\Referenz\Archivschluessel.pem.public-key.txt' `
  --root 'C:\GoBD\Archiv'
```

Das Passwort wird verdeckt abgefragt, nicht als Kommandozeilenargument gespeichert.
Vorhandene Schlüssel werden nicht überschrieben. Anschließend Dienst-/Schlüssel-ACLs
prüfen, Dienst starten und vollständige Integritätsprüfung durchführen. Ohne passende
Schlüsselsicherung keinen neuen Schlüssel als Ersatz für einen bestehenden Stand erzeugen.

Sperrdateien nach Prozess-/Stromabbruch nur nach dokumentierter Prüfung entfernen:
kein laufender Dienstvorgang, Originale/Journal prüfen, Fehlerbericht erhalten.
Archivinhalte/Journale niemals zur Behebung eines Konflikts bearbeiten oder löschen.
