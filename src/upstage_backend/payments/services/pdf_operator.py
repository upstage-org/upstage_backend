import fitz  # PyMuPDF
import io
import base64
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from upstage_backend.global_config.env import SUPPORT_EMAILS, UPLOAD_USER_CONTENT_FOLDER
from upstage_backend.global_config.helpers.background import spawn
from upstage_backend.mails.helpers.mail import send

# Resolved relative to this module, not the process working directory (the
# old "src/payments/services/..." string predates the package rename).
TEMPLATE_PATH = Path(__file__).with_name("UpStage_Receipt_Template.pdf")


def _receipt_filename(received_from: str) -> str:
    # The donor name is caller-supplied; keep only a conservative subset so
    # it can never carry path separators or shell-hostile characters.
    slug = re.sub(r"[^a-z0-9_-]+", "", received_from.strip().lower().replace(" ", "_"))
    return f"UpStage_receipt_{slug[:50] or 'donor'}.pdf"


def create_receipt_base64(received_from, date, description, amount):
    doc = fitz.open(str(TEMPLATE_PATH))

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont("Helvetica", 12)

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    # Paragraph() parses ReportLab markup: escape the free-text fields.
    data = [
        ["Received from", "Date", "Description", "Amount"],
        [
            Paragraph(escape(received_from), normal_style),
            escape(date),
            Paragraph(escape(description), normal_style),
            "USD$" + escape(amount),
        ],
    ]

    col_widths = [120, 80, 200, 80]

    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    x_pos = 60
    y_pos = 500
    tbl.wrapOn(can, A4[0], A4[1])
    tbl.drawOn(can, x_pos, y_pos - tbl._height)

    can.save()
    packet.seek(0)

    overlay_pdf = fitz.open("pdf", packet.read())
    page = doc[0]
    page.show_pdf_page(page.rect, overlay_pdf, 0)

    out_buf = io.BytesIO()
    doc.save(out_buf)
    doc.close()
    pdf_bytes = out_buf.getvalue()

    file_name = _receipt_filename(received_from)
    receipts_dir = os.path.join(UPLOAD_USER_CONTENT_FOLDER, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)
    file_path = os.path.join(receipts_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    admin_emails = SUPPORT_EMAILS
    spawn(
        send(
            admin_emails,
            "Donation receipt issued",
            content="",
            filenames=[file_path],
        )
    )

    return {
        "fileBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
        "fileName": file_name,
    }
