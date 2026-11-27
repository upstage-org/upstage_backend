"""
One clock for the whole backend: timezone-aware UTC.

Every timestamp column is `timestamptz`; a naive `datetime.now()` is only
correct while the process happens to run in UTC, and cannot be compared with
the aware values the database returns.
"""

from datetime import datetime, timezone

UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """
    `value` as an aware UTC datetime. Naive values are taken to be UTC: that
    is what every naive timestamp this application ever stored meant (the
    containers and Postgres run in UTC).
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
