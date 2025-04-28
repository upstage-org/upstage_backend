import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
import base64

def create_receipt_base64(received_from, date, description, amount):
    template_path = "src/payments/services/UpStage_Receipt_Template.pdf"
    doc = fitz.open(template_path)

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    can.setFont("Helvetica", 12)


    can.drawString(70, 450, received_from)
    can.drawString(200, 450, date)
    can.drawString(330, 450, description)
    can.drawString(450, 450, amount)

    can.save()

    packet.seek(0)

    overlay = fitz.open("pdf", packet.read())

    page = doc[0]
    page.show_pdf_page(page.rect, overlay, 0)

    output_buffer = io.BytesIO()
    doc.save(output_buffer)
    doc.close()


    pdf_bytes = output_buffer.getvalue()

    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    return pdf_base64
