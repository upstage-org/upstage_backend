"""Pinned stages lead the foyer (#1568).

FOYER_PINNED_STAGES (Foyer Customisation) holds the ids of the stages that
should come before the most-recently-active ordering, in that order.
"""

from __future__ import annotations

from upstage_backend.stages.services.stage import StageService


class _Row:
    def __init__(self, value):
        self.value = value


def test_parse_pinned_stage_ids_accepts_json_lists_and_csv():
    assert StageService.parse_pinned_stage_ids(None) == []
    assert StageService.parse_pinned_stage_ids(_Row("")) == []
    assert StageService.parse_pinned_stage_ids(_Row('[3, "7", 3, "x"]')) == [3, 7]
    assert StageService.parse_pinned_stage_ids(_Row("5, 2")) == [5, 2]
    assert StageService.parse_pinned_stage_ids(_Row("5")) == [5]
    assert StageService.parse_pinned_stage_ids(_Row('"7"')) == [7]
    assert StageService.parse_pinned_stage_ids(_Row('{"a": 1}')) == []


def test_order_foyer_stages_puts_pinned_first_in_pinned_order():
    recent_first = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    ordered = StageService.order_foyer_stages(recent_first, [3, 9, 1])
    assert [s["id"] for s in ordered] == [3, 1, 2, 4]
    assert [s["pinned"] for s in ordered] == [True, True, False, False]


def test_order_foyer_stages_without_pins_is_unchanged():
    stages = [{"id": "2"}, {"id": "1"}]
    assert [s["id"] for s in StageService.order_foyer_stages(stages, [])] == ["2", "1"]
