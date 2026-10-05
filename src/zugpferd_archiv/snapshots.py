"""Signed, immutable complete recovery checkpoints with independent references."""

from __future__ import annotations

import base64
import json
import uuid
import hashlib
import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from . import storage
from .errors import ArchiveError
from .journal import now

FOLDER = "Archivverwaltung/Sicherungsstaende"
MEDIA_FOLDER = "Sicherungsstaende"


def signing_key(key_folder: Path) -> Ed25519PrivateKey:
    key_folder = storage.safe_path(key_folder)
    key_folder.mkdir(parents=True, exist_ok=True)
    path = key_folder / "signing-key.pem"
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ArchiveError("Ungültiger Abschlussschlüssel")
        return key
    key = Ed25519PrivateKey.generate()
    storage.write_new(
        path,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    path.chmod(0o600)
    return key


def export_key(key_folder: Path, destination: Path, password: str) -> str:
    if len(password) < 12:
        raise ArchiveError("Schlüsselsicherung braucht mindestens 12 Zeichen Passwort")
    key = signing_key(key_folder)
    storage.write_new(
        destination,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(password.encode()),
        ),
    )
    return storage.sha256(destination)


def restore_key(
    key_folder: Path, backup: Path, password: str, expected_public_key: str
) -> str:
    target = storage.safe_path(key_folder / "signing-key.pem")
    if target.exists():
        raise ArchiveError("Vorhandener Signaturschlüssel wird nicht überschrieben")
    raw = storage.safe_path(backup).read_bytes()
    if b"BEGIN ENCRYPTED PRIVATE KEY" not in raw:
        raise ArchiveError("Nur verschlüsselte PKCS8-Schlüsselsicherungen zulässig")
    key = serialization.load_pem_private_key(raw, password=password.encode())
    if not isinstance(key, Ed25519PrivateKey):
        raise ArchiveError("Schlüsselsicherung enthält keinen Ed25519-Schlüssel")
    public = base64.b64encode(
        key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode()
    if public != expected_public_key.strip():
        raise ArchiveError(
            "Schlüsselsicherung widerspricht unabhängigem Referenzschlüssel"
        )
    storage.write_new(
        target,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    target.chmod(0o600)
    return public


def create_snapshot(root: Path, key_folder: Path) -> Path:
    existing = storage.child(root, FOLDER)
    if (
        existing.exists()
        and any(existing.iterdir())
        and not (key_folder / "signing-key.pem").is_file()
    ):
        raise ArchiveError(
            "Abschlussschlüssel fehlt; geschützt wiederherstellen, keinen neuen Schlüssel erzeugen"
        )
    key = signing_key(key_folder)
    identity = str(uuid.uuid4())
    destination = storage.child(root, FOLDER + "/" + identity)
    files = []
    sources = list(root.rglob("*"))
    for source in sources:
        relative = source.relative_to(root).as_posix()
        if (
            relative.startswith(FOLDER + "/")
            or source.name == ".zugpferd-operation.lock"
        ):
            continue
        storage.safe_path(source)
        if source.is_file():
            if ".partial-" in source.name:
                raise ArchiveError("Unvollständige lokale Datei vor Abschluss prüfen")
            digest = storage.sha256(source)
            files.append(dict(path=relative, sha256=digest, size=source.stat().st_size))
    manifest = dict(
        schema_version=1,
        id=identity,
        timestamp=now(),
        files=files,
        public_key=base64.b64encode(
            key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
        ).decode(),
    )
    signature = base64.b64encode(key.sign(storage.canonical(manifest))).decode()
    storage.write_new(
        destination / "manifest.json",
        storage.canonical(manifest | {"signature": signature}),
    )
    resume_snapshot(destination, root)
    return destination


def verify_snapshot(
    snapshot: Path, expected_public_key: str | None = None, allow_missing: bool = False
) -> dict:
    try:
        manifest = json.loads(
            storage.safe_path(snapshot / "manifest.json").read_text(encoding="utf-8")
        )
        signature = manifest.pop("signature")
        if (
            expected_public_key is not None
            and manifest["public_key"] != expected_public_key
        ):
            raise ArchiveError(
                "Abschlussschlüssel widerspricht unabhängigem Referenzschlüssel"
            )
        key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(manifest["public_key"], validate=True)
        )
        key.verify(
            base64.b64decode(signature, validate=True), storage.canonical(manifest)
        )
        seen = set()
        for item in manifest["files"]:
            if item["path"].casefold() in seen:
                raise ArchiveError("Doppelter Sicherungspfad")
            seen.add(item["path"].casefold())
            path = storage.child(snapshot, "Dateien/" + item["path"])
            if allow_missing and not path.exists():
                continue
            if (
                path.stat().st_size != item["size"]
                or storage.sha256(path) != item["sha256"]
            ):
                raise ArchiveError("Sicherungsstand-Datei fehlt oder verändert")
        expected = {"manifest.json"} | {
            "Dateien/" + i["path"] for i in manifest["files"]
        }
        actual = {
            p.relative_to(snapshot).as_posix()
            for p in snapshot.rglob("*")
            if p.is_file()
        }
        partials = {name for name in actual if ".partial-" in Path(name).name}
        actual -= partials
        if (not allow_missing and actual != expected) or actual - expected:
            raise ArchiveError("Unbekannte/unvollständige Datei im Sicherungsstand")
        manifest["warnings"] = sorted(partials)
        return manifest
    except InvalidSignature as exc:
        raise ArchiveError("Abschlusssignatur ungültig") from exc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ArchiveError("Sicherungsstand/Signatur nicht lesbar") from exc


def resume_snapshot(snapshot: Path, root: Path) -> None:
    manifest = verify_snapshot(snapshot, allow_missing=True)
    for item in manifest["files"]:
        target = storage.child(snapshot, "Dateien/" + item["path"])
        if target.exists():
            continue
        source = storage.child(root, item["path"])
        if storage.sha256(source) == item["sha256"]:
            storage.verified_copy(source, target, item["sha256"])
        elif item["path"].endswith(".jsonl"):
            # Logs can have appended failure/retry events since the signed intent.
            # Copy only the exact signed prefix into a new, private temporary file.
            with tempfile.TemporaryDirectory(prefix="zugpferd-prefix-") as folder:
                prefix = Path(folder) / "prefix.jsonl"
                digest = hashlib.sha256()
                remaining = item["size"]
                with source.open("rb") as original, prefix.open("xb") as output:
                    while remaining:
                        block = original.read(min(remaining, 1024 * 1024))
                        if not block:
                            raise ArchiveError("Journal vor Wiederanlauf gekürzt")
                        output.write(block)
                        digest.update(block)
                        remaining -= len(block)
                if digest.hexdigest() != item["sha256"]:
                    raise ArchiveError("Signierter Journal-Präfix widerspricht Quelle")
                storage.verified_copy(prefix, target, item["sha256"])
        else:
            raise ArchiveError("Quelle eines offenen Sicherungsstands verändert")
    verify_snapshot(snapshot)


def replicate_snapshot(snapshot: Path, a: Path, b: Path, validate=None) -> None:
    manifest = verify_snapshot(snapshot)
    for medium in (a, b):
        if validate:
            validate()
        target = storage.child(medium, MEDIA_FOLDER + "/" + manifest["id"])
        storage.verified_copy(
            snapshot / "manifest.json",
            target / "manifest.json",
            storage.sha256(snapshot / "manifest.json"),
        )
        for item in manifest["files"]:
            if validate:
                validate()
            relative = "Dateien/" + item["path"]
            storage.verified_copy(
                storage.child(snapshot, relative),
                storage.child(target, relative),
                item["sha256"],
            )
        storage.verified_copy(
            snapshot / "manifest.json",
            target / "manifest.json",
            storage.sha256(snapshot / "manifest.json"),
        )
        verify_snapshot(target, manifest["public_key"])
        if validate:
            validate()


def audit_snapshots(
    root: Path, a: Path, b: Path, require_equal: bool = True
) -> list[dict]:
    warnings = []
    key_path = root.parent / ("." + root.name + "-Schluessel") / "signing-key.pem"
    local_folder = storage.child(root, FOLDER)
    expected_key = None
    if local_folder.exists() and any(local_folder.iterdir()):
        if not key_path.is_file():
            # Pure recovery inspection may explicitly pin an independent public key;
            # live archive verification requires its protected signing identity.
            raise ArchiveError("Geschützter Abschlussschlüssel fehlt")
        key = signing_key(key_path.parent)
        expected_key = base64.b64encode(
            key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
        ).decode()
    from .journal import Journal

    committed = {
        e["data"]["snapshot"]
        for e in Journal(root / "Archivverwaltung/Register/events.jsonl").verify()
        if e["event"] == "register_backup_verified"
    }
    sets = []
    for medium in (a, b):
        folder = storage.child(medium, MEDIA_FOLDER)
        ids = set()
        if folder.exists():
            for snapshot in folder.iterdir():
                if not snapshot.is_dir():
                    raise ArchiveError("Unerwartete Datei bei Sicherungsständen")
                local = storage.child(root, FOLDER + "/" + snapshot.name)
                if (
                    not (snapshot / "manifest.json").exists()
                    and not require_equal
                    and snapshot.name not in committed
                ):
                    intent = verify_snapshot(local, expected_key, allow_missing=True)
                    expected_files = {
                        "Dateien/" + i["path"]: i for i in intent["files"]
                    }
                    for path in snapshot.rglob("*"):
                        if path.is_file() and ".partial-" not in path.name:
                            item = expected_files.get(
                                path.relative_to(snapshot).as_posix()
                            )
                            if not item or storage.sha256(path) != item["sha256"]:
                                raise ArchiveError(
                                    "Unbekanntes/widersprüchliches Objekt im offenen Sicherungsstand"
                                )
                    continue
                manifest = verify_snapshot(
                    snapshot,
                    expected_key,
                    allow_missing=not require_equal and snapshot.name not in committed,
                )
                warnings.extend(
                    dict(
                        kind="interrupted_snapshot",
                        path=str(snapshot / name),
                        detail="Unvollständige Arbeitsdatei erhalten; keine abgeschlossene Archivdatei",
                    )
                    for name in manifest.get("warnings", [])
                )
                ids.add(manifest["id"])
                local = storage.child(root, FOLDER + "/" + manifest["id"])
                if not local.is_dir() or storage.sha256(
                    local / "manifest.json"
                ) != storage.sha256(snapshot / "manifest.json"):
                    raise ArchiveError(
                        "Unabhängiger Sicherungsstand fehlt oder widerspricht lokaler Referenz"
                    )
                for item in manifest["files"]:
                    current_path = storage.child(root, item["path"])
                    if (
                        not item["path"].endswith(".jsonl")
                        and item["path"] != ".protected-service.json"
                    ):
                        if (
                            not current_path.is_file()
                            or storage.sha256(current_path) != item["sha256"]
                        ):
                            raise ArchiveError(
                                "Lokales abgeschlossenes Original/Verwaltungsobjekt fehlt oder verändert"
                            )
                    if item["path"].endswith(".jsonl"):
                        previous_path = storage.child(
                            snapshot, "Dateien/" + item["path"]
                        )
                        if (
                            not previous_path.exists()
                            and not require_equal
                            and snapshot.name not in committed
                        ):
                            continue
                        previous = storage.child(
                            snapshot, "Dateien/" + item["path"]
                        ).read_bytes()
                        current_path = storage.child(root, item["path"])
                        if (
                            not current_path.is_file()
                            or not current_path.read_bytes().startswith(previous)
                        ):
                            raise ArchiveError(
                                "Journal nach unabhängigem Abschluss verändert/gekürzt"
                            )
        sets.append(ids)
        if committed - ids:
            raise ArchiveError(
                "Bereits abgeschlossener Sicherungsstand fehlt; keine automatische Reparatur"
            )
    if require_equal and sets[0] != sets[1]:
        raise ArchiveError("A/B-Sicherungsstände unvollständig")
    return warnings
