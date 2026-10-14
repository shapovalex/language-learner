"""Comparing a port with its fake and its adapter (AD-1: every fake is kept in step)."""

import inspect


def public_methods(cls: type) -> dict[str, inspect.Signature]:
    """Each public function `cls` defines or inherits, by name, with its signature."""
    return {
        name: inspect.signature(member)
        for name, member in inspect.getmembers(cls, inspect.isfunction)
        if not name.startswith("_")
    }
