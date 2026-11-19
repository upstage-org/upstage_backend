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
    # Forget a font registered by an earlier test so each path is exercised.
    pdfmetrics._fonts.pop(pdf_operator.BODY_FONT_NAME, None)
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


def test_uses_a_font_file_when_one_exists(quiet_receipt):
    name = pdf_operator.body_font_name()
    has_file = any(p and __import__("os").path.isfile(p) for p in pdf_operator.FONT_CANDIDATES)
    assert name == (pdf_operator.BODY_FONT_NAME if has_file else pdf_operator.CID_FALLBACK)
