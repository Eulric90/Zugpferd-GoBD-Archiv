"""Exercise the frozen SCM service with a real standard-user token and NTFS ACLs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import win32con
import win32net
import win32netcon
import win32security
import win32service

from zugpferd_archiv.service import SERVICE_NAME, request
from zugpferd_archiv.windows_service import configuration_path


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(
            f"Windows-Provisioning fehlgeschlagen: {args[0]} exit {result.returncode}"
        )


def acl(path, service_sid, operator_sid=None):
    descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        "D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
        f"(A;OICI;FA;;;{service_sid})"
        + (f"(A;OICI;GRGX;;;{operator_sid})" if operator_sid else ""),
        1,
    )
    win32security.SetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION
        | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        descriptor.GetSecurityDescriptorDacl(),
        None,
    )


def main():
    if os.name != "nt":
        raise RuntimeError("Windows required")
    account = "ZA" + uuid.uuid4().hex[:12]
    group = "ZG" + uuid.uuid4().hex[:12]
    password = uuid.uuid4().hex + "!aA9"
    executable = Path(sys.argv[1]).resolve()
    config_path = configuration_path()
    if config_path.exists():
        raise RuntimeError("Test darf keine bestehende Dienstkonfiguration ersetzen")
    manager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    service_handle = None
    try:
        win32net.NetUserAdd(
            None,
            1,
            dict(
                name=account,
                password=password,
                priv=1,
                home_dir="",
                comment="Temporary CI standard user",
                flags=win32netcon.UF_SCRIPT | win32netcon.UF_DONT_EXPIRE_PASSWD,
                script_path="",
            ),
        )
        win32net.NetLocalGroupAdd(
            None, 1, dict(name=group, comment="Temporary CI archive operators")
        )
        win32net.NetLocalGroupAddMembers(None, group, 3, [dict(domainandname=account)])
        operator_sid = win32security.LookupAccountName(None, group)[0]
        service_handle = win32service.CreateService(
            manager,
            SERVICE_NAME,
            SERVICE_NAME,
            win32service.SERVICE_ALL_ACCESS,
            win32service.SERVICE_WIN32_OWN_PROCESS,
            win32service.SERVICE_DEMAND_START,
            win32service.SERVICE_ERROR_NORMAL,
            f'"{executable}" --service',
            None,
            0,
            None,
            f"NT SERVICE\\{SERVICE_NAME}",
            None,
        )
        command("sc.exe", "sidtype", SERVICE_NAME, "unrestricted")
        service_sid = win32security.ConvertSidToStringSid(
            win32security.LookupAccountName(None, f"NT SERVICE\\{SERVICE_NAME}")[0]
        )
        command(
            "icacls.exe",
            str(executable.parent),
            "/grant",
            f"*{service_sid}:(OI)(CI)RX",
            "/T",
            "/C",
        )
        with tempfile.TemporaryDirectory(
            prefix="zugpferd-protection-", dir=os.environ["ProgramData"]
        ) as directory:
            base = Path(directory)
            root, staging, keys = (
                base / "Archive",
                base / "Staging",
                base / ".Archive-Schluessel",
            )
            for folder in (root, staging, keys):
                folder.mkdir()
            (root / ".protected-service.json").write_text("{}")
            original = root / "original.pdf"
            original.write_bytes(b"immutable original")
            acl(base, service_sid, win32security.ConvertSidToStringSid(operator_sid))
            acl(root, service_sid, win32security.ConvertSidToStringSid(operator_sid))
            acl(staging, service_sid)
            acl(keys, service_sid)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    dict(
                        root=str(root),
                        staging=str(staging),
                        operator_group_sid=win32security.ConvertSidToStringSid(
                            operator_sid
                        ),
                    )
                ),
                encoding="utf-8",
            )
            acl(config_path.parent, service_sid)
            win32service.StartService(service_handle, None)
            for _ in range(100):
                if (
                    win32service.QueryServiceStatus(service_handle)[1]
                    == win32service.SERVICE_RUNNING
                ):
                    break
                time.sleep(0.1)
            else:
                import win32evtlog

                diagnostics = []
                for log_name in ("Application", "System"):
                    log = win32evtlog.OpenEventLog(None, log_name)
                    try:
                        events = win32evtlog.ReadEventLog(
                            log,
                            win32evtlog.EVENTLOG_BACKWARDS_READ
                            | win32evtlog.EVENTLOG_SEQUENTIAL_READ,
                            0,
                        )
                        for event in events[:30]:
                            if any(
                                word in event.SourceName.casefold()
                                for word in ("python", "zugpferd", "service control")
                            ):
                                diagnostics.append(
                                    dict(
                                        source=event.SourceName,
                                        id=event.EventID,
                                        details=event.StringInserts,
                                    )
                                )
                    finally:
                        win32evtlog.CloseEventLog(log)
                print(json.dumps(diagnostics, ensure_ascii=True))
                raise RuntimeError(
                    f"Frozen service failed to enter RUNNING: {win32service.QueryServiceStatus(service_handle)}"
                )
            encrypted = request(
                dict(operation="export_key", password="CI-secure-recovery-password")
            )
            assert encrypted
            token = win32security.LogonUser(
                account,
                ".",
                password,
                win32con.LOGON32_LOGON_INTERACTIVE,
                win32con.LOGON32_PROVIDER_DEFAULT,
            )
            win32security.ImpersonateLoggedOnUser(token)
            try:
                for operation in (
                    lambda: original.write_bytes(b"forged"),
                    lambda: original.unlink(),
                ):
                    try:
                        operation()
                    except PermissionError:
                        pass
                    else:
                        raise AssertionError(
                            "Standard user can change/delete protected original"
                        )
                try:
                    (keys / "stolen.pem").write_bytes(b"attack")
                except PermissionError:
                    pass
                else:
                    raise AssertionError("Standard user can write key store")
                request(
                    dict(
                        operation="start_series",
                        args=[2026, "", 0, "Windows CI verified baseline"],
                        actor="forged",
                    )
                )
                assert request(dict(operation="reserve", args=[2026])) == "20260001"
                events = request(dict(operation="events", args=[]))
                actual_sid = win32security.ConvertSidToStringSid(
                    win32security.GetTokenInformation(token, win32security.TokenUser)[0]
                )
                assert events[0]["data"]["actor"] == actual_sid
                try:
                    request(dict(operation="delete", path=str(original)))
                except Exception:
                    pass
                else:
                    raise AssertionError("Delete API unexpectedly accepted")
                try:
                    request(
                        dict(
                            operation="export_key",
                            password="CI-secure-recovery-password",
                        )
                    )
                except Exception:
                    pass
                else:
                    raise AssertionError(
                        "Standard user can export signing key through service"
                    )
                try:
                    (keys / "signing-key.pem").read_bytes()
                except PermissionError:
                    pass
                else:
                    raise AssertionError("Standard user can read signing key")
            finally:
                win32security.RevertToSelf()
                token.Close()
            assert original.read_bytes() == b"immutable original"
            win32service.ControlService(
                service_handle, win32service.SERVICE_CONTROL_STOP
            )
            for _ in range(100):
                if (
                    win32service.QueryServiceStatus(service_handle)[1]
                    == win32service.SERVICE_STOPPED
                ):
                    break
                time.sleep(0.1)
            print(
                "Frozen SCM service: authenticated SID, durable numbering, encrypted key export and real standard-user NTFS write/delete denial passed"
            )
    finally:
        if service_handle:
            try:
                win32service.ControlService(
                    service_handle, win32service.SERVICE_CONTROL_STOP
                )
            except Exception:
                pass
            win32service.DeleteService(service_handle)
            win32service.CloseServiceHandle(service_handle)
        win32service.CloseServiceHandle(manager)
        if config_path.exists():
            config_path.unlink()
        try:
            win32net.NetUserDel(None, account)
            win32net.NetLocalGroupDel(None, group)
        except Exception:
            pass


if __name__ == "__main__":
    main()
