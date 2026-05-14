# -*- coding: utf-8 -*-
"""Timeline compression: shrink idle gaps longer than a minimum pause (milliseconds)."""

from __future__ import annotations


def mqtt_timestamp_to_ms(raw: float | None) -> float:
    if raw is None:
        return 0.0
    x = float(raw)
    if x >= 1e12:
        return x
    return x * 1000.0


def ms_to_mqtt_storage(prev_raw: float | None, new_ms: float) -> float:
    if prev_raw is None:
        return float(new_ms) / 1000.0
    p = float(prev_raw)
    if p >= 1e12:
        return float(new_ms)
    return float(new_ms) / 1000.0


def compress_sorted_times_ms(times: list[float], min_pause_ms: float) -> list[float]:
    if min_pause_ms < 0:
        raise ValueError("min_pause_ms must be non-negative")
    if not times:
        return []
    out: list[float] = [times[0]]
    removal = 0.0
    for i in range(1, len(times)):
        gap = times[i] - times[i - 1]
        if gap > min_pause_ms:
            removal += gap - min_pause_ms
        out.append(times[i] - removal)
    return out


def is_chat_topic(topic: str | None) -> bool:
    return bool(topic) and topic.endswith("/chat")
