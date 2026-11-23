"""Pictures embedded as data: URIs are sent as inline (cid:) parts (#1575).

The rich text editor lets an admin pick a picture from their computer; it is
stored in the HTML as a data: URI. Most mail programs do not display data:
URIs, so a signature logo added that way never showed in the e-mail.
"""

from __future__ import annotations

import base64

import pytest

from upstage_backend.mails.helpers.mail import create_email, inline_data_images

# A real 1x1 PNG.
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
PNG_BYTES = base64.b64decode(PNG)


def _img(payload=PNG, kind="png", quote='"', extra=' alt="logo" width="120"'):
    return f"<img{extra} src={quote}data:image/{kind};base64,{payload}{quote}>"


def test_html_without_data_images_is_untouched():
    html = '<p>Hello <img src="https://upstage.live/logo.png" alt="x"></p>'
    assert inline_data_images(html) == (html, [])
    assert inline_data_images("") == ("", [])
    assert inline_data_images(None) == (None, [])


def test_data_image_becomes_a_cid_reference_and_an_inline_part():
    html, parts = inline_data_images(f"<p>Regards</p><p>{_img()}</p>")
    assert "data:image" not in html
    assert len(parts) == 1
    part = parts[0]
    cid = part["Content-ID"].strip("<>")
    assert f'src="cid:{cid}"' in html
    assert 'alt="logo" width="120"' in html  # other attributes are kept
    assert part.get_content_type() == "image/png"
    assert part.get_payload(decode=True) == PNG_BYTES
    assert part["Content-Disposition"].startswith("inline")


def test_the_same_picture_twice_is_one_part_and_different_pictures_are_two():
    other = base64.b64encode(PNG_BYTES + b"\x00").decode()
    html, parts = inline_data_images(_img() + _img() + _img(payload=other, kind="jpg"))
    assert len(parts) == 2
    assert html.count("cid:") == 3
    assert {p.get_content_type() for p in parts} == {"image/png", "image/jpeg"}


def test_single_quotes_and_wrapped_base64_are_understood():
    wrapped = PNG[:20] + "\n   " + PNG[20:]
    html, parts = inline_data_images(_img(payload=wrapped, quote="'"))
    assert len(parts) == 1
    assert parts[0].get_payload(decode=True) == PNG_BYTES
    assert "src='cid:" in html


def test_unsupported_or_broken_payloads_are_left_alone():
    svg = '<img src="data:image/svg+xml;base64,PHN2Zy8+">'
    broken = '<img src="data:image/png;base64,@@@notbase64@@@">'
    assert inline_data_images(svg) == (svg, [])
    assert inline_data_images(broken) == (broken, [])


class _NoConfig:
    """Stands in for the database session create_email opens for the subject prefix."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []


@pytest.fixture(autouse=True)
def _no_database(monkeypatch):
    monkeypatch.setattr("upstage_backend.mails.helpers.mail.ScopedSession", _NoConfig)


def _html_parts(message):
    return [p for p in message.walk() if p.get_content_type() == "text/html"]


def test_create_email_sends_related_html_with_the_picture_inline():
    message = create_email(
        to=["someone@example.com"], subject="Hi", html=f"<p>Body</p>{_img()}", cc=[], bcc=[]
    )
    types = [p.get_content_type() for p in message.walk()]
    assert "multipart/related" in types
    assert "image/png" in types
    html = _html_parts(message)[0].get_payload(decode=True).decode()
    assert "data:image" not in html and "cid:img-" in html
    # the plain-text alternative is still there, before the HTML
    assert types.index("text/plain") < types.index("text/html")


def test_create_email_without_data_images_is_built_as_before():
    message = create_email(
        to=["someone@example.com"], subject="Hi", html="<p>Body</p>", cc=[], bcc=[]
    )
    types = [p.get_content_type() for p in message.walk()]
    assert "multipart/related" not in types
    assert types.count("text/html") == 1 and types.count("text/plain") == 1
