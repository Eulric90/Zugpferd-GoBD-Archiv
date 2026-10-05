import pytest

from zugpferd_archiv.errors import ArchiveError
from zugpferd_archiv.protection import validate_acl


def test_operator_write_or_owner_control_is_rejected():
    with pytest.raises(ArchiveError):
        validate_acl([(0, 2, "operator")], "admin", {"admin", "service"})
    with pytest.raises(ArchiveError):
        validate_acl([(0, 0x120089, "operator")], "operator", {"admin", "service"})
    validate_acl(
        [(0, 0x120089, "operator"), (0, 0x1F01FF, "service")],
        "service",
        {"admin", "service"},
    )
