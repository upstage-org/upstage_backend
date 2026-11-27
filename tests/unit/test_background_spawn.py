"""global_config/helpers/background.spawn keeps a strong reference and logs failures."""

import asyncio
import gc

import pytest

from upstage_backend.global_config.helpers import background


async def _ok():
    await asyncio.sleep(0)
    return "done"


async def _boom():
    await asyncio.sleep(0)
    raise RuntimeError("boom")


@pytest.mark.anyio
async def test_spawn_tracks_until_done_and_forgets_after():
    task = background.spawn(_ok(), name="ok")
    assert task in background._TASKS
    gc.collect()
    assert await task == "done"
    await asyncio.sleep(0)
    assert task not in background._TASKS


@pytest.mark.anyio
async def test_spawn_swallows_and_logs_exception(monkeypatch):
    logged = []

    class _Logger:
        def opt(self, **_):
            return self

        def error(self, *args):
            logged.append(args)

    monkeypatch.setattr(background, "logger", _Logger())
    task = background.spawn(_boom(), name="boom")
    with pytest.raises(RuntimeError):
        await task
    await asyncio.sleep(0)
    assert logged and "boom" in logged[0][1]
    assert task not in background._TASKS
