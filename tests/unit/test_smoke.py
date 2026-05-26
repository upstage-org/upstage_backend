"""Starter smoke tests for the DB-free pre-push gate.

The point of this file is NOT comprehensive coverage — it's to make
the pre-push hook actually do something useful on day one and to make
import-graph regressions impossible to miss locally. Real DB-backed
tests live in `src/upstage_backend/<module>/tests/` (which can use
the in-memory SQLite rebind from `tests/conftest.py::rebound_db`).

Grow this file (and the wider `tests/unit/` directory) as new
DB-free unit-tests get added, especially for pure helpers and value
objects.
"""

from __future__ import annotations


def test_pure_logic_module_imports() -> None:
    """`performance_config.timeline_trim` is leaf-level pure-Python and a
    canary for "did somebody break the import graph in src/".
    """
    from upstage_backend.performance_config import timeline_trim

    assert callable(timeline_trim.compress_sorted_times_ms)
    assert callable(timeline_trim.mqtt_timestamp_to_ms)


def test_compress_sorted_times_ms_basic() -> None:
    """Anchor: at most one elementary correctness check per leaf util,
    so a refactor that quietly inverts the algorithm trips this gate.
    """
    from upstage_backend.performance_config.timeline_trim import (
        compress_sorted_times_ms,
    )

    assert compress_sorted_times_ms([], 1000.0) == []

    # No gap exceeds the minimum pause -> nothing is shifted.
    assert compress_sorted_times_ms([0.0, 100.0, 200.0], 1000.0) == [0.0, 100.0, 200.0]

    # A 5s idle gap with a 1s minimum pause shrinks by 4s.
    out = compress_sorted_times_ms([0.0, 5000.0, 6000.0], 1000.0)
    assert out == [0.0, 1000.0, 2000.0]


def test_mqtt_timestamp_normalisation() -> None:
    """Mixed seconds-vs-milliseconds inputs from old / new clients.

    Anything below 1e12 is treated as seconds and scaled up; anything
    above is already milliseconds and passes through. Locking this
    anchors the implicit contract every replay path depends on.
    """
    from upstage_backend.performance_config.timeline_trim import (
        mqtt_timestamp_to_ms,
    )

    assert mqtt_timestamp_to_ms(None) == 0.0
    assert mqtt_timestamp_to_ms(1.5) == 1500.0
    assert mqtt_timestamp_to_ms(1_700_000_000_000.0) == 1_700_000_000_000.0
