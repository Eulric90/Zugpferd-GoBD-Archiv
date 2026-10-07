"""Produce a portable Windows ZIP with a published SHA-256 checksum."""

import hashlib
import shutil
import tomllib
import zipfile
from pathlib import Path


def project_version() -> str:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as stream:
        return tomllib.load(stream)["project"]["version"]


def main() -> None:
    output = Path("dist")
    archive = Path(
        shutil.make_archive(
            str(output / f"ZugpferdArchiv-{project_version()}-Windows-x64"),
            "zip",
            root_dir=output,
            base_dir="ZugpferdArchiv",
        )
    )
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED) as package:
        package.write(
            output / "Install-ProtectedArchive.ps1", "Install-ProtectedArchive.ps1"
        )
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii"
    )
    print(archive, digest)


if __name__ == "__main__":
    main()
