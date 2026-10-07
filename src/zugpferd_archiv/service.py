"""Narrow local named-pipe API. Caller SID comes from Windows impersonation."""

from __future__ import annotations

import base64
import json
import inspect
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from . import storage
from .errors import ArchiveError

PIPE = r"\\.\pipe\ZugpferdArchiv.Writer.v1"
SERVICE_NAME = "ZugpferdArchivWriter"
MAX_REQUEST = 96 * 1024 * 1024
IN_SERVICE = False


def protected(root: Path) -> bool:
    if os.name != "nt" or IN_SERVICE:
        return False
    try:
        marker = json.loads(
            (root / ".protected-service.json").read_text(encoding="utf-8")
        )
        return (
            marker["service"] == SERVICE_NAME
            and str(Path(marker["root"]).resolve()).casefold()
            == str(root.resolve()).casefold()
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


class Dispatcher:
    def __init__(self, root: Path, staging: Path):
        self.root, self.staging = storage.safe_path(root), storage.safe_path(staging)

    def call(self, request: dict, actor: str):
        from .register import Register
        from .core import ArchiveService

        if not isinstance(request, dict) or not actor:
            raise ArchiveError("Ungültige Dienstanfrage")
        if (
            request.get("archive_root")
            and Path(request["archive_root"]).resolve() != self.root.resolve()
        ):
            raise ArchiveError("Oberfläche ist mit anderem Dienstarchiv verbunden")
        operation = request.get("operation")
        if operation in ("ingest", "add_related", "mark_sent_mail"):
            filename = request.get("filename", "")
            if Path(filename).name != filename or not filename:
                raise ArchiveError("Ungültiger Importdateiname")
            self.staging.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=self.staging) as directory:
                source = storage.chil
d(Path(directory), filename)
                raw = base64.b64decode(request["content"], validate=True)
                if len(raw) > 64 * 1024 * 1024:
                    raise ArchiveError("Import überschreitet Größenlimit")
                storage.write_new(source, raw)
                register = Register(self.root, actor=actor)
                if operation == "mark_sent_mail":
                    return register.mark_sent(
                        request["id"],
                        request["sent_date"],
                        request["recipient"],
                        source,
                    )
                if operation == "add_related":
                    return register.add_related(request["id"], source, request["kind"])
                from .inspection import analyze_bounded

                validation = analyze_bounded(source)
                fields = dict(request["fields"])
                fields["_source_metadata"] = request.get("source_metadata")
                for key in (
                    "format",
                    "profile",
                    "validator_version",
                    "critical_errors",
                ):
                    fields[key] = validation.get(key)
                for key in (
                    "number",
                    "invoice_date",
                    "currency",
                    "net",
                    "tax",
                    "gross",
                ):
                    if validation.get(key) and str(fields.get(key)) != str(
                        validation[key]
                    ):
                        fields["critical_errors"].append(
                            f"Registerfeld {key} widerspricht führender XML"
                        )
                return register.ingest(source, fields)
        register_ops = {
            "tasks": 0,
            "explain_number": 2,
            "close_period": 3,
            "save_setup": 1,
            "business_setup": 0,
            "
start_series": 4,
            "reserve": 1,
            "records": 0,
            "events": 0,
            "series": 1,
            "correct": 3,
            "search": 3,
        }
        if operation in register_ops:
            args = request.get("args", [])
            if not isinstance(args, list) or len(args) != register_ops[operation]:
                raise ArchiveError("Ungültige Anzahl von Dienstargumenten")
            method = getattr(Register(self.root, actor=actor), operation)
            try:
                inspect.signature(method).bind(*args)
            except TypeError as exc:
                raise ArchiveError("Ungültige Dienstargumente") from exc
            return method(*args)
        if operation == "mark_sent":
            identity, sent_date, recipient, digest = request["args"]
            register = Register(self.root, actor=actor)
            record = next(
                (r for r in register.records() if r["id"] == identity), None
            )
            if record is None:
                raise ArchiveError("Unbekannte Beleg-ID")
            if digest != record["sha256"]:
                raise ArchiveError(
                    "Versand-Anhang entspricht nicht archiviertem Original"
                )
            return register.mark_sent(
                identity,
                sent_date,
                recipient,
                storage.child(self.root, record["original_relative"]),
            )
        if operation == "export_key":
            from .snapshots import signing_key
            from cryptography.hazmat.primitives import serialization

            password = request.get("password", "")
            if len(password) < 12:
                raise ArchiveError(
                    "Schlüsselsicherung braucht mindestens 12 Zeichen Passwort"
                )
            folder = self.root.parent / ("." + self.root.name + "-Schluessel")
            stands = self.root / "Archivverwaltung/Sicherungsstaende"
            if (
                stands.exists()
                and any(stands.iterdir())
                and not (folder / "signing-key.pem").is_f
ile()
            ):
                raise ArchiveError(
                    "Abschlussschlüssel fehlt; vorhandene Schlüsselsicherung geschützt wiederherstellen"
                )
            key = signing_key(folder)
            data = key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.BestAvailableEncryption(password.encode()),
            )
            return base64.b64encode(data).decode()
        service = ArchiveService(self.root)
        service.actor = actor
        if operation in ("backup", "check", "compare"):
            args = request.get("args", [])
            if len(args) != 2:
                raise ArchiveError("A/B-Auswahl fehlt")
            return getattr(service, operation)(*(Path(p) for p in args)).data()
        if operation == "verify_pair":
            from .reports import Report

            a, b = request["args"]
            service._pair(Path(a), Path(b), Report("identity"))
            return None
        if operation == "setup":
            return service.setup()
        if operation == "configuration":
            return service.configuration()
        if operation in ("last_backup", "last_backup_success"):
            return getattr(service, operation)()
        if operation == "configure":
            config = service.configuration()
            from .media import validate_pair, Medium

            args = request.get("args", [])
            validate_pair(
                Path(args[0]),
                Path(args[1]),
                Medium(**config["A"]),
                Medium(**config["B"]),
            )
            return None
        if operation == "create_documentation":
            from .documentation import DocumentationData

            args = request["args"]
            return service.create_documentation(
                Path(args[0]), Path(args[1]), DocumentationData(**args[2])
            ).data()
        if operation == "export"
:
            args = request["args"]
            # The service cannot write to a caller-selected destination. User process
            # exports verified read-only originals after the service has audited A/B.
            return service.check(Path(args[0]), Path(args[1])).data()
        raise ArchiveError("Dienstoperation nicht erlaubt")


def request(payload: dict):
    import win32file
    import win32pipe
    import pywintypes
    import time

    raw = storage.canonical(payload)
    if len(raw) > MAX_REQUEST:
        raise ArchiveError("Dienstanfrage zu groß")
    deadline = time.monotonic() + 5
    while True:
        try:
            win32pipe.WaitNamedPipe(
                PIPE, max(1, int((deadline - time.monotonic()) * 1000))
            )
            break
        except pywintypes.error as exc:
            if exc.winerror != 2 or time.monotonic() >= deadline:
                raise
            time.sleep(0.05)
    handle = win32file.CreateFile(PIPE, 0xC0000000, 0, None, 3, 0, None)
    try:
        import ctypes
        from ctypes import wintypes
        import win32service

        manager = win32service.OpenSCManager(
            None, None, win32service.SC_MANAGER_CONNECT
        )
        service = win32service.OpenService(
            manager, SERVICE_NAME, win32service.SERVICE_QUERY_STATUS
        )
        try:
            status = win32service.QueryServiceStatusEx(service)
            server_pid = ctypes.c_ulong()
            get_server_pid = ctypes.windll.kernel32.GetNamedPipeServerProcessId
            get_server_pid.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
            get_server_pid.restype = wintypes.BOOL
            if (
                not get_server_pid(int(handle), ctypes.byref(server_pid))
                or server_pid.value != status["ProcessId"]
            ):
                raise ArchiveError(
                    "Named-Pipe-Server ist nicht der eingerichtete Windows-Dienst"
                )
        finally:
      
      win32service.CloseServiceHandle(service)
            win32service.CloseServiceHandle(manager)
        win32pipe.SetNamedPipeHandleState(
            handle, win32pipe.PIPE_READMODE_MESSAGE, None, None
        )
        win32file.WriteFile(handle, raw)
        response = json.loads(win32file.ReadFile(handle, MAX_REQUEST)[1])
        if not response.get("ok"):
            raise ArchiveError(response.get("error", "Dienstfehler"))
        return response.get("result")
    finally:
        win32file.CloseHandle(handle)


class RemoteRegister:
    def __init__(self, root: Path, actor=None):
        self.root = storage.safe_path(root)
        from .journal import Journal

        self.journal = Journal(root / "Archivverwaltung/Register/events.jsonl")

    def _request(self, payload):
        return request(payload | {"archive_root": str(self.root)})

    def __getattr__(self, operation):
        if operation not in (
            "tasks",
            "explain_number",
            "close_period",
            "save_setup",
            "business_setup",
            "start_series",
            "reserve",
            "records",
            "events",
            "series",
            "correct",
            "search",
        ):
            raise AttributeError(operation)

        def call(*args, **kwargs):
            if kwargs:
                if operation != "search":
                    raise ArchiveError("Dienstargumente ungültig")
                args = (
                    kwargs.get("text", ""),
                    kwargs.get("first", "0001-01-01"),
                    kwargs.get("last", "9999-12-31"),
                )
            return self._request(dict(operation=operation, args=list(args)))

        return call

    def ingest(self, source: Path, fields: dict):
        stat = source.stat()
        return self._request(
            dict(
                operation="ingest",
                filename=source.name,
                content=base64.b64encode(source.read_
bytes()).decode(),
                fields=fields,
                source_metadata=dict(
                    path=str(source),
                    mtime_ns=stat.st_mtime_ns,
                    ctime_ns=stat.st_ctime_ns,
                ),
            )
        )

    def add_related(self, identity: str, source: Path, kind: str):
        return self._request(
            dict(
                operation="add_related",
                id=identity,
                kind=kind,
                filename=source.name,
                content=base64.b64encode(source.read_bytes()).decode(),
            )
        )

    def mark_sent(
        self, identity: str, sent_date: str, recipient: str, attachment: Path
    ):
        if attachment.suffix.casefold() == ".eml":
            return self._request(
                dict(
                    operation="mark_sent_mail",
                    id=identity,
                    sent_date=sent_date,
                    recipient=recipient,
                    filename=attachment.name,
                    content=base64.b64encode(attachment.read_bytes()).decode(),
                )
            )
        return self._request(
            dict(
                operation="mark_sent",
                args=[identity, sent_date, recipient, storage.sha256(attachment)],
            )
        )


class RemoteArchive:
    def __init__(self, root: Path, progress=None):
        self.root = storage.safe_path(root)
        self.progress = progress or (lambda text: None)

    def _request(self, payload):
        return request(payload | {"archive_root": str(self.root)})

    def __getattr__(self, operation):
        if operation not in (
            "setup",
            "configure",
            "configuration",
            "last_backup",
            "last_backup_success",
            "backup",
            "check",
            "compare",
            "create_documentation",
        ):
            raise AttributeError(operation)

        def call(*args):

            serialized = [
                asdict(arg)
                if hasattr(arg, "__dataclass_fields__")
                else str(arg)
                if isinstance(arg, Path)
                else arg
                for arg in args
            ]
            result = self._request(dict(operation=operation, args=serialized))
            if operation in ("backup", "check", "compare", "create_documentation"):
                from .reports import Report

                return Report(**result)
            return result

        return call

    def _pair(self, a, b, report):
        return self._request(dict(operation="verify_pair", args=[str(a), str(b)]))

    def export(
        self, a, b, destination, first_year, last_year, first_date=None, last_date=None
    ):
        report = self.check(a, b)
        if not report.success:
            return report
        from .reports import Report
        from .workflow import new_destination
        from datetime import datetime

        rows = storage.read_lines(storage.child(a, "Manifest/records.jsonl"))
        selected = [
            r
            for r in rows
            if first_year <= int(r["source_relative"].split("/")[1]) <= last_year
            and (
                not first_date
                or datetime.fromisoformat(r["archived_at"]).date() >= first_date
            )
            and (
                not last_date
                or datetime.fromisoformat(r["archived_at"]).date() <= last_date
            )
        ]
        for medium in (a, b):
            if destination.is_relative_to(medium) or medium.is_relative_to(destination):
                raise ArchiveError("Export muss außerhalb der Medien liegen")
        target = new_destination(self.root, destination)
        for record in selected:
            storage.verified_copy(
                storage.child(a, record["archive_relative"]),
                storage.child(target, "Originale/" + record["source_relative"]),
                record["sha
256"],
            )
        storage.write_new(
            target / "index.json",
            storage.canonical(
                dict(
                    records=selected,
                    year_range=[first_year, last_year],
                    archive_date_range=[str(first_date), str(last_date)],
                )
            ),
        )
        result = Report("export", success=True)
        result.totals["candidates"] = len(selected)
        result.totals["verified"] = len(selected)
        result.save(target / "Pruefberichte")
        return result


def serve(config: dict, stop=None):
    global IN_SERVICE
    IN_SERVICE = True
    import pywintypes
    import win32api
    import win32con
    import win32file
    import win32pipe
    import win32security

    service_sid = win32security.ConvertSidToStringSid(
        win32security.LookupAccountName(None, f"NT SERVICE\\{SERVICE_NAME}")[0]
    )
    descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        f"D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;{service_sid})(A;;GRGW;;;{config['operator_group_sid']})",
        1,
    )
    attributes = pywintypes.SECURITY_ATTRIBUTES()
    attributes.SECURITY_DESCRIPTOR = descriptor
    dispatch = Dispatcher(Path(config["root"]), Path(config["staging"]))
    pipe = win32pipe.CreateNamedPipe(
        PIPE,
        win32pipe.PIPE_ACCESS_DUPLEX | 0x00080000,
        win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | 8,
        1,
        MAX_REQUEST,
        MAX_REQUEST,
        5000,
        attributes,
    )
    while stop is None or not stop():
        try:
            try:
                win32pipe.ConnectNamedPipe(pipe, None)
            except pywintypes.error as exc:
                if (
                    exc.winerror != 535
                ):  # client connected between creation/disconnect and this call
                    raise
            if stop and stop():
                break
            raw = win32file.ReadFile(pipe, 
MAX_REQUEST)[1]
            win32security.ImpersonateNamedPipeClient(pipe)
            try:
                token = win32security.OpenThreadToken(
                    win32api.GetCurrentThread(), win32con.TOKEN_QUERY, True
                )
                try:
                    sid = win32security.GetTokenInformation(
                        token, win32security.TokenUser
                    )[0]
                    actor = win32security.ConvertSidToStringSid(sid)
                    group = win32security.ConvertStringSidToSid(
                        config["operator_group_sid"]
                    )
                    is_key_export = json.loads(raw).get("operation") == "export_key"
                    if is_key_export and not win32security.CheckTokenMembership(
                        token, win32security.ConvertStringSidToSid("S-1-5-32-544")
                    ):
                        raise ArchiveError(
                            "Schlüsselsicherung nur als erhöhter Windows-Administrator"
                        )
                    if not is_key_export and not win32security.CheckTokenMembership(
                        token, group
                    ):
                        raise ArchiveError(
                            "Windows-Konto ist kein freigegebener Archivbediener"
                        )
                finally:
                    token.Close()
            finally:
                win32security.RevertToSelf()
            try:
                from .protection import audit_windows_protection

                audit_windows_protection(config)
                result = dispatch.call(json.loads(raw), actor)
                response = dict(ok=True, result=result)
            except Exception as exc:
                response = dict(ok=False, error=f"{type(exc).__name__}: {exc}")
            win32file.WriteFile(pipe, storage.canonical(response))
            win32file.FlushFileBuffers(pipe)
        except ArchiveError as exc:
            try:
   
             win32file.WriteFile(
                    pipe, storage.canonical(dict(ok=False, error=str(exc)))
                )
            except pywintypes.error:
                pass
        except (pywintypes.error, ValueError):
            pass
        finally:
            try:
                win32pipe.DisconnectNamedPipe(pipe)
            except pywintypes.error:
                pass

    win32file.CloseHandle(pipe)
