from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from io import BytesIO
import segno
from PIL import Image

def create_qr_overlay(qr_data_list, page_size=A4):
    """
    Creates a transparent PDF overlay with QR codes.
    qr_data_list: List of dicts with {'content': url, 'x': x_pos, 'y': y_pos, 'size': size}
    """
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=page_size)
    
    for item in qr_data_list:
        content = item['content']
        x = item['x']
        y = item['y']
        size = item.get('size', 80)
        
        # Generate QR code using segno
        qr = segno.make(content)
        out = BytesIO()
        qr.save(out, kind='png', scale=5)
        out.seek(0)
        
        img = Image.open(out)
        can.drawInlineImage(img, x, y, width=size, height=size)
        
    can.save()
    packet.seek(0)
    return packet

def add_qr_to_pdf(input_pdf_path, output_pdf_path, qr_configs):
    """
    qr_configs: list of dicts with qr info
    """
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    
    # Get first page
    first_page = reader.pages[0]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)
    
    # Create overlay for the first page
    overlay_pdf = create_qr_overlay(qr_configs, page_size=(width, height))
    overlay_reader = PdfReader(overlay_pdf)
    overlay_page = overlay_reader.pages[0]
    
    # Merge overlay with first page
    first_page.merge_page(overlay_page)
    
    # Add all pages to writer
    for page in reader.pages:
        writer.add_page(page)
        
    with open(output_pdf_path, "wb") as f:
        writer.write(f)
