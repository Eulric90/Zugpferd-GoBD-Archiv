import json
from pathlib import Path

from zugpferd_archiv.documentation import bundle_with_checksums


def test_old_documentation_renderer_preserves_existing_hashed_versions():
    folder = Path(__file__).parent / "fixtures/legacy-documentation"
    record = json.loads((folder / "document.json").read_text(encoding="utf-8"))
    for name, content in bundle_with_checksums(record).items():
        assert content == (folder / name).read_bytes(), name
