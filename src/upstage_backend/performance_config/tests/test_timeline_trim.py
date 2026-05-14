# -*- coding: utf-8 -*-

import pytest

from upstage_backend.performance_config.timeline_trim import (
    compress_sorted_times_ms,
    is_chat_topic,
    ms_to_mqtt_storage,
    mqtt_timestamp_to_ms,
)


def test_compress_sorted_times_ms():
    times = [1_000_000.0, 1_010_000.0, 1_120_000.0]
    assert compress_sorted_times_ms(times, 30_000.0) == [
        1_000_000.0,
        1_010_000.0,
        1_040_000.0,
    ]


def test_compress_sorted_times_ms_no_long_gaps():
    t = [0.0, 1000.0, 2000.0]
    assert compress_sorted_times_ms(t, 60_000.0) == t


def test_mqtt_timestamp_to_ms():
    assert mqtt_timestamp_to_ms(1000.0) == 1_000_000.0
    assert mqtt_timestamp_to_ms(1_500_000_000_000.0) == 1_500_000_000_000.0


def test_ms_to_mqtt_storage():
    assert ms_to_mqtt_storage(1000.0, 1_040_000.0) == 1040.0
    assert ms_to_mqtt_storage(1_000_000_000_000.0, 1_040_000_000_000.0) == 1_040_000_000_000.0


def test_is_chat_topic():
    assert is_chat_topic("production/foo/chat") is True
    assert is_chat_topic("production/foo/board") is False


def test_compress_negative_pause_rejects():
    with pytest.raises(ValueError):
        compress_sorted_times_ms([0.0, 1.0], -1.0)
