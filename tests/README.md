# Test requirements

Tests must cover at least:
- SHA-256 deterministic hashing
- creation of base directory structure
- non-destructive behavior with existing directories/files
- media marker creation and validation
- wrong/duplicate media rejection
- copy + read-back verification
- identical existing archive object treated as already archived
- conflicting existing archive object rejected without overwrite
- changed source detection
- journal hash-chain validation and tamper detection
- A/B comparison
- missing/corrupt file detection
- interrupted temporary-copy recovery behavior

Use temporary directories and mocks; tests must not require real USB media.

