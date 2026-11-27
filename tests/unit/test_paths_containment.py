"""
Path-containment helpers used for every user-supplied media location
(global_config/helpers/paths.py) and the base64 upload decoder
(files/file_handling.py).
"""

import base64
import os

import pytest
from graphql import GraphQLError

from upstage_backend.files.file_handling import FileHandling, decode_base64_payload
from upstage_backend.global_config.helpers.paths import (
    is_safe_relative_path,
    safe_join,
    try_safe_join,
)


@pytest.mark.parametrize(
    "value",
    ["media/abc.png", "stream-key", "avatar/x/y.gif", "a.b.c"],
)
def test_is_safe_relative_path_accepts_plain_relative_paths(value):
    assert is_safe_relative_path(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "../etc/passwd",
        "media/../../x",
        "/usr/app/main.py",
        "\\\\server\\share",
        "media\\..\\x",
        "a/./b",
        "media//x",
        "with\x00nul",
        123,
    ],
)
def test_is_safe_relative_path_rejects_traversal_and_absolute(value):
    assert is_safe_relative_path(value) is False


def test_safe_join_keeps_paths_inside_root(tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    joined = safe_join(str(root), "media", "file.png")
    assert joined == os.path.realpath(str(root / "media" / "file.png"))


@pytest.mark.parametrize("part", ["../outside.txt", "/etc/passwd", "media/../../x"])
def test_safe_join_raises_outside_root(tmp_path, part):
    with pytest.raises(GraphQLError):
        safe_join(str(tmp_path), part)


def test_safe_join_follows_symlinks_when_checking(tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside)
    with pytest.raises(GraphQLError):
        safe_join(str(root), "link", "x.txt")


def test_try_safe_join_returns_none_instead_of_raising(tmp_path):
    assert try_safe_join(str(tmp_path), "../x") is None
    assert try_safe_join(str(tmp_path), "ok.txt") is not None


def test_decode_base64_payload_accepts_data_url_and_bare_base64():
    raw = b"hello upstage"
    encoded = base64.b64encode(raw).decode()
    assert decode_base64_payload(f"data:text/plain;base64,{encoded}") == raw
    assert decode_base64_payload(encoded) == raw


@pytest.mark.parametrize("payload", ["", None, "data:text/plain;base64,", "not*base64!", "a"])
def test_decode_base64_payload_rejects_garbage(payload):
    with pytest.raises(GraphQLError):
        decode_base64_payload(payload)


def test_upload_file_refuses_sub_path_outside_storage(tmp_path):
    storage = tmp_path / "uploads"
    storage.mkdir()
    payload = "data:image/png;base64," + base64.b64encode(b"x").decode()
    with pytest.raises(GraphQLError):
        FileHandling().upload_file(payload, "a.png", None, str(storage), "../escape")
    assert not (tmp_path / "escape").exists()


def test_upload_file_writes_inside_sub_path_and_strips_directories(tmp_path):
    storage = tmp_path / "uploads"
    storage.mkdir()
    payload = "data:image/png;base64," + base64.b64encode(b"x").decode()
    location = FileHandling().upload_file(payload, "../../evil.png", None, str(storage), "media")
    assert location.startswith("media/")
    assert ".." not in location
    assert (storage / location).is_file()


def test_delete_file_ignores_none_and_directories(tmp_path):
    FileHandling().delete_file(None)
    FileHandling().delete_file(str(tmp_path))
    assert tmp_path.exists()
