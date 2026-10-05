# Codex / Agent Instructions

## Mission
Build a conservative Windows desktop application for redundant, integrity-verifiable invoice archiving. Do not claim that software alone creates GoBD compliance.

## Non-negotiable invariants
- Never modify invoice source files.
- Never silently overwrite or delete an archived invoice.
- SHA-256 is required for content integrity.
- After copy, hash the destination by reading it back from that medium.
- A conflicting existing destination is a hard error.
- Never identify an archive medium only by Windows drive letter.
- Do not mark a backup successful unless both configured media have been written and verified.
- Journal entries are append-oriented and hash chained.
- Destructive operations require explicit design review; V1 should expose no archive-delete feature.
- Preserve original filename, relative source path, size, timestamps where useful, archive timestamp and SHA-256 in metadata.
- Core archive logic must be independent from the GUI and unit-testable.

## Stack
- Python 3.12+
- PySide6 GUI
- pytest
- pathlib
- hashlib
- JSON/JSONL for portable metadata unless a stronger need emerges
- PyInstaller for Windows packaging

## Development
Use small modules, type hints, explicit exceptions and deterministic tests. Filesystem tests must use temporary directories. Abstract removable-drive discovery so it can be mocked outside Windows.

Before merging a feature, add tests for failure cases, especially hash mismatch, duplicate/conflicting content, missing media and interrupted copy.
