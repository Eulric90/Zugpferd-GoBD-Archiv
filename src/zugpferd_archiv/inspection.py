"""Bound parsing in a separate process; timeout/memory failure stays unverified."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from .invoice import MAX_FILE, VERSION


def analyze_bounded(path: Path) -> dict:
    if path.stat().st_size > MAX_FILE:
        return dict(
            format="Ungeprüft",
            critical_errors=["Größenlimit 64 MiB überschritten"],
            validator_version=VERSION,
            xml=None,
        )
    with tempfile.TemporaryDirectory(prefix="zugpferd-parse-") as directory:
        output = Path(directory) / "inspection.json"
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command += ["-m", "zugpferd_archiv.main"]
        command += ["--inspect-file", str(path), "--inspection-output", str(output)]
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        job = None
        try:
            if os.name == "nt":
                import win32api
                import win32con
                import win32job

                job = win32job.CreateJobObject(
                    None, "ZugpferdParse-" + uuid.uuid4().hex
                )
                limits = win32job.QueryInformationJobObject(
                    job, win32job.JobObjectExtendedLimitInformation
                )
                limits["BasicLimitInformation"]["LimitFlags"] = (
                    win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
                    | win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                )
                limits["ProcessMemoryLimit"] = 1024 * 1024 * 1024
                win32job.SetInformationJobObject(
                    job, win32job.JobObjectExtendedLimitInformation, limits
                )
                handle = win32api.OpenProcess(
                    win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE,
                    False,
                    process.pid,
                )
                try:
                    win32job.AssignProcessToJobObject(job, handle)
                finally:
                    handle.Close()
            if process.wait(timeout=30) != 0 or not output.is_file():
                raise RuntimeError(
                    "Parser-Prozess fehlgeschlagen oder Speichergrenze erreicht"
                )
            result = json.loads(output.read_text(encoding="utf-8"))
            if result.get("xml"):
                result["xml"] = base64.b64decode(result["xml"], validate=True)
            return result
        except Exception as exc:
            process.kill()
            process.wait(timeout=5)
            return dict(
                format="Ungeprüft",
                profile="Klärung erforderlich",
                critical_errors=[str(exc)],
                validator_version=VERSION,
                xml=None,
            )
        finally:
            if job is not None:
                job.Close()


def inspect_to_file(source: Path, destination: Path) -> None:
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    from .invoice import analyze_file
    from . import storage

    result = analyze_file(source)
    if result.get("xml"):
        result["xml"] = base64.b64encode(result["xml"]).decode()
    storage.write_new(destination, storage.canonical(result))
