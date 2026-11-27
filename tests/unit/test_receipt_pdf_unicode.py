"""Donation receipts must show the donor's name in any script, not boxes."""

import base64

import pymupdf
import pytest
from reportlab.pdfbase import pdfmetrics

from upstage_backend.payments.services import pdf_operator


@pytest.fixture
def quiet_receipt(monkeypatch, tmp_path):
    """No e-mail, files under a temp folder, fonts re-resolved per test."""
    monkeypatch.setattr(pdf_operator, "UPLOAD_USER_CONTENT_FOLDER", str(tmp_path))
    monkeypatch.setattr(
        pdf_operator, "spawn", lambda coro: coro.close() if hasattr(coro, "close") else None
    )
    monkeypatch.setattr(pdf_operator, "send", lambda *a, **k: None)
    # Forget fonts registered by an earlier test so each path is exercised.
    pdfmetrics._fonts.pop(pdf_operator.BODY_FONT_NAME, None)
    pdfmetrics._fonts.pop(pdf_operator.CID_FALLBACK, None)
    return tmp_path


def _text_of(result: dict) -> str:
    pdf = base64.b64decode(result["fileBase64"])
    with pymupdf.open("pdf", pdf) as doc:
        return "".join(page.get_text() for page in doc)


def test_cjk_donor_name_is_in_the_receipt(quiet_receipt):
    result = pdf_operator.create_receipt_base64(
        "張三 (Zhang San)", "2026-11-20", "捐款 — 謝謝 😀", "25"
    )
    text = _text_of(result)
    assert "張三" in text
    assert "捐款" in text
    assert "謝謝" in text
    assert "Zhang San" in text
    assert "USD$25" in text
    # The file name stays ASCII (it travels in a mail header); the PDF holds the real name.
    assert result["fileName"].isascii() and result["fileName"].endswith(".pdf")


def test_falls_back_to_a_reader_supplied_cid_font_without_font_files(quiet_receipt, monkeypatch):
    monkeypatch.setattr(pdf_operator, "FONT_CANDIDATES", [])
    assert pdf_operator.body_font_name() == pdf_operator.CID_FALLBACK
    result = pdf_operator.create_receipt_base64("李四", "2026-11-20", "捐款", "10")
    assert "李四" in _text_of(result)


def _cjk_capable(font_name: str) -> bool:
    font = pdfmetrics.getFont(font_name)
    glyphs = getattr(getattr(font, "face", None), "charToGlyph", None)
    # A CID font has no glyph table to inspect: the reader supplies it.
    return glyphs is None or bool(glyphs.get(pdf_operator.CJK_PROBE))


def test_registered_body_font_can_draw_cjk(quiet_receipt):
    """Whatever wins the candidate search must actually have CJK glyphs.

    The deployed image once had only Noto CJK (CFF outlines, which ReportLab
    refuses) and DejaVu (loads, no CJK) — the search then "succeeded" with
    DejaVu and receipts printed boxes while this suite stayed green on a host
    with another font.
    """
    name = pdf_operator.body_font_name()
    assert _cjk_capable(name)


def test_a_latin_only_candidate_is_skipped_for_the_cid_fallback(
    quiet_receipt, monkeypatch, tmp_path
):
    import os

    dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.isfile(dejavu):
        pytest.skip("DejaVu not installed on this host")
    pdfmetrics._fonts.pop(pdf_operator.CID_FALLBACK, None)
    monkeypatch.setattr(pdf_operator, "FONT_CANDIDATES", [dejavu])
    assert pdf_operator.body_font_name() == pdf_operator.CID_FALLBACK
    result = pdf_operator.create_receipt_base64("王五", "2026-11-20", "捐款", "10")
    assert "王五" in _text_of(result)


def test_an_unloadable_candidate_is_skipped(quiet_receipt, monkeypatch, tmp_path):
    bogus = tmp_path / "not-a-font.ttf"
    bogus.write_bytes(b"not a font")
    pdfmetrics._fonts.pop(pdf_operator.CID_FALLBACK, None)
    monkeypatch.setattr(pdf_operator, "FONT_CANDIDATES", [str(bogus)])
    assert pdf_operator.body_font_name() == pdf_operator.CID_FALLBACK
