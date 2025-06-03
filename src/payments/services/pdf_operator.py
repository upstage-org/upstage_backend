import asyncio
import fitz  # PyMuPDF
import io
import base64

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from global_config.env import SUPPORT_EMAILS
from mails.helpers.mail import send


def create_receipt_base64(received_from, date, description, amount):
    template_path = "src/payments/services/UpStage_Receipt_Template.pdf"
    doc = fitz.open(template_path)

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont("Helvetica", 12)

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    data = [
        ["Received from", "Date", "Description", "Amount"],
        [
            Paragraph(received_from, normal_style),
            date,
            Paragraph(description, normal_style),
            "USD$" + amount,
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

    file_path = (
        f"./uploads/UpStage_receipt_{received_from.replace(' ', '_').lower()}.pdf"
    )
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    admin_emails = SUPPORT_EMAILS
    asyncio.create_task(
        send(
            admin_emails,
            "Donation receipt issued",
            content="",
            filenames=[file_path],
        )
    )

    return {
        "fileBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
        "fileName": f"UpStage_receipt_{received_from.replace(' ', '_').lower()}.pdf",
    }
