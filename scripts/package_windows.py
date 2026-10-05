"""Produce a portable Windows ZIP with a published SHA-256 checksum."""
import hashlib
import shutil
from pathlib import Path


def main() -> None:
    output = Path('dist')
    archive = Path(shutil.make_archive(str(output / 'ZugpferdArchiv-1.0.0-Windows-x64'),
                                      'zip', root_dir=output, base_dir='ZugpferdArchiv'))
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(archive, digest)


if __name__ == '__main__':
    main()
