# V1.0 Specification

## 1. Local working structure
Default root: `C:\Rechnungen`.

On first-run setup create:
- `Eingang/<YEAR>/`
- `Ausgang/<YEAR>/`
- `Archivverwaltung/Protokolle/`
- `Archivverwaltung/Pruefberichte/`
- `Archivverwaltung/Konfiguration/`

Never overwrite existing user content. Ensure current-year folders on startup/backup.

## 2. GUI
Provide:
- root-folder selector plus button to create default C: structure
- dropdown/status for Archive A
- dropdown/status for Archive B
- setup/register-media workflow
- backup button
- full-integrity-check button
- A/B comparison
- visible last backup and counts
- clear success/warning/error messages

Long operations must not freeze the UI.

## 3. Media registration
Each archive medium receives a machine-readable marker containing:
- schema version
- archive ID
- medium role A or B
- medium UUID
- creation timestamp

A and B must share archive ID but have distinct medium UUIDs and roles. Reject duplicate roles and unexpected media.

## 4. Archive layout
Recommended:
`Archive/<year>/Eingang/...`
`Archive/<year>/Ausgang/...`
`Manifest/`
`Journal/`
`Pruefberichte/`
`Verfahrensdokumentation/`

Preserve source-relative organization sufficiently to prevent filename collisions.

## 5. Backup transaction
For each candidate file:
1. obtain source metadata and SHA-256
2. determine immutable destination
3. if destination exists, hash it
4. identical hash = already archived; no rewrite
5. differing hash = hard conflict; preserve both existing archive and source, log error
6. copy to temporary destination on medium
7. flush/close
8. read destination and calculate SHA-256
9. only after equality, atomically rename temporary file to final name where supported
10. record metadata/journal event

Perform and verify on A and B. Run result is successful only when required files are verified on both.

Interrupted temporary files must be recognizable and safely recoverable without treating them as archived originals.

## 6. Changed source
If the same logical/relative source path was previously archived with a different hash, do not replace history. Flag it prominently and preserve the old archive object. V1 may quarantine/archive the changed version under a unique immutable object name only when metadata clearly links both versions; otherwise fail safely and require user action.

## 7. Journal
Use canonical serialization for hash calculation. Each entry includes its predecessor hash. At minimum:
- sequence
- timestamp
- event type
- relevant file identity/hash
- previous entry hash
- entry hash

Provide journal-chain verification. A hash chain is tamper-evident, not magical write-once storage; documentation must say so.

## 8. Integrity check
Verify:
- media identity
- all manifest records resolve to existing files
- SHA-256 matches
- journal chain validates
- A/B expected content agrees

Report missing, changed, unexpected/conflicting and valid items separately.

## 9. Reports
Generate human-readable backup/integrity reports plus machine-readable data. Reports should contain timestamp, archive ID, medium IDs, totals and exceptions.

## 10. Export
Provide a non-destructive export for a selected date/year range, including selected originals plus index/manifest and a verification report. Export is a copy, never a move.

## 11. Scope/legal wording
UI/docs must use wording such as "GoBD-unterstützende Archivierung". Do not advertise legal certification or guaranteed GoBD conformity.

## 12. V1 exclusions
- no automatic deletion of retained invoices
- no silent repair of integrity failures
- no dependency on cloud services
- no requirement for administrator rights except where Windows itself requires them for the selected path
