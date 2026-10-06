"""Explicit UAC action using the executable registered in the protected SCM entry."""

from pathlib import Path
import subprocess

from .errors import ArchiveError


def backup_key_as_admin(root: Path, destination: Path) -> bool:
    import pywintypes
    import win32service
    import win32event
    import win32process
    from win32com.shell import shell, shellcon
    from .service import SERVICE_NAME

    manager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
    service = win32service.OpenService(
        manager, SERVICE_NAME, win32service.SERVICE_QUERY_CONFIG
    )
    try:
        binary_path = win32service.QueryServiceConfig(service)[3]
    finally:
        win32service.CloseServiceHandle(service)
        win32service.CloseServiceHandle(manager)
    if not binary_path.startswith('"'):
        raise ArchiveError("Unerwartete Dienstkonfiguration; Admin-Anleitung verwenden")
    executable = binary_path.split('"')[1]
    try:
        result = shell.ShellExecuteEx(
            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
            lpVerb="runas",
            lpFile=executable,
            lpParameters=subprocess.list2cmdline(
                ["--root", str(root), "--backup-key", str(destination)]
            ),
            nShow=1,
        )
    except pywintypes.error as exc:
        if exc.winerror == 1223:
            return False
        raise
    handle = result["hProcess"]
    try:
        win32event.WaitForSingleObject(handle, win32event.INFINITE)
        if win32process.GetExitCodeProcess(handle) != 0:
            raise ArchiveError(
                "Admin-Schlüsselsicherung nicht abgeschlossen; Konsolenausgabe prüfen"
            )
    finally:
        handle.Close()
    return True
