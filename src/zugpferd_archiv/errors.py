"""Explicit fail-closed errors shown to the operator."""


class ArchiveError(Exception):
    """An operation cannot safely proceed."""
