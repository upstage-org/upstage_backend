"""
helpers.clock and the serializer: timestamps are aware UTC inside the
application and always leave it with an explicit offset.
"""

from datetime import datetime, timedelta, timezone

from upstage_backend.global_config.helpers.clock import UTC, as_utc, utcnow
from upstage_backend.stages.db_models.stage import StageModel


def test_utcnow_is_aware_utc():
    now = utcnow()
    assert now.tzinfo is UTC
    assert now.utcoffset() == timedelta(0)


def test_as_utc_reads_naive_values_as_utc():
    naive = datetime(2026, 3, 1, 10, 0, 0)  # noqa: DTZ001  (the naive input is the point)
    assert as_utc(naive) == datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)


def test_as_utc_converts_other_zones():
    auckland = timezone(timedelta(hours=13))
    local = datetime(2026, 3, 1, 23, 0, 0, tzinfo=auckland)
    assert as_utc(local) == datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
    assert as_utc(local).utcoffset() == timedelta(0)


def test_naive_and_aware_database_values_compare():
    # A database that has not run the timestamptz migration yet still hands
    # back naive values; comparisons must work against both.
    stored_naive = datetime(2026, 3, 1, 10, 0, 0)  # noqa: DTZ001
    stored_aware = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
    cutoff = datetime(2026, 3, 1, 10, 30, 0, tzinfo=UTC)
    assert as_utc(stored_naive) < cutoff
    assert as_utc(stored_aware) < cutoff


def test_to_dict_always_carries_the_offset():
    naive = StageModel(name="s", file_location="s", owner_id=1)
    naive.created_on = datetime(2026, 3, 1, 10, 0, 0)  # noqa: DTZ001
    aware = StageModel(name="s", file_location="s", owner_id=1)
    aware.created_on = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

    assert naive.to_dict()["created_on"] == "2026-03-01T10:00:00+00:00"
    assert aware.to_dict()["created_on"] == "2026-03-01T10:00:00+00:00"
    assert naive.to_dict()["last_access"] is None
