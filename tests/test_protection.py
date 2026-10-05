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


@pytest.mark.parametrize("mask", [0x40000, 0x80000, 0x40, 0x10000])
def test_parent_permission_takeover_or_deletion_is_rejected(mask):
    with pytest.raises(ArchiveError):
        validate_acl(
            [(0, mask, "operator")], "admin", {"admin", "service"}, parent_only=True
        )
