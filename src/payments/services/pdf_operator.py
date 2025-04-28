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
    can.drawString(190, 450, date)
    # can.drawString(305, 450, description)
    can.drawString(430, 450, amount)
    x_start = 305
    x_end = 410
    y_position = 450  # Initial y position for the text

    max_width = x_end - x_start

    # Create a text object to calculate the wrapped text
    text_object = can.beginText(x_start, y_position)
    text_object.setFont("Helvetica", 12)
    text_object.setTextOrigin(x_start, y_position)

    # Wrap the description text to fit within the available width
    words = description.split()
    line = ""
    for word in words:
        # Try adding the word to the current line
        test_line = line + " " + word if line else word
        width = can.stringWidth(test_line, "Helvetica", 12)
        
        # If the line width exceeds max width, start a new line
        if width > max_width:
            text_object.textLine(line)
            line = word  # Start a new line with the current word
        else:
            line = test_line
    
    # Add the last line to the text object
    if line:
        text_object.textLine(line)
    
    # Draw the wrapped text on the PDF
    can.drawText(text_object)

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
