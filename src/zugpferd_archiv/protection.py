"""Verify actual NTFS descriptors, including owner and parent deletion rights."""

from __future__ import annotations

from pathlib import Path

from .errors import ArchiveError
from .storage import safe_path

WRITE_MASK = 0x40000000 | 0x10000000 | 0x000D0156


def validate_acl(
    aces: list[tuple[int, int, str]],
    owner: str,
    trusted: set[str],
    parent_only: bool = False,
) -> None:
    if owner not in trusted:
        raise ArchiveError(
            "NTFS-Eigentümer ist keine geschützte Schreib-/Adminidentität"
        )
    for kind, mask, sid in aces:
        if (
            kind == 0
            and sid not in trusted
            and mask & (0x10000000 | 0x000D0040 if parent_only else WRITE_MASK)
        ):
            raise ArchiveError(
                "NTFS-Rechte erlauben ungeschützte Änderung/Löschung; Admin-Abnahme erforderlich"
            )


def audit_windows_protection(config: dict) -> None:
    import win32net
    import win32security

    from .service import SERVICE_NAME

    root = safe_path(Path(config["root"]))
    service_sid = win32security.ConvertSidToStringSid(
        win32security.LookupAccountName(None, f"NT SERVICE\\{SERVICE_NAME}")[0]
    )
    admin_sid = win32security.ConvertStringSidToSid("S-1-5-32-544")
    admin_name = win32security.LookupAccountSid(None, admin_sid)[0]
    trusted = {"S-1-5-18", "S-1-5-32-544", service_sid}
    trusted.add(
        win32security.ConvertSidToStringSid(
            win32security.LookupAccountName(None, "NT SERVICE\\TrustedInstaller")[0]
        )
    )
    resume = 0
    while True:
        members, _, resume = win32net.NetLocalGroupGetMembers(
            None, admin_name, 0, resume
        )
        trusted.update(
            win32security.ConvertSidToStringSid(member["sid"]) for member in members
        )
        if not resume:
            break

    def check(path: Path, parent_only=False):
        descriptor = win32security.GetNamedSecurityInfo(
            str(safe_path(path)),
            win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION
            | win32security.DACL_SECURITY_INFORMATION,
        )
        dacl = descriptor.GetSecurityDescriptorDacl()
        if dacl is None:
            raise ArchiveError("Unbeschränkte NTFS-DACL im Schutzprofil")
        aces = []
        for index in range(dacl.GetAceCount()):
            ace = dacl.GetAce(index)
            header, mask = ace[:2]
            if header[1] & 8:  # inheritance-only does not grant access on this object
                continue
            if header[0] not in (0, 1):
                raise ArchiveError(
                    "Unerwarteter NTFS-ACE-Typ; Admin-Prüfung erforderlich"
                )
            aces.append((header[0], mask, win32security.ConvertSidToStringSid(ace[-1])))
        validate_acl(
            aces,
            win32security.ConvertSidToStringSid(
                descriptor.GetSecurityDescriptorOwner()
            ),
            trusted,
            parent_only,
        )

    key_folder = root.parent / ("." + root.name + "-Schluessel")
    for folder in (root, key_folder):
        check(folder)
        for path in folder.rglob("*"):
            check(path)
    for parent in root.parents:
        check(parent, parent_only=True)
