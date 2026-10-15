"""Which command errors count as a database outage (docs/DECISIONS.md ADR-127)."""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError, IntegrityError, InterfaceError, OperationalError

from bot.client import is_database_outage


def test_unreachable_database_is_an_outage() -> None:
    assert is_database_outage(OperationalError("SELECT 1", {}, Exception("SSL/TLS required")))
    assert is_database_outage(InterfaceError("SELECT 1", {}, Exception("closed")))
    assert is_database_outage(ConnectionRefusedError())
    assert is_database_outage(
        DBAPIError("SELECT 1", {}, Exception("gone"), connection_invalidated=True)
    )


def test_bugs_and_bad_queries_are_not() -> None:
    assert not is_database_outage(IntegrityError("INSERT", {}, Exception("duplicate")))
    assert not is_database_outage(KeyError("x"))
    assert not is_database_outage(ValueError("bad"))
