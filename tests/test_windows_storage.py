"""Windows error paths exercised deterministically without real volumes."""

import ctypes
from ctypes import wintypes
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from zugpferd_archiv import storage


@pytest.fixture
def kernel(monkeypatch):
    api = SimpleNamespace(
        **{
            name: Mock()
            for name in (
                "CreateFileW",
                "FlushFileBuffers",
                "CloseHandle",
                "OpenProcess",
                "GetExitCodeProcess",
            )
        }
    )
    monkeypatch.setattr(ctypes, "WinDLL", Mock(return_value=api), raising=False)
    monkeypatch.setattr(
        ctypes,
        "WinError",
        lambda code=0: OSError(code, "Windows failure"),
        raising=False,
    )
    return api


def test_denied_volume_flush_does_not_require_service_admin_rights(
    kernel, monkeypatch, tmp_path
):
    kernel.CreateFileW.return_value = ctypes.c_void_p(-1).value
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    storage._flush_volume_windows(tmp_path)
    assert kernel.CreateFileW.call_count == 1
    kernel.FlushFileBuffers.assert_not_called()
    kernel.CloseHandle.assert_not_called()


def test_unavailable_volume_is_still_a_hard_failure(kernel, monkeypatch, tmp_path):
    kernel.CreateFileW.return_value = ctypes.c_void_p(-1).value
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 21, raising=False)
    with pytest.raises(OSError) as error:
        storage._flush_volume_windows(tmp_path)
    assert error.value.errno == 21


def test_native_flush_keeps_full_width_handle_and_original_error(
    kernel, monkeypatch, tmp_path
):
    handle = 0x123456789
    kernel.CreateFileW.return_value = handle
    kernel.FlushFileBuffers.return_value = False
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 1117, raising=False)
    with pytest.raises(OSError) as error:
        storage._flush_volume_windows(tmp_path)
    assert error.value.errno == 1117
    assert kernel.CreateFileW.restype is wintypes.HANDLE
    assert kernel.FlushFileBuffers.argtypes == [wintypes.HANDLE]
    kernel.FlushFileBuffers.assert_called_once_with(handle)
    kernel.CloseHandle.assert_called_once_with(handle)


def test_required_file_fsync_failure_is_not_ignored(monkeypatch, tmp_path):
    monkeypatch.setattr(
        storage.os, "fsync", Mock(side_effect=OSError("file flush failed"))
    )
    with pytest.raises(OSError, match="file flush failed"):
        storage.write_new(tmp_path / "new.json", b"original")


def test_process_access_denied_is_not_evidence_of_stale_lock(kernel, monkeypatch):
    monkeypatch.setattr(storage, "os", SimpleNamespace(name="nt"))
    kernel.OpenProcess.return_value = None
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    assert storage._process_alive(12345)


def test_missing_process_is_not_reported_alive(kernel, monkeypatch):
    monkeypatch.setattr(storage, "os", SimpleNamespace(name="nt"))
    kernel.OpenProcess.return_value = None
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 87, raising=False)
    assert not storage._process_alive(12345)


def test_process_query_uses_full_width_handle(kernel, monkeypatch):
    monkeypatch.setattr(storage, "os", SimpleNamespace(name="nt"))
    handle = 0x123456789
    kernel.OpenProcess.return_value = handle

    def exit_code(actual_handle, pointer):
        assert actual_handle == handle
        pointer._obj.value = 259
        return True

    kernel.GetExitCodeProcess.side_effect = exit_code
    assert storage._process_alive(12345)
    assert kernel.GetExitCodeProcess.argtypes == [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.CloseHandle.assert_called_once_with(handle)
